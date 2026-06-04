#!/usr/bin/env python3
"""현실형 테스트 환경의 As-Is 입력 CSV 생성기 (Shift-JIS, 결정론적).

생성물(samples/realistic/asis/input/):
  · 顧客マスタ.csv   — rt_customer 적재용(데모 customer_master와 동일 스키마)
  · 取引明細.csv     — rt_transaction 적재용(transaction_log 스키마). R01의 DB 입력.
  · night/夜間取引.csv — 파일 입력(R02). transaction_log 스키마.

골든(asis/output)은 손으로 만들지 않는다 — tools/make_golden.py가 stub --clean 경로로 생성(D-027).
인코딩은 config.realistic.yaml의 Shift_JIS와 일치해야 한다(파일↔DB 경계만 디코드, D-018).

사용: python tools/make_realistic_samples.py
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

_ENC = "shift_jis"
_BASE = Path(__file__).resolve().parents[1] / "samples" / "realistic" / "asis" / "input"

# 고객 마스터 (rt_customer = customer_master 스키마) ------------------------------
_CUSTOMER_HEADER = [
    "customer_id", "name", "kana", "birth_date",
    "branch_code", "account_type", "balance", "opened_date",
]
_CUSTOMERS = [
    ["C0001", "田中太郎",   "タナカタロウ",     "1980-04-15", "101", "普通", "1500000", "2015-06-01"],
    ["C0002", "佐藤花子",   "サトウハナコ",     "1975-11-02", "101", "普通",  "820000", "2012-03-20"],
    ["C0003", "鈴木一郎",   "スズキイチロウ",   "1990-07-30", "102", "当座", "3200000", "2018-09-10"],
    ["C0004", "高橋美咲",   "タカハシミサキ",   "1988-01-25", "102", "普通",  "450000", "2019-12-05"],
    ["C0005", "伊藤健",     "イトウケン",       "1972-05-18", "103", "普通", "2750000", "2010-08-14"],
    ["C0006", "渡辺由美",   "ワタナベユミ",     "1995-03-08", "101", "普通",  "120000", "2021-04-01"],
    ["C0007", "山本大輔",   "ヤマモトダイスケ", "1983-09-22", "103", "当座", "5100000", "2016-02-28"],
    ["C0008", "中村愛",     "ナカムラアイ",     "1992-12-11", "102", "普通",  "670000", "2020-07-19"],
]

# 거래 명세 (rt_transaction = transaction_log 스키마) — R01의 DB 입력 -------------
_TX_HEADER = [
    "tx_id", "customer_id", "tx_date", "tx_type",
    "amount", "balance_after", "branch_code", "memo",
]
_TRANSACTIONS = [
    ["TR0001", "C0001", "2025-06-01", "入金", "200000", "1700000", "101", "給与振込"],
    ["TR0002", "C0001", "2025-06-03", "出金",  "50000", "1650000", "101", "ATM出金"],
    ["TR0003", "C0002", "2025-06-02", "入金", "180000", "1000000", "101", "給与振込"],
    ["TR0004", "C0002", "2025-06-08", "振込",  "90000",  "910000", "101", "公共料金"],
    ["TR0005", "C0003", "2025-06-01", "入金", "500000", "3700000", "102", "売上入金"],
    ["TR0006", "C0003", "2025-06-06", "出金", "200000", "3500000", "102", "仕入支払"],
    ["TR0007", "C0004", "2025-06-04", "入金", "150000",  "600000", "102", "給与振込"],
    ["TR0008", "C0005", "2025-06-03", "入金", "300000", "3050000", "103", "給与振込"],
    ["TR0009", "C0005", "2025-06-11", "出金", "100000", "2950000", "103", ""],
    ["TR0010", "C0007", "2025-06-02", "入金", "800000", "5900000", "103", "売上入金"],
    ["TR0011", "C0007", "2025-06-09", "振込", "400000", "5500000", "103", "給与支払"],
    ["TR0012", "C0008", "2025-06-06", "入金", "120000",  "790000", "102", "給与振込"],
]

# 夜間取引(파일 입력, R02) — transaction_log 스키마, 야간 추가분 ----------------
_NIGHT = [
    ["NT0001", "C0001", "2025-06-15", "振込", "120000", "1530000", "101", "家賃支払"],
    ["NT0002", "C0004", "2025-06-15", "出金",  "80000",  "520000", "102", "ATM出金"],
    ["NT0003", "C0006", "2025-06-16", "入金",  "80000",  "200000", "101", "給与振込"],
    ["NT0004", "C0008", "2025-06-16", "振込",  "60000",  "730000", "102", "家賃支払"],
]


def _write(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    path.write_bytes(buf.getvalue().encode(_ENC))
    print(f"[realistic-sample] {path}  ({len(rows)} 行, {_ENC})")


def main() -> None:
    _write(_BASE / "顧客マスタ.csv", _CUSTOMER_HEADER, _CUSTOMERS)
    _write(_BASE / "取引明細.csv", _TX_HEADER, _TRANSACTIONS)
    _write(_BASE / "night" / "夜間取引.csv", _TX_HEADER, _NIGHT)


if __name__ == "__main__":
    main()
