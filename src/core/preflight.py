"""C3 프리플라이트(dry-run) — 야간 1000건 실행 전 무실행 게이트 (HANDOFF_V3 C3).

실행 없이 정의·파일·환경을 점검해 문제를 **모두 모아** CSV 좌표(checklist) 리스트로 보고한다.
**첫 에러에서 멈추지 않는다**(부분 보고 = 다 통과한 착시). 에러가 하나라도 있으면 인터페이스가
실행을 거부한다. warning(예: record인데 key 없음)은 보고하되 실행을 막지는 않는다.

점검만 한다 — 배치/적재 실행 없음. DB는 접속 가능 여부만 확인(쿼리 없음), 디렉토리는 mkdir 없이
쓰기권한만 본다. print 금지(CLAUDE.md 3-1): 구조화 리포트 반환, 렌더링은 인터페이스(CLI/GUI).

좌표 체계: CSV→YAML 변환 단계의 구조 오류는 mapping_to_definition이 行番号로 보고하고, 여기(실행 전
게이트)는 배포된 정의의 **checklist(test_id) + 출력 라벨**을 좌표로 쓴다(YAML엔 원본 行番호가 없음).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from src.config.definition import DefinitionError, load_definitions

from .models import Config, OutputSpec, ShellDefinition
from .paths import (
    apply_group_dirs,
    input_dest_dir,
    input_source_path,
    output_asis_path,
    output_tobe_dir,
)
from .runner import _resolve_relative  # shell 경로 해석 단일화(드리프트 차단)


@dataclass
class PreflightIssue:
    """프리플라이트 점검에서 발견한 문제 1건. level=error면 실행 거부, warning이면 경고만."""

    level: str  # "error" | "warning"
    coordinate: str  # 좌표(checklist 또는 "checklist/출력라벨")
    message: str


@dataclass
class PreflightReport:
    """프리플라이트 결과 묶음. 에러가 하나라도 있으면 ok=False(실행 거부)."""

    issues: list[PreflightIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[PreflightIssue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[PreflightIssue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def ok(self) -> bool:
        """실행해도 되는가 — 에러가 없으면 True(warning은 허용)."""
        return not self.errors


def preflight(
    config: Config,
    definitions: list[ShellDefinition] | None = None,
    *,
    connect=None,
) -> PreflightReport:
    """정의·파일·환경을 무실행 점검해 PreflightReport를 반환한다(HANDOFF_V3 C3).

    definitions 미지정 시 config.definition_file에서 로드한다. 정의 자체가 깨졌으면(구조 오류)
    그 사실을 에러 1건으로 담아 돌려준다(예외 대신 — 인터페이스가 한 번에 보고). connect는
    DB 접속 점검용 콜러블(db_config -> connection); 미지정 시 psycopg2 기본(테스트는 주입).
    """
    issues: list[PreflightIssue] = []

    if definitions is None:
        definitions = _load_or_report(config, issues)
        if definitions is None:
            return PreflightReport(issues)

    _check_duplicate_checklists(definitions, issues)

    needs_db = False
    for d in definitions:
        apply_group_dirs(d, config)  # 업무별 디렉토리(D-044) 반영 후 점검(실행과 동일 경로)
        _check_shell_program(d, config, issues)
        _check_shell_group(d, config, issues)
        _check_inputs(d, config, issues)
        _check_outputs(d, config, issues)
        needs_db = needs_db or _needs_db(d)

    if needs_db:
        _check_db(config, issues, connect)

    return PreflightReport(issues)


# --- 개별 점검 -------------------------------------------------------------------


def _load_or_report(config: Config, issues: list[PreflightIssue]) -> list[ShellDefinition] | None:
    """정의 로드. 미설정·구조 오류는 에러 1건으로 담고 None 반환(전체 게이트 실패)."""
    if config.definition_file is None:
        issues.append(PreflightIssue("error", "config", "definition_file が設定されていません。"))
        return None
    try:
        return load_definitions(config.definition_file)
    except DefinitionError as exc:
        issues.append(PreflightIssue("error", "定義", f"定義ファイルの読み込みに失敗: {exc}"))
        return None


def _check_duplicate_checklists(
    definitions: list[ShellDefinition], issues: list[PreflightIssue]
) -> None:
    """checklist(test_id) 중복 검출 — 같은 번호가 여러 정의에 있으면 결과 집계가 뒤섞인다."""
    seen: dict[str, int] = {}
    for d in definitions:
        seen[d.test_id] = seen.get(d.test_id, 0) + 1
    for test_id, count in seen.items():
        if count > 1:
            issues.append(
                PreflightIssue("error", test_id, f"checklist が {count} 件重複しています（一意である必要があります）。")
            )


def _check_shell_program(d: ShellDefinition, config: Config, issues: list[PreflightIssue]) -> None:
    """배치 실행파일 존재 확인(없으면 run 단계에서 전건 실패)."""
    program = _resolve_relative(d.shell_program, config)
    if not program.is_file():
        issues.append(
            PreflightIssue("error", d.test_id, f"shell 実行ファイルがありません: {program}")
        )
    if d.setup:
        setup = _resolve_relative(d.setup, config)
        if not setup.is_file():
            issues.append(
                PreflightIssue("error", d.test_id, f"setup ファイルがありません: {setup}")
            )


def _check_shell_group(d: ShellDefinition, config: Config, issues: list[PreflightIssue]) -> None:
    """shell_group 점검(B). 멤버십·모호성은 config만 보는 순수 검사(환경 무관, B-Q1),
    셸 위치 대조만 FS 의존. ★runner는 group을 아직 소비하지 않음(실연결 보류) — 여긴 lint 전용.
    """
    groups = config.batch.groups
    if d.shell_group:
        # ① 멤버십(config-only): 선언한 업무가 config.batch.groups에 정의됐는가.
        if d.shell_group not in groups:
            issues.append(
                PreflightIssue(
                    "error", d.test_id,
                    f"shell_group '{d.shell_group}' が config.batch.groups に定義されていません。",
                )
            )
            return
        # ② 셸 위치(FS): shell 実行ファイルが宣言された業務グループのディレクトリ配下にあるか.
        base = Path(groups[d.shell_group].base_dir).resolve()
        program = _resolve_relative(d.shell_program, config).resolve()
        try:
            program.relative_to(base)
        except ValueError:
            issues.append(
                PreflightIssue(
                    "warning", d.test_id,
                    f"shell が業務グループ '{d.shell_group}' のディレクトリ({base})配下にありません: {program}",
                )
            )
    elif len(groups) > 1:
        # ③ 모호성(config-only): 그룹이 여러 개인데 태그가 비면 어느 업무인지 불명.
        issues.append(
            PreflightIssue(
                "warning", d.test_id,
                "shell_group が空ですが、batch.groups が複数定義されています（業務が不明確）。",
            )
        )


def _check_inputs(d: ShellDefinition, config: Config, issues: list[PreflightIssue]) -> None:
    """입력 원천 파일 존재·읽기 가능 + 파일입력 격납 디렉토리 쓰기권한(적재 전 차단)."""
    for spec in d.inputs:
        src = input_source_path(spec, config)
        if not src.is_file():
            issues.append(PreflightIssue("error", d.test_id, f"入力ファイルがありません: {src}"))
        elif not os.access(src, os.R_OK):
            issues.append(PreflightIssue("error", d.test_id, f"入力ファイルを読み取れません: {src}"))
        if spec.type == "file":
            try:
                dest = input_dest_dir(spec, config)
            except ValueError as exc:
                issues.append(PreflightIssue("error", d.test_id, f"入力格納ディレクトリが不明です: {exc}"))
                continue
            if not _writable(dest):
                issues.append(
                    PreflightIssue("error", d.test_id, f"入力格納ディレクトリに書き込めません: {dest}")
                )


def _check_outputs(d: ShellDefinition, config: Config, issues: list[PreflightIssue]) -> None:
    """출력별: 정답(expected) 파일 존재·비0·읽기 + To-Be 출력 디렉토리 쓰기권한 + 비교옵션 정합."""
    for k, out in enumerate(d.outputs, start=1):
        coord = f"{d.test_id}/{out.label}"
        _check_expected(out, config, coord, issues)
        if not _writable(output_tobe_dir(out, config)):
            issues.append(
                PreflightIssue("error", coord, f"出力ディレクトリに書き込めません: {output_tobe_dir(out, config)}")
            )
        _check_compare_options(out, coord, issues)


def _check_expected(
    out: OutputSpec, config: Config, coord: str, issues: list[PreflightIssue]
) -> None:
    """정답 파일(이미 변환된 As-Is 출력)이 존재·비0바이트·읽기 가능한지. 누락 = 비교 무의미."""
    if not out.expected:
        issues.append(PreflightIssue("error", coord, "正解ファイル名(expected)が空です。"))
        return
    path = output_asis_path(out, config)
    if not path.is_file():
        issues.append(PreflightIssue("error", coord, f"正解ファイルがありません: {path}"))
        return
    if path.stat().st_size == 0:
        issues.append(PreflightIssue("error", coord, f"正解ファイルが0バイトです: {path}"))
    if not os.access(path, os.R_OK):
        issues.append(PreflightIssue("error", coord, f"正解ファイルを読み取れません: {path}"))


def _check_compare_options(out: OutputSpec, coord: str, issues: list[PreflightIssue]) -> None:
    """record 비교 옵션 정합: key 비면 경고, has_header=false인데 컬럼명 지정이면 에러(Q3)."""
    opts = out.compare_options
    if opts.mode != "record":
        return
    if not opts.key:
        issues.append(
            PreflightIssue(
                "warning", coord, "record モードですが key がありません → 行順序が非決定で全件NGの恐れ（ソートキー指定を推奨）。"
            )
        )
    if not opts.has_header:
        named = _named_columns(opts)
        if named:
            issues.append(
                PreflightIssue(
                    "error",
                    coord,
                    f"has_header=false なのに列名指定({', '.join(named)}) → インデックスに変えるか has_header=true にしてください。",
                )
            )


def _named_columns(opts) -> list[str]:
    """key/mask/normalize에서 인덱스가 아닌 '이름'으로 지정된 컬럼들을 모은다(무헤더에선 불가)."""
    tokens: list[str] = []
    if opts.key:
        tokens.append(opts.key)
    tokens.extend(opts.mask)
    tokens.extend(col for col, _rule, _arg in opts.normalize)
    return [t for t in tokens if not t.isdigit()]


def _check_db(config: Config, issues: list[PreflightIssue], connect) -> None:
    """DB 접속 가능 여부만 확인(쿼리 없음). 실패 시 에러 1건(셸별 아님 — 환경 문제)."""
    connector = connect or _default_connect
    try:
        conn = connector(config.database)
        conn.close()
    except Exception as exc:  # noqa: BLE001 — 어떤 접속 실패도 게이트 에러로 수렴
        hint = ""
        if config.database.password is None:  # env 미설정이면 그 사실을 명시(인증실패와 구분)
            hint = (
                f" ※ 環境変数 {config.database.password_env} が設定されていません"
                " — 設定後に再実行してください。"
            )
        issues.append(PreflightIssue("error", "DB", f"DB 接続に失敗: {exc}{hint}"))


def _default_connect(db):
    """기본 DB 커넥터(psycopg2). 점검 시점에만 import해 비-DB 실행의 의존을 줄인다."""
    import psycopg2

    return psycopg2.connect(
        host=db.host, port=db.port, dbname=db.dbname, user=db.user, password=db.password
    )


# --- 헬퍼 -----------------------------------------------------------------------


def _writable(directory: Path) -> bool:
    """디렉토리가 쓰기 가능한가. 아직 없으면(런타임에 mkdir됨) 가장 가까운 존재 조상으로 판단."""
    p = directory
    while not p.exists():
        if p.parent == p:  # 루트까지 올라가도 없음
            return False
        p = p.parent
    return p.is_dir() and os.access(p, os.W_OK)


def _needs_db(d: ShellDefinition) -> bool:
    """이 셸이 DB를 쓰는가(입력 DB 적재·출력 export·.sql setup). orchestrator._needs_db와 동일 규칙."""
    setup_sql = bool(d.setup) and str(d.setup).lower().endswith(".sql")
    return (
        setup_sql
        or any(s.type == "database" for s in d.inputs)
        or any(o.type == "database" for o in d.outputs)
    )
