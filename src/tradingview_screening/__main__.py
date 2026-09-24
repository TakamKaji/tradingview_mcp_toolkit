from __future__ import annotations

import argparse

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tradingview_screening",
        description="TradingView official MCP support CLI (bootstrap)",
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main() -> int:
    build_parser().parse_args()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
