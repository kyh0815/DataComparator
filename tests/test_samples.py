"""T4-1 시연용 입력 샘플 데이터 불변식 테스트 (DB 불요 — 항상 실행).

stub의 NG 주입은 *위치 기반*(SPEC 6-5)이라, 입력 행 수/첫 행 고객이 요건을 어기면 시연이
조용히 망가진다. 그 요건과 직렬화 결정론을 코드로 가드한다(make_golden은 DB 필요라 제외).
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.make_samples import HEADER, SAMPLES, _csv_bytes

# 시드 customer_master (db/schema.sql): C0001~C0020.
_SEEDED = {f"C{n:04d}" for n in range(1, 21)}
_CID = HEADER.index("customer_id")


def test_all_ten_shells_present():
    assert sorted(SAMPLES) == [f"{n:03d}" for n in range(1, 11)]


def test_header_matches_transaction_log_schema():
    assert HEADER == [
        "tx_id", "customer_id", "tx_date", "tx_type",
        "amount", "balance_after", "branch_code", "memo",
    ]


def test_every_row_has_full_columns():
    for sid, rows in SAMPLES.items():
        for r in rows:
            assert len(r) == len(HEADER), f"{sid}: 컬럼 수 불일치 {r}"


def test_all_customer_ids_are_seeded():
    """모든 customer_id가 시드에 존재 → 顧客名 조인 enrich(없으면 빈칸이라 시연 약화)."""
    for sid, rows in SAMPLES.items():
        for r in rows:
            assert r[_CID] in _SEEDED, f"{sid}: 미시드 고객 {r[_CID]}"


def test_ng_positional_requirements():
    """위치 기반 NG 주입 요건(SPEC 6-5): 007/008 ≥1행, 009 ≥3행, 008 첫 행은 유효 고객."""
    assert len(SAMPLES["007"]) >= 1
    assert len(SAMPLES["008"]) >= 1
    assert len(SAMPLES["009"]) >= 3
    # 008은 첫 tx_id 행의 customer_name에 전각 공백을 넣으므로 고객명이 비면 안 된다.
    first_008 = sorted(SAMPLES["008"], key=lambda r: r[0])[0]
    assert first_008[_CID] in _SEEDED


def test_csv_bytes_deterministic_and_shift_jis():
    rows = SAMPLES["001"]
    b1 = _csv_bytes(rows)
    b2 = _csv_bytes(rows)
    assert b1 == b2  # 결정론
    text = b1.decode("shift_jis")  # Shift-JIS 왕복
    assert text.splitlines()[0] == ",".join(HEADER)
    assert "\r\n" not in text  # 줄바꿈은 \n (comparator/exporter와 일관)
