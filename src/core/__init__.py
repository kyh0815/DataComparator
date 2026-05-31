"""Core Layer 패키지.

비교 엔진·적재·배치 호출·리포트 등 인터페이스에 무관한 비즈니스 로직.
E2E 오케스트레이션 함수(`run_full_comparison`)는 인터페이스(CLI/GUI)의 공통 진입점이다.
"""

from .orchestrator import OrchestratorError, run_full_comparison

__all__ = ["run_full_comparison", "OrchestratorError"]
