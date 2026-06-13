#!/usr/bin/env python3
"""mock 업무 셸(파일흐름) — tobe_src/<출력명>을 --output-path로 바이트 복사(실 배치 자리)."""
import shutil
import sys
from pathlib import Path


def main(argv):
    out = None
    i = 1
    while i < len(argv):
        if argv[i] == "--output-path" and i + 1 < len(argv):
            out = Path(argv[i + 1]); i += 2
        else:
            i += 1
    if out is None:
        print("no --output-path", file=sys.stderr); return 2
    src = Path(__file__).resolve().parents[5] / "tobe_src" / out.name
    if not src.is_file():
        print(f"tobe_src なし: {src}", file=sys.stderr); return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
