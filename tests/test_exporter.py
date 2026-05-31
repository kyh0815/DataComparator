"""T2-3 exporter(export_table_to_csv) 단위 테스트.

- CSV 포맷(헤더·NULL→빈칸·\\n·Shift-JIS)은 가짜 커서로 DB 없이 항상 검증.
- 실제 DB export는 RUN_DB_TESTS=1 일 때만 (stub 통합 테스트에서 함께 다룬다).
"""

from pathlib import Path

from src.core.exporter import export_table_to_csv

_COLS = ["tx_id", "customer_name", "amount", "memo"]


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, *args, **kwargs):
        pass

    def fetchall(self):
        return self._rows


class _FakeConn:
    """columns를 명시로 넘기면 SELECT 한 번만 → fetchall로 행을 돌려준다."""

    def __init__(self, rows):
        self._rows = rows

    def cursor(self):
        return _FakeCursor(self._rows)


def test_export_csv_format(tmp_path):
    """헤더=컬럼명, None→빈칸, 줄바꿈 \\n, Shift-JIS 인코딩."""
    rows = [
        ("T001", "田中太郎", "200000", "給与振込"),
        ("T002", "佐藤花子", "30000", None),  # memo NULL → 빈칸
    ]
    out = tmp_path / "out.csv"
    export_table_to_csv(_FakeConn(rows), "tobe_result", out, columns=_COLS)

    data = out.read_bytes()
    text = data.decode("shift_jis")
    assert text == (
        "tx_id,customer_name,amount,memo\n"
        "T001,田中太郎,200000,給与振込\n"
        "T002,佐藤花子,30000,\n"
    )
    assert b"\r" not in data  # \n 전용
