# HANDOFF.md

> 인수인계 가이드.
>
> ⚠️ **이 문서는 아직 미완성입니다.** 정직원 대상 *제품화 인계 가이드*(stub→Net COBOL 교체,
> GUI 추가, 클라이언트 환경 적응, 알려진 한계)는 **T4-3**에서 완성됩니다.
> 현재는 아래 **"세션 인계 템플릿"** 섹션만 작성되어 있습니다.

---

## 세션 인계 템플릿 (Claude Code 세션 간 인계용)

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

---

## (다음 세션 바로 쓰기) T2-3 Stub 배치

아래는 위 템플릿의 [2]·[3]단계를 현재 상태로 채운 즉시 사용본이다. **새 세션에 그대로 복붙**하면 된다.

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
5. docs/DECISIONS.md    (결정 이력 — D-001 ~ D-020)

읽고 다음을 3~5줄로 요약: 이 도구가 무엇이고, Core/Interface 분리 원칙을
어떻게 이해했는지.

────────────────────────────────────
[2단계] 현재까지 진행 상태 파악 (중요: 이미 끝난 것을 새로 만들지 말 것)
────────────────────────────────────
docs/TASKS.md 를 읽고 완료(`[x]`) 표시를 확인해. 지금까지 완료된 것:

- [x] T0-1 프로젝트 골격  → src/{core,cli,config}, stub_batch, tests 등 존재
- [x] T0-2 데이터 모델    → src/core/models.py (ComparisonStatus, ShellPair, DiffLine,
                            ComparisonResult, RunSummary(+missing_count), Config 등)
- [x] T0-3 설정 로더      → src/config/settings.py 의 load_config()/ConfigError (D-019)
- [x] T1-1 Comparator    → src/core/comparator.py 의 compare_files() (D-014/D-015)
- [x] T1-2 Reporter      → src/core/reporter.py 의 generate_report() (D-016/D-017)
- [x] T2-1 Sample DB     → db/schema.sql (customer_master/transaction_log + 더미) +
                            docs/SETUP.md. DB는 UTF-8, 파일만 Shift-JIS (D-018)
- [x] T2-2 Loader        → src/core/loader.py 의 load_input_csv(csv_path, conn,
                            table_name, encoding) -> int (D-020)
- [ ] T2-3 Stub 배치      → ★ 이번에 할 것
- [ ] T2-4 Runner, T3-*, T4-* → 이후

현재 `pytest` 는 37 passed / 3 skipped(DB 통합 테스트는 RUN_DB_TESTS=1 일 때만).
문서는 모두 docs/ 폴더, README.md만 루트(D-013).

★ 반드시 직접 열어 실제 계약을 확인할 것 (추측 금지):
- db/schema.sql            (테이블/컬럼 — stub이 SELECT/생성할 데이터 구조)
- src/core/loader.py       (load_input_csv 시그니처·동작 — 적재 결과를 stub이 읽음)
- src/core/comparator.py   (compare_files — stub 출력이 이걸로 비교됨)
- docs/DECISIONS.md D-018, D-020 (셸→데이터 매핑이 "T2-3에서 정의"로 미뤄져 있음)

────────────────────────────────────
[3단계] 이번 Task — T2-3 Stub 배치
────────────────────────────────────
관련 문서 정독:
- docs/TASKS.md 의 T2-3 항목 (목적·작업·완료 기준)
- docs/ARCHITECTURE.md 4-3 (runner)·8 (교체 포인트) — stub은 인수 시 교체 대상
- docs/SPEC.md 6 (stub 배치 동작)·6-2 (의도된 NG 시연 표)

이 Task는 결정이 많다. 보고에 반드시 포함할 것:
- stub 실행 인터페이스 (인자: --shell-id, --output-path, DB 접속 등)
- ★ 셸→데이터 매핑 설계 (D-018/D-020에서 미뤄둔 것):
  10개 셸이 customer_master/transaction_log(seed) 를 어떻게 읽어
  셸별 To-Be 출력 CSV를 만드는가. 입력 CSV는 어느 테이블에 적재되는가.
- ★ 시연용 NG 패턴 (SPEC 6-2): 001~006 OK / 007 한 줄 값 차이 /
  008 공백·포맷 차이 / 009 여러 줄 차이 / 010 종료코드 1(실행 실패)
- 출력 CSV 인코딩: Shift-JIS (파일↔DB 경계 변환, D-018)
- 코드 최상단 "=== 인수인계 시 교체 포인트 ===" 주석 (입출력 계약 유지)
- 테스트 전략 (DB 의존은 T2-2처럼 RUN_DB_TESTS=1 조건부 skip 권장)

핵심 완료 기준 (TASKS T2-3):
- 단독 실행 가능 (python stub_batch/run_batch.py --shell-id 001 ...)
- 정상 케이스에서 적절한 CSV 생성, 의도된 NG 패턴이 SPEC 6-2대로 동작

────────────────────────────────────
[게이트] 위 3단계 보고가 끝나면 멈추고 내 OK를 기다려.
특히 "셸→데이터 매핑"과 "NG 패턴 구현 방식"은 결정이 큰 부분이니
제안을 먼저 보여주고 내 OK 후에만 코딩 시작.
완료 시: DoD 자체 점검 → 새 결정은 docs/DECISIONS.md 에 기록(D-021~) →
docs/TASKS.md 의 T2-3 를 [x] 로 표시.
```

> 다음 Task로 넘어갈 때: 위 즉시 사용본의 [2]단계(완료 목록·pytest 수)와 [3]단계(Task)를
> 그때의 최신 상태로 갱신해서 쓰면 된다. 갱신이 귀찮으면 **A. 범용 템플릿**을 채워 사용.
