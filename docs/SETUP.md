# SETUP.md — 시연용 Sample DB 환경 구축 (우분투)

> ⚠️ **이 문서는 시연용 sample DB 구축 가이드다.** 여기서 만드는 스키마(`db/schema.sql`)는
> 금융 도메인을 흉내 낸 *시연용*이며, 실 운영에서는 마이그레이션 팀이 설계한 진짜
> 비즈니스 스키마(도메인 깊이가 다름)가 사용된다. **인수인계 시 정직원이 실 클라이언트
> 스키마로 교체**해야 한다.
>
> **인코딩 원칙 (D-018)** — 매우 중요:
> - PostgreSQL DB 내부는 **표준 UTF-8**. (DB 인코딩을 Shift-JIS로 설정하지 *않는다*.)
> - As-Is / To-Be 출력 **CSV 파일만 Shift-JIS**.
> - 파일 ↔ DB 경계에서만 Python 레벨(`encoding='shift_jis'`)로 디코드/인코드.
> - 비교는 파일 레벨에서 일어나므로 DB 내부 인코딩과 무관하게 성립한다.

깨끗한 우분투에서 이 문서를 위에서부터 따라 하면 PostgreSQL 설치 → DB/사용자 →
환경변수 → 스키마 적용 → 동작 확인까지 끝난다.

---

## 0. 전제

- 우분투 20.04 / 22.04 (시연 환경, D-003)
- `sudo` 권한
- 프로젝트 루트에서 명령을 실행한다고 가정 (`db/schema.sql` 경로 기준)

---

## 1. PostgreSQL 설치

```bash
sudo apt update
sudo apt install -y postgresql postgresql-client
```

설치 후 서비스 동작 확인:

```bash
sudo systemctl status postgresql      # active (exited/running) 이면 OK
sudo systemctl enable --now postgresql
```

---

## 2. DB · 사용자 준비

이 프로토는 시연 단순화를 위해 기본 슈퍼유저 `postgres`를 그대로 쓴다.

> ℹ️ **`postgres` 유저에 대하여**: 시연용 슈퍼유저다. **실 운영에서는 권한이 분리된
> 별도 유저(예: 적재 전용 계정)로 교체하는 것을 권장**한다.

### 2-1. `postgres` 유저 비밀번호 설정

```bash
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'demo_password';"
```

> 위 `'demo_password'`는 **예시**다. 실제 값은 본인이 정하고, 아래 4장에서
> 같은 값을 환경변수 `POSTGRES_PASSWORD`에 넣는다.

### 2-2. 데이터베이스 생성

```bash
sudo -u postgres createdb compare_proto
```

> DB 인코딩은 우분투 기본 템플릿(UTF-8)을 그대로 따른다. **Shift-JIS로 만들지 않는다.**
> (확인: 6장 locale 점검)

---

## 3. config.yaml 키 매핑

여기서 만든 값이 `config.yaml`(또는 `config.yaml.example`)의 어느 키와 대응되는지:

| SETUP에서 만든 것 | config.yaml 키 | 비고 |
|---|---|---|
| 호스트 `localhost` | `database.host` | 로컬 시연 기준 |
| 포트 `5432` | `database.port` | PostgreSQL 기본 |
| DB명 `compare_proto` | `database.dbname` | 2-2에서 생성 |
| 유저 `postgres` | `database.user` | 시연용 슈퍼유저 |
| 비밀번호 (2-1에서 정한 값) | `database.password_env` → **환경변수** | 설정 파일에 직접 적지 않음 (4장) |

> 비밀번호는 `config.yaml`에 직접 쓰지 않는다. `password_env`가 가리키는
> **환경변수 이름**(기본 `POSTGRES_PASSWORD`)만 설정에 두고, 실제 값은 환경변수로 준다.

---

## 4. 비밀번호 환경변수 설정 (`POSTGRES_PASSWORD`)

`config.yaml`의 `database.password_env: POSTGRES_PASSWORD`와 연결된다.
2-1에서 정한 비밀번호와 **같은 값**을 넣어야 한다.

### 4-1. 임시 (현재 터미널 세션 한정)

```bash
export POSTGRES_PASSWORD='demo_password'
```

> ⚠️ `export`는 **현재 터미널에서만** 유효하다. 새 터미널을 열거나 재부팅하면 사라진다.
> 시연 도중 새 탭에서 실행하면 "비밀번호 없음"으로 실패할 수 있으니, 시연 전에는
> 아래 4-2(영구 설정)를 권장한다.

### 4-2. 영구 — 방법 A: `~/.bashrc`

```bash
echo "export POSTGRES_PASSWORD='demo_password'" >> ~/.bashrc
source ~/.bashrc          # 현재 터미널에도 즉시 반영
```

### 4-3. 영구 — 방법 B: 프로젝트 `.env` (선택)

레포에 커밋되지 않도록 `.gitignore`에 `.env`가 포함돼 있는지 확인하고:

```bash
echo "POSTGRES_PASSWORD=demo_password" >> .env
```

> `.env`를 쓸 경우, 실행 전에 셸로 로드한다:
> ```bash
> set -a; source .env; set +a
> ```

### 4-4. 설정 확인

```bash
echo "$POSTGRES_PASSWORD"     # 정한 값이 출력되면 OK (빈 줄이면 미설정)
```

---

## 5. 스키마 + 더미 데이터 적용

프로젝트 루트에서:

```bash
PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U postgres -d compare_proto -f db/schema.sql
```

성공하면 `CREATE TABLE` ×2, `INSERT 0 20`, `INSERT 0 50`이 출력된다.
(`db/schema.sql` 상단에 `DROP TABLE IF EXISTS`가 있어 **여러 번 재적용**해도 안전하다.)

---

## 6. 동작 확인

### 6-1. 행 수 확인

```bash
PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U postgres -d compare_proto \
  -c "SELECT 'customer_master' AS tbl, count(*) FROM customer_master
      UNION ALL
      SELECT 'transaction_log', count(*) FROM transaction_log;"
```

기대 결과: `customer_master 20`, `transaction_log 50`.

### 6-2. 일본어 데이터 확인 (한자·가나 표시)

```bash
PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U postgres -d compare_proto \
  -c "SELECT customer_id, name, kana, account_type FROM customer_master LIMIT 3;"
```

기대 결과 (한자·가나가 깨지지 않고 보여야 함):

```
 customer_id |   name   |      kana      | account_type
-------------+----------+----------------+--------------
 C0001       | 田中太郎 | タナカタロウ   | 普通
 C0002       | 佐藤花子 | サトウハナコ   | 普通
 C0003       | 鈴木一郎 | スズキイチロウ | 当座
```

> 여기서 글자가 `???`나 깨진 문자로 보이면 **터미널/로케일** 문제일 가능성이 높다 (6-3 아님, 7장 locale 참조).
> DB 자체는 UTF-8이므로 데이터는 정상 저장돼 있다.

---

## 7. 트러블슈팅 (가장 흔한 사고)

### 7-1. 접속 실패: `peer authentication failed` (비밀번호 대신 OS 유저로 인증되는 경우)

증상: `psql -h localhost -U postgres ...` 실행 시 `Peer authentication failed for user "postgres"`.

원인: `pg_hba.conf`의 인증 방식이 `peer`(OS 유저 일치)로 되어 있어 비밀번호 인증이 안 됨.

해결: `pg_hba.conf`의 로컬 라인을 `peer` → `md5`(또는 `scram-sha-256`)로 변경.

```bash
# 경로 확인 (버전에 따라 14/16 등 숫자가 다름)
sudo -u postgres psql -c "SHOW hba_file;"

# 해당 파일에서 아래와 같은 라인의 마지막 컬럼 peer → md5 로 수정
#   local   all   all                     peer      →   md5
#   host    all   all   127.0.0.1/32      ...        →   md5
sudo nano /etc/postgresql/16/main/pg_hba.conf

# 수정 후 반영
sudo systemctl restart postgresql
```

> `-h localhost`(TCP) 접속에는 `host ... 127.0.0.1/32` 라인이, `psql`만 쓰는 소켓
> 접속에는 `local` 라인이 적용된다. 비밀번호 인증을 쓰려면 해당 라인을 `md5`로.

### 7-2. 일본어 깨짐: 로케일(locale) 확인

증상: 6-2에서 한자·가나가 `???`로 표시.

확인:

```bash
locale                                   # LANG, LC_ALL 등 확인
PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U postgres -d compare_proto \
  -c "SHOW server_encoding;"             # UTF8 이어야 함
```

해결: DB는 UTF-8이 맞는데 화면만 깨지면 **터미널 로케일**을 UTF-8로 맞춘다.

```bash
sudo apt install -y locales
sudo locale-gen ja_JP.UTF-8 en_US.UTF-8
export LANG=en_US.UTF-8                  # 또는 ja_JP.UTF-8
```

> 핵심: **DB는 UTF-8 그대로 둔다.** 깨짐은 거의 항상 *표시(터미널) 측* 문제다.
> 파일 비교용 Shift-JIS 변환은 본 도구가 파일 경계에서 Python으로 처리하므로
> DB/터미널 로케일과 무관하다.

---

## 8. 완료 체크리스트

- [ ] `sudo systemctl status postgresql` → 동작 중
- [ ] `compare_proto` DB 생성됨
- [ ] `POSTGRES_PASSWORD` 환경변수 설정 (영구 권장)
- [ ] `db/schema.sql` 적용 → CREATE ×2 / INSERT 20 / INSERT 50
- [ ] 6-1 행 수 20 / 50 확인
- [ ] 6-2 일본어 정상 표시 확인
- [ ] `config.yaml`의 `database.*` 키가 3장 매핑과 일치

여기까지 통과하면 Loader(T2-2) 작업으로 넘어갈 수 있다.
