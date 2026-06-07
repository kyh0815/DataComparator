#!/bin/sh
# mock 업무 셸(파일흐름) — tobe_src/<출력명>을 --output-path로 바이트 복사(실 배치 자리).
OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --output-path) OUT="$2"; shift 2 ;;
    *) shift ;;
  esac
done
[ -n "$OUT" ] || { echo "no --output-path" >&2; exit 2; }
SRC="$(cd "$(dirname "$0")/../../../../../tobe_src" && pwd)/$(basename "$OUT")"
[ -f "$SRC" ] || { echo "tobe_src なし: $SRC" >&2; exit 1; }
mkdir -p "$(dirname "$OUT")"
cp "$SRC" "$OUT"
