#!/usr/bin/env bash
# 웹 UI 기동 래퍼 (Phase 5, D-028). CLI의 run.sh와 짝.
#
# Core/Interface 분리(D-006)대로 GUI도 Core(run_full_comparison)를 재사용하는 얇은 인터페이스다.
# 브라우저는 src/gui/web.py:main()이 기동 직후 자동으로 연다(§④).
#
# 사용 예:
#   POSTGRES_PASSWORD=devpw ./run_gui.sh
#   GUI_PORT=8080 POSTGRES_PASSWORD=devpw ./run_gui.sh
set -euo pipefail
cd "$(dirname "$0")"
exec python3 -m src.gui.web "$@"
