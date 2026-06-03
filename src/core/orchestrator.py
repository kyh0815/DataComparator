"""E2E 오케스트레이션 — 정의 파일을 따라 셸을 1개씩 순차 처리한다 (T3-1).

CLI/GUI 공통 진입점. 각 셸에 대해 Load → Run → Compare를 호출하고,
진행 상황은 on_progress 콜백(ProgressEvent)으로만 알린다(Core print 금지, CLAUDE.md 3-1).

설계 결정은 DECISIONS.md D-023·D-024 참조:
- 테스트 목록·메타데이터는 **정의 파일(test_definition.yaml)이 정본**. 없으면 DefinitionError로
  즉시 종료한다(D-021의 range/ids 폴백은 D-022 구조 도입으로 무효 — D-024).
- **셸 단위 트랜잭션 경계 필수**(D-023):
  ① DB 입력은 load_input_csv 후 즉시 commit해야 stub(별도 connection)이 본다.
  ② 한 셸 종료 시 conn.rollback()으로 exporter의 read 트랜잭션(tobe_result ACCESS SHARE 락)을
     해제해야 다음 셸 stub의 TRUNCATE tobe_result가 막히지 않는다.
- DB가 필요한 셸이 하나라도 있으면 루프 진입 전 connection을 1회 연다. **접속 실패는 즉시
  종료(fatal)**(SPEC 8). DB가 전혀 필요 없으면 connect하지 않는다(파일 전용 실행 견고).
- 한 셸의 예외는 그 셸 ERROR로 기록하고 다음 셸을 계속 진행한다(SPEC 3-1·8).
"""

from __future__ import annotations

from collections.abc import Callable

import psycopg2

from src.config.definition import DefinitionError, load_definitions

from .comparator import compare_files
from .loader import copy_input_file, load_input_csv
from .models import (
    ComparisonResult,
    ComparisonStatus,
    Config,
    ProgressEvent,
    ProgressKind,
    RunSummary,
    ShellDefinition,
)
from .reporter import generate_report
from .runner import resolve_input_dir, run_batch


class OrchestratorError(Exception):
    """실행 전체를 중단시키는 치명적 오류(DB 접속 실패 등). CLI가 잡아 즉시 종료한다(SPEC 8)."""


def run_full_comparison(
    config: Config,
    on_progress: Callable[[ProgressEvent], None] | None = None,
    shell_ids: list[str] | None = None,
) -> RunSummary:
    """E2E 전체 실행. 정의 파일을 로드해 셸을 순차 처리하고 RunSummary를 반환한다.

    on_progress가 주어지면 셸 시작·단계 완료·셸 완료마다 ProgressEvent를 던진다(없어도 동작).
    shell_ids가 주어지면(인터페이스의 --shells 명시 선택, D-026) 정의 중 해당 test_id만 처리한다
    (None=전체, D-024). 정의 파일 순서를 유지하며, 정의에 없는 id 요청은 DefinitionError(fatal).
    정의 파일 누락·DB 접속 실패도 전파(fatal); 개별 셸 오류는 ERROR 결과로 흡수한다.
    """
    definitions = _load_definitions(config)
    if shell_ids is not None:
        definitions = _select_definitions(definitions, shell_ids)
    total = len(definitions)
    conn = _open_connection_if_needed(definitions, config)

    results: list[ComparisonResult] = []
    try:
        for index, definition in enumerate(definitions, start=1):
            _emit(
                on_progress,
                ProgressEvent(ProgressKind.SHELL_START, definition.test_id, index, total),
            )
            result = _process_shell(definition, config, conn, index, total, on_progress)
            results.append(result)
            _emit(
                on_progress,
                ProgressEvent(
                    ProgressKind.SHELL_DONE, definition.test_id, index, total, result=result
                ),
            )
    finally:
        if conn is not None:
            conn.close()

    return generate_report(results, config.report_dir)


def _process_shell(
    definition: ShellDefinition,
    config: Config,
    conn,
    index: int,
    total: int,
    on_progress: Callable[[ProgressEvent], None] | None,
) -> ComparisonResult:
    """한 셸을 Load → Run → Compare로 처리하고 ComparisonResult를 반환한다.

    예외는 ERROR 결과로 매핑한다(다음 셸 진행). finally에서 셸 단위 트랜잭션 경계를 정리한다.
    """
    step = "load"
    try:
        _load_step(definition, config, conn)
        _emit_step(on_progress, definition, index, total, "load", "OK")

        step = "run"
        tobe_path = run_batch(definition, config, conn, clean=False)
        _emit_step(on_progress, definition, index, total, "run", "OK")

        step = "compare"
        asis_path = config.asis_output_dir / definition.expected_output_csv
        result = compare_files(asis_path, tobe_path, encoding=config.encoding)
        _emit_step(on_progress, definition, index, total, "compare", result.status.value)
        return result
    except Exception as exc:  # noqa: BLE001 — 어떤 셸 오류도 ERROR로 흡수(SPEC 3-1·8)
        _emit_step(on_progress, definition, index, total, step, "ERROR")
        return ComparisonResult(
            shell_id=definition.test_id,
            status=ComparisonStatus.ERROR,
            error_message=str(exc),
        )
    finally:
        # D-023 ②: exporter read 트랜잭션(ACCESS SHARE 락)을 해제해 다음 셸 TRUNCATE가 막히지
        # 않게 한다. DB 입력 적재분은 _load_step에서 이미 commit됐으므로 rollback은 안전하다.
        if conn is not None:
            conn.rollback()


def _load_step(definition: ShellDefinition, config: Config, conn) -> None:
    """Load 단계: 셸의 입력 **여러 건**을 각각 DB 적재 또는 파일 복사로 처리한다(D-033 다중입력).

    한 배치가 여러 테이블을 조인해 읽으므로, inputs[]의 각 항목을 대응 테이블/디렉토리에 적재한다.
    DB 적재분은 stub(별도 connection)이 보도록 즉시 commit(D-023 ①). 모든 입력 적재 후 배치 실행.
    """
    for spec in definition.inputs:
        src = config.asis_input_dir / spec.csv
        if spec.type == "database":
            load_input_csv(src, conn, spec.table, encoding=config.encoding)
            conn.commit()  # D-023 ①
        else:
            # 파일 입력은 모두 tobe_input_dir로 복사(복사처=Runner 읽기처 공유 헬퍼 → 드리프트 차단).
            copy_input_file(src, resolve_input_dir(definition, config))


def _load_definitions(config: Config) -> list[ShellDefinition]:
    """정의 파일을 로드한다. 정의 파일은 정본이며 없으면 fatal(D-024)."""
    if config.definition_file is None:
        raise DefinitionError(
            "정의 파일이 설정되지 않았습니다(paths.definition_file). "
            "정의 파일은 실행 단위의 정본입니다 — D-021의 range/ids 폴백은 D-022 구조 "
            "도입으로 무효화되었습니다(D-024)."
        )
    return load_definitions(config.definition_file)


def _select_definitions(
    definitions: list[ShellDefinition], shell_ids: list[str]
) -> list[ShellDefinition]:
    """--shells 명시 선택(D-026): 정의 중 요청 test_id만 정의 파일 순서대로 추린다.

    정의에 없는 id는 silent drop하지 않고 DefinitionError(fatal)로 누락 id를 알린다(자가검증 ④).
    """
    available = {d.test_id for d in definitions}
    unknown = [s for s in shell_ids if s not in available]
    if unknown:
        raise DefinitionError(
            f"요청한 셸 ID가 정의 파일에 없습니다: {unknown} (정의 보유: {sorted(available)})"
        )
    requested = set(shell_ids)
    return [d for d in definitions if d.test_id in requested]


def _open_connection_if_needed(definitions: list[ShellDefinition], config: Config):
    """DB가 필요한 셸이 있으면 connection을 1회 연다. 접속 실패는 fatal(SPEC 8).

    DB가 전혀 필요 없으면 None을 반환한다(파일 전용 실행은 DB 없이 동작).
    """
    if not any(_needs_db(d) for d in definitions):
        return None

    db = config.database
    try:
        return psycopg2.connect(
            host=db.host,
            port=db.port,
            dbname=db.dbname,
            user=db.user,
            password=db.password,
        )
    except Exception as exc:  # noqa: BLE001
        raise OrchestratorError(f"DB 접속 실패: {exc}") from exc


def _needs_db(definition: ShellDefinition) -> bool:
    """이 셸이 DB connection을 필요로 하는가(입력 중 하나라도 DB 적재, 또는 출력 export)."""
    return any(s.type == "database" for s in definition.inputs) or definition.output_type == "database"


def _emit(
    on_progress: Callable[[ProgressEvent], None] | None, event: ProgressEvent
) -> None:
    """콜백이 있으면 이벤트를 전달한다(없으면 무시)."""
    if on_progress is not None:
        on_progress(event)


def _emit_step(
    on_progress: Callable[[ProgressEvent], None] | None,
    definition: ShellDefinition,
    index: int,
    total: int,
    step: str,
    step_status: str,
) -> None:
    """STEP 이벤트를 만들어 전달한다."""
    _emit(
        on_progress,
        ProgressEvent(
            ProgressKind.STEP,
            definition.test_id,
            index,
            total,
            step=step,
            step_status=step_status,
        ),
    )
