#!/usr/bin/env bash
# complete 단일 정본 데모셋 — 한 방 실행 진입점(구 run_realistic.sh 대체).
#   POSTGRES_PASSWORD=devpw PGPORT=5433 ./samples/complete/run_demo.sh
#
# 단계: ① 데이터·mock 셸 생성 → ② (DB 있으면) 스키마 적용 + DB CK 골든 생성
#       → ③ 프리플라이트 → ④ 検証実行 → ⑤ 試験成績書.
# DB가 없으면 프리플라이트가 DB CK(019/020) 접속불가로 전건 거부(C3 게이트). 파일 16건만 보려면 DB 없이도 OK 메시지.
set -euo pipefail
cd "$(dirname "$0")/../.."   # repo 루트

CFG="samples/complete/config.yaml"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5433}"

# config.yaml은 .gitignore(자격 보호) — 없으면 커밋된 완전판 example에서 자동 provisioning(fresh clone 대응).
if [ ! -f "$CFG" ]; then
  cp "samples/complete/config.yaml.example" "$CFG"
  echo "[complete] config.yaml 생성(example 복사). DB값은 자기 환경에 맞게 수정 가능 — 비번은 POSTGRES_PASSWORD env."
fi

echo "[complete] ① 데이터·mock 셸 생성"
python3 samples/complete/make_complete_data.py

if [ -n "${POSTGRES_PASSWORD:-}" ] && command -v psql >/dev/null \
   && PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$PGHOST" -p "$PGPORT" -U postgres -d compare_proto -tAc "select 1" >/dev/null 2>&1; then
  echo "[complete] ② スキーマ適用 + DB CK 골든 생성 (dc-pg ${PGHOST}:${PGPORT})"
  PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$PGHOST" -p "$PGPORT" -U postgres -d compare_proto -v ON_ERROR_STOP=1 -q -f db/schema.sql
  PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$PGHOST" -p "$PGPORT" -U postgres -d compare_proto -v ON_ERROR_STOP=1 -q -f db/schema_realistic.sql
  python3 samples/complete/make_db_golden.py
else
  echo "[complete] ② DB 미접속 — DB CK(019/020)는 프리플라이트가 거부(파일 16건 검증은 별도 환경에서)."
fi

echo "[complete] ③ プリフライト"
python3 -m src.cli.main --preflight --config "$CFG"
echo "[complete] ④ 検証実行"
python3 -m src.cli.main --config "$CFG"
echo "[complete] ⑤ 試験成績書"
python3 -m src.cli.main --evidence --config "$CFG"
