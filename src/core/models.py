"""Core 전체에서 공유하는 데이터 구조 정의.

인터페이스 간 *공통 어휘*. 모든 비교 결과는 여기 정의된 dataclass로 표현하고,
CLI/GUI는 이 객체들을 받아 출력만 한다 (CLAUDE.md 3-2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ComparisonStatus(str, Enum):
    """한 셸 비교의 판정 상태.

    str 상속이라 CSV 직렬화 시 값이 그대로 문자열로 쓰인다.
    """

    OK = "OK"
    NG = "NG"
    MISSING_ASIS = "MISSING_ASIS"
    MISSING_TOBE = "MISSING_TOBE"
    ERROR = "ERROR"


@dataclass
class ShellPair:
    """비교 단위. As-Is 출력 파일과 To-Be 출력 파일의 한 쌍."""

    shell_id: str  # 예: "001"
    asis_output_path: Path
    tobe_output_path: Path


@dataclass
class DiffLine:
    """한 줄 차이의 상세."""

    line_number: int
    asis_content: str
    tobe_content: str


@dataclass
class ComparisonResult:
    """한 셸의 비교 결과. diff_lines는 status가 NG일 때만 채워진다."""

    shell_id: str
    status: ComparisonStatus
    diff_lines: list[DiffLine] = field(default_factory=list)
    error_message: str | None = None


@dataclass
class RunSummary:
    """전체 실행의 요약. CLI 최종 출력과 리포트의 근거."""

    total: int
    ok_count: int
    ng_count: int
    error_count: int
    missing_count: int  # MISSING_ASIS + MISSING_TOBE 합산 (D-016)
    results: list[ComparisonResult]
    report_csv_path: Path


class ProgressKind(str, Enum):
    """오케스트레이터가 인터페이스(CLI/GUI)에 던지는 진행 이벤트의 종류 (ARCHITECTURE 5-3 옵션 A).

    Core는 print 금지(CLAUDE.md 3-1)이므로 진행 상황을 구조화 이벤트로만 알리고,
    실제 출력 포맷팅은 인터페이스가 담당한다.
    """

    SHELL_START = "shell_start"  # 한 셸 처리 시작 ([index/total])
    STEP = "step"  # 한 단계 완료 (load / run / compare)
    SHELL_DONE = "shell_done"  # 한 셸의 결과 확정


@dataclass
class ProgressEvent:
    """진행 보고 콜백(on_progress)에 전달되는 단일 이벤트.

    SPEC 5-1의 "입력 적재 / 배치 실행 / 결과 비교" 3단계에 STEP이 매핑된다.
    (출력=database의 다운로드는 run_batch 내부 exporter라 'run' 단계에 포함된다.)
    """

    kind: ProgressKind
    shell_id: str
    index: int  # 1-based 셸 순번
    total: int  # 전체 셸 수
    step: str | None = None  # STEP에만: "load" | "run" | "compare"
    step_status: str | None = None  # STEP에만: "OK" | "ERROR" | ComparisonStatus 값
    result: ComparisonResult | None = None  # SHELL_DONE에만: 확정된 비교 결과


@dataclass
class DatabaseConfig:
    """PostgreSQL 접속 정보. 비밀번호는 환경변수에서 해석해 채운다."""

    host: str
    port: int
    dbname: str
    user: str
    password: str | None = None  # password_env가 가리키는 환경변수에서 해석된 값
    password_env: str = "POSTGRES_PASSWORD"


@dataclass
class BatchConfig:
    """배치 실행 설정. type은 'stub'(현재) 또는 'netcobol'(추후)."""

    type: str = "stub"
    # DEPRECATED(D-023): 셸별 stub은 test_definition.yaml의 execution.shell_program이 선택한다.
    # 이 단일 stub_path는 더 이상 Runner가 쓰지 않으나, 기존 설정/테스트 호환을 위해 남겨둔다.
    # 정식 제거는 별도 정리 Task(연관 test_settings 단언도 함께 갱신).
    stub_path: Path = Path("./stub_batch/run_batch.py")
    timeout_seconds: int = 60


@dataclass
class OutputConfig:
    """CLI 출력·리포트 관련 옵션."""

    cli_color: bool = True
    cli_verbose: bool = False
    report_with_bom: bool = True


@dataclass
class ShellDefinition:
    """정의 파일(test_definition.yaml)의 테스트 1건 메타데이터 (D-021·D-022).

    Boss 기획 7.1 구조의 경량 버전. 입력·출력 각각 'database'|'file' 유형을 갖는다.
    프로토 미사용 필드(comparison_rules·success_criteria 등)는 자리만 채운다.
    """

    test_id: str  # 3자리 zero-pad 셸 ID (예: "001")
    test_name: str
    input_type: str  # "database" | "file"
    input_csv: str  # asis_input_dir 기준 입력 CSV 파일명
    output_type: str  # "database" | "file"
    expected_output_csv: str  # asis_output_dir 기준 정답지 파일명
    shell_program: str  # 기동할 stub(=shell) 경로
    timeout_seconds: int = 60
    input_table: str | None = None  # input_type == database
    input_dest_dir: str | None = None  # input_type == file (복사 대상; 없으면 config.tobe_input_dir)
    output_table: str | None = None  # output_type == database (결과 테이블)
    output_file: str | None = None  # output_type == file (배치가 직접 생성하는 파일명)
    export_csv: str | None = None  # output_type == database (다운로드 CSV 파일명)


@dataclass
class Config:
    """실행 설정 전체. config.yaml을 로드해 만든다 (T0-3에서 채움)."""

    encoding: str
    asis_input_dir: Path
    asis_output_dir: Path
    tobe_output_dir: Path
    report_dir: Path
    database: DatabaseConfig
    batch: BatchConfig
    shell_ids: list[str]  # range/ids를 해석한 최종 셸 ID 목록 (예: ["001", "002", ...])
    output: OutputConfig
    # D-021·D-022로 추가 (선택적; 없으면 None → range/ids 폴백, 파일흐름 미사용)
    tobe_input_dir: Path | None = None  # 파일 입력(야간 배치) raw 복사 대상
    definition_file: Path | None = None  # 셸별 정의 파일 경로
