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


# C6: 배치 호출 계약의 기본값(= 동봉 stub의 한 사례). 실 배치는 config.batch로 override한다.
# 토큰 규칙(runner._render_argv): "{name}"=문맥값 치환. [flag, "{값}"] 쌍은 값이 비면 **함께 드롭**
# (예: 파일 입력 셸은 input_table이 비어 --input-table 쌍이 빠진다). 도메인 상수·폴백 하드코딩 없음.
DEFAULT_BATCH_COMMAND: list[str] = [
    "--shell-id", "{shell_id}",
    "--output-type", "{output_type}",
    "--encoding", "{encoding}",
    "--db-host", "{db_host}",
    "--db-port", "{db_port}",
    "--db-name", "{db_name}",
    "--db-user", "{db_user}",
    "--input-table", "{input_table}",  # DB 입력일 때만(파일 입력이면 빈값→드롭)
    "--input-file", "{input_file}",    # 파일 입력일 때만
    "--output-table", "{output_table}",  # DB 출력일 때만
    "--output-path", "{output_path}",    # 파일 출력일 때만
]
# 비밀번호는 argv가 아니라 env로(ps 노출 방지). 값이 비면 해당 env 미설정.
DEFAULT_BATCH_ENV: dict[str, str] = {"POSTGRES_PASSWORD": "{db_password}"}


@dataclass
class BatchGroup:
    """업무 그룹 1건의 배치 환경 (C6 batch_groups 확장, D-040). shell_group 값이 이 키로 풀린다.

    매핑표는 '어느 업무'(shell_group 태그)만 들고, 디렉토리·env·종료코드는 여기(config)가 든다(2층 분리).
    ★보류(runner 실연결): 이번 단계에선 **lint(그룹 멤버십·셸 위치 점검)만** 이 값을 읽고,
    runner는 base_dir로 셸 경로를 해석하지 않는다(데모는 execution.shell_program 경로를 직접 실행).
    실제 경로 해석/배치 실행 연결은 고객 폴더 실구조 확정 후 별도 Task(HANDOFF §8·MAPPING §8).
    """

    base_dir: Path  # 업무 디렉토리(그룹 필수). env/success_exit_code는 비면 batch 전역값 상속.
    env: dict[str, str] = field(default_factory=dict)
    success_exit_code: int = 0
    # 업무별 데이터 디렉토리(선택, D-044) — 경로 3단계 폴백의 중간층: 항목 override > 업무 그룹 > 전역 config.
    # 비면 전역 config.paths를 쓴다. settings가 config 디렉토리 기준으로 절대화.
    asis_input_dir: Path | None = None
    asis_output_dir: Path | None = None
    tobe_input_dir: Path | None = None
    tobe_output_dir: Path | None = None


@dataclass
class BatchConfig:
    """배치 실행 설정. 호출 계약(argv·env·종료코드)을 config로 외부화한다(C6).

    command/env는 토큰 템플릿이며 동봉 stub의 기본값이 곧 '한 사례'다. 진짜 배치로 교체할 땐
    config.batch만 바꾸면 되고 코어는 0줄 수정한다(인자명·순서·env·exit code 의미 전부 config).
    """

    type: str = "stub"
    # DEPRECATED(D-023): 셸별 배치는 test_definition.yaml의 execution.shell_program이 선택한다.
    stub_path: Path = Path("./stub_batch/run_batch.py")
    timeout_seconds: int = 60
    command: list[str] = field(default_factory=lambda: list(DEFAULT_BATCH_COMMAND))  # argv 토큰
    env: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_BATCH_ENV))  # 추가 env(토큰값)
    success_exit_code: int = 0  # 이 코드만 성공. 그 외는 RunnerError(종료코드 의미 외부화)
    clean_flag: str | None = "--clean"  # 골든 생성(clean=True) 시 덧붙일 플래그. 미지원이면 None
    # 업무별 배치 환경(키=shell_group 값). ★보류: lint만 사용, runner 미소비(BatchGroup 참조).
    groups: dict[str, BatchGroup] = field(default_factory=dict)


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
    shell_group: str | None = None  # 업무 그룹 태그(선택, B). config.batch.groups의 키. 비면 None(하위호환)
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
