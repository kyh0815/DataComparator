"""C4 試験成績書(evidence) 단위 테스트 — 全件=정의기준·未実行·消化率·출처(run_id)·MISSING 분리."""

from pathlib import Path

import pytest

from src.core import evidence
from src.core.models import ComparisonResult, ComparisonStatus, OutputSpec, ShellDefinition
from src.core.store import ShellRecord


def _def(test_id, outputs):
    return ShellDefinition(
        test_id=test_id,
        test_name=f"試験{test_id}",
        input_type="file",
        input_csv=f"{test_id}.csv",
        output_type=outputs[0].type,
        expected_output_csv=outputs[0].expected,
        shell_program="b.sh",
        outputs=outputs,
    )


def _out(expected, name=None):
    return OutputSpec(type="file", expected=expected, file="o.dat", name=name)


def _rec(shell_id, run_id, results):
    return ShellRecord(shell_id=shell_id, results=results, run_id=run_id)


def test_build_rows_marks_unrun(  # 정의엔 있으나 실적 없는 항목 = 未実行
    tmp_path,
):
    defs = [_def("001", [_out("e1.dat")]), _def("002", [_out("e2.dat")])]
    records = [_rec("001", "20260605_100000", [ComparisonResult("001", ComparisonStatus.OK)])]
    rows = evidence.build_rows(defs, records)
    by_id = {r.test_id: r for r in rows}
    assert by_id["001"].status == "OK" and by_id["001"].run_id == "20260605_100000"
    assert by_id["002"].status == "未実行" and by_id["002"].run_id == "-"


def test_summarize_counts_and_rate():
    defs = [
        _def("001", [_out("e1")]),
        _def("002", [_out("e2")]),
        _def("003", [_out("e3")]),
        _def("004", [_out("e4")]),
    ]
    records = [
        _rec("001", "r1", [ComparisonResult("001", ComparisonStatus.OK)]),
        _rec("002", "r1", [ComparisonResult("002", ComparisonStatus.NG)]),
        _rec("003", "r1", [ComparisonResult("003", ComparisonStatus.MISSING_ASIS)]),
        # 004 미실행
    ]
    s = evidence.summarize(evidence.build_rows(defs, records))
    assert s["total"] == 4
    assert s["counts"]["OK"] == 1 and s["counts"]["NG"] == 1
    assert s["counts"]["MISSING_ASIS"] == 1
    assert s["not_run"] == 1 and s["done"] == 3
    assert s["rate"] == pytest.approx(75.0)  # 実施 3 / 全件 4


def test_multi_output_keys_by_label():
    """다중 출력 셸: output_name=라벨로 항목 키 매칭(orchestrator 규약)."""
    defs = [_def("001", [_out("eA", name="A"), _out("eB", name="B")])]
    records = [_rec("001", "r1", [
        ComparisonResult("001", ComparisonStatus.OK, output_name="A"),
        ComparisonResult("001", ComparisonStatus.NG, output_name="B"),
    ])]
    rows = evidence.build_rows(defs, records)
    by_item = {r.item: r.status for r in rows}
    assert by_item["A"] == "OK" and by_item["B"] == "NG"


def test_generate_xlsx_three_sheets(tmp_path):
    """실제 .xlsx 생성 — 要約/明細/差分明細 3시트, 全件·消化率·출처가 셀에 들어간다."""
    openpyxl = pytest.importorskip("openpyxl")
    defs = [_def("001", [_out("e1")]), _def("002", [_out("e2")])]
    records = [_rec("001", "20260605_120000", [
        ComparisonResult("001", ComparisonStatus.NG, diff_lines=[])
    ])]
    out = evidence.generate_evidence(defs, records, tmp_path / "ev.xlsx")
    assert out.is_file()

    wb = openpyxl.load_workbook(out)
    assert wb.sheetnames == ["要約", "明細", "差分明細"]
    summary_text = "\n".join(
        str(c.value) for row in wb["要約"].iter_rows() for c in row if c.value is not None
    )
    assert "全件" in summary_text and "消化率" in summary_text

    detail = wb["明細"]
    header = [c.value for c in detail[1]]
    assert header == ["チェックリスト", "試験名", "項目", "状態", "結果時刻", "差異内容"]
    # 002는 未実行 행으로 존재
    statuses = [row[3].value for row in detail.iter_rows(min_row=2)]
    assert "NG" in statuses and "未実行" in statuses
    # 출처(run_id)가 NG 행에 박혀 있다(낡은 OK 위장 방지)
    runids = [row[4].value for row in detail.iter_rows(min_row=2)]
    assert "20260605_120000" in runids


def test_diff_detail_sheet_lists_all_ng_lines(tmp_path):
    """差分明細 = NG의 모든 차이 줄(어느 行이 現→新으로 — 감사용 전건)."""
    from src.core.models import DiffLine
    openpyxl = pytest.importorskip("openpyxl")
    defs = [_def("001", [_out("e1")])]
    records = [_rec("001", "20260605_120000", [
        ComparisonResult("001", ComparisonStatus.NG,
                         diff_lines=[DiffLine(2, "AAA", "AAB"), DiffLine(5, "100", "200")])
    ])]
    out = evidence.generate_evidence(defs, records, tmp_path / "ev.xlsx")
    ws = openpyxl.load_workbook(out)["差分明細"]
    assert [c.value for c in ws[1]] == ["チェックリスト", "試験名", "項目", "行", "As-Is(現)", "To-Be(新)"]
    vals = [(r[3].value, r[4].value, r[5].value) for r in ws.iter_rows(min_row=2)]
    assert ("L2", "AAA", "AAB") in vals and ("L5", "100", "200") in vals  # 전 차이 줄
