"""골격(T0-1) 스모크 테스트.

패키지가 import 가능하고 CLI 파서가 구성되는지만 확인한다.
실제 로직 테스트는 각 Task(T0-2, T1-1 ...)에서 추가된다.
"""

import importlib


def test_core_package_imports():
    """Core 패키지와 모듈들이 import 된다."""
    for name in (
        "src.core",
        "src.core.models",
        "src.core.comparator",
        "src.core.reporter",
        "src.core.loader",
        "src.core.runner",
        "src.config.settings",
    ):
        importlib.import_module(name)


def test_cli_parser_builds():
    """CLI 인자 파서가 구성되고 기본값이 설정된다."""
    from src.cli.main import build_parser

    args = build_parser().parse_args([])
    assert args.config == "./config.yaml"
    assert args.verbose is False
