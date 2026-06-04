"""T2-4 Runner(run_batch) 테스트.

- argv 구성·비밀번호 비노출·종료코드/timeout→RunnerError → mock으로 항상 실행(DB 0).
- 실제 stub 실행/ export / 골든-To-Be byte 동일성 → RUN_DB_TESTS=1 일 때만.
"""

import os
import subprocess
from pathlib import Path

import pytest

from src.core import runner
from src.core.models import (
    BatchConfig,
    Config,
    DatabaseConfig,
    OutputConfig,
    ShellDefinition,
)

_ROOT = Path(__file__).resolve().parents[1]


def _config(tmp_path, password="secret-pw"):
    return Config(
        encoding="Shift_JIS",
        asis_input_dir=tmp_path / "asis/input",
        asis_output_dir=tmp_path / "asis/output",
        tobe_output_dir=tmp_path / "tobe_output",
        report_dir=tmp_path / "reports",
        database=DatabaseConfig(
            # db_conn fixture와 동일하게 env에서 읽어 포트 비종속(병렬 DB 가동 대응).
            host=os.environ.get("PGHOST", "localhost"),
            port=int(os.environ.get("PGPORT", "5432")),
            dbname=os.environ.get("PGDATABASE", "compare_proto"),
            user=os.environ.get("PGUSER", "postgres"),
            password=password,
        ),
        batch=BatchConfig(),
        shell_ids=["001"],
        output=OutputConfig(),
        tobe_input_dir=tmp_path / "tobe_input",
        definition_file=tmp_path / "test_definition.yaml",
    )


def _def(test_id, input_type, output_type, **kw):
    base = dict(
        test_id=test_id,
        test_name=f"t{test_id}",
        input_type=input_type,
        input_csv=f"{test_id}.csv",
        output_type=output_type,
        expected_output_csv=f"{test_id}.csv",
        shell_program=(
            "stub_batch/run_batch_db.py" if input_type == "database"
            else "stub_batch/run_batch_file.py"
        ),
        input_table="transaction_log" if input_type == "database" else None,
        output_table="tobe_result" if output_type == "database" else None,
        output_file=f"{test_id}.csv" if output_type == "file" else None,
        export_csv=f"{test_id}.csv" if output_type == "database" else None,
    )
    base.update(kw)
    return ShellDefinition(**base)


class _Proc:
    def __init__(self, returncode=0, stderr=""):
        self.returncode = returncode
        self.stderr = stderr


# --- argv 구성 (항상 실행) -------------------------------------------------------


def test_argv_db_input_db_output(tmp_path):
    """DB입력/DB출력: --input-table 있음, --output-table 있음, --output-path 없음(dead-arg 제거)."""
    argv, env, timeout = runner._build_command(
        _def("001", "database", "database"), _config(tmp_path), clean=False
    )
    assert argv[0].endswith("stub_batch/run_batch_db.py")
    assert argv[1:3] == ["--shell-id", "001"]
    assert "--input-table" in argv and "transaction_log" in argv
    assert "--output-table" in argv
    assert "--output-path" not in argv  # DB출력엔 출력경로를 stub에 넘기지 않음


def test_argv_file_input_file_output(tmp_path):
    """파일입력/파일출력: --input-file(복사 위치), --output-path 있음, --output-table 없음."""
    argv, env, timeout = runner._build_command(
        _def("006", "file", "file"), _config(tmp_path), clean=False
    )
    assert argv[0].endswith("stub_batch/run_batch_file.py")
    assert "--input-file" in argv
    assert str(tmp_path / "tobe_input" / "006.csv") in argv
    assert "--output-path" in argv
    assert "--output-table" not in argv


def test_password_not_in_argv_but_in_env(tmp_path):
    """비밀번호는 argv에 절대 없고 env(POSTGRES_PASSWORD)로만 전달된다(ps 노출 방지)."""
    cfg = _config(tmp_path, password="topsecret")
    argv, env, _t = runner._build_command(_def("001", "database", "database"), cfg, False)
    assert "topsecret" not in " ".join(argv)
    assert env["POSTGRES_PASSWORD"] == "topsecret"


def test_clean_flag_appended(tmp_path):
    argv, *_ = runner._build_command(_def("001", "database", "database"), _config(tmp_path), clean=True)
    assert "--clean" in argv


def test_timeout_uses_definition(tmp_path):
    _argv, _env, timeout = runner._build_command(
        _def("001", "database", "database", timeout_seconds=123), _config(tmp_path), False
    )
    assert timeout == 123


# --- 실행 흐름 (mock subprocess, 항상 실행) ---------------------------------------


def test_nonzero_exit_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: _Proc(returncode=1, stderr="boom"))
    with pytest.raises(runner.RunnerError, match="終了コード 1"):
        runner.run_batch(_def("006", "file", "file"), _config(tmp_path))


def test_timeout_raises(tmp_path, monkeypatch):
    def _boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd="stub", timeout=1)

    monkeypatch.setattr(runner.subprocess, "run", _boom)
    with pytest.raises(runner.RunnerError, match="タイムアウト"):
        runner.run_batch(_def("006", "file", "file"), _config(tmp_path))


def test_file_output_returns_path_without_export(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: _Proc(returncode=0))

    def _no_export(*a, **k):
        raise AssertionError("파일 출력에서는 export를 호출하면 안 된다")

    monkeypatch.setattr(runner, "export_table_to_csv", _no_export)
    resolved = runner.run_batch(_def("006", "file", "file"), _config(tmp_path))
    assert resolved[0][1] == tmp_path / "tobe_output" / "006.csv"


def test_db_output_calls_exporter(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: _Proc(returncode=0))
    calls = []
    monkeypatch.setattr(
        runner, "export_table_to_csv",
        lambda conn, table, out, encoding: calls.append((table, out, encoding)) or out,
    )
    runner.run_batch(_def("001", "database", "database"), _config(tmp_path), conn=object())
    assert calls == [("tobe_result", tmp_path / "tobe_output" / "001.csv", "Shift_JIS")]


def test_db_output_without_conn_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: _Proc(returncode=0))
    with pytest.raises(runner.RunnerError, match="conn"):
        runner.run_batch(_def("001", "database", "database"), _config(tmp_path), conn=None)


# --- DB 통합 (RUN_DB_TESTS=1 일 때만) -------------------------------------------

_DB_ENABLED = os.environ.get("RUN_DB_TESTS") == "1"
_db_only = pytest.mark.skipif(not _DB_ENABLED, reason="DB 통합 테스트는 RUN_DB_TESTS=1 일 때만 실행")


def _real_config(tmp_path):
    cfg = _config(tmp_path, password=os.environ.get("POSTGRES_PASSWORD"))
    cfg.definition_file = _ROOT / "test_definition.yaml"  # base=_ROOT → 실제 stub 경로 resolve
    return cfg


@pytest.fixture
def db_conn():
    import psycopg2

    conn = psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=int(os.environ.get("PGPORT", "5432")),
        dbname=os.environ.get("PGDATABASE", "compare_proto"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("POSTGRES_PASSWORD"),
    )
    yield conn
    conn.close()


@_db_only
def test_ok_db_output_golden_equals_tobe(db_conn, tmp_path):
    """🔴 false-NG 가드: OK DB출력 셸의 골든(clean) vs To-Be(non-clean)가 byte 동일 → comparator OK."""
    from src.core.comparator import compare_files
    from src.core.models import ComparisonStatus

    cfg = _real_config(tmp_path)
    d = _def("001", "database", "database")  # 실제 transaction_log(시드 50건) 사용

    golden = runner.run_batch(d, cfg, db_conn, clean=True)[0][1]
    gbytes = golden.read_bytes()
    db_conn.rollback()  # export 읽기 트랜잭션 해제(오케스트레이터의 셸 단위 경계 모사, SPEC 3-1)
    tobe = runner.run_batch(d, cfg, db_conn, clean=False)[0][1]
    tbytes = tobe.read_bytes()
    db_conn.rollback()

    assert gbytes == tbytes  # OK 셸 → NG no-op → export 경로가 byte 동일
    gold_file = tmp_path / "golden_001.csv"
    gold_file.write_bytes(gbytes)
    assert compare_files(gold_file, tobe).status == ComparisonStatus.OK


@_db_only
def test_file_input_db_output_ng_detected(db_conn, tmp_path):
    """008(파일입력/DB출력 NG): 전각 공백 주입이 export 경로를 거쳐 1줄 NG로 검출된다."""
    from src.core.comparator import compare_files
    from src.core.models import ComparisonStatus

    cfg = _real_config(tmp_path)
    raw = cfg.tobe_input_dir / "008.csv"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(
        (
            "tx_id,customer_id,tx_date,tx_type,amount,balance_after,branch_code,memo\n"
            "T00001,C0001,2025-05-01,入金,200000,1700000,101,給与振込\n"
        ).encode("shift_jis")
    )
    d = _def("008", "file", "database")

    golden = runner.run_batch(d, cfg, db_conn, clean=True)[0][1]
    gbytes = golden.read_bytes()
    db_conn.rollback()  # export 읽기 트랜잭션 해제(셸 단위 경계 모사)
    tobe = runner.run_batch(d, cfg, db_conn, clean=False)[0][1]
    db_conn.rollback()

    gold_file = tmp_path / "golden_008.csv"
    gold_file.write_bytes(gbytes)
    res = compare_files(gold_file, tobe)
    assert res.status == ComparisonStatus.NG
    assert len(res.diff_lines) == 1


@_db_only
def test_failure_shell_raises(tmp_path):
    """010: 의도된 종료코드 1 → RunnerError (오케스트레이터가 ERROR로 매핑)."""
    cfg = _real_config(tmp_path)
    with pytest.raises(runner.RunnerError, match="終了コード 1"):
        runner.run_batch(_def("010", "file", "file"), cfg, conn=None)
