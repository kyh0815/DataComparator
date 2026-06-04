# HANDOFF — Phase 7 (기획서 7.1 풀스키마 복원) 세션 인계

> 새 Claude Code 세션이 이 작업을 이어받기 위한 인계서. 작성 2026-06-03.
> 작업 방식은 **게이트형**(맥락 로드 → 설계 보고 → 사용자 OK → 코딩). [[dc-working-style]]·[[dc-self-review]] 준수.

---

## 0. 30초 요약

메인프레임→Linux 배치 출력 **동등성 자동 검증 도구**. 사장님 회의(2026-06-03)로 **기획서 7.1
풀스키마(한 셸이 다중 입력 테이블 + 다중 출력)**를 복원 중. 엔진·리포트·GUI의 **다중 입력(T7-1)·
다중 출력(T7-2)은 완료**. **남은 건 T7-3(UI 경량화) + 실전 QA + 정교비교 등 deferred**.

- **브랜치**: `feat/fullschema-multi-io` (origin push됨, HEAD `5167aa8`)
- **main**(`960875a`)에 **미머지** — Phase 5+6은 main에 있음, Phase 7은 브랜치에만.
- 전체 **170 passed**(DB 통합 포함). 로컬 워킹트리 clean.

---

## 1. 맥락 로드 순서 (새 세션은 이 순서로 읽기)

1. **메모리**: `MEMORY.md` → **`dc-fullschema`(★이번 작업 정본 포인터)** → `dc-current-state` → `dc-working-style` → `dc-self-review` → `dc-env-hazard`(★pytest 전 commit/push) → `dc-i18n-jp`.
2. **`docs/DEFINITION_SPEC.md`** ★ — 정의 파일 규격 **정본**(config 공통·다중 입출력·expected 명시·SAM은 파일출력만·출력 단위 집계).
3. **`docs/DECISIONS.md` D-033** — 7.1 복원 결정·회의 확정·단계화(P1/P2).
4. `docs/TASKS.md` **Phase 7**(T7-1 `[x]` / T7-2 `[x]` / T7-3 `[ ]`).
5. `docs/SPEC.md`·`docs/ARCHITECTURE.md` 상단 **정렬 노트**(단일 입출력은 프로토 현동작, 정본=DEFINITION_SPEC).
6. `docs/CLAUDE.md`(작업규칙: Core/Interface 분리·print 금지·하드코딩 금지).
7. 기획서 원안: `docs/AlignmentCheck/InitialPlanning.md` 7.1, `Requirements.md`.

---

## 2. 현재까지 완료된 것 (새로 만들지 말 것)

### T7-1 다중 입력 (커밋 `43c5d40`)
- `models.InputSpec`(csv/type/table/dest_dir) + `ShellDefinition.inputs[]`. `__post_init__`가 단일 필드에서 백필.
- `config/definition.py`: 신형 `input.tables:[...]` / 구형 단일 모두 파싱 → `inputs[]` 정규화(`_build_inputs`). DB 항목별 `table` 필수.
- `core/orchestrator.py` `_load_step`: `inputs[]` 루프 적재(DB 적재마다 commit, D-023 ①). `_needs_db` 다건 반영.

### T7-2 다중 출력 (커밋 `dcc8897`·`ad48658`·`5167aa8`) ★결과 단위 셸→(셸,출력) 전환
- `models.OutputSpec`(type/expected/table/export_as/file/name + `label`·`tobe_name` property) + `ShellDefinition.outputs[]`(`__post_init__` 백필). `ComparisonResult.output_name`(단일=None, 다중=라벨).
- `definition.py` `_build_outputs`: 신형 `outputs:[...]`(각 `expected`) / 구형 단일(`output`+`expected_output_csv`) 파싱·검증. 구형 `export_csv`→`export_as` 매핑.
- `core/runner.py` `run_batch` → **`list[tuple[OutputSpec, Path]]`**: 배치 1회 실행 후 `outputs[]` 루프(DB=export_table_to_csv / file=경로). `_build_command`는 1차 출력 기준 stub scaffolding(3-tuple 반환).
- `orchestrator._process_shell` → **`list[ComparisonResult]`**: 출력마다 compare(`shell_id`=test_id·`output_name`=label 못박음, **단일은 None**). `run_full_comparison`은 `results.extend` + 출력마다 `SHELL_DONE`. `_worst_status`로 compare STEP 표시.
- `core/reporter.py`: CSV에 **`output` 컬럼** + (shell,output) 행, `.diff`는 `{shell}_{output}.diff` 분리. `RunSummary.total`=출력 수(**D-016 합항등 유지** = ok+ng+error+missing).
- **GUI**: `gui/serialize.py` `output_name` 추가. `templates/index.html` — 셸 안 **출력별 결과 블록(`.outrow`, `data-status`)**, 헤더 배지=worst(`shellAgg`), **카드 필터를 출력 단위**(`.outrow` 필터, 보이는 출력 없는 셸 숨김), `diffHtml` 추출.
- **GUI 업로드 경로**: `gui/upload.py` `_definition_entry_from`(inputs.tables[]·outputs[] 재방출로 다중 보존), `prepare_jobs_from_definition`(정의가 참조하는 모든 입력 CSV·정답 파일 stem 매칭·배치).

### 검증 (현재 그린)
- 전체 **170 passed**(DB 통합 포함, dc-pg 5433). GUI 테스트 42.
- 하위호환: **단일 출력=N=1** → 데모 10셸 OK6/NG3/ERROR1 무회귀, 단일은 리포트 `output=-`.
- 라이브 E2E(dc-pg): 한 셸 **DB 출력 2개** → 결과 2건(`total=2`, 리포트 `001,A.csv,OK`/`001,B.csv,OK`).

---

## 3. 남은 작업 (우선순위)

### ★ T7-3. UI 경량화 (Phase 7 마무리, `[ ]`) — 1순위
회의 안: **"버튼 1개 → 자동 실행(Shell 1~1000) → 실시간 모니터링 → 결과"**. 현재 화면은 아직 Phase 6 UI(接続設定/テーブル選択/마ッピング/카드필터 등)라 회의 방향과 어긋남.
- **목표**: 매핑/연결 설정 UI를 **정의 파일 주도로 흡수**(설치 시 `config.yaml`·정의 파일에 다 있음). 화면은 정의 파일 선택(또는 고정) → 실행 버튼 → 모니터링 → 결과/리포트로 단순화.
- **주의**: 기존 GUI(접속테스트·매핑표 생성·카드필터)는 자산이니, **삭제 전 "무엇을 남기고 무엇을 흡수"를 설계 게이트로 확정**하고 진행. `src/gui/` 영역(web.py/templates)만, Core 무수정.
- DEFINITION_SPEC의 "결과 출력=화면 모니터링+CSV 리포트, 출력 단위" 그대로.

### 실전 QA (deferred였던 핵심) — 2순위
- 실데이터/실배치(stub→실 Net COBOL)로 검증. **SAM 등 확장자 파일** 입출력 실제 확인(바이트 비교라 형식 무관하나 골든 일치 확인).
- 대용량(셸 100~1000 × 다중 출력) 성능·시간(순차 실행)·DOM(diff 상한 200줄 있음).

### 기능 deferred — 3순위 이후
- **정교 비교**(숫자 공차·날짜 정규화·무시 규칙, D-022) — 통짜 바이트 false-NG 완화.
- 매핑표(long CSV: 셸×입출력 행) → 정의 생성 (현 매핑표는 단일 입출력만).
- 물리 다중 DB 접속(드묾), DB 결과 저장 테이블, HTML/Excel 리포트.
- Core/CLI/리포트 일본어화(현재 runner+stub만), 실 설치 패키징.

### 브랜치 정리
- `feat/fullschema-multi-io` → **main 머지 여부** 사용자 결정. (T7-3까지 끝내고 머지 권장)

---

## 4. 실행·환경 (그대로 재현)

- **DB**: dc-pg(postgres:16) 호스트 **5433**, `POSTGRES_PASSWORD=devpw`, db `compare_proto`. `config.yaml`은 gitignore(로컬, 포트 5433).
- **기본 스위트**: `python3 -m pytest -q` (DB 테스트 자동 skip).
- **DB 통합 포함**: `RUN_DB_TESTS=1 PGHOST=localhost PGPORT=5433 PGDATABASE=compare_proto PGUSER=postgres POSTGRES_PASSWORD=devpw python3 -m pytest -q`
- ⚠️ **DB 테스트/스모크는 `transaction_log` 시드(50건)를 오염**시킴 → 전후로 `PGPASSWORD=devpw psql -h localhost -p 5433 -U postgres -d compare_proto -f db/schema.sql`로 재시드.
- **GUI 기동**: `POSTGRES_PASSWORD=devpw GUI_PORT=8765 ./run_gui.sh` → http://127.0.0.1:8765/ (정리: `pkill -f src.gui.web`).
- ⚠️ **[[dc-env-hazard]]**: 이 환경에선 **pytest 전 commit/push**(과거 cwd rmtree 사건). 만들면 바로 commit·push.

### 다중 출력 라이브 확인(엔진) 스니펫
한 셸에 DB 출력 2개를 넣은 임시 정의로 `run_batch`(clean로 골든 생성)→`run_full_comparison` 하면 결과 2건이 나온다. (이번 세션에서 검증 완료 — 재현 시 `shell_program`은 **절대경로**로, 상대경로는 정의 파일 디렉토리 기준 해석됨.)

---

## 5. 설계 핵심 (놓치기 쉬운 것)

- **도구는 블랙박스**: 셸 내 프로그램 개수·참조 DB 수는 무관. 도구는 `program`(잡) **1회 실행** + `inputs[]` 세팅 + `outputs[]` 비교만. 최종 출력만 비교(중간 산출물 검증 X — 회의 확정).
- **DB 접속 = config 공통 1곳**(정의 미포함), 비번 env(모델A, D-019).
- **디렉토리 = config 공통, 정의엔 파일명만**. 실경로 = config dir + 파일명.
- **SAM은 파일 출력에서만** → 바이트 비교(D-004)라 SAM export 포맷터·레이아웃 **불요**. DB 출력은 항상 CSV export.
- **결과 단위 = 출력**(셸 1개에 출력 2개면 결과 2건). `RunSummary.total`=출력 수, D-016 합항등 유지.
- **하위호환 필수**: 신형 `inputs[]`/`outputs[]`와 구형 단일 정의를 **둘 다** 읽어야(로더가 정규화). 단일 출력은 `output_name=None`(리포트 `-`).

---

## 6. 자가검증 체크포인트 (T7-3 설계 전 [[dc-self-review]] 실행)

- 재사용>재구현: 기존 GUI 자산(serialize·진행 이벤트·diff 렌더) 재사용. UI 경량화가 **삭제만**이 아니라 흡수인지.
- 단일 진실: 정의 파일이 정본 — UI가 받은 값과 정의 파일이 충돌하지 않게(드리프트).
- silent drop: 다중 입력/출력 누락(파일·정답)은 명시 노출(현재 `excluded`/MISSING 유지).
- 바이트 자기일치(D-027): 출력별 골든이 같은 직렬화 경로(DB=exporter, file=배치 산출).

---

> 즉시 시작: 위 1~2장 읽고 → **T7-3 통합 설계안 보고**(무엇 남기고 무엇 흡수, 화면 흐름, 영향 파일) → 사용자 OK → 코딩. 끝에 "자가검증:" 첨부. 완료 시 D-xxx·TASKS·메모리 갱신.
