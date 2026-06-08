"""연결 설정 — DB 접속 테스트(읽기전용) + config.yaml 자동 저장 (Phase 6).

화면에서 받은 **비-비밀 접속정보**로 두 가지를 한다:
- `test_connection`: 실제로 접속해 `SELECT 1` + (조건부) 입력/출력 테이블 존재 확인. **읽기전용**
  — DDL/쓰기 없음(운영 DB 오염 방지). 비밀번호는 **받지 않고** 서버 env(password_env)에서만
  끌어온다(모델 A, D-019 §6 확장). env에 없으면 .pgpass/trust 등에 위임.
- `save_connection`: DB 접속·인코딩만 config.yaml에 **원자적 저장**(+.bak 백업). 검증 정의값
  (테이블·배치·타입)은 여기 저장하지 않는다 — models.Config 필드가 아니라 ShellDefinition 값이라
  Core 무수정을 깨므로, **정의 파일이 정본**이다(T7-3 일원화, DEFINITION_SPEC).

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
) -> dict:
    """접속(SELECT 1) + public 스키마 테이블 목록을 취득해 결과 dict를 돌려준다(읽기전용).

    반환: {ok, message, checks:[{name, ok, detail}], tables:[...]}. 비밀번호는 env[password_env]에서만.
    테이블 존재 확인은 따로 하지 않는다 — 화면이 이 목록으로 드롭다운을 채워 사용자가 고르므로,
    "목록에서 고른 = 존재"가 자명해진다(자유입력·오탐 제거). G: public 스키마 가정(schema-qualify는 deferred).
    """
    password = os.environ.get(password_env)  # 모델 A: 폼이 아니라 env에서만.

    try:
        port_int = int(port)
    except (TypeError, ValueError):
        return {"ok": False, "message": f"ポートが数値ではありません: {port}", "checks": [], "tables": []}

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
        return {"ok": False, "message": f"DB接続に失敗しました: {exc}{hint}", "checks": [], "tables": []}

    checks: list[dict] = []
    tables: list[str] = []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        checks.append({"name": "DB接続 (SELECT 1)", "ok": True, "detail": f"{host}:{port_int}"})

        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name"
            )
            tables = [row[0] for row in cur.fetchall()]
        checks.append({"name": "テーブル取得", "ok": len(tables) > 0, "detail": f"{len(tables)}件"})
    finally:
        conn.close()

    ok = all(c["ok"] for c in checks)
    message = (
        "接続OK — テーブル一覧を取得しました。" if ok
        else "接続できましたが、public スキーマにテーブルがありません。"
    )
    return {"ok": ok, "message": message, "checks": checks, "tables": tables}


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


_PATH_KEYS = (
    "asis_input_dir", "asis_output_dir", "tobe_input_dir",
    "tobe_output_dir", "report_dir", "definition_file",
)


def save_paths(config_path: str, **path_values: object) -> Path:
    """paths(디렉토리·정의파일 경로)만 config.yaml에 원자적 저장한다(+.bak). 다른 블록은 보존.

    save_connection과 같은 원자적 쓰기. 빈칸으로 온 키는 **기존값 유지**(지우지 않음).
    경로 형식만 다루고, 실제 폴더 존재 여부는 事前点検(preflight)이 실행 전에 검증한다(저장 ≠ 검증 분리).
    """
    cp = Path(config_path)
    template = cp if cp.is_file() else _EXAMPLE_CONFIG
    if not template.is_file():
        raise ConnectionError_(f"テンプレート設定が見つかりません: {template}")
    raw = yaml.safe_load(template.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ConnectionError_(f"設定ファイルの最上位がマッピングではありません: {template}")

    paths = raw.get("paths")
    if not isinstance(paths, dict):
        paths = {}
    for k in _PATH_KEYS:
        v = str(path_values.get(k, "") or "").strip()
        if v:  # 빈칸은 기존값 유지(지우지 않음)
            paths[k] = v
    raw["paths"] = paths

    new_text = yaml.safe_dump(raw, allow_unicode=True, sort_keys=False)
    if cp.is_file():
        shutil.copyfile(cp, cp.with_name(cp.name + ".bak"))
    tmp = cp.with_name(cp.name + ".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    os.replace(tmp, cp)
    return cp
