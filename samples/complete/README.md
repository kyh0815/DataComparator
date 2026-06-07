# complete — 단일 정본 데모셋 (現新比較 E2E)

샘플셋 단일화의 **정본 1벌**. 한 시나리오로 비교기 전 기능을 한 바퀴 돌린다(프리플라이트→실행→비교→試験成績書).
구 픽스처(samples/asis·realtest·rehearsal·realistic)가 덮던 케이스를 **이 셋이 전부 흡수**한다(아래 ④ 대조표).

> ⚠️ **SAMPLE — 실데이터 아님.** `complete_sample.csv`의 normalize/mask/layout 값은 형식 예시일 뿐
> 실제 마이그레이션 판단이 아니다. 복사해 실정의로 쓸 때 검증된 기본값으로 신뢰하지 말 것(과한 mask/normalize = false-PASS).

## 구성
```
complete_sample.csv      정의(사람이 채우는 Long CSV) — 정본 20 체크리스트. shell_group·전 칼럼 시연.
config.yaml              실행 설정(파일흐름 18 + DB 2). batch.groups=業務A/B/C(lint 태그).
test_definition.yaml     complete_sample.csv → mapping_to_definition 변환물(비노출 중간물).
make_complete_data.py    asis/input·asis/output(파일 골든)·tobe_src·mock_linux 셸 생성기(결정론).
make_db_golden.py        DB CK(019/020) 골든만 clean 경로로 생성(파일 골든은 안 건드림). DB 필요.
mock_linux/opt/migsys/<業務>/sh/*.sh   실행되는 mock 셸(파일=복사 / MISSING=무출력 / DB=repo stub 래퍼).
asis/input, asis/output, tobe_src      입력·정답·To-Be 원본(생성물, 커밋). tobe/·reports/는 런타임(gitignore).
```

## 실행 (repo 루트)
```sh
python3 samples/complete/make_complete_data.py                 # 데이터·mock 셸 (재)생성
# DB CK(019/020) 사용 시: 스키마 적용 + DB 골든 생성 (dc-pg)
psql ... -f db/schema.sql ; psql ... -f db/schema_realistic.sql
POSTGRES_PASSWORD=devpw python3 samples/complete/make_db_golden.py
# 한 바퀴
POSTGRES_PASSWORD=devpw python3 -m src.cli.main --preflight --config samples/complete/config.yaml
POSTGRES_PASSWORD=devpw python3 -m src.cli.main           --config samples/complete/config.yaml
POSTGRES_PASSWORD=devpw python3 -m src.cli.main --evidence --config samples/complete/config.yaml
```
DB가 없으면 프리플라이트가 019/020 DB접속불가로 **전건 거부**(C3 게이트가 DB 유무로 올바르게 갈라줌).
파일흐름 16건만 보려면 DB를 띄우지 않고 프리플라이트 거부를 확인하거나, DB를 띄워 20건 완주한다.

## 의도된 결과 (출력단위 21건 = 20 CK, CK020 다중출력 2)
- **OK 17 / NG 3 / MISSING_TOBE 1 / ERROR 0**
- NG 3: CK003(残高 값변경) · CK005(承認 済→未) · CK009(区分 B→C) — 진짜 결함.
- MISSING_TOBE 1: CK013(정답 有·To-Be 미생성). MISSING_ASIS는 프리플라이트가 사전 차단(증적 미표기가 정상).

## 체크리스트 맵
| CK | 業務 | 흐름·모드 | 시연 |
|---|---|---|---|
| 001 | A | record | zeropad·num·date·nullblank·**mask**·셔플+key (OK) |
| 002 | A | record | **다중입력(2)**·num (OK) |
| 003 | A | record | **NG**(残高 값변경) |
| 004 | A | byte(.txt) | 완전일치 (OK) |
| 005 | A | byte(.txt) | **NG**(済→未) |
| 006 | A | text(.txt) | CRLF·우공백 정규화 (OK) |
| 007 | A | record | num:4 (OK) |
| 008 | A | record | zeropad:5 (OK) |
| 009 | B | record | **NG**(区分 B→C) |
| 010 | B | record | 셔플+key (OK) |
| 011 | B | **SAM** byte | 고정길이·layout 칼럼 표기(byte 통짜, D-039) (OK) |
| 012 | B | **SAM** byte | 고정길이 (OK) |
| 013 | B | record | **MISSING_TOBE**(무출력 셸) |
| 014 | B | text(.txt) | (OK) |
| 015 | C | record | **N:1**(ck_shared.sh 공유) (OK) |
| 016 | C | byte(.txt) | **N:1**(같은 셸 공유) (OK) |
| 017 | C | record | 비-key zeropad:4 (OK) |
| 018 | C | byte(.txt) | (OK) |
| 019 | C | **DB-export 단일** | type=database+table+**key**(tx_id)·record·SJIS·헤더 (OK) |
| 020 | C | **DB-export 다중출력** | 한 배치→파일 明細 + DB 集計(rt_summary export) (OK×2) |

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
