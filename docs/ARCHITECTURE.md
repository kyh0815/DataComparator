# ARCHITECTURE.md

> 시스템 구조와 모듈 책임. 코드 짜기 전에 반드시 이해할 것.

---

## 1. 가장 중요한 원칙: 2층 분리

```
┌─────────────────────────────────────────┐
│ Interface Layer                         │
│   ├─ CLI  (이번 프로토에서 만듦)         │
│   └─ GUI  (추후 같은 Core 위에 추가)     │
└─────────────────────────────────────────┘
              ↑ 호출
┌─────────────────────────────────────────┐
│ Core Layer                              │
│   비교 엔진, 배치 호출, 리포트 생성       │
│   인터페이스 무관. print() 금지.          │
│   구조화된 객체를 반환.                   │
└─────────────────────────────────────────┘
              ↓ 호출
┌─────────────────────────────────────────┐
│ Infrastructure                          │
│   PostgreSQL, 파일시스템, stub 배치       │
└─────────────────────────────────────────┘
```

**이유**: GUI를 향후 같은 Core 위에 얹기 위해. Core가 CLI 출력 코드와 섞이면 GUI 추가 시 재작업이 발생함.

---

## 2. 데이터 흐름 (E2E)

```
[입력]
  asis/input/*.csv      ─ As-Is 입력 CSV (Shift-JIS)
  asis/output/*.csv     ─ As-Is 출력 CSV (Shift-JIS, 정답지)
        │
        ▼
[1. Loader]
  As-Is 입력 CSV를 PostgreSQL 테이블에 적재
        │
        ▼
[2. Runner]
  Stub Batch 실행 (셸 단위, 1개씩 순차)
  → 배치가 DB를 읽고 to-be/output/*.csv 생성
        │
        ▼
[3. Comparator]
  asis/output/N.csv  vs  to-be/output/N.csv
  통짜 바이트 비교 → ComparisonResult 객체
        │
        ▼
[4. Reporter]
  ComparisonResult 리스트 → 요약 + CSV 리포트
        │
        ▼
[5. CLI Output]
  진행 상황·요약을 터미널에 출력 + report.csv 경로 안내
```

---

## 3. 폴더 구조 (제안)

```
project_root/
├── README.md               ← (루트) 빠른 시작 안내
├── docs/                   ← 설계·맥락 문서
│   ├── CLAUDE.md
│   ├── CONTEXT.md
│   ├── ARCHITECTURE.md     ← 지금 이 파일
│   ├── SPEC.md
│   ├── TASKS.md
│   └── DECISIONS.md
│
├── src/
│   ├── core/               ← Core Layer (Interface 무관)
│   │   ├── __init__.py
│   │   ├── models.py       ← dataclass 정의 (ComparisonResult 등)
│   │   ├── loader.py       ← CSV → PostgreSQL 적재
│   │   ├── runner.py       ← 배치 호출
│   │   ├── comparator.py   ← 바이트 비교
│   │   └── reporter.py     ← 결과 → 리포트 객체
│   │
│   ├── cli/                ← Interface Layer (CLI)
│   │   ├── __init__.py
│   │   ├── main.py         ← entry point
│   │   └── output.py       ← 터미널 출력 (색깔, 진행바 등)
│   │
│   └── config/             ← 설정 처리
│       ├── __init__.py
│       └── settings.py     ← config 파일 로드, default 값
│
├── stub_batch/             ← 가짜 배치 (시연용)
│   └── run_batch.py        ← stub: input 받아 output 만드는 가짜 로직
│
├── samples/                ← 시연용 샘플 데이터
│   ├── asis/
│   │   ├── input/
│   │   │   ├── 001.csv
│   │   │   └── ...
│   │   └── output/
│   │       ├── 001.csv
│   │       └── ...
│   └── expected_to_be/     ← (참고용) stub이 만들 것으로 기대되는 결과
│
├── tests/
│   ├── test_comparator.py
│   ├── test_loader.py
│   └── ...
│
├── config.yaml             ← 실행 설정 (인코딩, DB 접속, 경로 등)
├── pyproject.toml          ← 또는 requirements.txt
└── README.md
```

---

## 4. Core Layer 모듈 책임

### 4-1. `core/models.py`

모든 데이터 구조를 한 곳에 모음. 인터페이스 간 *공통 어휘*.

```python
@dataclass
class ShellPair:
    """비교 단위. As-Is 출력 파일과 To-Be 출력 파일의 한 쌍."""
    shell_id: str            # 예: "001"
    asis_output_path: Path
    tobe_output_path: Path

@dataclass
class DiffLine:
    """한 줄 차이의 상세."""
    line_number: int
    asis_content: str
    tobe_content: str

@dataclass
class ComparisonResult:
    """한 셸의 비교 결과."""
    shell_id: str
    status: Literal["OK", "NG", "MISSING_ASIS", "MISSING_TOBE", "ERROR"]
    diff_lines: list[DiffLine]  # status가 NG일 때만 채워짐
    error_message: str | None = None

@dataclass
class RunSummary:
    """전체 실행의 요약."""
    total: int
    ok_count: int
    ng_count: int
    error_count: int
    results: list[ComparisonResult]
    report_csv_path: Path
```

### 4-2. `core/loader.py`

- **책임**: As-Is 입력 CSV → PostgreSQL 테이블 적재
- **인터페이스**:
  ```python
  def load_input_csv(csv_path: Path, table_name: str, conn) -> None
  ```
- **금지**: print, CLI 출력. 예외는 발생시키고 상위에서 처리.

### 4-3. `core/runner.py`

- **책임**: stub 배치 실행 → To-Be 출력 CSV 생성
- **인터페이스**:
  ```python
  def run_batch(shell_id: str, conn, output_dir: Path) -> Path
  # 반환: 생성된 to-be 출력 CSV 경로
  ```
- **stub 구현**: 일단은 DB에서 input을 읽어 단순 변환 후 output 생성.
  - 시연용으로 일부 케이스에서 *의도적으로 다른 결과* 생성(NG 시연).
- **인수인계 시 교체 포인트**: 이 함수의 내부를 진짜 Net COBOL 배치 호출로 교체.

### 4-4. `core/comparator.py`

- **책임**: 두 CSV 파일을 바이트 단위로 비교, 차이를 줄 단위로 정리.
- **인터페이스**:
  ```python
  def compare_files(asis_path: Path, tobe_path: Path) -> ComparisonResult
  ```
- **구현**: 통짜 바이트 비교. 다르면 줄 단위로 diff 추출 (Python `difflib` 활용 가능).
- **금지**: LLM 호출, 추측. 결정론적이어야 함.

### 4-5. `core/reporter.py`

- **책임**: `list[ComparisonResult]` → CSV 리포트 파일 생성 + `RunSummary` 객체.
- **인터페이스**:
  ```python
  def generate_report(results: list[ComparisonResult], output_path: Path) -> RunSummary
  ```
- **CSV 컬럼**:
  `shell_id, status, diff_line_count, first_diff_line, first_diff_asis, first_diff_tobe`

### 4-6. `core/__init__.py`

오케스트레이션 함수 노출. Interface가 이걸 호출.

```python
def run_full_comparison(config: Config) -> RunSummary:
    """E2E 전체 실행. CLI/GUI 모두 이 함수를 호출."""
    # 1. 설정 로드
    # 2. shell pair 목록 결정
    # 3. 각 셸에 대해 loader → runner → comparator
    # 4. reporter
    # 5. RunSummary 반환
```

---

## 5. Interface Layer (CLI)

### 5-1. `cli/main.py`

- argparse로 인자 파싱
- config 로드
- `core.run_full_comparison(config)` 호출
- 진행 콜백을 통해 `cli/output.py`로 출력

### 5-2. `cli/output.py`

- 색깔 (ANSI), 진행 표시, 요약 출력 담당
- Core의 결과 객체를 받아 *예쁘게* 출력만 함

### 5-3. 진행 보고 패턴

Core가 진행 상황을 CLI에 알리는 방법. 두 가지 옵션:

- **(A) 콜백**: `run_full_comparison(config, on_progress=callback)`
- **(B) 이벤트 generator**: `for event in run_full_comparison(config): ...`

> **선택: (A) 콜백.** 단순하고 GUI에도 자연스럽게 이식 가능.

---

## 6. 설정 (config.yaml 예시)

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
  password_env: POSTGRES_PASSWORD   # 환경변수에서 읽음

batch:
  type: stub      # 'stub' | 'netcobol' (추후 확장)
  stub_path: ./stub_batch/run_batch.py

shells:
  range: [1, 10]  # 또는 ids: ["001", "002", ...]
```

---

## 7. 의존성 (최소)

- `python >= 3.10`
- `psycopg2-binary` 또는 `psycopg[binary]` — PostgreSQL
- `pyyaml` — config
- `pytest` — 테스트
- `black` — 포맷터

> 무거운 프레임워크 금지. Flask/Django/FastAPI 등은 GUI 단계에서 결정.

---

## 8. 인수인계 시 교체 포인트 (정직원이 바꿀 곳)

명시적으로 표시해 둬야 할 곳:

1. **`core/runner.py`**: stub 배치 → 진짜 Net COBOL 배치 호출
2. **`config.yaml`**: 환경별 값 (인코딩, OS, DB 접속, 경로)
3. **GUI 추가**: `src/gui/` 디렉토리로 별도 추가 (Core 그대로 재사용)

각 교체 포인트에는 코드 상단에 명시적 주석을 둘 것:

```python
# === 인수인계 시 교체 포인트 ===
# stub 배치를 실제 Net COBOL 배치 호출로 교체해야 함.
# 인터페이스 (입력/출력 시그니처)는 유지.
```

---

## 9. 테스트 전략 (프로토 수준)

- **Core 단위**: comparator, loader, reporter 각각에 대해 핵심 케이스
- **E2E smoke**: 샘플 1~3개를 넣어 전체 흐름이 도는지
- **NG 분류 케이스**: 의도적으로 다른 CSV 쌍을 만들어 NG 검출 확인

UI/시각 측면 테스트는 불요 (CLI 출력은 사람이 보고 확인).
