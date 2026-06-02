"""시연용 stub 배치 공통 로직 (run_batch_db.py / run_batch_file.py 가 공유).

# === 인수인계 시 교체 포인트 ===
# 이 stub들은 시연용이다. 실 운영에서는 고객의 진짜 배치(Net COBOL)로 교체한다.
# 입출력 계약(--shell-id, --output-path, --output-type)은 유지할 것.
# 본 stub은 도구가 입력 2종(DB/파일) × 출력 2종(DB/파일)을 모두 지원함을 시연하기 위한 placeholder.

동작: input(거래 데이터)을 읽어 customer_master(마스터)를 조인한 取引明細을 만든다.
출력은 --output-type 에 따라
  - file     : tobe_output CSV(Shift-JIS) 직접 생성
  - database : 결과 테이블(tobe_result)에 INSERT (오케스트레이터의 exporter가 CSV로 다운로드)
특정 shell_id에서는 의도적으로 다른 결과를 만들어 NG/ERROR를 시연한다(SPEC 6-5).

stub은 Core가 아닌 외부 프로세스이므로 print(진단은 stderr)가 허용된다.
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql

# 출력 CSV 컬럼 (헤더 ASCII, 값은 일본어 가능 — SPEC 6-3). tobe_result 컬럼명과 동일.
OUTPUT_COLUMNS = [
    "tx_id",
    "customer_id",
    "customer_name",
    "tx_date",
    "tx_type",
    "amount",
    "balance_after",
    "memo",
]

# ERROR 시연 셸 (의도적 배치 실패 → 종료코드 1).
_FAILURE_SHELLS = {"010"}

# 전각 공백 (U+3000) — 008 NG(가짜처럼 보이는 공백 차이)용.
_FULLWIDTH_SPACE = "　"


# ---------------------------------------------------------------------------
# 인자 파싱 / DB 접속
# ---------------------------------------------------------------------------
def build_common_parser(description: str) -> argparse.ArgumentParser:
    """두 stub이 공유하는 공통 인자를 가진 파서를 만든다."""
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--shell-id", required=True, help="셸 ID (예: 001)")
    # --output-path는 출력=file일 때만 필요(=database면 테이블에 쓰고 Runner가 export). dead-arg 방지.
    p.add_argument("--output-path", help="To-Be 출력 CSV 경로(출력=file일 때 직접 기록)")
    p.add_argument("--output-type", choices=("file", "database"), default="file")
    p.add_argument("--output-table", default="tobe_result", help="출력=database일 때 결과 테이블")
    p.add_argument("--encoding", default="shift_jis")
    p.add_argument("--db-host", default=os.environ.get("PGHOST", "localhost"))
    p.add_argument("--db-port", default=os.environ.get("PGPORT", "5432"))
    p.add_argument("--db-name", default=os.environ.get("PGDATABASE", "compare_proto"))
    p.add_argument("--db-user", default=os.environ.get("PGUSER", "postgres"))
    p.add_argument("--clean", action="store_true", help="NG 주입을 끈 정상 출력(골든 생성용)")
    return p


def connect(args) -> "psycopg2.extensions.connection":
    """args + POSTGRES_PASSWORD 환경변수로 DB에 접속한다."""
    return psycopg2.connect(
        host=args.db_host,
        port=int(args.db_port),
        dbname=args.db_name,
        user=args.db_user,
        password=os.environ.get("POSTGRES_PASSWORD"),
    )


# ---------------------------------------------------------------------------
# 입력 → 取引明細 행 만들기 (모든 셀은 문자열, None/빈값은 "")
# ---------------------------------------------------------------------------
def rows_from_db(conn) -> list[list[str]]:
    """transaction_log(적재된 입력) + customer_master 조인 → 取引明細 행 (tx_id 정렬)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT t.tx_id, t.customer_id, COALESCE(c.name, ''), t.tx_date, t.tx_type, "
            "       t.amount, t.balance_after, COALESCE(t.memo, '') "
            "FROM transaction_log t "
            "LEFT JOIN customer_master c ON t.customer_id = c.customer_id "
            "ORDER BY t.tx_id"
        )
        return [[_s(v) for v in row] for row in cur.fetchall()]


def rows_from_file(csv_path: Path, encoding: str, conn) -> list[list[str]]:
    """복사된 raw 거래 파일을 읽고 customer_master(DB) 조인 → 取引明細 행 (tx_id 정렬).

    raw 파일은 transaction_log 스키마(헤더 포함, Shift-JIS)라고 가정한다.
    """
    names = _fetch_customer_names(conn)
    text = Path(csv_path).read_bytes().decode(encoding, errors="strict")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[list[str]] = []
    for rec in reader:
        cid = (rec.get("customer_id") or "").strip()
        rows.append(
            [
                _s(rec.get("tx_id")),
                cid,
                names.get(cid, ""),
                _s(rec.get("tx_date")),
                _s(rec.get("tx_type")),
                _s(rec.get("amount")),
                _s(rec.get("balance_after")),
                _s(rec.get("memo")),
            ]
        )
    rows.sort(key=lambda r: r[0])  # tx_id 정렬 (결정론)
    return rows


def _fetch_customer_names(conn) -> dict[str, str]:
    """customer_master에서 customer_id → name 매핑을 읽는다."""
    with conn.cursor() as cur:
        cur.execute("SELECT customer_id, name FROM customer_master")
        return {cid: name for cid, name in cur.fetchall()}


def _s(value) -> str:
    """셀을 출력용 문자열로. None은 빈칸."""
    return "" if value is None else str(value)


# ---------------------------------------------------------------------------
# 의도된 NG 주입 (순수 함수 — DB 없이 단위 테스트 가능, SPEC 6-5)
# ---------------------------------------------------------------------------
def apply_ng_pattern(shell_id: str, rows: list[list[str]]) -> list[list[str]]:
    """shell_id에 따라 위치 기반·결정론적으로 행을 변형한다(rows를 제자리 수정 후 반환).

    007 한 줄 값 차이 / 008 전각 공백 / 009 여러 줄 차이. (010 실행 실패는 main에서 처리.)
    """
    if shell_id == "007" and len(rows) >= 1:
        rows[0][6] = _bump_number(rows[0][6])  # balance_after 1 증가 → 명백한 데이터 차이
    elif shell_id == "008" and len(rows) >= 1:
        rows[0][2] = _insert_fullwidth_space(rows[0][2])  # customer_name에 전각 공백
    elif shell_id == "009" and len(rows) >= 3:
        rows[0][6] = _bump_number(rows[0][6])  # balance_after
        rows[1][4] = rows[1][4] + "X"  # tx_type 변형
        rows[2][7] = (rows[2][7] or "") + "差分"  # memo 변형
    return rows


def is_failure_shell(shell_id: str) -> bool:
    """의도된 ERROR 시연 셸인지."""
    return shell_id in _FAILURE_SHELLS


def _bump_number(text: str) -> str:
    """숫자 문자열을 1 증가. 숫자가 아니면 끝에 표식을 붙여 어쨌든 다르게 만든다."""
    return str(int(text) + 1) if text.strip().lstrip("-").isdigit() else text + "9"


def _insert_fullwidth_space(name: str) -> str:
    """성명 가운데에 전각 공백을 삽입 (예: 田中太郎 → 田中　太郎)."""
    if not name:
        return _FULLWIDTH_SPACE
    mid = max(1, len(name) // 2)
    return name[:mid] + _FULLWIDTH_SPACE + name[mid:]


# ---------------------------------------------------------------------------
# 출력 (파일 직접 생성 / 결과 테이블 INSERT)
# ---------------------------------------------------------------------------
def write_csv_file(rows: list[list[str]], output_path: Path, encoding: str) -> None:
    """取引明細을 CSV(헤더 + 행, \\n, 지정 인코딩)로 직접 기록한다 (출력=file)."""
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(OUTPUT_COLUMNS)
    writer.writerows(rows)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(buf.getvalue().encode(encoding))


def write_to_result_table(conn, table_name: str, rows: list[list[str]]) -> None:
    """결과 테이블을 TRUNCATE 후 取引明細을 INSERT하고 commit한다 (출력=database).

    stub은 배치 본체이므로 자신의 출력 트랜잭션을 직접 커밋한다(exporter가 별도로 읽음).
    """
    with conn.cursor() as cur:
        cur.execute(sql.SQL("TRUNCATE TABLE {}").format(sql.Identifier(table_name)))
        if rows:
            insert = sql.SQL("INSERT INTO {table} ({cols}) VALUES ({ph})").format(
                table=sql.Identifier(table_name),
                cols=sql.SQL(", ").join(sql.Identifier(c) for c in OUTPUT_COLUMNS),
                ph=sql.SQL(", ").join(sql.Placeholder() for _ in OUTPUT_COLUMNS),
            )
            cur.executemany(insert, rows)
    conn.commit()


# ---------------------------------------------------------------------------
# 실행 오케스트레이션
# ---------------------------------------------------------------------------
def run(args, read_rows) -> None:
    """공통 실행 흐름: 실패 시연 → 접속 → 행 생성 → NG 주입 → 출력.

    read_rows(args, conn) -> list[list[str]] 는 입력 흐름별로 주입된다.
    """
    shell_id = args.shell_id
    if is_failure_shell(shell_id) and not args.clean:
        print(f"[stub] shell {shell_id}: 意図的なバッチ失敗のデモ → 終了コード 1", file=sys.stderr)
        sys.exit(1)

    if args.output_type == "file" and not args.output_path:
        print("[stub] 출력=file이면 --output-path가 필요합니다.", file=sys.stderr)
        sys.exit(2)

    conn = connect(args)
    try:
        rows = read_rows(args, conn)
        if not args.clean:
            apply_ng_pattern(shell_id, rows)
        if args.output_type == "file":
            write_csv_file(rows, Path(args.output_path), args.encoding)
        else:
            write_to_result_table(conn, args.output_table, rows)
    finally:
        conn.close()
