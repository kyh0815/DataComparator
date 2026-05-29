"""CLI 진입점.

사용 예:
    python -m src.cli.main --config ./config.yaml

인자를 파싱하고 Core의 `run_full_comparison`을 호출한다.
(T0-1 골격 단계에서는 파서만 동작하며, 실제 오케스트레이션 호출은 T3-3에서 연결한다.)
"""

from __future__ import annotations

import argparse
import sys


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
        help="실행할 셸 범위 또는 ID (예: 1-10 또는 001,002,005). 미지정 시 config 값 사용",
    )
    parser.add_argument(
        "--report-dir",
        default=None,
        help="리포트 출력 디렉토리 (미지정 시 config 값 사용)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="상세 로그 출력",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점. 종료 코드를 반환한다."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # TODO (T3-3): config 로드 → core.run_full_comparison(config, on_progress=cb) 호출.
    #              NG/ERROR가 있으면 1, 모두 OK면 0을 반환.
    print("아직 구현되지 않았습니다. (T3-3에서 오케스트레이션 연결 예정)")
    print(f"  config     = {args.config}")
    print(f"  shells     = {args.shells}")
    print(f"  report-dir = {args.report_dir}")
    print(f"  verbose    = {args.verbose}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
