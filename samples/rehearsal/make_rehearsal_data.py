#!/usr/bin/env python3
"""리허설용 As-Is 데이터 생성기 — 取引明細(입력) + 顧客残高マスタ(정답)을 Shift-JIS로 쓴다.

To-Be 출력은 더미 배치(batch/kokyaku_zandaka_update.py)가 실행 시 생성하므로 여기선 안 만든다.
이 스크립트는 데이터 재생성/편집 편의용 — 산출 CSV(asis/input·asis/output)가 실제 리허설 입력이다.
인코딩은 코어 기본(loader/comparator)과 동일한 Shift-JIS.
"""

from __future__ import annotations

import csv
from pathlib import Path

_ENCODING = "shift_jis"
_HERE = Path(__file__).resolve().parent

# 取引明細(As-Is 입력) — 더미 배치는 존재만 확인하지만, 실 배치 입력 자리로 현실감 있게 채운다.
_TORIHIKI_HEADER = ["TORIHIKI_ID", "KOKYAKU_ID", "SHITEN_CD", "TORIHIKI_KBN", "KINGAKU", "TORIHIKI_YMD"]
_TORIHIKI_ROWS = [
    ["T0001", "0001", "0007", "1", "50000", "2026-06-01"],
    ["T0002", "0002", "0007", "1", "12000", "2026-06-01"],
    ["T0003", "0003", "0007", "2", "500", "2026-06-01"],
    ["T0004", "0004", "0012", "1", "100000", "2026-06-01"],
    ["T0005", "0005", "0007", "2", "300", "2026-06-01"],
    ["T0006", "0001", "0007", "2", "1500", "2026-06-01"],
]

# 顧客残高マスタ(As-Is 정답) — 정렬된 순서, 제로패딩·소수2자리·ISO날짜·공백 BIKO.
# 0003 ZANDAKA=3000.00 이 정답(To-Be는 2500 = 결함).
_MASTER_HEADER = [
    "KOKYAKU_ID", "SHITEN_CD", "KOKYAKU_NM", "ZANDAKA",
    "TORIHIKI_KEN", "KISAN_YMD", "KOSHIN_NICHIJI", "BIKO",
]
_MASTER_ROWS = [
    ["0001", "0007", "山田太郎", "150000.00", "12", "2026-06-01", "2026-06-01 01:00:05", ""],
    ["0002", "0007", "鈴木花子", "89000.00", "5", "2026-06-01", "2026-06-01 01:00:05", ""],
    ["0003", "0007", "佐藤一郎", "3000.00", "2", "2026-06-01", "2026-06-01 01:00:05", ""],
    ["0004", "0012", "田中三郎", "250000.50", "8", "2026-06-01", "2026-06-01 01:00:05", "VIP"],
    ["0005", "0007", "高橋四郎", "0.00", "0", "2026-06-01", "2026-06-01 01:00:05", ""],
]


def _write(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=_ENCODING, newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main() -> int:
    _write(_HERE / "asis/input/torihiki_meisai.csv", _TORIHIKI_HEADER, _TORIHIKI_ROWS)
    _write(_HERE / "asis/output/kokyaku_zandaka_master.csv", _MASTER_HEADER, _MASTER_ROWS)
    print("生成: asis/input/torihiki_meisai.csv, asis/output/kokyaku_zandaka_master.csv (Shift-JIS)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
