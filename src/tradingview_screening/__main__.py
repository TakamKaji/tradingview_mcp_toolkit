from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from . import __version__
from .common.errors import AppError, ConfigError, TransientRequestError
from .integrations.tradingview.auth import KeyringTokenStorage
from .integrations.tradingview.client import ENDPOINT, TradingViewClient
from .integrations.tradingview.oauth_bootstrap import bootstrap_oauth
from .integrations.tradingview.tool_catalog import EXPECTED_TOOLS
from .screening.engine import run_screening
from .screening.results import TOKYO, latest_result, save_result
from .screening.schema import ScreeningDefinition
from .screening.validators import load_screening_by_name


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
    screen = commands.add_parser("screen")
    screen.add_argument("screening_name")
    results = commands.add_parser("results")
    result_operations = results.add_subparsers(dest="results_command", required=True, parser_class=Parser)
    latest = result_operations.add_parser("latest")
    latest.add_argument("screening_name", nargs="?")
    return parser


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True, separators=(",", ":")))


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


def _failed_screening(
    name: str | None, error: AppError, *, requested_count: int | None, duration_ms: int,
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "status": "failed",
        "operation": "screening",
        "name": name,
        "executedAt": datetime.now(TOKYO).isoformat(),
        "source": "tradingview_official_mcp",
        "metadata": {
            "requestedCount": requested_count, "returnedCount": 0,
            "partial": False, "durationMs": duration_ms,
        },
        "results": [],
        "errors": [{"code": error.code, "message": error.message}],
    }


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


async def _execute_screen(
    screening: ScreeningDefinition, project_root: Path, *, started: float,
) -> dict[str, Any]:
    async with TradingViewClient() as client:
        result = await run_screening(screening, client, started=started)
    save_result(result, project_root)
    return result


def main(argv: list[str] | None = None) -> int:
    try:
        parsed = build_parser().parse_args(argv)
    except CliUsageError:
        error = AppError("CLI_USAGE_ERROR", "Invalid command or arguments")
        _emit(_failed("cli", error))
        print(error.message, file=sys.stderr)
        return 2
    if parsed.command in {"screen", "results"}:
        name = parsed.screening_name
        project_root = Path.cwd()
        started = time.monotonic()
        requested_count: int | None = None
        try:
            if parsed.command == "screen":
                screening = load_screening_by_name(name, project_root)
                if screening.name != name:
                    raise ConfigError(
                        "CONFIG_VALIDATION_ERROR", "Screening name does not match filename", "name"
                    )
                requested_count = screening.limit
                payload = asyncio.run(_execute_screen(screening, project_root, started=started))
            else:
                payload = latest_result(project_root, name)
            _emit(payload)
            return 0
        except ConfigError as exc:
            error = AppError(exc.code, exc.message)
            code = 2
        except ValidationError:
            error = AppError("CONFIG_VALIDATION_ERROR", "Invalid local configuration")
            code = 2
        except AppError as exc:
            error = exc
            code = 3 if exc.code == "AUTH_REQUIRED" else 1
        except TransientRequestError:
            error = AppError("MCP_CONNECTION_ERROR", "MCP connection failed")
            code = 1
        except Exception:  # noqa: BLE001 - CLI boundary must emit one secret-free JSON error.
            error = AppError("MCP_CONNECTION_ERROR", "Screening execution failed")
            code = 1
        _emit(
            _failed_screening(
                name, error, requested_count=requested_count,
                duration_ms=round((time.monotonic() - started) * 1000),
            ) if parsed.command == "screen" else _failed("results_latest", error)
        )
        print(f"{error.code}: {error.message}", file=sys.stderr)
        return code
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
