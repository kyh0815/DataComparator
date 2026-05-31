
# ASIS → TOBE 마이그레이션 검증 자동화 시스템
## 프로젝트 기획서

---

## 1. 프로젝트 개요

### 1.1 프로젝트명
**ASIS(메인프레임) → TOBE(PITON) 마이그레이션 검증 자동화 시스템**

### 1.2 프로젝트 배경 및 필요성

#### 배경
- **현황**: 기존 메인프레임 시스템(ASIS, COBOL85 기반)에서 신규 PITON 기반 확장 미들웨어(TOBE, Net COBOL)로 마이그레이션 진행 중
- **문제점**: 
  - 100개의 테스트 케이스에 대해 ASIS와 TOBE의 출력 결과를 수동으로 비교하는 작업이 시간 소모적
  - 마이그레이션 정확성 검증에 많은 리소스 소비
  - 수동 비교 과정에서 인적 오류 발생 가능

#### 필요성
- ASIS 출력과 TOBE 출력의 자동 비교를 통한 **마이그레이션 정확성 검증**
- 배치 자동화를 통한 **테스트 시간 단축**
- 검증 프로세스의 **표준화 및 신뢰성 확보**

### 1.3 프로젝트 목표

#### 주 목표
**100개의 테스트 케이스에 대해 ASIS 기존 시스템 출력과 TOBE 신규 시스템 출력을 자동으로 비교하여 마이그레이션 정확성 검증**

#### 세부 목표
1. 정의 파일 기반 테스트 메타데이터 관리
2. TOBE 환경에서 자동화된 배치 처리 실행
3. 입출력 데이터(DB/파일) 자동 추출 및 변환
4. ASIS/TOBE 출력데이터 자동 비교
5. 테스트별 PASS/FAIL 자동 판정
6. 상세 검증 보고서 자동 생성

---

## 2. 시스템 범위 및 전제조건

### 2.1 프로젝트 범위

#### 기능 범위
| 항목 | 내용 |
|------|------|
| 테스트 케이스 수 | 100건 |
| 처리 방식 | Shell 스크립트 기반 배치 자동화 |
| 데이터 저장소 | PostgreSQL |
| 입출력 유형 | DB(테이블) / 파일 |
| 데이터 타입 | ABCDIC ↔ Shift_JIS 변환 지원 |
| 비교 대상 | ASIS 출력 ↔ TOBE 출력 |

#### 제외 범위
- ASIS 환경에서의 테스트 실행 (이미 완료된 상태 가정)
- TOBE 프로그램 개발 및 디버깅
- 사용자 인터페이스(UI) 개발

### 2.2 전제조건

#### 사전 준비 사항
1. **ASIS 테스트 결과 보유**
   - ASIS 체크리스트 및 테스트 사양 정의 완료
   - ASIS 테스트 실행 완료
   - ASIS 출력데이터(DB, 파일) 다운로드 완료
   - 문자코드 변환 완료 (ABCDIC → Shift_JIS)

2. **TOBE 환경 준비**
   - PostgreSQL 설치 및 구성 완료
   - Net COBOL 배치 프로그램 개발 완료
   - Shell 프로그램 작성 완료
   - 배치 실행 환경 구성 완료

3. **데이터 준비**
   - 테스트 입력 데이터 준비 (DB/파일)
   - ASIS 참조 데이터(ASIS 디렉토리) 준비 완료
   - 정의 파일 양식 정의 완료

---

## 3. 현황 시스템 환경

### 3.1 ASIS (기존) 시스템 환경
| 항목 | 사양 |
|------|------|
| **플랫폼** | 富士通 메인프레임 (OS: MSP) |
| **언어** | COBOL85 (BAGLESⅡ 자동생성) |
| **DBMS** | AIM/NDB (네트워크 DB) |
| **미들웨어** | AIM/DC |
| **특징** | 문자코드: EBCDIC (ABCDIC) |

### 3.2 TOBE (신규) 시스템 환경
| 항목 | 사양 |
|------|------|
| **플랫폼** | PITON 기반 확장 미들웨어 |
| **언어** | Net COBOL |
| **DBMS** | PostgreSQL (RDB 변환) |
| **배치 구성** | Shell 스크립트 → 배치 프로그램 → DB 저장 |
| **특징** | 문자코드: UTF-8 / Shift_JIS |

---

## 4. 전체 시스템 아키텍처

### 4.1 검증 자동화 프로세스 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                    마이그레이션 검증 자동화 시스템              │
└─────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │    1. 정의 파일 읽기 & 메타데이터 취득     │
        │  (테스트 ID, 입출력 정보, DB 연결 정보)  │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │         2. PostgreSQL DB 연결            │
        │      (연결 풀 관리 및 트랜잭션 처리)      │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │  3. 입력데이터 준비 (반복: 100 테스트)   │
        │  ├─ DB 데이터: 테이블에 INSERT          │
        │  └─ 파일 데이터: 지정 디렉토리에 COPY   │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │     4. Shell 프로그램 실행 (배치)        │
        │  → Net COBOL 프로그램 호출               │
        │  → 처리 완료 대기                        │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │    5. 출력데이터 추출 & 다운로드          │
        │  ├─ DB 테이블 → TOBE 비교 디렉토리      │
        │  └─ 출력 파일 → TOBE 비교 디렉토리      │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │   6. 데이터 비교 (ASIS vs TOBE)          │
        │  ├─ DB 비교: 행/열 데이터 검증          │
        │  └─ 파일 비교: 바이너리/텍스트 비교     │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │    7. PASS/FAIL 판정 & 보고서 생성       │
        │  ├─ 테스트 케이스별 결과 기록            │
        │  ├─ 불일치 항목 상세 분석               │
        │  └─ 검증 리포트 생성                     │
        └─────────────────────────────────────────┘
                              ↓
        ┌─────────────────────────────────────────┐
        │    8. 결과 저장 & 로깅                    │
        │  ├─ 검증 결과 DB 저장                    │
        │  ├─ 로그 파일 기록                       │
        │  └─ 최종 보고서 생성                     │
        └─────────────────────────────────────────┘
```

### 4.2 디렉토리 구조

```
/migration_validation_project/
│
├── /config/                          # 설정 파일
│   ├── test_definition.yaml          # 테스트 정의 파일 (100 테스트)
│   ├── database.conf                 # PostgreSQL 연결 설정
│   └── comparison_rules.yaml          # 비교 규칙 정의
│
├── /scripts/                         # 실행 스크립트
│   ├── main_batch.sh                 # 메인 배치 스크립트
│   ├── data_upload.sh                # 입력데이터 업로드
│   ├── program_execute.sh            # TOBE 프로그램 실행
│   ├── data_download.sh              # 출력데이터 다운로드
│   └── data_compare.sh               # 데이터 비교 스크립트
│
├── /src/                             # 소스 코드
│   ├── /python/
│   │   ├── config_reader.py          # 정의 파일 파서
│   │   ├── db_handler.py             # DB 연결 및 조작
│   │   ├── data_comparator.py        # 데이터 비교 로직
│   │   ├── report_generator.py       # 보고서 생성
│   │   └── main.py                   # 메인 프로그램
│   │
│   └── /cobol/
│       └── (Net COBOL 배치 프로그램 - 사전 개발)
│
├── /data/                            # 데이터 디렉토리
│   ├── /asis/                        # ASIS 참조 데이터
│   │   ├── /input/                   # ASIS 입력데이터
│   │   └── /output/                  # ASIS 출력데이터
│   │
│   ├── /tobe/                        # TOBE 테스트 데이터
│   │   ├── /input/                   # TOBE 입력 준비 디렉토리
│   │   └── /output/                  # TOBE 출력 비교 디렉토리
│   │
│   └── /temp/                        # 임시 파일 저장
│
├── /logs/                            # 로그 파일
│   ├── execution.log                 # 실행 로그
│   ├── error.log                     # 오류 로그
│   └── comparison.log                # 비교 결과 로그
│
├── /reports/                         # 검증 보고서
│   ├── summary_report.html           # 요약 보고서
│   ├── detailed_report.html          # 상세 보고서
│   └── failure_details.csv           # 실패 항목 상세
│
└── /database/                        # DB 스크립트
    ├── schema.sql                    # PostgreSQL 스키마
    └── test_results.sql              # 검증 결과 저장
```

---

## 5. 기술 스택

### 5.1 사용 기술

| 계층 | 기술 | 버전 | 용도 |
|------|------|------|------|
| **Orchestration** | Shell Script | bash 4.0+ | 배치 조율 |
| **Main Logic** | Python | 3.8+ | 비즈니스 로직 |
| **Database** | PostgreSQL | 12.0+ | 데이터 저장 |
| **Data Processing** | Pandas | 1.3+ | 데이터 비교/분석 |
| **Reporting** | Jinja2 | 3.0+ | 보고서 템플릿 |
| **Configuration** | YAML | - | 메타데이터 관리 |
| **Execution** | Net COBOL | - | TOBE 배치 실행 |

### 5.2 주요 라이브러리/도구

```
• psycopg2          - PostgreSQL Python 드라이버
• pandas            - 데이터프레임 조작
• pyyaml            - YAML 파일 파싱
• python-dotenv     - 환경변수 관리
• jinja2            - 템플릿 렌더링
• openpyxl          - Excel 보고서 생성
• difflib           - 텍스트 비교
• hashlib           - 파일 체크섬 검증
```

---

## 6. 구현 계획

### 6.1 단계별 구현 계획

#### **Phase 1: 기초 인프라 구축 (1주)**
- [ ] 프로젝트 디렉토리 구조 생성
- [ ] PostgreSQL 테이블 스키마 정의 및 생성
- [ ] 테스트 정의 파일(YAML) 양식 정의 및 샘플 작성
- [ ] Python 개발 환경 설정 (venv, requirements.txt)

#### **Phase 2: 핵심 모듈 개발 (2주)**
- [ ] `config_reader.py` - 정의 파일 파싱
- [ ] `db_handler.py` - PostgreSQL 연결 및 CRUD 작업
- [ ] `data_converter.py` - 문자코드 변환 (ABCDIC ↔ Shift_JIS)
- [ ] `file_handler.py` - 파일 업로드/다운로드 로직

#### **Phase 3: 데이터 비교 엔진 (1.5주)**
- [ ] `data_comparator.py` - DB 데이터 비교 알고리즘
- [ ] 파일 비교 로직 (텍스트/바이너리)
- [ ] 차이점 분석 및 상세 기록

#### **Phase 4: 자동화 스크립트 (1주)**
- [ ] Shell 스크립트 개발 (배치 조율)
- [ ] 에러 처리 및 재시도 로직
- [ ] 로깅 및 모니터링

#### **Phase 5: 보고서 생성 (1주)**
- [ ] `report_generator.py` - 보고서 템플릿
- [ ] HTML/CSV 보고서 생성
- [ ] Excel 통계 보고서

#### **Phase 6: 테스트 및 배포 (1.5주)**
- [ ] 단위 테스트 (Unit Tests)
- [ ] 통합 테스트 (Integration Tests)
- [ ] 샘플 데이터를 이용한 E2E 테스트
- [ ] 성능 최적화 및 튜닝
- [ ] 운영 배포 및 문서화

**총 소요 기간: 약 8주**

### 6.2 마일스톤

| 마일스톤 | 목표 | 기간 |
|---------|------|------|
| M1 | 기초 인프라 준비 완료 | 1주 |
| M2 | 핵심 모듈 개발 완료 | 3주 |
| M3 | 데이터 비교 엔진 완성 | 4.5주 |
| M4 | 배치 자동화 완성 | 5.5주 |
| M5 | 보고서 시스템 완성 | 6.5주 |
| M6 | 검증 테스트 완료 | 8주 |
| **Go Live** | **프로덕션 배포** | **8주 이후** |

---

## 7. 핵심 기능 상세 설계

### 7.1 정의 파일 (test_definition.yaml) 구조

```yaml
tests:
  - test_id: "TEST_001"
    test_name: "고객 마스터 조회"
    description: "고객 마스터 테이블 조회 테스트"
    
    # 입력 데이터 정의
    input:
      type: "database"  # database or file
      tables:
        - table_name: "customer_master"
          operation: "INSERT"  # INSERT, UPDATE, DELETE
          source_file: "/data/asis/input/TEST_001_customer.csv"
          key_columns: ["customer_id"]
    
    # TOBE 프로그램 실행
    execution:
      shell_program: "/path/to/tobe/batch/batch_001.sh"
      timeout: 300  # seconds
      parameters:
        - key: "TEST_ID"
          value: "TEST_001"
    
    # 출력 데이터 정의
    output:
      - type: "database"
        tables:
          - table_name: "customer_result"
            export_file: "/data/tobe/output/TEST_001_result.csv"
            comparison_columns: ["customer_id", "name", "address"]
      
      - type: "file"
        files:
          - source: "/path/to/tobe/output/result.txt"
            destination: "/data/tobe/output/TEST_001_result.txt"
            encoding: "shift_jis"
    
    # 비교 규칙
    comparison_rules:
      - type: "exact_match"  # exact_match, fuzzy_match, numeric_tolerance
        source: "database_table"
        target: "database_table"
      
      - type: "file_compare"
        source_file: "/data/asis/output/TEST_001_result.txt"
        target_file: "/data/tobe/output/TEST_001_result.txt"
        encoding: "shift_jis"
    
    # 성공 기준
    success_criteria:
      pass_condition: "all_exact_match"  # all_exact_match or percentage_match
      tolerance_percentage: 100

  - test_id: "TEST_002"
    # ... 이런 식으로 100개의 테스트 정의
```

### 7.2 데이터 비교 알고리즘

```
1. 행 개수 비교
   ├─ 불일치 → FAIL 기록
   └─ 일치 → 2번으로 진행

2. 컬럼별 데이터 타입 검증
   ├─ 불일치 → 경고 기록
   └─ 일치 → 3번으로 진행

3. 행별 데이터 비교
   ├─ 정렬 순서 확인
   ├─ 행의 순서 정렬 후 비교
   ├─ 각 행의 컬럼값 비교
   │  ├─ 정확 일치 → PASS
   │  ├─ 숫자형 공차 확인 → 공차 범위 내 → 경고
   │  ├─ 날짜/시간 형식 차이 → 정규화 후 비교
   │  └─ 불일치 → FAIL 상세 기록
   └─ 모든 행 비교 완료

4. 최종 판정
   ├─ 모두 일치 → PASS
   ├─ 경고 있음 → PASS(경고)
   └─ 불일치 있음 → FAIL
```

### 7.3 검증 결과 저장 구조 (PostgreSQL)

```sql
-- 검증 결과 테이블
CREATE TABLE test_validation_results (
    result_id SERIAL PRIMARY KEY,
    test_id VARCHAR(50),
    test_name VARCHAR(200),
    execution_date TIMESTAMP,
    status VARCHAR(20),  -- PASS, FAIL, PASS_WITH_WARNING
    total_rows_asis INT,
    total_rows_tobe INT,
    matched_rows INT,
    mismatch_rows INT,
    execution_time_sec INT,
    notes TEXT
);

-- 상세 불일치 항목 테이블
CREATE TABLE mismatch_details (
    detail_id SERIAL PRIMARY KEY,
    result_id INT REFERENCES test_validation_results(result_id),
    test_id VARCHAR(50),
    row_number INT,
    column_name VARCHAR(100),
    asis_value TEXT,
    tobe_value TEXT,
    mismatch_type VARCHAR(50),
    severity VARCHAR(20)  -- CRITICAL, WARNING
);
```

---

## 8. 예상 성과 및 효과

### 8.1 정량적 효과

| 항목 | 기존 (수동) | 개선 후 (자동화) | 효과 |
|------|-----------|--------------|------|
| **100개 테스트 검증 시간** | 50~80시간 | 2~3시간 | 약 95% 감소 |
| **인적 오류율** | 약 5~10% | 0.1% | 거의 제로 |
| **재실행 시간** | 20~30시간 | 2~3시간 | 90% 감소 |
| **결과 보고서 생성 시간** | 8~10시간 | 0.5시간 | 95% 감소 |

### 8.2 정성적 효과

- ✅ 마이그레이션 검증 프로세스의 **완전 자동화**
- ✅ 검증 결과의 **객관성 및 신뢰성** 확보
- ✅ 재검증 및 회귀 테스트 **용이성 증대**
- ✅ 마이그레이션 리스크 **조기 발견**
- ✅ 운영팀의 **생산성 향상**

---

## 9. 위험 요소 및 대응 방안

### 9.1 기술적 위험

| 위험 요소 | 영향도 | 가능성 | 대응 방안 |
|---------|-------|--------|---------|
| 문자코드 변환 오류 (ABCDIC ↔ Shift_JIS) | 높음 | 중간 | 변환 라이브러리 검증, 샘플 데이터로 선 테스트 |
| 대용량 데이터 처리 성능 | 중간 | 중간 | 배치 처리 최적화, 인덱스 활용 |
| PostgreSQL 연결 타임아웃 | 중간 | 낮음 | 연결 풀 관리, 재시도 로직 |
| 시간대 표준화 차이 | 중간 | 높음 | 사전 데이터 정규화 프로세스 |
| 환경 간 경로 차이 | 낮음 | 중간 | 설정 파일 기반 경로 관리 |

### 9.2 프로세스 위험

| 위험 요소 | 대응 방안 |
|---------|---------|
| 정의 파일 부정확 | 정의 파일 검증 프로세스 수립 |
| TOBE 프로그램 개발 지연 | 샘플 프로그램으로 선행 테스트 |
| 데이터 준비 지연 | 데이터 준비팀과 사전 조율 |
| 운영 이관의 복잡성 | 상세 운영 매뉴얼 및 교육 제공 |

---

## 10. 품질 보증 계획

### 10.1 테스트 전략

1. **단위 테스트 (Unit Test)**
   - 각 Python 모듈의 단위 테스트
   - 데이터 변환 함수 검증
   - 비교 로직 테스트

2. **통합 테스트 (Integration Test)**
   - DB 연결 및 조작 테스트
   - Shell 스크립트 실행 흐름 테스트
   - 전체 배치 프로세스 테스트

3. **E2E 테스트 (End-to-End Test)**
   - 10개 샘플 테스트 케이스로 전체 프로세스 검증
   - 다양한 데이터 타입 및 형식 검증
   - 성능 및 안정성 테스트

4. **회귀 테스트 (Regression Test)**
   - 최신 변경사항이 기존 기능을 훼손하지 않는지 확인
   - 수정사항 적용 후 재검증

### 10.2 코드 품질 기준

- 코드 커버리지: ≥ 85%
- 정적 분석 (pylint): 점수 ≥ 8.0/10
- 문서화율: ≥ 90%
- 에러 처리: 모든 예외 케이스 커버

---

## 11. 운영 및 유지보수

### 11.1 일일 운영 절차

```
1. 배치 실행 (자동/수동)
   └─ main_batch.sh 스크립트 실행

2. 결과 모니터링
   └─ execution.log, error.log 확인

3. 이상 발생 시 대응
   ├─ 오류 로그 분석
   ├─ 원인 파악
   └─ 재실행 또는 조치

4. 결과 보고
   └─ 검증 보고서 생성 및 배포
```

### 11.2 정기 유지보수

| 주기 | 작업 | 담당자 |
|------|------|--------|
| **월 1회** | PostgreSQL 백업 | DBA |
| **월 1회** | 로그 정리 및 아카이브 | 운영팀 |
| **분기 1회** | 성능 분석 및 최적화 | 개발팀 |
| **반기 1회** | 시스템 보안 업데이트 | 보안팀 |

---

## 12. 문서화 계획

### 12.1 산출 문서

1. **기술 문서**
   - 시스템 아키텍처 설계서
   - API/모듈 명세서
   - 데이터베이스 설계서

2. **사용자 문서**
   - 운영 매뉴얼
   - 정의 파일 작성 가이드
   - 보고서 해석 가이드

3. **개발 문서**
   - 소스 코드 주석 및 docstring
   - 테스트 케이스 명세
   - 변경 이력 (Change Log)

---

## 13. 성공 기준

프로젝트가 성공하기 위한 기준:

1. ✅ **기능 완성도**: 100개 테스트 자동 검증 시스템 완성
2. ✅ **정확성**: 수동 검증 대비 99.9% 이상 일치율
3. ✅ **성능**: 100개 테스트 2시간 이내 완료
4. ✅ **안정성**: 연속 운영 중 오류율 0.1% 이하
5. ✅ **운영성**: 운영팀 최소 교육으로 자체 운영 가능
6. ✅ **확장성**: 테스트 케이스 추가 시 정의 파일만 수정으로 확장 가능

---

## 14. 예산 및 자원

### 14.1 개발 인력 (8주)

| 역할 | 인원 | 소요시간 |
|------|------|---------|
| 프로젝트 리더 | 1명 | 8주 (40%) |
| Python 개발자 | 2명 | 8주 (100%) |
| DB/SQL 전문가 | 1명 | 4주 (100%) |
| QA/테스트 엔지니어 | 1명 | 4주 (100%) |
| **총 인원-월** | - | **약 14 인-월** |

### 14.2 인프라 자원

- PostgreSQL 서버 (기존 보유 가정)
- 개발 머신: 2대
- 테스트 환경: 1개 (독립 구성)

---

## 15. 일정 및 마일스톤

### Gantt Chart (개략)

```
Week 1   [=== 인프라 구축 ===]
Week 2-3 [====== 핵심 모듈 개발 ======]
Week 4   [=== 데이터 비교 엔진 ===]
Week 5   [== 배치 자동화 ==]
Week 6   [==== 보고서 시스템 ====]
Week 7-8 [======== 테스트 및 배포 ========]
```

---

## 부록 A: 용어 정의

| 용어 | 정의 |
|------|------|
| **ASIS** | 기존 메인프레임 시스템 (COBOL85, AIM/NDB) |
| **TOBE** | 신규 PITON 기반 시스템 (Net COBOL, PostgreSQL) |
| **마이그레이션 검증** | ASIS의 출력과 TOBE의 출력이 동일한지 확인하는 프로세스 |
| **정의 파일** | 테스트 메타데이터를 정의한 YAML 파일 |
| **문자코드 변환** | EBCDIC(ABCDIC) → UTF-8/Shift_JIS 변환 |
| **배치 프로세스** | 자동화된 일괄 처리 프로그램 |
| **PASS/FAIL** | 검증 결과 판정 (일치/불일치) |

---

## 부록 B: 참고 자료

- PostgreSQL 공식 문서: https://www.postgresql.org/docs/
- Python 데이터 처리: https://pandas.pydata.org/docs/
- Shell 스크립트 가이드: https://www.gnu.org/software/bash/manual/
- 문자코드 변환: https://docs.python.org/3/library/codecs.html

---

**문서 작성일**: 2026년 5월 30일  
**버전**: 1.0  
**상태**: 기획 완료  
**담당자**: [프로젝트 리더]