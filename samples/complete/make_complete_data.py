#!/usr/bin/env python3
"""complete 데모셋 데이터·mock 셸 생성기 (TASK A — 단일 정본 데모셋).

샘플셋 단일화의 정본 complete_sample.csv가 가리키는 실데이터를 결정론적으로 만든다:
  asis/input/   입력(존재용 더미 — 파일흐름 배치는 읽되 내용 미사용)
  asis/output/  정답(As-Is 출력) = expected
  tobe_src/     To-Be 원본(플랫폼차·결함 심음). mock 셸이 이걸 출력으로 복사.
  mock_linux/opt/migsys/<業務>/sh/<shell>.py  실행되는 mock 셸(파일흐름=복사 / MISSING=무출력 / DB=래퍼)
                                              ★.py = 크로스플랫폼(D-060) — runner가 인터프리터로 실행

파일흐름 22건(CK001~018 + VSAM 021~022 + N:M 023~024) + DB 2건(CK019~020, 래퍼 셸이 repo stub_batch/ 호출)을 시연한다.
의도된 결과: OK / NG 4건(003·005·009·022) / MISSING_TOBE 1건(013). 모드 byte/text/record·정규화·mask·
셔플+key·SAM(고정길이 byte)·VSAM(고정길이 키순 record+key: 021 셔플OK / 022 값차NG)·다중입력(002)·
N:M 다입력다출력(023=3in→2out · 024=2in→2out, 멀티복사 셸)·N:1 공유셸(015·016)을 한 셋으로 덮는다.

★SAMPLE — 실데이터 아님. normalize/mask 값은 형식 예시일 뿐 실제 마이그레이션 판단이 아니다.
이 값들을 검증된 기본값으로 신뢰하지 말 것(과한 mask/normalize = false-PASS 경로).
"""

from __future__ import annotations

import csv
import io
import os
import stat
from pathlib import Path

_ENC = "shift_jis"
_HERE = Path(__file__).resolve().parent

RECORD = "record"  # CSV(헤더 有) — record/byte 비교
RAW = "raw"        # 원문 그대로 — byte/text 비교
SAM = "sam"        # 고정길이(헤더 無) 순차 — byte 통짜(layout은 시연 표기, D-039/D-047)
VSAM = "vsam"      # 고정길이(헤더 無) KSDS 키순저장 가정 — record+layout+key 정렬·정합(D-047). 골든=키순, To-Be=물리 셔플
                   # ★ESDS(입력순)는 byte로 충분·RRDS는 번호순 — 3종 분기는 실데이터 후(record+key는 ESDS에도 틀리지 않음)
MISSING = "missing"  # tobe_src 없음 + 무출력 셸 → MISSING_TOBE


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


# 파일흐름 18건. group=업무(폴더·shell_group), shell=mock 셸 파일명(같은 값 공유=N:1).
CHECKS = [
    # ── 業務A (CK001~008) ──
    {"id": "CK001", "group": "業務A", "shell": "ck001.sh", "out": "ck001_zandaka.csv", "kind": RECORD,
     "header": ["KOKYAKU_ID", "SHITEN_CD", "KOKYAKU_NM", "ZANDAKA", "KISAN_YMD", "KOSHIN_NICHIJI", "BIKO"],
     "asis": [["0001", "0007", "山田太郎", "150000.00", "2026-06-01", "2026-06-01 01:00:05", ""],
              ["0002", "0007", "鈴木花子", "89000.00", "2026-06-01", "2026-06-01 01:00:05", ""],
              ["0003", "0012", "田中一郎", "250000.50", "2026-06-01", "2026-06-01 01:00:05", "VIP"],
              ["0004", "0007", "佐藤花", "0.00", "2026-06-01", "2026-06-01 01:00:05", ""]],
     "tobe": [["0003", "12", "田中一郎", "250000.5", "20260601", "2026-06-09 03:00:00", "VIP"],
              ["0001", "7", "山田太郎", "150000", "20260601", "2026-06-09 03:00:00", "NULL"],
              ["0004", "7", "佐藤花", "0", "20260601", "2026-06-09 03:00:00", "NULL"],
              ["0002", "7", "鈴木花子", "89000", "20260601", "2026-06-09 03:00:00", "NULL"]]},

    {"id": "CK002", "group": "業務A", "shell": "ck002.sh", "out": "ck002_shukei.csv", "kind": RECORD,
     "inputs": 2,  # 다중입력 시연(2 입력)
     "header": ["TX_ID", "KOKYAKU_ID", "KINGAKU"],
     "asis": [["T001", "0001", "5000"], ["T002", "0002", "12000"], ["T003", "0003", "300"]],
     "tobe": [["T002", "0002", "12000"], ["T001", "0001", "5000.0"], ["T003", "0003", "300"]]},

    {"id": "CK003", "group": "業務A", "shell": "ck003.sh", "out": "ck003_kensho.csv", "kind": RECORD,
     "header": ["KOKYAKU_ID", "ZANDAKA"],
     "asis": [["0001", "1000.00"], ["0002", "2000.00"], ["0003", "3000.00"]],
     "tobe": [["0001", "1000"], ["0002", "2500"], ["0003", "3000"]]},  # ★0002 값변경 → NG

    {"id": "CK004", "group": "業務A", "shell": "ck004.sh", "out": "ck004_chohyo.txt", "kind": RAW,
     "asis": "帳票ヘッダ\n合計: 1,234,567 円\n明細件数: 42\n",
     "tobe": "帳票ヘッダ\n合計: 1,234,567 円\n明細件数: 42\n"},  # byte 완전일치 → OK

    {"id": "CK005", "group": "業務A", "shell": "ck005.sh", "out": "ck005_seikyu.txt", "kind": RAW,
     "asis": "請求書\n金額: 50000\n承認: 済\n",
     "tobe": "請求書\n金額: 50000\n承認: 未\n"},  # ★承認 済→未 → NG

    {"id": "CK006", "group": "業務A", "shell": "ck006.sh", "out": "ck006_kouza.txt", "kind": RAW,
     "asis": "口座番号,氏名\n12345,山田\n67890,鈴木\n",
     "tobe": "口座番号,氏名  \r\n12345,山田\r\n67890,鈴木   \r\n"},  # CRLF·우공백 → text OK

    {"id": "CK007", "group": "業務A", "shell": "ck007.sh", "out": "ck007_kinri.csv", "kind": RECORD,
     "header": ["CODE", "RATE"],
     "asis": [["A", "0.0150"], ["B", "0.0200"], ["C", "0.0075"]],
     "tobe": [["A", "0.015"], ["B", "0.02"], ["C", "0.0075"]]},  # num:4 → OK

    {"id": "CK008", "group": "業務A", "shell": "ck008.sh", "out": "ck008_tesuryo.csv", "kind": RECORD,
     "header": ["KOKYAKU_ID", "TESU_CD", "KINGAKU"],
     "asis": [["0001", "00100", "500"], ["0002", "00200", "800"]],
     "tobe": [["0001", "100", "500"], ["0002", "200", "800"]]},  # zeropad:5 → OK

    # ── 業務B (CK009~014) ──
    {"id": "CK009", "group": "業務B", "shell": "ck009.sh", "out": "ck009_zokusei.csv", "kind": RECORD,
     "header": ["KOKYAKU_ID", "KUBUN", "BIKO"],
     "asis": [["0001", "A", ""], ["0002", "B", "メモ"], ["0003", "A", ""]],
     "tobe": [["0001", "A", "NULL"], ["0002", "C", "メモ"], ["0003", "A", "NULL"]]},  # ★KUBUN B→C → NG

    {"id": "CK010", "group": "業務B", "shell": "ck010.sh", "out": "ck010_shiten.csv", "kind": RECORD,
     "header": ["SHITEN_CD", "SHITEN_NM"],
     "asis": [["0007", "東京支店"], ["0012", "大阪支店"], ["0003", "名古屋支店"]],
     "tobe": [["0012", "大阪支店"], ["0007", "東京支店"], ["0003", "名古屋支店"]]},  # 셔플+key → OK

    {"id": "CK011", "group": "業務B", "shell": "ck011.sh", "out": "ck011_zandaka.dat", "kind": SAM,
     # 고정길이(ASCII) ID(6)+NAME(16)+AMOUNT(8). layout 시연용, 비교는 byte 통짜.
     "sam": ["000001YAMADA          00150000",
             "000002SUZUKI          00089000",
             "000003TANAKA          00250000"]},

    {"id": "CK012", "group": "業務B", "shell": "ck012.sh", "out": "ck012_kinri.dat", "kind": SAM,
     "sam": ["A 00150",
             "B 00200",
             "C 00075"]},  # ID(2)+RATE(6)

    {"id": "CK013", "group": "業務B", "shell": "ck013.sh", "out": "ck013_uriage.csv", "kind": MISSING,
     # MISSING_TOBE: 정답은 있으나 셸이 출력을 생성하지 않음(tobe_src 없음·무출력 셸).
     "header": ["KOKYAKU_ID", "URIAGE"],
     "asis": [["0001", "1000"], ["0002", "2000"]]},

    {"id": "CK014", "group": "業務B", "shell": "ck014.sh", "out": "ck014_log.txt", "kind": RAW,
     "asis": "実行ログ\n開始 09:00\n終了 09:05\n",
     "tobe": "実行ログ  \r\n開始 09:00\r\n終了 09:05\r\n"},  # text OK

    # ── 業務C (CK015~018; 019·020=DB는 complete_sample.csv에서 정의, 데이터는 DB) ──
    {"id": "CK015", "group": "業務C", "shell": "ck_shared.sh", "out": "ck015_a.csv", "kind": RECORD,
     "header": ["ID", "VAL"],
     "asis": [["1", "10"], ["2", "20"]],
     "tobe": [["2", "20"], ["1", "10"]]},  # 셔플+key → OK (N:1 공유셸)

    {"id": "CK016", "group": "業務C", "shell": "ck_shared.sh", "out": "ck016_b.txt", "kind": RAW,
     "asis": "レポートB\nstatus: ok\n",
     "tobe": "レポートB\nstatus: ok\n"},  # byte OK (N:1 같은 셸 공유)

    {"id": "CK017", "group": "業務C", "shell": "ck017.sh", "out": "ck017_tesu.csv", "kind": RECORD,
     "header": ["KOKYAKU_ID", "TESU_CD", "FEE"],
     "asis": [["0001", "0010", "100"], ["0002", "0020", "200"]],
     "tobe": [["0001", "10", "100"], ["0002", "20", "200"]]},  # 비-key 컬럼 zeropad:4 → OK

    {"id": "CK018", "group": "業務C", "shell": "ck018.sh", "out": "ck018_rep.txt", "kind": RAW,
     "asis": "月次レポート\n合計 999\n",
     "tobe": "月次レポート\n合計 999\n"},  # byte OK

    # ── VSAM(키순 저장 가정 모양) CK021~022 — ★실 고객 VSAM은 실데이터로 검증 예정(D-047 §14) ──
    # 고정길이 ID(6)+AMOUNT(8), layout 0:6;6:14, key=ID(인덱스0). 골든=키순, To-Be=물리 셔플.
    {"id": "CK021", "group": "業務B", "shell": "ck021.sh", "out": "ck021_zandaka.dat", "kind": VSAM,
     # OK: 동일값을 물리 셔플만 — key 정렬이 순서차를 흡수(byte/순서 비교였다면 false-NG였을 것).
     "vsam_golden": ["00000100150000", "00000200089000", "00000300250000"],
     "vsam_tobe":   ["00000300250000", "00000100150000", "00000200089000"]},

    {"id": "CK022", "group": "業務B", "shell": "ck022.sh", "out": "ck022_kinri.dat", "kind": VSAM,
     # NG: 셔플 + 000001 금액 실차이(...50000→...50001) — key로 짝지어 진짜 값차를 검출(정렬이 가려주지 않음).
     "vsam_golden": ["00000100150000", "00000200089000"],
     "vsam_tobe":   ["00000200089000", "00000100150001"]},

    # ── 業務D: 현실형 N:M(다입력·다출력) — 실무 배치는 마스터+트랜잭션 여러 입력→명세+집계 여러 출력 ──
    # 다출력 파일은 mock 멀티복사 셸이 자기 출력들을 tobe_src에서 복사(런너는 outputs[0] 경로만 전달, D-033 제약).
    {"id": "CK023", "group": "業務D", "shell": "ck023.sh", "kind": RECORD, "inputs": 3,  # 口座M+取引+支店M
     "outs": [
         {"out": "ck023_meisai.csv", "kind": RECORD,
          "header": ["KOKYAKU_ID", "SHITEN_CD", "KINGAKU"],
          "asis": [["0001", "0007", "5000"], ["0002", "0007", "12000"], ["0003", "0012", "300"]],
          "tobe": [["0002", "0007", "12000"], ["0001", "0007", "5000"], ["0003", "0012", "300"]]},  # 셔플+key OK
         {"out": "ck023_shukei.csv", "kind": RECORD,
          "header": ["SHITEN_CD", "GOKEI"],
          "asis": [["0007", "17000"], ["0012", "300"]],
          "tobe": [["0012", "300"], ["0007", "17000"]]},  # 셔플+key OK
     ]},

    {"id": "CK024", "group": "業務D", "shell": "ck024.sh", "kind": RECORD, "inputs": 2,  # 前日残高+当日取引
     "outs": [
         {"out": "ck024_zandaka.csv", "kind": RECORD,
          "header": ["KOKYAKU_ID", "ZANDAKA"],
          "asis": [["0001", "100000"], ["0002", "50000"]],
          "tobe": [["0001", "100000"], ["0002", "50000"]]},  # record OK
         {"out": "ck024_error.txt", "kind": RAW,
          "asis": "エラー件数: 0\n対象日: 2026-06-09\n",
          "tobe": "エラー件数: 0\n対象日: 2026-06-09\n"},  # byte OK
     ]},
]

# mock 복사 셸(파일흐름): --output-path를 받아 tobe_src/<출력명>을 복사한다(realtest 패턴).
# ★mock은 .py(D-060) — Windows에 shebang이 없어 .sh는 안 돌므로, runner가 인터프리터로 실행한다.
# 셸 위치 mock_linux/opt/migsys/<業務>/sh/ → tobe_src는 5단계 상위(complete 루트) 밑(parents[5]).
_COPY_PY = '''#!/usr/bin/env python3
"""mock 업무 셸(파일흐름) — tobe_src/<출력명>을 --output-path로 바이트 복사(실 배치 자리)."""
import shutil
import sys
from pathlib import Path


def main(argv):
    out = None
    i = 1
    while i < len(argv):
        if argv[i] == "--output-path" and i + 1 < len(argv):
            out = Path(argv[i + 1]); i += 2
        else:
            i += 1
    if out is None:
        print("no --output-path", file=sys.stderr); return 2
    src = Path(__file__).resolve().parents[5] / "tobe_src" / out.name
    if not src.is_file():
        print(f"tobe_src なし: {src}", file=sys.stderr); return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
'''

# MISSING_TOBE 시연 셸 — 정상 종료(exit 0)하되 출력을 생성하지 않는다(정답 有·To-Be 無).
_NOOP_PY = '''#!/usr/bin/env python3
"""MISSING_TOBE デモ — 出力を生成せず正常終了(exit 0)。比較段階で To-Be 不在 → MISSING_TOBE。"""
print("出力なし(MISSING_TOBE デモ)")
'''


def _write_sh(rel: str, content: str) -> None:
    p = _HERE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _write_output(o: dict, asis_out_dir: str = "asis/output") -> None:
    """출력 1건의 골든(asis_out_dir) + To-Be 원본(tobe_src)을 종류별로 쓴다(단일·다출력 공용).

    asis_out_dir은 expected_dir override 시연용(業務D는 전용 트리). tobe_src는 항상 전역 —
    mock 셸이 tobe_src→tobe_dir(override)로 복사하므로 원본 위치는 안 바뀐다.
    """
    kind, out = o["kind"], o["out"]
    if kind == RECORD:
        _write(f"{asis_out_dir}/{out}", _csv(o["header"], o["asis"]))
        _write(f"tobe_src/{out}", _csv(o["header"], o["tobe"]))
    elif kind == SAM:
        body = ("\n".join(o["sam"]) + "\n").encode("ascii")  # 고정길이(ASCII)
        _write(f"{asis_out_dir}/{out}", body)
        _write(f"tobe_src/{out}", body)  # byte 완전일치 → OK
    elif kind == VSAM:
        # 골든=키순(정답), To-Be=물리 셔플(+값차). record+layout+key가 키로 정합.
        _write(f"{asis_out_dir}/{out}", ("\n".join(o["vsam_golden"]) + "\n").encode("ascii"))
        _write(f"tobe_src/{out}", ("\n".join(o["vsam_tobe"]) + "\n").encode("ascii"))
    elif kind == MISSING:
        _write(f"{asis_out_dir}/{out}", _csv(o["header"], o["asis"]))  # 정답만, tobe_src 없음
    else:  # RAW(byte/text)
        _write(f"{asis_out_dir}/{out}", o["asis"].encode(_ENC))
        _write(f"tobe_src/{out}", o["tobe"].encode(_ENC))


def _multi_copy_py(names: list[str]) -> str:
    """다출력 mock 셸(.py, D-060) — 자기 출력들(baked)을 tobe_src에서 --output-path 디렉토리로 복사.

    런너는 outputs[0] 경로만 --output-path로 넘기므로(D-033 계약), 나머지 출력은 셸이 같은
    디렉토리에 만든다(실 배치는 자기 I/O 위치가 고정이라는 가정과 일치). NG/MISSING엔 미사용.
    """
    baked = ", ".join(repr(n) for n in names)
    return f'''#!/usr/bin/env python3
"""mock 멀티출력 셸 — 자기 출력들을 tobe_src에서 --output-path 디렉토리로 복사(실 배치는 자기 I/O 고정)."""
import shutil
import sys
from pathlib import Path

NAMES = [{baked}]


def main(argv):
    out = None
    i = 1
    while i < len(argv):
        if argv[i] == "--output-path" and i + 1 < len(argv):
            out = Path(argv[i + 1]); i += 2
        else:
            i += 1
    if out is None:
        print("no --output-path", file=sys.stderr); return 2
    src_dir = Path(__file__).resolve().parents[5] / "tobe_src"
    out.parent.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        src = src_dir / name
        if not src.is_file():
            print(f"tobe_src なし: {{src}}", file=sys.stderr); return 1
        shutil.copyfile(src, out.parent / name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
'''


def main() -> int:
    shells: dict[str, str] = {}  # (group/shell) → 종류(copy/noop). 같은 값 공유=N:1.
    for c in CHECKS:
        cid = c["id"].lower()
        # 業務D는 데이터가 전용 트리(業務D_io/)에 산다 — 정의 파일이 src_dir/expected_dir로 명시(override 시연).
        # 그 외는 전역 config 경로(asis/input·asis/output). tobe_src는 항상 전역(셸 복사 원본).
        io_dir = "業務D_io" if c["group"] == "業務D" else None
        in_dir = f"{io_dir}/asis_in" if io_dir else "asis/input"
        out_dir = f"{io_dir}/asis_out" if io_dir else "asis/output"

        n_in = c.get("inputs", 1)
        for i in range(1, n_in + 1):
            suffix = f"_in{i}" if n_in > 1 else "_in"
            _write(f"{in_dir}/{cid}{suffix}.csv",
                   _csv(["IN_KEY", "IN_DATA"], [["1", f"{c['id']}-入力{i}"]]))

        outs = c.get("outs") or [c]   # 단일출력 항목은 항목 자신이 그 1개 출력(하위호환)
        for o in outs:
            _write_output(o, out_dir)

        # ★mock 파일명은 .py로 생성(D-060 — CHECKS의 .sh 표기는 셸 식별자, 실파일은 크로스플랫폼 .py)
        stem = c["shell"].rsplit(".", 1)[0]
        rel_sh = f"mock_linux/opt/migsys/{c['group']}/sh/{stem}.py"
        if any(o["kind"] == MISSING for o in outs):
            shells[rel_sh] = _NOOP_PY
        elif len(outs) > 1:
            shells[rel_sh] = _multi_copy_py([o["out"] for o in outs])  # 다출력=멀티복사 셸(baked)
        else:
            shells[rel_sh] = _COPY_PY

    for rel_sh, content in shells.items():
        _write_sh(rel_sh, content)

    # ── DB CK 입력(CK019=데모 스키마 / CK020=rt_* 스키마) + 래퍼 셸 ──
    # 골든(asis/output)은 make_db_golden.py가 clean 경로로 생성(파일 CK 골든은 위에서 확정).
    _write("asis/input/ck019_in.csv", _csv(
        ["tx_id", "customer_id", "tx_date", "tx_type", "amount", "balance_after", "branch_code", "memo"],
        [["T001", "C0001", "2026-06-01", "入金", "200000", "1700000", "101", "給与振込"],
         ["T002", "C0002", "2026-06-01", "出金", "50000", "89000", "101", ""]]))
    _write("asis/input/ck020_tx.csv", _csv(
        ["tx_id", "customer_id", "tx_date", "tx_type", "amount", "balance_after", "branch_code", "memo"],
        [["TR01", "C0001", "2026-06-01", "入金", "200000", "1700000", "101", "給与"],
         ["TR02", "C0002", "2026-06-01", "出金", "50000", "89000", "101", ""]]))
    _write("asis/input/ck020_cust.csv", _csv(
        ["customer_id", "name", "kana", "birth_date", "branch_code", "account_type", "balance", "opened_date"],
        [["C0001", "田中太郎", "タナカタロウ", "1980-04-15", "101", "普通", "1500000", "2015-06-01"],
         ["C0002", "鈴木花子", "スズキハナコ", "1985-08-20", "101", "普通", "800000", "2016-03-01"]]))
    # DB 래퍼도 .py(D-060) — stub을 현재 인터프리터로 호출(Windows에 python3 별칭이 없을 수 있음).
    _db_wrap = '''#!/usr/bin/env python3
"""mock 업무 셸(DB) — repo stub_batch/의 실 DB stub을 호출(§1: DB 로직은 stub_batch에만)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
raise SystemExit(
    subprocess.run([sys.executable, str(ROOT / "stub_batch" / "%s"), *sys.argv[1:]]).returncode
)
'''
    _write_sh("mock_linux/opt/migsys/業務C/sh/ck019_db.py", _db_wrap % "run_batch_db.py")
    _write_sh("mock_linux/opt/migsys/業務C/sh/ck020_db.py", _db_wrap % "run_settlement.py")

    print(f"生成: {len(CHECKS)} 체크리스트(파일흐름) + {len(shells)} mock 셸 + DB CK 2건(019/020) 입력·래퍼 (Shift-JIS)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
