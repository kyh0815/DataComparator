#!/bin/sh
# mock 멀티출력 셸 — 자기 출력들을 tobe_src에서 --output-path 디렉토리로 복사(실 배치는 자기 I/O 고정).
OUT=""
while [ $# -gt 0 ]; do case "$1" in --output-path) OUT="$2"; shift 2 ;; *) shift ;; esac; done
[ -n "$OUT" ] || { echo "no --output-path" >&2; exit 2; }
DIR="$(dirname "$OUT")"
SRC="$(cd "$(dirname "$0")/../../../../../tobe_src" && pwd)"
mkdir -p "$DIR"
for f in ck023_meisai.csv ck023_shukei.csv; do
  [ -f "$SRC/$f" ] || { echo "tobe_src なし: $SRC/$f" >&2; exit 1; }
  cp "$SRC/$f" "$DIR/$f"
done
