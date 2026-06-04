"""As-Is 입력 CSV를 PostgreSQL 테이블에 적재.

print/CLI 출력 금지(CLAUDE.md 3-1). 실패 시 예외를 발생시키고 상위에서 처리한다.

설계 결정은 DECISIONS.md D-020 참조:
- 시그니처는 `table_name`을 받는 **범용 적재기**. 셸→테이블 매핑은 T2-3/T3-1에서 정의.
- CSV는 `encoding`(기본 shift_jis)으로 디코드해 UTF-8 DB에 적재 (파일↔DB 경계 변환, D-018).
- 헤더 행으로 컬럼을 매핑(순서 무관). 빈 문자열은 NULL로 적재.
- 적재 전 TRUNCATE → INSERT(executemany). loader는 commit하지 않는다(호출자가 트랜잭션 관리).
- table_name은 psycopg2.sql.Identifier로 안전하게 식별자 처리.
"""

from __future__ import annotations

import csv
import io
import shutil
from pathlib import Path

from psycopg2 import sql


class LoaderError(Exception):
    """CSV 적재 실패(파일 없음·헤더 불일치 등). DB 예외는 그대로 전파한다."""


def copy_input_file(csv_path: Path, dest_dir: Path, dest_name: str | None = None) -> Path:
    """파일 입력 흐름: As-Is 입력 CSV를 야간 배치 입력 디렉토리에 바이트 복사한다 (D-022).

    인코딩 변환은 하지 않는다(원본 Shift-JIS 바이트 그대로 — stub이 읽을 때 디코드한다).
    dest_dir는 없으면 생성한다. dest_name이 주어지면 그 이름으로 격납한다(#7-3, 없으면 원본명).
    복사된 파일 경로를 반환한다. 원본이 없으면 LoaderError.
    """
    csv_path = Path(csv_path)
    if not csv_path.is_file():
        raise LoaderError(f"복사할 입력 파일이 없습니다: {csv_path}")
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / (dest_name or csv_path.name)
    shutil.copyfile(csv_path, dest)  # 바이트 그대로 복사 (메타데이터 불필요)
    return dest


def load_input_csv(
    csv_path: Path,
    conn,
    table_name: str,
    encoding: str = "shift_jis",
) -> int:
    """CSV 파일을 지정 테이블에 적재하고 적재 행 수를 반환한다.

    적재 전 테이블을 TRUNCATE하여 재실행 시 깨끗하게 만든다. commit은 하지 않으므로
    호출자가 트랜잭션 경계를 관리한다(셸 단위 실패 격리, SPEC 3-1).
    """
    csv_path = Path(csv_path)
    if not csv_path.is_file():
        raise LoaderError(f"적재할 CSV 파일이 없습니다: {csv_path}")

    # 파일↔DB 경계에서만 Shift-JIS 디코드 (D-018). 이후는 UTF-8 DB에 그대로 들어간다.
    text = csv_path.read_bytes().decode(encoding, errors="strict")
    columns, rows = _parse_rows(text)

    with conn.cursor() as cur:
        # 대상 테이블의 실제 컬럼과 CSV 헤더가 일치하는지 검증한다.
        db_columns = _table_columns(cur, table_name)
        unknown = [c for c in columns if c not in db_columns]
        if unknown:
            raise LoaderError(
                f"CSV 헤더가 테이블 '{table_name}' 컬럼과 불일치: 알 수 없는 컬럼 {unknown}"
            )

        cur.execute(sql.SQL("TRUNCATE TABLE {}").format(sql.Identifier(table_name)))

        if not rows:
            return 0

        insert = sql.SQL("INSERT INTO {table} ({cols}) VALUES ({ph})").format(
            table=sql.Identifier(table_name),
            cols=sql.SQL(", ").join(sql.Identifier(c) for c in columns),
            ph=sql.SQL(", ").join(sql.Placeholder() for _ in columns),
        )
        cur.executemany(insert, rows)

    return len(rows)


def _parse_rows(text: str) -> tuple[list[str], list[tuple]]:
    """CSV 텍스트를 (헤더 컬럼 목록, 행 튜플 목록)으로 파싱한다 (순수 함수, DB 무관).

    빈 문자열 셀은 None(NULL)으로 변환한다. 헤더가 없으면 LoaderError.
    """
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        raise LoaderError("빈 CSV입니다(헤더 행이 없음).")

    columns = [c.strip() for c in header]
    rows: list[tuple] = []
    for line_no, raw in enumerate(reader, start=2):
        if not raw:  # 완전한 빈 줄은 건너뛴다.
            continue
        if len(raw) != len(columns):
            raise LoaderError(
                f"{line_no}행의 컬럼 수({len(raw)})가 헤더({len(columns)})와 다릅니다."
            )
        rows.append(tuple(value if value != "" else None for value in raw))
    return columns, rows


def _table_columns(cur, table_name: str) -> set[str]:
    """대상 테이블의 컬럼명 집합을 information_schema에서 조회한다."""
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
        (table_name,),
    )
    cols = {row[0] for row in cur.fetchall()}
    if not cols:
        raise LoaderError(f"테이블을 찾을 수 없습니다: {table_name}")
    return cols
