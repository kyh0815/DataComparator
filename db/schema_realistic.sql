-- =============================================================================
-- schema_realistic.sql — 현실형 테스트 환경 전용 테이블 (Phase 7 다중 입출력 검증)
--
-- 목적: "한 셸(잡)이 여러 테이블/파일을 입력으로 읽고 DB·파일로 동시에 출력"하는
--       실 운영 형태를 시연·테스트하기 위한 **격리된** 테이블 묶음.
--
-- ⚠️ 데모 10셸(customer_master / transaction_log / tobe_result)과 **이름이 다른**
--    rt_* 테이블을 쓴다 → 데모 시드를 오염시키지 않는다(병행 안전).
--
-- 적용:
--   PGPASSWORD=... psql -h localhost -p 5432 -U postgres -d compare_proto -f db/schema_realistic.sql
-- (이 dev 박스는 dc-pg 포트 5433: -p 5433)
--
-- 인코딩 원칙은 db/schema.sql과 동일(DB 내부 UTF-8, 파일만 Shift-JIS, D-018).
-- 제약은 PK·NOT NULL만(프로토 범위).
-- =============================================================================

DROP TABLE IF EXISTS rt_summary;
DROP TABLE IF EXISTS rt_transaction;
DROP TABLE IF EXISTS rt_customer;

-- -----------------------------------------------------------------------------
-- rt_customer — 고객 마스터 (As-Is CSV에서 셸 실행 시 적재; 시드 없음)
--   컬럼은 데모 customer_master와 동일 스키마 → 입력 CSV 헤더 검증 통과.
-- -----------------------------------------------------------------------------
CREATE TABLE rt_customer (
    customer_id  TEXT    NOT NULL,
    name         TEXT    NOT NULL,
    kana         TEXT    NOT NULL,
    birth_date   DATE    NOT NULL,
    branch_code  TEXT    NOT NULL,
    account_type TEXT    NOT NULL,
    balance      BIGINT  NOT NULL,
    opened_date  DATE    NOT NULL,
    PRIMARY KEY (customer_id)
);

-- -----------------------------------------------------------------------------
-- rt_transaction — 거래 명세 (As-Is CSV에서 적재; 시드 없음)
--   컬럼은 데모 transaction_log와 동일 스키마.
-- -----------------------------------------------------------------------------
CREATE TABLE rt_transaction (
    tx_id         TEXT    NOT NULL,
    customer_id   TEXT    NOT NULL,
    tx_date       DATE    NOT NULL,
    tx_type       TEXT    NOT NULL,
    amount        BIGINT  NOT NULL,
    balance_after BIGINT  NOT NULL,
    branch_code   TEXT    NOT NULL,
    memo          TEXT,
    PRIMARY KEY (tx_id)
);

-- -----------------------------------------------------------------------------
-- rt_summary — 배치의 "DB 출력"(고객별 집계) staging 테이블.
--   stub(run_settlement.py)이 TRUNCATE+INSERT → exporter가 CSV로 다운로드해 비교.
--   컬럼명 = 출력 CSV 헤더(ASCII). 전부 TEXT(텍스트 비교라 캐스팅 마찰 제거).
-- -----------------------------------------------------------------------------
CREATE TABLE rt_summary (
    customer_id   TEXT    NOT NULL,          -- 고객번호
    customer_name TEXT,                      -- 고객 성명(마스터 조인)
    tx_count      TEXT    NOT NULL,          -- 거래 건수
    total_amount  TEXT    NOT NULL,          -- 거래금액 합계(엔)
    PRIMARY KEY (customer_id)
);
