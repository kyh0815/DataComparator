#!/bin/sh
# mock 업무 셸(DB) — repo stub_batch/의 실 DB stub을 exec(§1: DB 로직은 stub_batch에만).
ROOT="$(cd "$(dirname "$0")/../../../../../../.." && pwd)"
exec python3 "$ROOT/stub_batch/run_settlement.py" "$@"
