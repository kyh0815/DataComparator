# TASKS.md

> 개발 작업을 Task 단위로 분할. **한 번에 하나씩만** 작업한다.
> 각 Task의 완료 기준(DoD)을 모두 만족할 때까지 다음 Task로 넘어가지 않는다.

---

## 작업 진행 표기

- `[ ]` 미착수
- `[~]` 진행 중
- `[x]` 완료

---

## Phase 0. 프로젝트 준비

### T0-1. 프로젝트 골격 생성 `[x]`

**목적**: 디렉토리 구조와 빈 모듈을 만들어 *컴파일 가능한 빈 껍데기* 확보.

**작업**:
- `ARCHITECTURE.md`의 폴더 구조대로 디렉토리·`__init__.py` 생성
- `pyproject.toml` 또는 `requirements.txt` 작성 (의존성: psycopg2-binary, pyyaml, pytest, black)
- `.gitignore` (`out/`, `__pycache__/`, `.venv/`, 비밀 등)
- `README.md` 초안 (실행 방법, 의존 설치 방법만)

**완료 기준**:
- `python -m src.cli.main --help` 가 (빈 파서라도) 동작
- `pytest` 실행 시 0 passed 로 정상 종료

**의존**: 없음.

---

### T0-2. 데이터 모델 정의 `[x]`

**목적**: Core 전체에서 공유할 dataclass들을 먼저 못박음. 이후 모든 Task가 이 모델을 import.

**작업**:
- `src/core/models.py`에 정의:
  - `ShellPair`
  - `DiffLine`
  - `ComparisonResult` (status enum 포함)
  - `RunSummary`
  - `Config` (설정 객체)
- 각 dataclass에 한국어 docstring

**완료 기준**:
- 모든 모델 import 가능
- 모델만 사용하는 단위 테스트 1~2개 통과 (생성/필드 접근)

**의존**: T0-1.

---

### T0-3. 설정 로더 `[x]`

**목적**: `config.yaml`을 읽어 `Config` 객체로 변환.

**작업**:
- `src/config/settings.py`
  - `load_config(path: Path) -> Config`
  - 환경변수에서 DB 비밀번호 읽기 (`password_env` 키)
  - 기본값 처리 (Shift_JIS, range [1,10] 등)
- `config.yaml.example` 작성

**완료 기준**:
- 예시 yaml을 로드해서 Config 객체로 변환 성공
- 필수 키 누락 시 명확한 에러
- 단위 테스트 (정상·이상 케이스)

**의존**: T0-2.

> 추가(D-021): T2-3에서 Config에 `definition_file`·`tobe_input_dir` 경로를 더한다(미세 수정, config 디렉토리 기준 절대경로화). 정의 파일 파서는 `src/config`에 둔다.

---

## Phase 1. 핵심 비교 엔진 (Core)

### T1-1. Comparator 구현 `[x]`

**목적**: 두 파일을 받아 `ComparisonResult` 반환. **이 도구의 심장.**

**작업**:
- `src/core/comparator.py`
  - `compare_files(asis_path: Path, tobe_path: Path) -> ComparisonResult`
  - 통짜 바이트 비교로 일치 여부 판정
  - 불일치 시 줄 단위 diff 추출 → `DiffLine` 리스트
  - 짝 누락 처리 (`MISSING_ASIS` / `MISSING_TOBE`)
- 인코딩은 *바이트 비교*이므로 디코드하지 않음. 단, 줄 분할 시 `\n` 기준.

**완료 기준**:
- 다음 테스트 케이스 통과:
  - 동일 파일 → OK
  - 한 줄 다름 → NG, diff_lines 1개
  - 여러 줄 다름 → NG, diff_lines N개
  - 한쪽만 존재 → MISSING_*
  - 빈 파일 vs 빈 파일 → OK
  - 빈 파일 vs 한 줄 → NG
- **`print()` 호출 없음**. 결과는 객체 반환만.

**의존**: T0-2.

> 이 Task는 **다른 Task가 없어도 단독으로 테스트 가능**. Claude Code가 가장 먼저 깊게 만들 가치가 있는 부분.

---

### T1-2. Reporter 구현 `[x]`

**목적**: `list[ComparisonResult]` → CSV 파일 + `RunSummary`.

**작업**:
- `src/core/reporter.py`
  - `generate_report(results, output_dir: Path) -> RunSummary`
  - CSV 파일 생성 (UTF-8 BOM 포함, Excel 호환)
  - 상세 diff는 별도 파일 (`{shell_id}.diff`)
  - 파일명에 타임스탬프

**완료 기준**:
- OK·NG·ERROR·MISSING이 섞인 결과 리스트로 호출 시 CSV가 정확히 생성됨
- CSV를 Excel에서 깨지지 않고 열림 (BOM 확인)
- `RunSummary`의 카운트가 정확함
- 단위 테스트

**의존**: T0-2, T1-1.

---

## Phase 2. 인프라 연동

### T2-1. PostgreSQL 환경 구축 가이드 `[x]`

**목적**: 우분투에서 PostgreSQL을 깔고 실행 가능 상태로 만드는 방법을 README에 정리.

**작업**:
- `SETUP.md` 작성
  - 우분투에 PostgreSQL 설치 명령
  - 데이터베이스·사용자 생성
  - 환경변수로 비밀번호 설정
  - 동작 확인 (`psql -h ... `)
- 스키마 SQL 파일 작성 (`schema.sql`)
  - 적재용 테이블 정의 (`input_data` 등 단순 구조)

**완료 기준**:
- 깨끗한 우분투에서 SETUP.md만 따라 했을 때 PostgreSQL 동작 + 스키마 생성 완료

**의존**: 없음 (병렬 가능).

---

### T2-2. Loader 구현 `[x]`

**목적**: As-Is 입력 CSV → PostgreSQL 테이블 적재.

**작업**:
- `src/core/loader.py`
  - `load_input_csv(csv_path: Path, shell_id: str, conn) -> None`
  - psycopg2의 `copy_from` 또는 `executemany` 사용
  - 같은 shell_id로 재실행 시 기존 데이터 처리 정책 정의 (TRUNCATE 후 INSERT 권장)
- 실패 시 적절한 예외 발생.

**완료 기준**:
- 샘플 CSV 1개를 적재 → DB에서 SELECT로 동일 데이터 조회 확인
- 적재 실패 케이스 (잘못된 CSV, DB 단절) 테스트

**의존**: T0-3, T2-1.

---

### T2-3. Stub 배치 작성 `[x]`

**목적**: 진짜 Net COBOL 배치 대신 시연용 가짜 배치. **입력 2종(DB/파일) × 출력 2종(DB/파일) = 4사분면**과 **정의 파일 라우팅**을 시연 (D-021·D-022 / `docs/T2-3_alignment.md`·`docs/AlignmentCheck/` 반영).

**작업**:
- `test_definition.yaml` 작성 (테스트 10건, SPEC 7-2 Boss 구조). 입력→출력 매핑은 SPEC 6-5표(001 DB→DB … 008 file→DB … 010 ERROR).
- `db/schema.sql`에 결과 테이블 `tobe_result` 추가 (DB 출력 셸이 INSERT, TRUNCATE per shell, PK·NOT NULL만 — D-022).
- `stub_batch/run_batch_db.py` — DB 입력 흐름 (셸 001~005)
  - 인자: `--shell-id --output-path --output-type {file|database} --input-table --encoding --db-*` + `POSTGRES_PASSWORD` env, `--clean`
  - `transaction_log` SELECT + `customer_master` 조인 → 取引明細レポート. 출력: file이면 CSV 직접, database면 `tobe_result` INSERT.
- `stub_batch/run_batch_file.py` — 파일 입력 흐름 = 야간 배치 시뮬 (셸 006~010)
  - 인자: `--shell-id --output-path --output-type --input-file --encoding --db-*` + env, `--clean`
  - 복사된 raw 파일 read + `customer_master` 조인 → 동일 출력 분기.
- `src/core/loader.py`에 `copy_input_file(csv_path, dest_dir) -> Path` 추가 (파일 입력용 바이트 복사).
- `src/core/exporter.py` 신규: `export_table_to_csv(conn, table_name, output_path, encoding, columns=None) -> Path` (DB 출력 다운로드, 결정론적·바이트비교 호환 — D-022).
- `src/config`에 정의 파일 파서(Boss 구조 → `ShellDefinition` 등) + Config에 `definition_file`·`tobe_input_dir` 추가.
- `run.sh` — 얇은 CLI 기동 래퍼 (Boss "Shell로 기동" 충족, D-022). *(엔트리 완성은 T3-3과 함께여도 됨 — 최소 자리 확보.)*
- **시연용 NG 패턴** (SPEC 6-5): 007 한 줄 값 / 008 전각 공백(顧客名, file→DB export 경로) / 009 여러 줄 / 010 종료코드 1
  - 순수 함수 `_apply_ng_pattern(shell_id, rows)`로 분리 (위치 기반·결정론적, DB 없이 테스트).
- 각 stub 최상단에 교체 포인트 주석 강화 (`--shell-id/--output-path/입출력 종류` 계약 유지).

**완료 기준**:
- 두 stub 모두 단독 실행 가능, `--output-type` file/database 양쪽 동작, `--clean` 모드 동작.
- DB 출력 셸: stub→`tobe_result` INSERT → `export_table_to_csv()`→CSV→비교가 E2E로 도는지 확인.
- 4사분면(DB→DB, DB→file, file→DB, file→file) 전부 정상 + NG/ERROR가 SPEC 6-5대로 동작.
- 순수 NG 주입 로직 단위 테스트(DB 없이 항상 실행) + DB/파일/export 통합 테스트(`RUN_DB_TESTS=1` 조건부).
- D-021·D-022 검증 결과 기록 / 정렬 문서 반영 자체 점검.

**의존**: T2-1, T2-2.

---

### T2-4. Runner 구현 `[x]`

**목적**: Core에서 stub 배치를 호출.

**작업**:
- `src/core/runner.py`
  - `run_batch(shell_id: str, config: Config) -> Path`
  - 정의 파일의 `execution.shell_program`에 따라 호출 stub·인자(`--output-type` 포함) 분기 (D-021·D-022)
  - `subprocess`로 stub 실행, stdout/stderr 캡쳐
  - 종료 코드 0이 아니면 예외 (010 ERROR 시연 경로)
  - `output.type == database`면 stub 실행 후 `exporter.export_table_to_csv()`로 다운로드(Boss 출력 다운로드 단계)
  - 반환: 생성된/다운로드된 To-Be 출력 CSV 경로
- 코드 상단에 교체 포인트 주석.

**완료 기준**:
- 정상 케이스에서 stub 호출 → 출력 CSV 경로 반환
- 비정상 종료 시 명확한 예외
- 단위 테스트 (mock subprocess)

**의존**: T2-3.

---

## Phase 3. 오케스트레이션과 CLI

### T3-1. Core 오케스트레이션 `[x]`

**목적**: E2E 흐름을 묶는 함수. CLI/GUI 공통 진입점.

**작업**:
- `src/core/__init__.py` 또는 `src/core/orchestrator.py`
  - `run_full_comparison(config: Config, on_progress: Callable | None = None) -> RunSummary`
  - 테스트 목록·메타데이터를 **정의 파일(test_definition.yaml)에서 로드** (없으면 config range/ids 폴백, D-021)
  - 각 테스트에 대해 `input.type`에 따라 loader 분기(load_input_csv / copy_input_file) → runner(+`output.type==database`면 exporter 다운로드) → comparator 순서로 호출 (D-022)
  - 각 단계 후 `on_progress` 콜백으로 진행 보고
  - 예외(RunnerError 등) 발생 시 해당 셸은 ERROR로 기록하고 다음 진행
  - **셸 단위 트랜잭션 경계 필수** (D-023 발견): ① DB 입력은 `load_input_csv` 후 **commit**해야 stub(별도 connection)이 본다. ② 출력=database의 exporter read가 남긴 트랜잭션을 **셸 종료 시 commit/rollback**해야 다음 셸 stub의 `TRUNCATE tobe_result`가 막히지 않는다.
  - 최종적으로 reporter 호출 → RunSummary 반환

**완료 기준**:
- 콜백 없이 호출해도 동작
- 콜백을 넘기면 단계별 이벤트 발생 확인
- 일부 셸에서 예외 발생 시 다른 셸은 정상 처리되는지 확인

**의존**: T1-1, T1-2, T2-2, T2-4.

---

### T3-2. CLI 출력 모듈 `[x]`

**목적**: 터미널에 색깔·진행·요약을 예쁘게 출력.

**작업**:
- `src/cli/output.py`
  - 콜백 함수들: 진행 시작, 단계 완료, 셸 완료, 전체 완료
  - ANSI 색깔 (NO_COLOR 환경변수 존중)
  - `--verbose` 시 추가 정보
  - 첫 NG 케이스의 상세를 즉시 표시

**완료 기준**:
- 콜백을 받아 SPEC의 출력 예시와 유사하게 출력
- 색깔이 안 되는 환경에서도 깨지지 않음

**의존**: T0-2.

---

### T3-3. CLI Entry Point `[x]`

**목적**: 사용자가 실제로 실행하는 진입점.

**작업**:
- `src/cli/main.py`
  - argparse로 인자 파싱
  - config 로드
  - `cli/output.py`의 콜백 준비
  - `core.run_full_comparison(config, on_progress=cb)` 호출
  - 최종 요약 출력
  - 종료 코드: NG/ERROR가 있으면 1, 모두 OK면 0
- `run.sh` — 얇은 Shell 기동 래퍼 완성(Boss "Shell 스크립트로 기동" 기대 충족, D-022). 내부는 `python -m src.cli.main "$@"` 위임.

**완료 기준**:
- `python -m src.cli.main --config config.yaml` 한 줄로 E2E 실행
- 결과가 SPEC 4·5장대로 출력 + CSV 파일 생성
- `--shells`, `--verbose` 인자 동작

**의존**: T3-1, T3-2, T0-3.

---

## Phase 4. 시연 데이터와 마무리

### T4-1. 시연용 샘플 데이터 작성 `[x]`

**목적**: 사장님 시연 시 사용할 1~10번 CSV 쌍(As-Is 입력 + As-Is 출력 정답지) 준비. 이게 갖춰지면 `python -m src.cli.main --config config.yaml` 한 줄로 SPEC 8장 시연 시나리오가 실데이터로 굴러간다(Phase 3 E2E는 이미 동작, 데이터만 비어 있음).

#### 1. As-Is 입력 CSV — `samples/asis/input/001.csv ~ 010.csv`

- **인코딩**: Shift-JIS, 줄바꿈 `\n`. 값에 일본어(거래구분 入金/出金/振込, 적요) 포함.
- **헤더(10개 전부 동일)**: `tx_id,customer_id,tx_date,tx_type,amount,balance_after,branch_code,memo`
  - = `transaction_log` 스키마 8컬럼(D-018). DB 입력(001~005)은 `load_input_csv`가 이 헤더를 테이블 컬럼과 대조하므로 **정확히 일치 필수**(loader가 불일치 시 LoaderError). 파일 입력(006~010)은 stub의 `rows_from_file`가 `DictReader`로 헤더명 매핑(`tx_id,customer_id,tx_date,tx_type,amount,balance_after,memo` 사용, `branch_code`는 무시) — 동일 헤더로 두면 두 흐름이 같은 입력 포맷을 공유해 단순.
- **값 제약**:
  - `customer_id`는 **시드 `customer_master`(C0001~C0020, 田中太郎 등)에 존재하는 값**만 사용 → stub이 顧客名을 조인해 enrich(없으면 빈칸이라 시연 임팩트↓).
  - `amount`/`balance_after`: 정수(엔). `tx_date`: `YYYY-MM-DD`. `tx_type`: 入金/出金/振込. `memo`: 비어도 됨(빈칸→출력서 빈칸).
  - `tx_id`는 셸 내 유일·정렬 가능(출력이 tx_id 정렬이므로). 예: `T00101`(001번), `T00701`(007번)…
- **행 수 / 도메인**:
  - 001~005(결제 도메인): 셸당 약 3~6행, 보기 좋은 결제 명세.
  - 006~010(야간 배치 도메인): 셸당 약 3~6행. **NG 주입 위치 요건 충족 필수**(아래):
    - **007**(1줄 NG): ≥1행. 첫 tx_id 행의 `balance_after`가 변형 대상.
    - **008**(전각공백 NG): ≥1행, **첫 tx_id 행의 customer_id가 유효 고객**이어야 顧客名이 비지 않아 전각 공백 삽입이 보임(예 田中太郎→田中　太郎).
    - **009**(다줄 NG): **≥3행**(stub가 row0 `balance_after`+1, row1 `tx_type`+"X", row2 `memo`+"差分" 변형 — row2는 memo가 있으면 더 자연스러움).
    - **010**(ERROR): 행 내용 무관(stub가 출력 전 종료코드 1로 실패 → To-Be 미생성).

#### 2. As-Is 출력 정답지(골든) — `samples/asis/output/001.csv ~ 010.csv`

- **🔴 손으로 쓰지 말 것 — stub의 `--clean` 직렬화 경로로 생성**(D-023 §4 / self-review #5). 골든과 To-Be가 *다른 writer*를 타면 통짜 바이트 비교(D-004)가 false-NG. 골든은 To-Be와 **동일 직렬화**(파일 출력=`write_csv_file`, DB 출력=`export_table_to_csv`)를 거쳐야 한다.
- **생성 방법**: 소형 골든 생성 스크립트(`tools/make_golden.py` 신규 제안)가 정의 파일을 읽어 각 셸에 대해 **오케스트레이터와 같은 경로**로
  `load_input_csv|copy_input_file` → `runner.run_batch(definition, config, conn, clean=True)`(→ DB 출력이면 exporter 다운로드) → 산출된 To-Be CSV를 `samples/asis/output/{id}.csv`로 복사.
  - `clean=True`라 NG 주입이 꺼져 정상 출력 = 골든. 실행 시 stub 비실패(`is_failure_shell`는 clean이면 통과)라 010 골든도 생성되나 **시연에선 미사용**(010 To-Be는 비-clean 실행서 RunnerError→ERROR라 비교 안 함).
  - DB 입력/출력 셸이 있으므로 **DB 필요**: dc-pg(현재 호스트 5433) + `db/schema.sql` 시드 적용, `RUN_DB_TESTS` 류 env(`PGPORT=5433` 등)·`POSTGRES_PASSWORD`.
- **출력 헤더(고정, ASCII)**: `tx_id,customer_id,customer_name,tx_date,tx_type,amount,balance_after,memo`(SPEC 6-3). `customer_name`=마스터 조인값, tx_id 정렬, Shift-JIS, `\n`.

#### 3. 정의 파일 정합

- `test_definition.yaml`은 이미 10셸이 SPEC 6-5 4사분면 매핑대로 존재(001 DB→DB … 010 ERROR). **샘플 파일명·셸 매핑이 정의와 일치**하는지만 확인(추가 편집 최소).

**완료 기준(DoD)**:
- `python -m src.cli.main --config config.yaml` E2E 실행 결과 **OK 6(001~006) / NG 3(007,008,009) / ERROR 1(010) / MISSING 0**, 종료코드 **1**(D-026: not all OK). 리포트 CSV + 007/008/009 `.diff` 생성.
- NG 3건이 SPEC 6-5 의도대로 표시: 007 `balance_after` 1자리, 008 顧客名 전각 공백, 009 3줄.
- 골든이 `--clean` 경로 산출이라 정상 셸(001~006)은 byte 동일(false-NG 0). DB 출력 셸(001,003,005,008)도 exporter 경로로 일치.
- 시연용으로 읽기 좋은 데이터(현실적 금액·일본어 이름·적요).

**산출물**: `samples/asis/input/{001~010}.csv`, `samples/asis/output/{001~010}.csv`(골든), `tools/make_golden.py`(골든 생성 스크립트, 인수 시 재생성 가능 자산), 골든 생성 스크립트의 결정론(같은 입력→같은 골든) 단위 점검.

**의존**: T2-3·T2-4(stub·runner) + T3-1~T3-3(E2E). DB(dc-pg:5433) 가동 필요.

**설계 메모(구현 시 D-027로 기록 권장)**: 골든 생성을 stub `--clean` 경로 재사용으로 못박는 결정 — 손으로 만든 골든의 직렬화 드리프트(false-NG)를 구조적으로 차단. `tools/make_golden.py`는 인수 후 실 클라이언트 데이터로 골든을 재생성하는 자산이 된다(시연 한정 데이터 교체 포인트).

---

### T4-2. README 완성 `[x]`

**목적**: 정직원이 받아서 바로 이어갈 수 있는 인수인계 문서.

**작업**:
- `README.md`
  - 프로젝트 개요 (CONTEXT 요약)
  - 빠른 시작 (5분 안에 시연 가능하도록)
  - 폴더 구조 설명
  - 교체 포인트 목록 (stub 배치, GUI 추가 위치)
  - 향후 작업 가이드 (`TASKS.md`의 미완료 항목)

**완료 기준**:
- README만 보고 처음 보는 사람이 시연을 따라할 수 있음

**의존**: 모든 이전 Task.

---

### T4-3. 인수인계 가이드 `[x]`

**목적**: 정직원이 *제품화*로 가져갈 때 필요한 가이드.

**작업**:
- `HANDOFF.md`
  - stub → 진짜 Net COBOL 배치로 교체하는 방법
  - GUI 추가 시 Core를 어떻게 재사용하는지
  - 클라이언트별 환경 적응 시 손볼 곳
  - 알려진 한계·미해결 사항 (예: 무시할 차이 규칙 미정)

**완료 기준**:
- 정직원이 이 문서만 읽고 다음 단계로 진입 가능

**의존**: 모든 이전 Task.

---

## Phase 5. GUI (프로토 이후 — 사용자 요청)

### T5-1. 로컬 웹 UI + 업로드 검증 `[x]`

**목적**: CLI 외에 브라우저에서 클릭으로 실행하는 GUI. ① 데모 10셸 자동 실행 ② 업로드 1쌍 풀체인 검증.

**작업** (D-028):
- `src/gui/web.py` — Flask. `/`·`/run`(SSE 데모)·`/verify/run`(POST 업로드, NDJSON)·`/report/<name>`(다운로드, traversal 차단).
- `src/gui/serialize.py` — Core 객체 → dict(gui에만, models 불변).
- `src/gui/upload.py` — `prepare_job`: 업로드 1쌍 → 임시 config+1셸 정의 → `run_full_comparison` 재사용.
- `src/gui/templates/index.html` — 탭 2개(데모/업로드), 실시간 진행·배지·차이·요약·리포트 다운로드.
- `run_gui.sh`(브라우저 자동 오픈) + `requirements.txt`에 `flask>=3.0`.
- **Core 무수정**. 동시 실행 락(try/finally), 비밀번호 env만.

**완료 기준**:
- `POSTGRES_PASSWORD=… ./run_gui.sh` → 브라우저에서 데모 실행 / 업로드 검증 모두 동작.
- DB 불요 단위·스모크 테스트 통과(`tests/test_gui.py`).

**의존**: T3-1~T3-3. **실행 시** DB 필요.

**후속(Phase B, 실 검증 지향)**: 업로드 UI에서 입력 테이블·배치·출력 테이블 직접 지정(데모 도메인 탈피) + 무시 규칙·정교 비교(D-022).

---

## Phase 6. GUI 납품 대비 격상 (사용자 요청)

### T6-1. 연결설정 + 다건업로드 + 일본어UI + 라이트 세련화 `[x]`

**목적**: Phase 5 GUI를 "시연용"에서 **납품 대비 제품**으로 격상. Core·`models.Config` 무수정, `src/gui/`만 확장.

**작업** (D-029):
- `src/gui/connection.py` — `test_connection`(읽기전용: SELECT 1 + 조건부 테이블 존재) + `save_connection`(DB·인코딩만 원자적 저장+.bak, 비번 미기록=모델A).
- `src/gui/upload.py` — `prepare_job`→`prepare_jobs`: N쌍 stem 짝짓기, 미매칭 명시 반환, 입력/출력 테이블·배치경로 파라미터화(_DEMO_* 제거).
- `src/gui/web.py` — `/connection/test`·`/connection/save` 신규, `/verify/run` 다건화, MAX_CONTENT_LENGTH+413, 사용자 메시지 일본어.
- `src/gui/templates/index.html` — 3탭(접속설정/업로드검증/데모), 연결설정 2섹션 분리, 폴더+다중파일, 짝짓기 안내, 일본어 전면, 라이트 세련화, localStorage 영속화.

**완료 기준**:
- 연결테스트 OK+조건부 테이블 / 잘못된 접속 친절 실패. 다건 OK/NG 혼합·미매칭 명시·매칭0건 에러.
- `tests/test_gui.py` 25개 + 전체 144 passed(DB 포함). 실 스택 라이브 스모크 통과.

**deferred**: 정교비교/무시규칙(D-022), 실 배치 연결, Core/CLI/리포트 일본어화, 실 설치 패키징, schema-qualify.

### T6-2. 정의 파일 주도 업로드 검증 `[x]`

**목적**: 셸마다 타입·테이블·배치가 다른 실무 케이스를 위해 `test_definition.yaml` 업로드로 N셸 검증(정의 주도). 화면 3칸(동질 묶음)과 양립.

**작업** (D-030):
- `src/gui/upload.py` — `summarize_definition`(파싱 미리보기), `prepare_jobs_from_definition`(yml 정본, 파일명 매칭, 누락 셸 제외, shell_program 절대화).
- `src/gui/web.py` — `/definition/parse` 신규(읽기전용), `/verify/run`을 `definition` 파일 유무로 분기(있으면 정의 우선).
- `src/gui/templates/index.html` — 업로드 탭에 "定義ファイル(任意)" 픽커 + 파싱 미리보기(N셸·타입) + 우선순위 안내 + 해제.

**완료 기준**:
- `/definition/parse`로 10셸 인식, 정의 주도 `/verify/run`이 입력/정답 매칭해 N셸 실행, 누락 셸 명시.
- `tests/test_gui.py` 34개 통과. 실 스택 라이브: 실 yaml+샘플20 → OK6/NG3/ERROR1.

**deferred**: 정의 파일이 참조하는 CSV의 원격/경로 참조(현재는 함께 업로드), 그 외 D-029 deferred 동일.

### T6-3. 매핑표(CSV) → 정의 yaml 자동 생성 `[x]`

**목적**: 수기 yaml 제거. 고객 셸-테이블 매핑표(CSV) 한 장으로 `test_definition.yaml` 자동 생성(대량 셸).

**작업** (D-031):
- `src/gui/upload.py` — `definition_from_mapping`(CSV→yaml, 필수열·기본값·엄격·round-trip 검증).
- `src/gui/web.py` — `/definition/from-mapping` 신규(읽기전용).
- `src/gui/templates/index.html` — "マッピング表(CSV)から生成" 픽커 + 미리보기 + YAML 다운로드 + 그대로 검증.
- `samples/shell_mapping.example.csv`(10셸).

**완료 기준**: 매핑표→10셸 yaml 생성→그 정의로 검증 OK6/NG3/ERROR1. `tests/test_gui.py` 39개 통과.

**deferred**: Excel(.xlsx) 직접 파싱(CSV로 저장), 매핑 자동 추론.

---

## Phase 7. 기획서 7.1 풀스키마 복원 — 다중 입력·다중 출력 (회의 2026-06-03, D-033)

**배경**: 실 운영 배치는 한 셸이 **여러 테이블/파일 입력**을 읽고 **DB·파일로 동시에 출력**한다(사장님 확인). 프로토에서 단일화(D-021/022)한 것을 기획서 7.1대로 **복원**. 정본 규격 = [DEFINITION_SPEC.md](DEFINITION_SPEC.md). 코어 재사용(리스트 루프), 새 설계 아님. 별도 브랜치 `feat/fullschema-multi-io`.

**회의 확정**: 다중출력 흔함→**출력 단위 집계** / 다중입력 필요 / 프로그램 여러 개는 **잡 1회·최종출력만 비교** / DB접속 **공통 1곳(config)** / 디렉토리 **config 공통** / 짝짓기 **expected 명시** / **SAM은 파일출력만**(포맷터 불요) / UI는 **버튼+모니터+결과**(매핑·연결 UI 경량화).

### T7-1. 다중 입력 적재 `[x]`

**작업** (D-033 P1): `models.InputSpec` + `ShellDefinition.inputs[]`(`__post_init__` 백필) / `definition`이 신형 `input.tables[]`·구형 단일 모두 파싱→정규화 / `orchestrator._load_step` 루프 적재(DB마다 commit, D-023) / `_needs_db` 다건.
**완료 기준**: 하위호환(기존 단일형 무수정 통과, 전체 160 passed) + 다중입력 테스트 4건. ✅

### T7-2. 다중 출력 추출·비교 `[x]`

**작업** (D-033 P2): `OutputSpec`/`ShellDefinition.outputs[]` + `ComparisonResult.output_name`(셸당 결과 N건) / `runner` 다중 출력 추출(DB→export / file→그대로) / `reporter` (shell_id,output) 행·RunSummary `total=출력 수`(D-016 합항등 유지) / 진행 이벤트 출력 단위 / GUI 출력별 표시·카드·필터(출력 단위).
**완료 기준**: 다중출력 정의(파일+DB 동시)로 출력별 OK/NG 결과·리포트·화면. 하위호환(단일=출력 1) 유지.

### T7-3. UI 경량화 + 정의 파일 주도 일원화 `[x]`

**작업** (D-034): 실무 타깃 UI(**버튼 1개→자동 실행→실시간 모니터링→결과**)로. 연결설정/테이블선택/매핑 UI는 정의 파일 주도로 흡수(설치 시 config·정의 파일로). 단일 화면 = 設定/接続(접이식, 접속테스트·저장) → 検証実行(정의 미리보기 N셸 + `/run` SSE) → 모니터링 → 요약/필터. 3탭·위저드·업로드CSV검증·매핑표생성·테이블선택 3칸 + 그 라우트(`/verify/run`·`/definition/parse`·`/from-mapping`·`/mapping-template`)·`upload.py` 미사용 함수·테스트 제거(불필요·간결, D-028~031 supersede). `summarize_definition`은 실행 전 미리보기로 재사용. **Core·models 무수정**.

**완료 기준**: 단일 화면 렌더, `/run` SSE 그대로 동작, 정의 미리보기(N셸·다중I/O 카운트), 접속테스트·저장 유지. `tests/test_gui.py` 그린.

**deferred**: 정교 비교(공차·날짜, D-022), 물리 다중 DB 접속, SAM 등 확장자 실데이터 QA(2순위).

### T7-4. 매핑표(Long CSV) → 정의 yaml 생성 도구 `[x]`

**작업** (D-035): 수기 YAML 회피 — 스프레드시트(CSV)로 셸-입출력 매핑을 채워 `test_definition.yaml` 생성. 다중 입출력 표현 위해 **Long 형식**(입출력 항목당 1행, `shell_id` 그룹화). **독립 CLI** `tools/mapping_to_definition.py`(GUI 아님 — T7-3 경량화 유지). 로더 실필드명 방출 + 엄격 검증 + round-trip. 예시 `samples/shell_mapping.long.example.csv`, 옛 단일I/O 매핑 예시 제거.

**완료 기준**: `python tools/mapping_to_definition.py mapping.csv -o def.yaml` 동작, 다중I/O 그룹화, 오류 행별 보고+종료코드1, 생성 yaml 로더 통과. `tests/test_mapping_to_definition.py` 12개 통과.

**보조 도구**(D-035): `tools/checklist_to_template.py` — 고객 **체크리스트(항목명 목록) → 기입용 빈 매핑 CSV 템플릿** 생성(shell_id 자동번호·test_name에 항목명 선반영). 고객은 빈 칸만 채워 반환 → 변환기로 yaml. **정의 순서·리포트가 체크리스트와 1:1**(추적·관리 용이). `tests/test_checklist_to_template.py` 6개 통과.

---

## 권장 작업 순서 요약

```
Phase 0:  T0-1 → T0-2 → T0-3
Phase 1:  T1-1 → T1-2          (Phase 2와 병렬 가능)
Phase 2:  T2-1 → T2-2 → T2-3 → T2-4
Phase 3:  T3-1 → T3-2 → T3-3
Phase 4:  T4-1 → T4-2 → T4-3
```

가장 *불확실성이 적은* T1-1(Comparator)부터 시작해서 자신감을 쌓은 뒤 인프라 작업으로 넘어가는 것을 권장.

---

## Task 작업 시 체크리스트

각 Task를 시작할 때:

- [ ] 이 Task의 목적·완료 기준을 읽었는가?
- [ ] 의존 Task가 모두 완료되었는가?
- [ ] 관련된 SPEC/ARCHITECTURE 섹션을 확인했는가?

각 Task를 끝낼 때:

- [ ] 모든 완료 기준을 만족하는가?
- [ ] 단위 테스트가 통과하는가?
- [ ] CLAUDE.md의 금지 사항을 어기지 않았는가? (특히 Core 안의 print, 하드코딩)
- [ ] 새로운 결정 사항이 있다면 DECISIONS.md에 기록했는가?
- [ ] 이 파일의 해당 Task를 `[x]`로 표시했는가?
