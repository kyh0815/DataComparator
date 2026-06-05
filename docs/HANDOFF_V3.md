# HANDOFF v3 — 現新比較 툴 (COBOL→Linux 마이그레이션 실무 기준 최종본)

> 정본. v1/v2 폐기. STATE_REPORT.md 대조 + 실무 스코프 재단 반영.
> 코드베이스는 구조적으로 건강(180 테스트 통과, 모듈 분리, 블랙박스 원칙 코어 준수).
> **재작성 금지. 국소 diff만.**

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
- 기존 테스트 180건 — 깨지면 안 됨. 변경마다 테스트 추가.

## C1. 비교기: 바이트 단일 → 모드 선택형 (DB export 비교라 필수)
compare_files를 모드 분기로. **비교기는 파일경로+옵션만. DB/배치 import 금지(격리 유지).**

    def compare_files(asis, tobe, opts=None, *, encoding=None)
    # opts 없으면 CompareOptions(mode="byte", encoding=encoding or "shift_jis") 합성 → 180 테스트 무수정

모드:
- byte  : 현재 로직 그대로(고정포맷·전바이트 의미). **미지정 기본.** 청크 비교로 OOM 방지(trivial).
- text  : 행 단위, 줄끝(CRLF/LF)·우측공백 정규화 후 위치 비교.
- record: 행→필드분할(layout/delimiter) → (key)정렬 → (mask)제외 → (정규화 최소) → 비교. diff 최대 50.

옵션(출력별):
- **key** : record 정렬키(컬럼명/인덱스). **DB/머지 출력 필수** — 없으면 순서로 전건 NG. record인데 비면 경고.
- **mask**: 매 실행 정상적으로 다른 컬럼(登録/更新日時·시퀀스ID). 여러 개 ; 구분.
- encoding: 판정용(text/record). Shift-JIS 기본 + UTF-8. **EBCDIC 스코프 밖.**
- layout : 고정길이 "start:end;..". delimiter: 기본 ,. has_header: 헤더 행 유무.
- **정규화는 최소만**: trim(고정길이 패딩), 부호/zeropad 정도. ★date/num/nullblank 풀세트는 보류(E1).
  원칙: **"통짜가 정답, false-NG 날 때만 그 컬럼에 규칙 추가."** 미니언어 선제 구축 금지.

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

## C4. 결과 에비던스 = 試験成績書 (실무 납품 필수 — 화면만으론 무의미)
- 결과 디스크 영속화(SSE/메모리 휘발 방지) — 재접속·내보내기의 전제.
- **Excel 試験結果一覧**: 全件 / OK / NG / ERROR 件数 + 消化率 + NG明細(체크리스트·항목·차이). 元請け 납품용.

## C5. 부분 실행 + checkpoint/resume — 실무 핵심
현실은 "전체 1000건 1회"가 아니라 **"NG난 50건만 고쳐서 재실행".**
- **체크리스트 부분 선택/범위/필터 실행**(예: NG건만, 특정 번호대).
- run별 checkpoint.json → 재개 시 OK/NG 건너뛰고 ERROR/미실행만.
- 적재 멱등(loader TRUNCATE). 체크리스트 간 DB 상태 격리/트랜잭션 경계 명시.

## C6. 배치 호출 결합 제거 (경량)
runner._build_command의 stub CLI 규약 + L106 "transaction_log" 폴백을 config 구동으로 외부화.
하드코딩 도메인 상수 제거, 폴백 금지(없으면 명시적 에러). 목표: 진짜 배치 교체 시 코어 0줄 수정.
DB는 **첫 프로젝트가 쓰는 1종만** 붙임(psycopg2를 끔찍하게 박지만 않으면 됨). 멀티DB 추상화는 보류(E3).

---

# ── 보류 (가치는 있으나 실무 v1 코어 밖 — 실제 필요해지면) ──

- **E1. normalize 풀세트**(date/num/nullblank/zeropad 미니언어): false-NG가 실제로 난 컬럼에만 사후 추가.
- **E2. 회차 간 회귀비교**(new OK/new NG 자동 델타): 그냥 재실행+NG리스트로 충분. 편의 기능.
- **E3. Oracle/DB2 멀티DB 어댑터**: 첫 DB 1종 외. 선제적 추상화 = 과설계.
- **E4. GB급 외부정렬 스트리밍**: 件당 수만 행이면 불필요. 진짜 대용량 만나면 그때(아키텍처는 C1에서 대비).
- **E5. 파일중심 경로 강화**: 현재 케이스가 DB 중심이면 우선순위 낮음.

---

## 순서 / 검증
1. **C1(비교기) + C2(정의) 함께** — 한쪽만은 무의미. record는 이터레이터 기반.
2. C3 프리플라이트 → C5 부분실행+resume → C4 에비던스 → C6 배치결합 제거.
3. 단위테스트: byte/text/record, key 순서무관·누락, mask, trim/zeropad, layout, has_header 이름해석.
   **180 기존 테스트 녹색 유지.**
4. 보류(E1~E5)는 손대지 말 것. 필요 신호가 오면 그때 별도 판단.

각 PR 국소 diff, 모듈경계 유지, 모호하면 추측 말고 질문.
