"""체크리스트(항목명) → 기입용 매핑 CSV 템플릿 생성 도구 테스트 (D-035 보조, DB 불요)."""

import csv
import io

import tools.checklist_to_template as ct
import tools.mapping_to_definition as m

_CHECKLIST = """\
1) 전각 체크
2) 맥시멈 체크 (200byte)
③ 桁あふれ 체크
- 必須項目 체크
"""


def test_parse_strips_numbering_and_bullets():
    items = ct.parse_checklist(_CHECKLIST)
    assert items == ["전각 체크", "맥시멈 체크 (200byte)", "桁あふれ 체크", "必須項目 체크"]


def test_template_has_block_per_item():
    text = ct.checklist_to_template(_CHECKLIST)
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0] == ct._HEADER
    body = rows[1:]
    # 4항목 × (입력1+출력1) = 8행
    assert len(body) == 8
    # shell_id가 체크리스트 순서대로 001~004, test_name이 항목명으로 박힘
    assert body[0][0] == "001" and body[0][1] == "input" and body[0][8] == "전각 체크"
    assert body[1][0] == "001" and body[1][1] == "output"
    assert body[6][0] == "004" and body[6][8] == "必須項目 체크"


def test_custom_input_output_counts():
    text = ct.checklist_to_template("A\nB\n", inputs=2, outputs=3)
    rows = list(csv.reader(io.StringIO(text)))[1:]
    # 2항목 × (입력2+출력3)=10행. 첫 항목: input,input,output,output,output
    kinds = [r[1] for r in rows[:5]]
    assert kinds == ["input", "input", "output", "output", "output"]
    # test_name은 셸 첫 행에만
    assert rows[0][8] == "A" and rows[1][8] == ""


def test_blank_template_is_rejected_by_mapping():
    """빈 템플릿(미기입)은 변환기가 거부해야(필수칸 비어있음) — 채우라는 신호."""
    text = ct.checklist_to_template(_CHECKLIST)
    r = m.mapping_to_definition(text)
    assert r["ok"] is False  # type/file 등이 비어 거부됨


def test_filled_template_converts_to_yaml():
    """템플릿을 채우면 변환기를 통과하고 체크리스트 순서·이름이 유지된다."""
    filled = (
        "shell_id,io,type,shell,table,input,to_be_output,as_is_output,test_name,timeout\n"
        "001,input,file,/opt/job001.sh,,zenkaku_in.csv,,,전각체크,\n"
        "001,output,file,,,,zenkaku_out.csv,正解_zenkaku.csv,,\n"
        "002,input,file,/opt/job001.sh,,max_in.csv,,,맥시멈체크,\n"
        "002,output,file,,,,max_out.csv,正解_max.csv,,\n"
    )
    r = m.mapping_to_definition(filled)
    assert r["ok"] and r["count"] == 2
    assert [s["test_id"] for s in r["shells"]] == ["001", "002"]
    import yaml
    doc = yaml.safe_load(r["yaml"])
    assert doc["tests"][0]["test_name"] == "전각체크"
    assert doc["tests"][1]["test_name"] == "맥시멈체크"


def test_cli_writes_file(tmp_path):
    src = tmp_path / "checklist.txt"
    src.write_text(_CHECKLIST, encoding="utf-8")
    out = tmp_path / "tmpl.csv"
    assert ct.main([str(src), "-o", str(out)]) == 0
    body = out.read_text(encoding="utf-8-sig")
    assert "전각 체크" in body and "必須項目 체크" in body
