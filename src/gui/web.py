"""로컬 웹 UI (Flask) — Core를 재사용하는 GUI 인터페이스 (Phase 7, T7-3 경량화 / D-034).

운영 타깃 화면은 **버튼 1개 → 자동 실행(Shell 1~1000) → 실시간 모니터링 → 결과**다.
데이터·정답·정의 파일은 `config.yaml`이 가리키는 디렉토리에 이미 있고(설치 시 준비),
화면은 그 정의를 그대로 실행만 한다 — CLI와 동일하게 `run_full_comparison(config, on_progress)`.

화면은 두 영역:
- "設定/接続"(접이식): DB 접속 테스트(읽기전용) + config.yaml 저장(/connection/*). 설치 시 1회.
- "検証実行": config의 정의 파일을 실행하며 진행을 SSE로 스트리밍(/run). 실시간 모니터링 + 결과.

설계 결정:
- 비밀번호는 UI에 두지 않고 서버 env(password_env)에서만 읽는다(모델 A, D-019).
- 검증 정의의 정본은 **정의 파일**(DEFINITION_SPEC) — 화면에 입력 타입·테이블 선택칸을 두지 않는다.
  실행 전 셸 수·셸별 I/O는 정의 파일을 읽어 미리보기로만 보여준다(읽기전용).
- 동시 실행 1건 락(try/finally), traversal 차단은 유지. Core 무수정.

T7-3에서 걷어낸 것(불필요·간결, D-028~031 supersede): 브라우저 업로드-CSV 검증,
매핑표→yaml 생성, 화면 테이블선택 3칸, 탭/위저드. 디렉토리 기반 단일 실행으로 일원화.

print 등 사람용 출력은 인터페이스인 여기서만(CLAUDE 3-1). app.run(threaded=True).
"""

from __future__ import annotations

import json
import os
import queue
import threading
import time
import webbrowser
from pathlib import Path

from flask import Flask, Response, abort, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from src.config.settings import load_config, parse_shell_selector
from src.core import run_full_comparison

from . import connection
from .serialize import event_to_dict, summary_to_dict
from .upload import summarize_definition_path

app = Flask(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLE_CONFIG = str(_REPO_ROOT / "config.yaml.example")

# 동시 실행 1건 제한. 해제는 스트림 제너레이터의 finally에서.
_run_lock = threading.Lock()


@app.route("/")
def index():
    """단일 페이지. 접속 초기값(비번 제외) + config 정의 파일 미리보기(N셸·셸별 I/O)를 폼에 내린다."""
    config_path = "./config.yaml"
    conn = _connection_defaults(config_path)
    definition = _definition_preview(config_path)
    # 설정 영역은 정의 미리보기에 실패(config·정의 미비)했을 때만 펼쳐 보여준다(초기 준비 유도).
    settings_open = not definition.get("ok")
    return render_template(
        "index.html",
        default_config=config_path,
        conn=conn,
        definition=definition,
        settings_open=settings_open,
    )


# --- 연결 설정 -------------------------------------------------------------------


@app.route("/connection/test", methods=["POST"])
def connection_test():
    """접속(SELECT 1) + public 테이블 목록을 취득한다(읽기전용). 비번은 env에서만(모델 A)."""
    f = request.form
    result = connection.test_connection(
        host=f.get("host", ""),
        port=f.get("port", ""),
        dbname=f.get("dbname", ""),
        user=f.get("user", ""),
        password_env=f.get("password_env") or "POSTGRES_PASSWORD",
    )
    return jsonify(result)


@app.route("/connection/save", methods=["POST"])
def connection_save():
    """DB 접속·인코딩만 config.yaml에 원자적 저장(+.bak). 비밀번호는 저장하지 않는다(모델 A)."""
    f = request.form
    config_path = f.get("config") or "./config.yaml"
    try:
        path = connection.save_connection(
            config_path,
            host=f.get("host", ""),
            port=f.get("port", ""),
            dbname=f.get("dbname", ""),
            user=f.get("user", ""),
            password_env=f.get("password_env") or "POSTGRES_PASSWORD",
            encoding=f.get("encoding") or "Shift_JIS",
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify(ok=False, message=f"保存に失敗しました: {exc}"), 400
    return jsonify(
        ok=True,
        message=f"接続設定を保存しました: {path.name}（パスワードは保存しません — 環境変数を使用）",
    )


@app.route("/definition/preview")
def definition_preview():
    """현재 config가 가리키는 정의 파일을 다시 요약해 돌려준다(저장/변경 후 갱신용, 읽기전용)."""
    config_path = request.args.get("config") or "./config.yaml"
    return jsonify(_definition_preview(config_path))


# --- 검증 실행 (SSE) -------------------------------------------------------------


@app.route("/run")
def run():
    """검증 실행: config 정의 파일의 셸들을 실행하며 진행을 SSE로 스트리밍한다(출력 단위).

    쿼리: config(설정 경로), shells(범위/ID, 선택).
    """
    config_path = request.args.get("config") or "./config.yaml"
    shells = request.args.get("shells") or None

    def stream():
        if not _run_lock.acquire(blocking=False):
            yield _sse({"type": "error", "message": "他の実行が進行中です。"})
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
            _run_lock.release()  # 클라 끊김·예외에도 반드시 해제

    return Response(stream(), mimetype="text/event-stream")


@app.route("/report/<name>")
def report(name: str):
    """리포트 CSV 다운로드. secure_filename + report_dir 하위 제한으로 traversal 차단."""
    config = load_config(request.args.get("config") or "./config.yaml")
    base = config.report_dir.resolve()
    target = (base / secure_filename(name)).resolve()
    # 정규화 후에도 report_dir 하위인지 재확인(이중 가드).
    if base != target and base not in target.parents:
        abort(404)
    if not target.is_file():
        abort(404)
    return send_file(target, as_attachment=True)


# --- 헬퍼 -----------------------------------------------------------------------


def _definition_preview(config_path: str) -> dict:
    """config의 definition_file을 읽어 요약한다(읽기전용). config·정의 미비면 ok=False."""
    for p in (config_path, _EXAMPLE_CONFIG):
        try:
            cfg = load_config(p)
        except Exception:  # noqa: BLE001 — 없거나 잘못돼도 다음 후보/빈 요약으로
            continue
        return summarize_definition_path(cfg.definition_file)
    return {"ok": False, "count": 0, "shells": [], "message": "config.yaml が見つかりません。"}


def _connection_defaults(config_path: str) -> dict:
    """폼 초기값으로 쓸 접속 정보(비번 제외)를 현 config.yaml→example 순으로 best-effort 로드."""
    for p in (config_path, _EXAMPLE_CONFIG):
        try:
            cfg = load_config(p)
        except Exception:  # noqa: BLE001 — 없거나 잘못돼도 다음 후보/빈값으로
            continue
        db = cfg.database
        return {
            "host": db.host,
            "port": db.port,
            "dbname": db.dbname,
            "user": db.user,
            "password_env": db.password_env,
            "encoding": cfg.encoding,
        }
    return {"host": "", "port": "", "dbname": "", "user": "", "password_env": "POSTGRES_PASSWORD", "encoding": "Shift_JIS"}


def _sse(payload: dict) -> str:
    """dict를 SSE 데이터 프레임으로 직렬화한다(/run용, GET)."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def main() -> None:
    """개발용 로컬 서버 기동 + 브라우저 자동 오픈."""
    host = os.environ.get("GUI_HOST", "127.0.0.1")
    port = int(os.environ.get("GUI_PORT", "8000"))
    url = f"http://{host}:{port}/"
    # 서버가 뜬 직후 브라우저를 연다(리로더 자식 프로세스에선 열지 않음).
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    main()
