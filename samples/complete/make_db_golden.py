#!/usr/bin/env python3
"""complete 데모셋 — DB 출력 CK(019/020)의 As-Is 정답(골든)만 clean 경로로 생성한다.

make_golden은 전건 대상이라 파일 CK의 의도된 NG 골든(003·005·009)을 덮어쓴다. 여기선
**DB 출력이 있는 CK만** 골든을 만든다(파일 CK 골든은 make_complete_data.py가 만든 그대로).
오케스트레이터와 동일한 Load→run_batch(clean=True)→exporter 경로(make_golden._make_one 재사용)라
골든과 To-Be가 같은 직렬화를 타 false-NG가 구조적으로 불가능(D-027).

DB 필요(dc-pg). 실행:
  python3 samples/complete/make_db_golden.py   # (Windows: py …)
선행: db/schema.sql + db/schema_realistic.sql 적용, make_complete_data.py 실행, test_definition.yaml 생성.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.config.definition import load_definitions  # noqa: E402
from src.config.settings import load_config  # noqa: E402
from tools.make_golden import _connect, _make_one  # noqa: E402


def main() -> int:
    config = load_config(Path(__file__).resolve().parent / "config.yaml")
    definitions = load_definitions(config.definition_file)
    db_defs = [d for d in definitions if any(o.type == "database" for o in d.outputs)]
    if not db_defs:
        print("DB 출력 CK 없음 — 생성할 골든 없음.")
        return 0
    conn = _connect(config)
    try:
        for d in db_defs:
            try:
                for dest in _make_one(d, config, conn):
                    print(f"[db-golden] {d.test_id} → {dest}")
            finally:
                conn.rollback()  # exporter read 트랜잭션 해제(D-023 ②)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
