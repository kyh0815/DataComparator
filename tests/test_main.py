"""T3-3 CLI 진입점(main) + --shells 파서 테스트.

run_full_comparison/load_config/CliReporter를 monkeypatch해 배선·종료코드·fatal 처리만
검증한다(Core/DB 의존 0 — 항상 실행).
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.cli import main as cli_main
from src.config.settings import ConfigError
from src.config.definition import DefinitionError
from src.core import OrchestratorError
from src.core.models import RunSummary


# --- parse_shell_selector (settings, CLI용) ---------------------------------------


def test_parse_range_inclusive_zero_padded():
    from src.config.settings import parse_shell_selector

    assert parse_shell_selector("1-10") == [f"{n:03d}" for n in range(1, 11)]


def test_parse_comma_list_zero_padded():
    from src.config.settings import parse_shell_selector

    assert parse_shell_selector("1,3,7") == ["001", "003", "007"]


def test_parse_already_padded_ids():
    from src.config.settings import parse_shell_selector

    assert parse_shell_selector("001,002,005") == ["001", "002", "005"]


def test_parse_bad_range_raises():
    from src.config.settings import parse_shell_selector

    with pytest.raises(ConfigError):
        parse_shell_selector("a-b")


# --- main 배선 / 종료코드 ---------------------------------------------------------


def _summary(total, ok, ng=0, error=0, missing=0):
    return RunSummary(
        total=total, ok_count=ok, ng_count=ng, error_count=error, missing_count=missing,
        results=[], report_csv_path=Path("./out/reports/report.csv"),
    )


def _fake_config():
    return SimpleNamespace(
        report_dir=Path("orig_report_dir"),
        output=SimpleNamespace(cli_color=True),
    )


class _FakeReporter:
    instances = []

    def __init__(self, *, use_color, verbose=False, stream=None):
        self.use_color = use_color
        self.verbose = verbose
        self.summary_calls = []
        _FakeReporter.instances.append(self)

    def on_progress(self, event):
        pass

    def print_summary(self, summary, elapsed_seconds):
        self.summary_calls.append((summary, elapsed_seconds))


@pytest.fixture
def wired(monkeypatch):
    """load_config/CliReporter를 가짜로, run_full_comparison을 기록기로 배선한다."""
    _FakeReporter.instances = []
    calls = {}

    def fake_run(config, on_progress=None, shell_ids=None, *, resume=False, retry_failed=False):
        calls["config"] = config
        calls["on_progress"] = on_progress
        calls["shell_ids"] = shell_ids
        calls["resume"] = resume
        calls["retry_failed"] = retry_failed
        return calls.get("summary", _summary(2, 2))

    monkeypatch.setattr(cli_main, "load_config", lambda p: _fake_config())
    monkeypatch.setattr(cli_main, "CliReporter", _FakeReporter)
    monkeypatch.setattr(cli_main, "run_full_comparison", fake_run)
    return calls


def test_exit_zero_when_all_ok(wired):
    wired["summary"] = _summary(3, 3)
    assert cli_main.main(["--config", "c.yaml"]) == 0


def test_exit_one_when_ng_present(wired):
    wired["summary"] = _summary(3, 2, ng=1)
    assert cli_main.main([]) == 1


def test_exit_one_when_missing_present(wired):
    """MISSING도 not-all-OK → 1 (D-026, D-025 종료코드 supersede)."""
    wired["summary"] = _summary(2, 1, missing=1)
    assert cli_main.main([]) == 1


def test_config_error_returns_2(monkeypatch, capsys):
    def _boom(_p):
        raise ConfigError("설정 파일을 찾을 수 없습니다")

    monkeypatch.setattr(cli_main, "load_config", _boom)
    assert cli_main.main(["--config", "missing.yaml"]) == 2
    assert "오류:" in capsys.readouterr().err


def test_definition_error_returns_2(wired, monkeypatch, capsys):
    def _boom(config, on_progress=None, shell_ids=None, **_kw):
        raise DefinitionError("정의 파일이 설정되지 않았습니다")

    monkeypatch.setattr(cli_main, "run_full_comparison", _boom)
    assert cli_main.main([]) == 2
    assert "오류:" in capsys.readouterr().err


def test_orchestrator_error_returns_2(wired, monkeypatch):
    def _boom(config, on_progress=None, shell_ids=None, **_kw):
        raise OrchestratorError("DB 접속 실패")

    monkeypatch.setattr(cli_main, "run_full_comparison", _boom)
    assert cli_main.main([]) == 2


def test_shells_arg_parsed_and_passed(wired):
    cli_main.main(["--shells", "1,3"])
    assert wired["shell_ids"] == ["001", "003"]


def test_no_shells_passes_none(wired):
    cli_main.main([])
    assert wired["shell_ids"] is None


def test_report_dir_override(wired):
    cli_main.main(["--report-dir", "./custom_reports"])
    assert wired["config"].report_dir == Path("./custom_reports").resolve()


def test_verbose_sets_app_logger_debug(wired):
    import logging

    cli_main.main(["--verbose"])
    assert logging.getLogger("src").level == logging.DEBUG
    assert _FakeReporter.instances[-1].verbose is True


# --- C3: --preflight 게이트 종료코드 ---------------------------------------------


class _FakeReport:
    def __init__(self, errors=(), warnings=()):
        self._errors, self._warnings = list(errors), list(warnings)
        self.issues = self._errors + self._warnings

    @property
    def errors(self):
        return self._errors

    @property
    def warnings(self):
        return self._warnings

    @property
    def ok(self):
        return not self._errors


def test_preflight_clean_exits_zero(wired, monkeypatch, capsys):
    """에러 0건이면 통과(0). run_full_comparison은 호출 안 함."""
    monkeypatch.setattr(cli_main, "preflight", lambda config: _FakeReport())
    assert cli_main.main(["--preflight"]) == 0
    assert "config" not in wired  # 실행 단계 미진입


def test_preflight_warning_only_exits_zero(wired, monkeypatch):
    """경고만 있으면 통과(0) — 실행 허용."""
    rep = _FakeReport(warnings=[_issue("warning", "001", "k없음")])
    monkeypatch.setattr(cli_main, "preflight", lambda config: rep)
    assert cli_main.main(["--preflight"]) == 0


def test_preflight_error_exits_two(wired, monkeypatch):
    """에러가 있으면 거부(2) — 실행하지 않음."""
    rep = _FakeReport(errors=[_issue("error", "001", "정답 없음")])
    monkeypatch.setattr(cli_main, "preflight", lambda config: rep)
    assert cli_main.main(["--preflight"]) == 2


def _issue(level, coord, msg):
    from src.core.preflight import PreflightIssue

    return PreflightIssue(level, coord, msg)


# --- C5: 부분 실행 플래그 배선 / 상호배타 ----------------------------------------


def test_resume_flag_passed(wired):
    cli_main.main(["--resume"])
    assert wired["resume"] is True and wired["retry_failed"] is False
    assert wired["shell_ids"] is None


def test_retry_failed_flag_passed(wired):
    cli_main.main(["--retry-failed"])
    assert wired["retry_failed"] is True and wired["resume"] is False


def test_selection_flags_are_mutually_exclusive(wired):
    """--shells/--resume/--retry-failed 동시 사용은 argparse가 거부(SystemExit)."""
    with pytest.raises(SystemExit):
        cli_main.main(["--shells", "1-10", "--resume"])
    with pytest.raises(SystemExit):
        cli_main.main(["--resume", "--retry-failed"])
