# SPEC.md

> 무엇을 만드는지에 대한 명세. 동작·입출력 계약.

---

## 1. CLI 사용 인터페이스

### 1-1. 기본 실행

```bash
python -m src.cli.main --config ./config.yaml
```

### 1-2. 선택적 인자

```bash
python -m src.cli.main \
  --config ./config.yaml \
  --shells 1-10            # 또는 --shells 001,002,005
  --report-dir ./out/reports \
  --verbose
```

| 인자 | 의미 | 기본값 |
|---|---|---|
| `--config` | 설정 파일 경로 | `./config.yaml` |
| `--shells` | 실행할 셸 범위 또는 ID | config에 정의된 값 |
| `--report-dir` | 리포트 출력 디렉토리 | config의 값 |
| `--verbose` | 상세 로그 출력 | False |

---

## 2. 입력

### 2-1. As-Is CSV 파일들

```
samples/asis/input/
  001.csv
  002.csv
  ...
  010.csv

samples/asis/output/
  001.csv   ← 정답지
  002.csv
  ...
  010.csv
```

### 2-2. 명명 규칙

- **반드시 동일한 파일명**으로 짝지어짐 (`input/001.csv` ↔ `output/001.csv`).
- 짝이 없는 파일은 NG 처리 (status: `MISSING_*`).

### 2-3. 인코딩

- **양쪽 모두 Shift-JIS**.
- 설정으로 변경 가능 (단, 이번 프로토는 Shift-JIS 고정 동작).

### 2-4. 파일 형식

- CSV (콤마 구분).
- 줄바꿈은 `\r\n` 또는 `\n` 모두 허용. 비교 시에는 *그대로 바이트 비교*. (필요 시 정규화는 향후 결정.)

---

## 3. 처리 동작

### 3-1. 셸 단위 처리

각 셸 ID(예: `001`)에 대해 다음 순서로 처리. **셸 1개씩 순차 진행**. 셸의 `input_type`(정의 파일에서 결정, 7-2)에 따라 1번 Load 단계가 분기한다.

1. **Load** (`input_type`에 따라 분기):
   - `database`: `asis/input/{N}.csv`를 PostgreSQL 테이블(`input_table`)에 적재(`load_input_csv()`).
   - `file`: `asis/input/{N}.csv`를 `tobe_input_dir`에 바이트 복사(`copy_input_file()`) — 야간 배치 입력 시뮬.
2. **Run**: 정의 파일의 `execution.shell_program`(stub)을 셸 ID와 함께 실행. 입력은 DB(`transaction_log`) 또는 복사된 raw 파일에서 읽는다.
3. **Download** (`output_type`에 따라 분기, Boss 명시 단계):
   - `file`: 배치가 이미 `tobe_output_dir/{N}.csv`를 직접 생성 → 그대로 사용.
   - `database`: 배치가 결과 테이블(`tobe_result`)에 INSERT → `export_table_to_csv()`로 `tobe_output_dir/{N}.csv`로 다운로드.
4. **Compare**: `asis/output/{N}.csv`와 `tobe_output_dir/{N}.csv`를 바이트 비교.
5. 결과를 `ComparisonResult`로 저장.

한 셸에서 예외가 발생해도 다음 셸 진행. 단, 예외는 결과의 `status: ERROR`로 기록.

### 3-2. 비교 로직

- **통짜 바이트 비교**가 1차 판정.
- 완전 일치 → `OK`.
- 다르면 → `NG`. 차이의 *어디*를 찾기 위해 줄 단위 diff 수행.
- 줄 단위 diff는 Python `difflib.unified_diff` 또는 동등한 방식 사용.
- 출력 줄 길이가 다르면 짧은 쪽에 빈 값을 채워서라도 행 단위 대응 표시.

### 3-3. 짝짓기 누락 처리

- `asis/output/N.csv`만 있고 `tobe_output/N.csv`가 없으면 → `MISSING_TOBE`.
- 그 반대 → `MISSING_ASIS`.
- 둘 다 없으면 → 해당 셸은 처리 목록에서 제외.

---

## 4. 출력 (Core 반환값)

### 4-1. `RunSummary` 객체

```python
RunSummary(
  total=10,
  ok_count=6,
  ng_count=2,
  error_count=1,
  missing_count=1,
  results=[ComparisonResult, ...],
  report_csv_path=Path("./out/reports/report_20250515_103000.csv")
)
```

### 4-2. CSV 리포트 형식

파일명: `report_{YYYYMMDD_HHMMSS}.csv`
인코딩: UTF-8 (BOM 포함, Excel 호환 위해)

| 컬럼 | 의미 |
|---|---|
| `shell_id` | 셸 ID (예: 001) |
| `status` | OK / NG / MISSING_ASIS / MISSING_TOBE / ERROR |
| `diff_line_count` | 다른 줄 수 (NG일 때만) |
| `first_diff_line` | 첫 차이 줄 번호 |
| `first_diff_asis` | 첫 차이 줄의 As-Is 내용 |
| `first_diff_tobe` | 첫 차이 줄의 To-Be 내용 |
| `error_message` | ERROR일 때만 |

상세 diff(여러 줄)는 별도 파일 `report_{...}_details/{shell_id}.diff`로 저장.
상세 디렉토리는 **CSV와 동일한 타임스탬프를 공유**하여 실행마다 분리된다 (D-017).
NG가 하나도 없으면 상세 디렉토리는 생성되지 않는다.

---

## 5. CLI 출력 (사람이 볼 화면)

### 5-1. 진행 표시

```
[1/10] 001번 셸 처리 중...
       ▸ 입력 적재 → OK
       ▸ 배치 실행 → OK
       ▸ 결과 비교 → OK ✓

[2/10] 002번 셸 처리 중...
       ▸ 입력 적재 → OK
       ▸ 배치 실행 → OK
       ▸ 결과 비교 → NG ✗   (3개 줄 차이)
       └─ 첫 차이: 12행
          As-Is: 東京都千代田区...
          To-Be: 東京都 千代田区...

[3/10] ...
```

색깔:
- `OK` / `✓` → 초록
- `NG` / `✗` → 빨강
- `ERROR` → 노랑
- 일반 진행 → 기본

### 5-2. 최종 요약

```
═══════════════════════════════════════════
  완료: 총 10건 / OK 6 / NG 3 / ERROR 1 / MISSING 0
  소요: 12.4초
  리포트: ./out/reports/report_20250515_103000.csv
═══════════════════════════════════════════
```

### 5-3. `--verbose` 모드

추가로:
- SQL 적재 쿼리 로그
- 배치 stdout/stderr
- diff 상세 (모든 차이 줄)

---

## 6. stub 배치의 동작 (시연용)

stub 배치는 진짜 Net COBOL 배치를 *흉내내는* 가짜다. **입력 흐름이 2가지**이므로 stub도 2종으로 나눈다(D-021). 각 셸이 어느 stub·어느 입력을 쓰는지는 정의 파일 `test_definition.yaml`(7-2)이 결정한다.

| stub 파일 | 입력 흐름 | 담당 셸 | 도메인 |
|---|---|---|---|
| `stub_batch/run_batch_db.py` | DB 입력 | 001~005 | 결제 |
| `stub_batch/run_batch_file.py` | 파일 입력(야간 배치 시뮬) | 006~010 | 야간 배치 |

**출력 유형도 2가지**(D-022). 각 stub은 `--output-type file|database`로 출력 방식을 받는다.
- `file`: stub이 `tobe_output_dir/{N}.csv`를 직접 생성.
- `database`: stub이 결과 테이블 `tobe_result`에 INSERT → 오케스트레이터가 `export_table_to_csv()`로 CSV 다운로드(Boss "출력 데이터 다운로드" 단계).

입력2 × 출력2 = **4사분면을 10셸로 전부 시연**한다(SPEC 6-5 표).

### 6-1. DB 입력 흐름 (`run_batch_db.py`, 셸 001~005)

- As-Is 입력 CSV는 오케스트레이터가 `load_input_csv()`로 **`transaction_log` 테이블에 적재**(TRUNCATE→INSERT).
- stub이 `transaction_log`(방금 적재된 입력)를 SELECT하고 `customer_master`(시드)를 `customer_id`로 **조인해 顧客名 enrich**.
- 결과를 `取引明細レポート`로 `tobe_output_dir/{shell_id}.csv`에 출력. **Shift-JIS**, 줄바꿈 `\n`, tx_id 정렬.

### 6-2. 파일 입력 흐름 (`run_batch_file.py`, 셸 006~010) — 야간 배치 시뮬

- As-Is 입력 CSV를 오케스트레이터가 `copy_input_file()`로 **`tobe_input_dir`에 바이트 복사**.
- stub이 *그 raw 파일을 직접 read* + `customer_master`(시드) DB SELECT로 마스터 조인 → 출력 CSV 생성.
- 야간 배치의 전형적 흐름(전날 raw 거래 파일 → 마스터 조인 → 일일 명세 파일)을 시뮬. 출력 포맷은 6-1과 동일 구조(입력 *방식*의 다양성을 시연하는 것이 목적).

### 6-3. 출력 컬럼 (양 흐름·양 출력유형 공통)

헤더는 **ASCII**, *값*은 일본어(顧客名·摘要 등) — Shift-JIS 인코딩. 헤더를 ASCII로 두어 exporter가 결과 테이블(`tobe_result`) 컬럼명을 그대로 헤더로 쓰는 제네릭 동작과 byte 일관성을 보장한다.

`tx_id, customer_id, customer_name, tx_date, tx_type, amount, balance_after, memo` (tx_id 정렬). `customer_name`은 `customer_master` 조인값(없으면 빈칸), `memo` 빈값은 빈칸.

### 6-4. 골든 생성 모드 (`--clean`)

- 두 stub 모두 `--clean` 플래그 지원: **NG 주입을 끈 정상 출력**을 생성한다.
- T4-1에서 골든(As-Is 출력)을 `--clean`으로 생성하면 정상 셸은 바이트 동일(OK), NG 셸은 stub의 주입분만큼만 차이가 나도록 보장된다.

### 6-5. 의도된 NG/ERROR 시연

NG/ERROR는 **야간 배치 흐름(파일 입력)에 모은다** — 사장님이 핵심으로 언급한 워크로드에서 검출이 일어나는 것이 시연 임팩트가 크다(D-021). 출력 유형은 4사분면을 모두 덮도록 분배한다(D-022).

| 셸 ID | 입력→출력 | 판정 | 시연 의도 |
|---|---|---|---|
| 001 | DB→DB | OK | 결제, 출력 DB(export 경로) |
| 002 | DB→file | OK | 결제, 출력 파일 |
| 003 | DB→DB | OK | 결제, 출력 DB(export) |
| 004 | DB→file | OK | 결제, 출력 파일 |
| 005 | DB→DB | OK | 결제, 출력 DB(export) |
| 006 | file→file | OK | 야간 배치 정상 |
| 007 | file→file | NG | 한 줄 데이터 차이 (`取引後残高` 1자리 변경) |
| 008 | file→**DB** | NG | 전각 공백 삽입 (`顧客名` 田中太郎→田中　太郎) — **export 경로에서도 NG 검출** 시연 |
| 009 | file→file | NG | 여러 줄 차이 (3개 행 변경) |
| 010 | file→(실패) | ERROR | stub 종료 코드 1 (출력 없음) |

4사분면 커버: DB→DB(001,003,005) · DB→file(002,004) · file→file(006,007,009) · file→DB(008).
NG 주입은 순수 함수 `_apply_ng_pattern(shell_id, rows)`로 분리해 *위치 기반·결정론적*으로 구현한다(DB 없이 단위 테스트 가능).

---

## 7. 설정 파일 (`config.yaml`)

`config.yaml`은 *환경 설정*(인코딩·경로·DB 접속·출력 옵션)을 담고, *셸별 메타데이터*는 별도 정의 파일 `test_definition.yaml`(7-2)로 분리한다(D-021).

```yaml
encoding: Shift_JIS

paths:
  asis_input_dir: ./samples/asis/input
  asis_output_dir: ./samples/asis/output
  tobe_input_dir: ./out/tobe_input      # 파일 입력(야간 배치) raw 복사 대상 (D-021)
  tobe_output_dir: ./out/tobe_output
  report_dir: ./out/reports
  definition_file: ./test_definition.yaml  # 셸별 정의 파일 (D-021)

database:
  host: localhost
  port: 5432
  dbname: compare_proto
  user: postgres
  password_env: POSTGRES_PASSWORD

batch:
  type: stub
  stub_dir: ./stub_batch          # 셸별 실제 stub(run_batch_db/file)은 정의 파일 batch 필드로 선택
  timeout_seconds: 60

shells:
  range: [1, 10]    # 정의 파일이 없을 때의 폴백. 정의 파일이 있으면 그쪽 셸 목록이 우선.
  # 또는 ids: ["001", "003", "007"]

output:
  cli_color: true
  cli_verbose: false
  report_with_bom: true
```

---

## 7-2. 정의 파일 (`test_definition.yaml`)

테스트별 메타데이터(입력·실행·출력·비교)를 코드에서 분리한다. **Boss 기획서 7.1절 구조에 맞춘 경량 버전**(D-022) — 구조·필드명을 맞춰 인수 시 풀스키마 전환이 매끄럽게. 입력·출력 각각 `type: database|file`로 두 흐름을 데이터 주도로 라우팅한다.

```yaml
tests:
  - test_id: "001"
    test_name: "결제 - 거래명세 (DB입력/DB출력)"
    input:
      type: database              # database | file
      table: transaction_log      # type==database: 적재 대상 테이블
      csv: 001.csv                # asis_input_dir 기준 입력 CSV
    execution:
      shell_program: stub_batch/run_batch_db.py   # 기동할 (시연) shell/배치
      timeout: 60
    output:
      type: database              # database | file
      table: tobe_result          # type==database: 배치가 쓰는 결과 테이블(=export 대상)
      export_csv: 001.csv         # tobe_output_dir 기준 다운로드 파일명
    expected_output_csv: 001.csv  # asis_output_dir 기준 정답지
    comparison_rules: { type: byte_exact }          # 프로토: 바이트 비교 (D-004)
    success_criteria: { pass_condition: all_exact_match }

  - test_id: "002"
    test_name: "결제 - 거래명세 (DB입력/파일출력)"
    input:   { type: database, table: transaction_log, csv: 002.csv }
    execution: { shell_program: stub_batch/run_batch_db.py, timeout: 60 }
    output:  { type: file, file: 002.csv }          # type==file: 배치가 직접 생성하는 파일명
    expected_output_csv: 002.csv
    comparison_rules: { type: byte_exact }
    success_criteria: { pass_condition: all_exact_match }

  - test_id: "008"
    test_name: "야간배치 - 일일명세 (파일입력/DB출력, NG시연)"
    input:   { type: file, dest_dir: ./out/tobe_input/, csv: 008.csv }
    execution: { shell_program: stub_batch/run_batch_file.py, timeout: 60 }
    output:  { type: database, table: tobe_result, export_csv: 008.csv }
    expected_output_csv: 008.csv
    comparison_rules: { type: byte_exact }
    success_criteria: { pass_condition: all_exact_match }
  # ... 003~007, 009, 010 동일 구조 (SPEC 6-5의 입력→출력 매핑대로)
```

설계 원칙:
- Boss 7.1 구조(`test_id/input/execution/output/comparison_rules/success_criteria`)를 따르되 값은 *경량*으로 채움.
- 프로토 미사용 필드(`comparison_rules` 세부, `success_criteria` 다양화, `parameters`, `key_columns` 등 풀스키마)는 *자리만 비워둠*, 인수 후 단계(D-022).
- `test_id`는 3자리 zero-pad 문자열(D-019 4항과 일관).

---

## 8. 예외 처리 정책

| 상황 | 동작 |
|---|---|
| 설정 파일 없음 | 즉시 종료, 에러 메시지 |
| DB 접속 실패 | 즉시 종료, 에러 메시지 |
| 한 셸의 입력 적재 실패 | 해당 셸 ERROR, 다음 셸 진행 |
| 한 셸의 배치 실행 실패 | 해당 셸 ERROR, 다음 셸 진행 |
| 한 셸의 비교 중 예외 | 해당 셸 ERROR, 다음 셸 진행 |
| 짝이 없는 파일 | MISSING_* status |

ERROR도 결과 리포트에 포함되어야 함. 사람이 보고 원인 파악 가능하도록 `error_message` 채울 것.

---

## 9. 비기능 요구

- 셸 10개 처리에 30초 이내 (시연 시 답답하지 않도록).
- CLI 출력은 *실시간으로* 흐름 (배치 처리 완료 후 한꺼번에 출력 X).
- 색깔이 안 되는 터미널에서도 동작 (NO_COLOR 환경변수 존중).
