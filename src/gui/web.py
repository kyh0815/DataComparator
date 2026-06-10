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

import yaml

from flask import Flask, Response, abort, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from src.config.definition import load_definitions
from src.config.settings import load_config, parse_shell_selector
from src.core import run_full_comparison, store
from src.core.evidence import generate_evidence
from src.core.preflight import preflight
from tools.mapping_to_definition import mapping_to_definition, read_mapping_bytes

from . import connection
from .run_manager import run_manager
from .serialize import event_to_dict, summary_to_dict
from .upload import summarize_definition_path

app = Flask(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLE_CONFIG = str(_REPO_ROOT / "config.yaml.example")
_DEFAULT_CONFIG = "./config.yaml"


def _active_config() -> str:
    """현재 활성 config 경로를 고르는 단일 진입점(GET args·POST form 모두 수용).

    config 선택이 여기 한 곳에 모인다 — 멀티프로젝트(여러 config 스캔·전환)로 확장할 땐
    이 함수만 바꾼다(B 확장 지점). 지금은 단일 config만 본다.
    """
    return request.values.get("config") or _DEFAULT_CONFIG

# 동시 실행 1건 제한·진행 상태는 run_manager가 단일 소스로 보유(구 /run·신 /run/start 공유).


@app.route("/")
def index():
    """단일 페이지. 접속 초기값(비번 제외) + config 정의 파일 미리보기(N셸·셸별 I/O)를 폼에 내린다."""
    config_path = _DEFAULT_CONFIG
    conn = _connection_defaults(config_path)
    definition = _definition_preview(config_path)
    # 설정 영역은 정의 미리보기에 실패(config·정의 미비)했을 때만 펼쳐 보여준다(초기 준비 유도).
    settings_open = not definition.get("ok")
    return render_template(
        "index.html",
        default_config=config_path,
        conn=conn,
        paths=_paths_defaults(config_path),
        groups=_groups_defaults(config_path),
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
    config_path = _active_config()
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


@app.route("/paths")
def paths_get():
    """선택 config의 paths(디렉토리·정의파일)를 폼 갱신용으로 돌려준다(읽기전용)."""
    return jsonify(_paths_defaults(_active_config()))


@app.route("/paths/save", methods=["POST"])
def paths_save():
    """paths(디렉토리·정의파일 경로)만 config.yaml에 원자적 저장(+.bak). 폴더 존재 검증은 事前点検."""
    f = request.form
    config_path = _active_config()
    try:
        path = connection.save_paths(
            config_path,
            asis_input_dir=f.get("asis_input_dir", ""),
            asis_output_dir=f.get("asis_output_dir", ""),
            tobe_input_dir=f.get("tobe_input_dir", ""),
            tobe_output_dir=f.get("tobe_output_dir", ""),
            report_dir=f.get("report_dir", ""),
            definition_file=f.get("definition_file", ""),
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify(ok=False, message=f"保存に失敗しました: {exc}"), 400
    return jsonify(ok=True, message=f"ディレクトリ設定を保存しました: {path.name}")


@app.route("/groups")
def groups_get():
    """선택 config의 batch.groups(업무별 디렉토리)를 폼 갱신용 리스트로 돌려준다(읽기전용, D-045)."""
    return jsonify(_groups_defaults(_active_config()))


@app.route("/groups/save", methods=["POST"])
def groups_save():
    """batch.groups(업무별 디렉토리)만 config.yaml에 원자적 저장(+.bak, D-045). 폴더 존재 검증은 事前点検."""
    f = request.form
    config_path = _active_config()
    try:
        groups = json.loads(f.get("groups") or "[]")
    except (ValueError, TypeError):
        return jsonify(ok=False, message="業務リストの形式が不正です。"), 400
    try:
        path = connection.save_groups(config_path, groups)
    except Exception as exc:  # noqa: BLE001
        return jsonify(ok=False, message=f"保存に失敗しました: {exc}"), 400
    return jsonify(ok=True, message=f"業務別ディレクトリを保存しました: {path.name}")


@app.route("/definition/preview")
def definition_preview():
    """현재 config가 가리키는 정의 파일을 다시 요약해 돌려준다(저장/변경 후 갱신용, 읽기전용)."""
    config_path = _active_config()
    return jsonify(_definition_preview(config_path))


# --- 검증 실행 (SSE) -------------------------------------------------------------


@app.route("/run")
def run():
    """검증 실행: config 정의 파일의 셸들을 실행하며 진행을 SSE로 스트리밍한다(출력 단위).

    쿼리: config(설정 경로), shells(범위/ID, 선택).
    """
    config_path = _active_config()
    shells = request.args.get("shells") or None

    def stream():
        # ★락은 run_manager가 소유하고 워커 finally에서만 해제한다(클라 끊김에 종속되지 않음 — bug1 수정).
        if not run_manager.try_begin(config_path, shells):
            yield _sse({"type": "error", "message": "他の実行が進行中です。"})
            yield _sse({"type": "done"})
            return
        events: queue.Queue = queue.Queue()

        def worker():
            start = time.perf_counter()
            try:
                config = load_config(config_path)
                shell_ids = parse_shell_selector(shells) if shells else None

                def on_prog(e):
                    run_manager.apply_progress(e)  # 폴링(/run/status)용 상태 갱신
                    events.put({"type": "progress", **event_to_dict(e)})

                summary = run_full_comparison(config, on_progress=on_prog, shell_ids=shell_ids)
                elapsed = time.perf_counter() - start
                run_manager.finish_done(summary, elapsed)
                events.put({"type": "summary", **summary_to_dict(summary, elapsed)})
            except Exception as exc:  # noqa: BLE001 — 어떤 실패든 브라우저에 메시지로 + 상태 failed
                run_manager.finish_failed(str(exc))
                events.put({"type": "error", "message": str(exc)})
            finally:
                run_manager.end()  # 먼저 락 해제 → 그 다음 done(소비자가 done을 본 시점엔 락 free 보장)
                events.put({"type": "done"})

        threading.Thread(target=worker, daemon=True).start()
        while True:
            msg = events.get()
            yield _sse(msg)
            if msg["type"] == "done":
                break

    return Response(stream(), mimetype="text/event-stream")


@app.route("/run/start", methods=["POST"])
def run_start():
    """검증을 백그라운드로 시작한다(즉시 반환). 진행/결과는 /run/status 폴링으로 본다.

    이미 실행 중이면 409. resume=1이면 코어 resume(이어하기 — 미실행+ERROR만)로 통과(코어 파라미터).
    워커는 데몬 스레드라 브라우저가 닫혀도 끝까지 돈다(상태는 서버 RunState/체크포인트에 보존).
    """
    config_path = _active_config()
    shells = request.values.get("shells") or None
    resume = request.values.get("resume") in ("1", "true", "yes", "on")
    if not run_manager.try_begin(config_path, shells, resume=resume):
        return jsonify({"ok": False, "message": "他の実行が進行中です。"}), 409

    def worker():
        start = time.perf_counter()
        try:
            config = load_config(config_path)
            shell_ids = parse_shell_selector(shells) if shells else None
            summary = run_full_comparison(
                config, on_progress=run_manager.apply_progress, shell_ids=shell_ids, resume=resume,
            )
            run_manager.finish_done(summary, time.perf_counter() - start)
        except Exception as exc:  # noqa: BLE001 — 워커 크래시도 락 해제 + failed 상태(조건2)
            run_manager.finish_failed(str(exc))
        finally:
            run_manager.end()  # 예외 포함 반드시 락 해제

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"ok": True, "run_id": run_manager.snapshot()["run_id"]})


@app.route("/run/status")
def run_status():
    """현재(또는 직전) 실행 상태 스냅샷(폴링용). 연결과 무관하게 서버 RunState를 반영 → 재접속 복원."""
    return jsonify(run_manager.snapshot())


@app.route("/run/resumable")
def run_resumable():
    """중단된 검증(미완 checkpoint)이 있으면 알려준다 — RESUMABLE 화면용(코어 store 재사용, 무수정).

    서버 재시작 등으로 RunState가 비어도 디스크 checkpoint로 "9,000/10,000 完了" 같은 중단을 감지한다.
    미비·오류면 그냥 재개 불가(resumable=False).
    """
    try:
        config = load_config(_active_config())
        cp = store.checkpoint_path(config.report_dir)
        if not store.has_checkpoint(cp):
            return jsonify({"resumable": False})
        all_ids = [d.test_id for d in load_definitions(config.definition_file)]
        total = len(all_ids)
        done = len(store.load_records(cp))
        remaining = len(store.shells_to_resume(cp, all_ids))
        return jsonify({
            "resumable": done > 0 and remaining > 0,
            "total": total, "done": done, "remaining": remaining,
        })
    except Exception:  # noqa: BLE001 — 설정/정의/checkpoint 미비면 재개 불가로 처리
        return jsonify({"resumable": False})


@app.route("/preflight")
def preflight_check():
    """C3 프리플라이트(dry-run) — 실행 없이 점검만. 문제를 모두 모아 JSON으로 돌려준다(C3 재사용).

    쿼리: config(설정 경로). ok=false면 화면이 실행을 막는다(에러가 있으면).
    """
    config_path = _active_config()
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
    config_path = _active_config()
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
    return render_template("define.html", default_config=_DEFAULT_CONFIG)


@app.route("/definition/from-csv", methods=["POST"])
def definition_from_csv():
    """업로드된 매핑표(Long CSV)를 test_definition.yaml로 변환한다(읽기전용 — 저장은 별도).

    반환 {ok, yaml, count, shells, errors}. 한 행이라도 오류면 ok=False(부분 생성 안 함).
    """
    file = request.files.get("csv")
    if file is None or not file.filename:
        return jsonify({"ok": False, "errors": ["マッピング表(CSV/xlsx)を選択してください。"]})
    return jsonify(mapping_to_definition(read_mapping_bytes(file.read())))  # CSV·xlsx 모두 수용


@app.route("/definition/sample-csv")
def definition_sample_csv():
    """정의 파일 CSV 샘플(정본 풀스키마 Long 예시)을 다운로드로 돌려준다.

    정본 1벌(samples/complete/complete_sample.csv)만 둔다 — GUI는 여기서 제공(2벌 손유지 금지, V3 C2).
    """
    sample = _REPO_ROOT / "samples" / "complete" / "complete_sample.csv"
    if not sample.is_file():
        abort(404)
    return send_file(sample, as_attachment=True, download_name="sample_definition.csv")


@app.route("/definition/save", methods=["POST"])
def definition_save():
    """생성된 정의 yaml을 config의 definition_file 경로에 저장한다(다음 단계: 그대로 検証実行)."""
    yaml_text = request.form.get("yaml", "")
    # 브라우저 폼 왕복에서 줄바꿈이 \r\n으로 정규화돼 들어온다(HTTP 폼 규약) → LF로 되돌려 CRLF 파일 산출 방지.
    yaml_text = yaml_text.replace("\r\n", "\n").replace("\r", "\n")
    config_path = _active_config()
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
    config = load_config(_active_config())
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


_PATHS_KEYS = ("asis_input_dir", "asis_output_dir", "tobe_input_dir", "tobe_output_dir", "report_dir", "definition_file")


def _paths_defaults(config_path: str) -> dict:
    """폼 초기값용 paths(원본 문자열·상대경로 보존). 현 config→example 순 best-effort(raw yaml)."""
    for p in (config_path, str(_EXAMPLE_CONFIG)):
        try:
            raw = yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001 — 없거나 깨졌으면 다음 후보
            continue
        pa = raw.get("paths") if isinstance(raw, dict) else None
        if isinstance(pa, dict) and pa:
            return {k: str(pa.get(k, "") or "") for k in _PATHS_KEYS}
    return {k: "" for k in _PATHS_KEYS}


def _groups_defaults(config_path: str) -> list:
    """폼용 batch.groups(업무별 디렉토리) 리스트. 현 config→example 순 best-effort(raw yaml). D-045."""
    dirs = ("asis_input_dir", "asis_output_dir", "tobe_input_dir", "tobe_output_dir")
    for p in (config_path, str(_EXAMPLE_CONFIG)):
        try:
            raw = yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            continue
        batch = raw.get("batch") if isinstance(raw, dict) else None
        groups = batch.get("groups") if isinstance(batch, dict) else None
        if isinstance(groups, dict) and groups:
            out = []
            for name, g in groups.items():
                if not isinstance(g, dict):
                    continue
                row = {"name": str(name), "base_dir": str(g.get("base_dir", "") or "")}
                row.update({k: str(g.get(k, "") or "") for k in dirs})
                out.append(row)
            return out
    return []


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
