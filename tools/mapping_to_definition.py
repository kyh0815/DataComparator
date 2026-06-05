#!/usr/bin/env python3
"""매핑표(Long CSV) → test_definition.yaml 생성기 (Phase 7, D-035).

수기 YAML을 피하려고, 고객이 **스프레드시트(CSV)** 로 셸-입출력 매핑을 채우면 그것을
`test_definition.yaml`로 변환한다. 풀스키마(다중 입력·다중 출력, D-033)를 표현하려면
한 셸이 입력 N·출력 M(가변 길이)이라 **납작한 1행/셸로는 부족**하므로 **Long 형식**을 쓴다:
**입출력 항목당 1행, `shell_id`로 그룹화.**

설치 준비용 **독립 CLI 도구**다(GUI 아님 — T7-3 경량화 유지). make_golden.py처럼 tools/에 둔다.
CSV 채움 → 변환 1회 → yaml → config의 `definition_file`이 가리킴 → 경량 GUI/CLI로 실행.

한 체크리스트가 입력 여러 개(예: A DB + B DB)를 읽어 출력(예: 병합된 C DB)을 내는 구조라,
**checklist를 1차 키로 묶는 Long 형식**(입출력 항목당 1행, checklist로 그룹화)을 쓴다.

CSV 열(대소문자·순서 무관, 빈 칸 허용):
  checklist  [필수] 체크리스트 번호(=검증 단위). 같은 값 행들이 한 체크리스트로 묶임(입력 N·출력 M).
             (구형 호환: shell_id 도 1차 키로 받음.)
  kind       [필수] input | output
  type       [필수] database | file  (입력/출력 데이터가 파일인지 DB인지)
  shell      [선택] 이 체크리스트에서 실행되는 배치(잡) 경로. 한 번만 적어도 됨(빈 칸=동봉 stub, 데모).
             (구형 호환: program)
  table      [입력/출력=database면 필수] As-Is 데이터를 적재할/결과가 쓰일 테이블명(어디에 업로드/적재).
  file       [선택] 파일명. 비우면 자동 생성(아래 규칙). input=입력CSV / output(db)=export CSV / output(file)=산출 파일.
  expected   [선택] 정답 파일명(asis_output_dir). 비우면 To-Be 출력과 같은 이름으로 자동.
  name       [선택] 출력 라벨(리포트/화면).
  test_name  [선택] 셸 이름(체크리스트 항목명).   timeout [선택] 초(기본 60).
  setup      [선택] 입력 적재 전 1회 실행할 준비 SQL(.sql)/스크립트 경로(체크리스트당 1회). 마스터·시퀀스 리셋용.
  in_encoding[입력/선택] 입력 적재 인코딩(미지정 시 config 전역).

  ── 출력별 비교 옵션(선택, V3 C1·C2 / 출력 행에서 읽어 compare 블록으로 운반) ──
  비우면 byte(바이트 완전 일치) 기본. 셀 내부 다중값(mask·layout·normalize)은 `;` 구분(CSV `,` 충돌 방지).
  compare_mode  byte | text | record (미지정=byte).
  key           record 정렬·정합 키(컬럼명 또는 인덱스). DB/머지 출력은 사실상 필수(없으면 행 순서 false-NG).
  encoding      출력 판정 인코딩(없으면 config 전역).   delimiter 필드 구분자(기본 ,).   has_header true/false.
  mask          무시할 컬럼(실행일자·시퀀스ID 등; `;` 구분).   tolerance 수치 허용오차.
  layout        고정길이 "start:end;start:end;..".   normalize 컬럼별 정규화 "COL:rule[:arg];.."
                (rule: date/num:N/nullblank/zeropad:N/trim).

  ── 항목별 격납 패스(선택, 사장님 규격 #4·#7·#7-3·#7-4·#11 / D-036) ──
  비우면 config.yaml 공통 디렉토리를 쓴다(권장). 셸별로 위치가 다를 때만 적는다.
  src_dir       [입력]  As-Is 입력 격납 패스(#4).        없으면 asis_input_dir.
  dest_dir      [입력]  type=file의 To-Be 격납 패스(#7-4). 없으면 tobe_input_dir.
  dest_name     [입력]  type=file의 To-Be 격납 파일명(#7-3). 없으면 입력 파일명 그대로.
  expected_dir  [출력]  As-Is 출력(정답) 격납 패스(#7). 없으면 asis_output_dir.
  tobe_dir      [출력]  To-Be 출력 격납 패스(#11).       없으면 tobe_output_dir.

**빈 파일명 자동 규칙**(D-035, 사용자 확정 — 내용은 수기, 파일명은 규칙):
  · 셸의 입력(또는 출력)이 1개면 `{shell_id}.csv`.
  · 여러 개면 `{shell_id}_{테이블명}.csv`(테이블 없으면 `{shell_id}_in{n}` / `{shell_id}_out{n}.csv`).
  · 정답(expected)이 비면 그 출력의 To-Be 이름과 동일(폴더가 달라 충돌 없음).
  · **이미 적힌 이름은 그대로 존중**(자동은 빈 칸만). 입력CSV·정답·DB export명은 우리가 정하는 이름이라 안전.

엄격 생성: 한 행이라도 오류면 전체 거부(부분 생성=전체검증 착시 차단). 생성 yaml은
load_definitions로 **round-trip 재파싱**해 깨진 정의를 막는다(D-031 §2·3 계승).

사용:
  python tools/mapping_to_definition.py mapping.csv -o test_definition.yaml
  python tools/mapping_to_definition.py mapping.csv          # stdout으로
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
import tempfile
from pathlib import Path

import yaml

# tools/를 직접 실행해도 repo 루트의 src 패키지를 import할 수 있게 path에 루트를 추가한다.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.definition import DefinitionError, load_definitions  # noqa: E402

# 1차 키 = checklist(체크리스트 번호). 같은 값 행들이 한 체크리스트로 묶임(입력 N·출력 M).
# 구형 호환: shell_id도 1차 키로 받음. 실행 배치는 shell(구형: program) 열.
# file·expected는 빈 칸이면 규칙으로 자동 채우므로 필수 아님(table은 DB의 사실이라 필수).
_KEY_COLS = ("checklist", "shell_id")  # 둘 중 하나는 있어야(checklist 우선)
_REQUIRED_COLS = ("kind", "type")
_VALID_KIND = ("input", "output")
_VALID_TYPE = ("database", "file")
_VALID_MODE = ("byte", "text", "record")
# 출력 행에서 읽어 compare 블록으로 운반하는 비교 옵션 열(V3 C1·C2). 빈 칸은 운반 안 함.
_COMPARE_COLS = ("key", "encoding", "mask", "tolerance", "layout", "delimiter", "normalize")
# 배치 경로 미지정 시 쓰는 동봉 stub(데모 기본 — 실 운영은 program 열에 실 배치 경로).
_STUB = {"database": "stub_batch/run_batch_db.py", "file": "stub_batch/run_batch_file.py"}


def mapping_to_definition(csv_text: str) -> dict:
    """Long CSV 텍스트 → {ok, yaml, count, shells, errors}. 오류가 하나라도 있으면 ok=False·yaml=''.

    shells는 [{test_id, input_count, output_count}]. errors는 사람용 메시지(행 번호 포함) 목록.
    빈 파일명은 _autofill_names가 규칙으로 채운다(내용은 수기, 파일명은 규칙 — D-035).
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        return _fail(["CSVが空です（ヘッダー行が必要）。"])
    cols = {(c or "").strip().lower() for c in reader.fieldnames}
    missing = [c for c in _REQUIRED_COLS if c not in cols]
    if missing:
        return _fail([f"必須列がありません: {', '.join(missing)}"])
    if not any(k in cols for k in _KEY_COLS):
        return _fail([f"必須列がありません: checklist（または shell_id）"])

    errors: list[str] = []
    order: list[str] = []                 # 셸 순서 보존
    shells: dict[str, dict] = {}

    for n, raw in enumerate(reader, start=2):  # 2 = 헤더 다음 첫 데이터 행(사람 기준 행 번호)
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        sid = row.get("checklist") or row.get("shell_id") or ""  # checklist(1차 키) 우선, 구형 shell_id 호환
        kind = row.get("kind", "").lower()
        itype = row.get("type", "").lower()
        if not sid:
            errors.append(f"{n}行目: checklist が空です。")
            continue
        if kind not in _VALID_KIND:
            errors.append(f"{n}行目[{sid}]: kind は {_VALID_KIND} のいずれか（受領: '{kind}'）。")
            continue
        if itype not in _VALID_TYPE:
            errors.append(f"{n}行目[{sid}]: type は {_VALID_TYPE} のいずれか（受領: '{itype}'）。")
            continue

        sh = shells.get(sid)
        if sh is None:
            sh = {"inputs": [], "outputs": [], "programs": set(),
                  "test_name": "", "timeout": "", "setup": ""}
            shells[sid] = sh
            order.append(sid)
        prog = row.get("shell") or row.get("program")  # shell(실행 배치) 우선, 구형 program 호환
        if prog:
            sh["programs"].add(prog)
        if row.get("test_name") and not sh["test_name"]:
            sh["test_name"] = row["test_name"]
        if row.get("timeout") and not sh["timeout"]:
            sh["timeout"] = row["timeout"]
        if row.get("setup") and not sh["setup"]:  # 체크리스트당 1회 준비 SQL/스크립트
            sh["setup"] = row["setup"]

        fname = row.get("file", "")        # 빈 칸이면 나중에 자동(규칙)
        table = row.get("table", "")

        if kind == "input":
            if itype == "database" and not table:
                errors.append(f"{n}行目[{sid}]: 入力=database には table が必要です。")
                continue
            spec = {"csv": fname, "type": itype}   # csv는 _autofill_names가 채울 수 있음
            if itype == "database":
                spec["table"] = table
            for col in ("dest_dir", "src_dir", "dest_name", "in_encoding"):  # #4·#7-3·#7-4 + 적재 인코딩
                if row.get(col):
                    spec[col] = row[col]
            sh["inputs"].append(spec)
        else:  # output
            if itype == "database" and not table:
                errors.append(f"{n}行目[{sid}]: 出力=database には table が必要です。")
                continue
            mode = row.get("compare_mode", "").lower()
            if mode and mode not in _VALID_MODE:
                errors.append(f"{n}行目[{sid}]: compare_mode は {_VALID_MODE} のいずれか（受領: '{mode}'）。")
                continue
            spec = {"type": itype, "expected": row.get("expected", "")}
            if itype == "database":
                spec["table"] = table
                spec["export_as"] = fname      # 비면 자동
            else:
                spec["file"] = fname           # 비면 자동
            if row.get("name"):
                spec["name"] = row["name"]
            for col in ("expected_dir", "tobe_dir"):  # #7·#11 (선택)
                if row.get(col):
                    spec[col] = row[col]
            cmp_block = _compare_block(row, mode)  # P0 §3: 출력별 비교 옵션
            if cmp_block:
                spec["compare"] = cmp_block
            sh["outputs"].append(spec)

    # 셸 단위 검증(입력·출력 ≥1, program 일관) + 빈 파일명 자동 채움.
    for sid in order:
        sh = shells[sid]
        if not sh["inputs"]:
            errors.append(f"[{sid}]: 入力（kind=input）が1件もありません。")
        if not sh["outputs"]:
            errors.append(f"[{sid}]: 出力（kind=output）が1件もありません。")
        if len(sh["programs"]) > 1:
            errors.append(f"[{sid}]: program が行ごとに異なります: {sorted(sh['programs'])}")
        if sh["inputs"] and sh["outputs"]:
            _autofill_names(sid, sh)

    if not order and not errors:
        errors.append("有効なシェル行がありません。")
    if errors:
        return _fail(errors)

    tests = [_emit_shell(sid, shells[sid]) for sid in order]
    text = yaml.safe_dump({"tests": tests}, allow_unicode=True, sort_keys=False)

    # round-trip: 생성한 yaml을 실제 로더로 다시 파싱(깨진 정의 차단).
    rt_err = _roundtrip_error(text)
    if rt_err:
        return _fail([f"生成YAMLの再パースに失敗（ツールのバグの可能性）: {rt_err}"])

    summary = [
        {"test_id": _pad(sid), "input_count": len(shells[sid]["inputs"]),
         "output_count": len(shells[sid]["outputs"])}
        for sid in order
    ]
    return {"ok": True, "yaml": text, "count": len(order), "shells": summary, "errors": []}


def _compare_block(row: dict, mode: str) -> dict:
    """출력 행의 비교 옵션 열을 compare 블록 dict로(빈 칸 제외). mode·has_header 포함.

    셀 내부 다중값(mask·layout·normalize)은 CSV 단계에서 `;` 구분 그대로 운반한다(V3 C2).
    """
    block: dict = {}
    if mode:
        block["mode"] = mode
    for col in _COMPARE_COLS:
        if row.get(col):
            block[col] = row[col]
    hh = row.get("has_header", "").lower()
    if hh in ("true", "1", "yes", "y"):
        block["has_header"] = True
    return block


def _name(sid: str, count: int, idx: int, table: str | None, role: str) -> str:
    """파일명 베이스: 항목 1개면 {sid}, 여러 개면 {sid}_{테이블명}(없으면 {sid}_{role}{idx})."""
    if count == 1:
        return sid
    if table:
        return f"{sid}_{table}"
    return f"{sid}_{role}{idx}"


def _autofill_names(sid: str, sh: dict) -> None:
    """빈 파일명(input.csv / output.export_as|file / expected)을 규칙으로 채운다(D-035).

    내용(테이블·타입·배치)은 수기, **파일명만** 자동. 이미 적힌 값은 건드리지 않는다.
    """
    n_in, n_out = len(sh["inputs"]), len(sh["outputs"])
    for i, sp in enumerate(sh["inputs"], start=1):
        if not sp.get("csv"):
            sp["csv"] = _name(sid, n_in, i, sp.get("table"), "in") + ".csv"
    for k, sp in enumerate(sh["outputs"], start=1):
        base = _name(sid, n_out, k, sp.get("table"), "out")
        if sp["type"] == "database":
            if not sp.get("export_as"):
                sp["export_as"] = base + ".csv"
            tobe = sp["export_as"]
        else:
            if not sp.get("file"):
                sp["file"] = base + ".csv"   # 확장자 미상이면 csv 기본(필요 시 file 칸에 직접 기입)
            tobe = sp["file"]
        if not sp.get("expected"):
            sp["expected"] = tobe            # 정답은 To-Be와 같은 이름(폴더가 달라 충돌 없음)


def _emit_shell(sid: str, sh: dict) -> dict:
    """셸 1건을 로더가 읽는 신형 정의 dict로(input.tables[] + outputs[])."""
    program = next(iter(sh["programs"]), "") or _STUB[sh["inputs"][0]["type"]]
    entry: dict = {"test_id": sid}
    if sh["test_name"]:
        entry["test_name"] = sh["test_name"]
    entry["input"] = {"tables": sh["inputs"]}
    execution: dict = {"shell_program": program}
    if sh["timeout"]:
        execution["timeout"] = int(sh["timeout"])
    if sh.get("setup"):
        execution["setup"] = sh["setup"]
    entry["execution"] = execution
    entry["outputs"] = sh["outputs"]
    return entry


def _roundtrip_error(yaml_text: str) -> str | None:
    """생성 yaml을 임시 파일로 써서 load_definitions로 검증. 통과면 None, 실패면 메시지."""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tf:
        tf.write(yaml_text)
        p = Path(tf.name)
    try:
        load_definitions(p)
        return None
    except DefinitionError as exc:
        return str(exc)
    finally:
        p.unlink(missing_ok=True)


def _pad(value: str) -> str:
    """test_id 3자리 zero-pad(로더와 동일 규칙). 비숫자는 그대로."""
    t = str(value).strip()
    return t.zfill(3) if t.isdigit() else t


def _fail(errors: list[str]) -> dict:
    return {"ok": False, "yaml": "", "count": 0, "shells": [], "errors": errors}


def _decode(data: bytes) -> str:
    """Excel 저장 대비: utf-8-sig 우선, 실패 시 cp932(일본어 Excel)."""
    for enc in ("utf-8-sig", "cp932"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    """CLI: 매핑 CSV → yaml. 오류면 stderr에 행별 메시지 출력 + 종료코드 1."""
    parser = argparse.ArgumentParser(description="Long形式マッピング表(CSV) → test_definition.yaml 生成")
    parser.add_argument("csv", help="入力マッピング表(CSV, Long形式)")
    parser.add_argument("-o", "--output", help="出力 yaml パス（省略時は標準出力）")
    args = parser.parse_args(argv)

    csv_path = Path(args.csv)
    if not csv_path.is_file():
        print(f"CSVが見つかりません: {csv_path}", file=sys.stderr)
        return 1

    result = mapping_to_definition(_decode(csv_path.read_bytes()))
    if not result["ok"]:
        print("変換に失敗しました:", file=sys.stderr)
        for e in result["errors"]:
            print(f"  ・{e}", file=sys.stderr)
        return 1

    if args.output:
        Path(args.output).write_text(result["yaml"], encoding="utf-8")
        print(f"生成しました: {args.output}（{result['count']} シェル）", file=sys.stderr)
        for s in result["shells"]:
            print(f"  {s['test_id']}: 入力{s['input_count']}・出力{s['output_count']}", file=sys.stderr)
    else:
        sys.stdout.write(result["yaml"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
