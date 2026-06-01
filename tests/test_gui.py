"""Phase 5 웹 UI 테스트 — 직렬화 + Flask 엔드포인트 + 업로드 검증 (DB·실서버 불요, 항상 실행).

run_full_comparison/load_config/prepare_job를 monkeypatch해 라우팅·SSE/NDJSON·traversal 차단·
업로드 준비만 검증한다.
"""

import io
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.core.models import (
    ComparisonResult,
    ComparisonStatus,
    DiffLine,
    ProgressEvent,
    ProgressKind,
    RunSummary,
)
from src.gui import web
from src.gui.serialize import event_to_dict, result_to_dict, summary_to_dict
from src.gui.upload import UploadError, prepare_job

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


def test_index_serves_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "현·신 비교" in body and "업로드 검증" in body


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
        raise RuntimeError("설정 파일을 찾을 수 없습니다")

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


# --- 업로드 검증: prepare_job (DB 불요, config.yaml.example을 베이스로) -----------


def test_prepare_job_builds_temp_config_and_definition():
    from src.config.definition import load_definitions

    config, tmpdir = prepare_job(
        _EXAMPLE_CONFIG,
        asis_input=b"tx_id,customer_id\nT1,C0001\n",
        asis_output=b"tx_id,customer_id,customer_name\nT1,C0001,A\n",
        input_type="database", output_type="file", encoding="Shift_JIS",
    )
    try:
        assert (config.asis_input_dir / "up1.csv").read_bytes().startswith(b"tx_id")
        assert (config.asis_output_dir / "up1.csv").is_file()
        defs = load_definitions(config.definition_file)
        assert len(defs) == 1 and defs[0].test_id == "up1"
        assert defs[0].input_table == "transaction_log" and defs[0].output_file == "up1.csv"
        assert Path(defs[0].shell_program).is_absolute() and Path(defs[0].shell_program).is_file()
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_prepare_job_db_output_uses_export():
    from src.config.definition import load_definitions

    config, tmpdir = prepare_job(
        _EXAMPLE_CONFIG, asis_input=b"a\n1\n", asis_output=b"a\n1\n",
        input_type="file", output_type="database", encoding="Shift_JIS",
    )
    try:
        d = load_definitions(config.definition_file)[0]
        assert d.output_table == "tobe_result" and d.export_csv == "up1.csv"
        assert d.shell_program.endswith("run_batch_file.py")
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_prepare_job_rejects_bad_type():
    with pytest.raises(UploadError):
        prepare_job(_EXAMPLE_CONFIG, asis_input=b"a", asis_output=b"a",
                    input_type="ftp", output_type="file", encoding="Shift_JIS")


# --- 업로드 검증: /verify/run 스트리밍 (run_full_comparison mock) ------------------


def test_verify_run_streams_then_summary(client, monkeypatch):
    def fake_run(config, on_progress=None, shell_ids=None):
        on_progress(ProgressEvent(ProgressKind.SHELL_START, "up1", 1, 1))
        on_progress(
            ProgressEvent(ProgressKind.SHELL_DONE, "up1", 1, 1,
                         result=ComparisonResult("up1", ComparisonStatus.NG,
                                                  diff_lines=[DiffLine(2, "x", "y")]))
        )
        return RunSummary(1, 0, 1, 0, 0, [], Path("out/reports/report_u.csv"))

    # 임시폴더 경로를 돌려준다(절대 cwd '.'를 쓰지 말 것 — verify_run cleanup이 rmtree함).
    monkeypatch.setattr(
        web, "prepare_job",
        lambda *a, **k: (SimpleNamespace(), Path(tempfile.mkdtemp(prefix="dc_test_"))),
    )
    monkeypatch.setattr(web, "run_full_comparison", fake_run)

    data = {
        "asis_input": (io.BytesIO(b"tx_id\nT1\n"), "in.csv"),
        "asis_output": (io.BytesIO(b"tx_id\nT1\n"), "out.csv"),
        "input_type": "database", "output_type": "file", "config": "./config.yaml",
    }
    resp = client.post("/verify/run", data=data, content_type="multipart/form-data")
    msgs = _ndjson_messages(resp.get_data())
    types = [m["type"] for m in msgs]
    assert "progress" in types and "summary" in types and types[-1] == "done"
    assert next(m for m in msgs if m["type"] == "summary")["ng_count"] == 1


def test_verify_run_requires_both_files(client, monkeypatch):
    # 임시폴더 경로를 돌려준다(절대 cwd '.'를 쓰지 말 것 — verify_run cleanup이 rmtree함).
    monkeypatch.setattr(
        web, "prepare_job",
        lambda *a, **k: (SimpleNamespace(), Path(tempfile.mkdtemp(prefix="dc_test_"))),
    )
    data = {"asis_input": (io.BytesIO(b"x"), "in.csv"),
            "input_type": "database", "output_type": "file"}
    msgs = _ndjson_messages(client.post("/verify/run", data=data,
                                        content_type="multipart/form-data").get_data())
    assert any(m["type"] == "error" and "올려주세요" in m["message"] for m in msgs)


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
