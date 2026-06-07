"""Long 매핑표(CSV) → test_definition.yaml 변환 도구 테스트 (D-035, DB 불요).

다중 입출력 그룹화·round-trip 유효성·엄격 검증(필수열/타입/누락)·CLI를 검증한다.
"""

from pathlib import Path

import pytest
import yaml

import tools.mapping_to_definition as m
from src.config.definition import load_definitions

_MULTI = (
    "shell_id,kind,type,program,table,file,expected,name\n"
    "001,input,database,/opt/job1,transaction_log,取引.csv,,\n"
    "001,input,database,,customer_master,顧客.csv,,\n"
    "001,input,file,,,夜間.csv,,\n"
    "001,output,database,,result_a,出A.csv,正A.csv,結果A\n"
    "001,output,file,,,出B.sam,正B.sam,\n"
    "002,input,file,/opt/job2,,002.csv,,\n"
    "002,output,database,,tobe_result,002.csv,002.csv,\n"
)


def test_groups_multi_io_by_shell_id():
    r = m.mapping_to_definition(_MULTI)
    assert r["ok"] and r["count"] == 2
    by = {s["test_id"]: s for s in r["shells"]}
    assert by["001"]["input_count"] == 3 and by["001"]["output_count"] == 2
    assert by["002"]["input_count"] == 1 and by["002"]["output_count"] == 1


def test_generated_yaml_round_trips_through_loader(tmp_path):
    r = m.mapping_to_definition(_MULTI)
    p = tmp_path / "def.yaml"
    p.write_text(r["yaml"], encoding="utf-8")
    defs = load_definitions(p)
    d0 = defs[0]
    assert [s.table for s in d0.inputs] == ["transaction_log", "customer_master", None]
    assert [(o.type, o.file or o.export_as, o.expected) for o in d0.outputs] == [
        ("database", "出A.csv", "正A.csv"), ("file", "出B.sam", "正B.sam")
    ]
    # program 열의 실 배치 경로가 shell_program이 된다.
    assert d0.shell_program == "/opt/job1"


def test_per_item_path_columns_flow_into_definition(tmp_path):
    """격납 패스 열(src_dir·dest_dir·dest_name·expected_dir·tobe_dir)이 yaml→로더로 실린다 (D-036)."""
    csv = (
        "shell_id,kind,type,program,table,file,expected,src_dir,dest_dir,dest_name,"
        "expected_dir,tobe_dir\n"
        "001,input,file,/opt/j,,in.csv,,/mnt/asis/in,/mnt/tobe/in,staged.csv,,\n"
        "001,output,file,,,out.dat,gold.dat,,,,/mnt/asis/out,/mnt/tobe/out\n"
    )
    r = m.mapping_to_definition(csv)
    assert r["ok"]
    p = tmp_path / "def.yaml"
    p.write_text(r["yaml"], encoding="utf-8")
    d = load_definitions(p)[0]
    i = d.inputs[0]
    assert (i.src_dir, i.dest_dir, i.dest_name) == ("/mnt/asis/in", "/mnt/tobe/in", "staged.csv")
    o = d.outputs[0]
    assert (o.expected_dir, o.tobe_dir) == ("/mnt/asis/out", "/mnt/tobe/out")


def test_checklist_key_with_multi_input_merge():
    """checklist를 1차 키로, 한 체크리스트가 입력 여러 개(A·B 병합)→출력 1개를 가질 수 있다 (사용자 시나리오)."""
    csv = (
        "checklist,kind,type,shell,file,table,expected\n"
        "001,input,database,/opt/job1,A.csv,table_a,\n"
        "001,input,database,,B.csv,table_b,\n"
        "001,output,database,,C.csv,table_c,正解C.csv\n"
    )
    r = m.mapping_to_definition(csv)
    assert r["ok"] and r["count"] == 1
    assert r["shells"][0] == {"test_id": "001", "input_count": 2, "output_count": 1}
    doc = yaml.safe_load(r["yaml"])
    t = doc["tests"][0]
    assert [x["table"] for x in t["input"]["tables"]] == ["table_a", "table_b"]
    assert t["execution"]["shell_program"] == "/opt/job1"  # shell 열이 실행 배치로


def test_checklist_column_required():
    """checklist(또는 shell_id) 1차 키 열이 없으면 거부."""
    r = m.mapping_to_definition("kind,type\ninput,database\n")
    assert r["ok"] is False and any("checklist" in e for e in r["errors"])


def test_blank_program_uses_stub_by_first_input_type():
    csv = (
        "shell_id,kind,type,program,table,file,expected\n"
        "001,input,file,,,a.csv,\n"
        "001,output,file,,,a.csv,gold.csv\n"
    )
    r = m.mapping_to_definition(csv)
    doc = yaml.safe_load(r["yaml"])
    assert doc["tests"][0]["execution"]["shell_program"].endswith("run_batch_file.py")


def test_missing_required_column_rejected():
    r = m.mapping_to_definition("shell_id,kind\n001,input\n")  # type 열 없음(file은 선택)
    assert r["ok"] is False and any("必須列" in e for e in r["errors"])


def test_bad_kind_and_type_rejected():
    r = m.mapping_to_definition(
        "shell_id,kind,type,file\n001,sideways,file,a.csv\n001,input,ftp,a.csv\n"
    )
    assert r["ok"] is False
    assert any("kind" in e for e in r["errors"]) and any("type" in e for e in r["errors"])


def test_blank_filenames_autofilled_single_io():
    """1입력·1출력에서 file/expected를 비우면 {shell_id}.csv로 자동 채워진다(내용은 수기, 파일명은 규칙)."""
    csv = (
        "shell_id,kind,type,table\n"
        "001,input,database,trans\n"
        "001,output,database,result\n"
    )
    r = m.mapping_to_definition(csv)
    assert r["ok"]
    t = yaml.safe_load(r["yaml"])["tests"][0]
    assert t["input"]["tables"][0]["csv"] == "001.csv"
    assert t["outputs"][0]["export_as"] == "001.csv"
    assert t["outputs"][0]["expected"] == "001.csv"   # 정답은 To-Be와 같은 이름


def test_autofill_multi_io_uses_table_name():
    """다입력/다출력은 {shell_id}_{테이블명}.csv로 충돌 없이 자동 채움."""
    csv = (
        "shell_id,kind,type,table\n"
        "001,input,database,trans\n"
        "001,input,database,cust\n"
        "001,output,database,res_a\n"
        "001,output,database,res_b\n"
    )
    r = m.mapping_to_definition(csv)
    assert r["ok"]
    t = yaml.safe_load(r["yaml"])["tests"][0]
    assert [x["csv"] for x in t["input"]["tables"]] == ["001_trans.csv", "001_cust.csv"]
    assert [o["export_as"] for o in t["outputs"]] == ["001_res_a.csv", "001_res_b.csv"]
    assert [o["expected"] for o in t["outputs"]] == ["001_res_a.csv", "001_res_b.csv"]


def test_provided_filenames_are_respected():
    """이미 적힌 파일명/정답은 그대로 둔다(자동은 빈 칸만)."""
    csv = (
        "shell_id,kind,type,table,file,expected\n"
        "001,input,database,trans,my_in.csv,\n"
        "001,output,database,res,my_out.csv,my_gold.csv\n"
    )
    r = m.mapping_to_definition(csv)
    t = yaml.safe_load(r["yaml"])["tests"][0]
    assert t["input"]["tables"][0]["csv"] == "my_in.csv"
    assert t["outputs"][0]["export_as"] == "my_out.csv"
    assert t["outputs"][0]["expected"] == "my_gold.csv"


def test_db_input_requires_table():
    csv = (
        "shell_id,kind,type,table,file,expected\n"
        "001,input,database,,a.csv,\n"   # database인데 table 없음
        "001,output,file,,a.csv,g.csv\n"
    )
    r = m.mapping_to_definition(csv)
    assert r["ok"] is False and any("table" in e for e in r["errors"])


def test_shell_without_output_rejected():
    csv = "shell_id,kind,type,file,expected\n001,input,file,a.csv,\n"
    r = m.mapping_to_definition(csv)
    assert r["ok"] is False and any("出力" in e for e in r["errors"])


def test_conflicting_program_within_shell_rejected():
    csv = (
        "shell_id,kind,type,program,file,expected\n"
        "001,input,file,/opt/x,a.csv,\n"
        "001,output,file,/opt/y,a.csv,g.csv\n"
    )
    r = m.mapping_to_definition(csv)
    assert r["ok"] is False and any("program" in e for e in r["errors"])


def test_cli_writes_output_file(tmp_path, capsys):
    src = tmp_path / "map.csv"
    src.write_text(_MULTI, encoding="utf-8")
    out = tmp_path / "gen.yaml"
    rc = m.main([str(src), "-o", str(out)])
    assert rc == 0 and out.is_file()
    assert load_definitions(out)[0].test_id == "001"


def test_cli_reports_errors_and_exits_nonzero(tmp_path):
    src = tmp_path / "bad.csv"
    src.write_text("shell_id,kind,type\n001,input,file\n", encoding="utf-8")  # file 열 없음
    assert m.main([str(src)]) == 1


def test_bundled_example_is_valid(tmp_path):
    """정본 데모셋(samples/complete/complete_sample.csv)이 그대로 변환·round-trip된다(20 CK)."""
    example = Path(__file__).resolve().parents[1] / "samples" / "complete" / "complete_sample.csv"
    r = m.mapping_to_definition(m._decode(example.read_bytes()))
    assert r["ok"] and r["count"] == 20


# --- P0: compare 옵션 / setup / in_encoding 컬럼 운반 (HANDOFF §2·§3) -------------

_P0_CSV = (
    "checklist,test_name,shell,timeout,setup,kind,type,table,file,expected,name,"
    "in_encoding,compare_mode,key,encoding,mask,tolerance,normalize,has_header\n"
    "CK1,merge,batch/m.sh,120,db/reset.sql,input,database,TBL_A,a.csv,,,shift_jis,,,,,,,\n"
    "CK1,,,,,output,database,TBL_C,c.csv,c_exp.dat,C,,record,CUST_ID,utf-8,UPD_TS,0.001,"
    "DT:date;BAL:num:2,true\n"
)


def test_p0_columns_carried_to_yaml():
    """신규 컬럼(setup/in_encoding/compare 9종)이 변환·round-trip된다."""
    r = m.mapping_to_definition(_P0_CSV)
    assert r["ok"], r["errors"]
    doc = yaml.safe_load(r["yaml"])
    t = doc["tests"][0]
    assert t["execution"]["setup"] == "db/reset.sql"
    assert t["input"]["tables"][0]["in_encoding"] == "shift_jis"
    cmp_block = t["outputs"][0]["compare"]
    assert cmp_block["mode"] == "record"
    assert cmp_block["key"] == "CUST_ID"
    assert cmp_block["mask"] == "UPD_TS"
    assert cmp_block["normalize"] == "DT:date;BAL:num:2"
    assert cmp_block["has_header"] is True


def test_p0_invalid_compare_mode_csv_coordinate_error():
    """잘못된 compare_mode는 行番号 포함 CSV 좌표 에러(YAML 노드 아님)."""
    bad = _P0_CSV.replace(",record,", ",bogus,")
    r = m.mapping_to_definition(bad)
    assert not r["ok"]
    assert any("行目" in e and "compare_mode" in e for e in r["errors"])


def test_p0_no_compare_columns_still_byte():
    """비교 컬럼이 비면 compare 블록 없이 byte 기본(현 동작 보존)."""
    csv = (
        "checklist,kind,type,table,file,expected\n"
        "CK9,input,database,TBL,a.csv,\n"
        "CK9,output,file,,o.dat,e.dat\n"
    )
    r = m.mapping_to_definition(csv)
    assert r["ok"], r["errors"]
    doc = yaml.safe_load(r["yaml"])
    assert "compare" not in doc["tests"][0]["outputs"][0]


# --- B: shell_group 칼럼(업무 그룹 태그) ------------------------------------------


def test_shell_group_carried_into_execution(tmp_path):
    """shell_group 열이 execution.shell_group으로 운반되고 로더가 읽는다(B)."""
    csv = (
        "checklist,kind,type,shell,shell_group,file,expected\n"
        "001,input,file,mock/A/ck1.sh,業務A,in.csv,\n"
        "001,output,file,,,out.dat,gold.dat\n"
    )
    r = m.mapping_to_definition(csv)
    assert r["ok"], r["errors"]
    assert yaml.safe_load(r["yaml"])["tests"][0]["execution"]["shell_group"] == "業務A"
    p = tmp_path / "def.yaml"
    p.write_text(r["yaml"], encoding="utf-8")
    assert load_definitions(p)[0].shell_group == "業務A"


def test_shell_group_differs_across_rows_is_error():
    """한 체크리스트가 두 업무에 걸치면 에러(program 일관성과 동일 정책, B-Q3)."""
    csv = (
        "checklist,kind,type,shell_group,file,expected\n"
        "001,input,file,業務A,in.csv,\n"
        "001,output,file,業務B,out.dat,gold.dat\n"
    )
    r = m.mapping_to_definition(csv)
    assert r["ok"] is False and any("shell_group" in e for e in r["errors"])


def test_shell_group_absent_is_backward_compatible(tmp_path):
    """shell_group 열이 없으면 execution에 키 없음·로더 None(하위호환)."""
    csv = (
        "checklist,kind,type,file,expected\n"
        "001,input,file,in.csv,\n"
        "001,output,file,out.dat,gold.dat\n"
    )
    r = m.mapping_to_definition(csv)
    assert r["ok"], r["errors"]
    assert "shell_group" not in r["yaml"]
    p = tmp_path / "def.yaml"
    p.write_text(r["yaml"], encoding="utf-8")
    assert load_definitions(p)[0].shell_group is None


# --- A: 1:N 셸 시퀀스(`;`) 거부 lint + #주석 헤더 허용 ------------------------------


def test_shell_semicolon_sequence_rejected():
    """shell 칸에 ';'(1:N 시퀀스)면 CSV 좌표 에러로 거부(실연결 보류, Q1=a). 실행 아님."""
    csv = (
        "checklist,kind,type,shell,file,expected\n"
        "010,input,file,a.sh;b.sh,in.csv,\n"
        "010,output,file,,out.dat,gold.dat\n"
    )
    r = m.mapping_to_definition(csv)
    assert not r["ok"]
    assert any("行目" in e and "シーケンス" in e and "未対応" in e for e in r["errors"])


def test_leading_comment_lines_skipped():
    """선두 '#' 주석 줄(SAMPLE 경고 헤더)은 건너뛰고 그 다음을 헤더로 파싱."""
    csv = (
        "# SAMPLE — 실데이터 아님. normalize/mask는 형식 예시일 뿐.\n"
        "#\n"
        "checklist,kind,type,file,expected\n"
        "001,input,file,in.csv,\n"
        "001,output,file,out.dat,gold.dat\n"
    )
    r = m.mapping_to_definition(csv)
    assert r["ok"], r["errors"]
    assert r["count"] == 1
