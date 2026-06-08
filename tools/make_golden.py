#!/usr/bin/env python3
"""시연용 As-Is 출력 정답지(골든) 생성기 (T4-1, D-027).

`samples/asis/output/{id}.csv`를 생성한다. **손으로 쓰지 않고**, 오케스트레이터와 동일한
Load → run_batch(clean=True) → (DB 출력이면 exporter 다운로드) 경로로 To-Be를 만들어 복사한다.
이렇게 해야 골든과 실제 To-Be가 *같은 직렬화*(파일=write_csv_file / DB=export_table_to_csv)를
거쳐 통짜 바이트 비교(D-004)에서 false-NG가 안 난다(D-023 §4, self-review #5).

clean=True라 NG 주입(apply_ng_pattern)이 꺼진 정상 출력 = 골든. 따라서 정상 셸은 실행 시
byte 동일(OK), NG 셸(007/008/009)은 stub 주입분만큼만 차이가 난다. 010(ERROR 시연)은 clean이면
실패하지 않아 골든이 만들어지나, 실제 실행에선 비-clean이라 RunnerError→ERROR로 비교되지 않는다.

# === 인수인계 시 교체 포인트 ===
# 실 클라이언트 데이터로 교체 후 이 스크립트를 다시 돌리면 골든이 재생성된다(시연 데이터 자산).
# 골든 생성이 stub --clean 경로를 재사용하는 한, 진짜 배치로 바꿔도 같은 원리가 유지된다.

사용:
  POSTGRES_PASSWORD=... python tools/make_golden.py --config ./config.yaml
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import psycopg2

# tools/를 직접 실행해도 repo 루트의 src 패키지를 import할 수 있게 path에 루트를 추가한다.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.definition import load_definitions
from src.config.settings import load_config
from src.core.loader import copy_input_file, load_input_csv
from src.core.paths import apply_group_dirs, input_dest_dir, input_source_path, output_asis_path
from src.core.runner import run_batch


def _needs_db(definitions) -> bool:
    return any(
        any(s.type == "database" for s in d.inputs)
        or any(o.type == "database" for o in d.outputs)
        for d in definitions
    )


def _connect(config):
    db = config.database
    return psycopg2.connect(
        host=db.host, port=db.port, dbname=db.dbname, user=db.user, password=db.password
    )


def _make_one(definition, config, conn) -> list[Path]:
    """한 셸의 골든을 clean 경로로 생성하고 출력마다 As-Is 정답 경로로 복사한다(다중 입출력, D-033/D-036).

    오케스트레이터와 동일하게 inputs[]를 적재 → run_batch(clean=True)로 출력별 To-Be 산출 →
    각 출력의 To-Be를 그 출력의 정답 경로(output_asis_path)로 복사한다. 골든·To-Be가 같은
    직렬화·경로 규칙을 타 false-NG를 구조적으로 차단한다(D-027).
    """
    apply_group_dirs(definition, config)  # 업무별 디렉토리(D-044) — 골든도 실행과 동일 경로
    for spec in definition.inputs:
        src = input_source_path(spec, config)
        if spec.type == "database":
            load_input_csv(src, conn, spec.table, encoding=config.encoding)
            conn.commit()  # stub(별도 connection)이 적재분을 보도록 (D-023 ①)
        else:
            copy_input_file(src, input_dest_dir(spec, config), dest_name=spec.dest_name)

    dests: list[Path] = []
    for out, tobe in run_batch(definition, config, conn, clean=True):  # NG 주입 꺼짐 = 골든
        dest = output_asis_path(out, config)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tobe, dest)
        dests.append(dest)
    return dests


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="시연용 골든(As-Is 출력) 생성기")
    parser.add_argument("--config", default="./config.yaml")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    definitions = load_definitions(config.definition_file)
    conn = _connect(config) if _needs_db(definitions) else None
    try:
        for definition in definitions:
            try:
                for dest in _make_one(definition, config, conn):
                    print(f"[golden] {definition.test_id} → {dest}")
            finally:
                if conn is not None:
                    conn.rollback()  # exporter read 트랜잭션 해제 (D-023 ②)
    finally:
        if conn is not None:
            conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
