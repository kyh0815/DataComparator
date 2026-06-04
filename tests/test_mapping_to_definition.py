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
    """동봉 예시(samples/shell_mapping.long.example.csv)가 그대로 변환·round-trip된다."""
    example = Path(__file__).resolve().parents[1] / "samples" / "shell_mapping.long.example.csv"
    r = m.mapping_to_definition(m._decode(example.read_bytes()))
    assert r["ok"] and r["count"] == 2
