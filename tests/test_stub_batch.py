"""T2-3 stub 배치 단위 테스트.

- NG 주입 순수 로직(`apply_ng_pattern` 등)·실패 셸 판정 → 항상 실행 (DB 의존 0).
- 실제 DB 입출력(stub subprocess 실행)은 RUN_DB_TESTS=1 일 때만 (T2-2 패턴 일관).
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "stub_batch"))

import _stub_common as common  # noqa: E402


def _sample_rows():
    # OUTPUT_COLUMNS: tx_id, customer_id, customer_name, tx_date, tx_type, amount, balance_after, memo
    return [
        ["T001", "C0001", "田中太郎", "2025-05-01", "入金", "200000", "1700000", "給与振込"],
        ["T002", "C0002", "佐藤花子", "2025-05-02", "出金", "30000", "970000", ""],
        ["T003", "C0003", "鈴木一郎", "2025-05-03", "振込", "300000", "3200000", "外注費"],
    ]


# --- NG 주입 순수 로직 (항상 실행) ---------------------------------------------


def test_ng_007_single_value_diff():
    """007: 첫 행 balance_after 1 증가 → 정확히 한 셀만 변경."""
    rows = _sample_rows()
    before = [r[:] for r in rows]
    common.apply_ng_pattern("007", rows)
    assert rows[0][6] == "1700001"  # 1700000 + 1
    rows[0][6] = before[0][6]
    assert rows == before  # 그 외엔 모두 동일


def test_ng_008_fullwidth_space_in_name():
    """008: 첫 행 customer_name에 전각 공백 삽입(田中太郎 → 田中　太郎)."""
    rows = _sample_rows()
    common.apply_ng_pattern("008", rows)
    assert rows[0][2] == "田中　太郎"
    assert "　" in rows[0][2]


def test_ng_009_multi_line_diff():
    """009: 서로 다른 3개 행이 변경된다."""
    rows = _sample_rows()
    before = [r[:] for r in rows]
    common.apply_ng_pattern("009", rows)
    changed = [i for i in range(len(rows)) if rows[i] != before[i]]
    assert changed == [0, 1, 2]
    assert rows[0][6] == "1700001"
    assert rows[1][4] == "出金X"
    assert rows[2][7] == "外注費差分"


def test_no_injection_for_ok_shell():
    """OK 셸(006)·정상 셸은 변형 없음."""
    rows = _sample_rows()
    before = [r[:] for r in rows]
    common.apply_ng_pattern("006", rows)
    assert rows == before


def test_is_failure_shell():
    assert common.is_failure_shell("010") is True
    assert common.is_failure_shell("001") is False
    assert common.is_failure_shell("007") is False


def test_bump_number_non_numeric():
    """숫자가 아니면 어쨌든 달라지게 만든다."""
    assert common._bump_number("100") == "101"
    assert common._bump_number("abc") == "abc9"


def test_insert_space_short_name():
    """짧은/빈 이름도 안전하게 전각 공백을 넣는다."""
    assert "　" in common._insert_fullwidth_space("林")
    assert common._insert_fullwidth_space("") == "　"


# --- DB 입출력 통합 (RUN_DB_TESTS=1 일 때만) ------------------------------------

_DB_ENABLED = os.environ.get("RUN_DB_TESTS") == "1"
_db_only = pytest.mark.skipif(
    not _DB_ENABLED, reason="DB 통합 테스트는 RUN_DB_TESTS=1 일 때만 실행"
)


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


def _run_stub(script: str, *args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_ROOT / "stub_batch" / script), *args],
        capture_output=True,
        text=True,
    )


@_db_only
def test_db_stub_file_output(db_conn, tmp_path):
    """DB 입력 → 파일 출력: transaction_log(시드)를 읽어 CSV(Shift-JIS) 생성."""
    out = tmp_path / "001.csv"
    proc = _run_stub(
        "run_batch_db.py", "--shell-id", "001",
        "--output-path", str(out), "--output-type", "file",
    )
    assert proc.returncode == 0, proc.stderr
    text = out.read_bytes().decode("shift_jis")
    lines = text.splitlines()
    assert lines[0] == "tx_id,customer_id,customer_name,tx_date,tx_type,amount,balance_after,memo"
    assert len(lines) == 51  # 헤더 + 거래 50건
    assert "田中太郎" in text  # 마스터 조인된 顧客名


@_db_only
def test_file_stub_db_output_then_export(db_conn, tmp_path):
    """파일 입력 → DB 출력(tobe_result) → exporter로 CSV 다운로드. 008 NG(전각 공백) 확인."""
    from src.core.exporter import export_table_to_csv

    raw = tmp_path / "008.csv"
    raw.write_bytes(
        (
            "tx_id,customer_id,tx_date,tx_type,amount,balance_after,branch_code,memo\n"
            "T00001,C0001,2025-05-01,入金,200000,1700000,101,給与振込\n"
        ).encode("shift_jis")
    )
    proc = _run_stub(
        "run_batch_file.py", "--shell-id", "008",
        "--output-path", str(tmp_path / "008_out.csv"), "--output-type", "database",
        "--input-file", str(raw),
    )
    assert proc.returncode == 0, proc.stderr

    exported = export_table_to_csv(db_conn, "tobe_result", tmp_path / "008_exp.csv")
    text = exported.read_bytes().decode("shift_jis")
    assert "田中　太郎" in text  # 008 NG: 전각 공백 주입이 export까지 반영


@_db_only
def test_failure_shell_exit_code(tmp_path):
    """010: 의도적 종료코드 1 (출력 파일 없이 실패)."""
    raw = tmp_path / "010.csv"
    raw.write_bytes("tx_id,customer_id,tx_date,tx_type,amount,balance_after,branch_code,memo\n".encode("shift_jis"))
    proc = _run_stub(
        "run_batch_file.py", "--shell-id", "010",
        "--output-path", str(tmp_path / "010.csv"), "--output-type", "file",
        "--input-file", str(raw),
    )
    assert proc.returncode == 1
