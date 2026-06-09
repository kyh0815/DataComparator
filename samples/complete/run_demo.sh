#!/usr/bin/env bash
# complete 단일 정본 데모셋 — 한 방 실행 진입점(구 run_realistic.sh 대체).
#   POSTGRES_PASSWORD=<자기비번> ./samples/complete/run_demo.sh
#
# ★접속 값(host/port/dbname/user)은 samples/complete/config.yaml의 database 블록이 단일 진실(D-048).
#   스키마 적용·골든·프리플라이트·실행 전부 그 값으로 붙는다. 비번만 POSTGRES_PASSWORD env(평문 금지).
#   팀원은 config의 database를 자기 값으로 채우면 자기 로컬에서 돈다(createdb는 최초 1회 수동).
# 단계: ① 데이터·mock 셸 생성 → ② (DB 접속되면) 스키마 적용 + DB CK 골든 생성
#       → ③ 프리플라이트 → ④ 検証実行 → ⑤ 試験成績書.
# DB가 없으면 프리플라이트가 DB CK(019/020) 접속불가로 전건 거부(C3 게이트). 파일 22건만 보려면 DB 없이도 OK 메시지.
set -euo pipefail
cd "$(dirname "$0")/../.."   # repo 루트

CFG="samples/complete/config.yaml"

# config.yaml은 .gitignore(자격 보호) — 없으면 커밋된 완전판 example에서 복사(안전망). ★자기 DB값으로 편집할 것.
if [ ! -f "$CFG" ]; then
  cp "samples/complete/config.yaml.example" "$CFG"
  echo "[complete] config.yaml 생성(example 복사). ★database 블록을 자기 환경에 맞게 편집하세요(port 등)."
fi

# ★접속 값은 config가 단일 진실 — psql도 config에서 host/port/dbname/user를 읽는다(env·하드코딩 금지).
# config을 못 읽으면(없음·YAML오류) 조용한 기본값 대신 명확히 멈춘다.
DBVALS="$(python3 -c "from src.config.settings import load_config as L; d=L('$CFG').database; print(d.host, d.port, d.dbname, d.user)" 2>/dev/null)" || true
if [ -z "$DBVALS" ]; then
  echo "[complete] ✖ config を読めません: $CFG — database 블록(host/port/dbname/user)을 확인하세요." >&2
  exit 1
fi
read -r DBHOST DBPORT DBNAME DBUSER <<< "$DBVALS"

echo "[complete] ① 데이터·mock 셸 생성"
python3 samples/complete/make_complete_data.py

if [ -n "${POSTGRES_PASSWORD:-}" ] && command -v psql >/dev/null \
   && PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DBHOST" -p "$DBPORT" -U "$DBUSER" -d "$DBNAME" -tAc "select 1" >/dev/null 2>&1; then
  echo "[complete] ② スキーマ適用 + DB CK 골든 생성 (config: ${DBUSER}@${DBHOST}:${DBPORT}/${DBNAME})"
  PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DBHOST" -p "$DBPORT" -U "$DBUSER" -d "$DBNAME" -v ON_ERROR_STOP=1 -q -f db/schema.sql
  PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DBHOST" -p "$DBPORT" -U "$DBUSER" -d "$DBNAME" -v ON_ERROR_STOP=1 -q -f db/schema_realistic.sql
  python3 samples/complete/make_db_golden.py
else
  echo "[complete] ② DB 미접속(config: ${DBHOST}:${DBPORT}/${DBNAME}) — DB CK(019/020)는 프리플라이트가 거부."
  echo "           DB로 돌리려면: createdb 후 POSTGRES_PASSWORD env + config의 database 값 확인."
fi

echo "[complete] ③ プリフライト"
python3 -m src.cli.main --preflight --config "$CFG"
echo "[complete] ④ 検証実行"
python3 -m src.cli.main --config "$CFG"
echo "[complete] ⑤ 試験成績書"
python3 -m src.cli.main --evidence --config "$CFG"
