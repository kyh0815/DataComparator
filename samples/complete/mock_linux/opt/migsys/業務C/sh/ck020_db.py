#!/usr/bin/env python3
"""mock 업무 셸(DB) — repo stub_batch/의 실 DB stub을 호출(§1: DB 로직은 stub_batch에만)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
raise SystemExit(
    subprocess.run([sys.executable, str(ROOT / "stub_batch" / "run_settlement.py"), *sys.argv[1:]]).returncode
)
