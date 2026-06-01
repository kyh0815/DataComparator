"""업로드 1건 검증을 위한 임시 작업 준비 (Phase A, D-028 §업로드).

업로드된 (As-Is 입력, As-Is 정답) 한 쌍을 임시 작업폴더에 두고, 그걸 가리키는 **임시 Config +
임시 1-셸 정의 파일**을 만든다. 그러면 `run_full_comparison(temp_config, shell_ids=["up1"])`이
파이프라인(적재/복사 → stub 배치 → exporter → 비교 → 리포트)을 그대로 태운다. Core·CLI 무수정.

전제(Phase A): 신환경 배치는 stub(데모 스키마 고정). DB 입력은 transaction_log, DB 출력은
tobe_result를 쓴다 — 임의 스키마·임의 배치 연결은 Phase B(실 검증 지향)에서.
"""

from __future__ import annotations

import dataclasses
import tempfile
from pathlib import Path

import yaml

from src.config.settings import load_config
from src.core.models import Config

_REPO_ROOT = Path(__file__).resolve().parents[2]
_VALID_INPUT = ("database", "file")
_VALID_OUTPUT = ("file", "database")

# Phase A 데모 스키마 고정값 (Phase B에서 UI 지정으로 일반화).
_DEMO_INPUT_TABLE = "transaction_log"
_DEMO_OUTPUT_TABLE = "tobe_result"
_SHELL_ID = "up1"


class UploadError(Exception):
    """업로드 검증 준비 실패(잘못된 type 등). web 계층이 잡아 사용자 메시지로 보낸다."""


def prepare_job(
    base_config_path: str,
    *,
    asis_input: bytes,
    asis_output: bytes,
    input_type: str,
    output_type: str,
    encoding: str,
) -> tuple[Config, Path]:
    """업로드 1쌍으로 임시 작업폴더·Config·정의 파일을 만들고 (Config, tmpdir)를 돌려준다.

    호출자는 실행 후 tmpdir를 rmtree로 정리한다(리포트는 base report_dir라 보존됨).
    """
    if input_type not in _VALID_INPUT:
        raise UploadError(f"input_type은 {_VALID_INPUT} 중 하나여야 합니다(받음: {input_type}).")
    if output_type not in _VALID_OUTPUT:
        raise UploadError(f"output_type은 {_VALID_OUTPUT} 중 하나여야 합니다(받음: {output_type}).")

    base = load_config(base_config_path)  # DB 접속·report_dir은 베이스에서 그대로 이어받는다.

    tmp = Path(tempfile.mkdtemp(prefix="dc_upload_"))
    (tmp / "input").mkdir()
    (tmp / "output").mkdir()
    (tmp / "tobe").mkdir()
    (tmp / "tobe_input").mkdir()

    # 업로드 바이트를 그대로 기록(재인코딩 금지 — 정답은 바이트 비교 대상, 입력은 경계서 디코드).
    (tmp / "input" / f"{_SHELL_ID}.csv").write_bytes(asis_input)
    (tmp / "output" / f"{_SHELL_ID}.csv").write_bytes(asis_output)

    definition_path = tmp / "test_definition.yaml"
    definition_path.write_text(
        yaml.safe_dump(_definition(input_type, output_type), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    config = dataclasses.replace(
        base,
        encoding=encoding,
        asis_input_dir=tmp / "input",
        asis_output_dir=tmp / "output",
        tobe_output_dir=tmp / "tobe",
        tobe_input_dir=tmp / "tobe_input",
        definition_file=definition_path,
        # report_dir은 base 그대로 → 리포트가 평소 위치(out/reports)에 떨어져 /report 다운로드 재사용.
    )
    return config, tmp


def _definition(input_type: str, output_type: str) -> dict:
    """업로드 1셸을 Boss 구조 정의 dict로. shell_program은 절대경로(임시 디렉토리 기준 해석 회피)."""
    stub = "run_batch_db.py" if input_type == "database" else "run_batch_file.py"
    shell_program = str(_REPO_ROOT / "stub_batch" / stub)

    inp: dict = {"type": input_type, "csv": f"{_SHELL_ID}.csv"}
    if input_type == "database":
        inp["table"] = _DEMO_INPUT_TABLE  # Phase A: 데모 스키마 고정

    out: dict = {"type": output_type}
    if output_type == "file":
        out["file"] = f"{_SHELL_ID}.csv"
    else:
        out["table"] = _DEMO_OUTPUT_TABLE
        out["export_csv"] = f"{_SHELL_ID}.csv"

    return {
        "tests": [
            {
                "test_id": _SHELL_ID,
                "test_name": "업로드 검증",
                "input": inp,
                "execution": {"shell_program": shell_program, "timeout": 60},
                "output": out,
                "expected_output_csv": f"{_SHELL_ID}.csv",
            }
        ]
    }
