# HANDOFF.md

> 인수인계 가이드. 두 종류의 인계를 다룬다.
>
> 1. **제품화 인계(정직원 대상)** — 이 프로토를 실 운영 제품으로 가져갈 때: 아래 본문(1~6장).
> 2. **Claude Code 세션 인계** — AI 세션 간 맥락 전달: 맨 아래 **부록 A**.

---

## 1. 이 문서의 대상

이 프로토타입을 받아 **제품화**하는 정직원을 위한 가이드다. "무엇이 이미 동작하고, 무엇이
시연용 부품이라 교체해야 하며, 어디를 어떻게 손대고, 무엇이 아직 안 된 채 남아 있는지"를
한곳에 모았다. 빠른 시작·실행법은 루트 `README.md`, 설계 근거는 `docs/DECISIONS.md`(D-xxx).

---

## 2. 30초 개요 — 동작 vs 시연 한정

| 구분 | 항목 | 상태 |
|---|---|---|
| **동작(자산)** | Core 6모듈(loader/runner/exporter/comparator/reporter/orchestrator) + CLI | ✅ E2E 동작 |
| | 입력 2종(DB/파일) × 출력 2종(DB/파일) = 4사분면 라우팅(정의 파일 주도) | ✅ |
| | 통짜 바이트 비교·리포트(CSV+`.diff`)·진행/요약 출력·종료코드 | ✅ |
| **시연 한정(교체 대상)** | `stub_batch/run_batch_db.py`·`run_batch_file.py` (가짜 배치) | 🔁 진짜 배치로 |
| | `db/schema.sql` (금융 도메인 시연 스키마) | 🔁 실 스키마로 |
| | `test_definition.yaml` (시연 10셸·경량 스키마) | 🔁 실 셸·풀스키마로 |
| | `samples/` (시연 입력·골든) | 🔁 실 데이터로 (정답=**변환 후 As-Is 출력 수령**, make_golden 아님) |
| | `config.yaml` (시연 환경값) | 🔁 클라이언트 환경값 |

핵심: **Core·정의 파일 메커니즘은 그대로 두고, 위 5개 부품만 교체**하면 실 운영으로 간다.
도구의 진짜 가치는 *정의 파일로 스키마·입출력 방식을 받아 처리하는 동적 적응*이다(D-021).

---

## 3. 교체 포인트 (제품화 핵심)

### 3-1. stub → 진짜 Net COBOL 배치 ★가장 중요·함정 많음

`test_definition.yaml`의 `execution.shell_program`을 진짜 배치(실행 가능 파일)로 바꾼다.
Runner가 그 경로를 **실행파일로 직접 호출**하므로(파이썬 하드코딩 아님, D-023) 런처 코드 수정은
불필요하다. 단, 아래 **계약**을 지켜야 시연이 조용히 깨지지 않는다.

**(1) Runner가 넘기는 argv는 고정 세트다 — "받되 무시 가능", "안 받는다"가 아니다.**

```
<shell_program> --shell-id <id> --output-type <file|database> --encoding <enc> \
                --db-host <h> --db-port <p> --db-name <db> --db-user <u> \
                (--input-table <t>   |  --input-file <path>) \
                (--output-path <path> |  --output-table <t>) \
                [--clean]
```

- 실 배치는 자기 I/O 위치가 고정이라 대부분의 인자를 **무시해도 된다**. 그러나 argparse 류
  래퍼라면 이 인자들을 **수용**해야 한다(정의해 두거나 `parse_known_args` 사용). 안 그러면
  `unknown argument`로 즉사한다. → "배치는 `--shell-id`만 받는다"가 아니라 **"이 argv를 받되
  무시해도 된다"**가 정확한 계약이다. 배치의 *본질* 식별자는 `--shell-id`.
- **비밀번호는 argv에 없다.** `POSTGRES_PASSWORD` 환경변수로 전달된다(ps 노출 방지). 배치가 DB에
  접속한다면 env에서 읽어야 한다.

**(2) 출력 위치는 argv가 아니라 정의 파일이 선언한다.** 오케스트레이터는 To-Be를 정의 파일이
선언한 위치에서 찾는다:

- **출력=file**: To-Be는 `tobe_output_dir/<output.file>`. Runner가 `--output-path`로 그 경로를
  알려주므로 배치가 거기에 쓰면 된다(또는 배치 고정 출력 위치에 맞춰 `output.file`을 선언).
- **출력=database**(파일 출력엔 없는 추가 계약):
  - ⓐ 배치는 **`output.table`이 가리키는 결과 테이블에 쓴다**(시연은 `tobe_result`). 위치는 argv가
    아니라 정의 파일 `output.table`이 정본.
  - ⓑ 배치는 **자기 connection에서 commit**해야 한다. exporter가 **별도 connection**으로 배치 실행
    *직후* 그 테이블을 읽어 CSV로 내리기 때문(`export_table_to_csv`). commit 누락 시 exporter가
    **빈/낡은 데이터**를 읽어 시연이 조용히 false-OK 또는 빈 출력으로 깨진다.
  - ⓒ 오케스트레이터의 **셸 단위 트랜잭션 경계(D-023)를 깨지 말 것**. 오케스트레이터는 셸 종료 시
    `rollback`으로 exporter의 읽기 트랜잭션을 해제해 다음 셸의 `TRUNCATE`가 락 걸리지 않게 한다.
    배치가 자기 트랜잭션만 정상 commit하면 이 경계는 유지된다.

**(3) 정답(골든)은 생성이 아니라 "변환 후 As-Is 출력"을 수령한다**(실환경): 정답 = 코드 변환 툴이 낸
*변환 후 As-Is 출력*을 `asis_output_dir`에 그대로 둔 것. To-Be 출력과 **같은 변환 표준 포맷**이라 데이터가
같으면 바이트도 같다(D-004). 표기만 미세하게 어긋나는 false-NG는 그때 가벼운 정규화로(D-022, 5장).
※ `tools/make_golden.py`(stub `--clean`로 골든 생성)는 **진짜 As-Is 출력이 없는 데모 한정** — 실환경 미사용(3-6).

> 요약: 파일-출력 배치는 "`--output-path`에 정해진 포맷으로 써라"가 전부지만, **DB-출력 배치는
> ⓐ 정의된 테이블에 ⓑ commit하고 ⓒ 트랜잭션 경계를 지켜야** 한다. "stub만 바꾸면 된다"를 믿고
> commit 없이 DB-출력 배치를 짜는 것이 가장 흔한 함정.

### 3-2. `test_definition.yaml` → 실 스키마·셸

시연 10셸(4사분면 매핑)을 실 클라이언트의 셸 목록·테이블로 교체한다(D-021/D-022). 구조는 Boss
기획 7.1절의 경량 버전이라, `comparison_rules`·`success_criteria`·`parameters`·`key_columns` 등
**풀스키마 필드는 자리만 비어 있다** — 정교 비교(5장) 도입 시 여기를 채운다.

### 3-3. `db/schema.sql` → 실 비즈니스 스키마

시연용 금융 도메인(`customer_master`/`transaction_log`/`tobe_result`)을 실 클라이언트 스키마로 교체
(D-018). 시연은 슈퍼유저 `postgres`를 쓰지만 **운영은 권한 분리된 별도 유저** 권장. DB 내부는
UTF-8, CSV만 Shift-JIS, 변환은 파일↔DB 경계의 Python 레벨에서만(D-018) — 이 원칙은 유지한다.

### 3-4. `config.yaml` → 클라이언트 환경값

인코딩·경로·OS·DB 접속을 환경에 맞춘다. `config.yaml`은 gitignore(실값 미커밋), `config.yaml.example`을
복사해 쓴다. 비밀번호는 `password_env`가 가리키는 환경변수에서 읽는다(D-019).

### 3-5. GUI 추가 → Core 그대로 재사용

`src/gui/`를 새로 추가하고 **Core는 그대로 호출**한다. CLI와 GUI는 같은 진입점을 공유한다:

```python
summary = run_full_comparison(config, on_progress=callback, shell_ids=None)
```

- `on_progress(event: ProgressEvent)` 콜백으로 진행을 받는다(`SHELL_START`/`STEP`/`SHELL_DONE`).
  콜백 방식은 **GUI 이식을 전제로 선택**됐다(D-025, ARCHITECTURE 5-3). GUI는 이 콜백을 위젯 갱신에
  연결하고, `RunSummary`(반환값)로 최종 요약을 그리면 된다.
- Core는 `print`를 하지 않으므로(CLAUDE 3-1) 출력 충돌이 없다. `src/cli/output.py`가 콜백→터미널
  렌더의 참조 구현이다.

### 3-6. 정답(골든)은 "변환 후 As-Is 출력"을 배치 — 생성 아님

**실환경**: 정답지 = 코드 변환 툴이 낸 **변환 후 As-Is 출력 데이터**를 `asis_output_dir`(정의의 `expected`)에
그대로 둔다. To-Be 출력과 동일 변환 표준 포맷이라 통짜 바이트 비교가 성립(CONTEXT 3-1 파이프라인). `make_golden` 안 돌린다.

**데모 한정**: 진짜 As-Is 출력이 없을 때만 `tools/make_golden.py`가 stub `--clean` 경로로 골든을 *흉내내* 생성한다
(To-Be와 같은 직렬화라 false-NG 차단, D-027). 입력 예시는 `tools/make_samples.py`. **둘 다 시연용이며 실 데이터로 교체 시 미사용.**

---

## 4. 클라이언트 환경 적응 체크리스트

- [ ] **인코딩**: 기본 Shift-JIS. 클라이언트가 다르면 `config.yaml`의 `encoding`만 바꾼다(코드 수정 X).
- [ ] **OS**: 시연은 우분투(D-003), 운영은 PITON 등. Runner는 실행파일을 직접 호출(shebang+실행비트
      전제) — **Windows는 현재 범위 밖**.
- [ ] **DB 접속·권한**: `database.*` + `password_env`. 운영은 최소 권한 유저.
- [ ] **셸 ID 명명**: 현재 **3자리 zero-pad 고정은 프로토 한정**(D-019 §4, 샘플 001~010 기준). 실
      운영의 셸 수/명명 규칙이 다르면 `settings._pad_shell_id`/정의 파일 ID 정규화를 재검토.
- [ ] **타임아웃**: 배치별 `execution.timeout` / `batch.timeout_seconds`.

---

## 5. 알려진 한계·미해결 (deferred)

| 한계 | 내용 | 근거 |
|---|---|---|
| 통짜 바이트 비교의 false-NG | DB 왕복·포맷 차 등으로 무해한 차이가 NG로 잡힐 수 있음 | D-004 |
| **무시할 차이 규칙 미정** | 운영 시 "무시해도 되는 차이"(공백·날짜 포맷 등) 규칙이 없음 | D-004/운영 |
| 정교 비교 부재 | 행/열 단위·정렬·숫자 공차·날짜 정규화 비교는 미구현 | D-022 |
| 리포트 고도화 부재 | HTML/Excel 리포트, DB 결과 저장(`test_validation_results`/`mismatch_details`) 없음 | D-022 |
| verbose 로그 일부 | 배치 stdout·SQL 적재 로그는 Core가 `logging` 미배출이라 `--verbose`로 안 보임 | D-025 §5 |
| 규모 | 100건 풀 구현·추가 도메인·직접 DB 비교 미구현(프로토는 10셸) | D-021 |
| `--clean` 미노출 | 골든 생성은 CLI가 아니라 `tools/make_golden.py` | D-026 |
| both-missing 처리 | As-Is·To-Be 둘 다 없으면 SPEC 3-3는 "제외"지만 프로토는 ERROR로 기록 | D-024 |

> **운영 위생 주의(D-023)**: DB-입력 셸의 `load_input_csv`는 적재 후 **commit**한다(stub이 별도
> connection으로 보게 하려고). 따라서 실 데이터 적재 시 시드/실데이터가 `TRUNCATE`→재적재로
> 덮인다 — 테스트뿐 아니라 **운영에서도** 대상 테이블 위생(전용 테이블/백업)에 주의.

---

## 6. 제품화 로드맵 제안 (인수 후 우선순위)

1. **실 연결**: `db/schema.sql`·`test_definition.yaml`을 실 스키마·셸로, stub을 진짜 배치로 교체(3-1~3-3).
2. **비교 정확도**: 무시할 차이 규칙 + 정교 비교(행/열·공차·날짜 정규화) — false-NG 감소(5장).
3. **리포트 고도화**: HTML/Excel·DB 결과 저장(D-022 풀스키마 필드 활성화).
4. **GUI**: `src/gui/`에서 Core 재사용(3-5).

각 단계는 Core 계약(구조화 객체 반환·정의 파일 주도)을 유지하는 한 독립적으로 진행 가능하다.

---
---

## 부록 A. 세션 인계 템플릿 (Claude Code 세션 간 인계용)

Claude Code는 세션 간 메모리가 없다. 새 세션은 **아무것도 모르는 상태**이므로,
*맥락 주입 → 현재 상태 인계 → Task 설명 → 게이트* 순서로 프롬프트를 준다.

### A. 범용 템플릿 (`{...}` 부분만 채워서 사용)

```
이 프로젝트는 메인프레임 → 리눅스 마이그레이션의 배치 출력 동등성을
자동 검증하는 도구의 Working 프로토타입이야. 너는 이 프로젝트를 처음 보는
새 세션이니, 먼저 맥락을 주입받고 → 현재 상태를 파악한 뒤 → 이번 Task를
시작한다. 각 단계가 끝나면 한국어로 보고하고, 마지막에 내 OK를 받고 코딩 시작.

────────────────────────────────────
[1단계] 맥락 주입 — 아래 순서로 읽어
────────────────────────────────────
1. docs/CLAUDE.md       (작업 규칙 — 특히 Core/Interface 분리, print 금지, 하드코딩 금지)
2. docs/CONTEXT.md      (사업·도메인 맥락)
3. docs/ARCHITECTURE.md (시스템 구조, 모듈 책임)
4. docs/SPEC.md         (기능 명세)
5. docs/DECISIONS.md    (결정 이력)

읽고 다음을 3~5줄로 요약: 이 도구가 무엇이고, Core/Interface 분리 원칙을
어떻게 이해했는지.

────────────────────────────────────
[2단계] 현재까지 진행 상태 파악 (중요: 이미 끝난 것을 새로 만들지 말 것)
────────────────────────────────────
docs/TASKS.md 를 읽고 완료(`[x]`) 표시를 확인해. 완료된 모듈은 그대로
import 해서 입력으로 사용한다 — 추측하지 말고 실제 파일을 열어 시그니처 확인.

{여기에 "지금까지 완료된 Task와 산출 파일" 목록을 구체적으로 적는다}
{예: [x] T1-1 Comparator → src/core/comparator.py compare_files() 완성}
{현재 pytest 통과 수도 적어두면 좋다}

────────────────────────────────────
[3단계] 이번 Task — {Task 번호와 제목}
────────────────────────────────────
관련 문서 정독:
- docs/TASKS.md 의 {Task 번호} 항목 (목적·작업·완료 기준)
- docs/ARCHITECTURE.md {관련 섹션}
- docs/SPEC.md {관련 섹션}

확인 후 보고할 것:
- 만들 함수 시그니처
- 처리할 케이스 (완료 기준의 테스트 케이스들)
- 작업 순서 계획

────────────────────────────────────
[게이트] 위 3단계 보고가 끝나면 멈추고 내 OK를 기다려. OK 후 코딩 시작.
완료 시: DoD 자체 점검 → 새 결정은 docs/DECISIONS.md 에 기록 →
docs/TASKS.md 의 해당 Task를 [x] 로 표시.
```

### B. 작성 원칙 (왜 이 구조인가)

- **맥락 주입을 항상 먼저**: 새 세션은 사업·구조·규칙을 모른다. 문서 읽기를 건너뛰면 설계가 어긋난다.
- **"이미 끝난 것"을 반드시 명시**: 가장 중요한 인계 정보. 완료된 모델/함수를 *새로 만들지 말고 import* 하도록 못박아 재작업을 막는다.
- **단계마다 보고 + 마지막 게이트**: 곧바로 코드로 폭주하는 것을 방지. 항상 사람이 게이트.
- **경로는 `docs/` 기준**(D-013): 설계 문서는 `docs/` 폴더, README.md만 루트.

> 즉시 사용본(현재 상태로 [2]·[3]단계를 채운 복붙용)은 매 Task마다 최신 상태로 갱신해 쓴다.
> 작성 당시 예시(T2-3용)는 git 이력 참고. 최신 진행 상태는 메모리(`dc-current-state`)·`docs/TASKS.md`.
