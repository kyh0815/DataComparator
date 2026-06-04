# 현실형 테스트 환경 (Phase 7 다중 입출력)

> 실 운영 형태 — **한 셸(잡)이 여러 입력을 읽고 파일·DB로 동시에 출력** — 을 시연·검증하는
> 자기완결 환경. 데모 10셸(`config.yaml`/`test_definition.yaml`)과 **완전히 격리**되어 병행 안전.

---

## 1. 한 줄 실행

```bash
PGPORT=5433 POSTGRES_PASSWORD=devpw ./run_realistic.sh
```

(실 배포는 `PGPORT` 생략 = 5432. 비밀번호는 `POSTGRES_PASSWORD` 환경변수에서만 — 모델A.)

`run_realistic.sh`가 4단계를 수행한다:
1. **rt_* 테이블 생성** (`db/schema_realistic.sql`) — `rt_customer`·`rt_transaction`·`rt_summary`
2. **As-Is 입력 샘플 생성** (`tools/make_realistic_samples.py`, Shift-JIS)
3. **골든(정답) 생성** — stub `--clean` 경로 재사용(손으로 안 씀, false-NG 차단 D-027). `--skip-golden`로 생략 가능
4. **現新比較 실행** — 화면 모니터링 + CSV 리포트

> `PGPORT`/`PGHOST`는 `config.realistic.yaml`을 덮어쓴 실효 설정(`.config.realistic.effective.yaml`,
> gitignore)으로 반영된다. 산출물·리포트는 `out/realistic/`(gitignore).

---

## 2. 구성 (격리 자산)

| 구분 | 데모(기존) | 현실형(이번) |
|---|---|---|
| config | `config.yaml` | `config.realistic.yaml` |
| 정의 | `test_definition.yaml` | `test_definition.realistic.yaml` |
| DB 테이블 | customer_master / transaction_log / tobe_result | **rt_customer / rt_transaction / rt_summary** |
| 입력 샘플 | `samples/asis/input` | `samples/realistic/asis/input` |
| stub | run_batch_db.py / run_batch_file.py (단일 출력) | **run_settlement.py (다중 출력)** |

데모 테이블을 건드리지 않으므로(rt_* 별도) 데모/현실형을 같은 DB에서 번갈아 돌려도 시드 오염이 없다.

---

## 3. 시나리오 (정의 = `test_definition.realistic.yaml`)

### R01. 日次決済バッチ — 다중 입력 → 파일 + DB 동시 출력
- **입력(2건)**: `取引明細.csv`→`rt_transaction`(DB), `顧客マスタ.csv`→`rt_customer`(DB, 조인용)
- **출력(2건, 한 번 실행에 동시 생성)**:
  - 파일: `決済明細.csv` — 거래×고객 조인 명세
  - DB: `rt_summary` 테이블 → `顧客別集計.csv`로 export(고객별 건수·합계)
- 집계 단위 = 출력 → **결과 2건**(R01/明細, R01/集計). 한 셸이 파일·DB 양쪽에 내는 실 형태를 stub이 모사.

### R02. 夜間取引取込 — 파일 입력 + 항목별 경로 override(D-036)
- **입력**: `夜間取引.csv`(파일) + `顧客マスタ.csv`(DB). 파일 입력에 항목별 경로 지정:
  - `src_dir`(#4)=`…/input/night`, `dest_dir`(#7-4)=`…/tobe_input/night`, `dest_name`(#7-3)=`staged_夜間取引.csv`
- **출력**: `夜間明細.csv`에 `expected_dir`(#7)·`tobe_dir`(#11) 지정 → `…/output(.tobe)/night/` 하위로.
- config 공통 디렉토리를 **셸/항목마다 다른 위치로 override**하는 사장님 규격(D-036)을 실제로 검증.

---

## 4. 기대 결과

```
완료: 총 3건 / OK 3 / NG 0 / ERROR 0 / MISSING 0
리포트: out/realistic/reports/report_*.csv   (행: R01/明細, R01/集計, R02/-)
```

### NG/ERROR를 보고 싶으면
- 골든 한 줄을 바꾸고 `--skip-golden`으로 비교만 재실행하면 해당 출력만 NG가 뜬다(출력 단위):
  ```bash
  # 예: 集計 골든의 합계를 변형
  PGPORT=5433 POSTGRES_PASSWORD=devpw python3 -m src.cli.main --config ./.config.realistic.effective.yaml
  ```
- 입력/정답 파일을 지우면 그 항목만 MISSING으로 명시된다(silent drop 없음).

---

## 5. 실 데이터로 교체(인수인계)

1. `db/schema_realistic.sql`의 rt_* 를 **실 비즈니스 스키마**로 교체(또는 실 테이블명 사용).
2. `samples/realistic/asis/input/`의 입력 CSV·`asis/output/`의 정답을 실 데이터로 교체.
3. `test_definition.realistic.yaml`의 테이블·파일명·경로를 실 환경에 맞춤(또는
   `tools/mapping_to_definition.py`로 매핑표(CSV)에서 생성).
4. `run_settlement.py`(stub)를 **실 래퍼 배치**로 교체 — 입출력 계약(`--shell-id`/`--output-path`/
   `--output-type`/`--input-table|--input-file`)만 유지하면 Core 무수정.
