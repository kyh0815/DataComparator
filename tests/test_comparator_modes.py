"""P0 비교기 모드 단위 테스트 (HANDOFF §2): byte 스트리밍 / text / record + 정규화.

기존 test_comparator.py(byte 기본 동작)는 그대로 두고, 모드·정규화·정합을 여기서 보호한다.
"""

from pathlib import Path

import pytest

from src.core import comparator
from src.core.comparator import compare_files
from src.core.models import CompareOptions, ComparisonStatus


def _w(path: Path, text: str, encoding: str = "utf-8") -> Path:
    path.write_bytes(text.encode(encoding))
    return path


def _opts(**kw) -> CompareOptions:
    kw.setdefault("encoding", "utf-8")
    return CompareOptions.from_raw(**kw)


# --- byte 모드 (청크 스트리밍) ---------------------------------------------------


def test_byte_default_unchanged_ok(tmp_path):
    """opts 미지정(byte 기본)·encoding= 호환 경로 — 동일 파일 OK."""
    a = _w(tmp_path / "001.csv", "あ\nい\n", "shift_jis")
    b = _w(tmp_path / "t001.csv", "あ\nい\n", "shift_jis")
    assert compare_files(a, b).status == ComparisonStatus.OK
    assert compare_files(a, b, encoding="shift_jis").status == ComparisonStatus.OK


def test_byte_streaming_large_equal(tmp_path):
    """청크 경계(>1MiB)를 넘는 큰 동일 파일도 OK(통째 적재 안 함)."""
    big = "x" * (3 * (1 << 20)) + "\n"
    a = _w(tmp_path / "a.csv", big)
    b = _w(tmp_path / "b.csv", big)
    assert compare_files(a, b, _opts(mode="byte")).status == ComparisonStatus.OK


def test_byte_diff_capped(tmp_path):
    """바이트 NG diff는 최대 50건으로 제한(대용량 무한 덤프 방지)."""
    a = _w(tmp_path / "a.csv", "\n".join(str(i) for i in range(200)) + "\n")
    b = _w(tmp_path / "b.csv", "\n".join("X" for _ in range(200)) + "\n")
    r = compare_files(a, b, _opts(mode="byte"))
    assert r.status == ComparisonStatus.NG
    assert len(r.diff_lines) == 50


# --- text 모드 -------------------------------------------------------------------


def test_text_crlf_and_trailing_space_ok(tmp_path):
    """줄끝(CRLF/LF) 정규화 + 우측 공백 trim 후 동일 → OK(byte였다면 NG)."""
    a = _w(tmp_path / "a.txt", "alpha\r\nbeta  \r\n")
    b = _w(tmp_path / "b.txt", "alpha\nbeta\n")
    assert compare_files(a, b, _opts(mode="text")).status == ComparisonStatus.OK
    assert compare_files(a, b, _opts(mode="byte")).status == ComparisonStatus.NG


def test_text_real_diff_ng(tmp_path):
    a = _w(tmp_path / "a.txt", "x\ny\n")
    b = _w(tmp_path / "b.txt", "x\nZ\n")
    r = compare_files(a, b, _opts(mode="text"))
    assert r.status == ComparisonStatus.NG and len(r.diff_lines) == 1
    assert r.diff_lines[0].line_number == 2


# --- record 모드: key 정렬·정합 ---------------------------------------------------


def test_record_key_order_independent_ok(tmp_path):
    """행 순서가 달라도 key 정렬 후 같으면 OK(DB 비결정 순서 false-NG 차단)."""
    a = _w(tmp_path / "a.csv", "ID,NAME\n1,alice\n2,bob\n")
    b = _w(tmp_path / "b.csv", "ID,NAME\n2,bob\n1,alice\n")
    r = compare_files(a, b, _opts(mode="record", key="ID", has_header="true"))
    assert r.status == ComparisonStatus.OK


def test_record_key_by_index_no_header(tmp_path):
    """has_header=false면 key는 인덱스. 순서 무관 OK."""
    a = _w(tmp_path / "a.csv", "1,alice\n2,bob\n")
    b = _w(tmp_path / "b.csv", "2,bob\n1,alice\n")
    r = compare_files(a, b, _opts(mode="record", key="0"))
    assert r.status == ComparisonStatus.OK


def test_record_missing_and_extra_key_ng(tmp_path):
    """한쪽에만 있는 key는 NG diff로 잡힌다(머지조인)."""
    a = _w(tmp_path / "a.csv", "ID,V\n1,a\n2,b\n")
    b = _w(tmp_path / "b.csv", "ID,V\n1,a\n3,c\n")
    r = compare_files(a, b, _opts(mode="record", key="ID", has_header="true"))
    assert r.status == ComparisonStatus.NG
    assert len(r.diff_lines) == 2  # 2(As-Is만) + 3(To-Be만)


def test_record_header_column_reorder_tolerant(tmp_path):
    """컬럼 순서가 바뀌어도 헤더 이름으로 정합 → OK(Q3 순서변경 내성)."""
    a = _w(tmp_path / "a.csv", "ID,NAME\n1,alice\n")
    b = _w(tmp_path / "b.csv", "NAME,ID\nalice,1\n")
    r = compare_files(a, b, _opts(mode="record", key="ID", has_header="true"))
    assert r.status == ComparisonStatus.OK


# --- record 모드: mask / tolerance / normalize / layout --------------------------


def test_record_mask_ignores_column(tmp_path):
    """mask 컬럼(실행시각 등) 차이는 무시 → OK."""
    a = _w(tmp_path / "a.csv", "ID,BAL,UPD_TS\n1,100,2024-01-01T00:00\n")
    b = _w(tmp_path / "b.csv", "ID,BAL,UPD_TS\n1,100,2024-06-09T12:34\n")
    r = compare_files(a, b, _opts(mode="record", key="ID", mask="UPD_TS", has_header="true"))
    assert r.status == ComparisonStatus.OK


def test_record_tolerance(tmp_path):
    """수치 허용오차 이내 차이는 OK, 초과는 NG."""
    a = _w(tmp_path / "a.csv", "ID,V\n1,1.000\n")
    b = _w(tmp_path / "b.csv", "ID,V\n1,1.0005\n")
    ok = compare_files(a, b, _opts(mode="record", key="ID", tolerance="0.001", has_header="true"))
    assert ok.status == ComparisonStatus.OK
    ng = compare_files(a, b, _opts(mode="record", key="ID", tolerance="0.0001", has_header="true"))
    assert ng.status == ComparisonStatus.NG


def test_record_normalize_date(tmp_path):
    """YYYYMMDD ↔ YYYY-MM-DD 동치."""
    a = _w(tmp_path / "a.csv", "ID,DT\n1,20240102\n")
    b = _w(tmp_path / "b.csv", "ID,DT\n1,2024-01-02\n")
    r = compare_files(a, b, _opts(mode="record", key="ID", normalize="DT:date", has_header="true"))
    assert r.status == ComparisonStatus.OK


def test_record_normalize_num_and_nullblank_and_zeropad_and_trim(tmp_path):
    a = _w(tmp_path / "a.csv", "ID,N,M,Z,T\n1,1.5,NULL,42, x \n")
    b = _w(tmp_path / "b.csv", "ID,N,M,Z,T\n1,1.50,,00042,x\n")
    norm = "N:num:2;M:nullblank;Z:zeropad:5;T:trim"
    r = compare_files(a, b, _opts(mode="record", key="ID", normalize=norm, has_header="true"))
    assert r.status == ComparisonStatus.OK


def test_record_fixed_length_layout(tmp_path):
    """고정길이 layout으로 필드 분할 후 비교(구분자 없음)."""
    # 0:3=ID, 3:8=NAME(5폭)
    a = _w(tmp_path / "a.dat", "001ALICE\n002BOB  \n")
    b = _w(tmp_path / "b.dat", "002BOB  \n001ALICE\n")
    r = compare_files(a, b, _opts(mode="record", key="0", layout="0:3;3:8"))
    assert r.status == ComparisonStatus.OK


# --- 경계: unknown mode / size guard --------------------------------------------


def test_unknown_mode_is_error(tmp_path):
    a = _w(tmp_path / "a.csv", "x\n")
    b = _w(tmp_path / "b.csv", "x\n")
    r = compare_files(a, b, _opts(mode="bogus"))
    assert r.status == ComparisonStatus.ERROR and "모드" in r.error_message


def test_record_size_guard_errors(tmp_path, monkeypatch):
    """인메모리 한계 초과 시 명시적 ERROR(외부정렬 스트리밍=E4 보류, OOM 백스톱)."""
    monkeypatch.setattr(comparator, "_RECORD_SIZE_GUARD", 4)
    a = _w(tmp_path / "a.csv", "ID,V\n1,aaaaaaaa\n")
    b = _w(tmp_path / "b.csv", "ID,V\n1,aaaaaaaa\n")
    r = compare_files(a, b, _opts(mode="record", key="ID", has_header="true"))
    assert r.status == ComparisonStatus.ERROR and "E4" in r.error_message


def test_missing_file_in_record_mode(tmp_path):
    """존재 검증은 모드 무관 — 한쪽 없으면 MISSING_*."""
    a = _w(tmp_path / "a.csv", "ID\n1\n")
    r = compare_files(a, tmp_path / "nope.csv", _opts(mode="record", key="ID", has_header="true"))
    assert r.status == ComparisonStatus.MISSING_TOBE
