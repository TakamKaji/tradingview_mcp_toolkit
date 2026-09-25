from __future__ import annotations

import json
from typing import Self

import pytest

from tradingview_screening import __main__ as cli
from tradingview_screening.common.errors import AppError
from tradingview_screening.integrations.tradingview.client import ToolCatalog, ToolInfo


class FakeClient:
    mode: bool | None = None
    failure: AppError | None = None

    def __init__(self, *, interactive: bool = False) -> None:
        self.interactive = interactive

    async def __aenter__(self) -> Self:
        FakeClient.mode = self.interactive
        if FakeClient.failure:
            raise FakeClient.failure
        return self

    async def __aexit__(self, *_args: object) -> None:
        pass

    async def list_tools(self) -> ToolCatalog:
        return ToolCatalog(
            tools=(ToolInfo("run_screener", "Run", "Description", {"type": "object"}, True),),
            expected_missing=("get_ohlcv",),
            unexpected_available=(),
        )

    @property
    def protocol_version(self) -> str:
        return "2025-06-18"

    @property
    def server_info(self) -> dict[str, str]:
        return {"name": "TradingView", "version": "1"}


@pytest.mark.parametrize(
    ("command", "operation", "interactive"),
    [("auth", "mcp_auth", True), ("status", "mcp_status", False), ("tools", "mcp_tools", False)],
)
def test_cli_success_json_once(
    command: str, operation: str, interactive: bool,
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    FakeClient.failure = None
    monkeypatch.setattr(cli, "TradingViewClient", FakeClient)
    assert cli.main(["mcp", command]) == 0
    captured = capsys.readouterr()
    assert len(captured.out.splitlines()) == 1
    payload = json.loads(captured.out)
    assert payload["status"] == "success"
    assert payload["operation"] == operation
    assert captured.err == ""
    assert FakeClient.mode is interactive
    if command == "status":
        assert payload["protocolVersion"] == "2025-06-18"
        assert payload["serverInfo"]["name"] == "TradingView"
    if command == "tools":
        assert payload["availableCount"] == 1
        assert payload["expectedCount"] == 35
        assert payload["tools"][0]["implemented"] is False


@pytest.mark.parametrize("present", [True, False, None])
def test_cli_status_auth_required_credential_presence(
    present: bool | None, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    FakeClient.failure = AppError("AUTH_REQUIRED", "TradingView authorization is required")
    monkeypatch.setattr(cli, "TradingViewClient", FakeClient)

    async def check() -> bool | None:
        return present

    monkeypatch.setattr(cli, "_credential_present", check)
    assert cli.main(["mcp", "status"]) == 3
    captured = capsys.readouterr()
    assert len(captured.out.splitlines()) == 1
    payload = json.loads(captured.out)
    assert payload["error"]["code"] == "AUTH_REQUIRED"
    assert payload["credentialPresent"] is present
    FakeClient.failure = None


def test_cli_failure_and_usage_are_sanitized(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    FakeClient.failure = AppError("MCP_CONNECTION_ERROR", "MCP connection failed")
    monkeypatch.setattr(cli, "TradingViewClient", FakeClient)
    assert cli.main(["mcp", "tools"]) == 1
    result = capsys.readouterr()
    assert json.loads(result.out)["error"]["code"] == "MCP_CONNECTION_ERROR"
    assert cli.main(["mcp", "unknown"]) == 2
    result = capsys.readouterr()
    assert len(result.out.splitlines()) == 1
    assert json.loads(result.out)["error"]["code"] == "CLI_USAGE_ERROR"
    FakeClient.failure = None
