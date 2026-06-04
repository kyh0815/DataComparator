#!/usr/bin/env bash
# 현실형 테스트 환경 셋업 + 실행 (Phase 7 다중 입출력).
#   PGPORT=5433 POSTGRES_PASSWORD=devpw ./run_realistic.sh
#
# 단계: ① rt_* 테이블 생성 → ② As-Is 입력 샘플(Shift-JIS) 생성 → ③ 골든 생성(stub --clean)
#       → ④ 現新比較 실행(리포트 + 화면 요약). --skip-golden 으로 ③ 생략 가능.
set -euo pipefail
cd "$(dirname "$0")"

: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD 환경변수를 설정하세요 (예: devpw)}"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
CONFIG="./config.realistic.yaml"

# config의 host/port를 환경에 맞춰 덮어쓴 실효 설정을 repo 루트에 생성(상대경로 해석 위해 루트).
EFFECTIVE="./.config.realistic.effective.yaml"
sed -e "s/host: localhost/host: ${PGHOST}/" -e "s/port: 5432/port: ${PGPORT}/" "$CONFIG" > "$EFFECTIVE"
echo "[realistic] 실효 설정: $EFFECTIVE (host=${PGHOST} port=${PGPORT})"

echo "[realistic] ① rt_* 테이블 생성 (db/schema_realistic.sql)"
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$PGHOST" -p "$PGPORT" -U postgres -d compare_proto \
    -v ON_ERROR_STOP=1 -q -f db/schema_realistic.sql

echo "[realistic] ② As-Is 입력 샘플 생성 (Shift-JIS)"
python3 tools/make_realistic_samples.py

if [ "${1:-}" != "--skip-golden" ]; then
  echo "[realistic] ③ 골든(As-Is 출력 정답) 생성 — stub --clean 경로"
  python3 tools/make_golden.py --config "$EFFECTIVE"
fi

echo "[realistic] ④ 現新比較 실행"
python3 -m src.cli.main --config "$EFFECTIVE"
