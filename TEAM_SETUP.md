# TEAM_SETUP — 팀원 1인 셋업 한 장

> 목적: 주니어 팀원이 **자기 PostgreSQL + 자기 샘플**로 e2e(프리플라이트→検証実行→試験成績書) 한 바퀴를 깨끗한 환경에서 막힘없이 돌린다.
> 이 문서만 따라하면 끝나야 한다. 막히면 6번을 보라.

전제: Python 3.10+, PostgreSQL 접속 가능, repo 클론 완료.

---

## 1. config 만들기 (환경당 1회)

```bash
cp config.yaml.example config.yaml
```

`config.yaml.example`은 **건드리지 말 것**(템플릿). 복사본 `config.yaml`만 수정한다.
비밀번호는 config에 **절대 적지 않는다**(4번 env에서 읽음).

---

## 2. config.yaml 채우기 (필드별)

### `encoding`
변환 툴이 만든 CSV 인코딩. 실데이터는 보통 `Shift_JIS`.
```yaml
encoding: Shift_JIS
```

### `paths` — 경로 (★ `report_dir`는 필수)
| 필드 | 필수 | 의미 | 예시 |
|---|---|---|---|
| `asis_input_dir`  | ✔ | 코드변환 후 As-Is 입력 디렉토리 | `/home/alice/data/asis/input` |
| `asis_output_dir` | ✔ | As-Is 출력(정답) 디렉토리 | `/home/alice/data/asis/output` |
| `tobe_output_dir` | ✔ | To-Be(신환경) 출력 디렉토리 | `/home/alice/out/tobe_output` |
| `report_dir`      | ✔ **(격리 핵심)** | 결과·checkpoint·試験成績書 출력 위치 | `/home/alice/reports` |
| `tobe_input_dir`  | 선택 | 파일 입력 raw 복사 대상 | `/home/alice/out/tobe_input` |
| `definition_file` | 선택 | 정의 파일(매핑표 CSV→생성) | `./test_definition.yaml` |

```yaml
paths:
  asis_input_dir:  /home/alice/data/asis/input
  asis_output_dir: /home/alice/data/asis/output
  tobe_output_dir: /home/alice/out/tobe_output
  report_dir:      /home/alice/reports
  tobe_input_dir:  /home/alice/out/tobe_input
  definition_file: ./test_definition.yaml
```

### `database` — DB 접속 (비번 제외)
```yaml
database:
  host: localhost
  port: 5432
  dbname: compare_proto
  user: postgres
  password_env: POSTGRES_PASSWORD   # 이 환경변수 키에서 비번을 읽음(아래 4번)
```
host/port/dbname/user는 필수. `password_env`는 **비번 자체가 아니라 비번이 담긴 환경변수의 이름**이다.

---

## 3. ★ 결과 격리 — `report_dir`를 팀원마다 다르게

`report_dir` 하위에 checkpoint·리포트·試験成績書·diff가 전부 쌓인다.
**같은 디렉토리를 공유하면 서로의 결과·checkpoint가 섞인다.** 반드시 자기 것으로:

```yaml
  report_dir: /home/<자기이름>/reports   # 예: /home/alice/reports, /home/bob/reports
```

(CLI에서 1회성으로 덮어쓰려면 `--report-dir <경로>`도 가능.)

---

## 4. DB 비밀번호 = 환경변수 (config 평문 금지)

`password_env`에 적은 키 이름(기본 `POSTGRES_PASSWORD`)으로 export:

```bash
export POSTGRES_PASSWORD='자기_DB_비밀번호'
```

설정 안 하면 프리플라이트가 `DB 接続に失敗 … ※ 環境変数 POSTGRES_PASSWORD が設定されていません` 로 알려준다.

---

## 5. e2e 한 바퀴 실행

### (A) CLI — 자기 config로 직접
```bash
# ① 프리플라이트(사전점검: 경로·권한·DB접속·정의)
python3 -m src.cli.main --preflight --config ./config.yaml
# ② 검증 실행
python3 -m src.cli.main --config ./config.yaml
# ③ 試験成績書(증빙)
python3 -m src.cli.main --evidence --config ./config.yaml
```

### (B) GUI — 브라우저에서
```bash
GUI_PORT=8000 POSTGRES_PASSWORD='자기비번' ./run_gui.sh
# → http://127.0.0.1:8000/  (사전점검 → 실행 → 결과/試験成績書)
```

### (C) 동봉 데모셋으로 먼저 감 잡기 (선택)
자기 데이터 전에 정본 데모셋(24 CK — 파일/DB·byte/text/record·SAM/VSAM·N:M)으로 흐름만 확인:
```bash
POSTGRES_PASSWORD=devpw PGPORT=5433 ./samples/complete/run_demo.sh
```
데모 config(`samples/complete/config.yaml`)는 `.gitignore`라 clone 직후엔 없지만, `run_demo.sh`가
커밋된 `samples/complete/config.yaml.example`에서 **자동 생성**한다(DB값은 자기 환경에 맞게 수정 가능).
기대 결과: 출력 27건 / OK 22 · NG 4 · MISSING 1.

**완료 기준**: 프리플라이트 통과 → 실행 → 試験成績書가 `report_dir`에 생성. 그게 보이면 셋업 성공.

---

## 6. 막혔을 때 — 프리플라이트 에러를 읽어라

프리플라이트는 **무엇이·어디서 틀렸는지** 좌표·경로·필드 단위로 알려준다. 메시지 그대로 고치면 된다.

| 증상(메시지) | 원인 | 조치 |
|---|---|---|
| `ファイルがありません: <경로>` | 입력/정답 파일 없음·경로 오타 | `paths`의 해당 디렉토리·파일명 확인 |
| `書き込めません: <경로>` | `report_dir` 등 쓰기 권한 없음 | 디렉토리 권한·존재 확인, 자기 경로로 |
| `DB 接続に失敗 … 環境変数 … が設定されていません` | 비번 env 미설정 | 4번 `export POSTGRES_PASSWORD=…` 후 재실행 |
| `DB 接続に失敗`(env는 설정됨) | 진짜 비번·권한·host/port 문제 | DB 접속정보·계정 권한 확인 |

해결이 안 되면 추측하지 말고 메시지 전문과 자기 `config.yaml`(비번 제외)을 들고 물어볼 것.
