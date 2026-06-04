#!/usr/bin/env python3
"""체크리스트(항목명 목록) → 고객 기입용 매핑 CSV 템플릿 (Phase 7, D-035 보조).

고객 체크리스트(전각체크·맥시멈체크…) **항목명**을 받아, 항목마다 한 블록(입력행+출력행)을
가진 **빈 매핑 CSV 템플릿**을 만든다. `shell_id`는 체크리스트 순서대로 자동 번호,
`test_name`엔 항목명을 미리 박는다. 고객은 **빈 칸(타입·배치·테이블·입력/정답 파일명)만**
채우면 되고, 다중 입출력 항목은 같은 shell_id로 행을 더 추가한다.

채운 CSV는 `tools/mapping_to_definition.py`로 `test_definition.yaml`로 변환한다. 이렇게 하면
정의 순서·리포트·화면이 **체크리스트와 1:1**로 정렬돼 추적·관리가 쉽다(사용자 요청).

입력 체크리스트: **텍스트 1줄 = 1항목**. 앞의 번호/불릿(`1)` · `1.` · `①` · `-` · `・` · `*`)은 떼어낸다.
사용:
  python tools/checklist_to_template.py checklist.txt -o mapping_template.csv
  python tools/checklist_to_template.py checklist.txt --inputs 2 --outputs 1   # 골격 행 수 조정
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from pathlib import Path

# 헤더 = 매핑 CSV(Long)와 동일(그대로 mapping_to_definition.py에 먹임).
# 뒤쪽 격납 패스 열(src_dir~tobe_dir)은 **선택**(비우면 config 공통 디렉토리) — 사장님 규격 11항목 대응.
_HEADER = [
    "checklist", "kind", "type", "shell", "table", "file", "expected", "name", "test_name", "timeout",
    "src_dir", "dest_dir", "dest_name", "expected_dir", "tobe_dir",
]
# 줄 앞 번호/불릿: "1)" "1." "①~⑳" "-" "・" "*" "•" 등.
_BULLET = re.compile(r"^\s*(?:\d+\s*[\)\.\:]|[①-⑳]|[-・*•‣◦])\s*")


def parse_checklist(text: str) -> list[str]:
    """체크리스트 텍스트 → 항목명 리스트(빈 줄 무시, 앞 번호/불릿 제거)."""
    items: list[str] = []
    for line in text.splitlines():
        name = _BULLET.sub("", line).strip()
        if name:
            items.append(name)
    return items


def checklist_to_template(text: str, inputs: int = 1, outputs: int = 1) -> str:
    """체크리스트 → 빈 기입 CSV 템플릿 문자열. 항목마다 입력 inputs행 + 출력 outputs행."""
    items = parse_checklist(text)
    pad = [""] * (len(_HEADER) - 10)  # 선택 격납 패스 열(빈 칸 = config 공통)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(_HEADER)
    for idx, name in enumerate(items, start=1):
        sid = str(idx).zfill(3)  # 로더와 같은 3자리 zero-pad
        for j in range(max(1, inputs)):
            # test_name은 셸 첫 행에만(매핑 로더가 셸별 첫 비어있지 않은 값을 씀).
            w.writerow([sid, "input", "", "", "", "", "", "", name if j == 0 else "", "", *pad])
        for _ in range(max(1, outputs)):
            w.writerow([sid, "output", "", "", "", "", "", "", "", "", *pad])
    return buf.getvalue()


def main(argv: list[str] | None = None) -> int:
    """CLI: 체크리스트 텍스트 → 기입용 매핑 CSV 템플릿."""
    parser = argparse.ArgumentParser(
        description="체크리스트(항목명 목록) → 고객 기입용 매핑CSVテンプレート 生成"
    )
    parser.add_argument("checklist", help="체크리스트 텍스트(1줄=1항목)")
    parser.add_argument("-o", "--output", help="出力 CSV パス（省略時は標準出力）")
    parser.add_argument("--inputs", type=int, default=1, help="항목당 입력 골격 행 수(기본 1)")
    parser.add_argument("--outputs", type=int, default=1, help="항목당 출력 골격 행 수(기본 1)")
    args = parser.parse_args(argv)

    path = Path(args.checklist)
    if not path.is_file():
        print(f"체크리스트 파일을 찾을 수 없습니다: {path}", file=sys.stderr)
        return 1

    # Excel 저장 대비 utf-8-sig/cp932 디코드.
    data = path.read_bytes()
    for enc in ("utf-8-sig", "cp932"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="replace")
    csv_text = checklist_to_template(text, inputs=args.inputs, outputs=args.outputs)
    n = len(parse_checklist(text))

    if args.output:
        Path(args.output).write_text(csv_text, encoding="utf-8-sig")  # 고객이 Excel로 열 것 → BOM
        print(f"기입 템플릿 생성: {args.output}（{n} 項目）", file=sys.stderr)
        print("→ 빈 칸(type·program·table·file·expected)을 채운 뒤 "
              "tools/mapping_to_definition.py 로 변환하세요.", file=sys.stderr)
    else:
        sys.stdout.write(csv_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
