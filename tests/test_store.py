"""C5 체크포인트 영속화(store) 단위 테스트 — append-only JSONL·last-wins fold·부분실행 선택."""

from pathlib import Path

from src.core import store
from src.core.models import ComparisonResult, ComparisonStatus, DiffLine


def _r(shell_id, status, output_name=None, diffs=()):
    return ComparisonResult(
        shell_id=shell_id,
        status=status,
        diff_lines=list(diffs),
        output_name=output_name,
    )


def test_append_and_load_roundtrip(tmp_path):
    """결과를 append 후 load하면 전 필드가 복원된다(diff 포함)."""
    p = tmp_path / "checkpoint.jsonl"
    diff = DiffLine(line_number=2, asis_content="あ", tobe_content="い")
    store.append_shell(p, "001", [_r("001", ComparisonStatus.NG, "出A", [diff])])
    state = store.load_state(p)
    assert list(state) == ["001"]
    r = state["001"][0]
    assert r.status == ComparisonStatus.NG and r.output_name == "出A"
    assert r.diff_lines[0].asis_content == "あ" and r.diff_lines[0].line_number == 2


def test_immediate_write_one_line_per_shell(tmp_path):
    """셸마다 한 줄씩 즉시 기록된다(일괄 저장 아님 — 중단 시 부분 보존)."""
    p = tmp_path / "checkpoint.jsonl"
    store.append_shell(p, "001", [_r("001", ComparisonStatus.OK)])
    store.append_shell(p, "002", [_r("002", ComparisonStatus.OK)])
    assert len(p.read_text(encoding="utf-8").splitlines()) == 2


def test_last_wins_fold_merges_partial_over_prior(tmp_path):
    """같은 셸 재기록은 last-wins로 머지(부분 재실행이 직전 결과를 갱신, req4)."""
    p = tmp_path / "checkpoint.jsonl"
    store.append_shell(p, "001", [_r("001", ComparisonStatus.NG)])  # 직전
    store.append_shell(p, "002", [_r("002", ComparisonStatus.OK)])
    store.append_shell(p, "001", [_r("001", ComparisonStatus.OK)])  # 고쳐서 재실행 → OK
    state = store.load_state(p)
    assert state["001"][0].status == ComparisonStatus.OK  # 최신만
    assert len(store.latest_results(p)) == 2  # 셸 2건(중복 없음)


def test_shells_to_resume_includes_unrun_and_error(tmp_path):
    """resume = 미실행(상태에 없음) + ERROR. OK/NG/MISSING은 제외."""
    p = tmp_path / "checkpoint.jsonl"
    store.append_shell(p, "001", [_r("001", ComparisonStatus.OK)])
    store.append_shell(p, "002", [_r("002", ComparisonStatus.NG)])
    store.append_shell(p, "003", [_r("003", ComparisonStatus.ERROR)])
    # 004는 정의에만 있고 미실행
    assert store.shells_to_resume(p, ["001", "002", "003", "004"]) == ["003", "004"]


def test_shells_to_retry_is_ng_and_error(tmp_path):
    """retry = NG + ERROR(직전 실패). OK/미실행 제외."""
    p = tmp_path / "checkpoint.jsonl"
    store.append_shell(p, "001", [_r("001", ComparisonStatus.OK)])
    store.append_shell(p, "002", [_r("002", ComparisonStatus.NG)])
    store.append_shell(p, "003", [_r("003", ComparisonStatus.ERROR)])
    assert sorted(store.shells_to_retry(p)) == ["002", "003"]


def test_aggregate_worst_status_for_multi_output(tmp_path):
    """다중 출력 셸: 하나라도 NG면 retry 대상."""
    p = tmp_path / "checkpoint.jsonl"
    store.append_shell(p, "001", [_r("001", ComparisonStatus.OK, "A"), _r("001", ComparisonStatus.NG, "B")])
    assert store.shells_to_retry(p) == ["001"]


def test_load_missing_file_is_empty(tmp_path):
    assert store.load_state(tmp_path / "none.jsonl") == {}
    assert store.has_checkpoint(tmp_path / "none.jsonl") is False


def test_corrupt_last_line_is_skipped(tmp_path):
    """중단으로 마지막 줄이 깨져도 앞 줄들은 유효하게 읽힌다."""
    p = tmp_path / "checkpoint.jsonl"
    store.append_shell(p, "001", [_r("001", ComparisonStatus.OK)])
    with p.open("a", encoding="utf-8") as f:
        f.write('{"shell_id": "002", "resul')  # 잘린 줄
    state = store.load_state(p)
    assert list(state) == ["001"]
