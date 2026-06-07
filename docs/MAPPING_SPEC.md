# MAPPING_SPEC — 매핑표(long 매핑 CSV) 설계 정본

> 매핑표(long 매핑 CSV: `samples/complete/complete_sample.csv`(정본 데모셋) / `tools/mapping_to_definition.py`)의 **설계 정본**.
> 스캐너·lint 등 실제 구현은 **고객 폴더 실제 규칙 + As-Is/SAM 데이터 1부 입수 후**(아래 §8). 추측 구현 금지.
> 정본 연계: DEFINITION_SPEC.md(YAML 정본)·DECISIONS.md(D-038~D-042)·HANDOFF_5.md·CONTEXT.md·DESIGN_TOKENS.md.

## 1. 폴더 스캐너 (정의 골격 자동 생성) — E7 1순위
고객 폴더 구조: `<체크리스트번호>/input/*` · `<체크리스트번호>/output/*`
(폴더명 = 체크리스트 번호 = 실제 체크리스트와 일치)
- 스캔이 **자동으로 채움**: checklist(폴더명)·kind(input/output)·file(파일명)·expected(output 파일명)·경로(src_dir/expected_dir).
- input/ 파일 N개 → input N행, output/ 파일 M개 → output M행 (다중 입출력 자동 전개).
- 개념 프로토타입으로 가능성 확인(레포 미포함·참조용. 전략 세션 산물 checklist-folders-sample/folder_scan_prototype.py — CK002 다중입력 OK). 실 스캐너는 데이터 입수 후 신규 구현(D-042).
- ★구현은 고객 폴더 실제 규칙 확정 후(§8).

## 2. 컬럼 다이어트 (사람 손작업 최소화)
> 대상 = **long 매핑 CSV**(YAML 정의 필드와 별개). encoding/has_header/delimiter 전역화는 **config에 `has_header`·`delimiter` 키 신설**을 포함한다(D-041, **설계 확정·구현은 데이터 입수 후**).
- **삭제**: `test_name`, `name`. (폴더가 못 줌=손작업인데 비교에 불필요. 이름은 번호로 원본 체크리스트에서 찾음)
- **전역 기본값으로 이동**(행별 칸에서 제거, config 1곳): `encoding`(=shift_jis), `has_header`(=true), `delimiter`(=,).
  → 예외만 해당 행에서 override.
- **원칙(공통)**: "비우면 config 기본값, 적으면 그 행 우선(override)." 반복되는 고정값은 전부 전역으로.

## 3. shell (배치 지정)
- 매핑표에 **shell 칼럼 유지**. 채우기는 **엑셀 복붙/드래그** 전제(상속·범위규칙 같은 도구 로직 만들지 말 것 — 과설계).
- 그룹별로 셸 다름(예: 1~100=A, 101~200=B)도 복붙으로 채움. 도구는 칼럼값 읽기만.
- **2층 분리**(D-040): 매핑표 shell엔 **단축 잡명만**(예: `job001` — 풀패스 금지). 배치 *디렉토리·호출규약*
  (인자형식·성공코드·env)은 **config 전역 1벌**(C6 BatchConfig)이 결합한다. CK1~100이 같은 셸이면 config default_shell 한 줄도 가능(복붙도 무방).

## 4. type / table (DB·파일 — 둘 다 섞임 확정)
- `type` = database / file. **행별로 다를 수 있음**(한 체크리스트에 DB·파일 출력 혼재 가능). 유지.
- type=database면 `table`(적재/결과 테이블) 필수 — **폴더가 못 줌 → 사람/카탈로그**.
  DB 적재 목적지는 디렉토리가 아니라 table.
- type=file이면 table 불필요(파일 경로로 비교).

## 5. 비교 옵션 (폴더가 못 주는 + 사람 판단)
- `key`: **export 시 `ORDER BY key`로 행순서를 결정화**하는 정렬키(보통 PK). **DB 출력 필수** — 없으면
  SELECT 순서 비결정으로 전건 false-NG. 결정화 후 **통짜 바이트 비교가 1순위**, record(키 정합)는 순서 결정화
  불가 시 폴백(D-038). 즉 key는 "정렬 결정화용"이지 "정합 비교용"이 아니다.
- `mask`: 매번 정상적으로 다른 컬럼 무시(更新日時·시퀀스ID). "보지 마".
- `normalize`: 표기차 흡수(date/num/zeropad/nullblank/trim). "보되 형식 맞춤". 풀세트 구현·유지됨.
- `layout`(SAM): SAM이면 **칼럼은 존재하되, 값은 mask/normalize를 걸 때만 채운다**(D-039). 순수 byte 비교
  SAM은 layout 없이 된다. 바이트위치 "0:6;6:26;..", 카피북에서 옴(폴더·카탈로그 못 줌).
- ★**자동 채우기 금지**(특히 normalize/mask). 카탈로그 있으면 key·타입에서 *후보 제안*까지만, **결정은 항상 사람**.
  과한 normalize/mask = **false-PASS(결함 은폐)** = 現新比較 최악. 사람이 false-NG 확인 후 그 컬럼만, 이유 명시.

## 6. SAM(고정길이) 섞임 — 확정 사항
- 비교 대상에 CSV + **SAM(고정길이) 혼재**. → `layout` 칼럼 *유지*(뺄 후보 아님). **값은 mask/normalize 필요 시에만**(D-039) — 순수 byte SAM은 빈칸.
- SAM 비교는 layout·패딩(공백/제로)·인코딩(Shift-JIS 반각/전각)이 민감 → 비교기 고정길이 모드를 **실데이터로 검증** 필요.

## 7. 자동/수동 경계 (요약)
| 칸 | 출처 |
|---|---|
| checklist·kind·file·expected·경로 | **폴더 스캔(자동)** |
| encoding·has_header·delimiter | **config 전역 기본값** |
| shell | 매핑표 칼럼, 엑셀 복붙 (또는 config default) |
| type·table | 사람(+카탈로그 후보) |
| key·mask·normalize·layout | **사람 판단**(카탈로그/카피북 후보까지, 결정은 사람. 자동적용 금지) |

## 8. 착수 조건 (중요)
- **지금 구현하지 말 것.** 고객 체크리스트 + As-Is/SAM 데이터 1부 입수 후 폴더 실제 규칙
  (폴더명 패턴·input/output 명칭·다중출력·SAM layout·파일↔테이블 대응) 확정 → 그때 스캐너·lint 구현.
- 그 전 안전한 것: lint/검증(형식 무관, 항상 작동)뿐. 채움 자동화는 실데이터 후.
