"""T1-2 Reporter 단위 테스트.

OK/NG/ERROR/MISSING이 섞인 결과로 generate_report를 호출해 검증한다:
CSV 생성·BOM·행 내용·RunSummary 카운트·상세 .diff 파일.
시각에 의존하지 않도록 파일은 "report_*.csv" 패턴으로 찾는다.
"""

import csv

from src.core.models import ComparisonResult, ComparisonStatus, DiffLine
from src.core.reporter import generate_report


def _mixed_results():
    """OK/NG(1줄)/NG(여러줄)/ERROR/MISSING_ASIS/MISSING_TOBE 혼합."""
    return [
        ComparisonResult("001", ComparisonStatus.OK),
        ComparisonResult(
            "007",
            ComparisonStatus.NG,
            diff_lines=[DiffLine(2, "東京都", "大阪府")],
        ),
        ComparisonResult(
            "009",
            ComparisonStatus.NG,
            diff_lines=[DiffLine(2, "2", "X"), DiffLine(4, "4", "Y")],
        ),
        ComparisonResult("010", ComparisonStatus.ERROR, error_message="배치 실패: 종료코드 1"),
        ComparisonResult("011", ComparisonStatus.MISSING_ASIS),
        ComparisonResult("012", ComparisonStatus.MISSING_TOBE),
    ]


def _read_rows(csv_path):
    """BOM을 utf-8-sig로 해석해 CSV를 dict 리스트로 읽는다."""
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_summary_counts(tmp_path):
    """RunSummary 카운트가 정확하고 total = ok+ng+error+missing."""
    summary = generate_report(_mixed_results(), tmp_path)
    assert summary.total == 6
    assert summary.ok_count == 1
    assert summary.ng_count == 2
    assert summary.error_count == 1
    assert summary.missing_count == 2
    assert (
        summary.total
        == summary.ok_count + summary.ng_count + summary.error_count + summary.missing_count
    )


def test_csv_created_with_bom(tmp_path):
    """report_*.csv가 생성되고 UTF-8 BOM(\\xef\\xbb\\xbf)으로 시작한다."""
    summary = generate_report(_mixed_results(), tmp_path)
    assert summary.report_csv_path.exists()
    assert summary.report_csv_path.name.startswith("report_")
    assert summary.report_csv_path.suffix == ".csv"
    raw = summary.report_csv_path.read_bytes()
    assert raw[:3] == b"\xef\xbb\xbf"


def test_csv_header_and_rows(tmp_path):
    """헤더와 각 status별 행 내용이 SPEC 4-2대로 채워진다."""
    summary = generate_report(_mixed_results(), tmp_path)
    rows = _read_rows(summary.report_csv_path)
    assert len(rows) == 6

    by_id = {r["shell_id"]: r for r in rows}

    ok = by_id["001"]
    assert ok["status"] == "OK"
    assert ok["diff_line_count"] == "0"  # 비교됨 → 차이 0건 명시
    assert ok["first_diff_line"] == "-"  # 해당 없음은 '-'로 명시
    assert ok["error_message"] == "-"

    ng1 = by_id["007"]
    assert ng1["status"] == "NG"
    assert ng1["diff_line_count"] == "1"
    assert ng1["first_diff_line"] == "2"
    assert ng1["first_diff_asis"] == "東京都"
    assert ng1["first_diff_tobe"] == "大阪府"

    ng_multi = by_id["009"]
    assert ng_multi["diff_line_count"] == "2"
    assert ng_multi["first_diff_line"] == "2"  # 첫 차이만 CSV에

    err = by_id["010"]
    assert err["status"] == "ERROR"
    assert err["error_message"] == "배치 실패: 종료코드 1"
    assert err["diff_line_count"] == "-"  # 비교 안 함 → '-'

    assert by_id["011"]["status"] == "MISSING_ASIS"
    assert by_id["012"]["status"] == "MISSING_TOBE"


def test_detail_files(tmp_path):
    """NG만 상세 .diff 파일이 생기고, 여러 줄 차이가 모두 기록된다."""
    summary = generate_report(_mixed_results(), tmp_path)
    details_dir = summary.report_csv_path.parent / (
        summary.report_csv_path.stem + "_details"
    )
    assert details_dir.is_dir()

    # NG인 007, 009만 존재. OK/ERROR/MISSING은 상세 없음.
    diff_files = sorted(p.name for p in details_dir.glob("*.diff"))
    assert diff_files == ["007.diff", "009.diff"]

    text = (details_dir / "009.diff").read_text(encoding="utf-8")
    assert "L2" in text and "L4" in text  # 두 차이 줄 모두 기록
    assert "X" in text and "Y" in text


def test_all_ok_no_details_dir(tmp_path):
    """전부 OK면 상세 디렉토리 자체가 생기지 않는다 (불필요한 산출물 방지)."""
    results = [
        ComparisonResult("001", ComparisonStatus.OK),
        ComparisonResult("002", ComparisonStatus.OK),
    ]
    summary = generate_report(results, tmp_path)
    details_dir = summary.report_csv_path.parent / (
        summary.report_csv_path.stem + "_details"
    )
    assert not details_dir.exists()
    assert summary.ok_count == 2
