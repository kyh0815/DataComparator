#!/usr/bin/env python3
"""시연용 stub 배치 — DB 입력 흐름 (셸 001~005, 결제 도메인).

# === 인수인계 시 교체 포인트 ===
# 이 파일은 시연용 stub 배치다. 실 운영에서는 고객의 진짜 배치(Net COBOL) 호출로 교체한다.
# 입출력 계약(--shell-id, --output-path, --output-type)은 유지할 것.

오케스트레이터가 transaction_log에 적재한 입력을 읽어 customer_master를 조인한
取引明細을 만들고, --output-type 에 따라 CSV(파일) 또는 tobe_result(DB)에 출력한다.

단독 실행 예:
  python stub_batch/run_batch_db.py --shell-id 001 \
      --output-path ./out/tobe_output/001.csv --output-type database
"""

from __future__ import annotations

import _stub_common as common


def _read(args, conn):
    # 프로토 한정: DB 입력은 항상 transaction_log를 읽는다(--input-table은 계약 유지용).
    return common.rows_from_db(conn)


def main() -> None:
    parser = common.build_common_parser("stub 배치(DB 입력) — 셸 001~005")
    parser.add_argument("--input-table", default="transaction_log", help="적재된 입력 테이블")
    args = parser.parse_args()
    common.run(args, _read)


if __name__ == "__main__":
    main()
