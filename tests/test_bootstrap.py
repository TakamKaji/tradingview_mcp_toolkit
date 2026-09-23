from tradingview_screening import __version__
from tradingview_screening.__main__ import build_parser


def test_package_version_is_defined() -> None:
    assert __version__ == "0.0.0"


def test_cli_parser_can_be_built() -> None:
    parser = build_parser()
    assert parser.prog == "tradingview_screening"
