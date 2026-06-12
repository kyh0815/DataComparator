# HANDOFF v8 — PoC 완성 → 엔터프라이즈급 (실데이터·패키징·i18n·스케일)

> **현행 정본 hand-off.** HANDOFF_5(코어 C1~C7)·DEFINITION_SPEC·MAPPING_SPEC은 여전히 상위 정본,
> HANDOFF_7(QA Iteration)은 **완료되어 이 문서로 승계**됨.
> 기준 시점 **2026-06-12, `origin/main = 35c2bc3`, 309 passed / 10 skipped.**

---

## 0. ★새 세션 착수 프롬프트 (이 문서를 읽힌 뒤 그대로 적용)

> 너는 진행 중인 프로젝트에 합류한다. 이 문서(docs/HANDOFF_8.md)가 현행 정본 hand-off다.
> §1(읽기 순서)의 문서를 읽고, §2(현황)·§3(이번에 끝난 것)을 흡수한 뒤,
> §4(엔터프라이즈 로드맵)에서 **이 세션에서 공략할 항목과 착수 계획을 한 번 보고하고 OK를 받은 뒤** 시작하라(게이트형).
> 규칙은 §6 — 특히 **코어 무수정**(예외는 멈추고 승인), **추측 금지**(실데이터 없으면 "실데이터 후 검증"으로 분리),
> **main 푸시는 지시받고**. 발견·결정은 docs/DECISIONS.md, 상태는 STATE_REPORT.md에 남긴다.
> 작업 중 검증: `python3 -m pytest -q`(309 green 최소선) + GUI 변경 시 **렌더된 `<script>`를 node --check** +
> **브라우저 클릭까지**(서버 테스트는 JS를 실행하지 않는다 — D-051 교훈).

---

## 1. 읽기 순서

1. `docs/CLAUDE.md`(작업 규칙) → `docs/CONTEXT.md`(사업·도메인 — 왜/누구를 위한지)
2. `docs/HANDOFF_5.md`(코어 정본) · `docs/DEFINITION_SPEC.md` · `docs/MAPPING_SPEC.md`
3. `docs/DECISIONS.md` — 특히 **D-049~D-059**(이번 사이클의 결정·수정·deferred 전부)
4. `STATE_REPORT.md`(2026-06-12 블록) · `TEAM_SETUP.md`(팀 셋업+합격 체크리스트)
5. **이 문서** §2~§7

---

## 2. 한 줄 현황 (2026-06-12)

- **`origin/main = 35c2bc3`** (public `github.com/kyh0815/DataComparator`, 팀 공유 중). **309 passed / 10 skipped.**
- **HANDOFF_7의 QA Iteration 완료**: J(매핑 적대검토)·H(보안)·GUI 재설계·머지 전 정밀 리뷰까지 D-049~D-059로 종결, 전부 main 반영.
- **GUI = 検証フロー 한 화면 자동 진행**(탭 2개: 検証フロー / Project Settings):
  매핑표(CSV/xlsx) 선택 → 정의 생성·저장·**사전점검 자동** → `▶ 検証開始` 1클릭 → **백그라운드 실행**
  (브라우저 닫아도 계속, 재접속 시 자동 복귀, 중단 시 「続きから再開」) → **결과 리포트**(합격/불합격 판정·
  메트릭·一致率·不一致 전건 목록+행별 As-Is↔To-Be diff 지연로드) → 試験成績書(Excel: 要約·明細·**差分明細**=
  NG 전 행별 차이) / 結果データ(CSV) 다운로드 → 再検証(全件 / NG・ERRORのみ).
- **백엔드 신규(인터페이스 계층)**: `src/gui/run_manager.py`(전역 락+RunState, 워커 생명주기 락 보유) +
  `POST /run/start`(resume/retry, 상호배타 400) · `GET /run/status`(폴링) · `/run/resumable` · `/run/results`(+`/diff` 안정 키).
- **코어 무수정 유지**. 승인 예외 2건만: `models.py` 비번 repr 차단 1줄, `evidence.py` 差分明細 시트+`=` 리터럴 강제.
- 정본 데모셋 `samples/complete/`(24 CK), run_demo 기대치 **출력 27 / OK22·NG4·MISSING1** 불변.

---

## 3. 이번 사이클에 끝난 것 (D-049~D-059 요약)

| D | 내용 |
|---|---|
| D-049 | 매핑도구 silent-drop 3건(sam 모드 무경고 강등·xlsx 다중/비활성 시트 누락·출력경로 충돌) 가드 |
| D-050 | 보안 감사: repr 비번 차단·데모 비번 평문 제거·bak/스크린샷 gitignore. 핵심(네트워크0·env비번)은 견고 확인 |
| D-051 | **activeConfig 무한재귀 회귀**(6/8 혼입, 메인 화면 클릭 전부 RangeError) 수정 + 정적 가드. 교훈: pytest는 JS를 실행하지 않는다 |
| D-052~056 | 検証フロー 재설계 3단계: 一括実行 → 세그먼트 병합 → RunManager 백그라운드 실행+상태머신 UI 승격, 구 아코디언/Artifacts/Quarantine 제거 |
| D-057~058 | 결과 화면: 불일치 브라우저 표시 → 체계적 리포트(판정·메트릭·一致率·필터) → 다운로드 config 정합(CSV 404·Excel 빈 明細 수정) → **差分明細 시트**(감사용 NG 전 행별 차이) |
| D-059 | **머지 전 정밀 리뷰(7앵글×검증자)** → 확정 결함 10건 전부 수정(수식 인젝션 리터럴화·diff 안정키·진행단위 정합·config 전환 리셋·resumable 조건·idle 폴링·input 리셋·예외 로깅·Thread.start 락 가드·再検証 동선+400) + **deferred 목록**(§5) |
| 문서 | TEAM_SETUP: 합격 체크리스트에 **GUI 클릭 필수화**(사이드바 데모 선택 → 업로드 → 検証開始 → 결과 + 다운로드 열림), 자기 데이터 배치표(매핑 칼럼↔paths 디렉토리), 운영 주의(단일 프로세스·절전) |

---

## 4. 다음 목표 — 엔터프라이즈급 로드맵 (이 세션의 작업 목록)

> ★대전제: 이 도구의 "엔터프라이즈급" = **실데이터에서 신뢰받는 것**. 첫 실전에서 false-NG를 쏟아내면 신뢰가 끝난다.

### Phase A — 첫 실전 투입 전 필수
| # | 항목 | 상태/선행조건 |
|---|---|---|
| A1 | **실배치 연동**: 진짜 Net COBOL 1건을 `config.batch.command`(C6 계약)로 e2e | ★실배치 입수 필요(사용자 액션) |
| A2 | **실 SAM/VSAM**: layout 바이트위치·key 확정(현재 "가정 모양" stub, D-047 deferred) | ★실파일 1쌍 입수 필요 |
| A3 | **false-NG 대응(D-022)**: 공차·날짜·NULL·공백 정규화 — **실NG 패턴 수집 후 필요한 만큼만**(과하면 false-PASS) | ★실 As-Is/To-Be 샘플 필요 |
| A4 | **i18n 일본어 최종화**: 사용자 대면 문구(UI·CLI·에러) 전부 일본어(현재 한/일 혼재) | 지금 가능 |
| A5 | **패키징/재현성**: requirements 버전 핀 고정 + **오프라인 설치 번들**(고객 외부망 없음) + 설치 검증 | 지금 가능 |
| A6 | **스케일 실측**: 합성 1k/10k 측정 → must-fix(checkpoint 캐싱·compaction, 差分明細 행 캡, evidence 비동기). 평가 완료: 1k=설계 커버, 10k=마찰 있는 가능, **100k=현재 깨짐**(差分明細 Excel 행한계·checkpoint 풀파싱) | 지금 가능 |

### Phase B — 운영 안정화
실행 이력(run history)+감사 추적 · GUI 접근 제어(현재 무인증 — **고객 운영 형태 확인 후 결정**) ·
파일 락(다중 프로세스 가드) · 中止(다음 셸 경계 정지) · 로깅 체계(로테이션·비밀0) ·
**CI + 헤드리스 브라우저 스모크**(D-051 근본 해결, Playwright 오프라인 번들 검토) · §5 deferred 정리.

### Phase C — 차별화
NG 원인 자동 분류(진짜결함/인코딩성/DB모델성/외자성 — CONTEXT 7의 장기 차별화) · run-to-run 이력 비교 · 업무그룹 병렬 실행.

**권장 착수 순서(실데이터 없는 동안): A5(패키징) 또는 A6(스케일 실측) → A4(i18n).** A1~A3은 실데이터 입수 즉시 최우선.

---

## 5. D-059 deferred (비차단 기술부채 — Phase B에서 소화)

죽은 CSS ~130줄·고아 JS(preflightOK/es/editProjName/refreshDefPreview 등, index.html) ·
구 `/run` SSE 엔드포인트 제거(UI 미사용, 테스트만 사용) · `_COUNT_KEYS`/`_BAD_STATUSES`를 ComparisonStatus enum에서 파생 ·
evidence `build_rows`/`build_diff_rows` 키잉 공유 · checkpoint 조회 캐싱(현재 클릭마다 풀파싱) ·
applyFailFilter 전체 재렌더(5000건 시 멈칫) · 差分明細 행 캡 · 매핑 collision 가드 경로 정규화 ·
멀티워커 WSGI loud 가드 · checkpoint compaction(누적 성장).

---

## 6. 규칙 (KEEP / 절대 — 변함없음)

- **코어 무수정**: `src/core/*`·`src/config/definition.py`·checkpoint. 건드려야 하면 **멈추고 근거와 함께 승인**(이번 사이클 예외 2건도 전부 사전 승인).
- 결정론 비교(LLM 금지) · 모델A(비번=env만) · 온프레미스(데이터 비반출·외부 네트워크 0) · 통짜 바이트 1순위(D-004/038).
- **게이트형(보고→OK→코딩)** · 국소 diff · 단위별 커밋 · 테스트 녹색 · 새 결정은 DECISIONS.md.
- **main 푸시는 지시받고** · 자격 평문 금지 · **모호하면 추측 말고 질문** · 실데이터 없으면 "실데이터 후 검증"으로 분리.
- GUI 변경 시: 렌더된 `<script>` `node --check` + **브라우저에서 클릭까지** 확인(pytest는 JS 미실행).

## 7. 운영 메모 / 자주 쓰는 명령

```bash
python3 -m pytest -q                                          # 309 passed / 10 skipped
export POSTGRES_PASSWORD=…                                    # dc-pg(로컬 데모 도커, port 5433) 비번
./samples/complete/run_demo.sh                                # CLI e2e — 출력 27 / OK22·NG4·MISSING1
lsof -ti tcp:8080 | xargs -r kill; GUI_PORT=8080 ./run_gui.sh # GUI(検証フロー). ★기동 전 기존 프로세스 정리
python3 tools/mapping_to_definition.py 표.xlsx -o def.yaml    # 매핑표 → 정의(CLI 경로)
```
- **GUI 데모 검증 함정**: 사이드바에서 『サンプル demo』 **선택 후** 업로드(기본값 本番이면 점검 실패).
- **단일 프로세스 전제**: RunState가 인메모리 — gunicorn 멀티워커 금지. 서버 PC 절전 시 실행도 멈춤.
- GUI 재기동 시 옛 프로세스가 같은 포트에 살아남아 옛 코드를 서빙할 수 있음 — kill 확인 후 기동(이번 세션 실사례).
- 팀원 안내: `git pull` + GUI 서버 재시작(브라우저 새로고침만으론 반영 안 됨), TEAM_SETUP 체크리스트 3항목으로 재검증.
