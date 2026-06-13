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
    # D-060: .py 배치는 [인터프리터, 스크립트, ...] — Windows 크로스플랫폼 실행
    import sys
    assert argv[0] == sys.executable
    assert argv[1].endswith("stub_batch/run_batch_db.py")
    assert argv[2:4] == ["--shell-id", "001"]
    assert "--input-table" in argv and "transaction_log" in argv
    assert "--output-table" in argv
    assert "--output-path" not in argv  # DB출력엔 출력경로를 stub에 넘기지 않음


def test_argv_file_input_file_output(tmp_path):
    """파일입력/파일출력: --input-file(복사 위치), --output-path 있음, --output-table 없음."""
    argv, env, timeout = runner._build_command(
        _def("006", "file", "file"), _config(tmp_path), clean=False
    )
    import sys
    assert argv[0] == sys.executable                       # D-060: .py → 인터프리터 경유
    assert argv[1].endswith("stub_batch/run_batch_file.py")
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


# --- P0: run_setup (입력 적재 전 준비 SQL/스크립트) ------------------------------


def test_run_setup_none_is_noop(tmp_path):
    """setup 미지정이면 무동작(예외 없음)."""
    runner.run_setup(_def("001", "file", "file"), _config(tmp_path), conn=None)


def test_run_setup_runs_script(tmp_path):
    """비-.sql setup은 실행파일로 호출된다(마커 파일로 확인)."""
    marker = tmp_path / "ran.txt"
    script = tmp_path / "prep.sh"
    script.write_text(f"#!/bin/sh\necho ok > {marker}\n", encoding="utf-8")
    script.chmod(0o755)
    d = _def("001", "file", "file", setup=str(script))
    runner.run_setup(d, _config(tmp_path), conn=None)
    assert marker.is_file()


def test_run_setup_script_failure_raises(tmp_path):
    """setup 스크립트 종료코드≠0 → RunnerError."""
    script = tmp_path / "bad.sh"
    script.write_text("#!/bin/sh\nexit 3\n", encoding="utf-8")
    script.chmod(0o755)
    d = _def("001", "file", "file", setup=str(script))
    with pytest.raises(runner.RunnerError, match="setup"):
        runner.run_setup(d, _config(tmp_path), conn=None)


def test_run_setup_sql_without_conn_raises(tmp_path):
    """.sql setup인데 conn 없음 → RunnerError(.sql은 DB 필요)."""
    sql = tmp_path / "reset.sql"
    sql.write_text("SELECT 1;\n", encoding="utf-8")
    d = _def("001", "file", "file", setup=str(sql))
    with pytest.raises(runner.RunnerError, match="conn"):
        runner.run_setup(d, _config(tmp_path), conn=None)


# --- C6: 배치 호출 결합 제거 (config 외부화 / 2번째 규약 검증) --------------------


def test_render_argv_pair_drop_and_eq_forms():
    """렌더러: [flag,{값}] 쌍은 빈값이면 함께 드롭, '--f={값}'·'{값}'도 빈값이면 드롭."""
    ctx = {"shell_id": "001", "input_table": "", "input_file": "/f",
           "output_table": "T", "output_path": ""}
    tmpl = ["run", "{shell_id}", "--it", "{input_table}", "--if", "{input_file}",
            "--ot={output_table}", "--op={output_path}"]
    assert runner._render_argv(tmpl, ctx) == ["run", "001", "--if", "/f", "--ot=T"]


def test_no_transaction_log_fallback(tmp_path):
    """폴백 제거: 입력 테이블은 정의값만 — 코어가 도메인 상수를 끼워넣지 않는다."""
    d = _def("001", "database", "database", input_table="MY_TBL")
    argv, *_ = runner._build_command(d, _config(tmp_path), clean=False)
    assert "MY_TBL" in argv and "transaction_log" not in argv


def test_second_batch_different_convention_via_config_only(tmp_path):
    """★C6 핵심: 인자 규약·성공코드가 *다른* 2번째 배치를 config만 바꿔 붙인다(코어 0줄 수정).

    같은 stub만 쓰면 결합이 안 풀려도 녹색이라, 일부러 전혀 다른 규약의 배치를 실제 실행해 검증한다.
    """
    marker = tmp_path / "argv.txt"
    script = tmp_path / "batch2.sh"
    script.write_text(f'#!/bin/sh\necho "$@" > "{marker}"\nexit 7\n', encoding="utf-8")
    script.chmod(0o755)

    cfg = _config(tmp_path)
    # 전혀 다른 규약: 서브커맨드 run + shell_id 위치인자 + --src/--dst, DB 인자 없음, 성공코드 7.
    cfg.batch.command = ["run", "{shell_id}", "--src", "{input_file}", "--dst", "{output_path}"]
    cfg.batch.success_exit_code = 7
    cfg.batch.env = {}
    d = _def("C002", "file", "file", shell_program=str(script))

    resolved = runner.run_batch(d, cfg)  # 성공코드 7 → RunnerError 안 남(코어 무수정)

    got = marker.read_text(encoding="utf-8").split()
    assert got[0] == "run" and got[1] == "C002"          # 새 규약대로 전달
    assert "--src" in got and "--dst" in got
    assert "--shell-id" not in got and "--db-host" not in got  # 옛 규약 흔적 없음
    assert resolved[0][1] == tmp_path / "tobe_output" / "C002.csv"


def test_success_exit_code_is_configurable(tmp_path, monkeypatch):
    """성공 종료코드가 config 구동 — 기본(0)에서 7은 실패, success_exit_code=7이면 성공."""
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: _Proc(returncode=7))
    with pytest.raises(runner.RunnerError, match="終了コード 7"):
        runner.run_batch(_def("006", "file", "file"), _config(tmp_path))
    cfg = _config(tmp_path)
    cfg.batch.success_exit_code = 7
    runner.run_batch(_def("006", "file", "file"), cfg)  # 이제 성공(예외 없음)


def test_exec_argv_py_uses_interpreter():
    """`.py` 배치는 현재 인터프리터로 실행(D-060 — Windows 크로스플랫폼). 그 외는 직접 호출(계약 불변)."""
    import sys
    from pathlib import Path
    from src.core.runner import _exec_argv

    assert _exec_argv(Path("/x/mock.py")) == [sys.executable, "/x/mock.py"]
    assert _exec_argv(Path("/x/MOCK.PY")) == [sys.executable, "/x/MOCK.PY"]  # 대소문자 무관
    assert _exec_argv(Path("/opt/job/batch.sh")) == ["/opt/job/batch.sh"]   # 실 배치는 그대로
    assert _exec_argv(Path("/opt/job/netcobol_bin")) == ["/opt/job/netcobol_bin"]
