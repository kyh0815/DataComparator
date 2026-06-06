#!/usr/bin/env python3
"""realtest 더미 배치(진짜 배치 자리) — tobe_src/<출력파일명>을 출력 경로로 바이트 복사한다.

호출 규약 = 코어 기본 BatchConfig.command(C6). 실제로 쓰는 건 --input-file / --output-path 뿐이고
나머지(--shell-id·--db-* 등)는 parse_known_args로 무시. 실 배치는 입력으로 출력을 *계산*하지만,
리허설/시험에선 검증 대상인 To-Be를 결정적으로 두려고 사전 준비된 tobe_src를 그대로 낸다.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="realtest dummy batch")
    p.add_argument("--input-file")
    p.add_argument("--output-path", required=True)
    args, _ignored = p.parse_known_args(argv)

    if args.input_file and not Path(args.input_file).is_file():
        print(f"入力ファイルがありません: {args.input_file}", file=sys.stderr)
        return 1

    out = Path(args.output_path)
    src = Path(__file__).resolve().parent.parent / "tobe_src" / out.name
    if not src.is_file():
        print(f"To-Beソースがありません: {src}", file=sys.stderr)
        return 1

    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, out)  # 바이트 보존(Shift-JIS 그대로)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
