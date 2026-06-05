"""정의 항목별 경로 해석 — config 공통 디렉토리 + 항목별 override의 **단일 진실** (D-036).

사장님 규격(체크리스트 항목별 격납 패스)을 충족하되, 회의 확정 "디렉토리=config 공통"과
양립하도록 **항목에 경로가 적혀 있으면 그걸, 없으면 config 공통**을 쓴다(하위호환·간결).

orchestrator(입력 적재처·정답 경로)와 runner(입력 읽기처·To-Be 산출 경로), make_golden이
모두 이 헬퍼를 공유해 *복사처=읽기처* 드리프트를 구조적으로 차단한다(기존 resolve_input_dir 정신 계승).

print/CLI 출력 금지(CLAUDE.md 3-1). 경로 부재(파일 입력 디렉토리 미상)는 ValueError로
던지고 상위(orchestrator/runner)가 셸 ERROR로 흡수한다.
"""

from __future__ import annotations

from pathlib import Path

from .models import Config, InputSpec, OutputSpec


def _dir(override: str | None, fallback: Path, config: Config) -> Path:
    """항목 경로 override가 있으면 그걸, 없으면 config 공통 디렉토리를 쓴다.

    override가 **상대경로**면 정의 파일 디렉토리 기준으로 절대화한다(shell_program과 동일 규칙,
    runner._resolve_program 참고) — 실행 CWD에 의존하지 않게. config 공통 dir은 settings가 이미 절대화함.
    """
    if not override:
        return fallback
    p = Path(override)
    if p.is_absolute():
        return p
    base = config.definition_file.parent if config.definition_file else Path.cwd()
    return (base / p).resolve()


def input_source_path(spec: InputSpec, config: Config) -> Path:
    """입력 1건의 As-Is 원천 경로 = (src_dir or asis_input_dir)/csv  (규격 #2·#4)."""
    return _dir(spec.src_dir, config.asis_input_dir, config) / spec.csv


def input_dest_dir(spec: InputSpec, config: Config) -> Path:
    """파일 입력의 To-Be 적재 디렉토리 (규격 #7-4). 항목 dest_dir 우선, 없으면 config.tobe_input_dir.

    둘 다 없으면 ValueError(상위에서 셸 ERROR로 매핑). DB 입력은 테이블이 격납지라 경로 불요(#7-1).
    """
    if spec.dest_dir:
        return _dir(spec.dest_dir, config.tobe_input_dir, config)
    if config.tobe_input_dir is None:
        raise ValueError(
            "ファイル入力先ディレクトリが不明です（tobe_input_dir/dest_dir 不足）。"
        )
    return config.tobe_input_dir


def input_dest_path(spec: InputSpec, config: Config) -> Path:
    """파일 입력의 To-Be 적재 파일 경로 = dest_dir/(dest_name or csv)  (규격 #7-3·#7-4)."""
    return input_dest_dir(spec, config) / (spec.dest_name or spec.csv)


def output_asis_path(out: OutputSpec, config: Config) -> Path:
    """출력 1건의 As-Is 정답(골든) 경로 = (expected_dir or asis_output_dir)/expected  (규격 #5·#7)."""
    return _dir(out.expected_dir, config.asis_output_dir, config) / out.expected


def output_tobe_dir(out: OutputSpec, config: Config) -> Path:
    """출력 1건의 To-Be 산출 디렉토리 = (tobe_dir or tobe_output_dir)  (규격 #11). **부수효과 없음**.

    프리플라이트(C3)가 쓰기권한을 무실행 점검할 때 쓴다(output_tobe_path는 mkdir 부수효과가 있어 부적합).
    """
    return _dir(out.tobe_dir, config.tobe_output_dir, config)


def output_tobe_path(out: OutputSpec, config: Config) -> Path:
    """출력 1건의 To-Be 산출 경로 = (tobe_dir or tobe_output_dir)/tobe_name  (규격 #9·#11). 부모 생성."""
    path = output_tobe_dir(out, config) / out.tobe_name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
