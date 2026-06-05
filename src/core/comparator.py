"""두 출력 파일의 동등성 비교 (이 도구의 심장).

판정은 반드시 결정론적 코드로만 한다 (LLM 금지, CLAUDE.md 6장). 모드(HANDOFF_V3 C1):
- byte  : 바이트 완전 일치. 모든 바이트가 의미있는 고정포맷용(미지정 시 기본). 대용량 대비 **청크 스트리밍**.
- text  : 행 단위. 줄끝(CRLF/LF) 정규화 + 우측 공백 trim 후 위치 비교.
- record: 행→필드 분할(layout/delimiter) → (key)정렬·정합 → (mask)제외 → (normalize)정규화
          → (tolerance)수치근사 → 비교. diff 최대 50건.

record는 **source→aligner 이터레이터 파이프라인**이라, 훗날 aligner만 외부정렬로 교체하면 된다.
단 V3 도메인 전제상 件당 수만 행 → **인메모리로 충분**(외부정렬 스트리밍=E4 보류). 현재 aligner는
인메모리(정렬 후 머지조인) + 하드 사이즈가드(수백 MB 초과 시 명시적 ERROR — OOM 백스톱).
"""

from __future__ import annotations

from itertools import zip_longest
from pathlib import Path
from typing import BinaryIO, Iterator

from .models import ComparisonResult, ComparisonStatus, CompareOptions, DiffLine

_CHUNK = 1 << 20  # 1 MiB: byte 스트리밍/라인 분할 청크
_MAX_DIFF = 50  # diff 최대 표시 건수(대용량에서 무한 덤프 방지)
_RECORD_SIZE_GUARD = 256 << 20  # 256 MiB: record 인메모리 OOM 백스톱(件당 수만 행이면 미발동). E4=외부정렬 보류


def compare_files(
    asis_path: Path,
    tobe_path: Path,
    opts: CompareOptions | None = None,
    *,
    encoding: str | None = None,
) -> ComparisonResult:
    """As-Is 출력과 To-Be 출력을 opts.mode대로 비교해 ComparisonResult를 반환한다.

    opts 미지정 시 byte 모드로 동작(현 동작 보존, Q1). 하위호환을 위해 encoding= 키워드도 받는다
    (opts 없을 때만 사용). 판정용 인코딩이 비면 shift_jis(D-003 기본).
    """
    if opts is None:
        opts = CompareOptions(mode="byte", encoding=encoding or "shift_jis")
    enc = opts.encoding or "shift_jis"

    asis_path = Path(asis_path)
    tobe_path = Path(tobe_path)
    shell_id = _derive_shell_id(asis_path, tobe_path)

    missing = _existence_result(asis_path, tobe_path, shell_id)
    if missing is not None:
        return missing

    mode = opts.mode or "byte"
    if mode == "byte":
        return _compare_byte(asis_path, tobe_path, enc, shell_id)
    if mode == "text":
        return _compare_text(asis_path, tobe_path, enc, shell_id)
    if mode == "record":
        return _compare_record(asis_path, tobe_path, opts, enc, shell_id)
    return ComparisonResult(
        shell_id=shell_id,
        status=ComparisonStatus.ERROR,
        error_message=f"알 수 없는 비교 모드: {mode!r} (byte|text|record)",
    )


def _existence_result(
    asis_path: Path, tobe_path: Path, shell_id: str
) -> ComparisonResult | None:
    """양쪽 파일 존재를 점검. 모두 없으면 ERROR, 한쪽만 없으면 MISSING_*. 둘 다 있으면 None."""
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
    return None


def _derive_shell_id(asis_path: Path, tobe_path: Path) -> str:
    """파일명 stem을 셸 ID로 사용한다 (예: 007.csv -> "007"). 존재하는 쪽 우선."""
    if asis_path.is_file():
        return asis_path.stem
    if tobe_path.is_file():
        return tobe_path.stem
    return asis_path.stem


# --- byte 모드 (청크 스트리밍) ---------------------------------------------------


def _compare_byte(asis_path: Path, tobe_path: Path, encoding: str, shell_id: str) -> ComparisonResult:
    """바이트 완전 일치 판정(청크 스트리밍, 통째 메모리 적재 안 함). 불일치 시 줄 단위 diff."""
    if _files_equal(asis_path, tobe_path):
        return ComparisonResult(shell_id=shell_id, status=ComparisonStatus.OK)
    diffs = _line_diffs(asis_path, tobe_path, encoding)
    return ComparisonResult(shell_id=shell_id, status=ComparisonStatus.NG, diff_lines=diffs)


def _files_equal(asis_path: Path, tobe_path: Path) -> bool:
    """두 파일을 청크 단위로 비교(첫 불일치에서 조기 종료). GB급 OOM 방지."""
    with asis_path.open("rb") as fa, tobe_path.open("rb") as fb:
        while True:
            ca = fa.read(_CHUNK)
            cb = fb.read(_CHUNK)
            if ca != cb:
                return False
            if not ca:  # 둘 다 EOF(위에서 같음 확인됨)
                return True


def _line_diffs(asis_path: Path, tobe_path: Path, encoding: str) -> list[DiffLine]:
    """\\n 기준 줄을 위치별로 대조(스트리밍). 다른 줄마다 DiffLine, 최대 _MAX_DIFF건.

    바이트 단위 비교라 공백·개행(\\r) 차이까지 결정론적으로 잡는다(표시만 디코딩).
    """
    diffs: list[DiffLine] = []
    with asis_path.open("rb") as fa, tobe_path.open("rb") as fb:
        for index, (a_line, b_line) in enumerate(
            zip_longest(_iter_lines(fa), _iter_lines(fb), fillvalue=None)
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
            if len(diffs) >= _MAX_DIFF:
                break
    return diffs


def _iter_lines(stream: BinaryIO) -> Iterator[bytes]:
    """파일을 b"\\n" 기준으로 스트리밍 분할. bytes.split(b"\\n")와 동일한 시퀀스를 낸다.

    즉 마지막 개행 뒤의 (빈) 세그먼트도 1건 낸다 — 기존 위치기반 비교 의미를 정확히 보존한다.
    """
    buf = b""
    while True:
        chunk = stream.read(_CHUNK)
        if not chunk:
            break
        buf += chunk
        parts = buf.split(b"\n")
        buf = parts.pop()  # 마지막 조각은 아직 미완(또는 트레일링) — 다음 청크와 이어붙임
        for p in parts:
            yield p
    yield buf  # split의 트레일링 원소에 해당(빈 파일이면 b"" 1건)


def _decode_for_display(line: bytes | None, encoding: str) -> str:
    """표시용 디코딩. 없는 줄(None)은 빈 문자열, 끝의 \\r은 표시상 제거."""
    if line is None:
        return ""
    return line.rstrip(b"\r").decode(encoding, errors="replace")


# --- text 모드 (행 정규화 후 위치 비교) ------------------------------------------


def _compare_text(asis_path: Path, tobe_path: Path, encoding: str, shell_id: str) -> ComparisonResult:
    """행 단위 비교: 줄끝(CRLF/LF) 정규화 + 우측 공백 trim 후 위치별 대조(V3 C1 text)."""
    diffs: list[DiffLine] = []
    with asis_path.open("rb") as fa, tobe_path.open("rb") as fb:
        for index, (a_raw, b_raw) in enumerate(
            zip_longest(_iter_lines(fa), _iter_lines(fb), fillvalue=None)
        ):
            a_norm = _norm_text_line(a_raw, encoding)
            b_norm = _norm_text_line(b_raw, encoding)
            if a_norm == b_norm:
                continue
            diffs.append(DiffLine(line_number=index + 1, asis_content=a_norm or "", tobe_content=b_norm or ""))
            if len(diffs) >= _MAX_DIFF:
                break
    status = ComparisonStatus.OK if not diffs else ComparisonStatus.NG
    return ComparisonResult(shell_id=shell_id, status=status, diff_lines=diffs)


def _norm_text_line(line: bytes | None, encoding: str) -> str | None:
    """text 모드 행 정규화: 디코드 후 우측 공백·\\r 제거. 없는 줄(None)은 None 유지(존재 차이 보존)."""
    if line is None:
        return None
    return line.decode(encoding, errors="replace").rstrip()


# --- record 모드 (필드 분할 → 정렬·정합 → 정규화 → 비교) -------------------------


def _compare_record(
    asis_path: Path, tobe_path: Path, opts: CompareOptions, encoding: str, shell_id: str
) -> ComparisonResult:
    """레코드 비교. P0: 인메모리 정렬+머지조인(사이즈가드). 파이프라인은 source→aligner 이터레이터."""
    guard = _size_guard(asis_path, tobe_path, shell_id)
    if guard is not None:
        return guard

    asis_header, asis_rows = _record_source(asis_path, opts, encoding)
    tobe_header, tobe_rows = _record_source(tobe_path, opts, encoding)

    # mask/normalize는 각 파일 자기 헤더로 colid 해석(To-Be 컬럼 순서변경 내성, Q3).
    asis_recs = [_to_record(cells, asis_header, opts) for cells in asis_rows]
    tobe_recs = [_to_record(cells, tobe_header, opts) for cells in tobe_rows]

    diffs = _align_and_diff(asis_recs, tobe_recs, opts)
    status = ComparisonStatus.OK if not diffs else ComparisonStatus.NG
    return ComparisonResult(shell_id=shell_id, status=status, diff_lines=diffs)


def _size_guard(asis_path: Path, tobe_path: Path, shell_id: str) -> ComparisonResult | None:
    """record 인메모리 한계 초과 시 ERROR(외부정렬 스트리밍=E4 보류, OOM 백스톱). 이하면 None."""
    biggest = max(asis_path.stat().st_size, tobe_path.stat().st_size)
    if biggest > _RECORD_SIZE_GUARD:
        return ComparisonResult(
            shell_id=shell_id,
            status=ComparisonStatus.ERROR,
            error_message=(
                f"record 모드 인메모리 한계 초과({biggest} bytes > {_RECORD_SIZE_GUARD}). "
                "대용량 스트리밍(외부정렬)은 E4(보류) — 그때까지 byte/text 모드 또는 분할 검증을 쓰세요."
            ),
        )
    return None


def _record_source(
    path: Path, opts: CompareOptions, encoding: str
) -> tuple[list[str], Iterator[list[str]]]:
    """파일을 (헤더, 레코드 이터레이터)로. 헤더는 has_header일 때만 채워짐(아니면 빈 리스트).

    source 단계 — 행을 필드 리스트로 분할만 한다(정규화·정렬은 하류). 빈 줄(트레일링 개행 등)은 제외.
    """
    lines = _decoded_nonempty_lines(path, encoding)
    header: list[str] = []
    if opts.has_header:
        try:
            first = next(lines)
            header = _split_cells(first, opts)
        except StopIteration:
            header = []
    rows = (_split_cells(line, opts) for line in lines)
    return header, rows


def _decoded_nonempty_lines(path: Path, encoding: str) -> Iterator[str]:
    """파일을 스트리밍 디코드해 빈 줄(트레일링 개행 등)을 뺀 행만 낸다."""
    with path.open("rb") as f:
        for raw in _iter_lines(f):
            line = raw.rstrip(b"\r")
            if line == b"":
                continue
            yield line.decode(encoding, errors="replace")


def _split_cells(line: str, opts: CompareOptions) -> list[str]:
    """한 행을 필드 리스트로. layout(고정길이)이 있으면 슬라이스, 없으면 delimiter 분할."""
    if opts.layout:
        return [line[start:end] for start, end in opts.layout]
    return line.split(opts.delimiter)


def _to_record(cells: list[str], header: list[str], opts: CompareOptions) -> dict[str, str]:
    """필드 리스트를 colid→값 dict로. colid = (헤더면 컬럼명, 아니면 위치 인덱스 문자열)."""
    rec: dict[str, str] = {}
    for i, val in enumerate(cells):
        colid = header[i] if (opts.has_header and i < len(header)) else str(i)
        rec[colid] = val
    return rec


def _align_and_diff(
    asis_recs: list[dict[str, str]], tobe_recs: list[dict[str, str]], opts: CompareOptions
) -> list[DiffLine]:
    """aligner: key가 있으면 정렬 후 머지조인, 없으면 위치 정합. 다른 레코드마다 DiffLine(최대 50).

    현재 인메모리 정렬. 훗날 스트리밍(E4)은 이 함수만 외부정렬(정렬된 런 머지)로 교체(상류 동일).
    """
    if opts.key:
        asis_sorted = sorted(asis_recs, key=lambda r: _rec_key(r, opts))
        tobe_sorted = sorted(tobe_recs, key=lambda r: _rec_key(r, opts))
        return _merge_join_diff(asis_sorted, tobe_sorted, opts)
    return _positional_diff(asis_recs, tobe_recs, opts)


def _rec_key(rec: dict[str, str], opts: CompareOptions) -> str:
    """레코드의 정렬·정합 키 값. 레코드는 자기 colid를 이미 들고 있어 헤더 불요.

    이름 지정이면 colid=이름, 인덱스 지정이면 colid=str(idx) — _to_record가 같은 규칙으로 채운다.
    """
    if not opts.key:
        return ""
    colid = opts.key if (opts.has_header and not opts.key.isdigit()) else str(int(opts.key))
    return rec.get(colid, "")


def _merge_join_diff(
    asis_sorted: list[dict[str, str]], tobe_sorted: list[dict[str, str]], opts: CompareOptions
) -> list[DiffLine]:
    """정렬된 두 레코드열을 키로 머지조인. 키 누락·잉여·값차이를 모두 diff로 낸다."""
    diffs: list[DiffLine] = []
    i = j = 0
    n = 0
    while i < len(asis_sorted) and j < len(tobe_sorted):
        ka = _rec_key(asis_sorted[i], opts)
        kb = _rec_key(tobe_sorted[j], opts)
        if ka == kb:
            if not _records_equal(asis_sorted[i], tobe_sorted[j], opts):
                n += 1
                diffs.append(_rec_diff(n, asis_sorted[i], tobe_sorted[j]))
            i += 1
            j += 1
        elif ka < kb:  # As-Is에만 있는 키
            n += 1
            diffs.append(_rec_diff(n, asis_sorted[i], None))
            i += 1
        else:  # To-Be에만 있는 키
            n += 1
            diffs.append(_rec_diff(n, None, tobe_sorted[j]))
            j += 1
        if len(diffs) >= _MAX_DIFF:
            return diffs
    for k in range(i, len(asis_sorted)):
        n += 1
        diffs.append(_rec_diff(n, asis_sorted[k], None))
        if len(diffs) >= _MAX_DIFF:
            return diffs
    for k in range(j, len(tobe_sorted)):
        n += 1
        diffs.append(_rec_diff(n, None, tobe_sorted[k]))
        if len(diffs) >= _MAX_DIFF:
            return diffs
    return diffs


def _positional_diff(
    asis_recs: list[dict[str, str]], tobe_recs: list[dict[str, str]], opts: CompareOptions
) -> list[DiffLine]:
    """key 미지정 시 위치별 정합(행 순서 비결정성에 취약 — 검증 경고 대상)."""
    diffs: list[DiffLine] = []
    n = 0
    for a, b in zip_longest(asis_recs, tobe_recs, fillvalue=None):
        if a is not None and b is not None and _records_equal(a, b, opts):
            continue
        if a is None and b is None:
            continue
        n += 1
        diffs.append(_rec_diff(n, a, b))
        if len(diffs) >= _MAX_DIFF:
            break
    return diffs


def _records_equal(a: dict[str, str], b: dict[str, str], opts: CompareOptions) -> bool:
    """두 레코드의 동등성: mask 제외 colid 합집합을 normalize·tolerance 적용해 셀별 비교."""
    norm_map = _normalize_map(opts)
    mask = _mask_set(opts)
    colids = (set(a) | set(b)) - mask
    for colid in colids:
        av = _apply_normalize(a.get(colid, ""), norm_map.get(colid, []))
        bv = _apply_normalize(b.get(colid, ""), norm_map.get(colid, []))
        if not _cell_equal(av, bv, opts.tolerance):
            return False
    return True


def _mask_set(opts: CompareOptions) -> set[str]:
    """mask 토큰을 colid 집합으로(이름/인덱스 둘 다 colid 규칙으로 정규화)."""
    out: set[str] = set()
    for tok in opts.mask:
        if opts.has_header and not tok.isdigit():
            out.add(tok)
        else:
            out.add(str(int(tok)))
    return out


def _normalize_map(opts: CompareOptions) -> dict[str, list[tuple[str, str | None]]]:
    """normalize 규칙을 colid→[(rule,arg)] 로. 한 colid에 규칙 여럿이면 순차 적용."""
    out: dict[str, list[tuple[str, str | None]]] = {}
    for col, rule, arg in opts.normalize:
        colid = col if (opts.has_header and not col.isdigit()) else str(int(col))
        out.setdefault(colid, []).append((rule, arg))
    return out


def _apply_normalize(value: str, rules: list[tuple[str, str | None]]) -> str:
    """셀 값에 정규화 규칙을 순차 적용한다(date/num/nullblank/zeropad/trim)."""
    for rule, arg in rules:
        value = _normalize_value(value, rule, arg)
    return value


def _normalize_value(value: str, rule: str, arg: str | None) -> str:
    """단일 정규화 규칙 적용. 파싱 실패(num 등)는 원값 유지(결정론·안전)."""
    if rule == "trim":
        return value.strip()
    if rule == "nullblank":
        return "" if value.strip() == "" or value.strip().upper() == "NULL" else value
    if rule == "zeropad":
        return value.strip().zfill(int(arg)) if arg else value.strip()
    if rule == "date":
        # YYYYMMDD ↔ YYYY-MM-DD 동치: 구분자 제거(숫자만 남김).
        return "".join(ch for ch in value if ch.isdigit())
    if rule == "num":
        try:
            f = float(value.strip())
        except ValueError:
            return value
        digits = int(arg) if arg else 0
        return f"{f:.{digits}f}" if f != 0 else f"{0.0:.{digits}f}"  # -0 → 0 정규화
    return value


def _cell_equal(a: str, b: str, tolerance: float) -> bool:
    """정규화된 두 셀 비교. 같으면 True, 아니면 둘 다 수치이고 |차|<=tolerance면 True."""
    if a == b:
        return True
    if tolerance > 0:
        try:
            return abs(float(a) - float(b)) <= tolerance
        except ValueError:
            return False
    return False


def _rec_diff(n: int, a: dict[str, str] | None, b: dict[str, str] | None) -> DiffLine:
    """레코드 차이 1건을 DiffLine으로(표시는 원 필드 join). 없는 쪽은 빈 문자열."""
    return DiffLine(line_number=n, asis_content=_render(a), tobe_content=_render(b))


def _render(rec: dict[str, str] | None) -> str:
    """레코드를 사람이 보는 한 줄로(colid 순서대로 값 join)."""
    if rec is None:
        return ""
    return ",".join(rec[k] for k in rec)
