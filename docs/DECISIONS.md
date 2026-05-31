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

---

> 새로운 결정이 생기면 아래에 추가:
>
> ## D-XXX. (제목)
> **결정**: ...
> **이유**: ...
