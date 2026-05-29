"""T0-2 데이터 모델 단위 테스트.

dataclass 생성·기본값·필드 접근만 검증한다 (로직 없음).
"""

from pathlib import Path

from src.core.models import (
    BatchConfig,
    ComparisonResult,
    ComparisonStatus,
    Config,
    DatabaseConfig,
    DiffLine,
    OutputConfig,
    RunSummary,
    ShellPair,
)


def test_comparison_result_defaults():
    """ComparisonResult는 diff_lines 기본값이 빈 리스트, error_message는 None."""
    r = ComparisonResult(shell_id="001", status=ComparisonStatus.OK)
    assert r.diff_lines == []
    assert r.error_message is None
    # 기본 리스트가 인스턴스 간 공유되지 않아야 함
    r.diff_lines.append(DiffLine(1, "a", "b"))
    r2 = ComparisonResult(shell_id="002", status=ComparisonStatus.OK)
    assert r2.diff_lines == []


def test_comparison_status_is_str():
    """상태 enum은 문자열로 직렬화된다 (CSV 호환)."""
    assert ComparisonStatus.NG == "NG"
    assert ComparisonStatus.NG.value == "NG"


def test_shell_pair_and_diffline_fields():
    """ShellPair / DiffLine 필드 접근."""
    pair = ShellPair("007", Path("asis/007.csv"), Path("tobe/007.csv"))
    assert pair.shell_id == "007"
    assert pair.asis_output_path == Path("asis/007.csv")

    d = DiffLine(line_number=12, asis_content="東京都", tobe_content="東京 都")
    assert d.line_number == 12
    assert d.tobe_content == "東京 都"


def test_config_composition():
    """Config가 중첩 설정 객체들을 담는다."""
    cfg = Config(
        encoding="Shift_JIS",
        asis_input_dir=Path("./samples/asis/input"),
        asis_output_dir=Path("./samples/asis/output"),
        tobe_output_dir=Path("./out/tobe_output"),
        report_dir=Path("./out/reports"),
        database=DatabaseConfig(host="localhost", port=5432, dbname="compare_proto", user="postgres"),
        batch=BatchConfig(),
        shell_ids=["001", "002", "003"],
        output=OutputConfig(),
    )
    assert cfg.encoding == "Shift_JIS"
    assert cfg.database.password_env == "POSTGRES_PASSWORD"
    assert cfg.batch.type == "stub"
    assert cfg.output.report_with_bom is True
    assert cfg.shell_ids[0] == "001"


def test_run_summary_fields():
    """RunSummary 카운트·결과 리스트 접근."""
    s = RunSummary(
        total=10,
        ok_count=6,
        ng_count=2,
        error_count=1,
        missing_count=1,
        results=[ComparisonResult("001", ComparisonStatus.OK)],
        report_csv_path=Path("./out/reports/report.csv"),
    )
    assert s.total == 10
    assert s.missing_count == 1
    assert len(s.results) == 1
