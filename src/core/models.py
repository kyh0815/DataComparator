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
    stub_path: Path = Path("./stub_batch/run_batch.py")
    timeout_seconds: int = 60


@dataclass
class OutputConfig:
    """CLI 출력·리포트 관련 옵션."""

    cli_color: bool = True
    cli_verbose: bool = False
    report_with_bom: bool = True


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
