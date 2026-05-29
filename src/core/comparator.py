"""두 CSV 출력 파일의 동등성 비교 (이 도구의 심장).

통짜 바이트 비교로 OK/NG를 판정하고, 불일치 시 줄 단위 diff를 추출한다.
판정은 반드시 결정론적 코드로만 한다 (LLM 금지, CLAUDE.md 6장).

판정 원칙:
- OK/NG 판정은 **파일 바이트 완전 일치** 여부로만 결정한다. 디코딩하지 않는다.
- diff 상세(`DiffLine`)의 사람이 볼 내용만 표시용으로 디코딩한다.
  (디코딩 실패 바이트는 errors="replace"로 대체 — 판정에는 영향 없음)
"""

from __future__ import annotations

from itertools import zip_longest
from pathlib import Path

from .models import ComparisonResult, ComparisonStatus, DiffLine


def compare_files(
    asis_path: Path,
    tobe_path: Path,
    encoding: str = "shift_jis",
) -> ComparisonResult:
    """As-Is 출력과 To-Be 출력을 바이트 비교해 ComparisonResult를 반환한다.

    encoding은 diff 줄 내용을 *표시용으로 디코딩*할 때만 쓰인다 (판정은 바이트).
    """
    asis_path = Path(asis_path)
    tobe_path = Path(tobe_path)
    shell_id = _derive_shell_id(asis_path, tobe_path)

    asis_exists = asis_path.is_file()
    tobe_exists = tobe_path.is_file()

    if not asis_exists and not tobe_exists:
        return ComparisonResult(
            shell_id=shell_id,
            status=ComparisonStatus.ERROR,
            error_message=f"비교할 파일이 양쪽 모두 없음: {asis_path}, {tobe_path}",
        )
    if not asis_exists:
        return ComparisonResult(shell_id=shell_id, status=ComparisonStatus.MISSING_ASIS)
    if not tobe_exists:
        return ComparisonResult(shell_id=shell_id, status=ComparisonStatus.MISSING_TOBE)

    asis_bytes = asis_path.read_bytes()
    tobe_bytes = tobe_path.read_bytes()

    # 1차 판정: 통짜 바이트 비교 (D-004).
    if asis_bytes == tobe_bytes:
        return ComparisonResult(shell_id=shell_id, status=ComparisonStatus.OK)

    # NG: 어느 줄이 다른지 위치 기반으로 추출.
    diff_lines = _extract_diff_lines(asis_bytes, tobe_bytes, encoding)
    return ComparisonResult(
        shell_id=shell_id,
        status=ComparisonStatus.NG,
        diff_lines=diff_lines,
    )


def _derive_shell_id(asis_path: Path, tobe_path: Path) -> str:
    """파일명 stem을 셸 ID로 사용한다 (예: 007.csv -> "007"). 존재하는 쪽 우선."""
    if asis_path.is_file():
        return asis_path.stem
    if tobe_path.is_file():
        return tobe_path.stem
    return asis_path.stem


def _extract_diff_lines(asis_bytes: bytes, tobe_bytes: bytes, encoding: str) -> list[DiffLine]:
    """\\n 기준으로 줄을 나눠 위치별로 대조, 다른 줄마다 DiffLine을 만든다.

    짧은 쪽은 없는 줄로 패딩한다 (SPEC 3-2). 줄 단위 비교도 바이트로 하여
    공백·개행(\\r) 차이까지 결정론적으로 잡아낸다.
    """
    asis_raw_lines = asis_bytes.split(b"\n")
    tobe_raw_lines = tobe_bytes.split(b"\n")

    diffs: list[DiffLine] = []
    for index, (a_line, b_line) in enumerate(
        zip_longest(asis_raw_lines, tobe_raw_lines, fillvalue=None)
    ):
        if a_line == b_line:
            continue
        diffs.append(
            DiffLine(
                line_number=index + 1,
                asis_content=_decode_for_display(a_line, encoding),
                tobe_content=_decode_for_display(b_line, encoding),
            )
        )
    return diffs


def _decode_for_display(line: bytes | None, encoding: str) -> str:
    """표시용 디코딩. 없는 줄(None)은 빈 문자열, 끝의 \\r은 표시상 제거."""
    if line is None:
        return ""
    return line.rstrip(b"\r").decode(encoding, errors="replace")
