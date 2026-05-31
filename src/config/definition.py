"""정의 파일(test_definition.yaml)을 읽어 ShellDefinition 목록으로 변환한다.

설계 결정은 DECISIONS.md D-021·D-022 참조:
- Boss 기획 7.1 구조의 경량 버전: test_id / input / execution / output / (comparison_rules·success_criteria).
- 입력·출력 각각 type: "database" | "file" 로 두 흐름을 데이터 주도로 라우팅한다.
- 프로토 미사용 필드(comparison_rules·success_criteria·parameters 등)는 읽되 무시한다(자리만 유지).
- test_id는 3자리 zero-pad 문자열로 정규화(D-019 4항과 일관, 프로토 한정).

print/CLI 출력 금지(CLAUDE.md 3-1). 실패 시 DefinitionError를 던지고 상위(CLI)에서 처리한다.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from src.core.models import ShellDefinition

_VALID_IO_TYPES = ("database", "file")

# test_id zero-pad 자리수.
# === 인수인계 시 재검토 대상 ===
# 3자리 고정은 시연용 샘플(001~010) 기준. 실 운영 명명 규칙이 다르면 교체.
_TEST_ID_WIDTH = 3


class DefinitionError(Exception):
    """정의 파일 로드/검증 실패. CLI가 잡아 즉시 종료 + 에러 메시지로 처리한다."""


def load_definitions(path: Path) -> list[ShellDefinition]:
    """정의 파일을 읽어 ShellDefinition 목록을 반환한다.

    파일 없음·YAML 파싱 실패·필수 키 누락·잘못된 type은 모두 DefinitionError.
    """
    path = Path(path)
    if not path.is_file():
        raise DefinitionError(f"정의 파일을 찾을 수 없습니다: {path}")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise DefinitionError(f"정의 파일 YAML 파싱 실패: {path}\n{exc}") from exc

    if not isinstance(raw, dict) or not isinstance(raw.get("tests"), list):
        raise DefinitionError(f"정의 파일 최상위에 'tests' 리스트가 필요합니다: {path}")

    tests = raw["tests"]
    if not tests:
        raise DefinitionError(f"정의 파일 'tests'가 비어 있습니다: {path}")

    return [_build_definition(entry, idx, path) for idx, entry in enumerate(tests, start=1)]


def _build_definition(entry: object, idx: int, path: Path) -> ShellDefinition:
    """tests 리스트의 한 항목을 ShellDefinition으로 검증·변환한다."""
    if not isinstance(entry, dict):
        raise DefinitionError(f"{idx}번째 test 항목이 매핑이 아닙니다: {path}")

    test_id = _pad_test_id(_req(entry, "test_id", idx, path))
    inp = _req_block(entry, "input", idx, path)
    execution = _req_block(entry, "execution", idx, path)
    out = _req_block(entry, "output", idx, path)

    input_type = _req_choice(inp, "type", _VALID_IO_TYPES, test_id, path)
    output_type = _req_choice(out, "type", _VALID_IO_TYPES, test_id, path)

    definition = ShellDefinition(
        test_id=test_id,
        test_name=str(entry.get("test_name", test_id)),
        input_type=input_type,
        input_csv=str(_req(inp, "csv", idx, path)),
        output_type=output_type,
        expected_output_csv=str(_req(entry, "expected_output_csv", idx, path)),
        shell_program=str(_req(execution, "shell_program", idx, path)),
        timeout_seconds=int(execution.get("timeout", 60)),
        input_table=_opt_str(inp, "table"),
        input_dest_dir=_opt_str(inp, "dest_dir"),
        output_table=_opt_str(out, "table"),
        output_file=_opt_str(out, "file"),
        export_csv=_opt_str(out, "export_csv"),
    )
    _validate_io(definition, path)
    return definition


def _validate_io(d: ShellDefinition, path: Path) -> None:
    """입력/출력 type별로 필요한 키가 채워졌는지 검증한다."""
    if d.input_type == "database" and not d.input_table:
        raise DefinitionError(f"[{d.test_id}] input.type=database이면 input.table이 필요합니다: {path}")
    if d.output_type == "database" and not (d.output_table and d.export_csv):
        raise DefinitionError(
            f"[{d.test_id}] output.type=database이면 output.table과 output.export_csv가 필요합니다: {path}"
        )
    if d.output_type == "file" and not d.output_file:
        raise DefinitionError(f"[{d.test_id}] output.type=file이면 output.file이 필요합니다: {path}")


def _req(block: dict, key: str, idx: object, path: Path) -> object:
    value = block.get(key)
    if value is None:
        raise DefinitionError(f"[{idx}] 필수 키 '{key}' 누락: {path}")
    return value


def _req_block(entry: dict, key: str, idx: object, path: Path) -> dict:
    block = entry.get(key)
    if not isinstance(block, dict):
        raise DefinitionError(f"[{idx}] '{key}' 블록이 없거나 매핑이 아닙니다: {path}")
    return block


def _req_choice(block: dict, key: str, choices: tuple, idx: object, path: Path) -> str:
    value = str(_req(block, key, idx, path))
    if value not in choices:
        raise DefinitionError(f"[{idx}] '{key}'는 {choices} 중 하나여야 합니다(받은 값: {value}): {path}")
    return value


def _opt_str(block: dict, key: str) -> str | None:
    value = block.get(key)
    return None if value is None else str(value)


def _pad_test_id(value: object) -> str:
    """test_id를 3자리 zero-pad 문자열로. 정수/문자열 모두 수용, 비숫자는 그대로."""
    text = str(value).strip()
    return text.zfill(_TEST_ID_WIDTH) if text.isdigit() else text
