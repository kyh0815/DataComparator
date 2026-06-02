"""stub 배치를 실행해 To-Be 출력 CSV를 만든다 (T2-4).

# === 인수인계 시 교체 포인트 ===
# execution.shell_program(시연용 stub)을 실 운영의 진짜 배치(Net COBOL)로 교체한다.
# 입출력 계약은 유지: Runner는 batch를 '실행파일'로 직접 호출하므로(파이썬 하드코딩 안 함)
# stub을 같은 경로의 실행 가능한 배치로 바꾸기만 하면 된다.
# 실 배치의 *본질* 계약은 --shell-id 하나이며, 나머지 인자는 stub scaffolding이다.
# (실 배치는 자기 I/O 위치가 고정이고, 그 위치는 test_definition.yaml이 도구에 알려준다.)

설계 결정은 DECISIONS.md D-023 참조:
- run_batch(definition, config, conn=None, *, clean=False) -> Path.
  ARCHITECTURE 4-3의 shell_id 대신 ShellDefinition을 받는다(분기 정보 재조회 회피).
- 종료코드≠0/timeout은 RunnerError로 던지고, 오케스트레이터(T3-1)가 ComparisonResult.ERROR로
  매핑한다(예상된 ERROR도 '구조화된 결과'는 경계에서 만들어짐 — Runner는 산출물 유무만 신호).
- shell_program은 실행파일로 직접 호출(우분투 전제 D-003, shebang+실행비트). Windows는 범위 밖.
- 출력=database면 같은 함수가 exporter로 결과 테이블을 CSV 다운로드(Boss 출력 단계).
- clean=True면 stub에 --clean 전달(골든 생성). 골든·To-Be가 동일 경로를 타 false-NG를 구조적 차단.
- 비밀번호는 argv가 아니라 환경변수(POSTGRES_PASSWORD)로 전달(ps 노출 방지).

print/CLI 출력 금지(CLAUDE.md 3-1). stdout/stderr는 캡처만 한다.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .exporter import export_table_to_csv
from .models import Config, ShellDefinition


class RunnerError(Exception):
    """배치 실행 실패(종료코드≠0·timeout·설정 모순). 오케스트레이터가 ERROR로 기록한다."""


def run_batch(
    definition: ShellDefinition,
    config: Config,
    conn=None,
    *,
    clean: bool = False,
) -> Path:
    """정의 1건의 stub 배치를 실행하고 To-Be 출력 CSV 경로를 반환한다.

    conn은 출력=database(export 다운로드)에서만 사용한다 — 파일 출력 셸은 None을 허용한다.
    clean=True면 NG 주입을 끈 정상 출력을 만든다(골든 생성용).
    """
    argv, env, output_path, timeout = _build_command(definition, config, clean)

    try:
        proc = subprocess.run(
            argv, env=env, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        raise RunnerError(
            f"[{definition.test_id}] バッチタイムアウト({timeout}s): {definition.shell_program}"
        ) from exc

    if proc.returncode != 0:
        raise RunnerError(
            f"[{definition.test_id}] バッチ実行失敗(終了コード {proc.returncode}): "
            f"{definition.shell_program}\nstderr: {proc.stderr.strip()}"
        )

    if definition.output_type == "database":
        if conn is None:
            raise RunnerError(
                f"[{definition.test_id}] 出力=database ですが DB 接続(conn)がありません。"
            )
        export_table_to_csv(
            conn, definition.output_table, output_path, encoding=config.encoding
        )

    return output_path


def _build_command(
    definition: ShellDefinition, config: Config, clean: bool
) -> tuple[list[str], dict, Path, int]:
    """실행 argv·env·출력경로·timeout을 구성한다(순수 — 단위 테스트로 검증).

    비밀번호는 env에만 넣고 argv에는 절대 넣지 않는다.
    """
    program = _resolve_program(definition, config)
    output_path = _output_path(definition, config)

    argv = [
        str(program),
        "--shell-id", definition.test_id,
        "--output-type", definition.output_type,
        "--encoding", config.encoding,
        "--db-host", config.database.host,
        "--db-port", str(config.database.port),
        "--db-name", config.database.dbname,
        "--db-user", config.database.user,
    ]

    # 입력 분기
    if definition.input_type == "database":
        argv += ["--input-table", definition.input_table or "transaction_log"]
    else:
        argv += ["--input-file", str(_input_file_path(definition, config))]

    # 출력 분기 (dead-arg 제거: 필요한 쪽 인자만 전달)
    if definition.output_type == "file":
        argv += ["--output-path", str(output_path)]
    else:
        argv += ["--output-table", definition.output_table]

    if clean:
        argv.append("--clean")

    env = dict(os.environ)
    if config.database.password is not None:
        env["POSTGRES_PASSWORD"] = config.database.password  # argv 아님(ps 노출 방지)

    timeout = definition.timeout_seconds or config.batch.timeout_seconds
    return argv, env, output_path, timeout


def _resolve_program(definition: ShellDefinition, config: Config) -> Path:
    """shell_program을 절대경로로. 상대경로는 정의 파일 디렉토리(=프로젝트 루트) 기준."""
    base = config.definition_file.parent if config.definition_file else Path.cwd()
    program = Path(definition.shell_program)
    return program if program.is_absolute() else (base / program).resolve()


def _output_path(definition: ShellDefinition, config: Config) -> Path:
    """To-Be 출력 CSV 경로 = tobe_output_dir / (output_file 또는 export_csv)."""
    name = definition.output_file if definition.output_type == "file" else definition.export_csv
    path = config.tobe_output_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def resolve_input_dir(definition: ShellDefinition, config: Config) -> Path:
    """파일 입력 셸의 raw 복사 디렉토리를 결정한다 — **단일 진실**.

    오케스트레이터(T3-1)의 copy_input_file *복사처*와 Runner의 *읽기처*가 반드시
    일치해야 한다(드리프트 시 파일셸 전멸). 그래서 양쪽이 이 헬퍼를 공유한다.
    우선순위: config.tobe_input_dir > definition.input_dest_dir. 둘 다 없으면 RunnerError.
    """
    base = config.tobe_input_dir
    if base is None:
        if not definition.input_dest_dir:
            raise RunnerError(
                f"[{definition.test_id}] ファイル入力先ディレクトリが不明です"
                "（tobe_input_dir/input_dest_dir 不足）。"
            )
        base = Path(definition.input_dest_dir)
    return base


def _input_file_path(definition: ShellDefinition, config: Config) -> Path:
    """파일 입력 셸의 복사된 raw 파일 경로(오케스트레이터가 copy_input_file로 둔 위치)."""
    return resolve_input_dir(definition, config) / definition.input_csv
