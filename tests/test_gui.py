"""웹 UI 테스트 — 직렬화 + Flask 엔드포인트 + 연결설정 + 정의 미리보기 (DB·실서버 불요, 항상 실행).

Phase 7 (T7-3) 경량화: 화면은 **정의 파일 주도 단일 실행**(버튼1→/run SSE→모니터링→결과).
업로드-CSV 검증·매핑표 생성은 걷어냈으므로(D-034), 여기선 라우팅·SSE·traversal 차단·
연결설정 저장/테스트·정의 미리보기 배선만 검증한다(실 DB 접속 없음).
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from src.core.models import (
    ComparisonResult,
    ComparisonStatus,
    DiffLine,
    ProgressEvent,
    ProgressKind,
    RunSummary,
)
from src.gui import connection as conn_mod
from src.gui import web
from src.gui.serialize import event_to_dict, result_to_dict, summary_to_dict
from src.gui.upload import summarize_definition, summarize_definition_path

_EXAMPLE_CONFIG = str(Path(__file__).resolve().parents[1] / "config.yaml.example")


# --- 직렬화 (src/gui 전용, models 불변) ------------------------------------------


def test_result_to_dict_flattens_diff_lines():
    r = ComparisonResult("007", ComparisonStatus.NG, diff_lines=[DiffLine(2, "a", "b")])
    d = result_to_dict(r)
    assert d["status"] == "NG"
    assert d["diff_lines"] == [{"line_number": 2, "asis_content": "a", "tobe_content": "b"}]


def test_event_to_dict_shell_done_nests_result():
    ev = ProgressEvent(
        ProgressKind.SHELL_DONE, "001", 1, 10, result=ComparisonResult("001", ComparisonStatus.OK)
    )
    d = event_to_dict(ev)
    assert d["kind"] == "shell_done" and d["result"]["status"] == "OK"


def test_event_to_dict_step_has_no_result():
    ev = ProgressEvent(ProgressKind.STEP, "001", 1, 10, step="load", step_status="OK")
    d = event_to_dict(ev)
    assert d["step"] == "load" and d["result"] is None


def test_summary_to_dict_exposes_report_name_only():
    s = RunSummary(10, 6, 3, 1, 0, [], Path("/x/out/reports/report_20250101_000000.csv"))
    d = summary_to_dict(s, 12.37)
    assert d["report_name"] == "report_20250101_000000.csv"
    assert d["elapsed_seconds"] == 12.4 and d["ng_count"] == 3


# --- Flask 엔드포인트 -------------------------------------------------------------


@pytest.fixture
def client():
    web.app.config.update(TESTING=True)
    return web.app.test_client()


def _sse_messages(raw: bytes) -> list[dict]:
    lines = raw.decode("utf-8").splitlines()
    return [json.loads(l[len("data: "):]) for l in lines if l.startswith("data: ")]


def test_index_serves_japanese_page(client):
    """単一画面(縦アコーディオン): 接続設定 + ①定義 ②事前点検 ③検証実行 ④結果(GUI 재구성)."""
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "現新比較" in body and "検証実行" in body and "接続設定" in body
    assert "事前点検" in body and "試験成績書" in body  # 4단계 동선이 한 화면에


def test_index_active_config_accessor_not_self_recursive(client):
    """activeConfig()가 자기 자신을 호출하면 모든 config 의존 동작이 콜스택 초과로 깨진다(회귀 가드).

    b1bf0a7에서 `const activeConfig = () => activeConfig();`(무한재귀)로 들어가 메인 화면의
    정의 저장·preflight·실행이 RangeError로 전부 실패했었다. JS는 서버 테스트로 실행되지 않아
    렌더 본문에서 자기재귀 패턴 부재 + #config 셀렉터 참조를 정적으로 확인한다.
    """
    body = client.get("/").get_data(as_text=True)
    assert "activeConfig = () => activeConfig()" not in body  # 자기재귀 금지
    assert 'const activeConfig =' in body and '$("config")' in body  # #config 값을 읽는 accessor


def test_index_embeds_definition_preview(client, monkeypatch):
    """index가 config 정의 파일을 요약해 JSON으로 임베드한다(실행 전 미리보기)."""
    monkeypatch.setattr(
        web, "_definition_preview",
        lambda p: {"ok": True, "count": 2,
                   "shells": [{"test_id": "001", "input_type": "database",
                               "output_type": "file", "input_count": 2, "output_count": 1}],
                   "message": "2 シェル"},
    )
    body = client.get("/").get_data(as_text=True)
    assert "2 シェル" in body and '"input_count": 2' in body


def test_run_streams_progress_then_summary(client, monkeypatch):
    def fake_run(config, on_progress=None, shell_ids=None):
        on_progress(ProgressEvent(ProgressKind.SHELL_START, "001", 1, 1))
        on_progress(
            ProgressEvent(ProgressKind.SHELL_DONE, "001", 1, 1,
                         result=ComparisonResult("001", ComparisonStatus.OK))
        )
        return RunSummary(1, 1, 0, 0, 0, [], Path("out/reports/report_x.csv"))

    monkeypatch.setattr(web, "load_config", lambda p: SimpleNamespace(report_dir=Path(".")))
    monkeypatch.setattr(web, "run_full_comparison", fake_run)

    msgs = _sse_messages(client.get("/run?config=./config.yaml").get_data())
    types = [m["type"] for m in msgs]
    assert "progress" in types and "summary" in types and types[-1] == "done"
    assert next(m for m in msgs if m["type"] == "summary")["report_name"] == "report_x.csv"


def test_run_reports_error_message(client, monkeypatch):
    def boom(p):
        raise RuntimeError("설정 파일을 찾을 수 없습니다")  # Core/config 메시지는 한국어 유지

    monkeypatch.setattr(web, "load_config", boom)
    msgs = _sse_messages(client.get("/run?config=missing.yaml").get_data())
    assert any(m["type"] == "error" and "찾을 수 없습니다" in m["message"] for m in msgs)
    assert msgs[-1]["type"] == "done"


def test_report_download_ok(client, monkeypatch, tmp_path):
    (tmp_path / "report_ok.csv").write_text("shell_id,status\n001,OK\n", encoding="utf-8")
    monkeypatch.setattr(web, "load_config", lambda p: SimpleNamespace(report_dir=tmp_path))
    resp = client.get("/report/report_ok.csv")
    assert resp.status_code == 200 and b"001,OK" in resp.get_data()


def test_report_blocks_path_traversal(client, monkeypatch, tmp_path):
    (tmp_path.parent / "secret.csv").write_text("TOPSECRET", encoding="utf-8")
    monkeypatch.setattr(web, "load_config", lambda p: SimpleNamespace(report_dir=tmp_path))
    assert client.get("/report/..%2fsecret.csv").status_code == 404


# --- 연결 설정: save_connection (DB 불요) ----------------------------------------


def test_save_connection_atomic_with_backup(tmp_path):
    cfg = tmp_path / "config.yaml"
    # 1차 저장: 기존 파일 없음 → example 템플릿 사용, .bak 없음.
    conn_mod.save_connection(
        str(cfg), host="h1", port=5433, dbname="d", user="u", password_env="PE", encoding="Shift_JIS"
    )
    assert cfg.is_file()
    raw = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    assert raw["database"]["host"] == "h1" and raw["database"]["password_env"] == "PE"
    assert "password" not in raw["database"]  # 모델 A: 평문 비번 미기록
    assert "paths" in raw  # 템플릿의 다른 블록 보존
    assert not (tmp_path / "config.yaml.bak").exists()

    # 2차 저장: 기존 파일 있음 → .bak 백업 생성, 값 갱신.
    conn_mod.save_connection(
        str(cfg), host="h2", port=5433, dbname="d", user="u", password_env="PE", encoding="Shift_JIS"
    )
    assert (tmp_path / "config.yaml.bak").is_file()
    assert yaml.safe_load(cfg.read_text(encoding="utf-8"))["database"]["host"] == "h2"


def test_connection_test_endpoint_wires(client, monkeypatch):
    monkeypatch.setattr(
        web.connection, "test_connection",
        lambda **k: {"ok": True, "message": "OK", "checks": [{"name": "x", "ok": True}]},
    )
    r = client.post(
        "/connection/test",
        data={"host": "h", "port": "5433", "dbname": "d", "user": "u"},
    ).get_json()
    assert r["ok"] and r["checks"][0]["name"] == "x"


def test_connection_test_returns_table_list(monkeypatch):
    """접속(SELECT 1) + public 테이블 목록을 취득해 tables로 돌려준다."""
    class FakeCur:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, q, *a): self.q = q
        def fetchone(self): return (1,)
        def fetchall(self): return [("transaction_log",), ("tobe_result",), ("customer_master",)]
    class FakeConn:
        def cursor(self): return FakeCur()
        def close(self): pass

    monkeypatch.setattr(conn_mod.psycopg2, "connect", lambda **k: FakeConn())
    r = conn_mod.test_connection(host="h", port=5433, dbname="d", user="u")
    assert r["ok"] and "transaction_log" in r["tables"] and len(r["tables"]) == 3
    names = [c["name"] for c in r["checks"]]
    assert any("DB接続" in n for n in names) and any("テーブル取得" in n for n in names)


# --- 정의 미리보기 (읽기전용 요약) ----------------------------------------------

_DEF_YAML = b"""tests:
  - test_id: "001"
    input: { type: database, table: transaction_log, csv: 001.csv }
    execution: { shell_program: stub_batch/run_batch_db.py, timeout: 60 }
    output: { type: file, file: 001.csv }
    expected_output_csv: 001.csv
  - test_id: "002"
    input: { type: file, csv: 002.csv }
    execution: { shell_program: stub_batch/run_batch_file.py }
    output: { type: database, table: tobe_result, export_csv: 002.csv }
    expected_output_csv: 002.csv
"""


def test_summarize_definition_parses_shells():
    r = summarize_definition(_DEF_YAML)
    assert r["ok"] and r["count"] == 2
    s0, s1 = r["shells"]
    assert s0["test_id"] == "001" and s0["output_type"] == "file"
    assert s0["input_count"] == 1 and s0["output_count"] == 1
    assert s1["input_type"] == "file" and s1["output_type"] == "database"


def test_summarize_definition_reports_parse_error():
    r = summarize_definition(b"not: a valid tests file\n")
    assert r["ok"] is False and "失敗" in r["message"]


def test_summarize_definition_counts_multi_io():
    """다중 입력/출력 정의(T7-1/T7-2)는 input_count/output_count로 노출된다."""
    yml = (
        b"tests:\n"
        b"  - test_id: \"001\"\n"
        b"    input:\n"
        b"      type: database\n"
        b"      tables:\n"
        b"        - { csv: trans.csv, table: transaction_log }\n"
        b"        - { csv: cust.csv,  table: customer_master }\n"
        b"    execution: { shell_program: stub_batch/run_batch_db.py }\n"
        b"    outputs:\n"
        b"      - { type: database, table: tobe_result, export_as: A.csv, expected: gA.csv }\n"
        b"      - { type: file,     file: B.sam,                          expected: gB.sam }\n"
    )
    r = summarize_definition(yml)
    assert r["ok"] and r["count"] == 1
    assert r["shells"][0]["input_count"] == 2 and r["shells"][0]["output_count"] == 2


def test_summarize_definition_path_reads_file(tmp_path):
    p = tmp_path / "def.yaml"
    p.write_bytes(_DEF_YAML)
    assert summarize_definition_path(p)["count"] == 2
    # 없는 파일은 ok=False(미비 안내).
    assert summarize_definition_path(tmp_path / "missing.yaml")["ok"] is False


def test_definition_preview_endpoint(client, monkeypatch):
    monkeypatch.setattr(web, "_definition_preview", lambda p: {"ok": True, "count": 3, "shells": []})
    r = client.get("/definition/preview?config=./config.yaml").get_json()
    assert r["ok"] and r["count"] == 3


# --- 定義作成 화면(/define, D-037) -------------------------------------------------

def test_define_page_renders(client):
    """별도 정의작성 화면이 렌더되고 검증실행으로 돌아가는 링크가 있다."""
    body = client.get("/define").get_data(as_text=True)
    assert "定義作成" in body and 'href="/"' in body


def test_index_folds_definition_upload(client):
    """定義作成이 메인 화면 ①단계로 흡수됨(매핑 CSV 업로드 + 샘플 다운로드 링크가 인라인)."""
    body = client.get("/").get_data(as_text=True)
    assert "マッピング表" in body and "/definition/sample-csv" in body


def test_from_csv_generates_definition(client):
    """매핑표 CSV 업로드 → 정의 생성(셸·입출력 카운트 반환)."""
    from io import BytesIO
    csv = (
        "shell_id,kind,type,table,file,expected\n"
        "001,input,database,t_in,,\n"
        "001,output,database,t_out,,\n"
    )
    data = {"csv": (BytesIO(csv.encode("utf-8")), "m.csv")}
    r = client.post("/definition/from-csv", data=data, content_type="multipart/form-data").get_json()
    assert r["ok"] and r["count"] == 1
    assert r["shells"][0]["input_count"] == 1 and r["shells"][0]["output_count"] == 1


def test_from_csv_rejects_bad_rows(client):
    """필수열/타입 불비 행이 있으면 ok=False·errors 반환(부분 생성 안 함)."""
    from io import BytesIO
    data = {"csv": (BytesIO(b"shell_id,kind\n001,input\n"), "m.csv")}
    r = client.post("/definition/from-csv", data=data, content_type="multipart/form-data").get_json()
    assert r["ok"] is False and r["errors"]


def test_from_csv_requires_file(client):
    r = client.post("/definition/from-csv", data={}, content_type="multipart/form-data").get_json()
    assert r["ok"] is False


def test_sample_csv_downloads(client):
    """정의 CSV 샘플(동봉 Long 예시)을 화면에서 받을 수 있다."""
    resp = client.get("/definition/sample-csv")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "checklist," in body  # checklist 기준 Long 형식 헤더(선두 #SAMPLE 주석 허용)


def test_save_writes_to_config_definition_file(client, tmp_path):
    """생성 yaml을 config의 definition_file 경로에 저장한다."""
    defp = tmp_path / "gen_def.yaml"
    cfgp = tmp_path / "config.yaml"
    cfgp.write_text(
        "encoding: Shift_JIS\n"
        "paths:\n"
        f"  asis_input_dir: {tmp_path}/in\n"
        f"  asis_output_dir: {tmp_path}/out\n"
        f"  tobe_output_dir: {tmp_path}/tobe\n"
        f"  report_dir: {tmp_path}/rep\n"
        f"  definition_file: {defp}\n"
        "database: { host: h, port: 1, dbname: d, user: u, password_env: POSTGRES_PASSWORD }\n",
        encoding="utf-8",
    )
    r = client.post("/definition/save",
                    data={"yaml": "tests:\n  - test_id: X\n", "config": str(cfgp)}).get_json()
    assert r["ok"] and defp.read_text(encoding="utf-8").startswith("tests:")


def test_paths_save_writes_paths_block(client, tmp_path):
    """ディレクトリ設定 저장(G6): paths만 갱신, 다른 블록 보존, 빈칸은 기존값 유지."""
    import yaml
    cfgp = tmp_path / "config.yaml"
    cfgp.write_text(
        "encoding: Shift_JIS\n"
        "paths: { asis_input_dir: ./a, asis_output_dir: ./b, tobe_input_dir: ./ti, tobe_output_dir: ./c, report_dir: ./r, definition_file: ./d.yaml }\n"
        "database: { host: h, port: 1, dbname: d, user: u, password_env: POSTGRES_PASSWORD }\n"
        "batch: { type: stub }\n",
        encoding="utf-8",
    )
    r = client.post("/paths/save", data={
        "config": str(cfgp),
        "asis_input_dir": "/X/in", "asis_output_dir": "/X/out",
        "tobe_input_dir": "",  # 빈칸 → 기존값 유지
        "tobe_output_dir": "/X/tobe", "report_dir": "/X/rep", "definition_file": "./d2.yaml",
    }).get_json()
    assert r["ok"]
    saved = yaml.safe_load(cfgp.read_text(encoding="utf-8"))
    assert saved["paths"]["asis_input_dir"] == "/X/in"
    assert saved["paths"]["tobe_input_dir"] == "./ti"        # 빈칸 → 기존값 보존
    assert saved["paths"]["definition_file"] == "./d2.yaml"
    assert saved["database"]["host"] == "h" and saved["batch"]["type"] == "stub"  # 다른 블록 보존


def test_paths_get_returns_current_paths(client, tmp_path):
    """/paths는 선택 config의 paths를 폼 갱신용으로 돌려준다(G6)."""
    cfgp = tmp_path / "config.yaml"
    cfgp.write_text(
        "paths: { asis_input_dir: ./aa, asis_output_dir: ./bb, tobe_output_dir: ./cc, report_dir: ./rr, definition_file: ./dd.yaml }\n"
        "database: { host: h, port: 1, dbname: d, user: u }\n",
        encoding="utf-8",
    )
    r = client.get("/paths?config=" + str(cfgp)).get_json()
    assert r["asis_input_dir"] == "./aa" and r["definition_file"] == "./dd.yaml"


def test_groups_save_writes_batch_groups(client, tmp_path):
    """業務別ディレクトリ 저장(D-045): batch.groups만 갱신, name·base_dir 필수, 기존 키·다른 블록 보존."""
    import json
    import yaml
    cfgp = tmp_path / "config.yaml"
    cfgp.write_text(
        "paths: { asis_input_dir: ./a, asis_output_dir: ./b, tobe_output_dir: ./c, report_dir: ./r, definition_file: ./d.yaml }\n"
        "database: { host: h, port: 1, dbname: d, user: u }\n"
        "batch: { type: stub, groups: { 業務A: { base_dir: /old/A, success_exit_code: 3 } } }\n",
        encoding="utf-8",
    )
    groups = [
        {"name": "業務A", "base_dir": "/new/A", "asis_input_dir": "/data/A/in"},
        {"name": "", "base_dir": "x"},        # name 없음 → 스킵
        {"name": "業務B", "base_dir": ""},      # base_dir 없음 → 스킵
    ]
    r = client.post("/groups/save", data={"config": str(cfgp), "groups": json.dumps(groups)}).get_json()
    assert r["ok"]
    saved = yaml.safe_load(cfgp.read_text(encoding="utf-8"))
    assert set(saved["batch"]["groups"]) == {"業務A"}                # name·base_dir 없으면 스킵
    assert saved["batch"]["groups"]["業務A"]["base_dir"] == "/new/A"  # 갱신
    assert saved["batch"]["groups"]["業務A"]["asis_input_dir"] == "/data/A/in"
    assert saved["batch"]["groups"]["業務A"]["success_exit_code"] == 3  # 기존 키 보존
    assert saved["batch"]["type"] == "stub" and "database" in saved     # 다른 블록 보존


def test_groups_get_returns_list(client, tmp_path):
    """/groups는 batch.groups를 폼용 리스트로 돌려준다(D-045)."""
    cfgp = tmp_path / "config.yaml"
    cfgp.write_text(
        "database: { host: h, port: 1, dbname: d, user: u }\n"
        "batch: { type: stub, groups: { 業務A: { base_dir: /A, asis_input_dir: /A/in } } }\n",
        encoding="utf-8",
    )
    r = client.get("/groups?config=" + str(cfgp)).get_json()
    assert r[0]["name"] == "業務A" and r[0]["asis_input_dir"] == "/A/in"


# --- C3/C4: /preflight · /evidence 엔드포인트 -----------------------------------


def test_preflight_endpoint_returns_issues_json(client, monkeypatch):
    """/preflight는 점검 결과(ok/errors/warnings)를 CSV 좌표 JSON으로 돌려준다(C3 재사용)."""
    from src.core.preflight import PreflightIssue, PreflightReport

    rep = PreflightReport([
        PreflightIssue("error", "CK003/出A", "정답 파일이 없습니다: /x"),
        PreflightIssue("warning", "CK002", "record인데 key가 없습니다"),
    ])
    monkeypatch.setattr(web, "load_config", lambda p: SimpleNamespace())
    monkeypatch.setattr(web, "preflight", lambda config: rep)
    d = client.get("/preflight?config=c.yaml").get_json()
    assert d["ok"] is False
    assert d["errors"][0]["coordinate"] == "CK003/出A"
    assert d["warnings"][0]["message"].startswith("record")


def test_preflight_endpoint_config_error_is_ok_false(client, monkeypatch):
    """config 로드 실패도 화면 메시지로(ok=false, coordinate=config)."""
    def _boom(p):
        raise RuntimeError("config 없음")

    monkeypatch.setattr(web, "load_config", _boom)
    d = client.get("/preflight").get_json()
    assert d["ok"] is False and d["errors"][0]["coordinate"] == "config"


def test_evidence_endpoint_downloads_xlsx(client, monkeypatch, tmp_path):
    """/evidence는 생성한 試験成績書 파일을 첨부로 내려준다(C4)."""
    cfg = SimpleNamespace(definition_file=tmp_path / "def.yaml", report_dir=tmp_path)
    monkeypatch.setattr(web, "load_config", lambda p: cfg)
    monkeypatch.setattr(web, "load_definitions", lambda p: ["DEF"])
    monkeypatch.setattr(web.store, "latest_records", lambda p: ["REC"])

    def fake_gen(definitions, records, out):
        Path(out).write_bytes(b"xlsxdata")
        return Path(out)

    monkeypatch.setattr(web, "generate_evidence", fake_gen)
    resp = client.get("/evidence?config=c.yaml")
    assert resp.status_code == 200
    assert resp.data == b"xlsxdata"
