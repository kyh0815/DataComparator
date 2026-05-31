#!/usr/bin/env python3
"""시연용 stub 배치 — 파일 입력 흐름 = 야간 배치 시뮬 (셸 006~010).

# === 인수인계 시 교체 포인트 ===
# 이 파일은 시연용 stub 배치다. 실 운영에서는 고객의 진짜 배치(Net COBOL) 호출로 교체한다.
# 입출력 계약(--shell-id, --output-path, --output-type)은 유지할 것.

야간 배치 시뮬: 오케스트레이터가 복사해 둔 raw 거래 파일을 직접 읽고 customer_master를
조인한 取引明細을 만든다. --output-type 에 따라 CSV(파일) 또는 tobe_result(DB)에 출력한다.
셸 010은 의도적으로 종료코드 1로 실패한다(ERROR 시연).

단독 실행 예:
  python stub_batch/run_batch_file.py --shell-id 006 \
      --output-path ./out/tobe_output/006.csv --output-type file \
      --input-file ./out/tobe_input/006.csv
"""

from __future__ import annotations

from pathlib import Path

import _stub_common as common


def _read(args, conn):
    return common.rows_from_file(Path(args.input_file), args.encoding, conn)


def main() -> None:
    parser = common.build_common_parser("stub 배치(파일 입력=야간 배치) — 셸 006~010")
    parser.add_argument("--input-file", required=True, help="복사된 raw 거래 파일")
    args = parser.parse_args()
    common.run(args, _read)


if __name__ == "__main__":
    main()
