#!/usr/bin/env bash
# 데모 진입점 — 크로스플랫폼 run_demo.py로 위임(D-060). Linux/macOS 편의 래퍼.
#   POSTGRES_PASSWORD=<자기비번> ./samples/complete/run_demo.sh
# Windows(또는 직접): python3 samples/complete/run_demo.py
exec python3 "$(dirname "$0")/run_demo.py" "$@"
