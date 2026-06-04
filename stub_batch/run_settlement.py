#!/usr/bin/env python3
"""현실형 stub 배치 — 日次決済バッチ 시뮬 (Phase 7 다중 입출력 검증).

# === 인수인계 시 교체 포인트 ===
# 이 파일은 "한 셸(잡)이 여러 입력을 읽고 파일·DB로 동시 출력"하는 실 운영 형태를
# 시연하기 위한 stub다. 실 운영에서는 고객의 진짜 래퍼 배치(Net COBOL 등)로 교체한다.
# 입출력 계약(--shell-id / --output-path / --output-type / --input-table|--input-file)은 유지.

동작(한 번 실행에 출력 2건 동시 생성 — 실 배치가 자기 출력 위치에 내는 것을 모사):
  1) 거래를 읽는다: --input-table(DB) 또는 --input-file(파일, Shift-JIS) 중 주어진 쪽.
  2) rt_customer(마스터, 도구가 적재) 조인 → 取引明細(detail).
  3) **파일 출력**: detail을 --output-path CSV(Shift-JIS)로 직접 기록.   ← 정의 outputs[0](file)
  4) **DB 출력**: 고객별 집계(건수·합계)를 --summary-table에 TRUNCATE+INSERT.
                  오케스트레이터(exporter)가 이 테이블을 CSV로 다운로드해 비교.  ← 정의 outputs[1](database)

runner는 outputs[0](file) 기준으로만 scaffolding 인자를 넘기지만(--output-path),
실 배치처럼 이 stub은 **자기 출력 전부**(파일 + 집계 테이블)를 안다. 집계/마스터 테이블명은
runner가 넘기지 않으므로 기본값(rt_summary / rt_customer)을 쓴다.

단독 실행 예:
  python stub_batch/run_settlement.py --shell-id R01 \
      --output-path ./out/realistic/tobe_output/決済明細.csv --output-type file \
      --input-table rt_transaction
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import _stub_common as common


def _read_transactions(args, conn) -> list[list[str]]:
    """거래를 OUTPUT_COLUMNS 형태(마스터 미조인)로 읽는다 — DB 테이블 또는 파일.

    반환 행: [tx_id, customer_id, "", tx_date, tx_type, amount, balance_after, memo]
    (customer_name은 _join_master에서 채운다.)
    """
    if args.input_table:  # DB 입력(runner가 inputs[0]=database면 전달)
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT tx_id, customer_id, tx_date, tx_type, amount, balance_after, "  # noqa: S608
                f"COALESCE(memo,'') FROM {args.input_table} ORDER BY tx_id"
            )  # 테이블명은 정의(신뢰 입력)에서 옴 — 사용자 입력 아님
            return [
                [common._s(r[0]), common._s(r[1]), "", common._s(r[2]), common._s(r[3]),
                 common._s(r[4]), common._s(r[5]), common._s(r[6])]
                for r in cur.fetchall()
            ]
    # 파일 입력(runner가 inputs[0]=file이면 --input-file 전달)
    text = Path(args.input_file).read_bytes().decode(args.encoding, errors="strict")
    rows: list[list[str]] = []
    for rec in csv.DictReader(io.StringIO(text)):
        rows.append([
            common._s(rec.get("tx_id")), (rec.get("customer_id") or "").strip(), "",
            common._s(rec.get("tx_date")), common._s(rec.get("tx_type")),
            common._s(rec.get("amount")), common._s(rec.get("balance_after")),
            common._s(rec.get("memo")),
        ])
    rows.sort(key=lambda r: r[0])  # tx_id 정렬(결정론)
    return rows


def _join_master(rows: list[list[str]], conn, master_table: str) -> list[list[str]]:
    """customer_id → name 조인으로 customer_name(인덱스 2)을 채운다."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT customer_id, name FROM {master_table}")  # noqa: S608
        names = {cid: name for cid, name in cur.fetchall()}
    for r in rows:
        r[2] = names.get(r[1], "")
    return rows


def _summarize(detail: list[list[str]]) -> list[list[str]]:
    """detail → 고객별 집계 행 [customer_id, customer_name, tx_count, total_amount] (customer_id 정렬)."""
    agg: dict[str, dict] = {}
    for r in detail:
        cid = r[1]
        a = agg.setdefault(cid, {"name": r[2], "count": 0, "total": 0})
        a["count"] += 1
        a["total"] += int(r[5]) if r[5].lstrip("-").isdigit() else 0
        if not a["name"]:
            a["name"] = r[2]
    return [
        [cid, agg[cid]["name"], str(agg[cid]["count"]), str(agg[cid]["total"])]
        for cid in sorted(agg)
    ]


_SUMMARY_COLUMNS = ["customer_id", "customer_name", "tx_count", "total_amount"]


def _write_summary(conn, table: str, rows: list[list[str]]) -> None:
    """집계를 결과 테이블에 TRUNCATE+INSERT하고 commit한다(출력=database — exporter가 읽음)."""
    from psycopg2 import sql

    with conn.cursor() as cur:
        cur.execute(sql.SQL("TRUNCATE TABLE {}").format(sql.Identifier(table)))
        if rows:
            stmt = sql.SQL("INSERT INTO {t} ({c}) VALUES ({p})").format(
                t=sql.Identifier(table),
                c=sql.SQL(", ").join(sql.Identifier(c) for c in _SUMMARY_COLUMNS),
                p=sql.SQL(", ").join(sql.Placeholder() for _ in _SUMMARY_COLUMNS),
            )
            cur.executemany(stmt, rows)
    conn.commit()


def main() -> None:
    parser = common.build_common_parser("현실형 stub(日次決済) — 다중 입력→파일+DB 출력")
    parser.add_argument("--input-table", help="DB 입력 거래 테이블(runner가 inputs[0]=database면 전달)")
    parser.add_argument("--input-file", help="파일 입력 거래 파일(runner가 inputs[0]=file이면 전달)")
    parser.add_argument("--master-table", default="rt_customer", help="조인할 고객 마스터 테이블")
    parser.add_argument("--summary-table", default="rt_summary", help="DB 출력(집계) 테이블")
    args = parser.parse_args()

    conn = common.connect(args)
    try:
        detail = _join_master(_read_transactions(args, conn), conn, args.master_table)
        # 파일 출력(outputs[0]=file): detail을 --output-path에 기록.
        if args.output_path:
            common.write_csv_file(detail, Path(args.output_path), args.encoding)
        # DB 출력(outputs[1]=database): 집계를 결과 테이블에. runner가 listed면 export해 비교.
        _write_summary(conn, args.summary_table, _summarize(detail))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
