"""T2-2 Loader 단위/통합 테스트.

- 순수 파싱(`_parse_rows`)·헤더 검증·파일 없음 → 기본 pytest에서 항상 실행 (DB 의존 0).
- 실제 DB 적재 → RUN_DB_TESTS=1 일 때만 실행 (T2-1 패턴과 일관, 정직원이 그냥
  pytest 돌려도 사고 없게). 통합 테스트는 일회용 정보를 환경변수로 받는다.
"""

import os
from pathlib import Path

import pytest

from src.core.loader import LoaderError, _parse_rows, load_input_csv

# --- 순수 단위 테스트 (항상 실행) ------------------------------------------------


def test_parse_rows_basic():
    """헤더 + 데이터 행을 컬럼·튜플로 파싱한다."""
    columns, rows = _parse_rows("tx_id,amount,memo\nT001,100,給与\nT002,200,家賃\n")
    assert columns == ["tx_id", "amount", "memo"]
    assert rows == [("T001", "100", "給与"), ("T002", "200", "家賃")]


def test_parse_rows_empty_cell_becomes_none():
    """빈 문자열 셀은 None(NULL)으로 변환된다."""
    _, rows = _parse_rows("tx_id,memo\nT001,\nT002,振込\n")
    assert rows[0] == ("T001", None)
    assert rows[1] == ("T002", "振込")


def test_parse_rows_column_count_mismatch():
    """행 컬럼 수가 헤더와 다르면 LoaderError."""
    with pytest.raises(LoaderError, match="컬럼 수"):
        _parse_rows("a,b,c\n1,2\n")


def test_parse_rows_empty_csv():
    """헤더조차 없으면 LoaderError."""
    with pytest.raises(LoaderError, match="빈 CSV"):
        _parse_rows("")


def test_parse_rows_skips_blank_lines():
    """완전한 빈 줄은 건너뛴다(말미 개행 등)."""
    _, rows = _parse_rows("a,b\n1,2\n\n")
    assert rows == [("1", "2")]


def test_load_missing_file_raises(tmp_path):
    """존재하지 않는 CSV → LoaderError (conn은 닿지 않으므로 None으로 충분)."""
    with pytest.raises(LoaderError, match="CSV 파일이 없"):
        load_input_csv(tmp_path / "nope.csv", conn=None, table_name="transaction_log")


# --- DB 통합 테스트 (RUN_DB_TESTS=1 일 때만) -------------------------------------

_DB_ENABLED = os.environ.get("RUN_DB_TESTS") == "1"
_db_only = pytest.mark.skipif(
    not _DB_ENABLED, reason="DB 통합 테스트는 RUN_DB_TESTS=1 일 때만 실행"
)


@pytest.fixture
def db_conn():
    """통합 테스트용 임시 테이블이 있는 연결. 환경변수로 접속 정보를 받는다."""
    import psycopg2

    conn = psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=int(os.environ.get("PGPORT", "5432")),
        dbname=os.environ.get("PGDATABASE", "compare_proto"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("POSTGRES_PASSWORD"),
    )
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS loader_test")
        cur.execute(
            "CREATE TABLE loader_test ("
            " tx_id TEXT NOT NULL, amount BIGINT NOT NULL, memo TEXT,"
            " PRIMARY KEY (tx_id))"
        )
    conn.commit()
    yield conn
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS loader_test")
    conn.commit()
    conn.close()


def _write_csv(tmp_path: Path, text: str, encoding: str = "shift_jis") -> Path:
    p = tmp_path / "001.csv"
    p.write_bytes(text.encode(encoding))
    return p


@_db_only
def test_load_and_select_roundtrip(db_conn, tmp_path):
    """샘플 CSV 적재 → SELECT로 동일 데이터·행수 확인. 일본어·NULL 포함."""
    csv_path = _write_csv(tmp_path, "tx_id,amount,memo\nT001,100,給与振込\nT002,200,\n")
    count = load_input_csv(csv_path, db_conn, "loader_test")
    db_conn.commit()
    assert count == 2

    with db_conn.cursor() as cur:
        cur.execute("SELECT tx_id, amount, memo FROM loader_test ORDER BY tx_id")
        got = cur.fetchall()
    assert got == [("T001", 100, "給与振込"), ("T002", 200, None)]


@_db_only
def test_truncate_on_reload(db_conn, tmp_path):
    """재적재 시 TRUNCATE되어 행수가 누적되지 않는다."""
    first = _write_csv(tmp_path, "tx_id,amount,memo\nT001,100,A\nT002,200,B\n")
    load_input_csv(first, db_conn, "loader_test")
    db_conn.commit()

    second = _write_csv(tmp_path, "tx_id,amount,memo\nT009,900,Z\n")
    count = load_input_csv(second, db_conn, "loader_test")
    db_conn.commit()
    assert count == 1

    with db_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM loader_test")
        assert cur.fetchone()[0] == 1


@_db_only
def test_unknown_header_column_raises(db_conn, tmp_path):
    """CSV 헤더에 테이블에 없는 컬럼이 있으면 LoaderError."""
    bad = _write_csv(tmp_path, "tx_id,amount,bogus\nT001,100,x\n")
    with pytest.raises(LoaderError, match="알 수 없는 컬럼"):
        load_input_csv(bad, db_conn, "loader_test")
