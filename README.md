# 현·신 비교 자동화 도구 (Working 프로토타입)

메인프레임 → 리눅스 마이그레이션의 배치 출력 동등성을 자동 검증하는 도구.

---

## 빠르게 시작하기

### 1. 환경 준비

- Ubuntu 22.04 이상
- Python 3.10+
- PostgreSQL 14+

```bash
# 의존성 설치
pip install -r requirements.txt

# PostgreSQL 설정은 docs/SETUP.md 참고
```

### 2. 설정

```bash
cp config.yaml.example config.yaml
# config.yaml을 환경에 맞게 수정
export POSTGRES_PASSWORD=your_password
```

### 3. 시연 실행

```bash
python -m src.cli.main --config ./config.yaml
```

샘플 데이터 1~10번 셸이 자동으로 처리되며, 일부 NG 케이스가 의도적으로 포함되어 있습니다.

---

## 문서 읽기 순서

Claude Code와 함께 작업하거나 인수받은 분은 아래 순서로 읽으세요.

1. **[docs/CLAUDE.md](docs/CLAUDE.md)** — Claude Code 작업 규칙 (AI 도구 사용 시)
2. **[docs/CONTEXT.md](docs/CONTEXT.md)** — 사업 맥락, 왜 만드는지
3. **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — 시스템 구조
4. **[docs/SPEC.md](docs/SPEC.md)** — 기능 명세
5. **[docs/TASKS.md](docs/TASKS.md)** — 작업 분할
6. **[docs/DECISIONS.md](docs/DECISIONS.md)** — 결정 이력
7. **[docs/HANDOFF.md](docs/HANDOFF.md)** — 인수인계 가이드 (TASKS.md의 T4-3에서 작성 예정)

---

## 폴더 구조

```
.
├── README.md         ← (루트) 빠른 시작·인수인계 안내
├── docs/             ← 모든 설계·맥락 문서 (CLAUDE/CONTEXT/ARCHITECTURE/SPEC/TASKS/DECISIONS/HANDOFF)
├── src/
│   ├── core/         ← 핵심 로직 (인터페이스 무관)
│   ├── cli/          ← CLI 인터페이스 (얇은 껍데기)
│   └── config/       ← 설정 로더
├── stub_batch/       ← 시연용 가짜 배치 (인수 후 교체)
├── samples/          ← 시연용 샘플 CSV
├── tests/
└── config.yaml
```

---

## 핵심 설계 원칙

- **Core / Interface 분리**: Core는 print 없이 객체만 반환. GUI 확장 가능.
- **결정론적 비교**: LLM 사용 금지. 판정은 코드가.
- **설정은 코드 바깥**: 인코딩·OS·경로 등은 config.yaml.
- **셸 1개씩 순차**: 실패 격리·디버깅 용이.

---

## 인수인계 시 교체 포인트

1. **`stub_batch/run_batch.py`** → 진짜 Net COBOL 배치 호출로 교체
2. **`config.yaml`** → 클라이언트별 환경값 채우기
3. **GUI 추가** → `src/gui/` 별도 디렉토리, Core 그대로 재사용

자세한 가이드는 `docs/HANDOFF.md` 참고 (T4-3에서 작성 예정).

---

## 라이선스 / 저작권

(추후 결정)
