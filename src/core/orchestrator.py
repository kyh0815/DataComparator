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
from datetime import datetime

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
from .paths import input_dest_dir, input_source_path, output_asis_path
from .reporter import generate_report
from .runner import run_batch, run_setup
from . import store


class OrchestratorError(Exception):
    """실행 전체를 중단시키는 치명적 오류(DB 접속 실패 등). CLI가 잡아 즉시 종료한다(SPEC 8)."""


def run_full_comparison(
    config: Config,
    on_progress: Callable[[ProgressEvent], None] | None = None,
    shell_ids: list[str] | None = None,
    *,
    resume: bool = False,
    retry_failed: bool = False,
) -> RunSummary:
    """E2E 전체 실행. 정의 파일을 로드해 셸을 순차 처리하고 RunSummary를 반환한다.

    shell_ids(--shells 명시 선택, D-026)가 주어지면 해당 test_id만 처리한다(None=전체, D-024).
    resume(이어하기)=미실행+ERROR만, retry_failed(재시험)=직전 NG+ERROR만 — 둘 다 체크포인트
    기준으로 셸을 추린다(HANDOFF_V3 C5). 셋은 인터페이스에서 상호배타.
    셸 1건 종료 직후 결과를 체크포인트(JSONL)에 즉시 기록한다(중단 시 부분 상태 보존, req2).
    정의 파일 누락·DB 접속 실패는 전파(fatal); 개별 셸 오류는 ERROR 결과로 흡수한다.
    """
    definitions = _load_definitions(config)
    shell_ids = _resolve_selection(definitions, config, shell_ids, resume, retry_failed)
    if shell_ids is not None:
        definitions = _select_definitions(definitions, shell_ids)
    total = len(definitions)
    conn = _open_connection_if_needed(definitions, config)
    cp_path = store.checkpoint_path(config.report_dir)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")  # 결과 출처(시각). C4가 행별로 표기

    results: list[ComparisonResult] = []
    try:
        for index, definition in enumerate(definitions, start=1):
            _emit(
                on_progress,
                ProgressEvent(ProgressKind.SHELL_START, definition.test_id, index, total),
            )
            shell_results = _process_shell(definition, config, conn, index, total, on_progress)
            results.extend(shell_results)  # D-033 P2: 셸당 결과 N건(출력 단위)
            store.append_shell(cp_path, definition.test_id, shell_results, run_id=run_id)  # C5 즉시 영속
            for r in shell_results:  # 출력마다 SHELL_DONE(GUI가 출력별로 그림)
                _emit(
                    on_progress,
                    ProgressEvent(
                        ProgressKind.SHELL_DONE, definition.test_id, index, total, result=r
                    ),
                )
    finally:
        if conn is not None:
            conn.close()

    return generate_report(results, config.report_dir)


def _resolve_selection(
    definitions: list[ShellDefinition],
    config: Config,
    shell_ids: list[str] | None,
    resume: bool,
    retry_failed: bool,
) -> list[str] | None:
    """부분 실행 모드를 체크포인트 기준 shell_ids로 환원한다(HANDOFF_V3 C5).

    resume/retry_failed는 직전 run(체크포인트)이 있어야 의미 — 없으면 fatal. 명시 shell_ids가
    함께 오면(인터페이스가 막지만 방어적으로) 그대로 둔다(셋은 본래 상호배타).
    """
    if not (resume or retry_failed):
        return shell_ids
    cp_path = store.checkpoint_path(config.report_dir)
    if not store.has_checkpoint(cp_path):
        raise OrchestratorError(
            "체크포인트가 없습니다 — resume/retry는 직전 실행이 있어야 합니다(먼저 1회 실행)."
        )
    if resume:
        return store.shells_to_resume(cp_path, [d.test_id for d in definitions])
    return store.shells_to_retry(cp_path)


def _process_shell(
    definition: ShellDefinition,
    config: Config,
    conn,
    index: int,
    total: int,
    on_progress: Callable[[ProgressEvent], None] | None,
) -> list[ComparisonResult]:
    """한 셸을 Load → Run → (출력마다) Compare로 처리하고 결과 리스트를 반환한다(D-033 P2).

    배치 1회 실행 후 outputs[]마다 정답과 비교 → 출력 단위 결과 N건. 결과의 shell_id는 정의의
    test_id로, output_name은 출력 라벨로 못박는다(compare_files는 파일명 파생이라). 예외는 셸 단위
    ERROR 1건. finally에서 셸 단위 트랜잭션 경계를 정리한다(D-023 ②).
    """
    step = "load"
    try:
        _load_step(definition, config, conn)
        _emit_step(on_progress, definition, index, total, "load", "OK")

        step = "run"
        resolved = run_batch(definition, config, conn, clean=False)  # [(OutputSpec, tobe_path)]
        _emit_step(on_progress, definition, index, total, "run", "OK")

        step = "compare"
        results: list[ComparisonResult] = []
        multi = len(definition.outputs) > 1  # 단일 출력은 output_name=None(리포트 '-'·화면 라벨 없음)
        for out, tobe_path in resolved:
            asis_path = output_asis_path(out, config)  # #5·#7 항목별 경로 override 반영
            opts = out.compare_options  # V3 C2: 출력별 모드·정규화 옵션
            if opts.encoding is None:  # 출력 인코딩 미지정이면 config 전역
                opts.encoding = config.encoding
            r = compare_files(asis_path, tobe_path, opts)
            r.shell_id = definition.test_id  # 파일명 파생 대신 셸 ID로 못박음
            r.output_name = out.label if multi else None
            results.append(r)
        _emit_step(on_progress, definition, index, total, "compare", _worst_status(results))
        return results
    except Exception as exc:  # noqa: BLE001 — 어떤 셸 오류도 ERROR로 흡수(SPEC 3-1·8)
        _emit_step(on_progress, definition, index, total, step, "ERROR")
        return [ComparisonResult(
            shell_id=definition.test_id,
            status=ComparisonStatus.ERROR,
            error_message=str(exc),
        )]
    finally:
        # D-023 ②: exporter read 트랜잭션(ACCESS SHARE 락)을 해제해 다음 셸 TRUNCATE가 막히지
        # 않게 한다. DB 입력 적재분은 _load_step에서 이미 commit됐으므로 rollback은 안전하다.
        if conn is not None:
            conn.rollback()


def _load_step(definition: ShellDefinition, config: Config, conn) -> None:
    """Load 단계: 셸의 입력 **여러 건**을 각각 DB 적재 또는 파일 복사로 처리한다(D-033 다중입력).

    한 배치가 여러 테이블을 조인해 읽으므로, inputs[]의 각 항목을 대응 테이블/디렉토리에 적재한다.
    DB 적재분은 stub(별도 connection)이 보도록 즉시 commit(D-023 ①). 모든 입력 적재 후 배치 실행.
    setup(준비 SQL/스크립트)이 있으면 적재 전 1회 먼저 실행한다(마스터·참조 테이블·시퀀스).
    """
    run_setup(definition, config, conn)  # 입력 적재 전 1회(setup 비면 무동작)
    for spec in definition.inputs:
        src = input_source_path(spec, config)  # #2·#4 항목별 As-Is 원천 경로
        if spec.type == "database":
            load_input_csv(src, conn, spec.table, encoding=spec.in_encoding or config.encoding)
            conn.commit()  # D-023 ①
        else:
            # 파일 입력은 항목별 To-Be 격납 디렉토리/파일명으로 복사(#7-3·#7-4).
            # 복사처(여기)=Runner 읽기처가 paths 헬퍼를 공유 → 드리프트 차단.
            copy_input_file(src, input_dest_dir(spec, config), dest_name=spec.dest_name)


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


def _worst_status(results: list[ComparisonResult]) -> str:
    """compare STEP 표시용 — 출력 중 OK 아닌 게 있으면 그 상태값, 모두 OK면 'OK'."""
    for r in results:
        if r.status != ComparisonStatus.OK:
            return r.status.value
    return "OK"


def _needs_db(definition: ShellDefinition) -> bool:
    """이 셸이 DB connection을 필요로 하는가(입력 DB 적재·출력 export·또는 .sql setup)."""
    setup_sql = bool(definition.setup) and str(definition.setup).lower().endswith(".sql")
    return (
        setup_sql
        or any(s.type == "database" for s in definition.inputs)
        or any(o.type == "database" for o in definition.outputs)
    )


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
