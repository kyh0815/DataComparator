#!/usr/bin/env python3
"""리허설용 더미 배치 — CK001 顧客残高マスタ日次更新 (진짜 Net COBOL 배치 자리).

진짜 배치 붙기 전 compare 파이프라인을 한 바퀴 돌려보는 연습용. 입력(取引明細)을 받아
顧客残高マスタの To-Be 출력(DB export 형식 = Shift-JIS·헤더 有)을 낸다. 실 배치는 입력으로부터
잔고를 계산하지만, 여기선 **검증 대상인 차이 패턴이 고정**이어야 하므로 To-Be를 캐닝해 기록한다.

호출 규약 = 코어 기본 BatchConfig.command(C6). 파일 입출력 셸이라 실제로 쓰는 건 --input-file /
--output-path / --encoding 이고, 나머지(--shell-id·--db-* 등)는 parse_known_args로 무시한다.

★심은 차이(As-Is 정답 대비) — samples/rehearsal/README.md의 표와 일치:
- 행 순서 셔플(SELECT 비결정) → key로 해소
- SHITEN_CD 제로패딩 탈락(0007→7) → normalize zeropad:4
- ZANDAKA 소수자리 탈락(150000.00→150000) → normalize num:2
- KISAN_YMD 날짜포맷(2026-06-01→20260601) → normalize date
- KOSHIN_NICHIJI 실행시각 상이 → mask
- BIKO 공백→NULL → normalize nullblank
- ★KOKYAKU_ID=0003 ZANDAKA = 진짜 결함(3000.00 → 2500). 정규화로도 NG 유지(손대지 말 것).
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

_HEADER = [
    "KOKYAKU_ID", "SHITEN_CD", "KOKYAKU_NM", "ZANDAKA",
    "TORIHIKI_KEN", "KISAN_YMD", "KOSHIN_NICHIJI", "BIKO",
]

# To-Be 顧客残高マスタ — 행 순서 셔플 + 플랫폼 차이 심음. 0003만 ZANDAKA 값 자체가 결함(2500).
# KOSHIN_NICHIJI는 As-Is와 다른 실행시각(마스킹 대상이라 OK여야 함).
_TOBE_ROWS = [
    ["0003", "7", "佐藤一郎", "2500", "2", "20260601", "2026-06-15 03:22:41", "NULL"],   # ★결함
    ["0001", "7", "山田太郎", "150000", "12", "20260601", "2026-06-15 03:22:41", "NULL"],
    ["0005", "7", "高橋四郎", "0", "0", "20260601", "2026-06-15 03:22:41", "NULL"],
    ["0002", "7", "鈴木花子", "89000", "5", "20260601", "2026-06-15 03:22:41", "NULL"],
    ["0004", "12", "田中三郎", "250000.5", "8", "20260601", "2026-06-15 03:22:41", "VIP"],
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="리허설 더미 배치(CK001 顧客残高マスタ)")
    parser.add_argument("--input-file")
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--encoding", default="shift_jis")
    # --shell-id·--db-* 등 나머지 호출규약 인자는 무시(실 배치도 자기 I/O만 씀).
    args, _ignored = parser.parse_known_args(argv)

    # 입력(取引明細)을 받는다 — 존재 확인(실 배치는 이걸로 잔고를 계산).
    if args.input_file:
        src = Path(args.input_file)
        if not src.is_file():
            print(f"入力ファイルがありません: {src}", file=sys.stderr)
            return 1

    out = Path(args.output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding=args.encoding, newline="") as f:
        writer = csv.writer(f)
        writer.writerow(_HEADER)
        writer.writerows(_TOBE_ROWS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
