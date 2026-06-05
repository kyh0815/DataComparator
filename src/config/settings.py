"""config.yaml을 읽어 Config 객체로 변환하는 설정 로더.

클라이언트마다 다른 값(인코딩·경로·DB 접속 등)은 코드에 박지 않고 여기서 로드한다
(CLAUDE.md 3-3). DB 비밀번호는 yaml의 `password_env` 키가 가리키는 환경변수에서 읽는다.

설계 결정은 DECISIONS.md D-019 참조:
- 필수 키(`paths`, `database`)는 누락 시 ConfigError. 나머지는 기본값 허용.
- `shells`는 `ids`가 `range`를 이긴다(구체 > 일반). `range`는 inclusive.
- 셸 ID는 3자리 zero-pad 문자열로 정규화. (3자리 고정은 프로토 한정 — 인수 시 재검토.)
- 상대경로는 config 파일의 디렉토리 기준으로 resolve.
- 비밀번호 환경변수가 없으면 password=None (접속 시점에 실패 처리).
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from src.core.models import (
    BatchConfig,
    Config,
    DatabaseConfig,
    OutputConfig,
)

# 셸 ID zero-pad 자리수.
# === 인수인계 시 재검토 대상 ===
# 3자리 고정은 시연용 샘플(001.csv ~ 010.csv) 기준. 실 운영에서 셸 수/명명 규칙이
# 다르면(예: 4자리, 비숫자 ID) 이 값 또는 정규화 로직을 교체해야 한다.
_SHELL_ID_WIDTH = 3

_DEFAULT_ENCODING = "Shift_JIS"
_DEFAULT_SHELL_RANGE = [1, 10]  # inclusive (1~10 → 10개)


class ConfigError(Exception):
    """설정 파일 로드/검증 실패. CLI가 잡아 즉시 종료 + 에러 메시지로 처리한다."""


def load_config(path: Path) -> Config:
    """config.yaml을 읽어 Config 객체로 변환한다.

    필수 키(`paths`, `database`) 누락·파일 없음·YAML 파싱 실패 시 ConfigError를 던진다.
    상대경로는 config 파일이 위치한 디렉토리 기준으로 해석한다.
    """
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"설정 파일을 찾을 수 없습니다: {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"설정 파일 YAML 파싱 실패: {path}\n{exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"설정 파일 최상위는 매핑이어야 합니다: {path}")

    base_dir = path.resolve().parent

    encoding = raw.get("encoding", _DEFAULT_ENCODING)

    paths = _require(raw, "paths", path)
    asis_input_dir = _resolve_path(paths, "asis_input_dir", base_dir, path)
    asis_output_dir = _resolve_path(paths, "asis_output_dir", base_dir, path)
    tobe_output_dir = _resolve_path(paths, "tobe_output_dir", base_dir, path)
    report_dir = _resolve_path(paths, "report_dir", base_dir, path)

    # 선택적 경로 (D-021·D-022). 없으면 None — 파일 흐름/정의 파일 미사용으로 동작.
    tobe_input_dir = _resolve_optional_path(paths, "tobe_input_dir", base_dir)
    definition_file = _resolve_optional_path(paths, "definition_file", base_dir)

    database = _build_database(_require(raw, "database", path), path)
    batch = _build_batch(raw.get("batch") or {}, base_dir)
    output = _build_output(raw.get("output") or {})
    shell_ids = _normalize_shell_ids(raw.get("shells") or {}, path)

    return Config(
        encoding=encoding,
        asis_input_dir=asis_input_dir,
        asis_output_dir=asis_output_dir,
        tobe_output_dir=tobe_output_dir,
        report_dir=report_dir,
        database=database,
        batch=batch,
        shell_ids=shell_ids,
        output=output,
        tobe_input_dir=tobe_input_dir,
        definition_file=definition_file,
    )


def _require(raw: dict, key: str, path: Path) -> dict:
    """필수 매핑 블록을 꺼낸다. 없거나 매핑이 아니면 ConfigError."""
    block = raw.get(key)
    if not isinstance(block, dict):
        raise ConfigError(f"필수 설정 블록 '{key}'가 없거나 매핑이 아닙니다: {path}")
    return block


def _resolve_path(block: dict, key: str, base_dir: Path, path: Path) -> Path:
    """경로 키를 꺼내 base_dir 기준으로 절대경로화한다. 없으면 ConfigError."""
    value = block.get(key)
    if value is None:
        raise ConfigError(f"필수 경로 키 'paths.{key}'가 없습니다: {path}")
    candidate = Path(str(value))
    return candidate if candidate.is_absolute() else (base_dir / candidate).resolve()


def _resolve_optional_path(block: dict, key: str, base_dir: Path) -> Path | None:
    """선택적 경로 키를 base_dir 기준 절대경로화한다. 없으면 None(예외 아님)."""
    value = block.get(key)
    if value is None:
        return None
    candidate = Path(str(value))
    return candidate if candidate.is_absolute() else (base_dir / candidate).resolve()


def _build_database(block: dict, path: Path) -> DatabaseConfig:
    """database 블록을 DatabaseConfig로. 비밀번호는 password_env 환경변수에서 해석."""
    missing = [k for k in ("host", "port", "dbname", "user") if block.get(k) is None]
    if missing:
        raise ConfigError(
            f"필수 database 키 누락: {', '.join(missing)} ({path})"
        )
    password_env = block.get("password_env", "POSTGRES_PASSWORD")
    return DatabaseConfig(
        host=str(block["host"]),
        port=int(block["port"]),
        dbname=str(block["dbname"]),
        user=str(block["user"]),
        password=os.environ.get(password_env),  # 없으면 None — 접속 시점에 실패 처리
        password_env=password_env,
    )


def _build_batch(block: dict, base_dir: Path) -> BatchConfig:
    """batch 블록을 BatchConfig로. 누락 키는 dataclass 기본값(=동봉 stub 계약)을 따른다(C6).

    command(argv 토큰 리스트)·env(추가 env 토큰)·success_exit_code·clean_flag를 config로 외부화한다.
    """
    defaults = BatchConfig()
    stub_path = block.get("stub_path")
    command = block.get("command")
    env = block.get("env")
    clean_flag = block.get("clean_flag", defaults.clean_flag)
    return BatchConfig(
        type=str(block.get("type", defaults.type)),
        stub_path=_abs_path(stub_path, base_dir, defaults.stub_path),
        timeout_seconds=int(block.get("timeout_seconds", defaults.timeout_seconds)),
        command=[str(t) for t in command] if command is not None else list(defaults.command),
        env={str(k): str(v) for k, v in env.items()} if isinstance(env, dict) else dict(defaults.env),
        success_exit_code=int(block.get("success_exit_code", defaults.success_exit_code)),
        clean_flag=None if clean_flag is None else str(clean_flag),
    )


def _abs_path(value: object | None, base_dir: Path, default: Path) -> Path:
    """경로 값을 base_dir 기준 절대경로로. 값이 없으면 default를 그대로 쓴다."""
    if value is None:
        return default
    candidate = Path(str(value))
    return candidate if candidate.is_absolute() else (base_dir / candidate).resolve()


def _build_output(block: dict) -> OutputConfig:
    """output 블록을 OutputConfig로. 누락 키는 dataclass 기본값을 따른다."""
    defaults = OutputConfig()
    return OutputConfig(
        cli_color=bool(block.get("cli_color", defaults.cli_color)),
        cli_verbose=bool(block.get("cli_verbose", defaults.cli_verbose)),
        report_with_bom=bool(block.get("report_with_bom", defaults.report_with_bom)),
    )


def _normalize_shell_ids(block: dict, path: Path) -> list[str]:
    """shells 블록을 셸 ID 문자열 목록으로 정규화한다.

    `ids`가 `range`보다 우선한다(구체 > 일반). 둘 다 없으면 기본 range [1,10].
    `range: [a, b]`는 inclusive. 모든 ID는 3자리 zero-pad 문자열로 통일.
    """
    ids = block.get("ids")
    if ids is not None:
        if not isinstance(ids, list) or not ids:
            raise ConfigError(f"shells.ids는 비어있지 않은 리스트여야 합니다: {path}")
        return [_pad_shell_id(i) for i in ids]

    rng = block.get("range", _DEFAULT_SHELL_RANGE)
    if not (isinstance(rng, list) and len(rng) == 2):
        raise ConfigError(f"shells.range는 [시작, 끝] 형식이어야 합니다: {path}")
    start, end = int(rng[0]), int(rng[1])
    if start > end:
        raise ConfigError(f"shells.range 시작이 끝보다 큽니다: {rng} ({path})")
    return [_pad_shell_id(n) for n in range(start, end + 1)]  # inclusive


def _pad_shell_id(value: object) -> str:
    """셸 ID를 3자리 zero-pad 문자열로. 정수/문자열 모두 수용."""
    text = str(value).strip()
    return text.zfill(_SHELL_ID_WIDTH) if text.isdigit() else text


def parse_shell_selector(value: str) -> list[str]:
    """CLI `--shells` 문자열을 셸 ID 목록으로 파싱한다(인터페이스용, T3-3).

    `"1-10"`(inclusive 범위) 또는 `"001,002,005"`(쉼표 목록)를 받는다. zero-pad·inclusive·
    검증 규칙은 `_normalize_shell_ids`를 **그대로 재사용**해 config 셸 규칙과 드리프트를 막는다.
    형식 오류는 ConfigError(CLI가 잡아 즉시 종료 + 메시지).
    """
    text = value.strip()
    if not text:
        raise ConfigError("--shells 값이 비어 있습니다.")
    if "-" in text:
        parts = [p.strip() for p in text.split("-")]
        if len(parts) != 2 or not all(p.isdigit() for p in parts):
            raise ConfigError(f"--shells 범위는 'N-M'(정수) 형식이어야 합니다: {value}")
        block = {"range": [int(parts[0]), int(parts[1])]}
    else:
        ids = [p.strip() for p in text.split(",") if p.strip()]
        if not ids:
            raise ConfigError(f"--shells 목록이 비어 있습니다: {value}")
        block = {"ids": ids}
    return _normalize_shell_ids(block, Path("--shells"))  # Path는 에러 메시지용 라벨
