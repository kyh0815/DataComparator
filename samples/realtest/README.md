# realtest — 実際に動作する定義ファイルサンプル(現新比較)

사전점검 통과 + 검증실행까지 **실제로 도는** 풀세트. 銀行勘定系 10 체크리스트(파일 흐름, DB 불요).
Long CSV 20행(체크리스트당 입력+출력 2행), 모드 혼합(record/byte/text)·정규화·의도된 **OK 7 / NG 3**.

## 구성
```
config.yaml              실행 설정(상대경로, Shift-JIS)
shell_mapping.csv        정의(사람이 채우는 Long CSV) — 10 체크리스트
test_definition.yaml     위 CSV를 변환한 정본(mapping_to_definition 생성)
make_realtest_data.py    As-Is 입력/정답 + To-Be 소스 생성기(Shift-JIS)
batch/run_batch.py       더미 배치(진짜 배치 자리) — tobe_src/<출력명>을 출력으로 복사
asis/input/              입력 데이터(존재용)
asis/output/             정답(As-Is 출력) = expected
tobe_src/                To-Be 원본(플랫폼차이·결함 심음) — 배치가 이걸 출력으로 냄
tobe/, reports/          런타임 생성물(.gitignore)
```

## 체크리스트(의도된 결과)
| ID | 내용 | 모드 | 결과 | 비고 |
|---|---|---|---|---|
| CK001 | 顧客残高マスタ | record | OK | 셔플·zeropad·num·date·nullblank·mask 정규화 흡수 |
| CK002 | 取引明細集計 | record | OK | 셔플 + num:0 |
| CK003 | 残高検証 | record | **NG** | ★0002 ZANDAKA 2000→2500 (진짜 결함) |
| CK004 | 帳票 | byte | OK | 완전 일치 |
| CK005 | 請求書 | byte | **NG** | ★承認 済→未 (진짜 결함) |
| CK006 | 口座一覧 | text | OK | CRLF·우측공백 정규화 |
| CK007 | 金利マスタ | record | OK | num:4 |
| CK008 | 手数料 | record | OK | zeropad:5 |
| CK009 | 顧客属性 | record | **NG** | ★0002 KUBUN B→C (진짜 결함) |
| CK010 | 支店マスタ | record | OK | 셔플만(key 정렬) |

## 실행 (repo 루트)
```sh
python3 samples/realtest/make_realtest_data.py            # (재)생성 필요 시
python3 -m src.cli.main --preflight --config samples/realtest/config.yaml   # → 通過
python3 -m src.cli.main           --config samples/realtest/config.yaml   # → 全件10/OK7/NG3
python3 -m src.cli.main --evidence --config samples/realtest/config.yaml  # → 試験結果一覧.xlsx
```

## 동작 원리(왜 통과하는가)
정의의 경로가 **실제 파일**을 가리킵니다(상대경로 → 정의파일 폴더 기준):
- 입력 `asis/input/ckNNN_in.csv`, 정답 `asis/output/<출력명>` 존재
- shell `batch/run_batch.py` 존재, 출력 디렉토리 `tobe/output` 쓰기 가능
→ 사전점검 通過. 배치가 `tobe_src/<출력명>`을 `tobe/output`으로 내고, 비교기가 정답과 대조해 OK/NG 판정.

※ 더미 배치는 입력→출력을 *계산*하지 않고 준비된 To-Be를 복사합니다(검증 대상 고정용 스텁).
실 배치로 교체 시 `shell_mapping.csv`의 shell 열만 실 배치 경로로 바꾸면 됩니다(코어 0줄 수정, C6).
