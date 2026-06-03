"""Core 객체 → 표시용 dict 직렬화 (웹 UI 전용, D-028 §②).

이 직렬화는 **GUI 인터페이스의 표시 관심사**이므로 `src/gui/`에만 둔다 — `core/models.py`는
순수 데이터 구조로 유지(인터페이스 무관, CLAUDE 3-1). CLI는 객체를 직접 렌더하므로 불필요하고,
웹은 SSE/JSON으로 브라우저에 보내야 하므로 여기서 dict로 변환한다.
"""

from __future__ import annotations

from src.core.models import ComparisonResult, ProgressEvent, RunSummary


def event_to_dict(event: ProgressEvent) -> dict:
    """ProgressEvent를 JSON 직렬화 가능한 dict로. SHELL_DONE이면 result를 중첩 직렬화."""
    return {
        "kind": event.kind.value,
        "shell_id": event.shell_id,
        "index": event.index,
        "total": event.total,
        "step": event.step,
        "step_status": event.step_status,
        "result": result_to_dict(event.result) if event.result is not None else None,
    }


def result_to_dict(result: ComparisonResult) -> dict:
    """ComparisonResult를 dict로. diff_lines는 표시에 필요한 필드만 펼친다."""
    return {
        "shell_id": result.shell_id,
        "output_name": result.output_name,  # D-033 P2: 다중 출력 식별자(단일/오류는 None)
        "status": result.status.value,
        "error_message": result.error_message,
        "diff_lines": [
            {
                "line_number": d.line_number,
                "asis_content": d.asis_content,
                "tobe_content": d.tobe_content,
            }
            for d in result.diff_lines
        ],
    }


def summary_to_dict(summary: RunSummary, elapsed_seconds: float) -> dict:
    """RunSummary + 소요시간을 요약 카드용 dict로. 리포트는 다운로드용 파일명만 노출."""
    return {
        "total": summary.total,
        "ok_count": summary.ok_count,
        "ng_count": summary.ng_count,
        "error_count": summary.error_count,
        "missing_count": summary.missing_count,
        "elapsed_seconds": round(elapsed_seconds, 1),
        "report_name": summary.report_csv_path.name,
        "report_path": str(summary.report_csv_path),
    }
