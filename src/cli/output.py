"""터미널 출력 담당 (Interface Layer) — T3-2.

Core(orchestrator)가 던지는 ProgressEvent를 받아 진행 상황을, RunSummary를 받아 최종
요약을 사람이 보기 좋게 출력*만* 한다. Core 로직·DB 의존 없음(순수 표시). print는 여기서만
한다(Core는 print 금지, CLAUDE.md 3-1).

설계 결정은 DECISIONS.md D-025 참조:
- load/run 단계 줄은 STEP 이벤트로 실시간 렌더하되, **"결과 비교" 판정 줄(상태·개수·첫 차이)은
  SHELL_DONE.result에서 렌더**한다. diff_lines가 STEP(compare)엔 없고 result에만 있기 때문
  (계약 단일 출처 — silent drop 차단). STEP(compare)는 표시에 쓰지 않는다.
- 색은 config.output.cli_color AND (NO_COLOR 미설정) AND stream.isatty() 3중 가드(SPEC 9).
- verbose는 '모든 diff 줄 + 전체 error_message'로 한정. 배치 stdout/SQL 로그는 이벤트 계약에
  없어 T3-2 범위 밖(T3-3에서 logging으로 배선, D-025).
- 소요 시간은 인터페이스(T3-3)가 측정해 print_summary로 주입한다(타이밍 단일 출처).
"""

from __future__ import annotations

import os
import sys

from src.core.models import (
    ComparisonResult,
    ComparisonStatus,
    ProgressEvent,
    ProgressKind,
    RunSummary,
)

# ANSI 색상 코드. use_color=False면 _c가 원문을 그대로 돌려줘 무채색이 된다.
_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_RESET = "\033[0m"

# 진행 줄 들여쓰기(SPEC 5-1: 7칸).
_INDENT = " " * 7

# STEP 단계명 → 사람이 읽는 라벨(compare는 SHELL_DONE에서 렌더하므로 여기 없음).
_STEP_LABELS = {"load": "입력 적재", "run": "배치 실행"}

_SUMMARY_RULE = "═" * 43


def should_use_color(config_color: bool, stream) -> bool:
    """색을 쓸지 결정한다 — config 허용 AND NO_COLOR 미설정 AND TTY (SPEC 9).

    셋 중 하나라도 어긋나면 무채색. 파이프/파일 리다이렉트로 ANSI가 새는 것을 막는다.
    """
    if not config_color:
        return False
    if "NO_COLOR" in os.environ:
        return False
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


class CliReporter:
    """진행 콜백(on_progress)과 최종 요약 출력을 담당하는 표시기.

    이벤트마다 즉시 출력해 실시간 진행을 보인다(SPEC 9). 모든 이벤트가 index/total을
    운반하므로 셸 간 상태를 들지 않는다(무상태).
    """

    def __init__(self, *, use_color: bool, verbose: bool = False, stream=None) -> None:
        self._use_color = use_color
        self._verbose = verbose
        self._stream = stream if stream is not None else sys.stdout

    # --- 진행 표시 (SPEC 5-1) ----------------------------------------------------

    def on_progress(self, event: ProgressEvent) -> None:
        """run_full_comparison(on_progress=...)에 넘기는 콜백. 이벤트 종류별로 분기한다."""
        if event.kind is ProgressKind.SHELL_START:
            self._on_shell_start(event)
        elif event.kind is ProgressKind.STEP:
            self._on_step(event)
        elif event.kind is ProgressKind.SHELL_DONE:
            self._on_shell_done(event)

    def _on_shell_start(self, event: ProgressEvent) -> None:
        if event.index > 1:
            self._print("")  # 셸 사이 빈 줄
        self._print(f"[{event.index}/{event.total}] {event.shell_id}번 셸 처리 중...")

    def _on_step(self, event: ProgressEvent) -> None:
        # compare 단계는 SHELL_DONE.result에서 렌더한다(diff 상세가 거기에만 있음, D-025).
        label = _STEP_LABELS.get(event.step)
        if label is None:
            return
        if event.step_status == "ERROR":
            self._print(f"{_INDENT}▸ {label} → {self._c('ERROR', _YELLOW)}")
        else:
            self._print(f"{_INDENT}▸ {label} → {self._c('OK', _GREEN)}")

    def _on_shell_done(self, event: ProgressEvent) -> None:
        result = event.result
        if result is None:  # 방어적: SHELL_DONE엔 항상 result가 온다.
            return
        status = result.status
        if status is ComparisonStatus.OK:
            self._print(f"{_INDENT}▸ 결과 비교 → {self._c('OK ✓', _GREEN)}")
        elif status is ComparisonStatus.NG:
            self._render_ng(result)
        elif status in (ComparisonStatus.MISSING_TOBE, ComparisonStatus.MISSING_ASIS):
            self._render_missing(status)
        elif status is ComparisonStatus.ERROR:
            # 판정 줄은 없다 — 실패 단계 STEP이 이미 '→ ERROR'를 표시했다(D-025).
            self._print(f"{_INDENT}└─ {self._c('오류', _YELLOW)}: {result.error_message or ''}")

    def _render_ng(self, result: ComparisonResult) -> None:
        n = len(result.diff_lines)
        self._print(f"{_INDENT}▸ 결과 비교 → {self._c('NG ✗', _RED)}   ({n}개 줄 차이)")
        if not result.diff_lines:
            return
        # 기본은 첫 차이만, verbose면 모든 차이 줄(SPEC 5-3에서 받을 수 있는 유일 항목).
        lines = result.diff_lines if self._verbose else result.diff_lines[:1]
        for i, dl in enumerate(lines):
            last = i == len(lines) - 1
            connector = "└─" if last else "├─"
            head = "첫 차이" if (i == 0 and not self._verbose) else "차이"
            self._print(f"{_INDENT}{connector} {head}: {dl.line_number}행")
            self._print(f"{_INDENT}   As-Is: {dl.asis_content}")
            self._print(f"{_INDENT}   To-Be: {dl.tobe_content}")

    def _render_missing(self, status: ComparisonStatus) -> None:
        note = (
            "To-Be 출력이 없습니다"
            if status is ComparisonStatus.MISSING_TOBE
            else "As-Is 정답지가 없습니다"
        )
        self._print(f"{_INDENT}▸ 결과 비교 → {self._c(status.value, _YELLOW)}")
        self._print(f"{_INDENT}└─ {note}")

    # --- 최종 요약 (SPEC 5-2) ----------------------------------------------------

    def print_summary(self, summary: RunSummary, elapsed_seconds: float) -> None:
        """전체 실행 요약을 출력한다. elapsed_seconds는 인터페이스(T3-3)가 측정해 넘긴다."""
        counts = (
            f"총 {summary.total}건 / "
            f"OK {self._c(str(summary.ok_count), _GREEN)} / "
            f"NG {self._c(str(summary.ng_count), _RED)} / "
            f"ERROR {self._c(str(summary.error_count), _YELLOW)} / "
            f"MISSING {summary.missing_count}"
        )
        self._print("")
        self._print(_SUMMARY_RULE)
        self._print(f"  완료: {counts}")
        self._print(f"  소요: {elapsed_seconds:.1f}초")
        self._print(f"  리포트: {summary.report_csv_path}")
        self._print(_SUMMARY_RULE)

    # --- 내부 헬퍼 ---------------------------------------------------------------

    def _c(self, text: str, color: str) -> str:
        """use_color일 때만 색을 입힌다. 아니면 원문 그대로(파이프/NO_COLOR 안전)."""
        return f"{color}{text}{_RESET}" if self._use_color else text

    def _print(self, text: str) -> None:
        print(text, file=self._stream)
