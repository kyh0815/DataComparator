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

from src.core.models import InputSpec, OutputSpec, ShellDefinition

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

    inputs = _build_inputs(inp, test_id, path)  # D-033: 다중 입력(신 tables[] / 구 단일)
    outputs = _build_outputs(entry, test_id, path)  # D-033 P2: 다중 출력(신 outputs[] / 구 단일)
    fi, fo = inputs[0], outputs[0]  # 하위호환 단일 필드는 1차 입력/출력에서 파생

    definition = ShellDefinition(
        test_id=test_id,
        test_name=str(entry.get("test_name", test_id)),
        input_type=fi.type,
        input_csv=fi.csv,
        output_type=fo.type,
        expected_output_csv=fo.expected,
        shell_program=str(_req(execution, "shell_program", idx, path)),
        timeout_seconds=int(execution.get("timeout", 60)),
        setup=_opt_str(execution, "setup"),  # P0: 입력 적재 전 준비 SQL/스크립트(선택)
        shell_group=_opt_str(execution, "shell_group"),  # B: 업무 그룹 태그(선택, 전달만). 비면 None

        input_table=fi.table,
        input_dest_dir=fi.dest_dir,
        output_table=fo.table,
        output_file=fo.file,
        export_csv=fo.export_as,
        inputs=inputs,
        outputs=outputs,
    )
    _validate_io(definition, path)
    return definition


def _build_outputs(entry: dict, test_id: str, path: Path) -> list[OutputSpec]:
    """output을 OutputSpec 리스트로. 신형 `outputs:[...]`(각 expected) 또는 구형 단일(`output`+`expected_output_csv`).

    구형 키 `export_csv`는 OutputSpec.export_as로 매핑(의미 동일). 각 출력은 expected 필수.
    """
    rows = entry.get("outputs")
    if rows is not None:
        if not isinstance(rows, list) or not rows:
            raise DefinitionError(f"[{test_id}] outputs는 비어있지 않은 리스트여야 합니다: {path}")
        specs = []
        for j, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                raise DefinitionError(f"[{test_id}] outputs[{j}] 항목이 매핑이 아닙니다: {path}")
            otype = str(row.get("type", ""))
            if otype not in _VALID_IO_TYPES:
                raise DefinitionError(
                    f"[{test_id}] outputs[{j}].type는 {_VALID_IO_TYPES} 중 하나여야 합니다: {path}"
                )
            specs.append(OutputSpec(
                type=otype,
                expected=str(_req(row, "expected", f"{test_id}.output[{j}]", path)),
                table=_opt_str(row, "table"),
                export_as=_opt_str(row, "export_as"),
                file=_opt_str(row, "file"),
                name=_opt_str(row, "name"),
                expected_dir=_opt_str(row, "expected_dir"),  # #7 As-Is 출력 격납 패스
                tobe_dir=_opt_str(row, "tobe_dir"),  # #11 To-Be 출력 격납 패스
                **_compare_kwargs(row, f"{test_id}.output[{j}]", path),  # P0 §3: compare 블록
            ))
        return specs
    # 구형 단일: output 블록 + 최상위 expected_output_csv
    out = _req_block(entry, "output", test_id, path)
    otype = _req_choice(out, "type", _VALID_IO_TYPES, test_id, path)
    return [OutputSpec(
        type=otype,
        expected=str(_req(entry, "expected_output_csv", test_id, path)),
        table=_opt_str(out, "table"),
        export_as=_opt_str(out, "export_csv"),  # 구형 키
        file=_opt_str(out, "file"),
        expected_dir=_opt_str(out, "expected_dir"),
        tobe_dir=_opt_str(out, "tobe_dir"),
    )]


_VALID_COMPARE_MODES = ("byte", "text", "record")


def _compare_kwargs(row: dict, where: object, path: Path) -> dict:
    """출력 행의 `compare` 블록을 OutputSpec 옵션 kwargs로 변환한다(없으면 빈 dict=byte 기본).

    mode 값만 여기서 검증(byte|text|record). 나머지 정밀 검증(key 누락 경고·이름+무헤더 등)은
    C3 프리플라이트가 CSV 좌표로 보고한다(V3 C3).
    """
    c = row.get("compare")
    if c is None:
        return {}
    if not isinstance(c, dict):
        raise DefinitionError(f"[{where}] compare 블록이 매핑이 아닙니다: {path}")
    mode = _opt_str(c, "mode")
    if mode is not None and mode not in _VALID_COMPARE_MODES:
        raise DefinitionError(
            f"[{where}] compare.mode는 {_VALID_COMPARE_MODES} 중 하나여야 합니다(받은 값: {mode}): {path}"
        )
    return {
        "compare_mode": mode,
        "key": _opt_str(c, "key"),
        "encoding": _opt_str(c, "encoding"),
        "mask": _opt_str(c, "mask"),
        "tolerance": _opt_str(c, "tolerance"),
        "layout": _opt_str(c, "layout"),
        "delimiter": _opt_str(c, "delimiter"),
        "has_header": _opt_bool(c, "has_header"),
        "normalize": _opt_str(c, "normalize"),
    }


def _build_inputs(inp: dict, test_id: str, path: Path) -> list[InputSpec]:
    """input 블록을 InputSpec 리스트로. 신형 `tables:[...]` 또는 구형 단일(`type/csv/table`) 모두 수용.

    신형은 항목별 type을 허용(없으면 input.type 상속). 구형은 1개짜리 리스트로 정규화한다.
    """
    default_type = str(inp.get("type", "database"))
    rows = inp.get("tables")
    if rows is not None:
        if not isinstance(rows, list) or not rows:
            raise DefinitionError(f"[{test_id}] input.tables는 비어있지 않은 리스트여야 합니다: {path}")
        specs = []
        for j, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                raise DefinitionError(f"[{test_id}] input.tables[{j}] 항목이 매핑이 아닙니다: {path}")
            itype = str(row.get("type", default_type))
            if itype not in _VALID_IO_TYPES:
                raise DefinitionError(
                    f"[{test_id}] input.tables[{j}].type는 {_VALID_IO_TYPES} 중 하나여야 합니다: {path}"
                )
            specs.append(InputSpec(
                csv=str(_req(row, "csv", f"{test_id}.input[{j}]", path)),
                type=itype,
                table=_opt_str(row, "table"),
                dest_dir=_opt_str(row, "dest_dir"),  # #7-4 To-Be 격납 패스
                src_dir=_opt_str(row, "src_dir"),  # #4 As-Is 입력 격납 패스
                dest_name=_opt_str(row, "dest_name"),  # #7-3 To-Be 격납 파일명
                in_encoding=_opt_str(row, "in_encoding"),  # P0: 입력 적재 인코딩 override
            ))
        return specs
    # 구형 단일
    itype = _req_choice(inp, "type", _VALID_IO_TYPES, test_id, path)
    return [InputSpec(
        csv=str(_req(inp, "csv", test_id, path)),
        type=itype,
        table=_opt_str(inp, "table"),
        dest_dir=_opt_str(inp, "dest_dir"),
        src_dir=_opt_str(inp, "src_dir"),
        dest_name=_opt_str(inp, "dest_name"),
        in_encoding=_opt_str(inp, "in_encoding"),
    )]


def _validate_io(d: ShellDefinition, path: Path) -> None:
    """입력/출력 type별로 필요한 키가 채워졌는지 검증한다(inputs[]·outputs[] 전건)."""
    for i, spec in enumerate(d.inputs, start=1):
        if spec.type == "database" and not spec.table:
            raise DefinitionError(
                f"[{d.test_id}] input(테이블 {i})이 database이면 table이 필요합니다: {path}"
            )
    for k, o in enumerate(d.outputs, start=1):
        if o.type == "database" and not (o.table and o.export_as):
            raise DefinitionError(
                f"[{d.test_id}] output({k})=database이면 table과 export_as(export_csv)가 필요합니다: {path}"
            )
        if o.type == "file" and not o.file:
            raise DefinitionError(f"[{d.test_id}] output({k})=file이면 file이 필요합니다: {path}")
        if not o.expected:
            raise DefinitionError(f"[{d.test_id}] output({k})은 expected(정답 파일)가 필요합니다: {path}")


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


def _opt_bool(block: dict, key: str) -> bool:
    """has_header 등 불리언. YAML bool 또는 "true"/"1"/"yes" 문자열을 참으로."""
    value = block.get(key)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "y") if value is not None else False


def _pad_test_id(value: object) -> str:
    """test_id를 3자리 zero-pad 문자열로. 정수/문자열 모두 수용, 비숫자는 그대로."""
    text = str(value).strip()
    return text.zfill(_TEST_ID_WIDTH) if text.isdigit() else text
