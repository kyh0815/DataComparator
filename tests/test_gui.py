"""웹 UI 테스트 — 직렬화 + Flask 엔드포인트 + 업로드(다건) + 연결설정 (DB·실서버 불요, 항상 실행).

run_full_comparison/load_config/prepare_jobs/connection을 monkeypatch해 라우팅·SSE/NDJSON·
traversal 차단·다건 짝짓기·연결설정 저장/테스트 배선만 검증한다(실 DB 접속 없음).
"""

import io
import json
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from src.config.definition import load_definitions
from src.core.models import (
    ComparisonResult,
    ComparisonStatus,
    DiffLine,
    ProgressEvent,
    ProgressKind,
    RunSummary,
)
from src.gui import connection as conn_mod
from src.gui import web
from src.gui.serialize import event_to_dict, result_to_dict, summary_to_dict
from src.gui.upload import PairingInfo, UploadError, prepare_jobs

_EXAMPLE_CONFIG = str(Path(__file__).resolve().parents[1] / "config.yaml.example")


# --- 직렬화 (src/gui 전용, models 불변) ------------------------------------------


def test_result_to_dict_flattens_diff_lines():
    r = ComparisonResult("007", ComparisonStatus.NG, diff_lines=[DiffLine(2, "a", "b")])
    d = result_to_dict(r)
    assert d["status"] == "NG"
    assert d["diff_lines"] == [{"line_number": 2, "asis_content": "a", "tobe_content": "b"}]


def test_event_to_dict_shell_done_nests_result():
    ev = ProgressEvent(
        ProgressKind.SHELL_DONE, "001", 1, 10, result=ComparisonResult("001", ComparisonStatus.OK)
    )
    d = event_to_dict(ev)
    assert d["kind"] == "shell_done" and d["result"]["status"] == "OK"


def test_event_to_dict_step_has_no_result():
    ev = ProgressEvent(ProgressKind.STEP, "001", 1, 10, step="load", step_status="OK")
    d = event_to_dict(ev)
    assert d["step"] == "load" and d["result"] is None


def test_summary_to_dict_exposes_report_name_only():
    s = RunSummary(10, 6, 3, 1, 0, [], Path("/x/out/reports/report_20250101_000000.csv"))
    d = summary_to_dict(s, 12.37)
    assert d["report_name"] == "report_20250101_000000.csv"
    assert d["elapsed_seconds"] == 12.4 and d["ng_count"] == 3


# --- Flask 엔드포인트 -------------------------------------------------------------


@pytest.fixture
def client():
    web.app.config.update(TESTING=True)
    return web.app.test_client()


def _sse_messages(raw: bytes) -> list[dict]:
    lines = raw.decode("utf-8").splitlines()
    return [json.loads(l[len("data: "):]) for l in lines if l.startswith("data: ")]


def _ndjson_messages(raw: bytes) -> list[dict]:
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


def test_index_serves_japanese_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "現新比較" in body and "アップロード検証" in body and "接続設定" in body


def test_run_streams_progress_then_summary(client, monkeypatch):
    def fake_run(config, on_progress=None, shell_ids=None):
        on_progress(ProgressEvent(ProgressKind.SHELL_START, "001", 1, 1))
        on_progress(
            ProgressEvent(ProgressKind.SHELL_DONE, "001", 1, 1,
                         result=ComparisonResult("001", ComparisonStatus.OK))
        )
        return RunSummary(1, 1, 0, 0, 0, [], Path("out/reports/report_x.csv"))

    monkeypatch.setattr(web, "load_config", lambda p: SimpleNamespace(report_dir=Path(".")))
    monkeypatch.setattr(web, "run_full_comparison", fake_run)

    msgs = _sse_messages(client.get("/run?config=./config.yaml").get_data())
    types = [m["type"] for m in msgs]
    assert "progress" in types and "summary" in types and types[-1] == "done"
    assert next(m for m in msgs if m["type"] == "summary")["report_name"] == "report_x.csv"


def test_run_reports_error_message(client, monkeypatch):
    def boom(p):
        raise RuntimeError("설정 파일을 찾을 수 없습니다")  # Core/config 메시지는 한국어 유지(D)

    monkeypatch.setattr(web, "load_config", boom)
    msgs = _sse_messages(client.get("/run?config=missing.yaml").get_data())
    assert any(m["type"] == "error" and "찾을 수 없습니다" in m["message"] for m in msgs)
    assert msgs[-1]["type"] == "done"


def test_report_download_ok(client, monkeypatch, tmp_path):
    (tmp_path / "report_ok.csv").write_text("shell_id,status\n001,OK\n", encoding="utf-8")
    monkeypatch.setattr(web, "load_config", lambda p: SimpleNamespace(report_dir=tmp_path))
    resp = client.get("/report/report_ok.csv")
    assert resp.status_code == 200 and b"001,OK" in resp.get_data()


def test_report_blocks_path_traversal(client, monkeypatch, tmp_path):
    (tmp_path.parent / "secret.csv").write_text("TOPSECRET", encoding="utf-8")
    monkeypatch.setattr(web, "load_config", lambda p: SimpleNamespace(report_dir=tmp_path))
    assert client.get("/report/..%2fsecret.csv").status_code == 404


# --- 연결 설정: save_connection (DB 불요) ----------------------------------------


def test_save_connection_atomic_with_backup(tmp_path):
    cfg = tmp_path / "config.yaml"
    # 1차 저장: 기존 파일 없음 → example 템플릿 사용, .bak 없음.
    conn_mod.save_connection(
        str(cfg), host="h1", port=5433, dbname="d", user="u", password_env="PE", encoding="Shift_JIS"
    )
    assert cfg.is_file()
    raw = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    assert raw["database"]["host"] == "h1" and raw["database"]["password_env"] == "PE"
    assert "password" not in raw["database"]  # 모델 A: 평문 비번 미기록
    assert "paths" in raw  # 템플릿의 다른 블록 보존
    assert not (tmp_path / "config.yaml.bak").exists()

    # 2차 저장: 기존 파일 있음 → .bak 백업 생성, 값 갱신.
    conn_mod.save_connection(
        str(cfg), host="h2", port=5433, dbname="d", user="u", password_env="PE", encoding="Shift_JIS"
    )
    assert (tmp_path / "config.yaml.bak").is_file()
    assert yaml.safe_load(cfg.read_text(encoding="utf-8"))["database"]["host"] == "h2"


def test_connection_test_endpoint_wires(client, monkeypatch):
    monkeypatch.setattr(
        web.connection, "test_connection",
        lambda **k: {"ok": True, "message": "OK", "checks": [{"name": "x", "ok": True}]},
    )
    r = client.post(
        "/connection/test",
        data={"host": "h", "port": "5433", "dbname": "d", "user": "u"},
    ).get_json()
    assert r["ok"] and r["checks"][0]["name"] == "x"


def test_connection_test_table_check_conditional(monkeypatch):
    """B: type이 file인 쪽은 테이블을 확인하지 않는다(파일 흐름 오탐 방지)."""
    class FakeCur:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, *a): self.q = a
        def fetchone(self): return (1,)
    class FakeConn:
        def cursor(self): return FakeCur()
        def close(self): pass

    monkeypatch.setattr(conn_mod.psycopg2, "connect", lambda **k: FakeConn())
    r = conn_mod.test_connection(
        host="h", port=5433, dbname="d", user="u",
        input_type="database", output_type="file",
        input_table="transaction_log", output_table="tobe_result",
    )
    names = [c["name"] for c in r["checks"]]
    assert any("入力テーブル" in n for n in names)
    assert not any("出力テーブル" in n for n in names)  # output=file이므로 확인 안 함


# --- 업로드 검증: prepare_jobs (DB 불요, config.yaml.example 베이스) ----------------


def test_prepare_jobs_pairs_by_stem_and_reports_unmatched():
    config, tmpdir, pairing = prepare_jobs(
        _EXAMPLE_CONFIG,
        inputs={"001": b"a\n1\n", "002": b"a\n2\n", "099": b"a\n9\n"},
        outputs={"001": b"a\n1\n", "002": b"a\n2\n", "777": b"a\n7\n"},
        input_type="database", output_type="file", encoding="Shift_JIS",
        input_table="transaction_log",
    )
    try:
        assert pairing.matched == ["001", "002"]
        assert pairing.unmatched_input == ["099"] and pairing.unmatched_output == ["777"]
        defs = load_definitions(config.definition_file)
        assert [d.test_id for d in defs] == ["001", "002"]
        assert defs[0].input_table == "transaction_log" and defs[0].output_file == "001.csv"
        assert Path(defs[0].shell_program).is_absolute() and Path(defs[0].shell_program).is_file()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_prepare_jobs_db_output_uses_export_table():
    config, tmpdir, _ = prepare_jobs(
        _EXAMPLE_CONFIG, inputs={"001": b"a\n1\n"}, outputs={"001": b"a\n1\n"},
        input_type="file", output_type="database", encoding="Shift_JIS", output_table="tobe_result",
    )
    try:
        d = load_definitions(config.definition_file)[0]
        assert d.output_table == "tobe_result" and d.export_csv == "001.csv"
        assert d.shell_program.endswith("run_batch_file.py")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_prepare_jobs_custom_batch_program():
    config, tmpdir, _ = prepare_jobs(
        _EXAMPLE_CONFIG, inputs={"001": b"a\n1\n"}, outputs={"001": b"a\n1\n"},
        input_type="file", output_type="file", encoding="Shift_JIS",
        batch_program="stub_batch/run_batch_file.py",
    )
    try:
        d = load_definitions(config.definition_file)[0]
        assert Path(d.shell_program).is_absolute() and d.shell_program.endswith("run_batch_file.py")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_prepare_jobs_requires_table_for_db():
    with pytest.raises(UploadError):
        prepare_jobs(
            _EXAMPLE_CONFIG, inputs={"1": b"a"}, outputs={"1": b"a"},
            input_type="database", output_type="file", encoding="Shift_JIS", input_table=None,
        )


def test_prepare_jobs_zero_match_errors():
    with pytest.raises(UploadError):
        prepare_jobs(
            _EXAMPLE_CONFIG, inputs={"a": b"x"}, outputs={"b": b"y"},
            input_type="file", output_type="file", encoding="Shift_JIS",
        )


def test_prepare_jobs_rejects_bad_type():
    with pytest.raises(UploadError):
        prepare_jobs(
            _EXAMPLE_CONFIG, inputs={"a": b"x"}, outputs={"a": b"y"},
            input_type="ftp", output_type="file", encoding="Shift_JIS",
        )


# --- 업로드 검증: /verify/run 다건 스트리밍 (prepare_jobs/run_full_comparison mock) --


def _fake_prepare(pairing):
    # 임시폴더 경로를 돌려준다(절대 cwd '.'를 쓰지 말 것 — verify_run cleanup이 rmtree함).
    return lambda *a, **k: (SimpleNamespace(), Path(tempfile.mkdtemp(prefix="dc_test_")), pairing)


def test_verify_run_streams_then_summary(client, monkeypatch):
    def fake_run(config, on_progress=None, shell_ids=None):
        on_progress(ProgressEvent(ProgressKind.SHELL_START, "001", 1, 1))
        on_progress(
            ProgressEvent(ProgressKind.SHELL_DONE, "001", 1, 1,
                         result=ComparisonResult("001", ComparisonStatus.NG,
                                                  diff_lines=[DiffLine(2, "x", "y")]))
        )
        return RunSummary(1, 0, 1, 0, 0, [], Path("out/reports/report_u.csv"))

    monkeypatch.setattr(web, "prepare_jobs", _fake_prepare(PairingInfo(["001"], [], [])))
    monkeypatch.setattr(web, "run_full_comparison", fake_run)

    data = {
        "asis_inputs": (io.BytesIO(b"a\n1\n"), "001.csv"),
        "asis_outputs": (io.BytesIO(b"a\n1\n"), "001.csv"),
        "input_type": "database", "output_type": "file", "config": "./config.yaml",
        "input_table": "transaction_log",
    }
    resp = client.post("/verify/run", data=data, content_type="multipart/form-data")
    msgs = _ndjson_messages(resp.get_data())
    types = [m["type"] for m in msgs]
    assert "progress" in types and "summary" in types and types[-1] == "done"
    assert next(m for m in msgs if m["type"] == "summary")["ng_count"] == 1


def test_verify_run_warns_on_unmatched(client, monkeypatch):
    monkeypatch.setattr(web, "prepare_jobs", _fake_prepare(PairingInfo(["001"], ["099"], ["777"])))
    monkeypatch.setattr(
        web, "run_full_comparison",
        lambda *a, **k: RunSummary(1, 1, 0, 0, 0, [], Path("out/reports/r.csv")),
    )
    data = {
        "asis_inputs": (io.BytesIO(b"a\n1\n"), "001.csv"),
        "asis_outputs": (io.BytesIO(b"a\n1\n"), "001.csv"),
        "input_type": "file", "output_type": "file",
    }
    msgs = _ndjson_messages(
        client.post("/verify/run", data=data, content_type="multipart/form-data").get_data()
    )
    assert any(m["type"] == "warning" and "099" in m["message"] and "777" in m["message"] for m in msgs)


def test_verify_run_requires_both_sides(client, monkeypatch):
    monkeypatch.setattr(web, "prepare_jobs", _fake_prepare(PairingInfo([], [], [])))
    data = {  # 정답 없이 입력만 → 에러
        "asis_inputs": (io.BytesIO(b"a\n1\n"), "001.csv"),
        "input_type": "database", "output_type": "file", "input_table": "t",
    }
    msgs = _ndjson_messages(
        client.post("/verify/run", data=data, content_type="multipart/form-data").get_data()
    )
    assert any(m["type"] == "error" and "アップロード" in m["message"] for m in msgs)


def test_verify_run_rejects_duplicate_stems(client, monkeypatch):
    from werkzeug.datastructures import MultiDict

    monkeypatch.setattr(web, "prepare_jobs", _fake_prepare(PairingInfo(["001"], [], [])))
    data = MultiDict([  # 같은 stem 입력 2건 → 모호성 거부(중복 키라 MultiDict 필요)
        ("asis_inputs", (io.BytesIO(b"a\n1\n"), "001.csv")),
        ("asis_inputs", (io.BytesIO(b"a\n2\n"), "001.csv")),
        ("asis_outputs", (io.BytesIO(b"a\n1\n"), "001.csv")),
        ("input_type", "file"), ("output_type", "file"),
    ])
    msgs = _ndjson_messages(
        client.post("/verify/run", data=data, content_type="multipart/form-data").get_data()
    )
    assert any(m["type"] == "error" and "重複" in m["message"] for m in msgs)


def test_upload_too_large_returns_413(client):
    saved = web.app.config["MAX_CONTENT_LENGTH"]
    web.app.config["MAX_CONTENT_LENGTH"] = 10
    try:
        data = {"asis_inputs": (io.BytesIO(b"x" * 5000), "001.csv")}
        resp = client.post("/verify/run", data=data, content_type="multipart/form-data")
        assert resp.status_code == 413 and resp.get_json()["ok"] is False
    finally:
        web.app.config["MAX_CONTENT_LENGTH"] = saved


# --- _cleanup_tmpdir 안전장치 (회귀 가드: 과거 cwd 통째 rmtree 버그) -----------------


def test_cleanup_tmpdir_deletes_real_tempdir():
    d = Path(tempfile.mkdtemp(prefix="dc_clean_"))
    (d / "f").write_text("x")
    web._cleanup_tmpdir(d)
    assert not d.exists()  # 시스템 임시 하위 → 정상 삭제


def test_cleanup_tmpdir_refuses_outside_tempdir(tmp_path, monkeypatch):
    """임시 디렉토리 *밖* 경로는 절대 삭제하지 않는다 — cwd('.') 통째 삭제 재발 차단."""
    fake_tmp = tmp_path / "fake_tmp"
    fake_tmp.mkdir()
    monkeypatch.setattr(web.tempfile, "gettempdir", lambda: str(fake_tmp))
    outside = tmp_path / "outside"  # fake_tmp 밖
    outside.mkdir()
    (outside / "keep").write_text("x")
    web._cleanup_tmpdir(outside)
    assert outside.exists()  # 보호됨(삭제 거부)
    web._cleanup_tmpdir(Path("."))  # cwd도 거부 — 예외/삭제 없이 통과해야 함
