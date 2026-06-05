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
    """한 (셸, 출력)의 비교 결과. diff_lines는 status가 NG일 때만 채워진다.

    D-033 P2: 한 셸이 출력 여러 건이면 출력마다 결과 1건(output_name으로 구분). 단일 출력이면
    output_name=None(또는 단일 라벨). 집계는 출력 단위(결과 1건 = 출력 1건).
    """

    shell_id: str
    status: ComparisonStatus
    diff_lines: list[DiffLine] = field(default_factory=list)
    error_message: str | None = None
    output_name: str | None = None  # D-033: 출력 식별자(다중 출력). 단일/배치오류는 None


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
class InputSpec:
    """한 셸이 적재할 입력 1건 (기획 7.1 input.tables[] 복원, D-033).

    한 셸이 여러 테이블/파일을 입력으로 받을 수 있어(배치가 여러 테이블 조인) inputs 리스트의 한 항목.
    경로 필드(src_dir·dest_dir)는 **항목별 선택적 override**(D-036): 비면 config 공통 디렉토리.
    """

    csv: str  # #2 As-Is 입력데이터 명 (파일명, asis_input_dir 기준)
    type: str = "database"  # #3 As-Is 입력데이터 종류: "database" | "file"
    table: str | None = None  # #7-1 type==database: To-Be 격납 테이블(적재 대상)
    dest_dir: str | None = None  # #7-4 type==file: To-Be 격납 패스(없으면 config.tobe_input_dir)
    src_dir: str | None = None  # #4 As-Is 입력 격납 패스 override(없으면 config.asis_input_dir)
    dest_name: str | None = None  # #7-3 type==file: To-Be 격납 파일명(없으면 csv 그대로)
    in_encoding: str | None = None  # 입력 적재 인코딩 override(없으면 config 전역). P0 신규


def _split_semi(raw: str | None) -> list[str]:
    """셀 내부 다중값(`;` 구분)을 비지 않은 토큰 리스트로. CSV `,`와 충돌 방지(V3 C2)."""
    if not raw:
        return []
    return [t.strip() for t in str(raw).split(";") if t.strip()]


def _parse_layout(raw: str | None) -> list[tuple[int, int]]:
    """고정길이 layout "start:end;start:end" → [(start,end), ...]. 빈 값이면 []."""
    slices: list[tuple[int, int]] = []
    for tok in _split_semi(raw):
        start_s, _, end_s = tok.partition(":")
        slices.append((int(start_s), int(end_s)))
    return slices


def _parse_normalize(raw: str | None) -> list[tuple[str, str, str | None]]:
    """컬럼별 정규화 "COL:rule[:arg];..." → [(col, rule, arg|None), ...].

    rule: date | num | nullblank | zeropad | trim. arg는 num/zeropad의 자리수(없으면 None).
    """
    rules: list[tuple[str, str, str | None]] = []
    for tok in _split_semi(raw):
        parts = tok.split(":")
        col = parts[0].strip()
        rule = parts[1].strip() if len(parts) > 1 else ""
        arg = parts[2].strip() if len(parts) > 2 else None
        rules.append((col, rule, arg))
    return rules


def _parse_bool(raw: str | bool | None) -> bool:
    """has_header 등 불리언 표기("true"/"1"/"yes"=참)를 bool로."""
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ("true", "1", "yes", "y") if raw else False


@dataclass
class CompareOptions:
    """비교기 모드·정규화 옵션(출력 spec에서 주입, V3 C1). compare_files의 유일한 옵션 운반체.

    mode 미지정=byte(현 동작 보존). 문자열 원본은 OutputSpec이 들고, from_raw가 구조화한다.
    """

    mode: str = "byte"  # byte | text | record
    encoding: str | None = None  # 판정용 디코드(None이면 호출측이 config 전역으로 채움)
    key: str | None = None  # record 정렬키(컬럼명 또는 인덱스)
    mask: list[str] = field(default_factory=list)  # 통째 무시할 컬럼
    tolerance: float = 0.0  # 수치 허용오차
    layout: list[tuple[int, int]] = field(default_factory=list)  # 고정길이 슬라이스
    delimiter: str = ","  # record 필드 구분자
    has_header: bool = False  # 첫 행이 헤더면 제외 + key/mask/normalize를 컬럼명으로 해석
    normalize: list[tuple[str, str, str | None]] = field(default_factory=list)  # 컬럼별 정규화

    @classmethod
    def from_raw(
        cls,
        *,
        mode: str | None = None,
        encoding: str | None = None,
        key: str | None = None,
        mask: str | None = None,
        tolerance: str | float | None = None,
        layout: str | None = None,
        delimiter: str | None = None,
        has_header: str | bool | None = None,
        normalize: str | None = None,
    ) -> "CompareOptions":
        """OutputSpec의 원본 문자열 옵션을 구조화된 CompareOptions로 파싱한다(순수)."""
        return cls(
            mode=(mode or "byte"),
            encoding=encoding or None,
            key=(key or None),
            mask=_split_semi(mask),
            tolerance=float(tolerance) if tolerance not in (None, "") else 0.0,
            layout=_parse_layout(layout),
            delimiter=(delimiter or ","),
            has_header=_parse_bool(has_header),
            normalize=_parse_normalize(normalize),
        )


@dataclass
class OutputSpec:
    """한 셸의 출력 1건 (기획 7.1 outputs[] 복원, D-033 P2).

    type=database면 결과 테이블을 CSV로 export(export_as), type=file이면 배치 산출 파일(file)을 그대로.
    To-Be 산출물(tobe_output_dir 기준 tobe_name)을 정답(expected, asis_output_dir 기준)과 바이트 비교.
    """

    type: str  # #10 To-Be 출력데이터 종류: "database" | "file"
    expected: str  # #5 As-Is 출력데이터 명 (정답 파일명, asis_output_dir 기준)
    table: str | None = None  # type == database (결과 테이블)
    export_as: str | None = None  # #9 type==database: To-Be 출력 명(export CSV 파일명)
    file: str | None = None  # #9 type==file: To-Be 출력 명(배치 산출 파일명)
    name: str | None = None  # 라벨(리포트/화면). 없으면 export_as/file에서 파생
    expected_dir: str | None = None  # #7 As-Is 출력 격납 패스 override(없으면 config.asis_output_dir)
    tobe_dir: str | None = None  # #11 To-Be 출력 격납 패스 override(없으면 config.tobe_output_dir)
    # V3 C1·C2: 출력별 비교 모드·정규화 옵션(원본 문자열; compare_options가 구조화).
    compare_mode: str | None = None  # byte | text | record (미지정=byte)
    key: str | None = None  # record 정렬키(컬럼명 또는 인덱스)
    encoding: str | None = None  # 출력 판정 인코딩(없으면 config 전역)
    mask: str | None = None  # 무시 컬럼(; 구분)
    tolerance: str | None = None  # 수치 허용오차
    layout: str | None = None  # 고정길이 스펙(start:end; 구분)
    delimiter: str | None = None  # record 구분자(기본 ,)
    has_header: bool = False  # export 헤더 행 유무
    normalize: str | None = None  # 컬럼별 정규화(; 구분)

    @property
    def label(self) -> str:
        """리포트·화면용 출력 식별자."""
        return self.name or self.export_as or self.file or self.type

    @property
    def compare_options(self) -> "CompareOptions":
        """이 출력의 비교 옵션을 구조화해 반환(orchestrator가 compare_files에 주입, V3 C2).

        encoding은 None일 수 있고(미지정), 호출측(orchestrator)이 config 전역으로 채운다.
        """
        return CompareOptions.from_raw(
            mode=self.compare_mode,
            encoding=self.encoding,
            key=self.key,
            mask=self.mask,
            tolerance=self.tolerance,
            layout=self.layout,
            delimiter=self.delimiter,
            has_header=self.has_header,
            normalize=self.normalize,
        )

    @property
    def tobe_name(self) -> str:
        """tobe_output_dir 기준 To-Be 산출 파일명(database=export_as / file=file)."""
        return self.export_as if self.type == "database" else self.file


@dataclass
class ShellDefinition:
    """정의 파일(test_definition.yaml)의 테스트 1건 메타데이터 (D-021·D-022 → D-033 다중입출력).

    Boss 기획 7.1 구조. 입력 여러 건(inputs[]) 적재 + 출력 여러 건(outputs[]) 비교. 단일 필드는
    inputs[0]/outputs[0]에서 파생한 하위호환 뷰 — 적재/비교는 리스트를 정본으로 루프한다.
    """

    test_id: str  # 3자리 zero-pad 셸 ID (예: "001")
    test_name: str
    input_type: str  # 하위호환: inputs[0].type (1차 입력)
    input_csv: str  # 하위호환: inputs[0].csv
    output_type: str  # "database" | "file"
    expected_output_csv: str  # asis_output_dir 기준 정답지 파일명
    shell_program: str  # 기동할 stub(=shell) 경로
    timeout_seconds: int = 60
    setup: str | None = None  # 입력 적재 전 1회 실행할 준비 SQL(.sql)/스크립트 경로(선택). P0 신규
    input_table: str | None = None  # 하위호환: inputs[0].table
    input_dest_dir: str | None = None  # 하위호환: inputs[0].dest_dir
    output_table: str | None = None  # output_type == database (결과 테이블)
    output_file: str | None = None  # output_type == file (배치가 직접 생성하는 파일명)
    export_csv: str | None = None  # output_type == database (다운로드 CSV 파일명)
    # D-033: 다중 입력. definition 로더가 항상 채운다(단일도 1개짜리 리스트). 단일 필드는
    # inputs[0]에서 파생한 하위호환 뷰 — 적재는 inputs[]를 정본으로 루프한다(orchestrator).
    inputs: list[InputSpec] = field(default_factory=list)
    # D-033 P2: 다중 출력. 단일 필드(output_*·expected_output_csv)는 outputs[0]에서 파생한 호환 뷰.
    outputs: list[OutputSpec] = field(default_factory=list)

    def __post_init__(self) -> None:
        # inputs/outputs 미지정으로 생성된 경우(직접 생성·구형 경로) 단일 필드에서 1건 파생 — 단일 진실.
        if not self.inputs and self.input_csv:
            self.inputs = [
                InputSpec(
                    csv=self.input_csv,
                    type=self.input_type,
                    table=self.input_table,
                    dest_dir=self.input_dest_dir,
                )
            ]
        if not self.outputs and self.output_type:
            self.outputs = [
                OutputSpec(
                    type=self.output_type,
                    expected=self.expected_output_csv,
                    table=self.output_table,
                    export_as=self.export_csv,
                    file=self.output_file,
                )
            ]


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
