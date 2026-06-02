"""연결 설정 — DB 접속 테스트(읽기전용) + config.yaml 자동 저장 (Phase 6).

화면에서 받은 **비-비밀 접속정보**로 두 가지를 한다:
- `test_connection`: 실제로 접속해 `SELECT 1` + (조건부) 입력/출력 테이블 존재 확인. **읽기전용**
  — DDL/쓰기 없음(운영 DB 오염 방지). 비밀번호는 **받지 않고** 서버 env(password_env)에서만
  끌어온다(모델 A, D-019 §6 확장). env에 없으면 .pgpass/trust 등에 위임.
- `save_connection`: DB 접속·인코딩·경로만 config.yaml에 **원자적 저장**(+.bak 백업). 검증 정의값
  (테이블·배치·타입)은 여기 저장하지 않는다 — models.Config 필드가 아니라 ShellDefinition 값이라
  Core 무수정을 깨므로, /verify/run 폼으로 전달한다(A).

검증 정의값을 config.yaml에 넣지 않으므로 password도 절대 기록하지 않는다(password_env 이름만).
print/CLI 출력 금지(CLAUDE.md 3-1) — 결과는 dict로 돌려 web 계층이 렌더한다.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import psycopg2
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLE_CONFIG = _REPO_ROOT / "config.yaml.example"

# 접속 테스트 타임아웃(초). 잘못된 host/port에 오래 매달리지 않도록 짧게.
_CONNECT_TIMEOUT = 3


class ConnectionError_(Exception):
    """연결 설정 저장 실패 등. web 계층이 잡아 사용자 메시지로 보낸다."""


def test_connection(
    *,
    host: str,
    port: object,
    dbname: str,
    user: str,
    password_env: str = "POSTGRES_PASSWORD",
    input_type: str = "database",
    output_type: str = "file",
    input_table: str | None = None,
    output_table: str | None = None,
) -> dict:
    """접속 + SELECT 1 + (조건부) 테이블 존재를 확인하고 결과 dict를 돌려준다(읽기전용).

    반환: {ok, message, checks:[{name, ok, detail?}]}. 비밀번호는 env[password_env]에서만 읽는다.
    """
    password = os.environ.get(password_env)  # 모델 A: 폼이 아니라 env에서만.

    try:
        port_int = int(port)
    except (TypeError, ValueError):
        return {"ok": False, "message": f"ポートが数値ではありません: {port}", "checks": []}

    try:
        conn = psycopg2.connect(
            host=host,
            port=port_int,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=_CONNECT_TIMEOUT,
        )
    except Exception as exc:  # noqa: BLE001 — 접속 실패는 메시지로 안내
        hint = ""
        if password is None:
            hint = (
                f"（環境変数 {password_env} が未設定です。"
                "パスワードはツールに保存せず、DBAが環境変数/.pgpass に設定します）"
            )
        return {"ok": False, "message": f"DB接続に失敗しました: {exc}{hint}", "checks": []}

    checks: list[dict] = []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        checks.append({"name": "DB接続 (SELECT 1)", "ok": True})

        # B: type이 database인 쪽의 테이블만 확인(파일 흐름엔 테이블 확인 금지 — 오탐 방지).
        if input_type == "database" and input_table:
            checks.append(_table_check(conn, input_table, "入力テーブル"))
        if output_type == "database" and output_table:
            checks.append(_table_check(conn, output_table, "出力テーブル"))
    finally:
        conn.close()

    ok = all(c["ok"] for c in checks)
    message = "接続OK — すべての確認に成功しました。" if ok else "接続はできましたが、一部の確認に失敗しました。"
    return {"ok": ok, "message": message, "checks": checks}


def _table_check(conn, table_name: str, label: str) -> dict:
    """테이블 존재를 information_schema에서 확인한다(읽기전용).

    G: public 스키마 가정(스키마 한정 미적용). loader/exporter와 동일하게 table_name만으로
    조회하므로, 동명 테이블이 여러 스키마에 있으면 모호 — schema-qualify는 deferred(설치 시).
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = %s LIMIT 1",
            (table_name,),
        )
        exists = cur.fetchone() is not None
    return {
        "name": f"{label} '{table_name}' の存在",
        "ok": exists,
        "detail": None if exists else "テーブルが見つかりません",
    }


def save_connection(
    config_path: str,
    *,
    host: str,
    port: object,
    dbname: str,
    user: str,
    password_env: str,
    encoding: str,
) -> Path:
    """DB 접속·인코딩만 config.yaml에 원자적 저장한다(+.bak). password는 절대 쓰지 않는다(모델 A).

    기존 config.yaml이 있으면 그걸 템플릿으로(다른 블록 보존), 없으면 config.yaml.example을
    템플릿으로 쓴다. 경로·batch·shells·output 블록은 그대로 유지한다(검증 정의값은 미저장, A).
    """
    cp = Path(config_path)
    template = cp if cp.is_file() else _EXAMPLE_CONFIG
    if not template.is_file():
        raise ConnectionError_(f"テンプレート設定が見つかりません: {template}")

    raw = yaml.safe_load(template.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ConnectionError_(f"設定ファイルの最上位がマッピングではありません: {template}")

    raw["encoding"] = encoding
    db = raw.get("database")
    if not isinstance(db, dict):
        db = {}
    db.update({"host": host, "port": int(port), "dbname": dbname, "user": user, "password_env": password_env})
    db.pop("password", None)  # 모델 A: 평문 비밀번호는 절대 기록하지 않는다.
    raw["database"] = db

    new_text = yaml.safe_dump(raw, allow_unicode=True, sort_keys=False)

    # 원자적 쓰기: 기존 파일은 .bak로 백업 → tmp에 쓴 뒤 os.replace로 교체.
    if cp.is_file():
        shutil.copyfile(cp, cp.with_name(cp.name + ".bak"))
    tmp = cp.with_name(cp.name + ".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    os.replace(tmp, cp)
    return cp
