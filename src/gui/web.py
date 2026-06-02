"""로컬 웹 UI (Flask) — Core를 재사용하는 GUI 인터페이스 (Phase 5 → Phase 6 격상, D-028).

브라우저에서 세 가지를 한다:
- "연결 설정": 비-비밀 접속정보로 DB 접속 테스트(읽기전용) + config.yaml 자동 저장(/connection/*).
- "업로드 검증": As-Is (입력, 정답) **여러 쌍**을 올려 풀체인(적재→배치→추출→비교→리포트) 실행
  (/verify/run, 다건). 짝짓기는 파일명 일치.
- "샘플 데모": test_definition.yaml의 10셸을 자동 실행(/run, SSE 실시간 진행).

Core는 무수정 — CLI와 동일하게 run_full_comparison(config, on_progress, shell_ids)만 호출한다.

설계 결정(D-028 + Phase 6):
- 비밀번호는 UI에 두지 않고 서버 env(password_env)에서만 읽는다(모델 A, D-019 §6 확장).
- 연결설정 저장은 DB 접속·인코딩·경로만(검증 정의값은 폼 전달) — models.Config 불변, Core 무수정(A).
- 업로드 다건: prepare_jobs가 N-셸 정의를 만들고 엔진이 순차 처리. 짝 안 맞는 파일은 명시 노출(C·④).
- 업로드 본문 상한 MAX_CONTENT_LENGTH + 413 친절 에러(F). 사용자向け 문구는 일본어(D).
- 진행 스트리밍/락 해제(try/finally)/traversal 차단/임시폴더 cleanup 가드는 Phase 5 그대로 유지.

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

from flask import Flask, Response, abort, jsonify, render_template, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from src.config.settings import load_config, parse_shell_selector
from src.core import run_full_comparison

from . import connection
from .serialize import event_to_dict, summary_to_dict
from .upload import (
    MAPPING_TEMPLATE_CSV,
    definition_from_mapping,
    prepare_jobs,
    prepare_jobs_from_definition,
    summarize_definition,
)

app = Flask(__name__)

# F: 업로드 본문 상한(다건/폴더). 초과 시 413 → 친절 에러로 안내.
_MAX_UPLOAD_MB = int(os.environ.get("GUI_MAX_UPLOAD_MB", "100"))
app.config["MAX_CONTENT_LENGTH"] = _MAX_UPLOAD_MB * 1024 * 1024

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLE_CONFIG = str(_REPO_ROOT / "config.yaml.example")

# 데모 편의: 검증정의 테이블칸이 비면 동봉 stub 스키마로 채운다(빈칸=기본값).
# 실납품은 화면에서 실제 테이블명을 입력하면 그 값이 우선한다(하드코딩 아님 — 폴백일 뿐).
_DEMO_INPUT_TABLE = "transaction_log"
_DEMO_OUTPUT_TABLE = "tobe_result"


def _resolve_tables(
    input_type: str, output_type: str, input_table: str | None, output_table: str | None
) -> tuple[str | None, str | None]:
    """DB 타입인데 테이블칸이 비면 데모 기본값으로 채운다(GUI 폴백, 단일 진실).

    파일 타입 쪽은 건드리지 않는다(테이블 불필요). 비-DB에서는 None 유지.
    """
    if input_type == "database" and not input_table:
        input_table = _DEMO_INPUT_TABLE
    if output_type == "database" and not output_table:
        output_table = _DEMO_OUTPUT_TABLE
    return input_table, output_table

# 동시 실행 1건 제한(데모용). 해제는 스트림 제너레이터의 finally에서(§③).
_run_lock = threading.Lock()


@app.route("/")
def index():
    """단일 페이지. 기본 config 경로 + 연결 초기값(비번 제외) + 검증정의 기본 테이블을 폼에 내린다."""
    conn = _connection_defaults("./config.yaml")
    # 검증정의 테이블은 미리 채워 보여준다(빈칸 placeholder보다 명확). 실납품은 실테이블명으로 수정.
    conn["input_table"] = _DEMO_INPUT_TABLE
    conn["output_table"] = _DEMO_OUTPUT_TABLE
    return render_template("index.html", default_config="./config.yaml", conn=conn)


@app.errorhandler(RequestEntityTooLarge)
def _too_large(_exc):
    """413: 업로드 본문이 상한을 넘었을 때 친절한 일본어 안내(F)."""
    return (
        jsonify(
            ok=False,
            message=f"アップロードサイズが上限（{_MAX_UPLOAD_MB}MB）を超えています。"
            "ファイル数を減らすか、分割してください。",
        ),
        413,
    )


# --- 연결 설정 -------------------------------------------------------------------


@app.route("/connection/test", methods=["POST"])
def connection_test():
    """접속(SELECT 1) + public 테이블 목록을 취득한다(읽기전용). 비번은 env에서만(모델 A).

    응답의 tables로 화면이 입력/출력 테이블 드롭다운을 채운다(목록에서 고르므로 존재가 자명).
    """
    f = request.form
    result = connection.test_connection(
        host=f.get("host", ""),
        port=f.get("port", ""),
        dbname=f.get("dbname", ""),
        user=f.get("user", ""),
        password_env=f.get("password_env") or "POSTGRES_PASSWORD",
    )
    return jsonify(result)


@app.route("/definition/parse", methods=["POST"])
def definition_parse():
    """업로드된 test_definition.yaml을 파싱만 해서 셸 요약을 돌려준다(미리보기, 읽기전용)."""
    f = request.files.get("definition")
    if not f or not f.filename:
        return jsonify(ok=False, count=0, shells=[], message="定義ファイルを選択してください。"), 400
    return jsonify(summarize_definition(f.read()))


@app.route("/definition/mapping-template")
def mapping_template():
    """고객 배포용 매핑표 빈 양식(CSV)을 내려준다. Excel 대비 BOM(utf-8-sig) 부착."""
    return Response(
        "﻿" + MAPPING_TEMPLATE_CSV,  # BOM: Excel(일/한)에서 깨짐 방지
        content_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=shell_mapping_template.csv"},
    )


@app.route("/definition/from-mapping", methods=["POST"])
def definition_from_mapping_route():
    """매핑표 CSV → test_definition.yaml 생성(읽기전용). {ok, yaml, count, shells, errors}."""
    f = request.files.get("mapping")
    if not f or not f.filename:
        return jsonify(ok=False, yaml="", count=0, shells=[],
                       errors=["マッピング表(CSV)を選択してください。"]), 400
    return jsonify(definition_from_mapping(f.read()))


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


# --- 데모 실행 (SSE) -------------------------------------------------------------


@app.route("/run")
def run():
    """데모 실행: 정의 파일의 셸들을 실행하며 진행을 SSE로 스트리밍한다.

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
            _run_lock.release()  # §③ 클라 끊김·예외에도 반드시 해제

    return Response(stream(), mimetype="text/event-stream")


# --- 업로드 검증 (다건, NDJSON) --------------------------------------------------


@app.route("/verify/run", methods=["POST"])
def verify_run():
    """업로드 N쌍(As-Is 입력들 + 정답들)으로 풀체인 검증을 실행하고 진행을 NDJSON으로 스트리밍한다.

    짝짓기는 파일명(stem) 일치. 짝 안 맞는 파일은 warning으로 명시 노출(silent drop 금지).
    멀티파트라 EventSource(GET) 대신 fetch+스트림을 쓰므로 SSE가 아닌 NDJSON 프레임을 보낸다.
    """
    input_type = request.form.get("input_type") or "database"
    output_type = request.form.get("output_type") or "file"
    encoding = request.form.get("encoding") or "Shift_JIS"
    base_config = request.form.get("config") or "./config.yaml"
    batch_program = request.form.get("batch_program") or None
    # 빈 테이블칸 → 데모 기본값(빈칸=기본). 실납품은 입력값 우선.
    input_table, output_table = _resolve_tables(
        input_type, output_type,
        request.form.get("input_table") or None,
        request.form.get("output_table") or None,
    )
    # 요청 컨텍스트가 살아 있을 때 파일을 읽어 둔다(제너레이터는 나중에 실행됨).
    inputs, dup_in = _collect_csv(request.files.getlist("asis_inputs"))
    outputs, dup_out = _collect_csv(request.files.getlist("asis_outputs"))
    # 정의 파일이 있으면 그것이 정본(셸별 타입·테이블·배치는 정의에서). 없으면 폼 3칸 사용.
    f_def = request.files.get("definition")
    def_bytes = f_def.read() if f_def and f_def.filename else b""

    def stream():
        if not _run_lock.acquire(blocking=False):
            yield _ndjson({"type": "error", "message": "他の実行が進行中です。"})
            yield _ndjson({"type": "done"})
            return
        tmpdir = None
        try:
            if dup_in or dup_out:
                yield _ndjson({
                    "type": "error",
                    "message": f"同名のファイルが重複しています: 入力{dup_in} / 正解{dup_out}",
                })
                yield _ndjson({"type": "done"})
                return
            if not inputs or not outputs:
                yield _ndjson({
                    "type": "error",
                    "message": "As-Is入力CSVと正解CSVを1組以上アップロードしてください。",
                })
                yield _ndjson({"type": "done"})
                return
            try:
                if def_bytes:
                    # 정의 파일 주도: yml이 정본(타입·테이블·배치는 정의에서, 폼 3칸 무시).
                    config, tmpdir, dinfo = prepare_jobs_from_definition(
                        base_config,
                        definition_bytes=def_bytes,
                        inputs=inputs,
                        outputs=outputs,
                        encoding=encoding,
                    )
                    excluded, unmatched_msg = dinfo.excluded, None
                else:
                    config, tmpdir, pairing = prepare_jobs(
                        base_config,
                        inputs=inputs,
                        outputs=outputs,
                        input_type=input_type,
                        output_type=output_type,
                        encoding=encoding,
                        input_table=input_table,
                        output_table=output_table,
                        batch_program=batch_program,
                    )
                    excluded = None
                    unmatched_msg = (
                        "ペアにならず除外: 入力="
                        f"{pairing.unmatched_input} / 正解={pairing.unmatched_output}"
                        "（入力と正解は同じファイル名で対応します）"
                    ) if (pairing.unmatched_input or pairing.unmatched_output) else None
            except Exception as exc:  # noqa: BLE001
                yield _ndjson({"type": "error", "message": f"準備に失敗しました: {exc}"})
                yield _ndjson({"type": "done"})
                return

            # C·④: 누락/미매칭은 조용히 버리지 않고 명시 노출(실행은 유효분만 진행).
            if def_bytes and excluded:
                shells = " / ".join(f"{e['test_id']}({', '.join(e['missing'])})" for e in excluded)
                yield _ndjson({"type": "warning", "message": f"ファイル不足で除外したシェル: {shells}"})
            elif unmatched_msg:
                yield _ndjson({"type": "warning", "message": unmatched_msg})

            events: queue.Queue = queue.Queue()

            def worker():
                start = time.perf_counter()
                try:
                    summary = run_full_comparison(
                        config,
                        on_progress=lambda e: events.put({"type": "progress", **event_to_dict(e)}),
                        shell_ids=None,  # 생성된 모든 셸을 정의 파일 순서대로 처리
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


# --- 헬퍼 -----------------------------------------------------------------------


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


def _collect_csv(files) -> tuple[dict, list]:
    """업로드 파일 목록을 {stem: 바이트}로. .csv만 수용, basename만 사용(폴더 업로드 경로 방어).

    같은 stem이 둘 이상이면 중복 목록에 담아 호출자가 거부하게 한다(짝짓기 모호성 차단).
    """
    out: dict[str, bytes] = {}
    dups: list[str] = []
    for f in files:
        if not f or not f.filename:
            continue
        name = Path(f.filename).name  # 폴더 업로드의 상대경로 → basename(traversal 방어)
        if not name.lower().endswith(".csv"):
            continue  # 폴더에 섞인 비-CSV는 무시
        stem = name[:-4]
        if not stem or stem in (".", ".."):
            continue
        data = f.read()
        if not data:
            continue
        if stem in out:
            if stem not in dups:
                dups.append(stem)
            continue
        out[stem] = data
    return out, dups


def _sse(payload: dict) -> str:
    """dict를 SSE 데이터 프레임으로 직렬화한다(데모 실행 /run용, GET)."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _ndjson(payload: dict) -> str:
    """dict를 NDJSON 한 줄로 직렬화한다(업로드 /verify/run용, POST 스트림)."""
    return json.dumps(payload, ensure_ascii=False) + "\n"


def _cleanup_tmpdir(tmpdir) -> None:
    """업로드 임시 작업폴더를 삭제한다. **시스템 임시 디렉토리 하위만** 삭제하는 안전장치.

    prepare_jobs는 tempfile.mkdtemp() 경로를 돌려주므로 정상 동작하며, 혹시라도 잘못된 경로
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
