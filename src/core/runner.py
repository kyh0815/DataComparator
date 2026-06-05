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
import re
import subprocess
from pathlib import Path

from .exporter import export_table_to_csv
from .models import Config, OutputSpec, ShellDefinition
from .paths import input_dest_path, output_tobe_path

_PLACEHOLDER = re.compile(r"\{(\w+)\}")  # 배치 호출 토큰의 {name} 치환자(C6)


class RunnerError(Exception):
    """배치 실행 실패(종료코드≠0·timeout·설정 모순). 오케스트레이터가 ERROR로 기록한다."""


def run_setup(definition: ShellDefinition, config: Config, conn=None) -> None:
    """입력 적재 전 1회 실행하는 준비 단계(마스터·참조 테이블·시퀀스 리셋 등). setup 비면 무동작.

    setup 경로가 .sql이면 conn으로 실행(DB 준비), 아니면 실행파일로 호출(스크립트 준비).
    실패는 RunnerError로 던지고 오케스트레이터가 셸 ERROR로 흡수한다(D-023 흐름과 동일).
    """
    setup = definition.setup
    if not setup:
        return
    path = _resolve_relative(setup, config)
    if str(path).lower().endswith(".sql"):
        if conn is None:
            raise RunnerError(
                f"[{definition.test_id}] setup={setup} は .sql ですが DB 接続(conn)がありません。"
            )
        sql = path.read_text(encoding="utf-8")
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()  # 후속 적재/배치가 보도록 즉시 커밋(D-023 ① 정신)
        return
    timeout = definition.timeout_seconds or config.batch.timeout_seconds
    proc = subprocess.run([str(path)], env=dict(os.environ), capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RunnerError(
            f"[{definition.test_id}] setup スクリプト失敗(終了コード {proc.returncode}): "
            f"{setup}\nstderr: {proc.stderr.strip()}"
        )


def run_batch(
    definition: ShellDefinition,
    config: Config,
    conn=None,
    *,
    clean: bool = False,
) -> list[tuple[OutputSpec, Path]]:
    """정의 1건의 배치를 **1회 실행**하고, **출력마다** To-Be 산출물 경로를 돌려준다(D-033 P2).

    배치(잡)를 한 번 호출(내부 프로그램 다수는 잡 내부)한 뒤, outputs[]를 루프:
    - type=database → 결과 테이블을 export_as CSV로 다운로드(exporter)
    - type=file     → 배치가 tobe_output_dir에 만든 파일 경로 그대로
    반환 [(OutputSpec, tobe_path), ...]. conn은 database 출력이 하나라도 있을 때 필요.
    clean=True면 NG 주입을 끈 정상 출력(골든 생성).
    """
    argv, env, timeout = _build_command(definition, config, clean)

    try:
        proc = subprocess.run(
            argv, env=env, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        raise RunnerError(
            f"[{definition.test_id}] バッチタイムアウト({timeout}s): {definition.shell_program}"
        ) from exc

    if proc.returncode != config.batch.success_exit_code:
        raise RunnerError(
            f"[{definition.test_id}] バッチ実行失敗(終了コード {proc.returncode}, "
            f"成功={config.batch.success_exit_code}): "
            f"{definition.shell_program}\nstderr: {proc.stderr.strip()}"
        )

    resolved: list[tuple[OutputSpec, Path]] = []
    for out in definition.outputs:
        tobe = output_tobe_path(out, config)
        if out.type == "database":
            if conn is None:
                raise RunnerError(
                    f"[{definition.test_id}] 出力=database ですが DB 接続(conn)がありません。"
                )
            export_table_to_csv(conn, out.table, tobe, encoding=config.encoding)
        resolved.append((out, tobe))
    return resolved


def _build_command(
    definition: ShellDefinition, config: Config, clean: bool
) -> tuple[list[str], dict, int]:
    """실행 argv·env·timeout을 config.batch 계약으로 구성한다(C6 — 도메인 상수·폴백 하드코딩 없음).

    배치 호출 규약(인자명·순서·env·종료코드)은 config.batch.command/env이며, 동봉 stub의 기본값이
    한 사례다. 진짜 배치 교체 시 코어 0줄 — config만 바꾼다. 1차 입력/출력 기준 scaffolding이고,
    실 배치는 자기 I/O 위치가 고정이라 불필요 인자를 무시한다. 비밀번호는 argv 아닌 env로.
    """
    program = _resolve_program(definition, config)
    ctx = _command_context(definition, config)

    argv = [str(program)] + _render_argv(config.batch.command, ctx)
    if clean and config.batch.clean_flag:  # 골든 생성 플래그(미지원 배치면 clean_flag=None)
        argv.append(config.batch.clean_flag)

    env = dict(os.environ)
    for key, template in config.batch.env.items():
        value = _render_token(template, ctx)
        if value is not None:  # 값이 빈 토큰은 env 미설정(예: 비밀번호 없음)
            env[key] = value

    timeout = definition.timeout_seconds or config.batch.timeout_seconds
    return argv, env, timeout


def _command_context(definition: ShellDefinition, config: Config) -> dict[str, str]:
    """배치 호출 토큰에 채울 문맥값(1차 입력/출력 기준). 해당 없는 슬롯은 빈 문자열(→ 쌍 드롭)."""
    first = definition.outputs[0]
    db = config.database
    is_file_in = definition.input_type == "file"
    is_file_out = first.type == "file"
    return {
        "shell_id": definition.test_id,
        "output_type": first.type,
        "encoding": config.encoding,
        "db_host": db.host,
        "db_port": str(db.port),
        "db_name": db.dbname,
        "db_user": db.user,
        "db_password": db.password or "",  # 비면 env에서 드롭
        "input_table": definition.input_table or "",  # 파일 입력이면 빈값(폴백 없음)
        "input_file": str(input_dest_path(definition.inputs[0], config)) if is_file_in else "",
        "output_table": (first.table or "") if not is_file_out else "",
        "output_path": str(output_tobe_path(first, config)) if is_file_out else "",
    }


def _render_argv(template: list[str], ctx: dict[str, str]) -> list[str]:
    """토큰 템플릿을 argv로. [flag, "{값}"] 쌍은 값이 비면 함께 드롭, "--f={값}"·"{값}"도 비면 드롭.

    이 쌍 드롭 규칙 덕에 한 템플릿이 DB/파일 입출력 셸을 모두 커버하고(빈 슬롯만 빠짐), 인자명·순서는
    전부 config라 다른 규약의 배치도 코어 수정 없이 붙는다(C6 검증: 2번째 가짜 배치).
    """
    argv: list[str] = []
    i, n = 0, len(template)
    while i < n:
        tok = template[i]
        names = _PLACEHOLDER.findall(tok)
        if not names:  # 리터럴 — 다음이 순수 플레이스홀더면 [flag, 값] 쌍
            nxt = template[i + 1] if i + 1 < n else None
            if nxt is not None and _PLACEHOLDER.fullmatch(nxt):
                val = ctx.get(_PLACEHOLDER.findall(nxt)[0], "")
                if val != "":
                    argv += [tok, val]
                i += 2  # 값이 비면 flag+값 함께 드롭
            else:
                argv.append(tok)
                i += 1
        else:  # 플레이스홀더 포함 토큰("--f={값}" 또는 순수 "{값}")
            if not any(ctx.get(nm, "") == "" for nm in names):
                argv.append(_PLACEHOLDER.sub(lambda m: ctx[m.group(1)], tok))
            i += 1
    return argv


def _render_token(template: str, ctx: dict[str, str]) -> str | None:
    """env 값 토큰을 치환. 참조 플레이스홀더 중 하나라도 비면 None(해당 env 미설정)."""
    names = _PLACEHOLDER.findall(template)
    if any(ctx.get(nm, "") == "" for nm in names):
        return None
    return _PLACEHOLDER.sub(lambda m: ctx.get(m.group(1), ""), template)


def _resolve_program(definition: ShellDefinition, config: Config) -> Path:
    """shell_program을 절대경로로. 상대경로는 정의 파일 디렉토리(=프로젝트 루트) 기준."""
    return _resolve_relative(definition.shell_program, config)


def _resolve_relative(value: str, config: Config) -> Path:
    """경로 문자열을 절대경로로. 상대경로는 정의 파일 디렉토리 기준(shell_program과 동일 규칙)."""
    base = config.definition_file.parent if config.definition_file else Path.cwd()
    p = Path(value)
    return p if p.is_absolute() else (base / p).resolve()
