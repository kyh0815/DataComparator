"""CLI 진입점 (Interface Layer) — T3-3.

사용 예:
    python -m src.cli.main --config ./config.yaml
    python -m src.cli.main --config ./config.yaml --shells 1-10 --verbose

인자를 파싱해 설정을 로드하고, CliReporter를 진행 콜백으로 배선해 Core의
run_full_comparison을 호출한 뒤 최종 요약을 출력한다(Core/Interface 분리, ARCHITECTURE 5).

설계 결정은 DECISIONS.md D-026 참조:
- 종료 코드: 0=전부 OK / 1=NG·ERROR·MISSING 하나라도(not all OK) / 2=fatal 설정·접속 오류(SPEC 8).
- --shells는 settings.parse_shell_selector로 파싱해 run_full_comparison(shell_ids=)로 명시 전달(D-024).
- --verbose는 앱 네임스페이스 로거(src)만 DEBUG로 한정(서드파티 소음 차단) + 모든 diff 줄 표시.
- 소요 시간은 여기서 측정(실행을 소유하는 쪽이 타이밍도 소유, D-025 §6).
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from src.cli.output import CliReporter, should_use_color
from src.config.definition import DefinitionError
from src.config.settings import ConfigError, load_config, parse_shell_selector
from src.core import OrchestratorError, run_full_comparison


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서를 구성한다 (SPEC 1장)."""
    parser = argparse.ArgumentParser(
        prog="python -m src.cli.main",
        description="현·신 비교 자동화 도구 — 배치 출력 동등성 검증",
    )
    parser.add_argument(
        "--config",
        default="./config.yaml",
        help="설정 파일 경로 (기본: ./config.yaml)",
    )
    parser.add_argument(
        "--shells",
        default=None,
        help="실행할 셸 범위 또는 ID (예: 1-10 또는 001,002,005). 미지정 시 정의 파일 전체",
    )
    parser.add_argument(
        "--report-dir",
        default=None,
        help="리포트 출력 디렉토리 (미지정 시 config 값)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="상세 출력 (모든 diff 줄 + 앱 로그)",
    )
    return parser


def _enable_verbose_logging() -> None:
    """앱 네임스페이스(src) 로거만 DEBUG로 켠다 — 서드파티 로그 소음을 차단한다(D-026)."""
    logger = logging.getLogger("src")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.StreamHandler()  # stderr
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점. 종료 코드를 반환한다(0=전부 OK / 1=불일치 있음 / 2=fatal)."""
    args = build_parser().parse_args(argv)

    try:
        config = load_config(args.config)
        if args.report_dir:
            config.report_dir = Path(args.report_dir).resolve()  # cwd 기준 override
        shell_ids = parse_shell_selector(args.shells) if args.shells else None

        if args.verbose:
            _enable_verbose_logging()

        reporter = CliReporter(
            use_color=should_use_color(config.output.cli_color, sys.stdout),
            verbose=args.verbose,
        )
        start = time.perf_counter()
        summary = run_full_comparison(
            config, on_progress=reporter.on_progress, shell_ids=shell_ids
        )
        reporter.print_summary(summary, time.perf_counter() - start)
    except (ConfigError, DefinitionError, OrchestratorError) as exc:
        # SPEC 8: 설정 파일 오류·DB 접속 실패 등은 즉시 종료 + 에러 메시지(정상 요약과 분리).
        print(f"오류: {exc}", file=sys.stderr)
        return 2

    # 전부 OK일 때만 0. NG·ERROR·MISSING 중 하나라도 있으면 1(D-026, D-025 종료코드 supersede).
    return 0 if summary.ok_count == summary.total else 1


if __name__ == "__main__":
    sys.exit(main())
