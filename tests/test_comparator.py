"""T1-1 Comparator 단위 테스트.

DoD의 케이스를 모두 커버한다:
동일 → OK / 한 줄 다름 → NG(1) / 여러 줄 다름 → NG(N) /
한쪽만 존재 → MISSING_* / 빈 vs 빈 → OK / 빈 vs 한 줄 → NG.
"""

from pathlib import Path

import pytest

from src.core.comparator import compare_files
from src.core.models import ComparisonStatus


def _write(path: Path, content: bytes) -> Path:
    path.write_bytes(content)
    return path


def test_identical_files_ok(tmp_path):
    """동일한 내용 → OK, diff 없음."""
    data = "あ,東京\nい,大阪\n".encode("shift_jis")
    asis = _write(tmp_path / "001.csv", data)
    tobe = _write(tmp_path / "tobe_001.csv", data)

    result = compare_files(asis, tobe)
    assert result.status == ComparisonStatus.OK
    assert result.diff_lines == []
    assert result.shell_id == "001"


def test_one_line_diff_ng(tmp_path):
    """한 줄만 다름 → NG, diff_lines 1개. 내용이 디코딩되어 담긴다."""
    asis = _write(tmp_path / "007.csv", "a\n東京都\nc\n".encode("shift_jis"))
    tobe = _write(tmp_path / "tobe_007.csv", "a\n大阪府\nc\n".encode("shift_jis"))

    result = compare_files(asis, tobe)
    assert result.status == ComparisonStatus.NG
    assert len(result.diff_lines) == 1
    d = result.diff_lines[0]
    assert d.line_number == 2
    assert d.asis_content == "東京都"
    assert d.tobe_content == "大阪府"


def test_multiple_line_diff_ng(tmp_path):
    """여러 줄 다름 → NG, diff_lines N개."""
    asis = _write(tmp_path / "009.csv", "1\n2\n3\n4\n".encode("shift_jis"))
    tobe = _write(tmp_path / "tobe_009.csv", "1\nX\n3\nY\n".encode("shift_jis"))

    result = compare_files(asis, tobe)
    assert result.status == ComparisonStatus.NG
    assert len(result.diff_lines) == 2
    assert [d.line_number for d in result.diff_lines] == [2, 4]


def test_missing_tobe(tmp_path):
    """To-Be 파일 없음 → MISSING_TOBE."""
    asis = _write(tmp_path / "002.csv", b"data\n")
    tobe = tmp_path / "tobe_002.csv"  # 생성 안 함

    result = compare_files(asis, tobe)
    assert result.status == ComparisonStatus.MISSING_TOBE
    assert result.shell_id == "002"


def test_missing_asis(tmp_path):
    """As-Is 파일 없음 → MISSING_ASIS. 셸 ID는 존재하는 To-Be에서 유도."""
    asis = tmp_path / "003.csv"  # 생성 안 함
    tobe = _write(tmp_path / "003_tobe.csv", b"data\n")

    result = compare_files(asis, tobe)
    assert result.status == ComparisonStatus.MISSING_ASIS


def test_both_missing_error(tmp_path):
    """양쪽 모두 없음 → ERROR (방어적; 정상 흐름에선 오케스트레이터가 제외)."""
    result = compare_files(tmp_path / "x.csv", tmp_path / "y.csv")
    assert result.status == ComparisonStatus.ERROR
    assert result.error_message


def test_empty_vs_empty_ok(tmp_path):
    """빈 파일 vs 빈 파일 → OK."""
    asis = _write(tmp_path / "004.csv", b"")
    tobe = _write(tmp_path / "tobe_004.csv", b"")

    result = compare_files(asis, tobe)
    assert result.status == ComparisonStatus.OK


def test_empty_vs_one_line_ng(tmp_path):
    """빈 파일 vs 한 줄 → NG, diff 1개."""
    asis = _write(tmp_path / "005.csv", b"")
    tobe = _write(tmp_path / "tobe_005.csv", b"line1")

    result = compare_files(asis, tobe)
    assert result.status == ComparisonStatus.NG
    assert len(result.diff_lines) == 1
    assert result.diff_lines[0].asis_content == ""
    assert result.diff_lines[0].tobe_content == "line1"


def test_whitespace_diff_is_ng(tmp_path):
    """공백 차이도 바이트가 다르면 NG (008 가짜처럼 보이는 NG 시연 대응)."""
    asis = _write(tmp_path / "008.csv", "東京都千代田区\n".encode("shift_jis"))
    tobe = _write(tmp_path / "tobe_008.csv", "東京都 千代田区\n".encode("shift_jis"))

    result = compare_files(asis, tobe)
    assert result.status == ComparisonStatus.NG
    assert len(result.diff_lines) == 1


def test_no_decode_for_judgment(tmp_path):
    """판정은 바이트 기준 — 디코딩 불가 바이트가 있어도 예외 없이 동작."""
    asis = _write(tmp_path / "006.csv", b"\xff\xfe\x00bad\n")
    tobe = _write(tmp_path / "tobe_006.csv", b"\xff\xfe\x00bad\n")
    assert compare_files(asis, tobe).status == ComparisonStatus.OK

    tobe2 = _write(tmp_path / "tobe_006b.csv", b"\xff\xfe\x01bad\n")
    result = compare_files(asis, tobe2)
    assert result.status == ComparisonStatus.NG  # 디코딩 실패해도 판정·diff 생성됨
    assert len(result.diff_lines) >= 1
