"""Core Layer 패키지.

비교 엔진·적재·배치 호출·리포트 등 인터페이스에 무관한 비즈니스 로직.
E2E 오케스트레이션 함수(`run_full_comparison`)는 인터페이스(CLI/GUI)의 공통 진입점이다.
"""

__all__ = ["run_full_comparison", "OrchestratorError"]


# orchestrator는 src.config.definition을 import하고, 그 모듈은 다시 src.core.models를 import한다.
# 여기서 orchestrator를 즉시 import하면 core↔config 순환이 된다(core.__init__ → orchestrator →
# config.definition → core.models → core.__init__). PEP 562 지연 로딩으로 *실제 접근 시점*에만
# orchestrator를 들여와 순환을 끊는다 — `from src.core import run_full_comparison`은 그대로 동작.
def __getattr__(name: str):
    if name in __all__:
        from . import orchestrator

        return getattr(orchestrator, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
