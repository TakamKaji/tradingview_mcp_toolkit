from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from . import __version__
from .common.errors import AppError, ConfigError, TransientRequestError
from .integrations.tradingview.auth import KeyringTokenStorage
from .integrations.tradingview.client import ENDPOINT, TradingViewClient
from .integrations.tradingview.oauth_bootstrap import bootstrap_oauth
from .integrations.tradingview.tool_catalog import EXPECTED_TOOLS


class CliUsageError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CliUsageError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(prog="tradingview_screening", description="TradingView official MCP support CLI")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
    mcp = commands.add_parser("mcp")
    operations = mcp.add_subparsers(dest="mcp_command", required=True, parser_class=Parser)
    for command in ("auth", "status", "tools"):
        operations.add_parser(command)
    return parser


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def _failed(
    operation: str, error: AppError, *, credential_present: bool | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schemaVersion": 1,
        "status": "failed",
        "operation": operation,
        "error": {"code": error.code, "message": error.message},
    }
    if operation == "mcp_status":
        payload.update({
            "endpoint": ENDPOINT,
            "credentialPresent": credential_present,
            "authenticated": False,
            "toolDiscoveryAvailable": False,
        })
    return payload


async def _execute(command: str) -> dict[str, Any]:
    if command == "auth":
        await bootstrap_oauth()
        return {
            "schemaVersion": 1,
            "status": "success",
            "operation": "mcp_auth",
            "authenticated": True,
        }
    async with TradingViewClient() as client:
        catalog = await client.list_tools()
        if command == "status":
            return {
                "schemaVersion": 1,
                "status": "success",
                "operation": "mcp_status",
                "endpoint": ENDPOINT,
                "credentialPresent": True,
                "authenticated": True,
                "toolDiscoveryAvailable": True,
                "protocolVersion": client.protocol_version,
                "serverInfo": client.server_info,
            }
        return {
            "schemaVersion": 1,
            "status": "success",
            "operation": "mcp_tools",
            "provider": "tradingview",
            "retrievedAt": datetime.now(UTC).isoformat(),
            "availableCount": catalog.available_count,
            "expectedCount": len(EXPECTED_TOOLS),
            "expectedMissing": list(catalog.expected_missing),
            "unexpectedAvailable": list(catalog.unexpected_available),
            "tools": [tool.to_dict() for tool in catalog.tools],
        }


async def _credential_present() -> bool | None:
    try:
        return await KeyringTokenStorage().get_tokens() is not None
    except AppError:
        return None


def main(argv: list[str] | None = None) -> int:
    try:
        parsed = build_parser().parse_args(argv)
    except CliUsageError:
        error = AppError("CLI_USAGE_ERROR", "Invalid command or arguments")
        _emit(_failed("cli", error))
        print(error.message, file=sys.stderr)
        return 2
    command = parsed.mcp_command
    operation = f"mcp_{command}"
    try:
        _emit(asyncio.run(_execute(command)))
        return 0
    except AppError as error:
        present = asyncio.run(_credential_present()) if command == "status" else None
        _emit(_failed(operation, error, credential_present=present))
        print(f"{error.code}: {error.message}", file=sys.stderr)
        return 3 if error.code == "AUTH_REQUIRED" else 1
    except TransientRequestError as transient:
        error = AppError("MCP_CONNECTION_ERROR", str(transient))
        _emit(_failed(operation, error))
        print(f"{error.code}: {error.message}", file=sys.stderr)
        return 1
    except (ConfigError, ValidationError):
        error = AppError("CONFIG_VALIDATION_ERROR", "Invalid local configuration")
        _emit(_failed(operation, error))
        print(f"{error.code}: {error.message}", file=sys.stderr)
        return 2
    except Exception:  # noqa: BLE001 - CLI boundary must emit one secret-free JSON error.
        error = AppError("MCP_CONNECTION_ERROR", "MCP connection failed")
        _emit(_failed(operation, error))
        print(f"{error.code}: {error.message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
