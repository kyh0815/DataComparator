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

각 셸 ID(예: `001`)에 대해 다음 순서로 처리. **셸 1개씩 순차 진행**.

1. **Load**: `asis/input/{N}.csv`를 PostgreSQL의 정해진 테이블에 적재.
2. **Run**: stub 배치(`stub_batch/run_batch.py`)에 셸 ID를 전달해 실행.
   - 배치는 DB에서 input을 읽고 `tobe_output_dir/{N}.csv` 생성.
3. **Compare**: `asis/output/{N}.csv`와 `tobe_output_dir/{N}.csv`를 바이트 비교.
4. 결과를 `ComparisonResult`로 저장.

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

`stub_batch/run_batch.py`는 진짜 Net COBOL 배치를 *흉내내는* 가짜.

### 6-1. 기본 동작

- DB에서 input 데이터를 SELECT
- 단순 변환 로직 (예: 일부 컬럼 그대로, 일부 컬럼 단순 계산) 적용
- 결과를 `tobe_output_dir/{shell_id}.csv`로 출력
- Shift-JIS로 인코딩

### 6-2. 의도된 NG 시연

시연 임팩트를 위해 일부 셸 ID에서는 **의도적으로 다른 결과** 생성:

| 셸 ID | 시연 의도 |
|---|---|
| 001~006 | 정상 일치 (OK 시연) |
| 007 | 한 줄에서 데이터 차이 (NG: 명백한 차이) |
| 008 | 공백/포맷 차이 (NG: 가짜처럼 보이는 NG) |
| 009 | 여러 줄 차이 |
| 010 | 배치 실패 → ERROR |

이렇게 *시연 시나리오*가 미리 짜여 있어야 사장님 앞에서 자연스럽게 흘러감.

---

## 7. 설정 파일 (`config.yaml`)

```yaml
encoding: Shift_JIS

paths:
  asis_input_dir: ./samples/asis/input
  asis_output_dir: ./samples/asis/output
  tobe_output_dir: ./out/tobe_output
  report_dir: ./out/reports

database:
  host: localhost
  port: 5432
  dbname: compare_proto
  user: postgres
  password_env: POSTGRES_PASSWORD

batch:
  type: stub
  stub_path: ./stub_batch/run_batch.py
  timeout_seconds: 60

shells:
  range: [1, 10]
  # 또는 ids: ["001", "003", "007"]

output:
  cli_color: true
  cli_verbose: false
  report_with_bom: true
```

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
