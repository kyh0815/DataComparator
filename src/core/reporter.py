"""비교 결과 리스트를 CSV 리포트 + RunSummary 객체로 변환.

CSV는 Excel 호환을 위해 UTF-8 BOM 포함(utf-8-sig). 상세 diff(여러 줄)는
실행마다 별도 디렉토리(`report_{TS}_details/{shell_id}.diff`)에 저장한다 (D-017).

판정 자체는 Comparator(T1-1)가 이미 끝낸 상태이고, 여기서는 *집계·기록*만 한다.
print() 금지 — Core는 구조화된 객체(RunSummary)만 반환한다 (CLAUDE.md 3-1).
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .models import ComparisonResult, ComparisonStatus, RunSummary

# CSV 헤더 (SPEC 4-2). 순서가 곧 컬럼 순서.
_CSV_HEADER = [
    "shell_id",
    "status",
    "diff_line_count",
    "first_diff_line",
    "first_diff_asis",
    "first_diff_tobe",
    "error_message",
]


def generate_report(results: list[ComparisonResult], output_dir: Path) -> RunSummary:
    """비교 결과 리스트를 CSV 리포트로 기록하고 RunSummary를 반환한다.

    output_dir 아래에 타임스탬프가 붙은 `report_{TS}.csv`와, NG 상세를 담는
    `report_{TS}_details/` 디렉토리를 생성한다. 둘은 같은 타임스탬프를 공유한다.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"report_{timestamp}.csv"
    details_dir = output_dir / f"report_{timestamp}_details"

    # UTF-8 BOM(utf-8-sig)으로 기록해야 Excel에서 일본어가 깨지지 않는다 (SPEC 4-2).
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(_CSV_HEADER)
        for result in results:
            writer.writerow(_row_for(result))
            _write_detail(result, details_dir)

    return RunSummary(
        total=len(results),
        ok_count=_count(results, ComparisonStatus.OK),
        ng_count=_count(results, ComparisonStatus.NG),
        error_count=_count(results, ComparisonStatus.ERROR),
        missing_count=_count(results, ComparisonStatus.MISSING_ASIS)
        + _count(results, ComparisonStatus.MISSING_TOBE),
        results=results,
        report_csv_path=csv_path,
    )


def _count(results: list[ComparisonResult], status: ComparisonStatus) -> int:
    """해당 status를 가진 결과 수를 센다."""
    return sum(1 for r in results if r.status == status)


def _row_for(result: ComparisonResult) -> list[str]:
    """한 결과를 CSV 한 행으로 변환한다. 해당 없는 칸은 빈 문자열로 둔다.

    first_diff_* 는 NG일 때 첫 DiffLine의 내용만 담는다 (전체는 별도 .diff 파일).
    """
    diff_count = len(result.diff_lines)
    first = result.diff_lines[0] if result.diff_lines else None
    return [
        result.shell_id,
        result.status.value,
        str(diff_count) if first is not None else "",
        str(first.line_number) if first is not None else "",
        first.asis_content if first is not None else "",
        first.tobe_content if first is not None else "",
        result.error_message or "",
    ]


def _write_detail(result: ComparisonResult, details_dir: Path) -> None:
    """NG 상세 diff를 `{shell_id}.diff` 파일로 기록한다 (diff_lines가 있을 때만).

    디렉토리는 첫 상세 기록이 필요한 시점에 생성한다 (전부 OK면 디렉토리도 안 생김).
    """
    if not result.diff_lines:
        return

    details_dir.mkdir(parents=True, exist_ok=True)
    detail_path = details_dir / f"{result.shell_id}.diff"
    with detail_path.open("w", encoding="utf-8", newline="\n") as f:
        for line in result.diff_lines:
            f.write(f"L{line.line_number}\n")
            f.write(f"  As-Is: {line.asis_content}\n")
            f.write(f"  To-Be: {line.tobe_content}\n")
