"""T3-2 CLI 출력 모듈(output.py) 테스트.

ProgressEvent를 mock으로 주입하고 io.StringIO로 출력을 캡처해 포맷·색·verbose·요약을
검증한다. Core/DB 의존 0 — 항상 실행.
"""

import io
from pathlib import Path

from src.cli.output import CliReporter, should_use_color
from src.core.models import (
    ComparisonResult,
    ComparisonStatus,
    DiffLine,
    ProgressEvent,
    ProgressKind,
    RunSummary,
)


def _reporter(use_color=False, verbose=False):
    buf = io.StringIO()
    return CliReporter(use_color=use_color, verbose=verbose, stream=buf), buf


def _start(shell_id="001", index=1, total=3):
    return ProgressEvent(ProgressKind.SHELL_START, shell_id, index, total)


def _step(step, status, shell_id="001", index=1, total=3):
    return ProgressEvent(
        ProgressKind.STEP, shell_id, index, total, step=step, step_status=status
    )


def _done(result, shell_id="001", index=1, total=3):
    return ProgressEvent(ProgressKind.SHELL_DONE, shell_id, index, total, result=result)


def _feed(reporter, events):
    for e in events:
        reporter.on_progress(e)


class _FakeTTY:
    def __init__(self, isatty):
        self._isatty = isatty

    def isatty(self):
        return self._isatty


# --- should_use_color (SPEC 9) ----------------------------------------------------


def test_color_disabled_when_config_off():
    assert should_use_color(False, _FakeTTY(True)) is False


def test_color_disabled_when_no_color_env(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert should_use_color(True, _FakeTTY(True)) is False


def test_color_disabled_when_not_tty(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert should_use_color(True, _FakeTTY(False)) is False


def test_color_enabled_when_all_conditions_met(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert should_use_color(True, _FakeTTY(True)) is True


def test_no_color_when_stream_has_no_isatty(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert should_use_color(True, io.StringIO()) is False  # StringIO.isatty()는 False


# --- 진행 렌더링 (SPEC 5-1) -------------------------------------------------------


def test_ok_shell_render():
    rep, buf = _reporter()
    result = ComparisonResult("001", ComparisonStatus.OK)
    _feed(rep, [_start(), _step("load", "OK"), _step("run", "OK"),
               _step("compare", "OK"), _done(result)])
    out = buf.getvalue()
    assert "[1/3] 001번 셸 처리 중..." in out
    assert "▸ 입력 적재 → OK" in out
    assert "▸ 배치 실행 → OK" in out
    assert "▸ 결과 비교 → OK ✓" in out


def test_ng_shell_render_first_diff_only():
    rep, buf = _reporter()
    diffs = [
        DiffLine(12, "東京都千代田区", "東京都 千代田区"),
        DiffLine(20, "abc", "abd"),
        DiffLine(31, "x", "y"),
    ]
    result = ComparisonResult("002", ComparisonStatus.NG, diff_lines=diffs)
    _feed(rep, [_start("002", 2, 3), _step("load", "OK", "002", 2, 3),
               _step("run", "OK", "002", 2, 3), _done(result, "002", 2, 3)])
    out = buf.getvalue()
    assert "▸ 결과 비교 → NG ✗   (3개 줄 차이)" in out
    assert "└─ 첫 차이: 12행" in out
    assert "As-Is: 東京都千代田区" in out
    assert "To-Be: 東京都 千代田区" in out
    # 기본 모드: 첫 차이만 — 둘째/셋째 줄 내용은 나오지 않는다(silent하지 않게 개수는 표기됨).
    assert "20행" not in out and "31행" not in out


def test_ng_verbose_shows_all_diffs():
    rep, buf = _reporter(verbose=True)
    diffs = [DiffLine(12, "a", "b"), DiffLine(20, "c", "d")]
    result = ComparisonResult("002", ComparisonStatus.NG, diff_lines=diffs)
    _feed(rep, [_start("002"), _done(result, "002")])
    out = buf.getvalue()
    assert "12행" in out and "20행" in out
    assert "├─" in out and "└─" in out  # 마지막만 └─, 나머지 ├─


def test_error_shell_render():
    rep, buf = _reporter()
    result = ComparisonResult(
        "010", ComparisonStatus.ERROR, error_message="배치 실행 실패(종료코드 1)"
    )
    _feed(rep, [_start("010"), _step("load", "OK"),
               _step("run", "ERROR"), _done(result, "010")])
    out = buf.getvalue()
    assert "▸ 배치 실행 → ERROR" in out
    assert "└─ 오류: 배치 실행 실패(종료코드 1)" in out
    # ERROR엔 '결과 비교' 판정 줄을 만들지 않는다(D-025).
    assert "결과 비교" not in out


def test_missing_tobe_render():
    rep, buf = _reporter()
    result = ComparisonResult("005", ComparisonStatus.MISSING_TOBE)
    _feed(rep, [_start("005"), _done(result, "005")])
    out = buf.getvalue()
    assert "▸ 결과 비교 → MISSING_TOBE" in out
    assert "To-Be 출력이 없습니다" in out


# --- 색 on/off -------------------------------------------------------------------


def test_ansi_present_when_color_on():
    rep, buf = _reporter(use_color=True)
    _feed(rep, [_start(), _done(ComparisonResult("001", ComparisonStatus.OK))])
    assert "\033[32m" in buf.getvalue()  # 초록


def test_no_ansi_when_color_off():
    rep, buf = _reporter(use_color=False)
    _feed(rep, [_start(), _step("load", "OK"),
               _done(ComparisonResult("001", ComparisonStatus.OK))])
    assert "\033[" not in buf.getvalue()


def test_blank_line_between_shells():
    rep, buf = _reporter()
    _feed(rep, [_start("001", 1, 2), _start("002", 2, 2)])
    lines = buf.getvalue().split("\n")
    # 두 번째 셸 헤더 앞에 빈 줄이 들어간다.
    assert "" in lines


# --- 최종 요약 (SPEC 5-2, D-016) --------------------------------------------------


def test_summary_format_and_counts():
    rep, buf = _reporter()
    summary = RunSummary(
        total=10, ok_count=6, ng_count=3, error_count=1, missing_count=0,
        results=[], report_csv_path=Path("./out/reports/report_20250515_103000.csv"),
    )
    rep.print_summary(summary, 12.4)
    out = buf.getvalue()
    assert "완료: 총 10건 / OK 6 / NG 3 / ERROR 1 / MISSING 0" in out
    assert "소요: 12.4초" in out
    assert "report_20250515_103000.csv" in out
    assert "═" in out


def test_summary_sum_identity_d016():
    """합 항등(D-016): total == ok+ng+error+missing 가 요약에 그대로 드러난다."""
    rep, buf = _reporter()
    summary = RunSummary(
        total=4, ok_count=1, ng_count=1, error_count=1, missing_count=1,
        results=[], report_csv_path=Path("r.csv"),
    )
    rep.print_summary(summary, 1.0)
    assert "총 4건 / OK 1 / NG 1 / ERROR 1 / MISSING 1" in buf.getvalue()
