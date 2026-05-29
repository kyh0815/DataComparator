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

### T2-3. Stub 배치 작성 `[ ]`

**목적**: 진짜 Net COBOL 배치 대신 시연용 가짜 배치.

**작업**:
- `stub_batch/run_batch.py`
  - 인자: `--shell-id`, `--output-path`, DB 접속 정보
  - DB에서 input 읽어 단순 변환 후 CSV로 출력 (Shift-JIS)
  - **시연용 NG 패턴**: 특정 shell_id에서 의도적으로 다르게 동작
    - 007: 한 줄 값 변경
    - 008: 공백/포맷 차이
    - 009: 여러 줄 차이
    - 010: 의도적 종료 코드 1 (실행 실패 시연)
- 코드 최상단에 명시:
  ```
  # === 인수인계 시 교체 포인트 ===
  # 이 파일은 시연용 stub 배치. 실 운영에서는 Net COBOL 배치 호출로 교체.
  # 입출력 계약(--shell-id, --output-path)은 유지.
  ```

**완료 기준**:
- 단독으로 실행 가능 (`python stub_batch/run_batch.py --shell-id 001 ...`)
- 정상 케이스에서 적절한 CSV 생성
- 의도된 NG 패턴이 SPEC.md대로 동작

**의존**: T2-1, T2-2.

---

### T2-4. Runner 구현 `[ ]`

**목적**: Core에서 stub 배치를 호출.

**작업**:
- `src/core/runner.py`
  - `run_batch(shell_id: str, config: Config) -> Path`
  - `subprocess`로 stub 실행, stdout/stderr 캡쳐
  - 종료 코드 0이 아니면 예외
  - 반환: 생성된 To-Be 출력 CSV 경로
- 코드 상단에 교체 포인트 주석.

**완료 기준**:
- 정상 케이스에서 stub 호출 → 출력 CSV 경로 반환
- 비정상 종료 시 명확한 예외
- 단위 테스트 (mock subprocess)

**의존**: T2-3.

---

## Phase 3. 오케스트레이션과 CLI

### T3-1. Core 오케스트레이션 `[ ]`

**목적**: E2E 흐름을 묶는 함수. CLI/GUI 공통 진입점.

**작업**:
- `src/core/__init__.py` 또는 `src/core/orchestrator.py`
  - `run_full_comparison(config: Config, on_progress: Callable | None = None) -> RunSummary`
  - 셸 ID 목록 결정 (config의 range 또는 ids)
  - 각 셸에 대해 loader → runner → comparator 순서로 호출
  - 각 단계 후 `on_progress` 콜백으로 진행 보고
  - 예외 발생 시 해당 셸은 ERROR로 기록하고 다음 진행
  - 최종적으로 reporter 호출 → RunSummary 반환

**완료 기준**:
- 콜백 없이 호출해도 동작
- 콜백을 넘기면 단계별 이벤트 발생 확인
- 일부 셸에서 예외 발생 시 다른 셸은 정상 처리되는지 확인

**의존**: T1-1, T1-2, T2-2, T2-4.

---

### T3-2. CLI 출력 모듈 `[ ]`

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

### T3-3. CLI Entry Point `[ ]`

**목적**: 사용자가 실제로 실행하는 진입점.

**작업**:
- `src/cli/main.py`
  - argparse로 인자 파싱
  - config 로드
  - `cli/output.py`의 콜백 준비
  - `core.run_full_comparison(config, on_progress=cb)` 호출
  - 최종 요약 출력
  - 종료 코드: NG/ERROR가 있으면 1, 모두 OK면 0

**완료 기준**:
- `python -m src.cli.main --config config.yaml` 한 줄로 E2E 실행
- 결과가 SPEC 4·5장대로 출력 + CSV 파일 생성
- `--shells`, `--verbose` 인자 동작

**의존**: T3-1, T3-2, T0-3.

---

## Phase 4. 시연 데이터와 마무리

### T4-1. 시연용 샘플 데이터 작성 `[ ]`

**목적**: 사장님 시연 시 사용할 1~10번 CSV 쌍 준비.

**작업**:
- `samples/asis/input/001.csv ~ 010.csv` 생성
  - 일본어 데이터 포함 (Shift-JIS 인코딩)
  - 실제 메인프레임 배치 결과처럼 보이는 형태 (예: 고객 마스터, 거래 명세 등)
- `samples/asis/output/001.csv ~ 010.csv` 생성
  - stub 배치가 *정상 케이스*에서 만들어낼 결과와 동일
  - 단, 007/008/009는 stub과 *의도된 차이*를 갖도록 설계

**완료 기준**:
- 전체 E2E 실행 시 6 OK / 3 NG / 1 ERROR로 결과가 나옴 (SPEC 6-2 표대로)
- 시연용으로 보기 좋은 데이터

**의존**: T2-3 (stub 동작 확인 후).

---

### T4-2. README 완성 `[ ]`

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

### T4-3. 인수인계 가이드 `[ ]`

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
