"""DB 결과 테이블을 CSV로 다운로드(export)한다 — 출력 'DB 유형' 흐름 (D-022).

Boss 처리단계 "SHELL프로그램이 출력한 데이터(DB,파일)를 TOBE 디렉토리에 다운로드"를 충족한다.
TOBE 배치가 결과 테이블(tobe_result)에 쓴 데이터를 비교용 CSV로 내린 뒤 comparator가 바이트 비교한다.

판정 신뢰를 위해 export는 **결정론적**이다:
- 컬럼 순서: 인자 columns(없으면 테이블 정의 순서)
- 행 순서: 전체 컬럼 기준 ORDER BY (총 순서 → 재현성)
- NULL → 빈칸, 줄바꿈 \n, 지정 인코딩(기본 Shift-JIS)
이로써 export 결과를 그대로 통짜 바이트 비교할 수 있다(D-004 일관).

print/CLI 출력 금지(CLAUDE.md 3-1). 읽기 전용이므로 commit하지 않는다.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from psycopg2 import sql


class ExporterError(Exception):
    """결과 테이블 export 실패(테이블 없음 등). DB 예외는 그대로 전파한다."""


def export_table_to_csv(
    conn,
    table_name: str,
    output_path: Path,
    encoding: str = "shift_jis",
    columns: list[str] | None = None,
) -> Path:
    """결과 테이블을 CSV(헤더 = 컬럼명)로 export하고 그 경로를 반환한다.

    columns가 None이면 테이블 정의 순서의 모든 컬럼을 쓴다. DB→파일 경계에서만
    `encoding`(기본 shift_jis)으로 인코드한다(D-018). 테이블이 없으면 ExporterError.
    """
    output_path = Path(output_path)

    with conn.cursor() as cur:
        cols = columns if columns else _table_columns_ordered(cur, table_name)
        if not cols:
            raise ExporterError(f"export할 테이블/컬럼을 찾을 수 없습니다: {table_name}")

        select = sql.SQL("SELECT {fields} FROM {table} ORDER BY {order}").format(
            fields=sql.SQL(", ").join(sql.Identifier(c) for c in cols),
            table=sql.Identifier(table_name),
            order=sql.SQL(", ").join(sql.SQL(str(i)) for i in range(1, len(cols) + 1)),
        )
        cur.execute(select)
        rows = cur.fetchall()

    text_buf = io.StringIO(newline="")
    writer = csv.writer(text_buf, lineterminator="\n")  # comparator/stub과 동일하게 \n
    writer.writerow(cols)
    for row in rows:
        writer.writerow(["" if v is None else str(v) for v in row])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(text_buf.getvalue().encode(encoding))
    return output_path


def _table_columns_ordered(cur, table_name: str) -> list[str]:
    """테이블 컬럼명을 정의(ordinal) 순서로 반환한다."""
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = %s ORDER BY ordinal_position",
        (table_name,),
    )
    return [row[0] for row in cur.fetchall()]
