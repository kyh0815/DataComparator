#!/usr/bin/env bash
# 얇은 Shell 기동 래퍼 (Boss "Shell 스크립트로 자동화 배치 처리" 기대 충족, D-022).
#
# 실제 오케스트레이션 로직은 Python Core(CLI)에 있다(Core/Interface 분리, D-006).
# 이 스크립트는 그 진입점을 Shell에서 한 줄로 기동하기 위한 위임 래퍼일 뿐이다.
#
# === 인수인계 시 교체 포인트 ===
# 실 운영의 배치 운영 방식(cron/jobnet 등)에 맞춰 이 래퍼를 조정한다. CLI 계약은 유지.
#
# 사용 예:
#   ./run.sh --config ./config.yaml
#   ./run.sh --config ./config.yaml --shells 1-10 --verbose
set -euo pipefail
cd "$(dirname "$0")"
exec python -m src.cli.main "$@"
