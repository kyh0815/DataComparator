# 정의 파일 규격서 (test_definition.yaml)

> 現新比較ツール의 **정본(single source)**. 이 파일 하나로 Shell 1~N(최대 1000)을
> 업로드→배치 실행→출력 정규화→이동→비교→결과까지 자동 수행한다.
> 회의 확정(2026-06-03) 및 기획서 7.1(`docs/AlignmentCheck/InitialPlanning.md`)·D-033 기반.

---

## 1. 두 파일의 역할 분리

| 파일 | 담는 것 | 비고 |
|---|---|---|
| **config.yaml** (공통 1곳) | DB 접속, 디렉토리(입력/정답/To-Be출력/리포트), 인코딩 | 환경값. 셸마다 안 바뀜 |
| **test_definition.yaml** (정본) | 셸마다 **무엇을(program) / 무엇을 입력(inputs) / 무엇을 출력·비교(outputs)** | 검증 내용 |

> **DB 접속은 정의 파일에 넣지 않는다**(회의 확정 — 검증 DB 1곳 공통). 비밀번호는 모델A(env, D-019).
> **디렉토리는 config 공통, 정의엔 파일명만**(회의 확정). 실제 경로 = `config의 dir` + `정의의 파일명`.
> **단, 셸/항목마다 위치가 다르면 항목별 경로 override 가능**(D-036, 사장님 규격): `src_dir`·`dest_dir`·
> `expected_dir`·`tobe_dir`를 항목에 적으면 그 경로가 config 공통보다 우선한다(비우면 config 공통).

---

## 2. config.yaml (공통)

```yaml
encoding: Shift_JIS

paths:
  asis_input_dir:  ./asis/input      # As-Is 입력 데이터(코드변환 후) 디렉토리
  asis_output_dir: ./asis/output     # As-Is 출력 데이터(정답) 디렉토리
  tobe_output_dir: ./tobe/output     # To-Be 출력(추출/이동) 디렉토리
  report_dir:      ./out/reports      # 결과 리포트 출력 디렉토리
  tobe_input_dir:  ./tobe/input       # 파일 입력 배치가 읽을 위치(복사 대상)
  definition_file: ./test_definition.yaml

database:                            # 검증용 DB 1곳(공통)
  host: localhost
  port: 5432
  dbname: migverify
  user: verify_ro
  password_env: POSTGRES_PASSWORD    # 비번은 env에서만(모델A)
```

---

## 3. test_definition.yaml — 전체 구조

```yaml
tests:
  - shell_id: "001"                  # 셸(잡) 식별자. 문자열
    test_name: "결제 거래명세"          # 사람용 이름(선택)
    program: /opt/batch/job001        # 실행할 배치(잡) 경로. 내부에서 PGM 여러 개 순차 실행해도 1회 호출
    timeout: 300                      # 초(선택, 기본 60)

    inputs:                          # ── 다중 입력(P1 구현 완료) ──
      - { file: 거래.csv, type: database, table: transaction_log }
      - { file: 고객.csv, type: database, table: customer_master }
      - { file: 야간.csv, type: file }                 # 파일 입력(배치가 직접 읽음)

    outputs:                         # ── 다중 출력(P2) ──
      - type: database               # 배치가 DB에 쓴 결과 → CSV로 export 후 비교
        table: result_a
        export_as: 出A.csv           # tobe_output_dir에 내릴 CSV 파일명
        expected: 正解A.csv          # asis_output_dir의 정답 파일명
      - type: file                   # 배치가 파일로 낸 결과 → 그대로 비교
        file: 出B.sam                # tobe_output_dir의 배치 산출 파일명(확장자 무관: csv/sam/…)
        expected: 正解B.sam          # asis_output_dir의 정답 파일명

  - shell_id: "002"
    # ... 1000건까지 반복
```

---

## 4. 필드 상세

### 4-1. tests[] (셸 1건)

| 필드 | 필수 | 의미 |
|---|---|---|
| `shell_id` | ✅ | 셸 식별자(문자열). 리포트·모니터링 단위 |
| `test_name` | — | 사람용 이름(없으면 shell_id) |
| `program` | ✅ | 실행할 배치 경로. **잡 1개로 호출(내부 PGM 다수는 잡이 처리), 최종 출력만 비교**. (매핑표 `shell`은 **단축 잡명**, 디렉토리·호출규약은 BatchConfig가 결합 — D-040) |
| `timeout` | — | 배치 타임아웃(초, 기본 60) |
| `inputs` | ✅(≥1) | 입력 목록 → 4-2 |
| `outputs` | ✅(≥1) | 출력 목록 → 4-3 |

### 4-2. inputs[] (입력 1건 — 다중 적재, P1 완료)

| 필드 | 필수 | 의미 |
|---|---|---|
| `file`(=`csv`) | ✅ | 입력 파일명(`asis_input_dir` 기준). DB 적재 대상은 **CSV**여야(헤더=컬럼 매핑) — 규격 #2 |
| `type` | ✅ | `database`(테이블 적재) \| `file`(디렉토리 복사) — 규격 #3 |
| `table` | type=database면 ✅ | To-Be 격납(적재 대상) 테이블. 도구가 `TRUNCATE+INSERT` — 규격 #7-1 |
| `src_dir` | — | As-Is 입력 격납 패스 override(없으면 `config.asis_input_dir`) — 규격 #4 |
| `dest_dir` | — | type=file의 To-Be 격납 패스(없으면 `config.tobe_input_dir`) — 규격 #7-4 |
| `dest_name` | — | type=file의 To-Be 격납 파일명(없으면 입력 파일명 그대로) — 규격 #7-3 |

> 한 배치가 여러 테이블을 조인해 읽으므로 inputs는 **여러 건**. DB 적재분은 항목마다 commit(D-023 ①).
> *(현재 구현 필드명: `csv` — 규격 확정 시 `file`로 별칭/정렬 예정. 의미 동일.)*

### 4-3. outputs[] (출력 1건 — 다중 비교, P2)

| 필드 | 필수 | 의미 |
|---|---|---|
| `type` | ✅ | To-Be 출력 종류: `database`(결과 테이블 → CSV export) \| `file`(배치 산출 파일 그대로) — 규격 #10 |
| `table` | type=database면 ✅ | 배치가 결과를 쓴 테이블 |
| `export_as` | type=database면 ✅ | To-Be 출력 명: export할 CSV 파일명(`tobe_output_dir`) — 규격 #9 |
| `file` | type=file면 ✅ | To-Be 출력 명: 배치가 만든 파일명(`tobe_output_dir`, 확장자 무관) — 규격 #9 |
| `expected` | ✅ | As-Is 출력(정답) 명(`asis_output_dir`). To-Be 출력과 **바이트 비교** — 규격 #5 |
| `expected_dir` | — | As-Is 출력 격납 패스 override(없으면 `config.asis_output_dir`) — 규격 #7 |
| `tobe_dir` | — | To-Be 출력 격납 패스 override(없으면 `config.tobe_output_dir`) — 규격 #11 |

> 규격 #6(As-Is 출력 종류)은 **필드를 두지 않는다**(D-037 보정): 비교가 통짜 바이트라 판정에 무관하고
> 리포트·화면에도 안 쓰여 inert였으므로 사용자 결정으로 제거. 출력 종류는 To-Be 기준 `type`(#10)만 둔다.
| `name` | — | 출력 식별자(리포트/화면 라벨; 없으면 `export_as`/`file`) |

> **출력 형식과 SAM**: 비교는 **통짜 바이트**(D-004)가 기본 원칙이다(형식을 해석하지 않는다).
> - `type: file` → 배치가 만든 파일을 **그대로 비교**(SAM/CSV 등 확장자 무관).
> - `type: database` → SELECT 순서 비결정이라 그대로는 byte 비교 불가 → **export 시 `ORDER BY key`로
>   행순서를 결정화한 뒤 통짜 바이트 비교가 1순위**(D-038, 현 exporter: 컬럼순·`\n`·인코딩 D-027).
>   record(키 정합) 모드는 **순서 결정화가 불가능할 때의 폴백**. 즉 `key`는 "정렬 결정화용"이지 "정합 비교용"이 아니다.
> - **SAM은 파일 출력에서만**(회의 확정). `layout`(바이트위치)은 **그 SAM 필드에 mask/normalize를 걸 때만
>   소비**된다 — 순수 byte 비교 SAM은 layout 없이 된다(D-039). SAM export 포맷터는 불필요.

---

## 5. 처리 흐름 (셸 1건당)

```
1) UPLOAD   : inputs[] 루프 → DB면 table 적재(+commit) / file이면 dest_dir 복사
2) 배치 실행 : program 1회 호출
3) 출력 정규화: outputs[] 루프 → database면 export_as로 CSV export / file이면 그대로
4) 이동      : (정규화 산출물이) tobe_output_dir에 위치
5) 비교      : 각 출력의 (To-Be 파일) ↔ asis_output_dir/expected 바이트 비교
6) 결과      : 출력마다 OK/NG/... → 셸당 결과 N건
```

---

## 6. 검증 규칙 (로더가 거부 = DefinitionError)

- 최상위 `tests` 리스트 필수, 비어있으면 에러
- 셸: `shell_id`·`program`·`inputs`(≥1)·`outputs`(≥1) 필수
- input: `type`∈{database,file}, `file` 필수; **type=database면 `table` 필수**
- output: `type`∈{database,file}, `expected` 필수; **database면 `table`+`export_as`**, **file면 `file`** 필수
- (실행 시) inputs의 입력 파일·outputs의 expected 파일이 디렉토리에 없으면 그 항목 MISSING/ERROR로 명시(silent drop 금지)

---

## 7. 결과 출력 (회의 확정: 화면 모니터링 + CSV 리포트)

- **화면**: 버튼 1개 → Shell 1~N 자동 실행, **실시간 진행 모니터링**(현재 어느 셸/단계), 끝나면 **요약(합계/OK/NG/ERROR/MISSING)**
- **리포트 CSV**: **출력 단위** 행 — `shell_id, output, status, diff_line_count, first_diff_asis, first_diff_tobe, error_message`
- 상세 diff: `report_{TS}_details/{shell}_{output}.diff` (전건)
- 집계 단위 = **출력**(셸 1개에 출력 2개면 결과 2건)

---

## 8. 하위호환 (구형 단일 정의)

기존 단일 입출력 정의도 계속 읽는다(P1 적용):
```yaml
- test_id: "001"            # = shell_id
  input:  { type: database, table: transaction_log, csv: 001.csv }   # → inputs 1건으로 정규화
  output: { type: file, file: 001.csv }                              # → outputs 1건(P2)
  expected_output_csv: 001.csv                                       # → outputs[0].expected
```
→ 신형(`inputs`/`outputs` 리스트)과 구형(단일) 모두 내부적으로 리스트로 정규화.

---

## 9. 구현 단계 매핑

| 영역 | 상태 |
|---|---|
| 다중 입력(`inputs[]` 적재) | ✅ **P1 완료**(D-033) |
| 다중 출력(`outputs[]` export·비교·결과 N건) | ⏳ **P2** (모델 `output_name`, runner 다중출력, reporter (shell,output) 행, RunSummary total=출력수, 진행이벤트·GUI) |
| UI 경량화(매핑/연결 UI 제거 → 버튼+모니터+결과) | ⏳ P2 이후 |
| 매핑표(long CSV)→정의 생성 | (보조, 후순위) |

---

> 본 규격은 회의 확정 사항(DB접속 공통·디렉토리 config·expected 명시·SAM은 파일출력만·출력단위 집계)을
> 정본화한 것이다. 변경 시 이 파일과 D-033을 함께 갱신한다.
