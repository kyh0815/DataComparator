# 현·신 비교 자동화 도구 (Working 프로토타입)

메인프레임 → 리눅스 마이그레이션의 **배치 출력 동등성을 자동 검증**하는 도구.
CLI 한 줄로 1~10번 셸을 적재 → 배치 → 비교 → 리포트까지 자동 처리하는 **E2E 프로토타입**이다.

---

## 빠르게 시작하기 (약 5분)

### 0. 환경

- Ubuntu 20.04+ / macOS (시연 기준 우분투, D-003)
- Python 3.10+
- PostgreSQL 14+ (네이티브 또는 Docker)

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 데이터베이스 준비 (시연용 Sample DB)

비교 도구는 입력을 PostgreSQL에 적재하고 일부 셸은 결과를 DB에 쓴다.
**팀원 셋업·데모 e2e의 정본 절차는 [TEAM_SETUP.md](TEAM_SETUP.md)** — 스키마는
데모 진입점(`run_demo.sh`)이 **자동 적용**하므로 DB(서버+`compare_proto`)만 준비하면 된다.

**(A) 우분투 네이티브** — PostgreSQL 설치 상세는 **[docs/SETUP.md](docs/SETUP.md)**.

**(B) Docker로 빠르게** (비밀번호는 본인이 정한다 — 레포·문서에 실값 금지):

```bash
docker run -d --name dc-pg \
  -e POSTGRES_PASSWORD='<자기비번>' -e POSTGRES_DB=compare_proto \
  -p 5432:5432 postgres:16
```

> 인코딩 원칙(D-018): DB 내부는 UTF-8, As-Is/To-Be **CSV만 Shift-JIS**, 변환은 파일↔DB 경계의 Python 레벨에서만.

### 3. 설정

```bash
cp config.yaml.example config.yaml      # 환경에 맞게 수정 (특히 database.port)
export POSTGRES_PASSWORD='<자기비번>'    # 비밀번호는 코드/설정이 아니라 환경변수로
```

### 4. 시연 실행

```bash
python -m src.cli.main --config ./config.yaml
# 또는 동등한 Shell 래퍼:
./run.sh --config ./config.yaml
```

성공하면 다음처럼 끝난다(샘플 데이터는 의도적으로 NG/ERROR를 포함):

```
═══════════════════════════════════════════
  완료: 총 10건 / OK 6 / NG 3 / ERROR 1 / MISSING 0
  소요: 0.7초
  리포트: ./out/reports/report_YYYYMMDD_HHMMSS.csv
═══════════════════════════════════════════
```

- **007** 한 줄 데이터 차이 / **008** 顧客名 전각 공백 / **009** 여러 줄 차이 / **010** 배치 실패(ERROR).
- NG/ERROR가 있으면 **종료 코드 1**, 전부 OK면 0. 상세 차이는 리포트 CSV와 `report_*_details/{셸}.diff`에 기록된다.
- 시연용 입력/정답지(골든)는 `samples/`에 이미 포함되어 있어 별도 생성이 필요 없다.

---

## CLI 옵션

| 인자 | 의미 | 기본값 |
|---|---|---|
| `--config` | 설정 파일 경로 | `./config.yaml` |
| `--shells` | 실행할 셸 범위/ID (`1-10` 또는 `001,003,007`) | 정의 파일 전체 |
| `--report-dir` | 리포트 출력 디렉토리 | config의 값 |
| `--verbose` | 모든 차이 줄 + 앱 로그 표시 | off |

---

## 테스트

```bash
pytest                                  # 단위·E2E (DB 불요 — DB 통합은 자동 skip)

# DB 통합까지 (PostgreSQL 필요)
RUN_DB_TESTS=1 PGHOST=localhost PGPORT=5432 PGDATABASE=compare_proto \
  PGUSER=postgres POSTGRES_PASSWORD='<자기비번>' pytest
```

---

## 폴더 구조

```
.
├── README.md              ← (루트) 빠른 시작·인수인계 안내
├── docs/                  ← 설계·맥락 문서 (CLAUDE/CONTEXT/ARCHITECTURE/SPEC/TASKS/DECISIONS/SETUP/HANDOFF)
├── src/
│   ├── core/              ← 핵심 로직 (인터페이스 무관, print 금지)
│   │   ├── orchestrator.py  ← E2E 오케스트레이션 (run_full_comparison)
│   │   ├── loader / runner / exporter / comparator / reporter / models
│   ├── cli/               ← CLI 인터페이스 (main.py 진입점 + output.py 표시)
│   └── config/            ← 설정 로더 (settings.py / definition.py)
├── stub_batch/            ← 시연용 가짜 배치 2종 (인수 후 교체)
│   ├── run_batch_db.py      ← DB 입력 흐름 (셸 001~005, 결제)
│   └── run_batch_file.py    ← 파일 입력 흐름 (셸 006~010, 야간 배치 시뮬)
├── db/schema.sql          ← 시연용 Sample DB 스키마 + 시드
├── samples/asis/
│   ├── input/             ← As-Is 입력 CSV (001~010)
│   └── output/            ← As-Is 정답지(골든) CSV (001~010)
├── tools/                 ← make_samples.py(입력 생성) / make_golden.py(골든 재생성)
├── tests/
├── config.yaml.example    ← 설정 예시 (복사해 config.yaml로, 실값은 gitignore)
├── test_definition.yaml   ← 셸별 정의 파일 (입력/출력 type·테이블 — 도구의 동적 적응 지점)
└── run.sh                 ← 얇은 Shell 기동 래퍼
```

---

## 핵심 설계 원칙

- **Core / Interface 분리**: Core는 `print` 없이 구조화 객체만 반환 → 같은 Core 위에 GUI 확장 가능.
- **결정론적 비교**: 판정에 LLM 금지. 통짜 바이트 비교(D-004)로 OK/NG.
- **설정은 코드 바깥**: 인코딩·OS·경로·DB 접속은 `config.yaml`, 셸별 메타데이터는 `test_definition.yaml`.
- **데이터 주도 라우팅**: 입력 2종(DB/파일) × 출력 2종(DB/파일) = 4사분면을 정의 파일이 결정(D-021·D-022).
- **셸 1개씩 순차**: 실패 격리·디버깅 용이. 한 셸 오류는 ERROR로 기록하고 다음 진행.

---

## 인수인계 시 교체 포인트

1. **`stub_batch/run_batch_db.py`·`run_batch_file.py`** → 진짜 Net COBOL 배치(실행 가능 파일)로 교체. Runner가 `execution.shell_program`을 직접 호출하므로 런처 수정 불필요(본질 계약은 `--shell-id`).
2. **`test_definition.yaml`** → 실 클라이언트 스키마·셸 목록으로 교체(도구의 동적 적응 지점).
3. **`config.yaml`** → 클라이언트별 환경값(인코딩·경로·OS·DB 접속).
4. **`db/schema.sql`** → 실 클라이언트 비즈니스 스키마로 교체(현재는 시연용 금융 도메인).
5. **GUI 추가** → `src/gui/` 별도 디렉토리, Core 그대로 재사용.
6. **골든 재생성** → 데이터 교체 후 `tools/make_golden.py`로 정답지를 다시 만든다(stub `--clean` 경로 재사용 → false-NG 차단).

자세한 가이드는 **[docs/HANDOFF.md](docs/HANDOFF.md)** 참고.

---

## 문서 읽기 순서

인수받았거나 Claude Code와 함께 작업하는 분은 아래 순서로 읽으세요.

1. **[docs/CLAUDE.md](docs/CLAUDE.md)** — Claude Code 작업 규칙 (AI 도구 사용 시)
2. **[docs/CONTEXT.md](docs/CONTEXT.md)** — 사업 맥락, 왜 만드는지
3. **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — 시스템 구조
4. **[docs/SPEC.md](docs/SPEC.md)** — 기능 명세
5. **[docs/TASKS.md](docs/TASKS.md)** — 작업 분할·진행 상황
6. **[docs/DECISIONS.md](docs/DECISIONS.md)** — 결정 이력 (D-001~)
7. **[docs/SETUP.md](docs/SETUP.md)** — 시연용 DB 구축
8. **[docs/HANDOFF.md](docs/HANDOFF.md)** — 인수인계 가이드 (T4-3에서 작성 예정)

---

## 라이선스 / 저작권

(추후 결정)
