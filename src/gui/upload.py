"""업로드 검증을 위한 임시 작업 준비 (Phase 6, D-028 → 다건·정의 파라미터화).

업로드된 (As-Is 입력, As-Is 정답) **여러 쌍**을 임시 작업폴더에 두고, 그걸 가리키는 **임시
Config + 임시 N-셸 정의 파일**을 만든다. 그러면 `run_full_comparison(temp_config)`이
파이프라인(적재/복사 → stub 배치 → exporter → 비교 → 리포트)을 셸마다 그대로 태운다.
Core·CLI 무수정 — 엔진은 이미 N셸을 정의 파일 순서대로 처리한다(orchestrator).

Phase 6 변경(D-028 Phase B 일반화):
- 입력/출력 테이블·배치 경로를 **인자로 받는다**(연결설정 탭이 화면에서 지정) — 데모 스키마
  하드코딩(`transaction_log`/`tobe_result`)을 제거했다. models.Config는 손대지 않는다(A).
- 짝짓기는 **파일명 stem 일치**(고객 규약). 짝 안 맞는 파일은 silent drop하지 않고 호출자에게
  돌려줘 화면에 명시 노출한다(자가검증 ④). 매칭 0건은 UploadError.
"""

from __future__ import annotations

import csv
import dataclasses
import io
import shutil
import tempfile
from pathlib import Path

import yaml

from src.config.definition import DefinitionError, load_definitions
from src.config.settings import load_config
from src.core.models import Config

_REPO_ROOT = Path(__file__).resolve().parents[2]
_VALID_INPUT = ("database", "file")
_VALID_OUTPUT = ("file", "database")

# 배치 경로 미지정 시 쓰는 번들 stub(Phase 6 QA 기본 — 실 배치는 설치 시 지정).
_STUB_DB = "run_batch_db.py"
_STUB_FILE = "run_batch_file.py"


class UploadError(Exception):
    """업로드 검증 준비 실패(잘못된 type·매칭 0건 등). web 계층이 잡아 사용자 메시지로 보낸다."""


@dataclasses.dataclass
class PairingInfo:
    """업로드 짝짓기 결과. unmatched는 silent drop 금지 — 화면에 명시 노출한다(자가검증 ④)."""

    matched: list[str]  # 입력·정답 양쪽에 있는 stem(=셸 ID), 정렬됨
    unmatched_input: list[str]  # 정답이 없는 입력 stem
    unmatched_output: list[str]  # 입력이 없는 정답 stem


def prepare_jobs(
    base_config_path: str,
    *,
    inputs: dict[str, bytes],
    outputs: dict[str, bytes],
    input_type: str,
    output_type: str,
    encoding: str,
    input_table: str | None = None,
    output_table: str | None = None,
    batch_program: str | None = None,
) -> tuple[Config, Path, PairingInfo]:
    """업로드 N쌍으로 임시 작업폴더·Config·N-셸 정의 파일을 만든다.

    inputs/outputs는 {stem: 바이트}. stem이 양쪽에 모두 있는 항목만 셸로 만든다(파일명 일치=짝).
    (Config, tmpdir, PairingInfo)를 돌려준다 — 호출자는 실행 후 tmpdir를 정리하고, PairingInfo의
    unmatched를 화면에 노출한다(리포트는 base report_dir라 보존됨).
    """
    if input_type not in _VALID_INPUT:
        raise UploadError(f"input_type은 {_VALID_INPUT} 중 하나여야 합니다(받음: {input_type}).")
    if output_type not in _VALID_OUTPUT:
        raise UploadError(f"output_type은 {_VALID_OUTPUT} 중 하나여야 합니다(받음: {output_type}).")
    if input_type == "database" and not input_table:
        raise UploadError("입력=DB이면 입력 테이블명이 필요합니다(연결설정에서 지정).")
    if output_type == "database" and not output_table:
        raise UploadError("출력=DB이면 출력 테이블명이 필요합니다(연결설정에서 지정).")

    pairing = _pair(inputs, outputs)
    if not pairing.matched:
        raise UploadError(
            "짝지을 수 있는 (입력, 정답) 쌍이 없습니다 — 입력과 정답은 같은 파일명이어야 합니다."
        )

    base = load_config(base_config_path)  # DB 접속·report_dir은 베이스(저장된 config.yaml)에서 이어받음.

    tmp = Path(tempfile.mkdtemp(prefix="dc_upload_"))
    (tmp / "input").mkdir()
    (tmp / "output").mkdir()
    (tmp / "tobe").mkdir()
    (tmp / "tobe_input").mkdir()

    tests: list[dict] = []
    for stem in pairing.matched:
        # 업로드 바이트를 그대로 기록(재인코딩 금지 — 정답은 바이트 비교 대상, 입력은 경계서 디코드).
        (tmp / "input" / f"{stem}.csv").write_bytes(inputs[stem])
        (tmp / "output" / f"{stem}.csv").write_bytes(outputs[stem])
        tests.append(
            _definition_entry(stem, input_type, output_type, input_table, output_table, batch_program)
        )

    definition_path = tmp / "test_definition.yaml"
    definition_path.write_text(
        yaml.safe_dump({"tests": tests}, allow_unicode=True, sort_keys=False),
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
    return config, tmp, pairing


def _pair(inputs: dict[str, bytes], outputs: dict[str, bytes]) -> PairingInfo:
    """입력·정답 stem 집합으로 매칭/미매칭을 가른다(silent drop 금지 — 미매칭도 돌려준다)."""
    in_stems, out_stems = set(inputs), set(outputs)
    return PairingInfo(
        matched=sorted(in_stems & out_stems),
        unmatched_input=sorted(in_stems - out_stems),
        unmatched_output=sorted(out_stems - in_stems),
    )


def _definition_entry(
    stem: str,
    input_type: str,
    output_type: str,
    input_table: str | None,
    output_table: str | None,
    batch_program: str | None,
) -> dict:
    """업로드 1셸을 Boss 구조 정의 dict로. shell_program은 절대경로(임시 디렉토리 해석 회피)."""
    if batch_program:
        program = Path(batch_program)
        shell_program = str(program if program.is_absolute() else (_REPO_ROOT / program).resolve())
    else:
        stub = _STUB_DB if input_type == "database" else _STUB_FILE
        shell_program = str(_REPO_ROOT / "stub_batch" / stub)

    inp: dict = {"type": input_type, "csv": f"{stem}.csv"}
    if input_type == "database":
        inp["table"] = input_table

    out: dict = {"type": output_type}
    if output_type == "file":
        out["file"] = f"{stem}.csv"
    else:
        out["table"] = output_table
        out["export_csv"] = f"{stem}.csv"

    return {
        "test_id": stem,
        "test_name": f"업로드 검증 ({stem})",
        "input": inp,
        "execution": {"shell_program": shell_program, "timeout": 60},
        "output": out,
        "expected_output_csv": f"{stem}.csv",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 정의 파일 주도(definition-driven) — yml이 정본. 셸별 타입·테이블·배치가 다른 실무 케이스.
# (D-021/022 정의 파일 주도 설계를 GUI로 노출. prepare_jobs의 "화면 3칸" 방식과 양립.)
# ─────────────────────────────────────────────────────────────────────────────


@dataclasses.dataclass
class DefIngestInfo:
    """정의 파일 적재 결과. excluded는 파일 누락 셸(silent drop 금지 — 화면에 명시)."""

    shells: list[dict]  # 실행 대상 [{test_id, input_type, output_type, input_table, output_table}]
    excluded: list[dict]  # 파일 누락 제외 [{test_id, missing:[...]}]


def summarize_definition(definition_bytes: bytes) -> dict:
    """업로드된 정의 파일을 파싱만 해서 셸 요약을 돌려준다(미리보기용, 실행·파일 불요).

    {ok, count, shells:[{test_id,input_type,output_type,input_table,output_table,
    input_csv,expected_output_csv}], message}. 파싱 실패는 ok=False + 메시지.
    """
    with tempfile.NamedTemporaryFile("wb", suffix=".yaml", delete=False) as tf:
        tf.write(definition_bytes)
        p = Path(tf.name)
    try:
        defs = load_definitions(p)
    except DefinitionError as exc:
        return {"ok": False, "count": 0, "shells": [], "message": f"定義ファイルの解析に失敗: {exc}"}
    finally:
        p.unlink(missing_ok=True)
    shells = [
        {
            "test_id": d.test_id,
            "input_type": d.input_type,
            "output_type": d.output_type,
            "input_table": d.input_table,
            "output_table": d.output_table,
            "input_csv": d.input_csv,
            "expected_output_csv": d.expected_output_csv,
        }
        for d in defs
    ]
    return {"ok": True, "count": len(shells), "shells": shells, "message": f"{len(shells)} シェルを読み込みました。"}


def prepare_jobs_from_definition(
    base_config_path: str,
    *,
    definition_bytes: bytes,
    inputs: dict[str, bytes],
    outputs: dict[str, bytes],
    encoding: str,
) -> tuple[Config, Path, DefIngestInfo]:
    """업로드된 정의 파일을 정본으로 임시 작업폴더·Config·정규화 정의를 만든다(정의 파일 주도).

    정의의 각 셸이 참조하는 input_csv/expected_output_csv 파일명을 업로드 CSV(stem 키)와 맞춰
    배치하고, 둘 다 있는 셸만 실행 대상으로 삼는다(누락 셸은 DefIngestInfo.excluded로 명시 노출).
    셸의 shell_program 상대경로는 repo 루트 기준 절대화한다(prepare_jobs와 동일 — 임시 디렉토리
    기준 오해석 회피). 타입·테이블·배치는 모두 정의 파일에서 온다(화면 폼 무시).
    """
    base = load_config(base_config_path)

    tmp = Path(tempfile.mkdtemp(prefix="dc_upload_"))
    (tmp / "input").mkdir()
    (tmp / "output").mkdir()
    (tmp / "tobe").mkdir()
    (tmp / "tobe_input").mkdir()

    uploaded = tmp / "_uploaded_definition.yaml"
    uploaded.write_bytes(definition_bytes)
    try:
        defs = load_definitions(uploaded)
    except DefinitionError as exc:
        shutil.rmtree(tmp, ignore_errors=True)
        raise UploadError(f"定義ファイルの解析に失敗しました: {exc}") from exc

    run_tests: list[dict] = []
    ran: list[dict] = []
    excluded: list[dict] = []
    for d in defs:
        in_stem = Path(d.input_csv).stem
        out_stem = Path(d.expected_output_csv).stem
        missing = []
        if in_stem not in inputs:
            missing.append(f"入力 {d.input_csv}")
        if out_stem not in outputs:
            missing.append(f"正解 {d.expected_output_csv}")
        if missing:
            excluded.append({"test_id": d.test_id, "missing": missing})
            continue
        (tmp / "input" / d.input_csv).write_bytes(inputs[in_stem])
        (tmp / "output" / d.expected_output_csv).write_bytes(outputs[out_stem])
        run_tests.append(_definition_entry_from(d))
        ran.append(
            {
                "test_id": d.test_id,
                "input_type": d.input_type,
                "output_type": d.output_type,
                "input_table": d.input_table,
                "output_table": d.output_table,
            }
        )

    if not run_tests:
        shutil.rmtree(tmp, ignore_errors=True)
        raise UploadError(
            "定義に対応する入力/正解 CSV が見つかりません（ファイル名が定義の input/expected と一致する必要があります）。"
        )

    definition_path = tmp / "test_definition.yaml"
    definition_path.write_text(
        yaml.safe_dump({"tests": run_tests}, allow_unicode=True, sort_keys=False),
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
    )
    return config, tmp, DefIngestInfo(shells=ran, excluded=excluded)


def _definition_entry_from(d) -> dict:
    """ShellDefinition을 Boss 구조 정의 dict로 되돌린다. shell_program은 절대경로화."""
    program = Path(d.shell_program)
    shell_program = str(program if program.is_absolute() else (_REPO_ROOT / program).resolve())

    inp: dict = {"type": d.input_type, "csv": d.input_csv}
    if d.input_type == "database":
        inp["table"] = d.input_table
    if d.input_dest_dir:
        inp["dest_dir"] = d.input_dest_dir

    out: dict = {"type": d.output_type}
    if d.output_type == "file":
        out["file"] = d.output_file
    else:
        out["table"] = d.output_table
        out["export_csv"] = d.export_csv

    return {
        "test_id": d.test_id,
        "test_name": d.test_name,
        "input": inp,
        "execution": {"shell_program": shell_program, "timeout": d.timeout_seconds},
        "output": out,
        "expected_output_csv": d.expected_output_csv,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 매핑표(CSV) → test_definition.yaml 자동 생성 — "손으로 yaml 안 쓰기"의 완성형.
# 고객의 셸-테이블 매핑 한 장으로 N셸 정의를 만든다(대량 자동화). 셸별 정의의 *사실*(어느
# 테이블·배치)은 데이터로 유추 불가라 표로 받되, yaml 문법은 도구가 생성한다.
# ─────────────────────────────────────────────────────────────────────────────

_MAPPING_REQUIRED = ("shell_id", "input_type", "output_type")

# 고객 배포용 빈 양식(필수열 + 기입 예시 2행: DB→DB, file→file). 고객은 예시를 지우고 자기 셸을 적는다.
MAPPING_TEMPLATE_CSV = (
    "shell_id,input_type,input_table,output_type,output_table\n"
    "001,database,transaction_log,database,tobe_result\n"
    "006,file,,file,\n"
)


def definition_from_mapping(mapping_bytes: bytes) -> dict:
    """매핑표 CSV를 test_definition.yaml 텍스트로 변환한다(+round-trip 검증).

    반환 {ok, yaml, count, shells, errors}. 한 행이라도 오류면 ok=False·yaml="" (부분 생성
    안 함 — 부분만 만들어 '전체 검증' 착시를 막는다, 자가검증 ④). 열 이름은 대소문자 무시.
    필수 열: shell_id·input_type·output_type. DB 타입 쪽은 input_table/output_table 필수.
    나머지(input_csv/expected_output_csv/export_csv/output_file/batch_program/test_name/timeout)는
    비면 관례 기본값({shell_id}.csv 등, 배치 공란→동봉 stub).
    """
    text = _decode_mapping(mapping_bytes)
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return {"ok": False, "yaml": "", "count": 0, "shells": [],
                "errors": ["空のファイル、またはヘッダー行がありません。"]}

    cols = {(c or "").strip().lower(): c for c in reader.fieldnames}
    missing_cols = [c for c in _MAPPING_REQUIRED if c not in cols]
    if missing_cols:
        return {"ok": False, "yaml": "", "count": 0, "shells": [],
                "errors": [f"必須列がありません: {missing_cols}（必要: shell_id, input_type, output_type）"]}

    def cell(row: dict, key: str) -> str:
        src = cols.get(key)
        return (row.get(src) or "").strip() if src else ""

    tests: list[dict] = []
    shells: list[dict] = []
    errors: list[str] = []
    seen: set[str] = set()
    for line_no, row in enumerate(reader, start=2):  # 2행=첫 데이터행(헤더 다음)
        sid = cell(row, "shell_id")
        if not sid:
            errors.append(f"{line_no}行目: shell_id が空です")
            continue
        if sid in seen:
            errors.append(f"{line_no}行目: shell_id '{sid}' が重複しています")
            continue
        seen.add(sid)
        itype, otype = cell(row, "input_type") or "database", cell(row, "output_type") or "file"
        if itype not in _VALID_INPUT:
            errors.append(f"{line_no}行目({sid}): input_type は database|file（受け取り: {itype}）")
            continue
        if otype not in _VALID_OUTPUT:
            errors.append(f"{line_no}行目({sid}): output_type は file|database（受け取り: {otype}）")
            continue
        intable, outtable = cell(row, "input_table"), cell(row, "output_table")
        if itype == "database" and not intable:
            errors.append(f"{line_no}行目({sid}): input=DB は input_table が必須")
            continue
        if otype == "database" and not outtable:
            errors.append(f"{line_no}行目({sid}): output=DB は output_table が必須")
            continue

        input_csv = cell(row, "input_csv") or f"{sid}.csv"
        expected = cell(row, "expected_output_csv") or f"{sid}.csv"
        batch = cell(row, "batch_program")
        shell_program = batch or ("stub_batch/" + (_STUB_DB if itype == "database" else _STUB_FILE))
        execution: dict = {"shell_program": shell_program}
        if cell(row, "timeout"):
            try:
                execution["timeout"] = int(cell(row, "timeout"))
            except ValueError:
                errors.append(f"{line_no}行目({sid}): timeout は整数")
                continue

        inp: dict = {"type": itype, "csv": input_csv}
        if itype == "database":
            inp["table"] = intable
        out: dict = {"type": otype}
        if otype == "file":
            out["file"] = cell(row, "output_file") or f"{sid}.csv"
        else:
            out["table"] = outtable
            out["export_csv"] = cell(row, "export_csv") or f"{sid}.csv"

        tests.append({
            "test_id": sid,
            "test_name": cell(row, "test_name") or sid,
            "input": inp,
            "execution": execution,
            "output": out,
            "expected_output_csv": expected,
        })
        shells.append({"test_id": sid, "input_type": itype, "output_type": otype,
                       "input_table": intable or None, "output_table": outtable or None})

    if not tests and not errors:
        errors.append("データ行がありません。")
    if errors:
        return {"ok": False, "yaml": "", "count": 0, "shells": shells, "errors": errors}

    yaml_text = yaml.safe_dump({"tests": tests}, allow_unicode=True, sort_keys=False)

    # round-trip 검증: 생성한 yaml이 실제 로더를 통과하는지 확인(깨진 정의 생성 방지, 자가검증 ⑤).
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tf:
        tf.write(yaml_text)
        p = Path(tf.name)
    try:
        load_definitions(p)
    except DefinitionError as exc:
        return {"ok": False, "yaml": "", "count": 0, "shells": shells,
                "errors": [f"生成した定義の検証に失敗: {exc}"]}
    finally:
        p.unlink(missing_ok=True)

    return {"ok": True, "yaml": yaml_text, "count": len(tests), "shells": shells, "errors": []}


def _decode_mapping(b: bytes) -> str:
    """매핑표 CSV 바이트를 텍스트로. Excel 한국어/일본어 저장 대비 utf-8-sig→cp932 순 시도."""
    for enc in ("utf-8-sig", "cp932", "utf-8"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", errors="replace")
