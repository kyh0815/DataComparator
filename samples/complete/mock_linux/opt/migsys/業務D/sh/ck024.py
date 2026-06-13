#!/usr/bin/env python3
"""mock 멀티출력 셸 — 자기 출력들을 tobe_src에서 --output-path 디렉토리로 복사(실 배치는 자기 I/O 고정)."""
import shutil
import sys
from pathlib import Path

NAMES = ['ck024_zandaka.csv', 'ck024_error.txt']


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
    src_dir = Path(__file__).resolve().parents[5] / "tobe_src"
    out.parent.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        src = src_dir / name
        if not src.is_file():
            print(f"tobe_src なし: {src}", file=sys.stderr); return 1
        shutil.copyfile(src, out.parent / name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
