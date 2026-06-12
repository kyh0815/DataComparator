# TEAM_SETUP — 팀원 1인 셋업 한 장

> 목적: 주니어 팀원이 **자기 PostgreSQL + 자기 샘플**로 e2e(프리플라이트→検証実行→試験成績書) 한 바퀴를 깨끗한 환경에서 막힘없이 돌린다.
> 이 문서만 따라하면 끝나야 한다. 막히면 6번을 보라.

전제: Python 3.10+, 자기 PostgreSQL(직접 띄움 — 도구가 안 띄운다).

---

## 0. 처음 준비 (clone 후 1회)

```bash
# ① 클론 & 의존성
git clone <repo-url> && cd DataComparator
pip install -r requirements.txt          # psycopg2 · pyyaml · flask · openpyxl

# ② 설치 확인 — DB 없이 도는 단위 테스트로 환경 검증
python3 -m pytest -q                      # 286 passed / 10 skipped 면 환경 OK

# ③ ★자기 PostgreSQL 띄우기(도구가 안 띄움 — 직접). 예시는 docker, 비번은 자기가 정함:
docker run -d --name my-pg -e POSTGRES_PASSWORD='<자기비번>' -p 5432:5432 postgres:16
#   로컬에 PG가 이미 있으면 그걸 써도 됨(보통 5432). 설치 상세는 docs/SETUP.md.

# ④ DB 생성 — createdb만 수동(최초 1회). ★스키마(db/schema*.sql)는 run_demo가 자동 적용 — 수동 적용 말 것.
createdb -h localhost -p 5432 -U postgres compare_proto
```

> ★**DB는 팀원이 직접 띄운다.** 도구는 config에 적힌 값으로 *그 DB에 붙기만* 한다(첫 실배치 때 고객 DB에 붙는 연습).

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

### (B) GUI — 브라우저에서 (検証フロー: 한 화면 자동 진행)
```bash
GUI_PORT=8000 POSTGRES_PASSWORD='자기비번' ./run_gui.sh
# → http://127.0.0.1:8000/
```
1. **検証フロー** 화면에서 `▶ マッピング表を選択` → 매핑표(CSV/xlsx) 선택
   → 정의 생성·저장·**사전점검까지 자동** 진행(에러면 그 화면에서 멈추고 원인 표시).
2. 점검 통과 화면에서 `▶ 検証開始` 클릭 — 이후 전자동. **브라우저를 닫아도 실행은 계속**되고,
   다시 열면 진행/결과 화면으로 자동 복귀(중단됐으면 「続きから再開」 제안).
3. 결과 화면: 합격/불합격 판정·메트릭(一致率)·**不一致 상세(행별 As-Is↔To-Be diff)** +
   `試験成績書(Excel)`(要約·明細·**差分明細**=NG 전 행별 차이) / `結果データ(CSV)` 다운로드.
   재검증은 `再検証(全件)`(저장된 정의로, 파일 재업로드 불요) / `NG・ERRORのみ再検証`.
- 운영 주의: GUI 서버는 **단일 프로세스**(run_gui.sh 그대로)로 띄운다 — gunicorn 멀티워커 금지(실행 상태가 깨짐).
- 서버 PC가 절전되면 실행도 멈춘다 — 장시간(야간) 실행 시 절전 해제.

### (C) ★먼저 권장: 동봉 데모셋으로 내 환경 검증 (자기 DB로 e2e)
자기 데이터 전에 정본 데모셋(24 CK — 파일/DB·byte/text/record·SAM/VSAM·N:M)으로 자기 환경이 도는지 확인.

1. **데모 config의 DB값을 자기 것으로** — `samples/complete/config.yaml`(없으면 run_demo가 example에서 복사):
   ```bash
   cp samples/complete/config.yaml.example samples/complete/config.yaml   # run_demo가 없으면 자동 복사도 함
   # → samples/complete/config.yaml 의 database: host/port/dbname/user 를 §0에서 띄운 자기 값으로 편집
   ```
   ★접속 값은 이 config가 **단일 진실** — run_demo의 스키마적용·골든·프리플라이트·비교가 **전부 여기서** 읽는다
   (PGPORT 같은 env·하드코딩 없음). config의 port를 바꾸면 전부 그 포트로 붙는다.
2. **비번 env + 실행**:
   ```bash
   export POSTGRES_PASSWORD='자기비번'
   ./samples/complete/run_demo.sh
   ```
기대 결과: **출력 27건 / OK 22 · NG 4 · MISSING 1**, 試験成績書(.xlsx)가 `samples/complete/reports/`에 생성.

> DB 없이 파일 CK만 보려면(022건): DB CK(019/020)는 빼고 `--shells`로 선택 —
> `python3 -m src.cli.main --config samples/complete/config.yaml --shells CK001,…,CK024`(019·020 제외). DB 불요.

**완료 기준**: 프리플라이트 통과 → 실행 → 試験成績書가 생성. 그게 보이면 셋업 성공.

---

## 7. 매핑표 작성 (자기 정의 만들 때)
검증할 셸-입출력 매핑은 **엑셀 템플릿**으로 채운다(코드·고정길이가 Excel 자동변환에 안 깨지게 텍스트 서식 잠금):
- 템플릿: `definition_template.xlsx`(루트). 팀원에게 이 파일을 공유 → Excel로 채워 제출.
- 변환: `python3 tools/mapping_to_definition.py 채운표.xlsx -o test_definition.yaml` (.xlsx 직접 읽음, CSV 저장 불요).
- 칼럼: checklist·io(input/output)·type(database/file/sam/vsam)·input·as_is_output·to_be_output·input_dir·as_is_dir·to_be_dir·compare_mode·key_columns·fixed_layout·… (헤더 그대로).

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
