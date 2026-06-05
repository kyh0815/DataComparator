"""로컬 웹 UI (Flask) — Core를 재사용하는 GUI 인터페이스 (Phase 7, T7-3 경량화 / D-034).

운영 타깃 화면은 **버튼 1개 → 자동 실행(Shell 1~1000) → 실시간 모니터링 → 결과**다.
데이터·정답·정의 파일은 `config.yaml`이 가리키는 디렉토리에 이미 있고(설치 시 준비),
화면은 그 정의를 그대로 실행만 한다 — CLI와 동일하게 `run_full_comparison(config, on_progress)`.

화면(페이지 2개):
- "/" 検証実行 — "設定/接続"(접이식, DB 테스트·config 저장) + 정의 파일 실행(/run SSE 모니터링).
- "/define" 定義作成 — 매핑표(CSV)→정의 yaml 생성·config 저장 + 샘플 CSV 다운로드(D-037, 설치 준비).
  운영(실행)과 준비(정의 만들기)를 **별도 화면**으로 분리 — 실행 화면은 버튼+모니터+결과로 유지.

설계 결정:
- 비밀번호는 UI에 두지 않고 서버 env(password_env)에서만 읽는다(모델 A, D-019).
- 검증 정의의 정본은 **정의 파일**(DEFINITION_SPEC) — 화면에 입력 타입·테이블 선택칸을 두지 않는다.
  실행 전 셸 수·셸별 I/O는 정의 파일을 읽어 미리보기로만 보여준다(읽기전용).
- 동시 실행 1건 락(try/finally), traversal 차단은 유지. Core 무수정.

T7-3에서 걷어낸 것(불필요·간결, D-028~031 supersede): 브라우저 업로드-CSV "검증", 화면
테이블선택 3칸, 탭/위저드. 디렉토리 기반 단일 실행으로 일원화. 단 **매핑표→정의 생성은
실행과 분리된 별도 화면(/define)으로 복원**(D-037) — CLI만으론 부족하다는 사용자 요구.

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

from src.config.definition import load_definitions
from src.config.settings import load_config, parse_shell_selector
from src.core import run_full_comparison, store
from src.core.evidence import generate_evidence
from src.core.preflight import preflight
from tools.mapping_to_definition import mapping_to_definition

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


@app.route("/preflight")
def preflight_check():
    """C3 프리플라이트(dry-run) — 실행 없이 점검만. 문제를 모두 모아 JSON으로 돌려준다(C3 재사용).

    쿼리: config(설정 경로). ok=false면 화면이 실행을 막는다(에러가 있으면).
    """
    config_path = request.args.get("config") or "./config.yaml"
    try:
        report = preflight(load_config(config_path))
    except Exception as exc:  # noqa: BLE001 — 설정 로드 실패도 화면 메시지로
        return jsonify({"ok": False, "errors": [{"coordinate": "config", "message": str(exc)}], "warnings": []})
    to_dict = lambda i: {"coordinate": i.coordinate, "message": i.message}  # noqa: E731
    return jsonify({
        "ok": report.ok,
        "errors": [to_dict(i) for i in report.errors],
        "warnings": [to_dict(i) for i in report.warnings],
    })


@app.route("/evidence")
def evidence():
    """C4 試験成績書(Excel) 다운로드 — 체크포인트 머지 최신 상태 + 정의(계획) 기준."""
    config_path = request.args.get("config") or "./config.yaml"
    try:
        config = load_config(config_path)
        if config.definition_file is None:
            abort(400, "definition_file이 설정되지 않았습니다.")
        definitions = load_definitions(config.definition_file)
        records = store.latest_records(store.checkpoint_path(config.report_dir))
        out = config.report_dir / f"試験結果一覧_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
        path = generate_evidence(definitions, records, out)
    except Exception as exc:  # noqa: BLE001
        abort(400, str(exc))
    return send_file(path, as_attachment=True, download_name=path.name)


# --- 定義作成 (CSV/체크리스트 → test_definition.yaml) ----------------------------


@app.route("/define")
def define():
    """별도 화면: 매핑표(CSV) → 정의 yaml 생성 + 체크리스트 → 기입 템플릿(설치 준비)."""
    return render_template("define.html", default_config="./config.yaml")


@app.route("/definition/from-csv", methods=["POST"])
def definition_from_csv():
    """업로드된 매핑표(Long CSV)를 test_definition.yaml로 변환한다(읽기전용 — 저장은 별도).

    반환 {ok, yaml, count, shells, errors}. 한 행이라도 오류면 ok=False(부분 생성 안 함).
    """
    file = request.files.get("csv")
    if file is None or not file.filename:
        return jsonify({"ok": False, "errors": ["CSVファイルを選択してください。"]})
    return jsonify(mapping_to_definition(_decode(file.read())))


@app.route("/definition/sample-csv")
def definition_sample_csv():
    """정의 파일 CSV 샘플(정본 풀스키마 Long 예시)을 다운로드로 돌려준다.

    정본 1벌(samples/sample_definition_v2.csv)만 둔다 — GUI는 여기서 제공(2벌 손유지 금지, V3 C2).
    """
    sample = _REPO_ROOT / "samples" / "sample_definition_v2.csv"
    if not sample.is_file():
        abort(404)
    return send_file(sample, as_attachment=True, download_name="sample_definition.csv")


@app.route("/definition/save", methods=["POST"])
def definition_save():
    """생성된 정의 yaml을 config의 definition_file 경로에 저장한다(다음 단계: 그대로 検証実行)."""
    yaml_text = request.form.get("yaml", "")
    config_path = request.form.get("config") or "./config.yaml"
    if not yaml_text.strip():
        return jsonify({"ok": False, "message": "保存する定義がありません（先に生成してください）。"})
    try:
        cfg = load_config(config_path)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "message": f"config.yaml を読めません: {exc}"})
    target = cfg.definition_file
    if target is None:
        return jsonify({"ok": False, "message": "config.yaml に paths.definition_file がありません。"})
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml_text, encoding="utf-8")
    return jsonify({"ok": True, "message": f"定義を保存しました: {target}", "path": str(target)})


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


def _decode(data: bytes) -> str:
    """업로드 CSV 디코드: Excel 저장 대비 utf-8-sig 우선, 실패 시 cp932(일본어 Excel)."""
    for enc in ("utf-8-sig", "cp932"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


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
