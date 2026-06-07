# HANDOFF v3 — 現新比較 툴 (COBOL→Linux 마이그레이션 실무 기준 최종본)

> 정본. v1/v2 폐기. STATE_REPORT.md 대조 + 실무 스코프 재단 반영.
> 코드베이스는 구조적으로 건강(180 테스트 통과, 모듈 분리, 블랙박스 원칙 코어 준수).
> **재작성 금지. 국소 diff만.**

## 진행 상태 (2026-06 기준)
**코어 C1~C6 전부 완료. + C7 GUI 재구성(지시 완료·구현 대기).** ✅ C1 ✅ C2 ✅ C3 ✅ C5 ✅ C4 ✅ C6 | ☐ C7 GUI
테스트: 180(baseline) → **255 passed, 10 skipped** (회귀 0). 커밋됨, 푸시 보류 중.
다음: C7 GUI 동선 재구성(화면만) + **첫 실배치·실데이터 투입(진짜 검증)**. 보류 E1~E6은 필요 신호 시.

## 도메인 전제 (COBOL→Linux 現新比較)
- 본질 = **동작 무변경 증명.** As-Is/To-Be 출력은 원칙적으로 같아야 하고, 다른 건
  (a)진짜 결함 또는 (b)알려진 플랫폼 차이뿐.
- 비교 대상 = **DB 테이블을 export한 CSV(Shift-JIS, 변환 완료).** 코드 변환은 외부 도구 몫 — 이 툴은 변환 안 함.
- 1건 구조 = 입력 DB 여러 개 → 배치 프로그램(들) → 출력 DB. 체크리스트 1~N 순차.
- 데이터 규모 = **件당 수만 행 수준** → 인메모리로 충분(스트리밍 불필요).

## 다시 틀리면 안 되는 개념
1. **블랙박스 ≠ 바이트일치.** 배치 *내부 로직*은 몰라도 되나, 비교기는 출력 *형식*(정렬키·
   인코딩·무시컬럼)은 알아야 한다. **DB export 비교라 byte 통짜는 애초에 못 쓴다** —
   SELECT 순서 비결정 + 登録/更新日時 컬럼이 매 실행 달라져 정상도 전건 NG. → 모드 선택형으로.
2. **변환 안 함.** 이미 변환된 As-Is 출력(정답)이 존재한다고 가정. 실행 전 정답 파일 존재만 검증.

---

# ── 코어 (반드시 — 이거 없으면 실무에서 못 씀) ──

## 1. 절대 건드리지 말 것 (KEEP)
- 모듈 분리(loader/runner/exporter/orchestrator/paths/reporter/web)
- SSE 진행 파이프라인(on_progress → web queue → _sse → EventSource), 셸별 에러 격리
- 배치 도메인 로직은 stub_batch/에만(코어로 끌어오지 말 것)
- 기존 테스트(180 baseline → 현재 240) — 깨지면 안 됨. 변경마다 테스트 추가.

## C1. 비교기: 바이트 단일 → 모드 선택형 (DB export 비교라 필수)
compare_files를 모드 분기로. **비교기는 파일경로+옵션만. DB/배치 import 금지(격리 유지).**

    def compare_files(asis, tobe, opts=None, *, encoding=None)
    # opts 없으면 CompareOptions(mode="byte", encoding=encoding or "shift_jis") 합성 → 180 테스트 무수정

모드:
- byte  : 현재 로직 그대로(고정포맷·전바이트 의미). **미지정 기본.** 청크 비교로 OOM 방지(trivial).
- text  : 행 단위, 줄끝(CRLF/LF)·우측공백 정규화 후 위치 비교.
- record: 행→필드분할(layout/delimiter) → (key)정렬 → (mask)제외 → (정규화 최소) → 비교. diff 최대 50.
- ※ **DB byte 1순위**(D-038): export 시 `ORDER BY key`로 순서 결정화 후 **byte 비교가 1순위**, record는 순서 결정화 불가 시 폴백. 위 line 21 "byte 통짜 못 쓴다"는 *정렬 없는* naive byte를 가리킨다.

옵션(출력별):
- **key** : record 정렬키(컬럼명/인덱스). **DB/머지 출력 필수** — 없으면 순서로 전건 NG. record인데 비면 경고.
- **mask**: 매 실행 정상적으로 다른 컬럼(登録/更新日時·시퀀스ID). 여러 개 ; 구분.
- encoding: 판정용(text/record). Shift-JIS 기본 + UTF-8. **EBCDIC 스코프 밖.**
- layout : 고정길이 "start:end;..". delimiter: 기본 ,. has_header: 헤더 행 유무.
- **normalize: 풀세트 구현 완료(date/num/nullblank/zeropad/trim) — 유지.** 기본은 byte, 사용은 출력별 opt-in.
  원칙 "통짜가 정답, 규칙은 사후"는 *능력 제거*가 아니라 **사용 규율**: normalize/mask는 **실제 false-NG를 확인한
  그 컬럼에만, 이유를 명시해** 최소로 추가.
  ⚠ 過정규화 = **false-PASS = 마이그레이션 결함 은폐.** 現新比較에서 false-NG보다 위험(동작 무변경을 거짓 증명).

has_header=true → 양쪽 첫 행 헤더 제외, **이름은 각 파일 자기 헤더로 해석**(To-Be 컬럼 순서변경 내성).
이름+has_header=false → 프리플라이트 CSV 좌표 에러.

**대용량**: 件당 수만 행 → 인메모리 OK. 사이즈 가드만(수백 MB 초과 시 명시적 경고). 외부정렬 스트리밍 = 보류(E4).
record 파이프라인은 이터레이터 기반(source→aligner)으로 짜서, 훗날 스트리밍이 aligner 교체만 되게.

## C2. 정의파일: 비교 옵션을 출력별 운반 (C1과 반드시 함께)
- 입력 정본 = **사람이 채우는 Long CSV 단일.** mapping_to_definition → YAML(비노출, 내부 중간물).
- YAML comparison_rules(읽되 무시)를 실제 사용되는 출력별 compare 블록으로 교체.
  definition.py:_build_outputs / models.py(OutputSpec+CompareOptions) / orchestrator.py:115.
- **검증 메시지는 CSV 좌표로**("CK003 12행: output=database인데 key 비어있음 → 순서로 NG").
- **setup 컬럼 = 죽은 컬럼 만들지 말 것.** load_inputs 직전 체크리스트당 1회 실행(DB=SQL/파일=스크립트).
- 셀 내부 다중값 ; 구분. 샘플 CSV는 **정본 1벌**(2벌 손유지 금지, GUI는 거기서 복사/생성).
- 신규 컬럼: compare_mode,key,encoding,mask,tolerance,layout,delimiter,has_header,normalize + setup,in_encoding.
  (normalize는 최소 규칙만 우선 — E1 참조)

## C3. 프리플라이트(dry-run) — 야간 1000건 전에 필수
무실행 점검 → 하나라도 실패 시 실행 거부 + CSV 좌표 리포트:
정의 검증 / 모든 input·expected 파일 존재 / shell 실행파일 / DB 접속 / 출력 디렉토리 쓰기권한.
정답 파일 누락 = 비교 무의미 → 여기서 반드시 사전 차단.

## C4. 결과 에비던스 = 試験成績書 (실무 납품 필수) ▶ 진행 중
- **소스 = store.latest_results** (이번 run만 아닌, 전체 1000건 머지 최신 상태).
- **각 행에 결과 출처(run 시각/식별자) 컬럼 노출** — 낡은 OK가 최신으로 위장 방지(C5 머지 안전장치).
- Excel 2시트: **요약**(全件/OK/NG/ERROR 件数 + 消化率) + **NG明細**(체크리스트·항목·차이내용 — 개발팀이 보고 고침).
- **MISSING_ASIS / MISSING_TOBE는 NG와 별도 표기**(정답없음 vs 값틀림 = 개발 대응이 다름).
- 결과 디스크 영속화는 C5 JSONL이 겸함.
- GUI `--preflight` 버튼을 이 화면 작업에 함께 노출(C3 기능 재사용, 화면만).

## C5. 부분 실행 + checkpoint/resume — 실무 핵심 ✅ 구현 완료
현실은 "전체 1000건 1회"가 아니라 **"NG난 50건만 고쳐서 재실행"** → 부분 재실행이 주력, 전체는 옵션.
구현(store.py, append-only JSONL = report_dir/checkpoint.jsonl):
- 셸 1건 종료 직후 즉시 기록(append+flush+fsync). 야간 중단 시 부분 상태 보존(깨진 마지막 줄만 버리고 앞줄 복원).
- 선택 3경로(상호배타): `--shells X`(ID/범위 — OK여도 강제 rerun, 고친 NG 재검증) / `--retry-failed`(직전 NG·ERROR 자동) / `--resume`(미실행+ERROR만, OK/NG 건너뜀).
- **머지: shell_id last-wins fold** → 부분 결과가 직전 전체에 합쳐져 전체 1000건 최신 상태 유지(= C4 납품물 소스 store.latest_results).
- ★결과에 run 출처/시각 동반(JSONL 누적이라 자연 확보) — 낡은 OK가 최신으로 위장 방지.
- 적재 멱등(loader TRUNCATE)·체크리스트 간 DB 격리 유지.
- 알려진 한계: JSONL **compaction 미구현**(run마다 누적 성장). fold 정상이라 기능 무해, 장기운영 시 추가(보류). 코드 주석/STATE_REPORT 명기.

## C6. 배치 호출 결합 제거 (경량)
runner._build_command의 stub CLI 규약 + L106 "transaction_log" 폴백을 config 구동으로 외부화.
하드코딩 도메인 상수 제거, 폴백 금지(없으면 명시적 에러). 목표: 진짜 배치 교체 시 코어 0줄 수정.
DB는 **첫 프로젝트가 쓰는 1종만** 붙임(psycopg2를 끔찍하게 박지만 않으면 됨). 멀티DB 추상화는 보류(E3).

## C7. GUI 고객 동선 재구성 (화면만 — 로직/API 손대지 말 것)
> ⚠️ **D-043으로 갱신**: "세로 한 페이지" 전제·DESIGN_TOKENS 먹네이비는 무효. 형제 제품 ModernizePro
> 셸(사이드바+탭)·녹색 디자인을 따르며, 아래 세로 흐름은 **Execution 탭 내부 레이아웃**으로만 존속. UI 실작업 보류.
기존 라우트/엔드포인트(preflight·검증실행·試験成績書·정의생성·접속설정) **재배치**. 백엔드 무수정.
- **세로 한 페이지 + 진행형 접힘** (페이지 마법사 X — 근거는 SESSION_CONTEXT §11).
  [상단] 接続設定 = 한 줄 요약 접힘("✓ host:port/dbname·인코딩" + 変更). config.yaml 경로/파일명 고객 화면에서 제거(내부 처리).
  ① 定義ファイル(別 페이지였던 定義作成 흡수) → ② 事前点検 → ③ 検証実行 → ④ 結果·試験成績書.
- 진행형 접힘: 완료 단계는 한 줄 요약으로 접고 지금 할 단계만 펼침("한 페이지 안 아코디언").
- 게이트: ②점검 에러0 전엔 ③실행 **비활성**. ④결과는 ③ 실행 시 그 자리 펼침(기존 SSE 재사용).
- 부분실행(C5)·差分全件표시는 ③詳細指定 접힘 / ④결과 근처로(평소 동선에서 숨김).
- **비주얼은 DESIGN_TOKENS.md가 정본**(먹네이비 #1F2937 주색·중간 질감·상태색 절제·스텝뱃지 단색 통일).
  글 해석 말고 hex/규칙 값을 CSS 변수로 그대로. 단계상태는 뱃지색 아닌 접힘+텍스트로.
- 라벨 일본어(고객=日本 SI). 255 테스트 녹색. **템플릿/뷰/CSS만 변경, 라우트·로직·스키마 금지.**

---

# ── 보류 (가치는 있으나 실무 v1 코어 밖 — 실제 필요해지면) ──

- **E1. normalize 규칙 *종류* 확장 금지**: 현재 date/num/nullblank/zeropad/trim은 구현·유지.
  이 외 **신규 규칙 종류**를 실제 필요 신호 전에 선제 추가하지 말 것.
- **E2. 회차 간 회귀비교**(new OK/new NG 자동 델타): 그냥 재실행+NG리스트로 충분. 편의 기능. *(D-043: 회차이력은 형제 제품 **Versions 탭**으로 귀속 예정.)*
- **E3. Oracle/DB2 멀티DB 어댑터**: 첫 DB 1종 외. 선제적 추상화 = 과설계.
- **E4. GB급 외부정렬 스트리밍**: 件당 수만 행이면 불필요. 진짜 대용량 만나면 그때(아키텍처는 C1에서 대비).
- **E5. 파일중심 경로 강화**: 현재 케이스가 DB 중심이면 우선순위 낮음.

---

## 순서 / 검증
1. ~~C1+C2~~ ✅ → ~~C3~~ ✅ → ~~C5~~ ✅ → **C4(진행 중)** → **C6(남음)**.
2. 단위테스트: byte/text/record, key 순서무관·누락, mask, trim/zeropad, layout, has_header 이름해석. **기존 테스트(현재 240) 녹색 유지.**
3. 보류(E1~E6)는 손대지 말 것. 필요 신호가 오면 그때 별도 판단.
4. C6 완료 = 코어 종료. 이후는 코드가 아니라 첫 실배치·실데이터 투입.

각 PR 국소 diff, 모듈경계 유지, 모호하면 추측 말고 질문.
