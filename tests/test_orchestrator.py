"""T3-1 오케스트레이션(run_full_comparison) 테스트.

- 정의 로드·콜백·단계 진행·예외 격리·트랜잭션 경계 호출 순서 → mock으로 항상 실행(DB 0).
- 연속 DB 셸의 TRUNCATE 비블로킹(D-023 ②)·골든 일치(D-023 ①) → RUN_DB_TESTS=1 일 때만.
"""

import os
from pathlib import Path

import pytest

from src.config.definition import DefinitionError
from src.core import orchestrator
from src.core.models import (
    BatchConfig,
    ComparisonResult,
    ComparisonStatus,
    Config,
    DatabaseConfig,
    OutputConfig,
    ProgressEvent,
    ProgressKind,
    ShellDefinition,
)

_ROOT = Path(__file__).resolve().parents[1]


def _config(tmp_path, password="secret-pw"):
    return Config(
        encoding="Shift_JIS",
        asis_input_dir=tmp_path / "asis/input",
        asis_output_dir=tmp_path / "asis/output",
        tobe_output_dir=tmp_path / "tobe_output",
        report_dir=tmp_path / "reports",
        database=DatabaseConfig(
            # db_conn fixture와 동일하게 env에서 읽어 포트 비종속(병렬 DB 가동 대응).
            host=os.environ.get("PGHOST", "localhost"),
            port=int(os.environ.get("PGPORT", "5432")),
            dbname=os.environ.get("PGDATABASE", "compare_proto"),
            user=os.environ.get("PGUSER", "postgres"),
            password=password,
        ),
        batch=BatchConfig(),
        shell_ids=["001"],
        output=OutputConfig(),
        tobe_input_dir=tmp_path / "tobe_input",
        definition_file=tmp_path / "test_definition.yaml",
    )


def _def(test_id, input_type, output_type, **kw):
    base = dict(
        test_id=test_id,
        test_name=f"t{test_id}",
        input_type=input_type,
        input_csv=f"{test_id}.csv",
        output_type=output_type,
        expected_output_csv=f"{test_id}.csv",
        shell_program=(
            "stub_batch/run_batch_db.py" if input_type == "database"
            else "stub_batch/run_batch_file.py"
        ),
        input_table="transaction_log" if input_type == "database" else None,
        output_table="tobe_result" if output_type == "database" else None,
        output_file=f"{test_id}.csv" if output_type == "file" else None,
        export_csv=f"{test_id}.csv" if output_type == "database" else None,
    )
    base.update(kw)
    return ShellDefinition(**base)


class _FakeConn:
    """commit/rollback/close 호출을 시간순으로 기록하는 가짜 connection."""

    def __init__(self):
        self.calls: list[str] = []
        self.closed = False

    def commit(self):
        self.calls.append("commit")

    def rollback(self):
        self.calls.append("rollback")

    def close(self):
        self.closed = True
        self.calls.append("close")


def _patch_pipeline(monkeypatch, *, definitions, run_batch=None, compare=None,
                    connect=None, load_csv=None, copy_file=None):
    """orchestrator가 import한 협력 함수들을 일괄 monkeypatch한다."""
    monkeypatch.setattr(orchestrator, "load_definitions", lambda _p: definitions)
    if run_batch is not None:
        monkeypatch.setattr(orchestrator, "run_batch", run_batch)
    if compare is not None:
        monkeypatch.setattr(orchestrator, "compare_files", compare)
    if connect is not None:
        monkeypatch.setattr(orchestrator.psycopg2, "connect", connect)
    if load_csv is not None:
        monkeypatch.setattr(orchestrator, "load_input_csv", load_csv)
    if copy_file is not None:
        monkeypatch.setattr(orchestrator, "copy_input_file", copy_file)


# --- 정의 로드 / fatal 경계 -------------------------------------------------------


def test_missing_definition_file_is_fatal(tmp_path):
    """정의 파일 미설정 → DefinitionError 전파(폴백 없음, D-024)."""
    cfg = _config(tmp_path)
    cfg.definition_file = None
    with pytest.raises(DefinitionError, match="정의 파일"):
        orchestrator.run_full_comparison(cfg)


def test_db_connect_failure_is_fatal(tmp_path, monkeypatch):
    """DB 필요 셸이 있는데 접속 실패 → OrchestratorError(즉시 종료, SPEC 8)."""
    def _boom(**kw):
        raise RuntimeError("no server")

    _patch_pipeline(monkeypatch, definitions=[_def("001", "database", "database")], connect=_boom)
    cfg = _config(tmp_path)
    with pytest.raises(orchestrator.OrchestratorError, match="DB 접속 실패"):
        orchestrator.run_full_comparison(cfg)


def test_no_db_shells_never_connects(tmp_path, monkeypatch):
    """파일 전용 실행은 connect를 호출하지 않는다(lazy-connect)."""
    def _must_not_connect(**kw):
        raise AssertionError("DB 셸이 없으면 connect하면 안 된다")

    defs = [_def("006", "file", "file"), _def("007", "file", "file")]
    _patch_pipeline(
        monkeypatch, definitions=defs, connect=_must_not_connect,
        run_batch=lambda d, c, conn, clean=False: [(d.outputs[0], tmp_path / f"{d.test_id}.csv")],
        compare=lambda a, b, encoding: ComparisonResult(a.stem, ComparisonStatus.OK),
        copy_file=lambda src, dest: dest / src.name,
    )
    summary = orchestrator.run_full_comparison(_config(tmp_path))
    assert summary.total == 2 and summary.ok_count == 2


# --- 콜백 / 진행 이벤트 -----------------------------------------------------------


def test_runs_without_callback(tmp_path, monkeypatch):
    """콜백 없이 호출해도 동작한다(DoD)."""
    defs = [_def("006", "file", "file")]
    _patch_pipeline(
        monkeypatch, definitions=defs,
        run_batch=lambda d, c, conn, clean=False: [(d.outputs[0], tmp_path / f"{d.test_id}.csv")],
        compare=lambda a, b, encoding: ComparisonResult(a.stem, ComparisonStatus.OK),
        copy_file=lambda src, dest: dest / src.name,
    )
    summary = orchestrator.run_full_comparison(_config(tmp_path))  # on_progress=None
    assert summary.total == 1
    assert summary.report_csv_path.is_file()


def test_progress_events_sequence(tmp_path, monkeypatch):
    """콜백을 넘기면 SHELL_START → STEP(load/run/compare) → SHELL_DONE 순으로 발생한다."""
    defs = [_def("006", "file", "file")]
    _patch_pipeline(
        monkeypatch, definitions=defs,
        run_batch=lambda d, c, conn, clean=False: [(d.outputs[0], tmp_path / f"{d.test_id}.csv")],
        compare=lambda a, b, encoding: ComparisonResult(a.stem, ComparisonStatus.OK),
        copy_file=lambda src, dest: dest / src.name,
    )
    events: list[ProgressEvent] = []
    orchestrator.run_full_comparison(_config(tmp_path), on_progress=events.append)

    kinds = [(e.kind, e.step, e.step_status) for e in events]
    assert kinds == [
        (ProgressKind.SHELL_START, None, None),
        (ProgressKind.STEP, "load", "OK"),
        (ProgressKind.STEP, "run", "OK"),
        (ProgressKind.STEP, "compare", "OK"),
        (ProgressKind.SHELL_DONE, None, None),
    ]
    done = events[-1]
    assert done.result.status == ComparisonStatus.OK
    assert done.index == 1 and done.total == 1


# --- 예외 격리 (한 셸 실패가 다음 셸을 막지 않음) ---------------------------------


def test_one_shell_error_does_not_block_others(tmp_path, monkeypatch):
    """한 셸이 RunnerError를 던져도 ERROR로 기록하고 다음 셸은 정상 처리(SPEC 3-1)."""
    from src.core.runner import RunnerError

    defs = [_def("007", "file", "file"), _def("006", "file", "file")]

    def _run(d, c, conn, clean=False):
        if d.test_id == "007":
            raise RunnerError("종료코드 1")
        return [(d.outputs[0], tmp_path / f"{d.test_id}.csv")]

    _patch_pipeline(
        monkeypatch, definitions=defs, run_batch=_run,
        compare=lambda a, b, encoding: ComparisonResult(a.stem, ComparisonStatus.OK),
        copy_file=lambda src, dest: dest / src.name,
    )
    events: list[ProgressEvent] = []
    summary = orchestrator.run_full_comparison(_config(tmp_path), on_progress=events.append)

    assert summary.total == 2
    assert summary.error_count == 1 and summary.ok_count == 1
    err = next(r for r in summary.results if r.shell_id == "007")
    assert err.status == ComparisonStatus.ERROR and "종료코드 1" in err.error_message
    # 실패 셸의 STEP은 run 단계에서 ERROR로 보고된다.
    run_steps = [e for e in events if e.kind == ProgressKind.STEP and e.shell_id == "007"]
    assert run_steps[-1].step == "run" and run_steps[-1].step_status == "ERROR"


# --- shell_ids 명시 선택 (D-026) -------------------------------------------------


def test_shell_ids_selects_subset_in_definition_order(tmp_path, monkeypatch):
    """shell_ids 주면 해당 test_id만, 정의 파일 순서 유지로 처리한다."""
    defs = [_def("006", "file", "file"), _def("007", "file", "file"), _def("009", "file", "file")]
    processed = []

    def _run(d, c, conn, clean=False):
        processed.append(d.test_id)
        return [(d.outputs[0], tmp_path / "x.csv")]

    _patch_pipeline(
        monkeypatch, definitions=defs, run_batch=_run,
        compare=lambda a, b, encoding: ComparisonResult(a.stem, ComparisonStatus.OK),
        copy_file=lambda src, dest: dest / src.name,
    )
    summary = orchestrator.run_full_comparison(_config(tmp_path), shell_ids=["009", "006"])
    assert processed == ["006", "009"]  # 정의 순서 유지(요청 순서 아님)
    assert summary.total == 2


def test_shell_ids_unknown_is_fatal(tmp_path, monkeypatch):
    """정의에 없는 id 요청 → DefinitionError(silent drop 금지, 자가검증 ④)."""
    defs = [_def("006", "file", "file")]
    _patch_pipeline(monkeypatch, definitions=defs)
    with pytest.raises(DefinitionError, match="999"):
        orchestrator.run_full_comparison(_config(tmp_path), shell_ids=["006", "999"])


def test_shell_ids_none_runs_all(tmp_path, monkeypatch):
    """shell_ids=None(기본)이면 전체 정의 실행(D-024)."""
    defs = [_def("006", "file", "file"), _def("007", "file", "file")]
    _patch_pipeline(
        monkeypatch, definitions=defs,
        run_batch=lambda d, c, conn, clean=False: [(d.outputs[0], tmp_path / "x.csv")],
        compare=lambda a, b, encoding: ComparisonResult(a.stem, ComparisonStatus.OK),
        copy_file=lambda src, dest: dest / src.name,
    )
    summary = orchestrator.run_full_comparison(_config(tmp_path))
    assert summary.total == 2


# --- 트랜잭션 경계 호출 순서 (D-023) ----------------------------------------------


def test_db_input_commits_then_shell_rolls_back(tmp_path, monkeypatch):
    """DB 입력 셸: load 후 commit(① stub 가시성) → 셸 종료 시 rollback(② 읽기락 해제)."""
    fake = _FakeConn()
    load_calls = []
    run_calls = []
    defs = [_def("001", "database", "database")]

    def _run(d, c, conn, clean=False):
        run_calls.append(conn)
        return [(d.outputs[0], tmp_path / f"{d.test_id}.csv")]

    _patch_pipeline(
        monkeypatch, definitions=defs,
        connect=lambda **kw: fake,
        load_csv=lambda src, conn, table, encoding: load_calls.append((table, encoding)) or 5,
        run_batch=_run,
        compare=lambda a, b, encoding: ComparisonResult(a.stem, ComparisonStatus.OK),
    )
    orchestrator.run_full_comparison(_config(tmp_path))

    assert load_calls == [("transaction_log", "Shift_JIS")]
    assert run_calls == [fake]  # run_batch에 conn이 전달됨
    # 순서: load 후 commit이 run보다 먼저, 셸 종료 rollback, 마지막 close.
    assert fake.calls == ["commit", "rollback", "close"]
    assert fake.closed


def test_file_input_copies_to_shared_resolved_dir(tmp_path, monkeypatch):
    """파일 입력 복사처 = paths.input_dest_dir(tobe_input_dir 우선) — 드리프트 차단(🔴1)."""
    copy_calls = []
    defs = [_def("006", "file", "file")]
    _patch_pipeline(
        monkeypatch, definitions=defs,
        run_batch=lambda d, c, conn, clean=False: [(d.outputs[0], tmp_path / f"{d.test_id}.csv")],
        compare=lambda a, b, encoding: ComparisonResult(a.stem, ComparisonStatus.OK),
        copy_file=lambda src, dest, dest_name=None: copy_calls.append((src, dest, dest_name))
        or (dest / (dest_name or src.name)),
    )
    cfg = _config(tmp_path)
    orchestrator.run_full_comparison(cfg)

    src, dest, dest_name = copy_calls[0]
    assert src == cfg.asis_input_dir / "006.csv"
    assert dest == cfg.tobe_input_dir  # paths.input_dest_dir와 동일한 base(override 없으면 config 공통)
    assert dest_name is None  # dest_name 미지정 → 입력 파일명 그대로


# --- DB 통합 (RUN_DB_TESTS=1 일 때만) -------------------------------------------

_DB_ENABLED = os.environ.get("RUN_DB_TESTS") == "1"
_db_only = pytest.mark.skipif(not _DB_ENABLED, reason="DB 통합 테스트는 RUN_DB_TESTS=1 일 때만 실행")


def _seed_input_csv(path: Path):
    """transaction_log 적재용 최소 입력 CSV(Shift-JIS) — 시드 고객(C0001) 참조."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        (
            "tx_id,customer_id,tx_date,tx_type,amount,balance_after,branch_code,memo\n"
            "T00001,C0001,2025-05-01,入金,200000,1700000,101,給与振込\n"
            "T00002,C0001,2025-05-02,出金,50000,1650000,101,ATM出金\n"
        ).encode("shift_jis")
    )


@_db_only
def test_db_consecutive_shells_no_truncate_block(tmp_path):
    """🔴 D-023 ②: 연속 DB→DB 셸이 run_full_comparison에서 블로킹 없이 완주하고 OK가 된다.

    트랜잭션 경계(셸 종료 rollback)가 없으면 두 번째 셸 stub의 TRUNCATE tobe_result가
    첫 셸 export 읽기락에 막혀 timeout RunnerError가 난다. 본 테스트가 그 회귀 가드다.
    또한 골든(clean)·To-Be(non-clean)가 byte 동일(D-023 ①·§4)이라 OK로 판정된다.
    """
    import psycopg2

    from src.core import orchestrator as orch
    from src.core.loader import load_input_csv
    from src.core.runner import run_batch

    _TX_COLS = "tx_id,customer_id,tx_date,tx_type,amount,balance_after,branch_code,memo"

    cfg = _config(tmp_path, password=os.environ.get("POSTGRES_PASSWORD"))
    cfg.database.host = os.environ.get("PGHOST", "localhost")
    cfg.database.port = int(os.environ.get("PGPORT", "5432"))
    cfg.database.dbname = os.environ.get("PGDATABASE", "compare_proto")
    cfg.database.user = os.environ.get("PGUSER", "postgres")

    # 두 개의 DB→DB 셸. shell_program은 절대경로로 둬 정의파일 위치에 무관하게 실 stub을 부른다.
    db_stub = str(_ROOT / "stub_batch" / "run_batch_db.py")
    defs = [
        _def("001", "database", "database", shell_program=db_stub),
        _def("003", "database", "database", shell_program=db_stub),
    ]
    for d in defs:
        _seed_input_csv(cfg.asis_input_dir / d.input_csv)

    admin = psycopg2.connect(
        host=cfg.database.host, port=cfg.database.port, dbname=cfg.database.dbname,
        user=cfg.database.user, password=cfg.database.password,
    )
    try:
        # 다른 테스트가 의존하는 transaction_log 시드를 스냅샷해 두고, 끝나면 복원한다
        # (오케스트레이터의 DB 입력 load는 D-023 ①로 commit하므로 시드를 영구 오염시킨다).
        with admin.cursor() as cur:
            cur.execute(f"SELECT {_TX_COLS} FROM transaction_log ORDER BY tx_id")
            seed_rows = cur.fetchall()

        # 골든(정답지) 사전 생성: load→commit→clean run→export 결과를 asis_output에 둔다.
        cfg.asis_output_dir.mkdir(parents=True, exist_ok=True)
        for d in defs:
            load_input_csv(
                cfg.asis_input_dir / d.input_csv, admin, d.input_table, encoding=cfg.encoding
            )
            admin.commit()
            golden = run_batch(d, cfg, admin, clean=True)[0][1]
            (cfg.asis_output_dir / d.expected_output_csv).write_bytes(golden.read_bytes())
            admin.rollback()  # 셸 경계 모사(읽기락 해제)

        # 본 실행: 오케스트레이터가 자체 connection으로 두 셸을 연속 처리(load_definitions 주입).
        orig = orch.load_definitions
        orch.load_definitions = lambda _p: defs
        try:
            summary = orch.run_full_comparison(cfg)
        finally:
            orch.load_definitions = orig

        assert summary.total == 2
        details = [(r.shell_id, r.status, r.error_message) for r in summary.results]
        assert summary.ok_count == 2, details
    finally:
        # 시드 복원(suite 오염 방지) — 다음 테스트가 50건 seed를 그대로 보게 한다.
        with admin.cursor() as cur:
            cur.execute("TRUNCATE transaction_log")
            cur.executemany(
                f"INSERT INTO transaction_log ({_TX_COLS}) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                seed_rows,
            )
        admin.commit()
        admin.close()


# --- D-033: 다중 입력 적재 ---------------------------------------------------------


def test_multi_input_loads_each_table(tmp_path, monkeypatch):
    """inputs[]의 각 DB 입력이 대응 테이블에 적재되고, 적재마다 commit된다(D-023 ①)."""
    from src.core.models import InputSpec

    loaded = []
    conn = _FakeConn()
    d = _def("001", "database", "file", inputs=[
        InputSpec(csv="trans.csv", type="database", table="transaction_log"),
        InputSpec(csv="cust.csv", type="database", table="customer_master"),
    ])
    _patch_pipeline(
        monkeypatch, definitions=[d],
        connect=lambda **k: conn,
        run_batch=lambda *a, **k: [(a[0].outputs[0], tmp_path / "001.csv")],
        compare=lambda *a, **k: ComparisonResult("001", ComparisonStatus.OK),
        load_csv=lambda src, c, table, encoding: loaded.append(table),
    )
    orchestrator.run_full_comparison(_config(tmp_path))
    assert loaded == ["transaction_log", "customer_master"]      # 둘 다 적재
    assert conn.calls.count("commit") == 2                       # 적재마다 commit


# --- D-033 P2: 다중 출력 (셸당 결과 N건) ------------------------------------------


def test_multi_output_yields_result_per_output(tmp_path, monkeypatch):
    """한 셸에 출력 2개 → 결과 2건(출력별 output_name), RunSummary는 출력 단위 집계."""
    from src.core.models import OutputSpec

    outs = [
        OutputSpec(type="database", table="result_a", export_as="A.csv", expected="正解A.csv"),
        OutputSpec(type="file", file="B.sam", expected="正解B.sam"),
    ]
    d = _def("001", "database", "file", outputs=outs)
    # 출력별로 다른 status: A=OK, B=NG
    statuses = {"A.csv": ComparisonStatus.OK, "B.sam": ComparisonStatus.NG}

    def _compare(asis, tobe, encoding):
        return ComparisonResult("x", statuses[tobe.name])

    _patch_pipeline(
        monkeypatch, definitions=[d],
        connect=lambda **k: _FakeConn(),
        load_csv=lambda *a, **k: 0,
        run_batch=lambda dd, c, conn, clean=False: [(o, tmp_path / o.tobe_name) for o in dd.outputs],
        compare=_compare,
    )
    summary = orchestrator.run_full_comparison(_config(tmp_path))
    assert summary.total == 2                       # 출력 단위(셸 1개에 출력 2개)
    assert summary.ok_count == 1 and summary.ng_count == 1
    names = sorted((r.shell_id, r.output_name, r.status.value) for r in summary.results)
    assert names == [("001", "A.csv", "OK"), ("001", "B.sam", "NG")]
