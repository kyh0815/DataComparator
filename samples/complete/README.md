# complete — 단일 정본 데모셋 (現新比較 E2E)

샘플셋 단일화의 **정본 1벌**. 한 시나리오로 비교기 전 기능을 한 바퀴 돌린다(프리플라이트→실행→비교→試験成績書).
구 픽스처(samples/asis·realtest·rehearsal·realistic)가 덮던 케이스를 **이 셋이 전부 흡수**한다(아래 ④ 대조표).

> ⚠️ **SAMPLE — 실데이터 아님.** `complete_sample.csv`의 normalize/mask/layout 값은 형식 예시일 뿐
> 실제 마이그레이션 판단이 아니다. 복사해 실정의로 쓸 때 검증된 기본값으로 신뢰하지 말 것(과한 mask/normalize = false-PASS).

## 구성
```
complete_sample.csv      정의(사람이 채우는 Long CSV) — 정본 24 체크리스트. shell_group·전 칼럼·SAM/VSAM·N:M 시연.
config.yaml.example      ★커밋되는 완전판 설정 예시(업무A~D 그룹·데모 경로·DB placeholder+env). cp→config.yaml.
config.yaml              실행 설정(.gitignore=자격 보호). 없으면 run_demo.sh가 example에서 자동 생성.
test_definition.yaml     complete_sample.csv → mapping_to_definition 변환물(비노출 중간물).
make_complete_data.py    asis/input·asis/output(파일 골든)·tobe_src·mock_linux 셸 생성기(결정론).
make_db_golden.py        DB CK(019/020) 골든만 clean 경로로 생성(파일 골든은 안 건드림). DB 필요.
mock_linux/opt/migsys/<業務>/sh/*.sh   실행되는 mock 셸(파일=복사 / MISSING=무출력 / DB=repo stub 래퍼).
asis/input, asis/output, tobe_src      입력·정답·To-Be 원본(생성물, 커밋). tobe/·reports/는 런타임(gitignore).
業務D_io/asis_in, 業務D_io/asis_out    ★dir override 시연 — 業務D 데이터가 config 공통 경로가 아닌 전용 트리에.
                                       정의가 src_dir/expected_dir로 명시(없으면 config 폴백). To-Be는 tobe/ 하위(런타임).
```

> **★디렉토리 override 시연(D-036)**: 디렉토리는 보통 config 공통이지만, 업무·항목마다 흩어질 수 있다.
> 정의(매핑 CSV)의 `src_dir·dest_dir·dest_name·expected_dir·tobe_dir`에 적으면 **그 행이 config보다 우선**,
> 비우면 config 폴백(항목 > 업무그룹 > 전역). CK023/024=전체 override(業務D_io 전용트리), CK001=tobe_dir 한 칸만(부분).
> 적은 경로가 전역 config 경로를 실제로 덮어 e2e가 도는 걸로 우선순위를 증명(override 미사용이면 파일 못 찾아 MISSING).

## 실행 (repo 루트)
```sh
python3 samples/complete/make_complete_data.py                 # 데이터·mock 셸 (재)생성
# DB CK(019/020) 사용 시: 스키마 적용 + DB 골든 생성 (dc-pg)
psql ... -f db/schema.sql ; psql ... -f db/schema_realistic.sql
POSTGRES_PASSWORD='<자기비번>' python3 samples/complete/make_db_golden.py
# 한 바퀴
POSTGRES_PASSWORD='<자기비번>' python3 -m src.cli.main --preflight --config samples/complete/config.yaml
POSTGRES_PASSWORD='<자기비번>' python3 -m src.cli.main           --config samples/complete/config.yaml
POSTGRES_PASSWORD='<자기비번>' python3 -m src.cli.main --evidence --config samples/complete/config.yaml
```
DB가 없으면 프리플라이트가 019/020 DB접속불가로 **전건 거부**(C3 게이트가 DB 유무로 올바르게 갈라줌).
파일흐름 22건만 보려면 DB를 띄우지 않고 프리플라이트 거부를 확인하거나, DB를 띄워 24건 완주한다.

## 의도된 결과 (출력단위 27건 = 24 CK, 다중출력: CK020·CK023·CK024)
- **OK 22 / NG 4 / MISSING_TOBE 1 / ERROR 0**
- NG 4: CK003(残高 값변경) · CK005(承認 済→未) · CK009(区分 B→C) · CK022(VSAM 金額 값차) — 진짜 결함.
- MISSING_TOBE 1: CK013(정답 有·To-Be 미생성). MISSING_ASIS는 프리플라이트가 사전 차단(증적 미표기가 정상).

## 체크리스트 맵
| CK | 業務 | 흐름·모드 | 시연 |
|---|---|---|---|
| 001 | A | record | zeropad·num·date·nullblank·**mask**·셔플+key + **tobe_dir 부분 override**(한 칸만) (OK) |
| 002 | A | record | **다중입력(2)**·num (OK) |
| 003 | A | record | **NG**(残高 값변경) |
| 004 | A | byte(.txt) | 완전일치 (OK) |
| 005 | A | byte(.txt) | **NG**(済→未) |
| 006 | A | text(.txt) | CRLF·우공백 정규화 (OK) |
| 007 | A | record | num:4 (OK) |
| 008 | A | record | zeropad:5 (OK) |
| 009 | B | record | **NG**(区分 B→C) |
| 010 | B | record | 셔플+key (OK) |
| 011 | B | **SAM** byte | type=sam → 고정길이 순차·byte 통짜(D-039/D-047) (OK) |
| 012 | B | **SAM** byte | type=sam (OK) |
| 013 | B | record | **MISSING_TOBE**(무출력 셸) |
| 014 | B | text(.txt) | (OK) |
| 015 | C | record | **N:1**(ck_shared.sh 공유) (OK) |
| 016 | C | byte(.txt) | **N:1**(같은 셸 공유) (OK) |
| 017 | C | record | 비-key zeropad:4 (OK) |
| 018 | C | byte(.txt) | (OK) |
| 019 | C | **DB-export 단일** | type=database+table+**key**(tx_id)·record·SJIS·헤더 (OK) |
| 020 | C | **DB-export 다중출력** | 한 배치→파일 明細 + DB 集計(rt_summary export) (OK×2) |
| 021 | B | **VSAM** record+key | type=vsam → 고정길이 키순·물리 셔플을 key 정렬이 흡수 (OK) |
| 022 | B | **VSAM** record+key | type=vsam → 셔플+金額 실차이를 key로 짝지어 **NG** 검출 |
| 023 | D | **N:M** 3입력→2출력 | 현실형 다입력·다출력(明細+集計)·멀티복사 셸 + **dir override**(業務D_io 전용트리) (OK×2) |
| 024 | D | **N:M** 2입력→2출력 | 残高 record + エラー byte·다출력 + **dir override** (OK×2) |

> **★VSAM(CK021/022)은 "가정 모양" 데모다.** 코드변환은 형식 보존이라 VSAM은 VSAM(고정길이)으로 온다.
> **현재 VSAM→record+layout+key는 KSDS(키순 저장) 가정**이다 — KSDS는 키순 저장이라 물리 행순서가 As-Is/To-Be 간
> 어긋날 수 있어(특히 To-Be가 RDB면 ORDER BY 없이는 순서 비보장) byte/순서 비교는 false-NG → **key 정렬·정합 필수**.
> VSAM 다른 종류: **ESDS(입력순)는 byte로 충분, RRDS는 번호순**. 실무 업무배치는 대부분 KSDS라 record+key가 안전한
> 기본값이고, record+key는 ESDS에도 틀리지 않는다(불필요 정렬일 뿐) → **지금 3종 분기 구현 안 함**(실데이터에 ESDS/RRDS 실재 시 type 분기, D-047 deferred).
> 데모 stub은 "SAM과 동일 고정길이 + 키순"이라는 가정으로 layout(0:6;6:14)·key(ID 인덱스0)를 둔 것이며,
> **실제 고객 VSAM의 layout 바이트위치·key 컬럼·key 유일성은 실 SAM/VSAM 1건 입수 후 검증**한다(D-047). 021=순서흡수 OK, 022=값차 NG로 양방향(정렬이 가리지 않음) 증명.

> **1:N(shell `;`)**: 미지원(실연결 보류) → mapping_to_definition이 거부(테스트 `test_shell_semicolon_sequence_rejected`).
> 데모셋에 실행 CK로 넣지 않는다(green run 보존).

## ④ 커버리지 대조표 (구 픽스처 삭제 게이트 근거)
| 구 픽스처 | 커버 항목 | 새 셋 흡수 | 확인 |
|---|---|---|---|
| **realtest** | record/byte/text | CK001~018 모드 혼합 | e2e OK |
| | zeropad/num/date/nullblank/mask | CK001(전부)·002·007·008·017 | e2e OK |
| | 셔플+key | CK001·010·015 | e2e OK |
| | NG 3건(값/byte/区分) | CK003·005·009 | 試験成績書 NG 3 |
| | csv/txt | .csv 다수 + .txt(004·005·006·014·016·018) | e2e OK |
| **rehearsal** | DB-export 형식(SJIS·헤더) | CK019(record·has_header·SJIS export) | e2e OK |
| **realistic** | DB-export 실행경로 | CK019·020(loader→배치→exporter 실 DB) | e2e OK |
| | **다중출력** | CK020 = 파일 明細 + DB 集計 (**2출력**) | 출력단위 2건 OK |
| **+ MISSING_TOBE** | 試験成績書 표기 | CK013 | 試験成績書 MISSING_TOBE 1 |
| **+ MISSING_ASIS** | 프리플라이트 차단(증적 미표기가 정상) | `test_preflight.test_missing_expected_is_error` | 테스트 통과 |
| **+ 1:N(lint만)** | shell `;` 거부 | `test_mapping_to_definition.test_shell_semicolon_sequence_rejected` | 테스트 통과 |
| **+ shell_group 3업무** | batch.groups lint | 業務A/B/C, preflight `_check_shell_group` | 통과 |

> ★**realistic 3출력 → CK020 2출력 축소**: realistic은 決済/集計/夜間 3출력. CK020은 run_settlement
> 재사용으로 **파일+DB 2출력**(다중출력 메커니즘은 동일하게 "한 배치→출력 N개 자동 전개"로 검증). 夜間(파일입력·
> 항목별 경로 override)은 본 데모 범위에서 생략(필요 시 별 CK로 추가 가능).
