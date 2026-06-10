"""백그라운드 검증 실행 관리(인터페이스 계층) — 코어 무수정.

코어 `run_full_comparison`을 **백그라운드 데몬 스레드**로 감싸 진행 상태를 서버(RunState)에
보존한다. 브라우저가 끊겨도 워커는 끝까지 돌고, `/run/status`로 진행/결과를 되읽을 수 있다
("실행 버튼 누르고 자리를 떠도 와서 보면 끝나있다").

설계 포인트:
- **동시 실행 1건**: `_run_lock`(전역). **락은 워커 생명주기 전체 동안 보유**하고 워커 finally에서만
  해제한다 — 클라 연결(SSE generator)에 종속되지 않는다(과거 버그: generator finally가 조기 해제해
  실행 중인데 2차 실행이 붙을 수 있었음).
- **락 소스 단일화**: 구 `/run`(SSE)·신 `/run/start`(폴링)가 **같은 `_run_lock`·RunState**를 공유한다.
- **예외 안전**: 워커가 예외로 죽어도 `end()`(finally)에서 반드시 락 해제 + 상태는 `failed`로 보존.
- 진행 카운트·current는 코어 `on_progress`(ProgressEvent)로 갱신. **코어는 손대지 않는다.**

단일 프로세스(`app.run(threaded=True)`) 전제 — 모듈 전역 `run_manager` 1개가 상태 단일 소스다.
"""

from __future__ import annotations

import threading
import time

from .serialize import summary_to_dict

# RunState.counts 키 = ComparisonStatus 값(models.py)과 정확히 일치해야 한다.
_COUNT_KEYS = ("OK", "NG", "MISSING_ASIS", "MISSING_TOBE", "ERROR")


def _idle_state() -> dict:
    """실행 전/초기화 상태."""
    return {
        "state": "idle",            # idle | running | done | failed
        "config": None,
        "shells": None,
        "resume": False,
        "run_id": None,
        "started_at": None,         # epoch 초(조건3) — "이 결과가 언제 것인가"
        "finished_at": None,        # epoch 초(조건3)
        "total": 0,                 # 전체 셸 수(첫 ProgressEvent.total에서 확정)
        "current_shell": None,
        "current_index": 0,
        "counts": {k: 0 for k in _COUNT_KEYS},
        "summary": None,            # done에서 summary_to_dict
        "error": None,              # failed에서 예외 메시지
    }


class RunManager:
    """전역 단일 실행 락 + RunState 보유. 실제 실행(run_full_comparison) 호출은 web.py가 한다.

    web.py가 try_begin()으로 시작 권한(락)을 얻고, 워커 스레드에서 apply_progress()/finish_*()로
    상태를 갱신한 뒤 finally에서 end()로 락을 해제한다. snapshot()이 `/run/status` 응답이다.
    """

    def __init__(self) -> None:
        self._run_lock = threading.Lock()   # 동시 실행 1건(워커 생명주기 동안 보유)
        self._slock = threading.RLock()      # RunState 보호(워커 스레드 ↔ 요청 스레드)
        self._st = _idle_state()

    # ── 생명주기 ───────────────────────────────────────────────────────────────
    def try_begin(self, config_path: str, shells: str | None = None, resume: bool = False) -> bool:
        """실행 권한(락)을 비차단으로 획득하고 RunState를 running으로 초기화한다.

        이미 실행 중이면 False(락 미획득). 락은 end()에서만 해제 — 호출자(워커)가 finally로 보장.
        """
        if not self._run_lock.acquire(blocking=False):
            return False
        with self._slock:
            self._st = _idle_state()
            self._st.update({
                "state": "running",
                "config": config_path,
                "shells": shells,
                "resume": bool(resume),
                "run_id": time.strftime("%Y%m%d_%H%M%S"),
                "started_at": time.time(),
            })
        return True

    def end(self) -> None:
        """워커 종료 시 호출(반드시 finally). 락을 해제한다. 중복/미보유 호출은 무시(예외 안전)."""
        try:
            self._run_lock.release()
        except RuntimeError:
            pass  # 이미 해제됨 — 안전하게 무시

    def apply_progress(self, event) -> None:  # event: core.models.ProgressEvent
        """코어 on_progress 콜백 — current/total 갱신, SHELL_DONE이면 결과 status로 카운트."""
        with self._slock:
            st = self._st
            if st["state"] != "running":
                return
            if getattr(event, "total", 0):
                st["total"] = event.total
            st["current_shell"] = event.shell_id
            st["current_index"] = event.index
            res = getattr(event, "result", None)  # SHELL_DONE에만 존재
            if res is not None and res.status is not None:
                key = res.status.value if hasattr(res.status, "value") else str(res.status)
                if key in st["counts"]:
                    st["counts"][key] += 1

    def finish_done(self, summary, elapsed_seconds: float | None = None) -> None:
        """정상 종료 — summary 보존(락 해제는 별도 end()에서)."""
        with self._slock:
            self._st["state"] = "done"
            self._st["finished_at"] = time.time()
            self._st["summary"] = summary_to_dict(summary, elapsed_seconds or self._elapsed())

    def finish_failed(self, message: str) -> None:
        """비정상 종료 — 예외 메시지 보존(조건2). 락 해제는 end()."""
        with self._slock:
            self._st["state"] = "failed"
            self._st["finished_at"] = time.time()
            self._st["error"] = message

    def reset(self) -> None:
        """idle로 강제 초기화(락 해제 포함). 테스트/복구용."""
        self.end()
        with self._slock:
            self._st = _idle_state()

    # ── 조회 ──────────────────────────────────────────────────────────────────
    def snapshot(self) -> dict:
        """`/run/status` 응답 — 연결과 무관하게 서버 RunState를 그대로 반영(폴링/재접속 복원용)."""
        with self._slock:
            st = self._st
            done = sum(st["counts"].values())
            return {
                "state": st["state"],
                "run_id": st["run_id"],
                "config": st["config"],
                "resume": st["resume"],
                "started_at": st["started_at"],
                "finished_at": st["finished_at"],
                "elapsed": round(self._elapsed(), 1),
                "total": st["total"],
                "done": done,
                "current_shell": st["current_shell"],
                "current_index": st["current_index"],
                "counts": dict(st["counts"]),
                "summary": st["summary"],
                "error": st["error"],
            }

    def _elapsed(self) -> float:
        s = self._st["started_at"]
        if not s:
            return 0.0
        return (self._st["finished_at"] or time.time()) - s


# 모듈 전역 단일 인스턴스(단일 프로세스 가정). 상태 단일 소스.
run_manager = RunManager()
