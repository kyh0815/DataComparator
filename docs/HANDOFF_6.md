# HANDOFF v6 — 팀 멀티환경 테스트 셋업(트랙1) + 사이드바·세그먼트 형제구조(트랙2)

> **현행 정본 hand-off.** HANDOFF_5(코어 C1~C7)·DEFINITION_SPEC(풀스키마)는 여전히 유효한 상위 정본.
> 이 문서는 그 위에서 **2026-06-08 이후의 작업 지시·현황**만 다룬다.
> **재작성 금지. 국소 diff만. 모듈경계 유지. 코어(비교/실행/exporter/정의 스키마/checkpoint) 무수정.**
> 모호하면 추측하지 말고 질문.

---

## 0. 새 세션 시작 시 읽는 순서
1. `docs/CLAUDE.md` (작업 규칙) → `docs/CONTEXT.md` (사업 맥락)
2. `docs/HANDOFF_5.md` (코어 C1~C7 정본) + `docs/DEFINITION_SPEC.md` (풀스키마 정본, D-033~D-036)
3. `docs/DECISIONS.md` (D-038~D-045 등) + `docs/DESIGN_TOKENS.md` (비주얼 정본: 먹네이비 #1F2937)
4. **이 문서**(HANDOFF_6) — 지금 할 일

---

## 1. 한 줄 현황 (2026-06-08)
- **브랜치**: `feat/fullschema-multi-io`. **테스트: 277 passed / 10 skipped**(회귀 0). 코어 0수정 유지 중.
- **최근 작업**: GUI 외형 다듬기(사이드바=프로젝트화·C로고·접속카드·프로필·아이콘제거·프로젝트명 인라인편집). 전부 `src/gui/templates/index.html`만 수정, 커밋됨(`112d1b1`까지).
- **미커밋 잡파일**: `config.yaml.bak`(저장 백업 부산물), `ui_screenshot/`(스크린샷). → 커밋 대상 아님. `.gitignore` 후보.
- **다음 할 일**: 아래 **트랙1 먼저 → 트랙2**.

---

## 2. ★ 수요일 목표 — 2트랙 작업 지시 (순서: 트랙1 → 트랙2)

### 공통 전제
재작성 금지·국소 diff·모듈경계 유지·277 녹색·코어 무수정. 막히거나 빨간불·코어 건드려야 하면 **멈추고 질문**.

---

### ━━ 트랙 1 — 팀 테스트 셋업 (먼저, "테스트 시작"의 필수) ━━
주니어 1년차 팀원들이 각자 자기 PostgreSQL + 자기 샘플로 e2e 돌리게 한다.
(조사 완료: report_dir 격리 ✅, config 전부 가변 ✅ — 아래 4절 근거 참조)

**1-A. 프리플라이트 DB 비번 힌트 1줄 (국소)**
- 대상: `src/core/preflight.py:268` 의 `DB 接続に失敗: {exc}` 메시지 1곳만.
- 동작: `config.database.password_env`가 가리키는 env(기본 `POSTGRES_PASSWORD`)가 **미설정이면** 그 사실 명시:
  `"DB 接続に失敗: <raw>. ※ 環境変数 <키>가 設定されていません — 設定後に再実行してください。"`
- env는 있는데 인증 실패면 **기존 raw 유지**(진짜 비번/권한 문제).
- ★범위: preflight 메시지 1곳 + 분기 테스트 1개. 비교/실행/orchestrator/exporter 무수정.
  - 참고: `src/gui/connection.py:67-72`에 이미 동일 취지의 env-미설정 hint 패턴 존재(test_connection). 같은 모양으로 맞추면 됨.
- ★언어 혼용(프리플라이트=일/ConfigError=한)은 **보류** — 좌표·경로 있어 액션 가능 + 최종 고객 日本이라 결국 일본어 통일이 정답. 지금 건드리지 말 것(별도 언어정책 결정).

**1-B. 셋업 README (`TEAM_SETUP.md`, 주니어가 따라하면 끝나는 한 장)**
- 위치: 레포 루트(또는 `samples/complete/` 옆).
- 절차(필드별 예시까지, 막힘없게):
  1. `cp config.yaml.example config.yaml`
  2. config.yaml 채우기 — `database`(host/port/dbname/user) + `paths`(asis_input/output·tobe_output·definition_file + **report_dir 필수**) + `encoding`. 필드별 한 줄 설명+예시값.
  3. **결과 격리**: 팀원마다 `report_dir` 다르게(예: `/home/<이름>/reports`). 안 그러면 결과·checkpoint 섞임.
  4. **`export POSTGRES_PASSWORD=...`** (config 평문 금지, env). `password_env` 키 이름 명시.
  5. 실행: `samples/complete/run_demo.sh` 또는 GUI(`./run_gui.sh`, port). e2e 한 바퀴(프리플라이트→실행→試験成績書) 확인.
  6. 막히면: 프리플라이트 에러의 경로·필드를 읽고 고쳐라(`ファイルがありません`/`書き込めません`/`接続に失敗` 등).
- ★README는 "현재 config 구조" 기준. 첫 실배치에서 구조 바뀌면 README만 갱신(폼이 아니라 README라 가능).

**트랙1 완료 기준**: 깨끗한 환경에서 README만 보고 셋업 → e2e 완주 재현. 277+ 녹색.

---

### ━━ 트랙 2 — 사이드바(A) + 세그먼트 복원 (그다음) ━━
★전제: **화면(템플릿/뷰/CSS) + config 선택 라우팅만.** 라우트 핸들러의 비교/실행/정의 로직·스키마·checkpoint 무수정.

**현재 상태(6점 조사 결과 — 이미 된 것/남은 것 명확):**
- 2-A(사이드바=프로젝트)·2-C(세그먼트=기능 탭 복원)·중복해소 = **이미 됨**(커밋 `45d3dd8` "형제 구조").
  - 사이드바: 接続環境 카드 → プロジェクト 목록(2개: `サンプル demo`, `本番`) → 프로필. 클릭=config 전환 실동작, 더블클릭=改名(localStorage).
  - 상단 탭: `Mapping · Execution · Artifacts · Quarantine · Project Settings` — 전부 실제 내용 있음(빈 껍데기 없음).
- **남은 실작업 2건:**

**2-B. config 선택 단일 진입점 (단일만 구현, 미래 멀티 대비)** — ☐ 미완
- 현재: 소스는 단일(`#config` hidden select)이나 **읽는 곳이 산발** — JS `$("config").value` ~10곳(preflight/run/evidence/paths/groups/definition/report), web.py `request.args.get("config") or "./config.yaml"` ~7곳(web.py:100·122·170·183·229 등).
- 할 일: "활성 config를 고르는 지점"을 **단일 함수/레이어 한 곳**으로 수렴(JS 1 accessor + 서버 1 helper). 지금은 **단일 config만** 본다.
- ★멀티 스캔 구현 금지(보류). 확장 가능한 모양으로 두기만, 기능은 단일. (과설계 아님 — 단일 가정을 한 점에 모으는 것뿐.)

**2-D. 각 탭 내부 = §11 세로 흐름 — ☐ 방향 결정 필요(상충 지점)**
- 현재: §11 체인이 **3탭에 분리** — 接続設定=Project Settings 탭, ①定義=Mapping 탭, ②事前点検·③検証実行·④結果=Execution 탭. (Execution 탭 안의 ②→③→④는 세로 아코디언+게이트로 이미 동작: run은 preflight 통과 전 disabled.)
- 2-D 지시 원문: Execution 탭 안에 접속設定(접힘)→①定義→②点検→③実行→④結果 **한 흐름**으로.
- ★**상충**: 현재 "기능=탭"(定義=Mapping, 接続=Settings)이 형제구조와 자연스럽게 맞물려 있는데, 2-D는 이를 Execution 한 탭으로 다시 모으라는 것 → 형제구조와 부분 상충.
- → **새 세션에서 사용자에게 먼저 확인할 것**: (a)현행 탭 분리 유지(형제구조 우선) vs (b)Execution 한 탭에 §11 전체 흐름 수렴(2-D 원문). **추측 말고 질문.**

**트랙2 완료 기준**: 사이드바=프로젝트/상단=기능 형제구조(됨). 단일 config 자연 동작(2-B). 빈 탭 없음(됨). 277 녹색. 코어 0수정.

**★시간 부족 시 트랙2 우선순위**: ①외곽(됨)+Execution 탭 §11 세로흐름 e2e가 진짜 도는 것 > ②나머지 탭 표시. "다 채우려다 아무것도 안 도는 것보다, 외곽+Execution 한 탭이 진짜 도는 게 데모에서 이김."

---

## 3. 절대 규칙 (KEEP / 금지)
- **KEEP**: 모듈 분리(loader/runner/comparator/orchestrator/paths/evidence/store/web), Core/Interface 분리(Core print 금지·구조화 반환), 결정론적 비교(LLM 금지), 설정 코드 바깥(config.yaml), 모델A(비번=env, config 평문 금지).
- **무수정 코어**: `src/core/*`(comparator·runner·orchestrator·paths·evidence·store·preflight*·models), `src/config/definition.py`(스키마), checkpoint. *단 1-A는 preflight.py 메시지 1곳 + 테스트만 허용(지시된 국소 예외).*
- **금지**: 재작성, 멀티 Task 혼합 커밋, 빈 탭(신뢰 즉사), 멀티프로젝트 스캔 구현(보류), 생성 폼/CRUD(보류 — 새 프로젝트=config 파일 추가 방식).

---

## 4. 트랙1 근거 — 조사 완료 사실(코드 위치)
- **결과 격리 ✅**: checkpoint = `report_dir/checkpoint.jsonl`(`src/core/store.py:37`). report_dir=config.paths.report_dir(필수, `settings.py:69`). orchestrator가 checkpoint·리포트·試験成績書·diff 전부 `config.report_dir` 하위에 씀(`orchestrator.py:70·94`). → 팀원마다 report_dir 다르면 완전 격리. CLI `--report-dir` override도 있음(`main.py:101`).
- **config 전부 가변 ✅**: encoding / paths(asis_input·output, tobe_output, report_dir 필수, tobe_input·definition_file 선택) / database(host·port·dbname·user 필수, **password_env가 가리키는 env에서 비번**) / batch(+groups) / shells. (`settings.py:63-91`, `_build_database`)
- **에러 친절도**: 프리플라이트=좌표+경로/필드 단위(액션 가능). 약점=DB 실패 raw + **POSTGRES_PASSWORD 미설정 미명시** → 이게 1-A로 보완.

---

## 5. 실행/검증 방법 (재현)
```bash
# 테스트(현재 277 passed / 10 skipped)
python3 -m pytest -q

# GUI 띄우기 (Flask non-debug → 템플릿 수정 후 반드시 서버 재시작)
lsof -ti tcp:8000 | xargs -r kill
POSTGRES_PASSWORD=devpw GUI_PORT=8000 nohup ./run_gui.sh >/tmp/dc_gui.log 2>&1 &
# → http://127.0.0.1:8000/  (브라우저 ⌘+Shift+R로 캐시 무시)

# 데모 e2e
cd samples/complete && ./run_demo.sh
```
- **데모 DB**: docker `dc-pg`(port 5433, user=postgres, **password=devpw**, db=compare_proto). 죽었으면 `docker start dc-pg`.
- **정본 샘플**: `samples/complete/`(20 CK, OK17/NG3/MISSING1). 빈 템플릿 `definition_template.csv`(UTF-8 BOM).

---

## 6. 진행 절차 (새 세션)
1. **트랙1-A**(preflight 비번 힌트 1줄 + 테스트 1개) → 277+ 녹색 확인 → 커밋.
2. **트랙1-B**(`TEAM_SETUP.md` 작성) → 깨끗한 환경 재현 점검 → 커밋.
3. **트랙2-D 방향을 사용자에게 질문**(탭 분리 유지 vs Execution 단일 흐름) → 답 받고 진행.
4. **트랙2-B**(config 단일 진입점 수렴) → 화면/라우팅만, 코어 0 → 커밋.
5. 각 단위 별개 커밋. 끝에 **STATE_REPORT 갱신**(277+·TEAM_SETUP·2-B/2-D 반영).
- 코어 건드려야 하거나 277 빨간불이면 멈추고 질문.

---

## 7. 미결정/보류 (나중)
- **2-D 방향**(위 6.3) — 사용자 확인 대기.
- 언어 통일(최종 일본어) — 별도 정책 결정.
- 멀티프로젝트(여러 config 스캔·전환) — 첫 실배치 후.
- 생성 폼/CRUD, D-041② encoding/has_header/delimiter 전역화, checklist_to_template.py 명명 — 보류.
- 첫 실배치·실데이터 투입(SAM·대용량 QA) — 진짜 검증.
