"""현실형 stub(run_settlement) 순수 로직 테스트 — DB 의존 0 (집계만 검증)."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "stub_batch"))

import run_settlement as s  # noqa: E402


def _detail():
    # OUTPUT_COLUMNS: tx_id, customer_id, customer_name, tx_date, tx_type, amount, balance_after, memo
    return [
        ["TR1", "C0001", "田中太郎", "2025-06-01", "入金", "200000", "1700000", "給与"],
        ["TR2", "C0001", "田中太郎", "2025-06-03", "出金", "50000", "1650000", ""],
        ["TR3", "C0002", "佐藤花子", "2025-06-02", "入金", "180000", "1000000", "給与"],
    ]


def test_summarize_groups_by_customer_with_count_and_total():
    rows = s._summarize(_detail())
    # customer_id 정렬, [customer_id, name, count, total]
    assert rows == [
        ["C0001", "田中太郎", "2", "250000"],
        ["C0002", "佐藤花子", "1", "180000"],
    ]


def test_summarize_columns_match_table_order():
    # export 헤더(=rt_summary 컬럼 순서)와 1:1 — 드리프트 가드.
    assert s._SUMMARY_COLUMNS == ["customer_id", "customer_name", "tx_count", "total_amount"]


def test_summarize_ignores_non_numeric_amount():
    rows = s._summarize([["TR9", "C9", "x", "d", "入金", "", "0", ""]])
    assert rows == [["C9", "x", "1", "0"]]


def test_summarize_empty():
    assert s._summarize([]) == []
