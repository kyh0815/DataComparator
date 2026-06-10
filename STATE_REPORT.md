# STATE_REPORT.md

> 현재 상태 있는-그대로 보고(읽기 전용). 작성 시점 기준 파일에 실제로 존재하는 것만 기록.
> 코드 수정 없음. 불확실한 것은 "불확실"로 명시.

> **2026-06-10 갱신(요지 — 이 블록이 최현행. 아래는 과거 스냅샷)**
> - 테스트 **293 passed / 10 skipped**(회귀 0). 브랜치 `feat/qa-mapping-guards`(미푸시), base=main `195dc1d`. 코어=models.py repr 1줄만(승인).
> - **HANDOFF_7 J(직전 변경분 D-046~048 적대적 검토)** → 매핑도구 **silent-drop/collision 3건** 발견·수정
>   (**D-049**, 코어 밖 `tools/mapping_to_definition.py`만 + 테스트 6건). ① sam+명시 compare_mode 강등 시 vsam과 동일
>   경고(무경고였음) ② xlsx 다중/비활성 시트 silent-drop → 데이터 시트 탐색+다중시 loud 에러 ③ 셸 내 동일 To-Be
>   출력경로 충돌 → 에러(덮어쓰기 검증손실 방지).
> - **HANDOFF_7 H(보안/온프레미스 감사)** 1차(**D-050**): 핵심 견고 확인(외부 네트워크 0·shell=True 0·GUI 비번 env만·
>   config 평문 비번 미기록). 수정 3건 — ① 코어 `DatabaseConfig.repr` 비번 차단(`field(repr=False)`, 사용자 승인)
>   ② docs `devpw` 평문 → env 참조 ③ `config.yaml.bak`/`.tmp`·`ui_screenshot/` .gitignore.
> - **정상 확인(발견 아님)**: io/kind 별칭 우선순위, in_encoding·setup 로더 도달, 빈 xlsx 거부, `;`시퀀스 거부, 파일출력 idx 분리.
> - **수동 QA 회귀 발견·수정(D-051)**: GUI `/`에 complete_sample 업로드 시 `RangeError: Maximum call stack`
>   — `index.html`의 `activeConfig`가 자기호출 무한재귀(b1bf0a7 혼입)로 **2026-06-08 이후 메인 화면 config 의존
>   동작 전부 깨져 있었음**. `#config` 셀렉터 값 반환으로 수정 + 정적 가드 테스트(서버 test_gui는 JS 미실행이라 놓침).
> - **検証フロー 재설계 1단계(D-054)**: "실행 후 자리 비워도 와서 보면 끝나있다"를 위한 백엔드. `src/gui/run_manager.py`
>   (전역 RunManager=락+RunState, run_full_comparison을 백그라운드 데몬 스레드로 감쌈) + `POST /run/start`·`GET /run/status`.
>   §0 버그1(락 조기해제) 수정·구 /run SSE 락 단일화(조건1)·워커 예외 안전(조건2)·started/finished_at(조건3).
>   코어/기존 엔드포인트 무수정. **2단계(D-055)**: 상태머신 패널 병존 + /run/resumable. **3단계(D-056)**: 상태머신 정식 승격·구 아코디언/Artifacts/Quarantine 제거(검証フロー+Settings 2세그먼트). node --check JS 검증. 300 passed.
> - **GUI 자동 흐름 복원(D-052)**: 원래 비전(Mapping→Execution→결과 자동 E2E) — 점검·실행이 별도 탭 수동 2버튼
>   이던 것을 **단일 `一括実行` 버튼**(점검 자동→0에러면 실행→결과/성적서 연쇄, 점검은 안전게이트 유지)으로.
>   Mapping 저장 직후 'このまま一括実行' CTA로 한 흐름. 코어/엔드포인트 무수정(인터페이스 wiring). 동반: 저장 CRLF 정규화.
> - 커밋 10개(브랜치): J·docs·gitignore·repr·hygiene·D-050·GUI회귀fix·D-051·칩제거·**一括実行+CRLF**·D-052.
>   **다음**: F(에러/엣지) 또는 J 잔여(DB 데모 e2e). GUI는 8080에서 기동 중(`POSTGRES_PASSWORD=devpw`).

> **2026-06-08 갱신(요지 — 아래 2026-06-07·§0~§7은 과거 스냅샷)**
> - 테스트 **278 passed / 10 skipped**(회귀 0). 코어(비교/실행/exporter/정의 스키마/checkpoint) **0수정** 유지.
> - **트랙1-A**(`1869900`): preflight DB 접속 실패 시 `password_env`(기본 POSTGRES_PASSWORD) 미설정이면 그 사실 1줄 명시.
>   env 있는데 실패면 raw 유지. `preflight.py:_check_db` 1곳 + 분기 테스트 1개(지시된 국소 예외).
> - **트랙1-B**(`9ed3828`): 루트에 `TEAM_SETUP.md` — 팀원 1인 셋업 한 장(cp example→config 필드별→report_dir 격리
>   →POSTGRES_PASSWORD env→CLI/GUI e2e→프리플라이트 에러 트러블슈팅). 코드 메시지와 대조 확인.
> - **트랙2-D**(결정): §11 흐름을 **현행 탭 분리 유지**(형제구조 우선)로 확정 — Execution 단일 흐름안은 보류/종결. 코드 변경 없음.
> - **트랙2-B**(`b1bf0a7`): config 선택을 **단일 진입점**으로 수렴. 서버 `_active_config()`(산발 7곳)·클라
>   `activeConfig()`(읽기 11곳). 멀티 스캔은 미구현(보류, 확장 지점만). 화면/라우팅만, 코어 0. GUI 스모크 통과.
> - 사이드바=프로젝트(2-A)·세그먼트 기능탭(2-C)·중복해소는 이전 세션(`45d3dd8`)에 이미 완료.

> **2026-06-07 갱신(요지 — 아래 §0~§7은 과거 스냅샷)**
> - 테스트 **269 passed / 10 skipped**.
> - 샘플셋 **단일화**: 정본 데모셋 = **`samples/complete/`** (정의 정본 `complete_sample.csv`, 한 방 진입점 `run_demo.sh`).
>   20 CK e2e 검증(출력단위 21: OK17/NG3/MISSING_TOBE1). 구 픽스처(`samples/asis`·`realtest`·`rehearsal`·`realistic`) 삭제.
> - **`config.yaml` = 데모 아님, 실배포 환경설정의 자리**(GUI「本番」). 데모는 `samples/complete/`로 분리.
>   커밋된 배포 템플릿 = **`config.yaml.example`**(+ `test_definition.template.yaml`); 루트 `config.yaml`은 **gitignore(로컬)**.
> - DB CK(019/020) e2e **재현 정보**: dc-pg **포트 5433** · 자격(user/db/pw)은 **컨테이너 env·`password_env` 참조**(★레포에 평문 금지) ·
>   기본 스위트는 **DB-free**, DB 검증은 **`RUN_DB_TESTS=1` 게이트** 뒤. 스키마 = `db/schema.sql`+`db/schema_realistic.sql`.
> - 도구 보강: `mapping_to_definition`이 shell `;`(1:N) 거부 + 선두 `#` 주석 허용. shell_group 칼럼 + `batch.groups` lint(runner 미연결).

---

## 0. 기본 사실 (명령 출력)

### 디렉토리 트리 (`.git`/`__pycache__`/`out`/`.pytest_cache` 제외, 요약)
```
src/__init__.py  src/cli/{main.py,output.py}  src/config/{definition.py,settings.py}
src/core/{comparator.py,exporter.py,loader.py,models.py,orchestrator.py,paths.py,reporter.py,runner.py}
src/gui/{connection.py,serialize.py,upload.py,web.py, templates/{index.html,define.html}}
stub_batch/{_stub_common.py,run_batch_db.py,run_batch_file.py,run_settlement.py}
tools/{checklist_to_template.py,make_golden.py,make_realistic_samples.py,make_samples.py,mapping_to_definition.py}
db/{schema.sql,schema_realistic.sql}
tests/ (19개 test_*.py)  docs/ (16개 md)
test_definition.yaml  test_definition.realistic.yaml  test_definition.template.yaml
config.yaml  config.realistic.yaml  config.yaml.example  .config.realistic.effective.yaml
samples/complete/{complete_sample.csv,config.yaml,test_definition.yaml,make_complete_data.py,make_db_golden.py,run_demo.sh,README.md,mock_linux/...,asis/...,tobe_src/...}
run.sh  run_gui.sh  requirements.txt
(※ 위 트리는 과거 스냅샷. 현행: samples/asis·realistic·realtest·rehearsal·run_realistic.sh·config.realistic.yaml·test_definition.realistic.yaml 삭제, samples/complete 단일화 — 갱신줄 참조)
```

### 언어/프레임워크/진입점/의존성
- 언어: Python (`python3 --version` → **Python 3.9.6**). `package.json` **없음**.
- 진입점(실제 명령):
  - CLI: `run.sh` → `exec python -m src.cli.main "$@"`
  - GUI: `run_gui.sh` → `exec python3 -m src.gui.web "$@"`
  - 현실형 데모: `run_realistic.sh`(psql 스키마 적용 → 샘플 생성 → make_golden → `python3 -m src.cli.main`)
- 의존성(`requirements.txt`): `psycopg2-binary>=2.9`, `pyyaml>=6.0`, `flask>=3.0`(GUI 전용), `pytest>=8.0`, `black>=24.0`

### 파일별 라인 수 (`wc -l`, 발췌)
```
src/cli/main.py 102   src/cli/output.py 160
src/config/definition.py 220   src/config/settings.py 214
src/core/comparator.py 101  exporter.py 73  loader.py 120  models.py 244
src/core/orchestrator.py 243  paths.py 68  reporter.py 110  runner.py 132
src/gui/web.py 292  connection.py 140  serialize.py 55  upload.py 56
stub_batch/_stub_common.py 229  run_batch_db.py 34  run_batch_file.py 37  run_settlement.py 132
tools/mapping_to_definition.py 300  checklist_to_template.py 102  make_golden.py 102
src 합계 약 1900줄, tests 합계 2972줄
```

### 테스트 (읽기전용 실행)
```
python3 -m pytest -q  →  269 passed, 10 skipped   (※ 과거 스냅샷엔 180 — 현행 269)
```
(skip 10건은 DB 통합 테스트 — `RUN_DB_TESTS=1` 미설정 시 자동 skip)

---

## 1. 정의파일 계약

**중요: 정의파일은 2종이 존재한다.**
- (A) **YAML**(`test_definition.yaml`) — 오케스트레이터가 **실제로 읽는** 실행 정본. 로더 `src/config/definition.py:load_definitions`.
- (B) **매핑 CSV**(정본 = `samples/complete/complete_sample.csv`) — 사람이 채워 (A)로 변환하는 입력. 변환 도구 `tools/mapping_to_definition.py`. 오케스트레이터는 CSV를 직접 읽지 않음.

### 1-A. YAML 로더가 실제로 읽는 키 (코드 추출, definition.py)
- 최상위: `tests`(리스트, 필수) — `load_definitions` L46-51
- test 항목별 (`_build_definition` L61-85): `test_id`(필수), `test_name`(선택), `input`(블록 필수), `execution`(블록 필수)
- `input` (`_build_inputs` L133-170): 신형 `input.tables[]`(각 `csv`필수·`type`·`table`·`dest_dir`·`src_dir`·`dest_name`) / 구형 단일 `input.{type,csv,table,dest_dir,src_dir,dest_name}`
- `execution`: `shell_program`(필수), `timeout`(선택, 기본 60)
- `output(s)` (`_build_outputs` L90-130): 신형 `outputs[]`(각 `type`·`expected`필수, `table`·`export_as`·`file`·`name`·`expected_dir`·`tobe_dir`) / 구형 단일 `output.{type,table,export_csv,file}`+최상위 `expected_output_csv`
- **읽되 무시되는 키**: docstring L6 "comparison_rules·success_criteria·parameters 등 … 읽되 무시한다(자리만 유지)". (코드에서 이 키들을 참조하는 곳 없음 — 확인됨)

### 1-B. 매핑 CSV 도구가 실제로 읽는 컬럼 (mapping_to_definition.py)
```
L69 _KEY_COLS = ("checklist", "shell_id")   # 둘 중 하나 필수(checklist 우선)
L70 _REQUIRED_COLS = ("kind", "type")
L99  sid  = row.get("checklist") or row.get("shell_id")
L100 kind = row.get("kind"); L101 itype = row.get("type")
L117 prog = row.get("shell") or row.get("program")
L120 test_name  L122 timeout  L125 file  L126 table  L143 expected  L149 name
L135 입력 선택열: dest_dir, src_dir, dest_name
L151 출력 선택열: expected_dir, tobe_dir
```
→ 읽는 컬럼 전체: `checklist|shell_id, kind, type, shell|program, table, file, expected, name, test_name, timeout, src_dir, dest_dir, dest_name, expected_dir, tobe_dir`

### 행 그룹화 / 다중 input 지원 (코드 근거)
- 매핑 CSV: 같은 `checklist` 값 행들을 한 셸로 묶음 — `shells[sid]["inputs"].append(...)` / `["outputs"].append(...)`.
- YAML: `input.tables[]` 리스트 → `inputs` 리스트.
- **한 체크리스트에 input 여러 개 = 지원됨.** 근거: orchestrator `_load_step` L140 `for spec in definition.inputs:` (전건 루프 적재).

### 검증 로직 / 빈칸 자동보정
- 검증: `definition.py:_validate_io` L173-188 — input=database면 `table` 필수, output=database면 `table`+`export_as` 필수, output=file이면 `file` 필수, 모든 output `expected` 필수.
- 빈칸 자동보정: `mapping_to_definition.py:_autofill_names`(존재) — 빈 `file`/`expected`를 규칙으로 채움(입력 1개면 `{sid}.csv`, 여러개면 `{sid}_{table}.csv` 등). YAML 로더 자체에는 자동보정 없음(필수 누락 시 에러).

### 파서 핵심 시그니처
```python
# src/config/definition.py
def load_definitions(path: Path) -> list[ShellDefinition]:          # L32
def _build_definition(entry, idx, path) -> ShellDefinition:         # L56
def _build_inputs(inp, test_id, path) -> list[InputSpec]:           # L133
def _build_outputs(entry, test_id, path) -> list[OutputSpec]:       # L90
def _validate_io(d: ShellDefinition, path) -> None:                 # L173
# tools/mapping_to_definition.py
def mapping_to_definition(csv_text: str) -> dict:   # {ok,yaml,count,shells,errors}  L72
```

### 샘플 정의파일 헤더(매핑 CSV, 그대로)
```
checklist,test_name,kind,type,shell,file,table,expected,name,src_dir,dest_dir,dest_name,expected_dir,tobe_dir,timeout
```
구형 YAML 데모(`test_definition.yaml`) 첫 항목: `test_id/input{type,table,csv}/execution{shell_program,timeout}/output{type,table,export_csv}/expected_output_csv` + `comparison_rules:{type: byte_exact}`(무시됨).

---

## 2. Executor 경계 (가장 중요)

### 분리 여부 / 추상화
- 오케스트레이션(`orchestrator.py`)과 환경 종속 실행(loader/runner/exporter/comparator)은 **파일(모듈) 단위로 분리**돼 있음.
- **단, 인터페이스/추상클래스 없음.** orchestrator가 **구체 함수를 직접 import**:
  `from .loader import copy_input_file, load_input_csv` / `from .runner import run_batch` / `from .comparator import compare_files`.
- DB는 **psycopg2/PostgreSQL에 하드 고정**, 쉘 실행은 **subprocess 고정**. "Executor 인터페이스"라 부를 추상화는 **불확실/없음**.

### 4개 동작 코드의 실제 시그니처·위치
```python
# ① 입력 적재
src/core/loader.py:44   def load_input_csv(csv_path, conn, table_name, encoding="shift_jis") -> int   # TRUNCATE+executemany
src/core/loader.py:27   def copy_input_file(csv_path, dest_dir, dest_name=None) -> Path               # shutil.copyfile
   호출: orchestrator.py:144 load_input_csv(...) / :149 copy_input_file(...)
# ② 배치 실행
src/core/runner.py:38   def run_batch(definition, config, conn=None, *, clean=False) -> list[tuple[OutputSpec, Path]]
   실행: runner.py:56  subprocess.run(argv, env=env, capture_output=True, text=True, timeout=timeout)
# ③ 출력 추출(DB→CSV)
src/core/exporter.py:28 def export_table_to_csv(conn, table_name, output_path, encoding="shift_jis", columns=None) -> Path
   호출: runner.py:78  export_table_to_csv(conn, out.table, tobe, ...)   # type=database 출력만. file 출력은 추출 없이 경로 그대로
# ④ 비교
src/core/comparator.py:20 def compare_files(asis_path, tobe_path, encoding="shift_jis") -> ComparisonResult
   호출: orchestrator.py:115 compare_files(asis_path, tobe_path, ...)
```

### 한 곳에 모였나 / 흩어졌나
- DB 코드: `loader.py`(적재) + `exporter.py`(추출) **2개 파일에 분산**. 쉘 실행: `runner.py`. 비교: `comparator.py`. 경로 조립: `paths.py`. → 관심사별 모듈 분리, 단일 "executor" 진입점은 없음.

### 실제 동작 코드인가 / stub인가
- **loader/runner/exporter/comparator = 실제 동작 코드**: psycopg2로 실제 PostgreSQL에 TRUNCATE+INSERT/SELECT, subprocess로 실제 실행파일 호출, 실제 파일 바이트 비교. (DB 통합 테스트가 `RUN_DB_TESTS=1`에서 검증)
- **호출되는 "배치" 자체 = stub**: `stub_batch/run_batch_db.py`·`run_batch_file.py`·`run_settlement.py`는 가짜 배치(HANDOFF에 "🔁 진짜 배치로 교체" 명시). DB 종류는 **PostgreSQL 한정**(다른 DBMS 코드 없음 — 불확실하지 않음, 없음).
- 즉 **실행 프레임워크는 실제, 실행 대상(배치)·DB드라이버 범위(Postgres)는 데모/한정**.

---

## 3. 상태·실시간 진행 모델

### 상태머신 / 상태 목록
- 셸 단위 "상태머신" 클래스는 **없음**. 대신 결과 상태 enum과 진행 이벤트 enum이 있음.
- 결과 상태 `ComparisonStatus`(models.py L14): `OK, NG, MISSING_ASIS, MISSING_TOBE, ERROR`
- 진행 이벤트 `ProgressKind`(models.py L73): `SHELL_START="shell_start", STEP="step"(load/run/compare), SHELL_DONE="shell_done"`

### 실시간 전송 방식
- **SSE** (Server-Sent Events). 코드 근거:
  - web.py:165 `return Response(stream(), mimetype="text/event-stream")`
  - web.py:265 `_sse(payload)` → `f"data: {json...}\\n\\n"`
  - index.html:628 `es=new EventSource("/run?"+params...)` / :629 `es.onmessage=(e)=>{...handleMsg(m)}`
- WebSocket/polling: 없음.

### end-to-end 연결 여부 (양쪽 코드 위치)
- 서버측: orchestrator가 `on_progress(ProgressEvent)` 콜백 호출 → web.py worker(L136-151)가 `events.put({"type":"progress", **event_to_dict(e)})` → 큐에서 꺼내 `_sse`로 yield(L159).
- 직렬화: `serialize.py:event_to_dict`(shell_id 등)·`result_to_dict`(shell_id/output_name).
- 화면측: index.html:629 `EventSource.onmessage` → `handleMsg(m)`.
- → **end-to-end 연결됨**(서버 emit → SSE → 브라우저 수신). CLI 경로는 `cli/output.py`가 같은 콜백을 터미널로 렌더.

---

## 4. 비교기 계약

- 지원 비교 모드: **바이트(통짜) 비교 1종만.** comparator.py:51 `if asis_bytes == tobe_bytes: ... OK`, 불일치 시 `_extract_diff_lines`로 `\n` 기준 **위치별** 줄 대조.
- 항목별 지원 여부(코드 근거: comparator.py에서 grep, 결과 "없음"):
  - key 정렬: **없음**(비교기). ※단 `exporter.py:48`은 export 시 `ORDER BY 1..N`(컬럼 순서) 적용 — 비교기가 아니라 추출 단계.
  - encoding: **표시용 디코드만** 지원(comparator.py:24 docstring "판정은 바이트", `_decode_for_display`). 판정에는 미사용.
  - mask(컬럼 무시): **없음**
  - tolerance(공차): **없음**
  - 고정길이 layout(reclen/copybook): **없음**
- 비교 로직 분리: `comparator.py`(비교)와 `runner.py`(배치 실행)는 **별도 파일로 분리**됨. 비교기는 배치/DB를 import하지 않음(파일 경로 2개만 받음).

```python
# comparator.py:72  위치 기반 줄 대조(키 정렬 아님)
asis_raw_lines = asis_bytes.split(b"\n"); tobe_raw_lines = tobe_bytes.split(b"\n")
for index,(a_line,b_line) in enumerate(zip_longest(asis_raw_lines, tobe_raw_lines, fillvalue=None)):
    if a_line == b_line: continue
    diffs.append(DiffLine(line_number=index+1, ...))
```

---

## 5. 격리·재개

- 한 셸 실패가 전체를 죽이는가 → **죽이지 않음.** orchestrator `_process_shell` L121-127:
```python
except Exception as exc:  # noqa: BLE001 — 어떤 셸 오류도 ERROR로 흡수
    _emit_step(..., step, "ERROR")
    return [ComparisonResult(shell_id=definition.test_id, status=ComparisonStatus.ERROR, error_message=str(exc))]
```
  → 셸별 try/except로 ERROR 결과 1건 반환 후 다음 셸 계속. 단 **치명적 오류는 전체 중단**: DB 접속 실패는 `_open_connection_if_needed`에서 `OrchestratorError`(fatal), 정의 파일 누락도 fatal(`_load_definitions`).
- checkpoint / resume(중단 지점 재개): **없음**(`grep -rni "resume|checkpoint|재개|restart" src/` → 없음).

---

## 6. 결합 냄새 (발견 위치 명시)

- **runner._build_command 가 stub 인자 규약에 결합** (runner.py:83-126): Core인 runner가 stub CLI 계약을 알고 있음 — `--shell-id/--output-type/--output-path/--output-table/--input-table/--input-file/--db-host...`. 또한 **하드코딩 데모 값**: L106 `definition.input_table or "transaction_log"`(없을 때 데모 테이블명으로 폴백). → 환경/도메인 상수가 Core에 박힌 지점.
- **배치 도메인 로직은 stub_batch/에 격리됨**(Core 아님): `run_settlement.py` `_join_master`(L66)·`_summarize`(L76)는 머지/집계 업무 로직이지만 **stub(가짜 배치) 안**에 있음 — 교체 대상 위치라 의도된 것. comparator/runner Core에는 머지/집계 도메인 로직 **없음**.
- input/output 혼동: 명확한 혼동 코드 **발견 못함**(불확실 — 전수는 아님). orchestrator는 inputs[]/outputs[]를 분리 처리.
- 환경 종속 상수: encoding 기본 `"shift_jis"`(comparator/loader/exporter 시그니처 기본값, config로 override), DB접속 기본값은 `_stub_common.build_common_parser`의 `os.environ.get("PGHOST"...)`(stub측), runner의 `"transaction_log"` 폴백(위). 경로/DB접속의 정본은 `config.yaml`(settings.py)로 외부화됨.
- "배치가 무엇을 하는지 이해하려 한 흔적": Core(comparator/runner/orchestrator)에서는 **발견 못함**(배치 출력만 비교, 내부 미해석). 머지/집계는 stub_batch 내부에만 존재.

---

## 7. 불확실성 (솔직)

- **"Executor 추상화 인터페이스"**: 명시적 인터페이스/ABC는 못 찾음 — 모듈 함수 직접호출 구조로 보임. "추상화가 의도적으로 없는 것"인지 "미구현"인지는 코드만으론 **불확실**(설계 문서 D-006/ARCHITECTURE는 'Core/Interface 분리'를 말하나 실행기 추상화와는 다른 축).
- **정의파일 이원화**(YAML 정본 vs 매핑 CSV)로 인해, "정의파일 계약"이라는 단어가 두 스키마를 가리킴 — 이 보고서는 둘 다 적었으나, 운영에서 어느 쪽을 정본으로 둘지는 코드만으론 단정 불가(YAML이 로더의 입력인 것은 확실).
- **DB 통합 동작**은 이 보고 시점에 `RUN_DB_TESTS` 없이 돌려 **10건 skip**됨 → DB 경로(적재/추출/트랜잭션 경계)의 런타임 동작은 단위 mock·과거 기록 기반이며 **이번 보고에서 직접 재실행 검증 안 함**(불확실).
- **`comparison_rules`/`success_criteria` 등 YAML 필드**: 로더가 읽되 무시한다고 docstring에 적혀 있고 참조 코드를 못 찾았으나, 전 코드 grep까지는 안 함 → "완전 미사용"은 **거의 확실하나 100%는 불확실**.
- **빈칸 자동보정 정확한 규칙**: `_autofill_names` 존재는 확인, 세부 분기(파일출력 확장자 등)는 전부 추적 안 함 — 일부 **불확실**.
- 알려진 한계(문서에 기재된 것, 코드와 일치): 통짜 바이트 비교의 false-NG 가능성, `--clean`(골든 생성)은 CLI 미노출(`tools/make_golden.py` 전용), 정교비교(공차·mask·layout) 미구현(deferred).
- **장기 운영 보류(C5 checkpoint)**: `report_dir/checkpoint.jsonl`은 append-only라 run마다 누적 성장한다(읽을 때 last-wins fold라 기능엔 무해). 1000건×다회 장기 운영에서 파일이 커지면 fold 후 재기록(compaction)으로 압축 가능 — 현재는 보류(E 항목), 필요 신호 오면 추가. (store.py 상단에도 동일 주석)
