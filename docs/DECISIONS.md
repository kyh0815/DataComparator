# DECISIONS.md

> 프로젝트 진행 중에 내려진 결정과 그 이유. 시간순.
> 새로운 결정이 생기면 이 파일에 한 항목을 추가한다.

---

## D-001. 인코딩 변환은 외부 툴 사용, 본 도구는 그 결과부터 시작

**결정**: EBCDIC → Shift-JIS 변환은 본 도구 외부에서 수행된다고 가정. 본 도구는 *변환된 Shift-JIS CSV*를 입력으로 받음.

**이유**:
- 후지쯔 JEF·외자·왕복 변환 등은 도메인 깊이가 매우 큼.
- 검증된 외부 변환 툴이 이미 사용 중.
- 우리 도구의 책임 범위를 좁혀 신뢰성을 확보.

---

## D-002. 양쪽 인코딩은 Shift-JIS로 통일

**결정**: As-Is, To-Be 출력 모두 Shift-JIS. 비교는 동일 인코딩 전제.

**이유**: 비교는 동일 인코딩일 때만 의미 있음. 현재 클라이언트가 Shift-JIS.

**여지**: 클라이언트별로 다를 수 있으므로 설정값으로 분리. 기본값만 Shift-JIS.

---

## D-003. OS는 시연용 우분투, 운영은 클라이언트 환경에 맞춤

**결정**:
- 본인의 시연 환경: **우분투**
- 운영(실 고객 환경): PITON 기반, 클라이언트별로 다름. 설정으로 대응.

**이유**:
- 시연은 본인이 자력 구축해야 하므로 가장 마찰 적은 우분투.
- 운영은 우리가 정할 수 없음 → 설정으로 추상화.

---

## D-004. 비교 방식은 통짜 바이트, 완전 일치

**결정**: 두 CSV를 바이트 단위로 비교. 1바이트라도 다르면 NG.

**이유**:
- 검증의 1단계는 엄격한 게 안전. 무해한 차이는 보면서 예외 처리.
- 셀 단위 파싱은 복잡도 증가, 프로토 범위 초과.

**예상 부작용**: DB 왕복 등으로 인한 가짜 NG가 다수 발생할 가능성. 운영 시 보정 필요(인수인계 후).

---

## D-005. 셸 1개씩 순차 실행

**결정**: 배치를 한 번에 하나씩 처리. 병렬 X.

**이유**:
- 실패 격리 용이
- 디버깅 용이
- 시연 단계에선 속도보다 명확성

---

## D-006. 인터페이스는 CLI, 단 Core/Interface 분리

**결정**:
- 본인 단계: CLI만 제공.
- Core는 인터페이스에 독립적으로 구성하여 향후 GUI를 같은 Core 위에 얹을 수 있게 함.

**이유**:
- 사장님(아버지) 시연자가 기술 베이스 → CLI도 가치 평가 가능.
- 본인이 후속 단계에서 GUI를 추가할 가능성이 큼.
- 일본 SI 시장 판매를 위해선 결국 GUI 필요하지만, 이는 다음 단계.

---

## D-007. 사업 모델은 "비교검증팀"으로 명확화

**결정**: 우리는 마이그레이션 자체는 하지 않음. 마이그레이션이 끝난 후의 검증만 담당.

**이유**:
- 마이그레이션 SI는 무겁고 진입장벽 높음.
- 검증만 떼어내면 누구의 마이그레이션이든 검증 가능 → 시장 넓음.
- 마이그레이션 SI 회사가 잠재 파트너 채널이 됨.

---

## D-008. 도구는 고객 환경(PITON)에 설치되는 *온프레미스 소프트웨어*

**결정**: SaaS 아님. 고객 환경 안에서 동작하는 설치형 라이선스 제품.

**이유**:
- 일본 엔터프라이즈 정서상 데이터 외부 반출 어려움.
- 고객 데이터를 우리가 받지 않으니 보안·계약 단순.

---

## D-009. 비교 판정에 LLM 사용 금지

**결정**: 비교 결과(OK/NG)는 결정론적 코드로만 판정.

**이유**:
- 검증 도구의 생명은 신뢰성·재현성.
- LLM은 비결정적이라 같은 입력에 다른 답 가능성.

**예외**: 향후 NG의 *원인 추정·분류·설명*을 도울 용도로는 검토 가능 (판정에는 절대 사용 X).

---

## D-010. 프로토에선 stub 배치 사용

**결정**: 진짜 Net COBOL 배치 대신 Python으로 만든 stub 배치를 시연에 사용.

**이유**:
- 본인의 우분투 환경에 Net COBOL·PITON을 구축할 수 없음.
- 시연의 본질은 *흐름이 자동으로 도는 것*. 배치 본체는 교체 가능한 부품.
- 인수인계 시 정직원이 실 환경에서 진짜 배치로 교체.

---

## D-011. 리포트는 "단계 2" 수준

**결정**: NG의 어느 줄이 어떻게 다른지(줄 번호 + 양쪽 내용)까지. NG 원인 분류는 안 함.

**이유**:
- 단계 1(OK/NG만)은 시연 임팩트 부족.
- 단계 3(원인 분류)은 프로토 범위 초과 + 분류 부정확 시 신뢰 손상.
- 단계 2가 수작업 대비 가치를 가장 명확히 보여줌.

---

## D-012. 프로젝트 폴더 구조: src/core, src/cli, src/config 분리

**결정**: `ARCHITECTURE.md` 3장 구조 채택.

**이유**:
- Core는 Interface 무관해야 함 (가장 중요한 설계 원칙).
- GUI 추가 시 `src/gui/`만 별도로 붙이면 됨.

---

## D-013. 설계·맥락 문서는 `docs/` 폴더에 모은다 (README.md만 루트)

**결정**: CLAUDE.md / CONTEXT.md / ARCHITECTURE.md / SPEC.md / TASKS.md / DECISIONS.md(및 추후 SETUP.md, HANDOFF.md)는 `docs/` 폴더에 위치. **README.md는 프로젝트 루트**에 유지.

**이유**:
- ARCHITECTURE.md가 원래 제안한 폴더 구조(`docs/`)와 일치시킴.
- 루트를 코드·설정(`src/`, `config.yaml` 등) 중심으로 깔끔하게 유지.
- README는 프로젝트 첫인상이므로 관례대로 루트에 둠.

**영향**:
- `docs/` 내부 문서끼리는 형제 관계이므로 서로를 접두어 없이(`CONTEXT.md`) 참조.
- README.md(루트)에서 설계 문서를 가리킬 때만 `docs/` 접두어 사용.
- ARCHITECTURE.md·README.md의 폴더 구조 다이어그램을 이 구조로 갱신.

---

## D-014. `compare_files`에 `encoding` 파라미터 추가 (표시용 디코딩 한정)

**결정**: ARCHITECTURE 4-4의 시그니처 `compare_files(asis_path, tobe_path)`에 `encoding: str = "shift_jis"`를 추가. 오케스트레이터는 `config.encoding`을 넘긴다.

**이유**:
- OK/NG 판정은 바이트 비교라 디코딩이 불필요하지만, `DiffLine`의 사람이 볼 내용(content)을 채우려면 디코딩이 필요함.
- 인코딩을 코드에 박지 않기 위해(CLAUDE 3-3) 파라미터로 분리. 기본값 Shift-JIS는 CLAUDE 3-3에서 명시 허용.
- 디코딩 실패 바이트는 `errors="replace"`로 처리 → 표시만 영향, **판정에는 무영향**.

## D-015. NG 줄 추출은 위치 기반(zip_longest) 대조

**결정**: 불일치 시 `\n`으로 줄을 나눠 *같은 인덱스끼리* 비교하고, 짧은 쪽은 빈 줄로 패딩. difflib 대신 위치 기반 사용.

**이유**:
- DoD("한 줄 다름 → 1개 / 여러 줄 → N개")와 정확히 일치, 결정론적.
- 프로토 범위에 충분. (삽입/삭제로 인한 정렬 어긋남 보정은 향후 difflib 도입으로 개선 여지 — 인수인계 항목.)

## D-016. RunSummary에 `missing_count` 필드 추가

**결정**: `RunSummary`에 `missing_count: int`를 추가(`MISSING_ASIS` + `MISSING_TOBE` 합산). 이로써 `total == ok_count + ng_count + error_count + missing_count` 항등이 성립한다. CLI 최종 요약·SPEC 5-2 형식도 MISSING을 항상 표기.

**이유**:
- 기존 4개 카운트(OK/NG/ERROR)만으로는 MISSING 케이스가 어디에도 안 잡혀 `합 ≠ total`이 될 수 있음.
- 시연 요약("총 N건 / OK / NG / ERROR / MISSING")의 합이 안 맞으면 신뢰가 깨짐.

**영향**: `models.py`(필드 추가), `reporter.py`(집계), `SPEC.md` 4-1·5-2, `tests/test_models.py`·`tests/test_reporter.py` 갱신. 시연 기본 데이터엔 MISSING이 없으므로 요약 예시는 `MISSING 0`.

---

## D-017. 상세 diff 디렉토리는 CSV와 타임스탬프를 공유 (실행마다 분리)

**결정**: 상세 diff는 `report_{TS}_details/{shell_id}.diff`에 저장하고, `{TS}`는 같은 실행의 `report_{TS}.csv`와 **동일한 타임스탬프**를 공유한다. NG가 하나도 없으면 상세 디렉토리는 만들지 않는다.

**이유**:
- SPEC 4-2 표기(`report_{...}_details/`)와 일치.
- 고정 `details/` 누적 방식은 실행 간 파일 충돌 위험. 실행별 분리가 깔끔.

## D-018. 적재 환경은 "길 3 — 시연용 Sample DB" (금융 도메인 실 스키마)

**결정**: T2-1의 적재 DB를 **시연용 Sample DB**로 구축한다. 범용 `TEXT[]` 랜딩 테이블(옵션 A)이나 DB 미사용(옵션 C) 대신, 금융 도메인을 흉내 낸 실 테이블 2개를 둔다.

- 테이블: `customer_master`(고객 마스터, 8컬럼), `transaction_log`(거래 명세, 8컬럼)
- 제약: **PK · NOT NULL만**. FK · 인덱스 · 트리거 · 뷰 · 시퀀스 일체 없음 (프로토 범위).
- 더미 데이터: 고객 20행 + 거래 50행 (셸 10개 시연에 충분).
- 산출물: `db/schema.sql`(CREATE + INSERT), `docs/SETUP.md`(우분투 설치~검증 가이드).

**인코딩**: DB 내부는 **표준 UTF-8**, As-Is/To-Be 출력 CSV 파일만 **Shift-JIS**, 변환은 **파일↔DB 경계의 Python 레벨에서만**. 비교는 파일 레벨이라 DB 인코딩과 무관하게 성립. (일본 엔터프라이즈 표준 패턴.)

**이유**:
- 옵션 A(범용 `TEXT[]`)보다 **시연 임팩트**가 크다 — 사장님이 "이런 비즈니스 데이터구나"를 직관적으로 이해.
- 옵션 C(DB 미사용)보다 **실 운영 흐름(적재→배치)을 정직하게** 시연.
- 인수인계 가이드(SETUP.md) 자체가 자산이 된다.

**한계 / 인수 시 교체 대상**:
- 이 스키마·데이터는 **시연용**이며 실 클라이언트의 비즈니스 스키마와 다르다 (도메인 깊이 상이).
- 인수인계 시 정직원이 **실 클라이언트 스키마로 교체**해야 한다.
- 시연용 슈퍼유저 `postgres` 사용 → 실 운영은 권한 분리된 별도 유저 권장.
- 셸 10개가 이 데이터를 읽어 셸별 출력을 만드는 매핑은 **T2-3(stub 배치)**에서 정의.

**검증**: PostgreSQL 16 컨테이너에 `db/schema.sql`을 `ON_ERROR_STOP=1`로 적용해 무오류 통과(CREATE×2, INSERT 20/50), `server_encoding=UTF8`, 한자·가나 정상 표시 확인.

## D-019. 설정 로더(`load_config`) 정책

**결정**: `load_config(path) -> Config`의 파싱·검증 규칙을 아래로 확정.

1. **필수 vs 기본값**: `paths`(4개 디렉토리)와 `database` 블록은 **필수** — 없으면 `ConfigError`(전용 예외). `encoding`·`shells`·`batch`·`output`은 **기본값 허용**(보편적 기본값이 있는 값만 선택적).
2. **`shells` 우선순위**: `ids`와 `range`가 둘 다 있으면 **`ids` 우선**(구체 > 일반).
3. **`range`는 inclusive**: `range: [1, 10]` → 1~10 모두 포함 = 10개. 시작 > 끝이면 `ConfigError`.
4. **셸 ID 정규화**: 모든 ID를 **3자리 zero-pad 문자열**(`1 → "001"`)로 통일. 정수·문자열 입력 모두 수용, 비숫자는 그대로 둠.
   - ⚠️ **3자리 고정은 프로토 한정 — 인수 시 재검토 대상**(샘플 `001.csv~010.csv` 기준). 실 운영의 셸 수/명명 규칙이 다르면 교체. (코드에 동일 주석 표기.)
5. **상대경로 해석**: 모든 경로는 **config 파일이 위치한 디렉토리 기준**으로 절대경로화 → 실행 cwd에 흔들리지 않음.
6. **비밀번호**: `database.password_env`(기본 `POSTGRES_PASSWORD`)가 가리키는 환경변수에서 해석. 없으면 `password=None`(예외 아님) — 실제 실패는 DB 접속 시점에서 처리. `load_config`은 *설정 파싱*만 책임.
7. **에러 타입**: 파일 없음·YAML 파싱 실패·필수 키 누락은 모두 전용 `ConfigError`로 던져 CLI가 SPEC 8대로 "즉시 종료 + 에러 메시지" 처리.

**이유**:
- 보편적 기본값이 없는 값(경로·DB)만 강제해 "필수 키 누락 시 명확한 에러"(DoD)와 사용성을 양립.
- `ids` 우선·`range` inclusive는 직관적 기대와 일치.
- config 디렉토리 기준 경로 해석으로 시연/테스트 환경 cwd 차이에 강건.

**검증**: 단위 테스트 9개(정상·기본값·ids우선·inclusive·경로해석·env해석·필수누락·파일없음·YAML오류) 통과. 실제 `config.yaml.example`도 정상 변환 확인.

## D-020. Loader(`load_input_csv`) 정책

**결정**: As-Is 입력 CSV를 PostgreSQL에 적재하는 로더를 아래로 확정.

1. **범용 `table_name` 시그니처 채택**: `load_input_csv(csv_path, conn, table_name, encoding="shift_jis") -> int`(적재 행수 반환). ARCHITECTURE 4-2의 `table_name`을 따르고 TASKS T2-2의 `shell_id` 시그니처는 채택하지 않음.
   - **이유**: schema(D-018)는 `customer_master`/`transaction_log` 도메인 테이블이고 `shell_id` 컬럼이 없다. "셸→테이블 매핑은 T2-3에서 정의"(D-018)와 일관되게, 로더는 *어느 테이블이든 적재하는 범용 부품*으로 두고 매핑 결정을 T2-3/T3-1로 미룬다.
2. **인코딩**: CSV를 `encoding`(기본 `shift_jis`)으로 디코드해 **UTF-8 DB에 적재** — 파일↔DB 경계 변환(D-018). conn만으론 인코딩을 알 수 없어 파라미터로 분리(선례 D-014).
3. **CSV 형식**: 헤더 행으로 테이블 컬럼에 매핑(순서 무관). 빈 문자열 셀 → `NULL`. 행 컬럼 수 불일치/없는 컬럼/빈 CSV는 전용 `LoaderError`. DB 예외(psycopg2)는 그대로 전파.
4. **재적재·트랜잭션**: 적재 전 `TRUNCATE` → `executemany` INSERT. 로더는 **commit하지 않음**(호출자가 셸 단위 트랜잭션 경계 관리, 실패 격리 SPEC 3-1).
5. **식별자 안전**: `table_name`은 `psycopg2.sql.Identifier`로 처리.

**통합 테스트 — 조건부 skip 방식 채택**:
- 순수 파싱(`_parse_rows`)·헤더 검증·파일 없음 단위 테스트는 **기본 pytest에서 항상 실행**(DB 의존 0).
- 실제 DB 적재 테스트는 **`RUN_DB_TESTS=1`일 때만 실행**(접속 정보는 환경변수). 미설정 시 `pytest.skip`.
- **이유**: T2-1(Docker 옵션 검증) 패턴과 일관 — 일반 pytest는 외부 의존 0, 통합은 옵션. **정직원이 그냥 `pytest`를 돌려도 DB 없이 사고 없이 통과**해야 한다.

**검증**: 기본 스위트 37 passed / 3 skipped. Docker PostgreSQL 16에 `RUN_DB_TESTS=1`로 통합 9개(일본어+NULL 왕복, TRUNCATE 재적재, 헤더 불일치) 전부 통과.

## D-021. 사장님 기획서 정렬 — 정의 파일 도입, 두 입력 흐름, 2 도메인

> 근거 문서: `docs/T2-3_alignment.md`(외주 작업자가 직접 판단해 확정). D-018/D-020에서 "T2-3에서 정의"로 미뤄둔 셸→데이터 매핑을 본 결정으로 확정한다.

**결정**:
- 사장님 기획서 검토 결과 4개 불일치 식별, 그중 3개를 프로토에 반영(100건은 10건 유지).
- **`test_definition.yaml` 도입**으로 셸별 메타데이터를 코드 밖으로 외부화(사장님 기획 7.1절 경량 버전). 셸마다 `input_type`(database/file)이 다를 수 있다.
- **입력 흐름 2가지** 모두 구현: DB 입력(셸 001~005) + 파일 입력=야간 배치 시뮬(셸 006~010).
- **시연 도메인 2개**로 최소화: 결제(DB 입력) + 야간 배치 시뮬(파일 입력). 추가 도메인(인사·근무 등) 만들지 않음.
- **stub 배치 2종**: `run_batch_db.py`(DB 입력) / `run_batch_file.py`(파일 입력). 공통 CLI 계약 유지(`--shell-id`/`--output-path`/`--clean`).
- **새 Loader 함수 `copy_input_file(csv_path, dest_dir) -> Path`** 추가: 파일 입력 흐름에서 As-Is 입력 CSV를 야간 배치 입력 디렉토리로 **바이트 복사**(인코딩 변환 없음 — stub이 읽을 때 디코드). 실패 시 `LoaderError`(D-020과 일관).
- ~~**schema.sql 변경 없음**~~ → **D-022로 보정**: 출력 DB 유형 시연을 위해 결과 테이블 `tobe_result` 1개를 추가한다(아래 D-022 참조).
- **Config 확장**: `definition_file`(정의 파일 경로) + `tobe_input_dir`(파일 입력 복사 대상) 추가. config 디렉토리 기준 절대경로화(D-019 5항과 일관).
- NG/ERROR는 야간 배치 흐름에 배치(007 한 줄 / 008 전각 공백 / 009 여러 줄 / 010 종료코드 1). 골든은 `--clean` 출력.
- 100건 풀 구현 / 추가 도메인 / 직접 DB 비교 / 정교한 비교 알고리즘은 인수 후 단계.

**이유**:
- 사장님 그림의 핵심(데이터 주도 메커니즘, 야간 배치)을 프로토에 반영해야 인수 시 정합성 확보.
- 시간 여유(외주 일정 2주~한달)로 두 입력 흐름 모두 구현 가능.
- 도구의 진짜 가치는 *우리가 도메인을 많이 만드는 것*이 아니라 *정의 파일로 스키마·입력 방식을 받아 처리하는 동적 적응 능력*. 실 운영은 고객 스키마를 따른다.
- 통짜 바이트 비교(D-004) 유지: 검증 도구는 엄격에서 관대로 푸는 게 안전. "DB 비교"는 CSV export 후 파일 비교와 사실상 동일(export 단계 명시화).

**한계 / 인수 시 교체 대상**:
- 시연용 도메인 2개·stub 2종은 시연 한정. 실 운영은 고객 스키마 + 진짜 Net COBOL 배치로 교체.
- 정의 파일은 경량 스키마. 사장님 기획 7.1절 풀 스키마(comparison_rules, success_criteria 등)는 인수 후 단계 — 자리만 비워둠.

**검증 결과** (T2-3 완료):
- 정의 파일 파서(Boss 구조)·copy_input_file·stub NG 주입 단위 테스트 통과. test_definition.yaml 10건이 SPEC 6-5 매핑대로 로드됨(001 DB→DB … 010 ERROR).

## D-022. Boss Requirements 정렬 — 출력 다운로드(export) 단계 추가, 정의 파일 Boss 구조 채택, 4사분면 시연

> 근거 문서: `docs/AlignmentCheck/Requirements.md`(Boss 원 지시) + `InitialPlanning.md`(초기 기획) 대조. D-021을 Boss 명세에 맞춰 정밀화한다. 100건은 적은 케이스로 줄여 "프로그램이 실제 Working함"만 증명한다(사용자 합의).

**결정**:
1. **Exporter 추가**: `src/core/exporter.py`에 `export_table_to_csv(conn, table_name, output_path, encoding="shift_jis", columns=None) -> Path`. TOBE 배치가 DB 결과 테이블에 쓴 출력을 **CSV로 다운로드**(현신비교용 TOBE 디렉토리)한다. Boss가 명시한 처리단계 *"SHELL프로그램이 출력한 데이터(DB,파일)를 TOBE 디렉토리에 다운로드"*를 충족. 결정론 보장(명시 컬럼 순서·PK ORDER BY·NULL→빈칸·Shift-JIS·`\n`)으로 export 후 **바이트 비교**(D-004 일관, 출력 DB 비교 = export+파일비교, D-021 §2-5).
2. **결과 테이블 `tobe_result` 추가**(schema.sql): DB 출력 셸은 stub이 여기에 INSERT → exporter가 CSV로 내림. 파일 출력 셸은 stub이 직접 CSV 생성. TRUNCATE per shell, 제약 PK·NOT NULL만(D-018 정책 일관).
3. **입력2 × 출력2 = 4사분면 전부 시연**(10셸, 적은 케이스). 도메인 분리(결제=DB입력 001~005 / 야간배치=파일입력 006~010)는 유지하되 출력 유형을 혼합:
   - 001 DB→DB, 002 DB→file, 003 DB→DB, 004 DB→file, 005 DB→DB (전부 OK, 결제)
   - 006 file→file OK / 007 file→file NG(1줄) / 008 file→**DB** NG(전각공백, export 경로의 NG 검출 시연) / 009 file→file NG(다줄) / 010 file→ERROR(종료코드 1)
   - 4사분면 커버: DB→DB(001,003,005), DB→file(002,004), file→file(006,007,009), file→DB(008).
4. **정의 파일을 Boss 7.1 구조에 가깝게**(경량 채움): `test_id / input{type,table,csv} / execution{shell_program,timeout} / output{type,table,file,export_csv} / comparison_rules / success_criteria`. 구조·필드명을 맞춰 인수 시 풀스키마 전환이 매끄럽게. 프로토에서 미사용 필드(comparison_rules 등)는 자리만 채움.
5. **오케스트레이션은 Python CLI 유지**(D-006) + 얇은 **`run.sh` 래퍼** 추가로 Boss "Shell 스크립트로 기동" 기대를 값싸게 충족.

**이유**:
- Boss가 명시한 입출력 4유형·다운로드 단계를 프로토에서 *실제 Working*으로 증명해야 인수 정합성·신뢰 확보.
- 정의 파일을 Boss 구조로 두면 도구의 핵심 가치(정의 파일 동적 적응)가 그대로 드러나고 풀스키마 전환 비용이 낮음.

**한계 / 인수 후 단계(deferred)**:
- HTML/Excel 리포트, `test_validation_results`·`mismatch_details` **DB 결과 저장**, InitialPlanning 7.2의 **정교 비교**(행/열·정렬·숫자 공차·날짜 정규화), pandas/jinja2/openpyxl 의존 → 인수 후. 프로토는 CSV+`.diff`+바이트 비교 유지(D-004/D-011, CLAUDE 3-5 의존 최소화).
- 결과 테이블·시연 도메인·stub은 시연 한정 — 실 운영은 고객 스키마·진짜 Net COBOL로 교체.

**D-021 보정**: D-021의 "schema.sql 변경 없음"·"flat 경량 정의 파일"은 본 결정으로 대체(결과 테이블 1개 추가 / Boss 구조 경량 정의 파일).

**검증 결과** (T2-3 완료):
- 기본 스위트(DB 없이) **53 passed / 6 skipped**. Docker PostgreSQL 16 + `RUN_DB_TESTS=1`로 **59 passed / 0 skipped**.
- 통합 검증된 경로: DB입력→파일출력(50건 CSV, 顧客名 조인), 파일입력→DB출력(`tobe_result`)→`export_table_to_csv` 다운로드(008 전각 공백 NG가 export까지 반영), 010 종료코드 1.
- E2E 시연 본질 확인: 같은 입력에 `--clean` 골든 vs NG 주입 출력 → comparator가 **007 NG(1줄, balance 1700000→1700001)** / 정상→**OK** 판정. Shift-JIS 일본어 왕복 정상.
- exporter 포맷(헤더=컬럼명·NULL→빈칸·`\n`·Shift-JIS)은 가짜 커서로 DB 없이 결정론 검증.

## D-023. Runner(`run_batch`) 정책

**결정**: stub 배치 실행기를 아래로 확정(T2-4). 리뷰 피드백 검토 후 결정.

1. **시그니처**: `run_batch(definition: ShellDefinition, config: Config, conn=None, *, clean=False) -> Path`.
   - ARCHITECTURE 4-3의 `run_batch(shell_id, ...)` 대신 **ShellDefinition을 받는다** — 입력/출력 type·shell_program 분기 정보를 재조회 없이 전달(더 깨끗).
   - `conn`은 **출력=database(export 다운로드)에서만** 사용. 파일 출력 셸은 `None` 허용(타입 `conn=None`).
2. **ERROR는 예외(RunnerError)로**: 종료코드≠0/timeout → `RunnerError`. 오케스트레이터(T3-1)가 셸별 try/except로 잡아 `ComparisonResult.ERROR`로 매핑한다. *예상된 ERROR도 '구조화된 결과'는 경계(comparator/orchestrator)에서 만들어지며*, Runner는 "산출물 유무"만 신호한다. → `RunResult` 구조체 도입은 `ComparisonResult`와 책임 중복이라 채택 안 함.
3. **shell_program은 실행파일로 직접 호출**(`[program, ...]`, 파이썬 하드코딩 금지). 실 Net COBOL 배치로 교체 시 런처 수정이 불필요해 교체 seam이 보존된다(우분투 전제 D-003, shebang+실행비트; Windows 범위 밖). 실 배치의 *본질* 계약은 `--shell-id` 하나이며 나머지 인자는 stub scaffolding.
4. **clean 플래그로 골든·To-Be 직렬화 통일**: 골든 생성(T4-1)은 `clean=True`로 **같은 Load→Run→export 경로**를 탄다. OK 셸은 `apply_ng_pattern`이 no-op이라 자동 byte-동일 → false-NG가 구조적으로 불가능. (DB 출력 셸의 To-Be는 exporter 직렬화이므로, 골든을 손으로/다른 도구로 만들면 통짜 바이트 비교가 깨진다 — 이를 원천 차단.)
5. **출력=database → exporter 후처리**: `export_table_to_csv(conn, output_table, output_path, encoding=config.encoding)`. 인코딩을 config에서 주입(하드코딩 금지, CLAUDE 3-3).
6. **비밀번호는 env로만**: argv가 아니라 `POSTGRES_PASSWORD` 환경변수로 전달(ps 노출 방지). 단위 테스트로 "argv에 비밀번호 없음" 회귀 가드.
7. **stub `--output-path` dead-arg 제거**: 출력=file일 때만 stub에 `--output-path`, 출력=database면 `--output-table`만 전달(진짜 배치 작성자가 I/O 계약을 명확히 읽도록).
8. **`BatchConfig.stub_path`는 deprecate(제거 보류)**: 셸별 stub은 `execution.shell_program`이 선택. 단 `test_settings`가 아직 단언하므로 T2-4에서 제거하지 않고 주석만(정식 제거는 별도 정리 Task).

**오케스트레이터(T3-1) 함의 — 통합 검증 중 발견**:
- exporter의 read SELECT는 `conn`에 열린 트랜잭션(`tobe_result` ACCESS SHARE 락)을 남긴다. 다음 셸 stub의 `TRUNCATE tobe_result`가 이와 충돌해 블로킹된다. → **오케스트레이터는 셸 단위로 트랜잭션 경계를 commit/rollback**해야 한다(SPEC 3-1 재확인).
- stub은 **별도 connection**으로 DB를 읽으므로, DB 입력 셸은 **loader 적재분을 stub 실행 전에 commit**해야 stub이 본다(load → commit → run → export → 셸 경계 정리).

**이유**: 리뷰의 🔴(골든-To-Be 직렬화 일치)을 clean 플래그로 구조적 해소. ERROR-예외는 기존 아키텍처(SPEC 8·T3-1)와 일관. 실행파일 직접 호출은 "재작업 없는 인수인계" 메타 기준 충족.

**검증 결과** (T2-4 완료):
- 기본 스위트 **63 passed / 9 skipped**, Docker PostgreSQL 16 + `RUN_DB_TESTS=1` **72 passed / 0 skipped**.
- mock 단위: db/file 입력 × file/db 출력 argv 정확성, 비밀번호 argv 미포함·env 전달, 종료코드≠0·timeout→RunnerError, db출력→exporter 호출, conn 없음→RunnerError.
- DB 통합: **OK db-출력 셸 골든(clean) vs To-Be(non-clean) byte 동일 → comparator OK**(false-NG 가드), 008 file→DB export 경로 NG 1줄 검출, 010 종료코드 1→RunnerError.

## D-024. 오케스트레이터(`run_full_comparison`) 정책 — T3-1

**결정**: E2E 오케스트레이터를 아래로 확정(T3-1). 리뷰 피드백(🔴 2건·🟡 2건)을 코드/SPEC에 대조 검증 후 전량 반영.

1. **배치·시그니처**: `src/core/orchestrator.py`에 `run_full_comparison(config: Config, on_progress: Callable[[ProgressEvent], None] | None = None) -> RunSummary`. `src/core/__init__.py`가 re-export(인터페이스 공통 진입점). 콜백 없이도 동작(DoD).
2. **진행 보고 = ProgressEvent 콜백**(ARCHITECTURE 5-3 옵션 A). `models.py`에 `ProgressKind`(SHELL_START/STEP/SHELL_DONE) + `ProgressEvent` 추가. Core는 print 금지(CLAUDE 3-1)라 구조화 이벤트만 던지고 출력은 인터페이스(T3-2) 담당. STEP은 SPEC 5-1의 load/run/compare 3단계에 매핑(출력=database 다운로드는 run 단계에 포함).
3. **정의 파일이 정본 — range/ids 폴백 제거(D-021 supersede)**: `config.definition_file`이 없으면 `DefinitionError`(fatal). D-021의 "정의 파일 없으면 config range/ids 폴백" 문구는 정의 파일이 flat·단순했을 때 결정이며, **D-022로 정의 구조가 input/output type·table·export_csv를 갖게 된 이후로는 shell_id만으로 정의를 합성할 수 없어 degenerate(전부 ERROR)**. 따라서 폴백은 dead code로 채택 안 함. (리뷰 🟡6a)
4. **`--shells` 필터는 T3-1에 넣지 않음**: `config.shell_ids`는 D-019로 항상 채워지므로(기본 1-10) 무조건 교집합하면 1-10 밖 test_id가 silent drop되고 "정의=정본"과 "config.shells=필터" 두 출처가 섞인다. T3-1은 **전체 정의 실행**, 부분 실행 필터는 T3-3(CLI)에서 명시적으로. (리뷰 🟡6b)
5. **DB connection 수명 = lazy + 접속 실패 fatal**: 정의 중 input/output이 database인 셸이 하나라도 있으면 루프 진입 전 connection 1회 생성, 끝에 close. **접속 실패는 `OrchestratorError`로 즉시 종료**(SPEC 8 "DB 접속 실패 → 즉시 종료"). DB가 전혀 필요 없으면 connect하지 않음(파일 전용 실행 견고). → 새 세션 초안의 "접속 실패 시 conn=None 진행"은 SPEC 8 및 자기 자신과 모순이라 폐기. (리뷰 🔴2)
6. **셸 단위 트랜잭션 경계(D-023 구현)**: 셸마다 ① DB 입력이면 `load_input_csv` 후 즉시 `conn.commit()`(stub은 별도 connection이라 commit해야 적재분을 봄), ② `finally`에서 `conn.rollback()`으로 exporter read 트랜잭션(`tobe_result` ACCESS SHARE 락)을 해제(다음 셸 stub의 `TRUNCATE tobe_result` 비블로킹). 적재분은 이미 commit됐으므로 rollback은 export 읽기락만 해제하며 안전.
7. **파일 입력 복사처 단일 진실(드리프트 차단)**: `runner.resolve_input_dir(definition, config)`를 public 헬퍼로 추출(우선순위 `config.tobe_input_dir` > `definition.input_dest_dir`). 오케스트레이터의 `copy_input_file` *복사처*와 Runner의 `_input_file_path` *읽기처*가 이 헬퍼를 **공유**한다. 초안이 우선순위를 반대로 적어 복사처≠읽기처 시 파일셸 전멸 위험이 있었음. (리뷰 🔴1)
8. **예외 경계**: `load_definitions`·DB 접속 등 루프 진입 전 오류는 전파(CLI가 SPEC 8대로 즉시 종료), per-shell 오류는 `Exception`으로 잡아 `ComparisonResult.ERROR`로 매핑(다음 셸 진행, SPEC 3-1). 실패한 단계는 STEP 이벤트에 step_status="ERROR"로 보고.

**검증 결과** (T3-1 완료):
- 기본 스위트(DB 없이) **71 passed / 10 skipped**, Docker PostgreSQL 16 + `RUN_DB_TESTS=1` **81 passed / 0 skipped**.
- mock 단위: 정의 파일 누락 fatal, DB 접속 실패 fatal, DB 셸 없으면 미접속, 콜백 없이 동작, 진행 이벤트 순서(SHELL_START→load/run/compare→SHELL_DONE), 한 셸 RunnerError가 다음 셸을 막지 않음(ERROR 격리), DB 입력 commit→셸 종료 rollback→close 순서, 파일 복사처=resolve_input_dir(tobe_input_dir).
- DB 통합: **연속 DB→DB 셸이 `run_full_comparison`에서 TRUNCATE 블로킹 없이 완주하고 골든(clean)==To-Be(non-clean)로 OK 판정**(D-023 ①②의 E2E 회귀 가드). 테스트는 transaction_log 시드를 스냅샷/복원해 suite 위생 유지.

**한계 / 인수 후 단계**: 콜백 기반 CLI 출력(T3-2)·argparse 진입점·종료코드(T3-3)·시연 샘플 데이터(T4-1)는 후속. SPEC 3-3의 "양쪽 파일 모두 없으면 처리 목록 제외"는 프로토에선 comparator 결과(both-missing→ERROR)를 그대로 기록(To-Be는 stub이 생성하므로 통상 발생 안 함).

## D-025. CLI 출력 모듈(`output.py`) 정책 — T3-2

**결정**: ProgressEvent 콜백을 받아 진행·요약을 출력하는 Interface 표시기를 아래로 확정(T3-2). 보고 전 자가검증 6항(`dc-self-review`)을 grep/read로 실행해 계약 갭을 선제 식별.

1. **API**: `src/cli/output.py`에 `CliReporter(*, use_color, verbose=False, stream=None)` — `on_progress(event)`(run_full_comparison 콜백) + `print_summary(summary, elapsed_seconds)`. 모든 이벤트가 index/total을 운반하므로 **무상태**. print는 Interface인 여기서만(Core는 금지, CLAUDE 3-1).
2. **🔴 "결과 비교" 판정은 SHELL_DONE.result에서 렌더(STEP(compare) 아님)**: SPEC 5-1의 `(N개 줄 차이)`·`└─ 첫 차이`는 `diff_lines`에서 나오는데, `diff_lines`는 `STEP(compare)`엔 없고 `SHELL_DONE.result`에만 있다. 따라서 load/run 단계 줄만 STEP 이벤트로 실시간 렌더하고, **compare 판정 줄 전체(상태·개수·첫 차이)는 SHELL_DONE에서** 렌더한다. `STEP(compare)`는 표시에 쓰지 않는다(데이터가 result의 부분집합 — 여기서 그리면 inline 개수 split/silent drop). SHELL_DONE은 compare STEP 직후라 실시간성(SPEC 9) 손상 없음. (자가검증 ①/④)
3. **ERROR 렌더**: 판정 줄을 만들지 않고 `└─ 오류: {error_message}`만 출력 — 실패 단계 STEP이 이미 `→ ERROR`를 표시했으므로(D-024 STEP(failing,"ERROR")). MISSING_*는 `▸ 결과 비교 → MISSING_TOBE` + 한 줄 설명.
4. **색상 3중 가드(SPEC 9)**: `should_use_color(config_color, stream) = config.output.cli_color AND ("NO_COLOR" not in env) AND stream.isatty()`. 파이프/파일 리다이렉트·NO_COLOR·비TTY에서 ANSI가 새지 않는다. 색은 표시 전용이라 판정·바이트 비교와 무관(자가검증 ⑤).
5. **🟡 verbose 계약 갭(deferred 명시, silent drop 금지)**: SPEC 5-3 verbose 3종 중 **diff 상세(모든 줄)만** 이벤트로 받을 수 있다(`result.diff_lines`). 배치 stdout/stderr·SQL 적재 로그는 ProgressEvent 계약에 없다(실패 시 stderr는 RunnerError→`error_message`에 일부 포함). → T3-2 verbose는 '모든 diff 줄 + 전체 error_message'로 한정. SQL/배치 stdout 로깅은 Core가 `logging`으로 내보내야 가능(CLAUDE 5 허용)하며 **T3-3에서 `--verbose` 시 logging 레벨 조정으로 배선**(deferred). 여기서 가짜로 만들지 않는다. (자가검증 ①/④)
6. **소요 시간 = 인터페이스(T3-3)가 측정해 주입**: `print_summary(summary, elapsed_seconds)`. 실행을 소유하는 쪽이 타이밍도 소유(단일 출처). output.py는 타이밍 부작용 없이 순수.

**검증 결과** (T3-2 완료):
- `tests/test_output.py` 15개(색 3중 조건·OK/NG/ERROR/MISSING 렌더·NG inline 개수+첫 차이·verbose 전체 diff·ANSI 유무·요약 포맷·D-016 합 항등) 통과. 기본 스위트 **86 passed / 10 skipped**, DB 통합 **96 passed / 0 skipped**.
- 시각 확인: SPEC 5-1 진행 표시(`[i/total]`·`▸`·`└─ 첫 차이`·색)·5-2 요약 배너 충실 재현.

**한계 / 후속**: argparse 진입점·`should_use_color`/`CliReporter` 배선·종료코드·소요시간 측정·`--verbose` logging 배선은 T3-3. 시연 샘플 데이터는 T4-1.

## D-026. CLI 진입점(`main.py`) 정책 — T3-3

**결정**: 사용자 실행 진입점을 아래로 확정(T3-3). 보고 전 자가검증 6항 실행 + 사용자 피드백 3건(①②③) 반영.

1. **흐름**: argparse → `load_config` → (`--report-dir`/`--shells`/`--verbose` 반영) → `CliReporter`를 `on_progress`로 배선 → `run_full_comparison` 호출 → `print_summary`. Core/Interface 분리(ARCHITECTURE 5) 유지. `run.sh`는 이미 완성(`exec python -m src.cli.main "$@"`)이라 불변.
2. **종료 코드**: `0`=전부 OK / `1`=NG·ERROR·**MISSING** 하나라도(=not all OK) / `2`=fatal 설정·접속 오류(ConfigError/DefinitionError/OrchestratorError → stderr 메시지, SPEC 8, 정상 요약과 분리). **① D-025의 종료코드 배선 메모(“ng+error>0이면 1”)를 supersede** — MISSING도 실패로 보아 1에 포함(D-016이 MISSING을 1급 카운트로 둔 것과 정합, “모두 OK면 0” 충족).
3. **`--shells` = 명시 선택(D-024 정합)**: `settings.parse_shell_selector(value)`가 `"1-10"`(inclusive)·`"001,002,005"`(목록)를 파싱 — 내부에서 **기존 `_normalize_shell_ids` 재사용**(zero-pad·inclusive·검증 규칙 드리프트 0, 자가검증 ①). 결과를 `run_full_comparison(config, shell_ids=...)`로 명시 전달.
4. **orchestrator에 `shell_ids` opt-in 파라미터 추가**: `run_full_comparison(config, on_progress=None, shell_ids: list[str] | None = None)`. None=전체(D-024), 주어지면 정의 중 해당 test_id만 **정의 파일 순서로** 처리. **정의에 없는 id 요청은 `DefinitionError`(fatal)** — silent drop 금지(자가검증 ④). 기존 호출/테스트는 None이라 무영향(additive).
5. **단일 진실**: 셸 선택 출처는 *정의 파일(메타데이터 정본) + `--shells`(명시 선택)* 둘뿐. config의 `shells:` 블록은 D-024 이후 **선택에 미사용(vestigial)** — 두 출처 혼동 방지차 명시(인수 시 config.shells 제거/재정의 검토 가능).
6. **`--report-dir`**: 주어지면 cwd 기준 절대화해 `config.report_dir` override(사용자 호출 위치 기준이 직관적).
7. **`--verbose`**: `CliReporter(verbose=True)`(모든 diff 줄) + **② 앱 네임스페이스 로거만 DEBUG**(`logging.getLogger("src")`에 전용 StreamHandler) — `basicConfig(DEBUG)`가 부르는 서드파티 로그 소음을 차단. 배치 stdout/SQL 적재 로그는 Core가 아직 `logging`으로 안 내보내므로 **여전히 deferred**(D-025 §5 일관, 가짜 생성 안 함).
8. **③ `--config` 기본 `./config.yaml`** 유지(SPEC 1-2 표).

**검증 결과** (T3-3 완료):
- `tests/test_main.py`(parse_shell_selector 4 + 배선/종료코드 9) + `test_orchestrator.py`에 shell_ids 필터 3개 추가. 기본 스위트 **103 passed / 10 skipped**, DB 통합 **113 passed / 0 skipped**.
- **실 CLI E2E 스모크**(dc-pg, 실 stub): `python -m src.cli.main`이 DB입력→DB출력(export)·DB입력→파일출력 2셸을 적재→배치→비교로 완주. 골든 부재 1차=MISSING_ASIS(exit 1) → To-Be를 골든화한 2차=OK ✓(exit 0). 연속 DB셸 트랜잭션 경계(D-023 ②)도 실 CLI에서 무블로킹 확인. 진행 표시·요약 배너·리포트 CSV 생성 SPEC 5 충실.

**한계 / 후속**: `--clean`(골든 생성)은 CLI 인자로 노출 안 함 — 골든 생성은 T4-1(시연 샘플 데이터) 단계의 책임. 시연용 asis 입력/정답지 CSV 작성이 T4-1.

## D-027. 시연 샘플 데이터 + 골든 생성 정책 — T4-1

**결정**: 시연용 As-Is 입력/정답지(골든)와 생성 도구를 아래로 확정(T4-1).

1. **입력 생성 = `tools/make_samples.py`**: `samples/asis/input/001~010.csv`를 Shift-JIS·`\n`으로 결정론 생성. 10개 모두 **`transaction_log` 8컬럼 헤더 통일**(DB 입력은 loader가 헤더 대조하므로 정확 일치, 파일 입력은 `branch_code` 무시). `customer_id`는 시드 `customer_master`(C0001~C0020)에 존재하는 값만 → stub이 顧客名 조인 enrich(SPEC 6-1·6-3). 입력은 전부 *정상값*이고 NG는 stub의 비-clean 위치 주입으로만 발생.
2. **🔴 골든 생성 = `tools/make_golden.py` (stub `--clean` 경로 재사용, 손작성 금지)**: 오케스트레이터와 동일한 `load → run_batch(clean=True) → (DB출력이면 exporter)` 경로로 To-Be를 만들어 `samples/asis/output/{id}.csv`로 복사. 골든과 실제 To-Be가 **같은 직렬화**(파일=`write_csv_file`/DB=`export_table_to_csv`)를 거쳐 통짜 바이트 비교(D-004)에서 false-NG가 구조적으로 불가능(D-023 §4 일관, self-review #5). `clean=True`라 NG 주입이 꺼진 정상 출력=골든. 010은 clean이면 실패 안 해 골든이 생기나 실제 실행(비-clean)은 RunnerError→ERROR라 비교 안 됨(골든 미사용).
3. **NG 위치 요건(SPEC 6-5)을 입력이 충족**: 007 첫 행 `balance_after` 변형(≥1행) / 008 첫 행 `customer_name` 전각공백(첫 행 유효 고객) / 009 row0·1·2 변형(≥3행) / 010 stub 종료코드 1. `tests/test_samples.py`가 이 불변식을 DB 없이 가드.
4. **순환 import 해소(골든 생성 중 발견)**: `core.__init__`가 `orchestrator`를 즉시 import하고 orchestrator가 `config.definition`을, 그게 다시 `core.models`를 import해 **core↔config 순환**이 잠복해 있었다(`python -m src.cli.main`은 import 순서 운으로 회피, `config.definition` 선(先) import 시 ImportError). → `core/__init__.py`를 **PEP 562 `__getattr__` 지연 로딩**으로 바꿔(`from src.core import run_full_comparison`은 그대로 동작) 순환을 끊었다. orchestrator의 `config.definition` import는 모듈 레벨 유지(테스트 monkeypatch seam 보존).
5. **실행 설정**: `config.yaml`은 gitignore(환경별 실값) — 로컬은 dc-pg 호스트 포트 **5433**(RegShift와 병렬, D-... 메모리). 비밀번호는 `POSTGRES_PASSWORD` env.

**검증 결과** (T4-1 완료):
- `python -m src.cli.main --config config.yaml` E2E: **OK 6(001~006) / NG 3(007,008,009) / ERROR 1(010) / MISSING 0**, 종료코드 **1**. NG가 SPEC 6-5 의도대로 표시(007 balance 1710000→1710001 1줄 / 008 田中太郎→田中　太郎 전각공백 / 009 3줄). 리포트 CSV(UTF-8 BOM·일본어·diff 상세) + 007/008/009 `.diff` 생성.
- 정상 셸 6건 모두 골든=To-Be byte 동일(false-NG 0). DB 출력 셸(001,003,005,008)도 exporter 경로 일치.
- 테스트: 기본 **103→109 passed**(test_samples 6 추가)/10 skipped, DB 통합 **113→119 passed**/0 skipped. 순환 import 양방향 회귀 가드 통과.

**한계 / 인수 시 교체**: 입력·골든은 시연 한정. 실 클라이언트 데이터로 교체 후 `make_samples`/`make_golden`을 재실행하면 골든이 재생성되는 자산(시연 데이터 교체 포인트). `make_golden`이 stub `--clean` 경로를 재사용하는 한 진짜 배치로 바꿔도 원리 유지.

## D-028. GUI = 로컬 웹 UI(Flask), Core 재사용 + 업로드 검증 — Phase 5

**결정**: 시연용 GUI를 **로컬 웹 UI(Flask)**로 추가한다(`src/gui/`). Core는 무수정. 두 모드: ① 데모 10셸 자동 실행 ② 업로드 1쌍(As-Is 입력+정답) 풀체인 검증.

1. **프레임워크 = Flask**: ARCHITECTURE 7이 "Flask/FastAPI는 GUI 단계에서 결정"으로 열어둔 지점 — 채택은 계획대로(경량 의존 1개 `flask>=3.0`, CLI는 불요).
2. **Core 재사용(무수정)**: CLI와 동일하게 `run_full_comparison(config, on_progress, shell_ids)` 호출 + `ProgressEvent`/`RunSummary` 소비. D-006/D-025 콜백 설계(GUI 이식 전제) 검증됨.
3. **실시간 진행**: 백그라운드 스레드 + 콜백→큐→스트림. 데모=SSE(`/run`), 업로드=NDJSON(`/verify/run`, POST 멀티파트). 종료 시 `done`으로 클라가 스트림을 닫음.
4. **§① traversal 차단**: `/report/<name>`은 `secure_filename` + `report_dir` 하위 재확인(이중 가드).
5. **§② dict 직렬화는 `src/gui/serialize.py`에만** — `core/models.py` 불변(CLAUDE 3-1).
6. **§③ 동시 실행 1건 + 락 try/finally 해제** + `app.run(threaded=True)`.
7. **§④ 브라우저 자동 오픈**: `web.py:main()`이 `webbrowser.open`(Timer). `run_gui.sh`가 위임.
8. **비밀번호는 UI에 없음** — `POSTGRES_PASSWORD` env만(D-019 일관).

**업로드 검증(Phase A)**: `src/gui/upload.py:prepare_job`이 업로드 1쌍을 **임시 작업폴더 + 임시 1-셸 정의 파일**로 만들어 `run_full_comparison(temp_config, shell_ids=["up1"])`에 먹인다 → 파이프라인 전부 재사용. 리포트는 base `report_dir`에 떨어져 `/report` 재사용, 임시폴더는 finally에서 rmtree.
- **한계(흐름 시연용)**: 신환경 배치가 stub(데모 스키마 고정)이라 입력 CSV는 `transaction_log` 스키마, 정답 CSV는 Shift-JIS여야 OK. 진짜 다규격·실데이터 검증은 stub→실 배치 교체 후(Phase B). DB 입력 실행은 `transaction_log`를 덮어쓰며 다음 데모 실행 시 자가 복구(D-023).

**Phase B(실 검증 지향, 후속)**: 업로드 UI에서 입력 테이블·배치·출력 테이블 직접 지정(데모 도메인 탈피) + 무시 규칙·정교 비교(D-022).

**검증**: `tests/test_gui.py` 14개 통과(직렬화·라우팅·SSE/NDJSON·traversal·prepare_job), 기본 스위트 123 passed. 실 스택 스모크(Flask+dc-pg): `/run` OK6/NG3/ERROR1, `/verify/run` 샘플 001 OK·변조 시 NG.

**🔴 버그 메모(2026-06-01) — pytest 시 작업트리 삭제, 원인 규명·수정 완료**: GUI 작업 중 `pytest`(전체 suite) 실행 직후 작업 디렉토리가 통째로 삭제되는 현상이 수 차례 발생. **원인은 하네스/홈-git-repo가 아니라 본 코드의 테스트 버그였음**: `tests/test_gui.py`의 `test_verify_run_streams_then_summary`가 `web.prepare_job`을 `(_, Path("."))`로 mock → `verify_run`의 cleanup이 `shutil.rmtree(Path("."))`=**cwd(repo 루트)를 통째 삭제**. pytest가 repo 루트에서 돌아 repo 전체가 날아감(`.pytest_cache`만 직후 재생성). **일회용 클론 전체 suite 실행으로 재현 확정.**
- **수정**: ① `web._cleanup_tmpdir()` 도입 — `tempfile.gettempdir()` **하위 경로만** 삭제(잘못된 경로·cwd는 거부). ② 테스트 mock이 `Path(".")` 대신 **실제 `mkdtemp()`** 반환. ③ 회귀 가드 테스트 2개(`test_cleanup_tmpdir_*`). 이후 전체 suite 실행해도 작업트리 안전.
- (홈이 git repo인 것은 별개의 잠재 위험으로 점검 권장이나, 이 삭제의 원인은 아니었음.)

---

## D-029. 웹 GUI "납품 대비 제품" 격상 — 연결설정·다건업로드·일본어UI — Phase 6

**결정**: Phase 5 GUI(D-028)를 **납품 대비 수준**으로 격상한다. Core·`models.Config`는 **무수정** 유지하고 `src/gui/`만 확장한다. (단 *진짜 납품급 QA*는 실 배치·실데이터 없이는 불가 — 작은 샘플로 "납품 대비 구조"를 갖추는 것이 목표, 사용자 합의.)

1. **연결 설정(신규 핵심) — `src/gui/connection.py`**: 화면에서 비-비밀 접속정보(host/port/dbname/user/password_env)·인코딩·검증정의(입력/출력 테이블·배치경로·I/O타입)를 받는다 = `config.yaml`/`test_definition.yaml`을 손으로 안 쓰는 정의 자동생성.
   - **`test_connection`(읽기전용)**: `psycopg2.connect(connect_timeout=3)` + `SELECT 1` + **조건부** 테이블 존재 확인 — `input_type==database`면 입력 테이블만, `output_type==database`면 출력 테이블만(파일 흐름은 확인 안 함, 오탐 방지). DDL·쓰기 없음(운영 DB 오염 차단). 테이블 확인은 **public 스키마 가정**(loader/exporter와 동일하게 `table_name`만 조회) — schema-qualify는 deferred(설치 시).
   - **비밀번호 = 모델 A(D-019 §6 확장)**: 폼은 비밀번호를 **받지도 저장도 안 한다**. 서버 env[`password_env`]에서만 끌어오고, 없으면 `.pgpass`/trust에 위임(안내만). 일본 보안심사 유리.
2. **저장 분리(★Core 무수정 보존)**: `save_connection`은 **DB 접속·인코딩만** `config.yaml`에 **원자적 저장**(`.bak` 백업 → tmp write → `os.replace`). 검증정의값(테이블·배치·타입)은 `Config` 필드가 아니라 `ShellDefinition` 값이라 저장 시 `models.Config` 확장이 필요 → 저장하지 않고 `/verify/run` **폼으로 전달**(+클라 localStorage 기억). 평문 비밀번호는 절대 기록 안 함(`password_env` 이름만).
3. **다건 업로드 — `prepare_job` → `prepare_jobs`**: N쌍을 받아 **N-셸 임시 정의**를 만들고 엔진(`run_full_comparison`)이 순차 처리. 입력/출력 테이블·배치경로를 **인자로 파라미터화**해 D-028 PhaseB가 예고한 `_DEMO_*` 하드코딩(`transaction_log`/`tobe_result`)을 제거. 짝짓기는 **파일명 stem 일치**(고객 규약 — UI 명시). 짝 안 맞는 파일은 **silent drop 금지** — `PairingInfo`로 돌려줘 화면에 warning으로 명시 노출, 매칭 0건은 `UploadError`. 같은 stem 중복 업로드는 모호성 거부.
4. **UI 전면 일본어**: `index.html` 표시 문구 + `web.py` 사용자向け 메시지(업로드 누락·중복·413 등)를 일본어로. **Core 예외·CLI·리포트 문구는 deferred**(한국어 유지) — 배치 실패 등 Core 한국어 메시지가 JP 화면에 노출되는 건 용인(사용자 합의). 코드/주석도 한국어 유지.
5. **라이트 UI 세련화**(다크 철회): 짙은 헤더→라이트 헤더(흰 배경+보더+액센트 바), 여백·타이포·카드 정돈. 3탭 재구성(접속설정/업로드검증/데모), 연결설정 2섹션 분리(DB접속/검증정의). diff 하이라이트 로직(d760188)은 보존.
6. **온프레미스 경량 유지**: 바닐라 HTML/CSS/JS, **CDN·웹폰트·빌드 0**, 의존성 `flask>=3.0` 1개. 폴더(`webkitdirectory`)+다중파일 업로드. **MAX_CONTENT_LENGTH + 413 친절 에러**. `_cleanup_tmpdir` 임시-하위-only 가드 유지(작업트리 삭제 재발 차단, D-028 §버그메모).

**이유**: 도구 가치는 "As-Is==To-Be" 판정이고 stub은 "이행된 배치" 대역이라 E2E QA가 stub으로 가능 — 실제와 다른 건 **운영 연결**(고객 계정·실 배치·실 스키마)뿐이라 ①연결설정이 핵심. Core 무수정·정의 파일 주도 계약을 유지하는 한 GUI는 독립 격상 가능(D-006/D-028).

**범위 밖 = deferred**: 정교 비교·무시 규칙(D-022), 대용량·성능·인코딩 엣지 QA, 진짜 Net COBOL 배치 연결(설치 시 `shell_program` 교체), Core 예외·CLI·리포트 일본어화, 실 설치 패키징(휠·인스톨러), schema-qualify, 다중 DB 도메인.

**검증**: `tests/test_gui.py` 25개(직렬화·라우팅·다건 짝짓기/미매칭/중복·connection 저장/조건부테이블·413·cleanup 가드) 통과, 전체 144 passed(DB 통합 포함, dc-pg 5433). 실 스택 라이브 스모크: `/connection/test` OK+조건부 테이블·잘못된 포트 친절 실패 / `/verify/run` 다건 001 OK+002 NG(diff)·미매칭 003·099 명시 제외.

---

## D-030. 정의 파일 주도 업로드 검증 — 셸별 정의 yml 업로드 (Phase B 일부 선반영)

**결정**: 업로드 검증에 **정의 파일(`test_definition.yaml`) 주도 모드**를 추가한다(D-028 Phase B의 "셸별 정의" 일부 선반영). 정의 파일을 업로드하면 그것이 **정본**이 되어 셸별 입력/출력 타입·테이블·배치를 정의대로 N셸 검증한다. Core·`models` 무수정, `src/gui/`만 확장.

1. **두 모드 양립**: ① **개별 업로드(폼 3칸)** — 동질 묶음(D-029) / ② **정의 파일 주도** — 셸마다 타입·테이블·배치가 다른 실무 케이스. `/verify/run`이 `definition` 파일 유무로 분기한다. 정의 파일이 있으면 폼 3칸(타입·테이블·배치)은 **무시**되고 정의가 우선한다.
2. **파싱·재사용**: `summarize_definition`(파싱 미리보기, 읽기전용 `/definition/parse`) + `prepare_jobs_from_definition`이 `load_definitions()`로 검증 후, 정의의 `input_csv`/`expected_output_csv` **파일명을 업로드 CSV(stem)와 매칭**해 임시 작업폴더에 배치하고 정규화 정의를 만들어 `run_full_comparison`에 먹인다(엔진 무수정).
3. **shell_program 절대화**: 업로드 정의의 상대 배치경로(`stub_batch/...`)는 **repo 루트 기준 절대경로**로 정규화해 임시 디렉토리 기준 오해석을 막는다(`prepare_jobs`와 동일 규칙, 자가검증 ⑤). 절대경로(실 배치)는 그대로 둔다.
4. **silent drop 금지(④)**: 정의의 셸 중 입력/정답 CSV가 빠진 셸은 조용히 버리지 않고 `DefIngestInfo.excluded`로 돌려줘 화면에 warning으로 명시한다(유효 셸만 실행, 0건이면 `UploadError`).
5. **단일 진실**: 정의 파일이 정본이라는 D-021/022 원칙을 GUI로 노출한 것일 뿐 — 엔진/정의 로더/트랜잭션 경계는 그대로 재사용(드리프트 없음).

**이유**: 실무 검증은 셸이 수십~수백 개이고 셸마다 정의가 다르다. 화면 3칸으로는 동질 묶음만 처리되므로, **고객이 가진 정의 파일을 그대로 받는 것**이 가장 실무적이고 우리 정의-주도 아키텍처와 정확히 맞는다(사용자 요청).

**범위 밖 = deferred(유지)**: 정교 비교·무시 규칙(D-022), 진짜 Net COBOL 배치 연결(설치 시 `shell_program` 교체), Core/CLI/리포트 일본어화, 실 설치 패키징, schema-qualify, 다중 DB 도메인. 정의 파일에 매칭되는 입력/정답 CSV는 여전히 함께 업로드해야 한다(원격 경로 참조는 deferred).

**검증**: `tests/test_gui.py` 34개(정의 파싱·정의주도 빌드·누락제외·zero-match·`/definition/parse`·`/verify/run` 분기 포함) 통과. 실 스택 라이브 스모크(dc-pg 5433): 실 `test_definition.yaml` 업로드 → `/definition/parse` 10셸 인식, `/verify/run` 정의 주도로 입력10+정답10 → **OK6/NG3/ERROR1**(데모 SPEC 6-5 매핑과 일치), 누락 셸 warning 노출.

---

## D-031. 매핑표(CSV) → 정의 yaml 자동 생성 — 수기 yaml 제거

**결정**: 고객의 셸-테이블 **매핑표(CSV)** 한 장으로 `test_definition.yaml`을 자동 생성한다. "정의 파일 주도(D-030)"가 *읽기*였다면, 이건 *생성* — 손으로 yaml 문법을 짜지 않게 한다(대량 셸 자동화).

1. **`definition_from_mapping(csv) -> {ok, yaml, count, shells, errors}`**: 필수 열 `shell_id·input_type·output_type`, DB 타입 쪽은 `input_table`/`output_table` 필수. 나머지(`input_csv`·`expected_output_csv`·`export_csv`·`output_file`·`batch_program`·`test_name`·`timeout`)는 비면 관례 기본값(`{shell_id}.csv` 등, 배치 공란→동봉 stub). 열 이름 대소문자 무시, `utf-8-sig`/`cp932` 디코드(Excel 저장 대비).
2. **엄격 생성(④)**: 한 행이라도 오류(필수 누락·중복 shell_id·잘못된 타입)면 `ok=False`·`yaml=""`로 **생성 거부** — 부분 생성으로 "전체 검증" 착시를 막는다. 행 번호별 오류 메시지 반환.
3. **round-trip 검증(⑤)**: 생성한 yaml을 `load_definitions()`로 다시 파싱해 깨진 정의 생성을 차단.
4. **GUI 흐름**: 업로드 탭의 "マッピング表(CSV)から生成" → `/definition/from-mapping`(읽기전용) → 미리보기 + `定義YAMLダウンロード`(다운로드) + **그대로 검증**(생성 yaml을 definition으로 전송, D-030 경로 재사용). 업로드 yaml과 상호 배타. `samples/shell_mapping.example.csv`(10셸) 동봉.
5. **빈 양식 배포(규격 제공)**: 고객이 "뭘 적을지" 고민 않게 **매핑표 템플릿**(`MAPPING_TEMPLATE_CSV` = 필수열 + `batch_program` + 기입 예시 2행)을 `/definition/mapping-template`(GET, BOM 부착 — Excel 깨짐 방지)로 다운로드 제공. 받아서 값만 채워 올리면 정의 자동 생성. 템플릿 자체가 유효 매핑표라 그대로 올려도 동작.
6. **`batch_program` = 구↔신 배치 매핑(이 표의 핵심)**: 매핑표의 `batch_program` 열에 셸별 **이행된 신환경 배치 실행파일 경로**를 적는다(공란=동봉 stub, 데모). 도구가 끝내 알 수 없는 유일한 사실(메인프레임 잡↔이행 실행파일)을 여기서 1회 받는다(D-032에서 접속탭 배치칸을 뺀 것과 짝 — 배치 매핑의 자리는 매핑표/정의 파일 한 곳). 데이터로 유추 불가·이름 규칙 없음·변환 당사자만 아는 값이라 자동 결정 불가; 도구는 테이블 목록·배치 디렉토리 제시 등 *적기 보조*만 가능(후속 가능).

**이유**: "수기 작성은 자동화가 아니다"(사용자). 셸별 정의의 *사실*(어느 테이블·배치)은 데이터로 유추 불가라 표로 받되, **yaml 문법 작성은 도구가** 한다. 수백 셸이면 표 한 장으로 정의 일괄 생성.

**deferred(유지)**: Excel(.xlsx) 직접 파싱은 안 함(의존 최소화 — "CSV로 저장"; CLAUDE 3-5). 매핑표 자동 추론(파일만으로 테이블 유추)은 불가(설계상). 그 외 D-029/030 deferred 동일.

**검증**: `tests/test_gui.py` 39개(생성·round-trip·필수열·중복·DB테이블·엔드포인트 포함) 통과. 라이브: `samples/shell_mapping.example.csv` → `/definition/from-mapping` 10셸 yaml 생성 → 그 yaml을 정의로 `/verify/run`(샘플20) → **OK6/NG3/ERROR1**(데모와 동일).

---

## D-032. 탭 순서·역할 분리 — 검증 우선, 연결설정 검증정의칸 축소

**결정**: 같은 검증정의를 두 곳(연결설정 폼 3칸 vs 업로드 탭 정의파일/매핑표)에서 받아 생기던 혼란을 역할 분리로 해소한다.

1. **탭 순서**: `アップロード検証(主) → 接続設定 → サンプルデモ`. 사용 빈도(검증이 잦음)에 맞춤. 접속은 1회성 준비라 2번째.
2. **연결설정 섹션 축소**: "検証定義（テーブル・バッチ・I/Oタイプ）" → **"接続テスト用テーブル／簡易モード既定"**. 의미를 "①접속 테스트가 존재확인할 테이블 ②정의 없이 CSV만 올리는 간단 모드의 기본값"으로 한정. **배치 경로 칸 제거**(접속 테스트는 배치 불요, 실배치는 정의 파일이 정함, 간단 모드는 입력타입별 동봉 stub 자동). 검증 정의의 **정본은 업로드 탭의 정의파일/매핑표**임을 안내문에 명시.
3. **연결성 안내**: 업로드 탭 상단에 "초회는 접속설정에서 접속 저장" 한 줄.

**이유**: 역할(연결=접속, 업로드=정의)이 또렷해지고, 반복되던 "이 3칸에 뭘 넣나" 혼란이 사라진다. 배치 칸 제거로 "stub=데모 / 실배치=정의파일" 경계도 분명.

**검증**: `tests/test_gui.py` 40개 통과. 라이브 렌더: 업로드 탭 active·접속설정 숨김·섹션 리라벨·배치칸 제거 확인. 간단 모드(정의 없이 CSV만)는 서버가 입력타입별 동봉 stub 자동 선택(`prepare_jobs` batch=None).

---

> 새로운 결정이 생기면 아래에 추가:
>
> ## D-XXX. (제목)
> **결정**: ...
> **이유**: ...
