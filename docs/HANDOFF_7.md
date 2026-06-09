# HANDOFF v7 — QA Iteration → 실 PRD 배포급 품질

> **현행 정본 hand-off.** HANDOFF_5(코어 C1~C7)·DEFINITION_SPEC(풀스키마)·MAPPING_SPEC는 여전히 상위 정본.
> 이 문서는 그 위에서 **2026-06-09 이후의 목표·현황**을 다룬다.
> 목표는 **프로토/데모 → 실 고객(일본 메인프레임→리눅스 마이그레이션 배치 출력 동등성 검증) 배포 가능 품질**.
> "돌아간다"가 아니라 **"실 배치·실 데이터·실 운영에서 신뢰할 수 있다"** 가 합격선.
> **코어 무수정 원칙·게이트형(보고→OK→코딩)·테스트 녹색.** 모호하면 추측 말고 질문.

---

## 0. 새 세션 시작 시 읽는 순서
1. `docs/CLAUDE.md`(작업 규칙) → `docs/CONTEXT.md`(사업·도메인 맥락 — 왜/누구를 위한지)
2. `docs/HANDOFF_5.md`(코어 C1~C7 정본) · `docs/DEFINITION_SPEC.md`(풀스키마) · `docs/MAPPING_SPEC.md`(매핑 CSV 칼럼)
3. `docs/DECISIONS.md` — 특히 **최신 D-038~D-048**
4. `STATE_REPORT.md` · `TEAM_SETUP.md` · 자동 로드되는 메모리(MEMORY.md)
5. **이 문서**(HANDOFF_7) — 지금 할 일

---

## 1. 한 줄 현황 (2026-06-09)
- **`origin/main` = `ce3d1e5`** (feat/fullschema-multi-io 머지 완료, **public repo** `github.com/kyh0815/DataComparator`, 팀 공유 시작됨).
- **286 passed / 10 skipped**. **코어 무수정** 원칙 유지 중.
- 정본 데모셋 = `samples/complete/` (24 CK: 파일 22 + DB 2 / byte·text·record·SAM·VSAM·N:M·dir override). `run_demo.sh` 한 방 e2e = **출력 27 / OK 22 · NG 4 · MISSING 1**.
- **접속 단일 진실 = `config.yaml`의 `database` 블록**(host/port/dbname/user, 비번만 env). run_demo의 psql까지 config에서 읽음. 팀원은 config 편집 + `createdb` + `POSTGRES_PASSWORD`로 자기 로컬 e2e.
- 매핑표 작성 = **엑셀 템플릿 `definition_template.xlsx`**(전 셀 텍스트서식 잠금 — 선두0·layout 안 깨짐) + **`.xlsx 직접 읽기`**(`mapping_to_definition.read_mapping_bytes`). CLI·GUI 모두 CSV/xlsx 수용.
- 직전 세션 작업: D-046(매핑 칼럼 `db_or_file`→`type`)·D-047(SAM/VSAM = 매핑도구가 record+layout[+key]로 컴파일, 코어무수정, VSAM=KSDS 가정)·D-048(매핑 칼럼 As-Is/To-Be 리네임 `file→input/to_be_output`·`expected_output→as_is_output`·`*_dir` 통일 + `dest_*` 표면제거, 엑셀 지원)·config 단일진실·TEAM_SETUP.
- **Self QA(fresh clone e2e) 통과**: GitHub main clone → pip → pytest(286) → config 편집 → run_demo(27) / 엑셀 round-trip / silent-drop·CSV↔YAML 드리프트 0.

---

## 2. PRD 갭 — QA가 공략할 영역 (핵심 작업 목록, 우선순위 매겨 진행)
- **A. 실 배치 연동**: stub(`stub_batch/`) → 진짜 Net COBOL 배치를 `config.batch.command`(C6 계약)로 붙이는 **교체 seam**의 견고성. 현재 stub만 검증됨. (ARCHITECTURE 8, D-022/023)
- **B. 실 SAM/VSAM**: layout 바이트위치·key 확정(현 데모 = 「가정 모양」 stub). VSAM **KSDS 가정** 외 ESDS(입력순=byte로 충분)/RRDS, **key 유일성 검증**(중복=머지조인 false-PASS). (D-047 deferred)
- **C. 대용량/성능**: 100~1000셸·件당 대용량 파일. record 모드 **인메모리 256MB 가드**·외부정렬(E4 보류)의 한계·OOM 거동·실행 시간.
- **D. 정교 비교(D-022 deferred)**: false-NG 저감(공차·날짜·숫자·NULL·공백·인코딩 정규화). **DB모델 차이(네트워크형→관계형)로 가짜 NG 다발 예상**(CONTEXT 5-3).
- **E. 인코딩 견고성**: Shift-JIS·EBCDIC 변환 잔재·외자/특수문자 — false-NG vs 진짜 결함 구분·진단성.
- **F. 에러/엣지·운영**: 부분 실패·checkpoint 재개·동시 실행 락·권한/디스크 장애·깨진 정의·잘못된 입력.
- **G. i18n**: UI·출력 문구 최종 **일본어**(현재 한국어 = 시연용). 데이터·인코딩은 이미 일본 전제.
- **H. 보안/온프레미스**: 자격 = env만 · 데이터 비반출 · **로그에 비밀 노출 0** · config 평문 금지 · 오프라인 동작.
- **I. 설치/패키징**: 고객 환경 설치 자동화·의존성·문서(TEAM_SETUP·docs/SETUP).
- **J. 직전 변경분 적대적 검토**: 매핑 리네임·.xlsx·sam/vsam 컴파일·N:M 멀티복사셸·config 단일진실 — 회귀·엣지.

---

## 3. QA 방법 (권장)
- **회귀**: `python3 -m pytest -q` (286 green 유지가 최소선).
- **fresh-clone e2e**(팀원 실경로 재현): `git clone` main → `pip install -r requirements.txt` → `pytest` → `samples/complete/config.yaml`의 DB값 편집 → `POSTGRES_PASSWORD=… ./samples/complete/run_demo.sh` → 27건 확인.
- **적대적/엣지**: 깨진 CSV/xlsx·대용량·인코딩·권한·동시실행·중단 후 재개.
- **정밀 리뷰**: `/code-review high`(또는 멀티에이전트 `/code-review ultra`)로 변경분·코어 리뷰. 실행 검증은 `/verify`·`/run`.
- **추측 금지**: 실 배치/실 SAM·VSAM 데이터를 못 구하면 stub「가정 모양」 유지 + **"실데이터 후 검증" 항목으로 분리**.

---

## 4. 규칙 (KEEP / 절대)
- **코어 무수정** 원칙: `src/core/*`(comparator·orchestrator·runner·exporter·paths·models·preflight) · `src/config/definition.py`(스키마) · checkpoint. 건드려야 하면 **멈추고 근거와 함께 질문**.
- 결정론 비교(LLM 금지) · 모델A(비번=env) · 온프레미스(데이터 비반출) · 모듈경계 · 통짜 바이트 1순위(D-004/D-038).
- **게이트형(보고→OK→코딩)** · 국소 diff · 각 단위 별개 커밋 · 테스트 녹색 · 새 결정은 `DECISIONS.md`.
- 자격 평문 금지 · **main 푸시는 사용자 지시 받고** · 모호하면 추측 말고 질문.
- 자가검증 6항(`dc-self-review` 메모리): 계약 드리프트·SPEC 충돌·결정 현행성·silent drop·바이트 자기일치.

---

## 5. 진행·산출
1. 위 PRD 갭(2절)을 읽고 **이 세션에서 공략할 우선순위 + 첫 항목 착수 계획을 한 번 보고**한 뒤 시작.
2. QA 발견 → **must-fix / deferred(실데이터 후)** 분류 → 국소 수정·테스트.
3. 끝에 `STATE_REPORT.md`·`DECISIONS.md` 갱신 + **PRD 배포 체크리스트** 산출.

---

## 6. 참고 — 자주 쓰는 명령
```bash
python3 -m pytest -q                                              # 회귀(286 passed/10 skipped)
POSTGRES_PASSWORD=devpw ./samples/complete/run_demo.sh           # 데모 e2e(dc-pg, config의 port로 접속)
python3 tools/mapping_to_definition.py 매핑.xlsx -o def.yaml      # 매핑표(CSV/xlsx) → 정의 yaml
python3 tools/make_xlsx_template.py                              # 공유용 엑셀 템플릿 재생성
lsof -ti tcp:8000 | xargs -r kill; POSTGRES_PASSWORD=devpw GUI_PORT=8000 ./run_gui.sh   # GUI
```
- 데모 DB: docker `dc-pg`(port 5433, user postgres, db compare_proto, password devpw). 죽었으면 `docker start dc-pg`.
- 팀원/실환경은 config의 `database` 값이 단일 진실(port 등 자기 환경에 맞춤).
