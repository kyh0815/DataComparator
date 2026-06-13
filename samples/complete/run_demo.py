#!/usr/bin/env python3
"""complete 단일 정본 데모셋 — 한 방 실행 진입점(크로스플랫폼, D-060).

  python3 samples/complete/run_demo.py        # Linux/macOS
  py samples\\complete\\run_demo.py            # Windows

run_demo.sh의 Python 포트 — bash·psql 외부 명령 의존을 없애 Windows에서도 그대로 돈다.
스키마 적용도 psycopg2로(psql 불요). 비교 판정·CLI는 src.cli.main을 그대로 호출한다.

★접속 값(host/port/dbname/user)은 samples/complete/config.yaml의 database 블록이 단일 진실(D-048).
  비번만 POSTGRES_PASSWORD env(평문 금지). DB 미접속이면 DB CK(019/020)는 프리플라이트가 거부한다.
단계: ① 데이터·mock 셸 생성 → ② (DB 접속되면) 스키마 적용 + DB CK 골든 → ③ 프리플라이트 → ④ 検証実行 → ⑤ 試験成績書.
"""

from __future__ import annotations

import runpy
import shutil
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_ROOT))

from src.config.settings import load_config  # noqa: E402


def _run_module(mod: str, argv: list[str]) -> None:
    """`python -m mod argv`와 동치 — 같은 인터프리터 안에서 실행(서브프로세스·셸 불요)."""
    saved = sys.argv
    sys.argv = [mod] + argv
    try:
        runpy.run_module(mod, run_name="__main__", alter_sys=True)
    except SystemExit as exc:  # CLI는 SystemExit(코드)로 끝난다 — 0이 아니면 전파
        if exc.code:
            raise
    finally:
        sys.argv = saved


def _apply_schema(config, sql_path: Path) -> None:
    """스키마 SQL을 psycopg2로 통째 실행(psql 불요 — 크로스플랫폼)."""
    from tools.make_golden import _connect  # 지연 import(psycopg2)

    conn = _connect(config)
    try:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


def _db_reachable(config) -> bool:
    try:
        from tools.make_golden import _connect

        conn = _connect(config)
        conn.close()
        return True
    except Exception:  # noqa: BLE001 — 접속 불가면 DB 단계 건너뜀(프리플라이트가 거부)
        return False


def main() -> int:
    cfg_path = _HERE / "config.yaml"
    # config.yaml은 .gitignore(자격 보호) — 없으면 커밋된 완전판 example에서 복사(안전망).
    if not cfg_path.is_file():
        shutil.copyfile(_HERE / "config.yaml.example", cfg_path)
        print("[complete] config.yaml 생성(example 복사). ★database 블록을 자기 환경에 맞게 편집하세요(port 등).")
    try:
        config = load_config(cfg_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[complete] ✖ config を読めません: {cfg_path} — {exc}", file=sys.stderr)
        return 1
    db = config.database

    print("[complete] ① 데이터·mock 셸 생성")
    _run_module("samples.complete.make_complete_data", [])

    if db.password and _db_reachable(config):
        print(f"[complete] ② スキーマ適用 + DB CK 골든 생성 (config: {db.user}@{db.host}:{db.port}/{db.dbname})")
        _apply_schema(config, _ROOT / "db" / "schema.sql")
        _apply_schema(config, _ROOT / "db" / "schema_realistic.sql")
        _run_module("samples.complete.make_db_golden", [])
    else:
        print(f"[complete] ② DB 미접속(config: {db.host}:{db.port}/{db.dbname}) — DB CK(019/020)는 프리플라이트가 거부.")
        print("           DB로 돌리려면: createdb 후 POSTGRES_PASSWORD env + config의 database 값 확인.")

    cfg = str(cfg_path)
    print("[complete] ③ プリフライト")
    _run_module("src.cli.main", ["--preflight", "--config", cfg])
    print("[complete] ④ 検証実行")
    _run_module("src.cli.main", ["--config", cfg])
    print("[complete] ⑤ 試験成績書")
    _run_module("src.cli.main", ["--evidence", "--config", cfg])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
