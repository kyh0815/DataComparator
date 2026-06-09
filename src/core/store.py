"""C5 체크포인트 영속화 — 셸 결과를 append-only JSONL로 즉시 기록하고 부분 실행 선택을 돕는다.

한 줄 = 한 셸의 결과 묶음(JSON). **셸 종료 직후 append+flush+fsync**(중단 시 부분 상태 보존 — run
끝 일괄저장 금지, HANDOFF_V3 C5 req2). 읽을 때 **shell_id last-wins로 fold** → 직전 전체 결과에
부분 결과가 머지된 '최신 상태'(전체 1000건 전제, req4). 메모리 휘발 방지 영속화도 이 파일이 겸한다.

print 금지(CLAUDE.md 3-1). 직렬화는 core 자족(gui/serialize에 의존하지 않음 — core→interface 금지).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .models import ComparisonResult, ComparisonStatus, DiffLine

CHECKPOINT_NAME = "checkpoint.jsonl"
# 장기 운영 메모(E 보류): JSONL은 run마다 누적 성장한다. 1000건×다회 운영에서 커지면 fold 후
# 재기록(compaction)으로 압축할 수 있다 — 현재 fold가 정상 동작하므로 기능엔 영향 없음(보류).


@dataclass
class ShellRecord:
    """체크포인트의 셸 1건 최신 기록 — 결과 + 출처(run_id). C4 試験成績書의 행 출처 표기에 쓴다."""

    shell_id: str
    results: list[ComparisonResult] = field(default_factory=list)
    run_id: str | None = None  # 이 결과를 만든 run 식별자(시각). 낡은 OK 위장 방지(C4 req2)

# 부분 실행 선택 기준(HANDOFF_V3 C5 req3). resume=이어하기, retry=직전 실패 재시험.
_RESUME_STATUSES = {ComparisonStatus.ERROR.value}  # +미실행(상태에 없는 셸)은 호출측에서 합산
_RETRY_STATUSES = {ComparisonStatus.NG.value, ComparisonStatus.ERROR.value}


def checkpoint_path(report_dir: Path) -> Path:
    """체크포인트 파일 경로(리포트 디렉토리 하위 고정 이름)."""
    return Path(report_dir) / CHECKPOINT_NAME


def append_shell(
    path: Path, shell_id: str, results: list[ComparisonResult], *, run_id: str | None = None
) -> None:
    """한 셸의 결과 묶음을 JSONL 한 줄로 즉시 추가한다(append+flush+fsync, 부분상태 보존).

    run_id(이 결과를 만든 run 식별자=시각)를 함께 박아 C4가 행별 출처를 표기한다(낡은 OK 위장 방지).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "shell_id": shell_id,
        "run_id": run_id,
        "results": [_result_to_dict(r) for r in results],
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())  # 야간 중단 대비 디스크 확정


def load_records(path: Path) -> dict[str, ShellRecord]:
    """JSONL을 shell_id last-wins로 fold해 '최신 상태'(shell_id → ShellRecord)를 반환한다.

    같은 셸이 여러 번 기록됐으면 마지막 기록만 남긴다(부분 재실행이 직전 결과를 머지·갱신, req4).
    파일이 없으면 빈 dict. 깨진 줄은 건너뛴다(부분 flush 중 중단 대비).
    """
    path = Path(path)
    if not path.is_file():
        return {}
    state: dict[str, ShellRecord] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue  # 중단으로 마지막 줄이 깨졌을 수 있음 — 무시(앞 줄들은 유효)
            sid = record["shell_id"]
            state[sid] = ShellRecord(
                shell_id=sid,
                results=[_result_from_dict(d) for d in record.get("results", [])],
                run_id=record.get("run_id"),
            )
    return state


def load_state(path: Path) -> dict[str, list[ComparisonResult]]:
    """선택용 뷰: shell_id → 결과 리스트(출처 제외). 부분실행 선택(resume/retry)이 쓴다."""
    return {sid: rec.results for sid, rec in load_records(path).items()}


def latest_records(path: Path) -> list[ShellRecord]:
    """머지된 최신 상태를 셸 기록 리스트로(출처 run_id 포함). C4 試験成績書 전제."""
    return list(load_records(path).values())


def latest_results(path: Path) -> list[ComparisonResult]:
    """머지된 최신 상태의 전체 결과를 평탄화해 반환한다(출처 불요한 소비자용)."""
    results: list[ComparisonResult] = []
    for rec in load_records(path).values():
        results.extend(rec.results)
    return results


def shells_to_resume(path: Path, all_ids: list[str]) -> list[str]:
    """이어하기 대상: 미실행(상태에 없음) + ERROR. 이미 OK/NG/MISSING은 건너뛴다(req3 resume)."""
    state = load_state(path)
    out: list[str] = []
    for sid in all_ids:  # 정의 순서 유지
        if sid not in state or _has_status(state[sid], _RESUME_STATUSES):
            out.append(sid)
    return out


def shells_to_retry(path: Path) -> list[str]:
    """직전 실패 재시험 대상: NG + ERROR(req3 retry / req1b 자동 선택). 상태 파일의 셸만."""
    state = load_state(path)
    return [sid for sid, results in state.items() if _has_status(results, _RETRY_STATUSES)]


def has_checkpoint(path: Path) -> bool:
    """체크포인트 파일이 존재하는가(resume/retry는 직전 run이 있어야 의미)."""
    return Path(path).is_file()


# --- 직렬화 (core 자족) ----------------------------------------------------------


def _has_status(results: list[ComparisonResult], wanted: set[str]) -> bool:
    return any(r.status.value in wanted for r in results)


def _result_to_dict(r: ComparisonResult) -> dict:
    """ComparisonResult를 JSON 직렬화 가능한 dict로(round-trip 가능하도록 전 필드 보존)."""
    return {
        "shell_id": r.shell_id,
        "status": r.status.value,
        "output_name": r.output_name,
        "error_message": r.error_message,
        "diff_lines": [
            {"line_number": d.line_number, "asis_content": d.asis_content, "tobe_content": d.tobe_content}
            for d in r.diff_lines
        ],
    }


def _result_from_dict(d: dict) -> ComparisonResult:
    """dict를 ComparisonResult로 복원(_result_to_dict의 역연산)."""
    return ComparisonResult(
        shell_id=d["shell_id"],
        status=ComparisonStatus(d["status"]),
        diff_lines=[
            DiffLine(line_number=x["line_number"], asis_content=x["asis_content"], tobe_content=x["tobe_content"])
            for x in d.get("diff_lines", [])
        ],
        error_message=d.get("error_message"),
        output_name=d.get("output_name"),
    )
