"""로컬 웹 UI (Flask) — Core를 재사용하는 GUI 인터페이스 (Phase 5, D-028).

브라우저에서 두 가지를 한다:
- "데모 실행": test_definition.yaml의 10셸을 자동 실행(/run, SSE 실시간 진행).
- "업로드 검증": As-Is 입력+정답 한 쌍을 올려 풀체인(적재→배치→추출→비교→리포트) 실행(/verify/run).

Core는 무수정 — CLI와 동일하게 run_full_comparison(config, on_progress, shell_ids)만 호출한다.

설계 결정(D-028):
- 진행 스트리밍: run_full_comparison을 백그라운드 스레드에서 실행, on_progress 콜백이 큐에 이벤트를
  넣고 제너레이터가 흘린다(데모=SSE, 업로드=NDJSON). 종료 시 done 메시지로 클라가 스트림을 닫는다.
- 동시 실행 1건 제한: 비차단 Lock. **해제는 try/finally**로 보장(클라 끊김에도 누수 없음)(§③).
- /report 다운로드: secure_filename + report_dir 하위로 제한해 경로 traversal 차단(§①).
- 비밀번호는 UI에 두지 않고 서버 기동 시 POSTGRES_PASSWORD env에서 읽는다(D-019 일관).
- 표시용 dict 직렬화는 src/gui/serialize.py에만(§②, models 불변).

print 등 사람용 출력은 인터페이스인 여기서만(CLAUDE 3-1). app.run(threaded=True)(§③).
"""

from __future__ import annotations

import json
import os
import queue
import shutil
import tempfile
import threading
import time
import webbrowser
from pathlib import Path

from flask import Flask, Response, abort, render_template, request, send_file
from werkzeug.utils import secure_filename

from src.config.settings import load_config, parse_shell_selector
from src.core import run_full_comparison

from .serialize import event_to_dict, summary_to_dict
from .upload import prepare_job

app = Flask(__name__)

# 동시 실행 1건 제한(데모용). 해제는 스트림 제너레이터의 finally에서(§③).
_run_lock = threading.Lock()


@app.route("/")
def index():
    """단일 페이지. 기본 config 경로를 함께 내려 폼 초기값으로 쓴다."""
    return render_template("index.html", default_config="./config.yaml")


@app.route("/run")
def run():
    """데모 실행: 정의 파일의 셸들을 실행하며 진행을 SSE로 스트리밍한다.

    쿼리: config(설정 경로), shells(범위/ID, 선택).
    """
    config_path = request.args.get("config") or "./config.yaml"
    shells = request.args.get("shells") or None

    def stream():
        if not _run_lock.acquire(blocking=False):
            yield _sse({"type": "error", "message": "이미 다른 실행이 진행 중입니다."})
            yield _sse({"type": "done"})
            return
        try:
            events: queue.Queue = queue.Queue()

            def worker():
                start = time.perf_counter()
                try:
                    config = load_config(config_path)
                    shell_ids = parse_shell_selector(shells) if shells else None
                    summary = run_full_comparison(
                        config,
                        on_progress=lambda e: events.put({"type": "progress", **event_to_dict(e)}),
                        shell_ids=shell_ids,
                    )
                    elapsed = time.perf_counter() - start
                    events.put({"type": "summary", **summary_to_dict(summary, elapsed)})
                except Exception as exc:  # noqa: BLE001 — 어떤 실패든 브라우저에 메시지로
                    events.put({"type": "error", "message": str(exc)})
                finally:
                    events.put({"type": "done"})

            threading.Thread(target=worker, daemon=True).start()
            while True:
                msg = events.get()
                yield _sse(msg)
                if msg["type"] == "done":
                    break
        finally:
            _run_lock.release()  # §③ 클라 끊김·예외에도 반드시 해제

    return Response(stream(), mimetype="text/event-stream")


@app.route("/verify/run", methods=["POST"])
def verify_run():
    """업로드 1쌍(As-Is 입력 + 정답)으로 풀체인 검증을 실행하고 진행을 NDJSON으로 스트리밍한다.

    멀티파트라 EventSource(GET) 대신 fetch+스트림을 쓰므로 SSE가 아닌 NDJSON 프레임을 보낸다.
    """
    input_type = request.form.get("input_type") or "database"
    output_type = request.form.get("output_type") or "file"
    encoding = request.form.get("encoding") or "Shift_JIS"
    base_config = request.form.get("config") or "./config.yaml"
    f_in = request.files.get("asis_input")
    f_out = request.files.get("asis_output")
    # 요청 컨텍스트가 살아 있을 때 바이트를 읽어 둔다(제너레이터는 나중에 실행됨).
    in_bytes = f_in.read() if f_in else b""
    out_bytes = f_out.read() if f_out else b""

    def stream():
        if not _run_lock.acquire(blocking=False):
            yield _ndjson({"type": "error", "message": "이미 다른 실행이 진행 중입니다."})
            yield _ndjson({"type": "done"})
            return
        tmpdir = None
        try:
            if not in_bytes or not out_bytes:
                yield _ndjson({"type": "error", "message": "As-Is 입력과 정답 CSV를 모두 올려주세요."})
                yield _ndjson({"type": "done"})
                return
            try:
                config, tmpdir = prepare_job(
                    base_config,
                    asis_input=in_bytes,
                    asis_output=out_bytes,
                    input_type=input_type,
                    output_type=output_type,
                    encoding=encoding,
                )
            except Exception as exc:  # noqa: BLE001
                yield _ndjson({"type": "error", "message": f"준비 실패: {exc}"})
                yield _ndjson({"type": "done"})
                return

            events: queue.Queue = queue.Queue()

            def worker():
                start = time.perf_counter()
                try:
                    summary = run_full_comparison(
                        config,
                        on_progress=lambda e: events.put({"type": "progress", **event_to_dict(e)}),
                        shell_ids=["up1"],
                    )
                    elapsed = time.perf_counter() - start
                    events.put({"type": "summary", **summary_to_dict(summary, elapsed)})
                except Exception as exc:  # noqa: BLE001
                    events.put({"type": "error", "message": str(exc)})
                finally:
                    events.put({"type": "done"})

            threading.Thread(target=worker, daemon=True).start()
            while True:
                msg = events.get()
                yield _ndjson(msg)
                if msg["type"] == "done":
                    break
        finally:
            _run_lock.release()
            _cleanup_tmpdir(tmpdir)  # 임시 작업폴더만 정리(리포트는 out/reports라 보존)

    return Response(stream(), mimetype="application/x-ndjson")


@app.route("/report/<name>")
def report(name: str):
    """리포트 CSV 다운로드. secure_filename + report_dir 하위 제한으로 traversal 차단(§①)."""
    config = load_config(request.args.get("config") or "./config.yaml")
    base = config.report_dir.resolve()
    target = (base / secure_filename(name)).resolve()
    # 정규화 후에도 report_dir 하위인지 재확인(이중 가드).
    if base != target and base not in target.parents:
        abort(404)
    if not target.is_file():
        abort(404)
    return send_file(target, as_attachment=True)


def _sse(payload: dict) -> str:
    """dict를 SSE 데이터 프레임으로 직렬화한다(데모 실행 /run용, GET)."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _ndjson(payload: dict) -> str:
    """dict를 NDJSON 한 줄로 직렬화한다(업로드 /verify/run용, POST 스트림)."""
    return json.dumps(payload, ensure_ascii=False) + "\n"


def _cleanup_tmpdir(tmpdir) -> None:
    """업로드 임시 작업폴더를 삭제한다. **시스템 임시 디렉토리 하위만** 삭제하는 안전장치.

    prepare_job은 tempfile.mkdtemp() 경로를 돌려주므로 정상 동작하며, 혹시라도 잘못된 경로
    (예: cwd '.')가 넘어와도 임시 디렉토리 밖이면 삭제하지 않는다(작업트리 보호).
    """
    if tmpdir is None:
        return
    tmp_root = Path(tempfile.gettempdir()).resolve()
    target = Path(tmpdir).resolve()
    if target == tmp_root or tmp_root not in target.parents:
        return  # 임시 디렉토리 하위가 아니면 절대 삭제하지 않음
    shutil.rmtree(target, ignore_errors=True)


def main() -> None:
    """개발용 로컬 서버 기동 + 브라우저 자동 오픈(§④)."""
    host = os.environ.get("GUI_HOST", "127.0.0.1")
    port = int(os.environ.get("GUI_PORT", "8000"))
    url = f"http://{host}:{port}/"
    # 서버가 뜬 직후 브라우저를 연다(리로더 자식 프로세스에선 열지 않음).
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    main()
