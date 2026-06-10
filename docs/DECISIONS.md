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

## D-033. 기획서 7.1 풀스키마 복원 — 다중 입력·다중 출력 (브랜치 feat/fullschema-multi-io)

**배경**: D-021/022에서 Boss 기획 7.1 정의 구조를 프로토용 **경량화(입력 1·출력 1)**했는데, 실 운영 배치는 7.1대로 **한 셸이 여러 테이블/파일을 입력으로 읽고(조인), DB와 파일로 동시에 출력**하는 경우가 흔함(사장님 확인). 따라서 7.1 풀스키마(다중 입력·다중 출력)를 **복원**한다. 이는 새 설계가 아니라 프로토 단순화의 supersede이며, 코어(범용 적재/추출/바이트비교)는 그대로 재사용한다.

**확정 결정(회의)**: ① **다중 출력 흔함** → 출력 단위 집계(셸이 아니라 **출력**당 OK/NG, 리포트/카운트/필터). ② **다중 입력(매번 여러 테이블 적재) 필요**. ③ 한 셸의 **프로그램 여러 개는 잡 1개로 묶어 1회 실행 + 최종 출력만 비교**(다중 배치 실행 로직 불요). ④ 입력 방식은 **정의 파일(yaml) 우선**, 매핑표(long CSV)는 후속.

**단계화(안전)**: 파급이 격리된 **다중 입력(P1)** 먼저, 결과 단위가 바뀌는 **다중 출력 캐스케이드(P2)**는 별도.

**P1 — 다중 입력(완료)**: `InputSpec`(csv/type/table/dest_dir) 추가, `ShellDefinition.inputs: list[InputSpec]`. 정의 로더가 신형 `input.tables:[...]`와 구형 단일(`input.table`)을 **모두 파싱→inputs[]로 정규화**(단일 호환 필드는 inputs[0]에서 파생, `__post_init__`가 직접생성 시도 백필 — 단일 진실). 오케스트레이터 `_load_step`이 inputs[]를 **루프 적재**(DB 적재마다 commit, D-023 ① 유지), `_needs_db`도 입력 다건 반영. **하위호환**: 기존 단일형 정의·테스트 무수정 통과(160 passed). 코어 함수(`load_input_csv`)는 그대로 재사용(드리프트 0).

**P2 — 다중 출력(예정, 게이트)**: `output[]` 리스트(각 expected) + runner 다중 출력 추출 + `ComparisonResult.output_name`(셸당 결과 N개) + 리포트 (test_id,output_name) 행 + RunSummary total=출력 수 + 진행 이벤트/ GUI 출력별 표시·카드·필터. **결과 단위 변경(셸→(셸,출력))이 최대 파급** — D-016 합항등 유지, total 의미를 출력 수로 못박음.

**SPEC 영향**: 현 SPEC은 단일 입출력 전제 → 본 결정이 명시적 supersede(SPEC/매핑표 형식은 P2에서 갱신).

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

---

## D-034. UI 경량화 + 정의 파일 주도 일원화 (T7-3 / 회의 2026-06-03 방향)

**결정**: GUI를 회의 확정 방향 — **"버튼 1개 → 자동 실행(Shell 1~1000) → 실시간 모니터링 → 결과"** — 로 경량화한다. 운영 타깃은 **디렉토리 기반**: 데이터·정답·정의 파일이 `config.yaml`이 가리키는 디렉토리에 이미 있고(설치 시 준비), 화면은 그 정의를 그대로 실행만 한다(`/run` SSE = CLI와 동일한 `run_full_comparison(config, on_progress)`). **Core·models 무수정**, `src/gui/`만 변경.

1. **단일 화면**: ① **設定/接続**(접이식 `<details>`, 정의 미리보기 실패 시에만 펼침) — 접속테스트(읽기전용)·config.yaml 저장. 설치 시 1회. ② **検証実行** — config 정의 파일을 요약해 **실행 전 미리보기**(N셸 + 셸별 I/O 타입, 다중 입출력은 `×N` 카운트, T7-1/T7-2 반영) 후 [検証実行] 버튼 → 실시간 모니터링(셸 행·3단계·출력별 블록) → 요약(출력 단위)·카드 필터·리포트.
2. **걷어낸 것(불필요·간결, 사용자 지시)**: 3탭+위저드, **테이블선택 3칸 폼**(input/output type·table), 브라우저 **업로드-CSV 검증**, **매핑표→yaml 생성**. 그에 딸린 라우트(`/verify/run`·`/definition/parse`·`/definition/from-mapping`·`/definition/mapping-template`)·`upload.py` 미사용 함수(`prepare_jobs`·`prepare_jobs_from_definition`·`definition_from_mapping`·`MAPPING_TEMPLATE_CSV` 등)·해당 테스트를 제거. → **D-028~031(Phase 5/6 업로드·매핑 자산)을 supersede**(git 브랜치에 이력 보존, 필요 시 복원).
3. **검증 정의의 정본 = 정의 파일**(DEFINITION_SPEC). 화면에 입력타입·테이블 선택칸을 두지 않아 "화면 3칸 vs 정의 파일" 드리프트 원천을 제거(자가검증 ②). 셸마다 타입·테이블·배치가 다른 실무 케이스를 정의 파일이 그대로 표현.
4. **재사용>재구현(자가검증 ①)**: 실시간 모니터링·요약/필터·diff 렌더·`/run` SSE·접속테스트/저장·`summarize_definition`(미리보기로 재사용)은 그대로 — 경량화는 **삭제가 아니라 정의 파일 주도로의 흡수**.

**이유**: 회의 확정 — 실 운영은 셸 수십~수백(최대 1000)이라 브라우저 업로드가 아니라 디렉토리 기반이어야 하고, 검증 내용은 정의 파일 한 곳이 정본이어야 한다. 업로드/매핑 UI는 프로토 시연·준비용 자산이었으나 운영 화면에선 불필요. "불필요한 건 제거하고 간결하게"(사용자).

**deferred(유지)**: 정교 비교·무시 규칙(D-022), 매핑표(long CSV)→정의 생성(보조 도구로 분리 가능), 물리 다중 DB 접속, Core/CLI/리포트 일본어화, 실 설치 패키징. **SAM 등 확장자 실데이터 QA**(2순위)는 별도.

**검증**: `tests/test_gui.py`(직렬화·`/run` SSE·report traversal·연결설정 저장/테스트·정의 미리보기 임베드·다중I/O 카운트) 그린. 라이브 렌더: 단일 화면, 업로드/매핑 어휘 부재, 정의 미리보기 N셸 표시.

---

## D-035. 매핑표(Long CSV) → 정의 yaml 생성 — 독립 도구·다중 입출력 (D-031 풀스키마 후속)

**결정**: 수기 YAML을 피하려고 고객이 **스프레드시트(CSV)** 로 셸-입출력 매핑을 채우면 `test_definition.yaml`로 변환한다. D-031(GUI 매핑표→yaml)이 **단일 입출력(셸당 1행)** 만 됐고 T7-3(D-034)에서 GUI와 함께 제거됐는데, 사용자 요청으로 **풀스키마(다중 입출력) + 독립 도구**로 복원한다.

1. **Long 형식**(셸당 1행 불가의 해법): 한 셸이 입력 N·출력 M(가변 길이)이라 납작한 1행으론 부족 → **입출력 항목당 1행, `shell_id`로 그룹화**. 열: `shell_id·kind(input|output)·type(database|file)·program·table·file·expected·name·test_name·timeout`. `file`=입력CSV/ DB출력 export CSV/ 파일출력 산출파일. `program` 공란=동봉 stub(첫 입력 타입 기준, 데모).
2. **독립 CLI 도구** `tools/mapping_to_definition.py`(make_golden.py처럼 tools/): `python tools/mapping_to_definition.py mapping.csv -o test_definition.yaml`. **GUI에 넣지 않음** — T7-3(D-034) 경량화 유지. 설치 준비용: CSV 채움→변환 1회→yaml→config의 `definition_file`→경량 GUI/CLI로 실행.
3. **로더 실필드명으로 방출**(input.tables[] + outputs[] + execution.shell_program + test_id) — 규격서(DEFINITION_SPEC)의 *목표* 명칭이 아니라 `src/config/definition.py`가 실제 읽는 이름. 핵심 로직 `mapping_to_definition(csv_text)->{ok,yaml,count,shells,errors}`로 분리(테스트 가능).
4. **엄격 생성 + round-trip**(D-031 §2·3 계승): 한 행이라도 오류(필수열·kind/type·file/table/expected 누락·셸당 입출력 0건·program 불일치)면 전체 거부(부분 생성=전체검증 착시 차단, 행 번호 메시지). 생성 yaml을 `load_definitions`로 재파싱해 깨진 정의 차단. Excel 대비 utf-8-sig/cp932 디코드.
5. **예시 교체**: `samples/shell_mapping.long.example.csv`(Long, 다중 입출력 셸 001 + 단일 002) 동봉. 옛 단일 입출력 `samples/shell_mapping.example.csv`(D-031, GUI 기능과 함께 사장)는 제거 — git 이력 보존, 혼동 방지. YAML 템플릿(`test_definition.template.yaml`) 헤더에 이 CSV 경로를 안내(쉬운 작성 경로).

**이유**: "CSV가 YAML 손코딩보다 쉽다"(사용자). 셸별 정의의 *사실*(테이블·배치)은 데이터로 유추 불가라 표로 받되, yaml 문법은 도구가 짠다. 다중 입출력은 Long 형식이라야 표현되며, 운영 화면(경량 GUI)과 분리된 **설치 준비 도구**라 T7-3 방향과 양립한다.

**deferred(유지)**: Excel(.xlsx) 직접 파싱 안 함(CSV로 저장 — 의존 최소화, CLAUDE 3-5). 매핑 자동 추론(파일만으로 테이블 유추) 불가. 정교 비교(D-022) 등 동일.

**검증**: `tests/test_mapping_to_definition.py` 12개(다중I/O 그룹화·round-trip·필수열·kind/type·expected/table 누락·출력0건·program 불일치·CLI·동봉예시) 통과. 전체 148 passed(+DB skip). CLI 스모크: 동봉 예시 → 셸 001(입력3·출력2)/002(입력1·출력1) yaml 생성, 로더 통과.

### D-035 보조. 체크리스트 → 기입용 매핑 템플릿 (고객 작성 흐름)

고객의 **Test case가 "검증 항목 체크리스트"**(전각 체크·맥시멈 체크 200byte·… 식)인 것이 확인됨(사용자). 이를 정의 파일로 잇기 위해:

- **검증 단위(셸 1건) = 체크리스트 항목 1개**. 같은 배치를 여러 항목으로 시험하면 정의 엔트리 여러 개(`program` 반복, `test_name`만 다름). 결과는 출력 통짜 바이트 비교이며, **항목 분류·판정은 안 함**(diff만 제공; 전각/반각 무시 같은 규칙 비교는 정교비교 D-022 deferred).
- **순서·추적**: 정의(=CSV 행) 순서대로 실행·리포트 → **체크리스트 순서로 정렬**. `test_id`=항목번호, `test_name`=항목명 → 리포트·화면에 항목명 표시(1:1 추적). 디렉토리는 "순서"가 아니라 **파일명**으로 묶임(폴더 평평, 명명으로 항목 구분; 서브폴더 분할은 모델 밖).
- **고객 작성 흐름**: 우리가 **기입용 템플릿**을 만들고 고객이 채워 반환. `tools/checklist_to_template.py`가 **체크리스트 항목명 목록 → 빈 매핑 CSV 템플릿**(항목마다 입력행+출력행, `shell_id` 자동 zero-pad, `test_name` 선반영) 생성. 고객은 빈 칸(type·program·table·file·expected)만 채우고 다중 입출력은 행 추가. 미기입 템플릿은 변환기가 거부(채우라는 신호). 채운 CSV → `mapping_to_definition.py` → yaml.

**미결**: 고객 체크리스트의 **실제 파일 형식**(텍스트/엑셀/표)에 맞춘 입력 어댑터는 샘플 확인 후(현재 생성기는 "1줄=1항목" 텍스트 입력 전제, 앞 번호/불릿 제거). **검증**: `tests/test_checklist_to_template.py` 6개 + `test_mapping_to_definition.py` 12개 통과.

### D-035 보조2. 빈 파일명 자동 채움 (내용은 수기, 파일명은 규칙)

**가정 확정(사용자)**: 정의 파일의 **내용물(어느 셸·입력/출력 테이블·배치·항목)은 고객/수기로** 채우고(데이터로 유추 불가한 사실), 도구는 **파일명처럼 규칙으로 정해지는 것만** 자동 채운다. → `mapping_to_definition.py`가 `file`·`expected` 빈 칸을 자동 채움(둘 다 선택 열로 강등, `table`은 DB의 사실이라 필수 유지).

**파일명 규칙(최적화)**: 셸의 입력(또는 출력)이 **1개면 `{shell_id}.csv`**, **여러 개면 `{shell_id}_{테이블명}.csv`**(테이블 없는 파일 입출력은 `{shell_id}_in{n}`/`{shell_id}_out{n}.csv`). **정답(expected)** 빈 칸은 그 출력의 **To-Be 이름과 동일**(asis_output_dir vs tobe_output_dir로 폴더가 달라 충돌 없음, 데모 관례와 일치). **이미 적힌 이름은 그대로 존중**(자동은 빈 칸만). 입력CSV·DB export·정답은 우리가 정하는 이름이라 안전; 파일출력 file은 확장자 미상이면 csv 기본(필요 시 직접 기입).

**효과**: 고객은 `type`·`table`(과 `test_name`)만 채우면 됨 — 체크리스트 템플릿과 합쳐지면 "항목명 선반영 + 테이블만 기입 + 파일명 자동". **검증**: `tests/test_mapping_to_definition.py` 14개(단일/다중 자동·제공값 존중 포함) + checklist 6개 통과.

---

## D-036. 정의 항목별 격납 패스 override — 사장님 규격 정합 (Phase 7, T7-5)

**결정**: 사장님이 보내주신 정의 파일 최소 항목(체크리스트 번호 / As-Is 입력·출력의 명·종류·격납패스 / To-Be 격납 테이블·파일·패스 / 실행shell / To-Be 출력 명·종류·패스)을 충족하도록 모델·로더·경로 해석을 보강한다. 핵심은 **격납 패스(저장 경로)를 항목별로 담는 것**인데, 과거 회의 확정(D-021/DEFINITION_SPEC §1 "디렉토리=config 공통, 정의엔 파일명만")과 양립시키기 위해 **"config 공통 + 항목별 선택적 override"** 방식을 택한다(사용자 확정 — "가장 자연스럽고 효율적인 방식").

1. **새 항목별 필드(전부 선택, 비면 config 공통 = 하위호환)**:
   - `InputSpec.src_dir`(#4 As-Is 입력 격납 패스), `InputSpec.dest_name`(#7-3 To-Be 격납 파일명). (`table`=#7-1, `dest_dir`=#7-4는 기존)
   - `OutputSpec.expected_dir`(#7 As-Is 출력 격납 패스), `OutputSpec.tobe_dir`(#11 To-Be 출력 격납 패스). (`expected`=#5, `export_as`/`file`=#9, `type`=#10은 기존) *(#6 As-Is 출력 종류는 D-037 보정에서 제거 — 아래.)*
2. **경로 해석 단일화(드리프트 차단)**: `src/core/paths.py` 신설 — `input_source_path`/`input_dest_dir`/`input_dest_path`/`output_asis_path`/`output_tobe_path`. "항목 경로 있으면 그걸, 없으면 config 공통". orchestrator(적재처·정답 경로)·runner(읽기처·To-Be 산출)·make_golden이 **모두 이 헬퍼를 공유**(기존 runner.resolve_input_dir/_tobe_path/_input_file_path 흡수·제거). 복사처=읽기처가 같은 규칙을 타 파일셸 드리프트를 구조적으로 차단.
3. **#6(As-Is 출력 종류)는 메타**: 비교는 통짜 바이트(D-004)라 판정에 영향 없음 — 리포트·기록·문서용 정보로만 보유(바이트 자기일치 유지, [[dc-self-review]]).
4. **#7-2(DB의 to_be 격납 패스)는 필드 미생성**: 우리 도구는 psycopg2로 CSV를 테이블에 **직접 적재**(스테이징 파일 경로 불요)하므로, DB 입력의 To-Be 격납지는 **테이블명(#7-1)**이 전부다. "DB는 경로 N/A". 만약 사장님 의도가 ⓐ적재 전 스테이징 디렉토리 또는 ⓑ스키마명이면 추후 `InputSpec.stage_dir`/`schema` 한 칸으로 확장(의미 확정 후) — **사장님 확인 대기 항목**.
5. **도구·골든 정합**: `mapping_to_definition.py`·`checklist_to_template.py`가 새 선택 열(`src_dir`·`dest_name`·`expected_dir`·`tobe_dir`)을 수용/방출 → 매핑 CSV에 1:1. `make_golden.py`는 paths 헬퍼로 전환하며 **다중 출력 리스트 반환 미반영 잠복 버그(T7-2 이후 `copyfile(list)`)를 함께 수정**(출력마다 정답 경로로 복사).
6. **`_needs_db` 보정**: 출력 중 **하나라도** database면 conn을 열도록(기존 1차 출력만 보던 것 → outputs 전건). 다중 출력에서 2번째가 DB여도 export 가능.

**이유**: 검증 항목(셸)마다 데이터/정답/산출물의 실제 위치가 다를 수 있다는 사장님 규격을 그대로 받되, 대다수 케이스(공통 디렉토리)는 config 한 곳으로 간결하게 — override는 필요한 셸만. 경로 조립을 한 모듈로 모아 드리프트(복사처≠읽기처)를 원천 차단.

**deferred(유지)**: #7-2 의미 확정 후 DB 스테이징/스키마 필드, 정교 비교(D-022), 물리 다중 DB 접속, Core/CLI/리포트 일본어화. SAM 등 확장자 실데이터 QA(2순위).

**검증**: `tests/test_paths.py` 8개(override·fallback·rename·부모생성·디렉토리 미상 에러) + `test_definition.py` 항목별 경로 파싱 2개 + `test_mapping_to_definition.py` 경로 열 1개 + 기존 스위트 그린(하위호환: 경로 미기재 정의 무수정 동작).

---

## D-037. 定義作成 화면 복원 — CSV→정의를 별도 GUI 페이지로 (D-034 부분 보정)

**결정**: T7-3(D-034)에서 운영 화면 경량화를 위해 GUI에서 걷어냈던 **매핑표(CSV)→정의 yaml 생성**을, **실행 화면과 분리된 별도 페이지 `/define`(定義作成)** 로 복원한다. "어떻게든 그걸 하는 화면이 있어야 한다"(사용자) — CLI 도구만으로는 부족.

1. **페이지 2분할**: `/` 検証実行(운영=버튼+모니터+결과, 그대로 유지) / `/define` 定義作成(준비=정의 만들기). 헤더에 상호 링크. 실행 화면의 경량성은 보존(준비 기능이 섞이지 않음).
2. **/define 기능**: 매핑표(Long CSV) 업로드 → `mapping_to_definition`(tools 재사용) → 미리보기(셸·입출력 카운트)/오류 행 표시 → **config의 definition_file에 저장** 또는 YAML 다운로드. 작성 시작점으로 **동봉 정의 CSV 샘플**(`samples/shell_mapping.long.example.csv`)을 화면에서 다운로드 제공. tools/ 로직 그대로 재사용(드리프트 없음). *(체크리스트→기입 템플릿 생성은 사용자 판단으로 GUI 미포함 — CLI `tools/checklist_to_template.py`로만 유지.)*
3. **새 라우트**: `/define`(GET), `/definition/from-csv`(POST, 읽기전용 생성), `/definition/sample-csv`(GET, 샘플 다운로드), `/definition/save`(POST, config의 definition_file에 기록). 엄격 생성·round-trip은 tools 그대로(한 행이라도 오류면 전체 거부).
4. **D-034와의 관계**: 운영 화면을 경량화한다는 D-034 원칙은 유지하되, "준비 작업도 화면이 필요하다"는 요구에 맞춰 **준비를 별도 화면으로** 둔 것(걷어낸 게 아니라 분리). 업로드-CSV "검증"(즉석 비교)·테이블선택 3칸·탭/위저드는 여전히 미복원.

**이유**: 정의 작성(CSV→yaml)은 설치 준비의 핵심인데 CLI만 두면 비개발 사용자가 못 쓴다. 운영(실행)과 준비(정의 생성)를 **별도 화면으로 분리**하면 실행 화면의 간결함과 준비 화면의 기능성을 모두 얻는다.

**검증**: `tests/test_gui.py` +7(=25개: /define 렌더·링크·from-csv 생성/거부/파일필수·sample-csv 다운로드·save가 definition_file에 기록) 통과. 라이브: 동봉 `samples/shell_mapping.long.example.csv` 업로드 → 2셸(001 입력3·출력2 / 002 입력1·출력1) 생성, 데모 정의 무사. 전체 178 passed.

### D-037 보정. expected_type(#6 As-Is 출력 종류) 컬럼 제거

**결정**(사용자): "새 정의 파일을 채웠을 때 커버 안 되는 부분" 감사 결과, 격납 패스 5종
(`src_dir`·`dest_dir`·`dest_name`·`expected_dir`·`tobe_dir`)은 전부 엔진이 실사용(코드 추적+라이브 R02
검증)하나 **`expected_type`만 파싱 후 아무 데서도 안 쓰임**(통짜 바이트 비교라 판정 무관, 리포트·화면
노출 0건)이 확인됨. 사용자 결정으로 **컬럼·필드 제거**. 출력 "종류"는 To-Be 기준 `type`(#10)만 둔다.
→ `OutputSpec.expected_type` 삭제, definition 파서·`mapping_to_definition`·`checklist_to_template`
헤더·샘플 CSV·템플릿 yaml·DEFINITION_SPEC에서 제거. 사장님 11항목 중 #6은 정의에서 빠짐(통짜
바이트 비교 모델에선 As-Is 출력 종류가 불요 — #7-2와 함께 "모델상 불필요"로 정리). 전체 178 passed.

### D-037 보정2. 매핑 CSV의 1차 키 = checklist (열 이름 명확화)

**결정**(사용자): 매핑 CSV는 **체크리스트 기준**이 포인트 — 1차 키 열을 `shell_id`가 아니라 **`checklist`**(체크리스트 번호)로, 실행 배치 열을 **`shell`**(구형 `program`)로 명명한다. 한 체크리스트가 입력 여러 개(예: A DB 짝수행 + B DB 홀수행을 shell이 Merge → C DB)를 읽고 최종 출력(C) 하나를 검증하는 구조라 **checklist로 묶는 Long 형식**(입출력 항목당 1행)이 정답. `mapping_to_definition`이 `checklist`/`shell`을 우선 인식(구형 `shell_id`/`program`도 호환). 샘플(`samples/shell_mapping.long.example.csv`)을 A·B→C 병합 예시로 교체, `checklist_to_template` 헤더도 동일 명명. (로더 yaml 필드는 그대로 `test_id`/`execution.shell_program` — CSV 열 이름만 사용자 어휘로.)

**이유**: 검증 단위는 셸이 아니라 **체크리스트 항목**이고, 셸(실행 배치)은 그 체크리스트의 한 속성일 뿐. 열 이름이 `shell_id`라 "체크리스트 번호"인지 "실행 셸"인지 혼동됐음 — `checklist`(키)/`shell`(실행 배치)로 분리해 해소.

**검증**: `tests/test_mapping_to_definition.py` +2(checklist 키·다중입력 병합·키열 필수), 샘플→정의 생성 ok(001 입력2·출력1 병합), 전체 그린.

---

## D-038. key = 정렬 결정화용(통짜 바이트 1순위), record는 폴백

**결정**: "통짜 바이트"(D-004)가 기본 원칙. DB 출력은 SELECT 순서 비결정이라 그대로는 byte 비교 불가
→ **export 시 `ORDER BY key`로 행순서를 결정화한 뒤 통짜 바이트 비교가 1순위**. record(키 정합) 모드는
순서 결정화가 불가능할 때의 **폴백**. 즉 `key`는 "정렬 결정화용"이지 "정합 비교용"이 아니다.

**이유**: 검증 도구의 생명은 통짜 바이트 신뢰성(해석 0). DB의 순서 비결정만 `ORDER BY key`로 제거하면
byte 모드를 그대로 살릴 수 있다 — record는 그게 불가능한 예외에만. MAPPING_SPEC §5·DEFINITION_SPEC §4-3
·HANDOFF_5 C1 문구를 이 한 줄로 통일.

## D-039. SAM layout = mask/normalize 시에만 소비

**결정**: `layout`(고정길이 바이트위치)은 **그 SAM 필드에 mask/normalize를 걸 때만 소비**된다. 순수
통짜 바이트 비교 SAM은 layout 없이 된다. MAPPING_SPEC "layout 필수" → **"SAM이면 칼럼은 존재하되 값은
mask/normalize 필요 시에만 채움"**으로 좁힘. DEFINITION_SPEC §4-3의 "SAM 레이아웃 불필요" 단정도 이로 보정.

**이유**: 통짜 바이트(D-004)는 형식을 해석하지 않으므로 layout이 필요 없다. layout이 필요한 유일한 경우는
SAM 내부 특정 필드만 마스킹/정규화할 때(바이트위치를 알아야 그 필드만 건드림) — 그 외엔 inert.

## D-040. 매핑표 shell = 단축 잡명, 디렉토리·호출규약 = BatchConfig (2층 분리)

**결정**: 매핑표 `shell` 칼럼은 **단축 잡명(예: `job001`)**으로 적고, 배치 디렉토리·호출규약(인자형식·
성공코드·env)은 **config 전역 1벌(C6 BatchConfig)**이 결합한다. 현행 샘플의 풀패스(`/opt/batch/job001`)
표기는 단축명으로 정정 — **단, 샘플 CSV 실파일·도구 정정은 데이터 입수 후**(이번엔 docs 예시 텍스트만).

**이유**: 같은 디렉토리·호출규약을 행마다 반복하면 드리프트·손작업. 변하는 *어느 배치*만 매핑표에,
고정값은 config 한 곳에. (열 이름 `shell`은 D-037 보정2와 동일.)

## D-041. long 매핑 CSV 컬럼 다이어트 (설계 확정·구현 보류)

**결정**: long 매핑 CSV의 컬럼을 다이어트한다 — ① `test_name`·`name` **삭제**(폴더가 못 줌=손작업인데
비교에 불필요), ② `encoding`·`has_header`·`delimiter`를 **config 전역 기본값으로 이동**(행별 칸에서 제거,
비우면 기본·적으면 그 행 override). 전역화에는 **config에 `has_header`·`delimiter` 키 신설**이 포함된다
(현 config는 `encoding`만). 대상은 long 매핑 CSV이며 DEFINITION_SPEC YAML 필드와는 별개.
**설계 확정, 구현(컬럼 제거·config 키 신설·도구 fallback)은 데이터 입수 후.**

**이유**: 반복되는 고정값을 전부 전역으로 모아 사람 손작업·드리프트를 줄임("비우면 기본, 적으면 override").

### D-041 보정. `test_name` 칼럼 정본 CSV에서 제거 (다이어트 ① 일부 실현)

**결정**(사용자): 정본 데모셋 `samples/complete/complete_sample.csv`를 직접 채워보니 `test_name` 기입이
수고로움이 드러남 → **정본 CSV에서 `test_name` 칼럼 제거**. test_name은 선택값(없으면 checklist 번호가
라벨)이라 **무손실**. 도구(`mapping_to_definition`)는 **하위호환으로 계속 읽음**(구 정의·기존 YAML 보호) —
정본 템플릿에서만 뺀 것. e2e 21건 OK17/NG3/MISSING1 무변, 269 green.
- `name`(출력 라벨)은 **유지**: 다중출력(CK020 明細/集計) 구분에 실효 — 단 D-041 원안엔 삭제 대상이라
  추후 동일 판단 시 제거 가능(현재는 보존). encoding/has_header/delimiter 전역화는 여전히 보류(데이터 입수 후).

### D-041 보정2. 매핑 CSV 컬럼명 직관화 + `name` 삭제 (사용자)

**결정**(사용자): 정본 CSV를 처음 보는 사람이 바로 이해하도록 컬럼명을 직관화. 구 이름은 **별칭으로 계속
수용**(`mapping_to_definition._get` — 신 이름 우선·구 이름 호환 → 깨짐 0). `name`(출력 라벨)도 삭제 —
출력은 table/file명으로 **항상 식별**되므로(같은 체크리스트 내 충돌 방지됨) name은 미관 라벨일 뿐, 없으면 file명 표시.
- 이름: kind→**io** · type→**db_or_file** · expected→**expected_output** · key→**key_columns** ·
  mask→**ignore_columns** · normalize→**normalize_rules** · layout→**fixed_layout**.
- 유지: checklist·shell·shell_group·table·file·compare_mode·encoding·has_header·timeout.
- 삭제: name(+ D-041 보정의 test_name). **compare 블록 YAML 키(key/mask/normalize/layout)는 불변**
  (로더 내부 계약) — CSV 신 이름 → 같은 YAML 키로 운반.
- complete_sample 헤더 갱신 + 칸 설명 `#` 주석. e2e 21건 무변, **270 passed**.
- ⏳보류: `tools/checklist_to_template.py`는 핵심 기능이 test_name(항목명 선반영)이라 이번 rename에서 제외 —
  test_name 폐지와 함께 재설계할지 별도 결정(현재 구 이름·별칭으로 정상 동작).

## D-042. 폴더 스캐너 = 개념 프로토타입만 검증, 실구현 보류

**결정**: `checklist-folders-sample/folder_scan_prototype.py`는 **레포 자산이 아니라 전략 세션의 개념
프로토타입**(레포 미포함·참조용). MAPPING_SPEC의 "프로토타입 검증됨" 표현을 "개념 프로토타입으로 가능성
확인"으로 정정. 실 스캐너(폴더→정의 골격)는 고객 폴더 실제 규칙 + 데이터 입수 후 신규 구현.

**이유**: 폴더명 패턴·input/output 명칭·다중출력·SAM layout·파일↔테이블 대응이 확정돼야 정확히 짠다.
추측 구현은 이 프로젝트가 내내 피한 실패.

---

## D-043. UI 방향 전환 — ModernizePro Compare(형제 제품 셸·녹색 디자인) 채택

**배경**: 본 Comparator는 **ModernizePro Compare**라는 이름으로 사장님 회사 ModernizePro 제품군의
**형제 제품**으로 출시된다. 코드 통합이 아니라 **같은 제품라인·같은 디자인 언어**를 공유한다. 형제 제품은
이미 **[사이드바=프로젝트 목록 + 상단 탭(Dashboard / Mapping / Execution / Artifacts / Versions /
Log viewer / Project Settings)]** 구조와 **녹색(틸/그린) 디자인**을 가진다.

**결정**: 형제 제품의 셸 구조·디자인 언어를 따른다. 이로써 아래 기존 결정이 갱신/무효화된다.
- **(무효)** "단일 화면 세로 흐름" 전제 → 형제 제품의 **사이드바+탭 구조**를 따른다. 우리의
  정의→점검→실행→결과 세로 흐름은 폐기가 아니라 **'Execution 탭 내부 레이아웃'으로 존속**.
- **(분산)** 기능을 탭으로 분산: 매핑표→**Mapping**, 검증실행→**Execution**, 試験成績書→**Artifacts**,
  회차이력(기존 E2 보류)→**Versions**, DB접속→**Project Settings**, 로그→**Log viewer**.
- **(폐기)** DESIGN_TOKENS.md의 먹네이비(#1F2937) 등 자체 토큰 → **재작성 예정**(주색은 D-043 보정 참조).
  정식 가이드 없음 → **스크린샷 기반 추출**. DESIGN_TOKENS.md는 "값 폐기·재작성 예정"으로 표시.
- **(갱신)** 외부 판매전략 자료 §12 *"엔터프라이즈 외피 나중에 자체 제작"* → **불필요**. 외피 = 형제 제품
  셸 패턴 차용으로 충당. (해당 §12는 외부 문서라 repo에 반영 대상 없음 — 본 결정으로 무효 기록만.)

**구현 보류**: UI·디자인 실작업은 **착수하지 않는다**. 착수 조건 = **첫 실배치 검증 후 + 형제 제품
스크린샷 확보 후**. 지금은 본 D-043 기록 + DESIGN_TOKENS.md 상단 표시 + HANDOFF_5 C7/E2 supersede
포인터만(코드·토큰 편집 금지).

**이유**: 형제 제품과 동일 셸·디자인 언어를 쓰면 제품라인 일관성·고객 인지·개발 비용(자체 외피 제작 불요)
모두 이득. 자체 토큰을 더 다듬는 건 곧 폐기될 값에 대한 매몰 작업이라 지금 중단하는 게 맞다.

### D-043 보정. 주색 = 녹색 아님(색상명 미정)·ModernizePro Compare 한정

**결정**(사용자): 형제 제품은 녹색(틸/그린)이지만, **ModernizePro Compare는 녹색이 아닌 별도 주색으로
간다.** **셸 구조(사이드바+탭)·디자인 언어는 형제 제품과 공유, 주색만 분기.** 색상명은 **미정**(계열도
미정) — 형제 제품·실제 가이드 스크린샷 확보 후 구체 값 확정. 범위는 **Compare 제품 한정**(형제 제품 색은 불변).

**제약(주색 후보 조건)**: 기존 제품군 팔레트 **주황·연초록·파랑·보라**와 시각적으로 대비될 것.
추가로 **빨강(우리 상태색 NG `#A83232`)과도 구분**될 것 — 검증툴에서 빨강=실패 의미라 주색으로 쓰면 혼동.
→ 위 5색(주황·연초록·파랑·보라·빨강)과 충돌하지 않는 레인에서 스크린샷 확보 후 선택.
→ D-043의 "녹색 계열로 대체" 표현 무효, DESIGN_TOKENS.md 배너도 "녹색 아닌 Compare 전용 색(미정)"으로 표시.

**이유**: 같은 제품라인이되 Compare가 색으로 구분되는 형제 관계. 색은 스크린샷·정식 가이드 확보 후
정해야 추측 토큰 매몰을 피한다. 지금은 "녹색 아님 + Compare 한정"만 확정, 구체 값은 보류.

## D-044. UI 셸 재구성 착수 — ModernizePro Compare(그래파이트 + 형제 셸)

**배경**: 형제 제품 ModernizePro 스크린샷 확보(`ui_screenshot/` 5장) → D-043 보류 조건("스크린샷 확보 후") 충족.
형제는 **틸/그린**, 2계층(사이트=프로젝트목록 사이드바+탭 / 프로젝트=Dashboard·Mapping·Versions·Execution·
Artifacts·Log viewer·Project Settings).

**결정**(사용자): GUI를 형제 셸(상단 앱바 + 좌측 사이드바 + 상단 탭)로 재구성. 주색 = **그래파이트(딥 그레이)** —
형제와 **색으로 구분**, 비활성처럼 안 보이게 **솔리드 딥**(검정 버튼처럼), **추후 변경 가능**(임시 확정).
`DESIGN_TOKENS.md` 재작성 완료(그래파이트 토큰·셸 레이아웃·컴포넌트·커스텀 드롭다운).
- **범위**: 현재 기능을 새 탭으로 **이식** + **디렉토리(paths) 편집·저장 신규**만(그 외 신기능 X).
- **드롭다운**: 시스템 `<select>` → **커스텀(프로그램다운) UI**로 교체.
- 탭 매핑: Mapping(정의/매핑표)·Execution(실행+모니터)·Artifacts(試験成績書/리포트)·Quarantine(NG/MISSING 상세)·
  Project Settings(DB접속+디렉토리). 멀티프로젝트·Versions/Log/Scheduler/Approvals는 **후순위/보류**.
- **불변**: 화면만(코어·comparator·스키마 무수정), **270 녹색 유지**, task 단위·각 task 끝 커밋.
- **D-043(보류)·D-043 보정(주색 미정) supersede**: 스크린샷 확보 + 주색=그래파이트로 확정.

**Task 분할**: G1 토큰(✅완료) → G2 셸 골격 → G3 Execution → G4 Mapping → G5 Artifacts+Quarantine →
G6 Project Settings(paths/DB) → G7 시각 디테일. G8(멀티프로젝트 등) 보류.

**이유**: 스크린샷 확보로 추측 매몰 위험 소멸(D-043 조건). 그래파이트는 형제 팔레트(주황·연초록·파랑·보라·틸)와
충돌 0 + 무채 셸이라 상태색(OK/NG/MISSING)이 또렷이 튐 = 검증툴에 적합.

## D-045. 업무별 데이터 디렉토리 — 3단계 경로 폴백 (구조 열기)

**배경**(사장님 확인): As-Is/To-Be 데이터 디렉토리가 **업무마다 다를 수 있음**. 기존엔 전역 config.paths(공통)
+ 정의 CSV 항목별 `*_dir` override(체크리스트 행마다)뿐이라, 업무별로 다르면 행마다 반복해야 했다(GUI는 전역만).

**결정**: config `batch.groups[업무]`(shell_group 키)에 **업무별 데이터 디렉토리**(`asis_input_dir`·
`asis_output_dir`·`tobe_input_dir`·`tobe_output_dir`, 전부 선택)를 추가. 경로 해석을 **3단계 폴백**으로:
**항목 override(정의 *_dir) > 업무 그룹 dir(shell_group) > 전역 config.paths**.
- 구현: `paths.apply_group_dirs(definition, config)` — 항목 override **빈 칸에만** 그룹 dir을 채움(idempotent),
  기존 `_dir(override>전역)` 해석을 그대로 사용(**paths 시그니처 무변경**). orchestrator·runner·preflight·
  make_golden 진입점에서 호출 → 실행·골든·프리플라이트가 **동일 경로**(false-NG 구조적 차단, D-027 정신).
- 하위호환: 그룹 dir 미설정이면 no-op → 전역 폴백(기존 동작). **273 passed 유지**(+그룹 dir 파싱·3단계 우선순위 테스트).
- config.yaml.example에 업무별 dir 문서화. **GUI 업무별 디렉토리 편집 UI는 다음 단계**(현 Project Settings는 전역만).

**이유**: 업무별 폴더가 실재(사장님 확인)하므로 "구조를 열어둔다"(나중에 실데이터 와도 재작업 없게). 단
**업무별이냐 체크리스트별이냐의 최종 폴더 규약은 여전히 보류**(Input DB/Output DB 폴더 구조 확정 후) — 이번 건은
"업무별일 때 대응 가능한 폴백을 마련"한 것이지 폴더 규약을 확정한 게 아니다.

## D-046. 매핑 CSV 열 `db_or_file` → `type` 재명명 (D-041 이 열 결정 supersede)

**배경**(사장님 확인): 코드변환은 문자코드만 바꾸고 형식은 보존 → 실무에 **SAM/VSAM**(고정길이) 파일이 그대로 온다.
이를 매핑 CSV에서 표현하려고 이 열에 `sam`·`vsam` 값을 추가한다(D-047). 그러면 값이 {database, file, sam, vsam}
4종이 되어, D-041에서 "직관화"를 이유로 붙인 이름 **`db_or_file`("DB냐 파일이냐")가 부정확**해진다(sam/vsam은
file의 하위 형식이라 2분법에 안 맞음).

**결정**: 이 열의 정본 이름을 **`type`** 으로 되돌린다. `db_or_file`은 **구 별칭으로 계속 수용**(기존
`complete_sample.csv`·`definition_template.csv`·고객 작성본 깨짐 0). 즉 이 열의 이름 흐름:
`type`(원래) → `db_or_file`(D-041, 직관화) → **`type`(D-046, sam/vsam 도입으로 2분법 깨짐)**.

- 범위: **순수 리네임 — 동작 0 변경**(별도 커밋). `mapping_to_definition.py`(별칭쌍 방향·에러문구·docstring),
  `definition_template.csv`·`samples/complete/complete_sample.csv`(헤더+주석), `MAPPING_SPEC.md`, 테스트.
- ★YAML 정의(`definition.py`)의 `type` 필드(database|file)와는 **다른 층**이다 — 매핑 CSV의 `type` 열은
  도구가 YAML로 컴파일하는 입력이고, sam/vsam은 도구 레벨에서 `type:file`+`compare` 블록으로 풀린다(D-047).
- 하위호환 가드 테스트 추가(`db_or_file` 별칭 여전히 동작).

**이유**: 이름이 값 집합을 정확히 반영해야 한다(sam/vsam 도입 시 db_or_file은 오해 유발). 별칭 유지로 역행 비용 0.

## D-047. SAM/VSAM 대응 — type에 sam/vsam 값 추가, 매핑도구가 컴파일(코어 무수정)

**배경**(사장님 확인): 코드변환은 문자코드만 바꾸고 **형식 보존** → SAM은 SAM, VSAM은 VSAM(둘 다 고정길이)으로
온다. 실무에 존재하므로 대응 필요. ★VSAM은 insert 시 **키순 정렬 저장** → 물리 행순서가 As-Is와 달라
순서 의존 비교(byte/위치)는 false-NG. **key 정렬·정합 필수.**

**결정**: 매핑 CSV `type` 열에 `sam`·`vsam`을 추가(총 4값). **Option A — 매핑도구가 기존 record/layout/key로
컴파일**(definition.py 스키마·orchestrator·comparator **무수정**, 코어 무수정 규칙 준수). 비교 엔진은 이미
record 모드에서 layout(고정길이 슬라이스)·key(정렬+머지조인)를 지원하므로 **새 비교로직 0**.
- **storage**: sam/vsam → YAML `type: file`(고정길이 파일이라 적재/추출은 file과 동일, 동봉 stub=run_batch_file).
- **compare 도출**(`_apply_format_compare`):
  - **sam** = 기본 **byte 통짜**(순차파일·순서 의미, D-039). `record` 명시 또는 `ignore_columns`/`normalize_rules`가
    있으면 **record+layout 필드비교**(그땐 layout 필수). byte일 때 layout은 운반 안 함(死데이터 방지).
  - **vsam** = **record+layout+key 필수**, `has_header: false`(고정길이=무헤더, 필드는 layout·인덱스).
    ★**KSDS(키순 저장) 가정**이다. KSDS는 키순 저장이라 물리 순서가 As-Is/To-Be 간 어긋날 수 있어(특히 To-Be가
    RDB면 ORDER BY 없이 순서 비보장 — DB SELECT 비결정과 같은 뿌리) key 정렬·정합이 안전판. VSAM 다른 종류:
    **ESDS(입력순)=byte로 충분, RRDS=번호순.** 실무 업무배치는 대부분 KSDS라 record+key가 안전한 기본값이고
    record+key는 ESDS에도 틀리지 않음(불필요 정렬일 뿐) → **3종 type 분기는 지금 구현 안 함**(과설계·추측 회피).
- **lint(비치명 warnings)**: Option A에선 YAML로 컴파일되면 sam/vsam 정체가 사라져 preflight가 못 보므로
  **매핑도구 단계에서** 경고한다. 결과 dict에 `warnings` 추가 → CLI(stderr)·GUI(定義作成 화면 警告박스) 노출.
  - vsam인데 key_columns 빔 → 경고(키순 저장, 정렬키 없으면 false-NG).
  - sam(필드비교)/vsam인데 fixed_layout 빔 → 경고(고정길이 분할 기준 없음).
- ★**실데이터 분리**: 비교 로직·라우팅·lint는 지금. **실제 layout 바이트위치·key 컬럼 값은 데모 stub의
  '가정 모양'**(VSAM=SAM동일 고정길이+키순 가정)이며, 실 SAM/VSAM 1건 입수 후 검증한다(README·데모 주석 명시).

**범위/규칙**: 매핑도구(비코어)+template/samples+GUI 표시계층+데모 데이터만. **코어 무수정.** D-046(리네임)과
별도 커밋. 데모셋에 sam(CK011/012 라벨 정정)+vsam(키로 순서흡수 OK 1 + 진짜 값차 NG 1) 정비, e2e 통과.

**deferred**(실데이터 후):
- 실 SAM/VSAM 실데이터 QA — layout 바이트위치·key 컬럼 확정.
- **VSAM key 유일성 검증** — vsam key가 실제 유일한지 확인, 중복이면 경고(머지조인 오짝 = false-PASS 위험, §5).
  KSDS 주키는 유일이라 보통 무문제지만 실 key 지정 시 의미 있음.
- **ESDS/RRDS type 분기** — 실데이터에 ESDS(입력순)/RRDS(번호순)가 실재하면 type 분기 추가(현재 KSDS 가정 단일).
- 1:N 시퀀스, 정교 비교(D-022).
- (참고·작업 없음) SAM byte 부가조건(인코딩·고정길이 패딩·레코드길이 일치)은 앞단 변환툴 책임(D-004) —
  어긋나면 우리 비교 문제 아니라 변환 문제이므로 진단 시 구분.

## D-048. 매핑 CSV 칼럼 As-Is/To-Be 이름 통일 + dest_* 표면 제거 (매핑 표면만, 코어 무수정)

**배경**: 채우는 사람이 디렉토리·파일명을 직관적으로 읽도록 칼럼 이름을 **As-Is/To-Be 짝 + io 흐름**으로 통일.
기존 `file`은 입력행=입력파일명·출력행=To-Be출력명으로 **과적**돼 헷갈렸고, 디렉토리 칼럼이 맨 뒤에 몰려
데이터 이름과 떨어져 있었다.

**결정**: 매핑 CSV(사람이 채우는 표) 칼럼을 재명명/정리한다. **별칭 없이 신 이름**(정본 데모셋만 사용).
- `file` → **`input`**(입력행) / **`to_be_output`**(출력행) 분리 · `expected_output` → **`as_is_output`**
- `src_dir` → **`input_dir`** · `expected_dir` → **`as_is_dir`** · `tobe_dir` → **`to_be_dir`**
- **`dest_dir`/`dest_name` 제거**(매핑 CSV 표면만, A안). 코어 `InputSpec.dest_*`·`paths.input_dest_*`는 유지 —
  파일입력 To-Be 스테이징은 `config.tobe_input_dir` 폴백, 행별 지정이 필요하면 손YAML로(사장님 규격 #7-3/#7-4 보존).
  ★B안(코어까지 삭제)은 기각: "코어 무수정·동작 0변경" 위반 + 검증 전 사장님 규격 임의 삭제(월권).
- 정본 20칼럼 순서로 재배치(데이터 이름 옆에 디렉토리). `type`(구 db_or_file, D-046)은 유지.

**범위/규칙**: **매핑도구(읽는 칼럼 분기)·두 CSV(template·complete_sample)·매핑 관련 도구
(`checklist_to_template`)·문서·매핑 테스트만.** 매핑도구는 신 칼럼을 읽어 **기존 YAML 필드(csv·file·
expected·src_dir·expected_dir·tobe_dir)로 그대로 방출** → **definition.py·models·paths·orchestrator·
comparator·loader·코어 테스트 무수정. 생성 YAML round-trip 동일**(코어 계약 불변 확인). 285 passed.

**이유**: 이름은 사람용(매핑 표)·YAML 필드는 코어 계약 — 두 층 분리로 직관성 개선과 동작 보존을 양립.
별칭 미유지: 정본 데모셋 외 구 이름 정의가 레포에 없음을 grep으로 확인(테스트는 신 이름으로 갱신).

**엑셀(.xlsx) 지원(동반)**: 팀원 공유 마찰을 줄이려 — ① `tools/make_xlsx_template.py`가 정본 CSV →
`definition_template.xlsx`(★전 셀 텍스트 서식 잠금: 선두0 `00100`·layout `0:6`·normalize가 Excel 자동변환에
안 깨짐). ② `mapping_to_definition.read_mapping_bytes`가 **.xlsx를 직접 읽음**(zip 시그니처 감지 → 첫 시트
→ CSV 텍스트, openpyxl 지연 import=試験成績書와 동일 의존). CLI·GUI(定義作成 화면·`/definition/from-csv`)
모두 CSV/xlsx 수용 → 팀원은 엑셀로 채워 **CSV 저장 단계 없이** 제출. 코어 무수정(도구·표시계층만).

## D-049. 매핑도구 silent-drop/collision 3건 가드 (J 적대적 검토, 코어 무수정)

**배경**: HANDOFF_7 J(직전 변경분 D-046~048 적대적 검토)에서 `mapping_to_definition`의 **검증 누락을
조용히 일으키는** 3개 지점을 적대 케이스로 발견. 검증도구에서 "조용히 검증 안 함"은 false 커버리지(최악).

**결정**(모두 매핑도구 비코어 국소 수정 — definition.py·orchestrator·comparator 무수정, 292 passed):
1. **sam + 명시 `compare_mode` 강등 경고**: sam 출력에 `text` 등 byte 아닌 모드를 명시하면 D-039대로
   byte로 덮어쓰는데, 기존엔 **무경고**였다(vsam은 동일 상황 경고). → `_apply_format_compare`에서
   명시 모드가 byte로 무시될 때 vsam과 동일하게 `warnings`에 1줄. (동작 불변, 가시성만 추가)
2. **xlsx 시트 선택 = 데이터 시트 기준**: `wb.active`만 읽던 것을 **데이터 있는 시트 탐색**으로 변경.
   1개면 그 시트(비활성 시트에 데이터가 있어도 포착), **2개 이상이면 loud `ValueError`**(1시트 통합 요구).
   기존엔 첫(활성) 시트 외 시트의 셸이 통째로 silent-drop(예: 業務B 시트의 002 누락) → 검증 누락.
   빈 시트(Excel 자동 생성)는 무시. `read_mapping_bytes`→`_xlsx_to_csv_text`만 수정.
3. **셸 내 동일 To-Be 출력경로 충돌 = 에러**: 같은 테이블/파일명 출력 2건이 빈 칸 자동채움으로 동일
   `export_as`/`file`이 되면 런타임에 서로 덮어써 한쪽 검증이 사라진다. → autofill 후
   `_output_target_collisions`가 `(to_be_dir, 파일명)` 중복을 에러로. 디렉토리가 다르면 충돌 아님(false-positive 가드).

**범위/규칙**: `tools/mapping_to_definition.py`만 수정 + 회귀 테스트 6건(`tests/test_mapping_to_definition.py`,
35→41). 코어·스키마·데모셋 데이터 무변경. 정본 `complete_sample.csv`(24 CK) 변환 영향 0(이미 distinct 이름·단일시트).

**이유**: 자가검증 6항의 **silent drop** 원칙 — 사용자 의도·검증 대상이 경고/에러 없이 사라지면 안 된다.
세 건 모두 "조용히 잘못"을 "loud 실패 또는 경고"로 바꾼 것(동작 보존, 가시성 강화).

## D-050. 보안/온프레미스 감사 — H 1차(코어 repr 차단 + 위생 3건)

**배경**: HANDOFF_7 H(보안/온프레미스). 일본 엔터프라이즈 온프레미스 배포 차단요건
(자격=env만·데이터 비반출·로그 비밀 0·config 평문 0·오프라인)을 코드 정독으로 감사.

**감사 결과 — 핵심은 견고(✅)**: 외부 네트워크 호출 0(localhost webbrowser/flask/psycopg2만),
`shell=True`/eval/os.system 0, GUI 기본 바인드 127.0.0.1, GUI는 폼에서 비번 미수령(env만)·
클라엔 password_env 이름만 반환, `save_connection`이 `db.pop("password")`로 config에 평문 비번 미기록.

**수정(3건)**:
1. **코어 repr 차단(사용자 승인 — 코어 무수정 예외)**: `DatabaseConfig`(dataclass) 자동 repr이
   password를 평문 출력 → repr/로그/예외로 누출될 지뢰(활성 누출은 0). `password` 필드에 `field(repr=False)`.
   값 보관·접속 동작 불변. `models.py` 1줄 + 가드 테스트 1건.
2. **devpw 평문 제거**: `HANDOFF_6/7.md`의 데모 DB 비번 `devpw` → 환경변수 참조로 리다이렉트
   (레포 자체 '★평문 금지' 정책 일치).
3. **공개 레포 위생 .gitignore**: 원자적 저장 산출물 `config.yaml.bak`/`.tmp`(고객 DB host/user 포함) +
   `ui_screenshot/`(형제 제품 디자인 참조) 무시.

**deferred/참고**: preflight DB 접속 에러는 psycopg2 예외를 그대로 노출하나 표준 접속 에러 메시지에
비번은 미포함(인증실패=user명만). 실데이터 운영에서 예외 문자열 점검은 F(운영 엣지)에서 재확인.

**범위**: 코어 `models.py` 1줄(승인)·문서·.gitignore. 293 passed/10 skipped.

## D-051. GUI activeConfig 무한재귀 회귀 수정 + JS 테스트 갭 인지 (수동 QA 산출)

**배경**: 사용자 수동 QA(GUI `/`에 정본 `complete_sample.csv` 업로드)에서
`通信エラー: RangeError: Maximum call stack size exceeded` 발생.

**원인**: `index.html`의 `const activeConfig = () => activeConfig();`(b1bf0a7, 트랙2-B에서
혼입) — base case 없는 자기호출. 메인 화면에서 config를 읽는 모든 동작(정의 생성·저장·
preflight·실행·paths·groups)이 **2026-06-08 이후 전부 RangeError로 깨져 있었음**. /define 화면은
`$("config").value`를 직접 읽어 무영향(그래서 from-csv 단독은 정상으로 보였음).

**수정**: `activeConfig`를 `#config` 셀렉터(option value=config 경로) 선택값 반환 + `lastConfig`
폴백으로. 서버 `_active_config()`(=`request.values.get("config") or _DEFAULT_CONFIG`)와 계약 일치.
GUI 템플릿(인터페이스 계층)만 수정 — 코어 무관.

**교훈(테스트 갭)**: 서버측 `test_gui`(Flask test_client)는 **브라우저 JS를 실행하지 않아** 이 회귀를
통과시켰다. 보강: 렌더 본문에서 자기재귀 패턴 부재 + `#config` 참조를 **정적 가드 테스트**로 확인
(완전한 JS 실행 검증은 아니지만 이 부류 회귀는 차단). 향후 JS 흐름은 수동 QA/별도 E2E가 필요.

**범위**: `src/gui/templates/index.html` 1줄 + `tests/test_gui.py` 가드 1건. 294 passed/10 skipped.

## D-052. GUI 一括実行 단일버튼 — Mapping→Execution→결과 자동 흐름 복원 (코어 무수정)

**배경**: 원래 비전(시연 시나리오·Phase7 "버튼+모니터+결과")은 **정의만 준비되면 한 흐름으로
점검→실행→결과/성적서**. 그런데 GUI(D-044 ModernizePro 탭 셸)가 점검·실행을 **별도 탭의 수동 2버튼**으로
쪼개 노출 중이었다. 엔진은 이미 자동 E2E(`/run` SSE = 전 셸 적재→배치→비교→리포트).

**결정**: **단일 `一括実行` 버튼** 추가(인터페이스 계층만, 코어/엔드포인트 무수정 — 기존 `/preflight`·`/run` wiring).
- `runPreflight()`를 await 가능 함수로 추출 → `runAll()`이 **점검 자동 실행 → 에러0이면 그대로 `startRun()`**.
  **점검은 안전 게이트로 유지**(에러 있으면 멈추고 preflight-out에 표시 — 야간 수천 건 헛실행 방지 C3).
- 배치: Execution 탭 상단 `#runall`(주버튼) + **Mapping 저장 직후 `goto-runall` CTA**("このまま一括実行")로
  탭 이동 없이 업로드→버튼→모니터 한 흐름.
- 동반 버그(수동 QA 발견): `/definition/save`가 **브라우저 폼 왕복 CRLF**(HTTP 폼 줄바꿈 정규화)를 그대로
  기록해 정의파일이 CRLF가 됐다(tracked 샘플 spurious diff). 저장 직전 `\r\n→\n` 정규화로 수정.

**범위**: `src/gui/templates/index.html`·`src/gui/web.py`(CRLF 1줄)·`tests/test_gui.py`(정적 가드 2 + CRLF 1).
코어·스키마·엔드포인트 계약 무변경. 296 passed/10 skipped. **D-034(경량 자동 흐름)·D-044(탭 셸) 양립**(탭 유지 +
단일버튼으로 자동 흐름 복원).

**deferred**: 더 깊은 경량화(탭→단일 화면 통합)는 별도 UX 결정 필요(지금은 탭 유지 + 자동 흐름만). i18n(G)·실 배치 연동(A) 무관.

## D-053. Mapping+Execution 단일 '検証フロー' 세그먼트 병합 (D-052 deferred 실현)

**배경**: D-052에서 "탭→단일 화면 통합은 별도 UX 결정 필요"로 보류했던 것을, 사용자 요청으로 실현.
"Mapping이랑 Execution을 아예 같은 segmented control로 묶어 한 화면에서 자동으로 넘어가게."

**결정**: 상단 세그먼트(기능 탭)에서 `Mapping`·`Execution` 두 탭을 **하나 `検証フロー`** 로 병합.
①定義 → 一括実行(②点検 ③実行) → ④結果를 **한 패널/화면**에 두고, 정의 저장 직후 `一括実行` 영역으로
**자동 스크롤**(scrollToEl)해 탭 이동 없이 흐름이 이어진다. 실제 실행은 단일 `一括実行` 버튼이 게이트(점검
안전장치 유지 — D-052). Artifacts/Quarantine/Project Settings 세그먼트는 그대로.

- 변경: 두 `tabpanel`(mapping/execution) → 하나(verify), `data-tab/data-panel` 갱신, `showTab("execution")→"verify"`,
  저장 후 `goto-runall` CTA 제거→자동 스크롤, placeholder 문구 정정. **코어/엔드포인트 무수정**(인터페이스 계층).
- 가드 테스트: verify 세그먼트 존재 + 옛 execution 분리탭 부재 + 자동전진 스크롤. 296 passed.

**이유**: 원래 비전(한 흐름 자동 E2E)에 맞춰 화면 분절을 제거. D-044(ModernizePro 탭 셸)의 세그먼트 개념은
유지하되, 핵심 검증 흐름만 단일 세그먼트로 합쳐 마찰 제거(D-034 경량화 정신과 합치).

## D-054. 検証フロー 재설계 1단계 — 백그라운드 실행(RunManager) + 상태 엔드포인트 (코어 무수정)

**배경**: GUI를 "긴 세로 스크롤 아코디언"에서 "한 화면 자동 전환 + 실행 후 자리 비워도 복귀"로
재설계(설계 승인됨). §0 조사: `/run`(SSE)은 데몬 워커라 실행은 끊겨도 계속 도나 **진행을 되읽을
서버 상태가 없고**, `_run_lock`을 generator finally가 조기 해제하는 **버그1**(실행 중 2차 기동 가능)이
있었다. 단 코어가 셸 종료 직후 **checkpoint.jsonl에 fsync**(영속)하므로 상태 복원의 토대는 이미 있음.

**결정(1단계, 인터페이스 계층만 — 코어/기존 엔드포인트 무수정)**:
- `src/gui/run_manager.py` 신설: 전역 단일 `RunManager`(락 + RunState). `run_full_comparison`을
  백그라운드 데몬 스레드로 감싸 진행/결과를 서버에 보존. 락은 **워커 생명주기 전체** 보유·워커
  finally에서만 해제(버그1 수정 — 연결 종속 제거).
- `POST /run/start`(즉시 반환, 진행 중 409, resume 플래그=코어 통과) + `GET /run/status`(폴링·재접속
  복원용 스냅샷: state·total(셸)·counts(출력)·current·started_at/finished_at·summary·error).
- **락 단일화(조건1)**: 구 `/run` SSE도 `run_manager` 락을 거치게 일원화 → 동시 기동 구멍 제거.
  구 SSE 기능(실시간 push)은 유지. (신규 UI는 폴링 기반으로 이행 후 구 SSE 정리 — 후속 단계)
- **예외 안전(조건2)**: 워커 크래시도 finally `end()`로 락 해제 + 상태 `failed` 보존(테스트 포함).
- **타임스탬프(조건3)**: started_at/finished_at — "이 결과가 언제 것인가"(어제 결과를 방금처럼 보이지 않게).

**단위 주의**: `total`=셸 수(ProgressEvent.total), `counts`/`done`=출력 수(N:M라 셸≠출력). 진행률 분모는
프론트가 from-csv의 output_count 합(출력)을 보존해 `done`과 짝짓는다(설계대로). 백엔드는 둘 다 제공.

**검증**: 단위 테스트 +3 + 격리 fixture, 구 SSE 테스트 2건 유지. dc-pg 실 데모를 `/run/start`로 백그라운드
실행 → `/run/status`가 done/OK22·NG4·MISSING1/타임스탬프/summary 정확 반영(curl). 299 passed/10 skipped.

**다음 단계(설계 2~6)**: 프론트 상태머신(고정 뷰포트·in-place) → 자동 연쇄(SELECT→READY) → RUNNING 폴링/
DONE/재접속 복원 → RESUMABLE(중단 checkpoint 감지 + resume) → 구 아코디언/SSE 정리.
**단일 프로세스 전제**(app.run threaded) — 다중 워커 WSGI면 RunState 깨짐(배포 가이드 명시 필요, 리스크).

## D-055. 検証フロー 재설계 2단계 — 고정 뷰포트 상태머신(新検証フロー β, 병존) (코어 무수정)

**배경**: 1단계(D-054) 백엔드 위에서, "긴 세로 스크롤 아코디언"을 "한 화면에서 단계 자동 전진"하는
상태머신 UI로. 기존 동작을 깨지 않으려고(로드시 dangling 참조=스크립트 전체 사망) **별도 세그먼트로 병존**.

**결정(인터페이스 계층만)**:
- 백엔드 `GET /run/resumable`(2-a): 미완 checkpoint 감지(store 재사용) → RESUMABLE 화면용.
- 프론트(2-b): 새 세그먼트 `新検証フロー(β)` + 상태머신 패널(고정 뷰포트, 단일 컨테이너 in-place 전환,
  스테퍼). 화면: SELECT→PREP(생성·저장·점검 자동 연쇄)→READY(경고 모음+検証開始)→RUNNING(폴링
  /run/status, 진행바+집계)→DONE(요약+다운로드) + BLOCKED(에러+재시도) + RESUMABLE(이어하기) +
  재접속 복원(로드 시 /run/status·/run/resumable로 적절 화면 복귀).
- 자기완결 IIFE(`nf-*` ID), 기존 `$`/`activeConfig`/`escapeHtml` 재사용. **node --check JS 문법 검증**.
- 셸 개별 리스트업 없음(PM 확정), NG 상세는 Quarantine/Artifacts·리포트 위임. 진행률 분모=출력(from-csv).

**병존 이유**: 기존 検証フ로ー(아코디언) 패널·JS를 손대지 않아 회귀 0. **다음 단계(3)**: β를 기본으로 승격 +
구 아코디언/`/run` SSE/결과 리스트 JS 제거 + (선택) Web Notification + 에러별 해결책 문구 정교화.

**검증**: 정적 가드 테스트, dc-pg 기동·렌더·엔드포인트 확인. 302 passed/10 skipped. **사용자 브라우저 QA 권장**
(β 탭에서 매핑표 업로드→自動進行→検証開始→진행/결과, 새로고침 복원, 중단 후 재개).
