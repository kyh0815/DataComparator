#!/usr/bin/env python3
"""realtest 데이터 생성기 — As-Is 입력/정답 + To-Be 소스를 Shift-JIS로 만든다.

더미 배치(batch/run_batch.py)가 실행 시 tobe_src/<출력명>을 tobe/output으로 복사해 To-Be를 낸다.
여기서 asis/input(입력), asis/output(정답), tobe_src(To-Be 원본)를 모두 만들어 둔다.
의도: 사전점검 통과 + 검증실행 시 OK 7 / NG 3 (현新비교 시험성적서 데모). 코어 코드는 안 건드림.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

_ENC = "shift_jis"
_HERE = Path(__file__).resolve().parent


def _csv(header: list[str], rows: list[list[str]]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue().encode(_ENC)


def _write(rel: str, data: bytes) -> None:
    p = _HERE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


# 각 체크리스트: 출력(정답 asis vs To-Be tobe). record=CSV, raw=원문 그대로(byte/text).
# 입력 파일은 존재만 하면 되므로 공통 더미로 생성(배치는 입력을 읽되 내용은 사용 안 함).
RECORD = "record"
RAW = "raw"

CHECKS = [
    # CK001 顧客残高マスタ — 플랫폼차이(셔플·zeropad·소수·날짜·NULL·시각) 정규화로 전부 흡수 → OK
    {"id": "CK001", "out": "ck001_zandaka.csv", "kind": RECORD,
     "header": ["KOKYAKU_ID", "SHITEN_CD", "KOKYAKU_NM", "ZANDAKA", "KISAN_YMD", "KOSHIN_NICHIJI", "BIKO"],
     "asis": [["0001", "0007", "山田太郎", "150000.00", "2026-06-01", "2026-06-01 01:00:05", ""],
              ["0002", "0007", "鈴木花子", "89000.00", "2026-06-01", "2026-06-01 01:00:05", ""],
              ["0003", "0012", "田中一郎", "250000.50", "2026-06-01", "2026-06-01 01:00:05", "VIP"],
              ["0004", "0007", "佐藤花", "0.00", "2026-06-01", "2026-06-01 01:00:05", ""]],
     "tobe": [["0003", "12", "田中一郎", "250000.5", "20260601", "2026-06-09 03:00:00", "VIP"],
              ["0001", "7", "山田太郎", "150000", "20260601", "2026-06-09 03:00:00", "NULL"],
              ["0004", "7", "佐藤花", "0", "20260601", "2026-06-09 03:00:00", "NULL"],
              ["0002", "7", "鈴木花子", "89000", "20260601", "2026-06-09 03:00:00", "NULL"]]},

    # CK002 取引明細集計 — 셔플 + 금액 소수표기차 정규화 → OK
    {"id": "CK002", "out": "ck002_shukei.csv", "kind": RECORD,
     "header": ["TX_ID", "KOKYAKU_ID", "KINGAKU"],
     "asis": [["T001", "0001", "5000"], ["T002", "0002", "12000"], ["T003", "0003", "300"]],
     "tobe": [["T002", "0002", "12000"], ["T001", "0001", "5000.0"], ["T003", "0003", "300"]]},

    # CK003 残高検証 — ★0002 ZANDAKA 값 자체가 다름(진짜 결함) → NG
    {"id": "CK003", "out": "ck003_kensho.csv", "kind": RECORD,
     "header": ["KOKYAKU_ID", "ZANDAKA"],
     "asis": [["0001", "1000.00"], ["0002", "2000.00"], ["0003", "3000.00"]],
     "tobe": [["0001", "1000"], ["0002", "2500"], ["0003", "3000"]]},

    # CK004 帳票 byte完全一致 → OK
    {"id": "CK004", "out": "ck004_chohyo.txt", "kind": RAW,
     "asis": "帳票ヘッダ\n合計: 1,234,567 円\n明細件数: 42\n",
     "tobe": "帳票ヘッダ\n合計: 1,234,567 円\n明細件数: 42\n"},

    # CK005 請求書 byte → ★承認 済→未(결함) → NG
    {"id": "CK005", "out": "ck005_seikyu.txt", "kind": RAW,
     "asis": "請求書\n金額: 50000\n承認: 済\n",
     "tobe": "請求書\n金額: 50000\n承認: 未\n"},

    # CK006 口座一覧 text — 줄끝(CRLF)·우측공백 차이 정규화 → OK
    {"id": "CK006", "out": "ck006_kouza.txt", "kind": RAW,
     "asis": "口座番号,氏名\n12345,山田\n67890,鈴木\n",
     "tobe": "口座番号,氏名  \r\n12345,山田\r\n67890,鈴木   \r\n"},

    # CK007 金利マスタ — 소수자리(num:4) 정규화 → OK
    {"id": "CK007", "out": "ck007_kinri.csv", "kind": RECORD,
     "header": ["CODE", "RATE"],
     "asis": [["A", "0.0150"], ["B", "0.0200"], ["C", "0.0075"]],
     "tobe": [["A", "0.015"], ["B", "0.02"], ["C", "0.0075"]]},

    # CK008 手数料 — 제로패딩(zeropad:5) 정규화 → OK
    {"id": "CK008", "out": "ck008_tesuryo.csv", "kind": RECORD,
     "header": ["KOKYAKU_ID", "TESU_CD", "KINGAKU"],
     "asis": [["0001", "00100", "500"], ["0002", "00200", "800"]],
     "tobe": [["0001", "100", "500"], ["0002", "200", "800"]]},

    # CK009 顧客属性 — BIKO 공백/NULL은 정규화, ★0002 KUBUN B→C(결함) → NG
    {"id": "CK009", "out": "ck009_zokusei.csv", "kind": RECORD,
     "header": ["KOKYAKU_ID", "KUBUN", "BIKO"],
     "asis": [["0001", "A", ""], ["0002", "B", "メモ"], ["0003", "A", ""]],
     "tobe": [["0001", "A", "NULL"], ["0002", "C", "メモ"], ["0003", "A", "NULL"]]},

    # CK010 支店マスタ — 셔플만(key 정렬로 흡수) → OK
    {"id": "CK010", "out": "ck010_shiten.csv", "kind": RECORD,
     "header": ["SHITEN_CD", "SHITEN_NM"],
     "asis": [["0007", "東京支店"], ["0012", "大阪支店"], ["0003", "名古屋支店"]],
     "tobe": [["0012", "大阪支店"], ["0007", "東京支店"], ["0003", "名古屋支店"]]},
]


def main() -> int:
    for c in CHECKS:
        cid = c["id"].lower()
        # 입력(존재용 더미 — 배치는 읽되 내용 미사용)
        _write(f"asis/input/{cid}_in.csv",
               _csv(["IN_KEY", "IN_DATA"], [["1", f"{c['id']}-入力1"], ["2", f"{c['id']}-入力2"]]))
        # 정답(As-Is 출력) + To-Be 소스
        if c["kind"] == RECORD:
            _write(f"asis/output/{c['out']}", _csv(c["header"], c["asis"]))
            _write(f"tobe_src/{c['out']}", _csv(c["header"], c["tobe"]))
        else:  # raw(byte/text) — 원문 그대로
            _write(f"asis/output/{c['out']}", c["asis"].encode(_ENC))
            _write(f"tobe_src/{c['out']}", c["tobe"].encode(_ENC))
    print(f"生成: {len(CHECKS)} チェックリスト分の asis/input・asis/output・tobe_src (Shift-JIS)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
