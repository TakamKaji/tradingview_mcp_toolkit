from __future__ import annotations

import json
from typing import Self

import httpx2
import pytest
from test_oauth_bootstrap import ASM, PRM, REGISTER, TOKEN, FakeCallback
from test_tradingview_auth import NativeKeyring

from tradingview_screening import __main__ as cli
from tradingview_screening.common.errors import AppError, TransientRequestError
from tradingview_screening.integrations.tradingview import auth
from tradingview_screening.integrations.tradingview.client import ToolCatalog, ToolInfo
from tradingview_screening.integrations.tradingview.oauth_bootstrap import (
    bootstrap_oauth as real_bootstrap,
)


class FakeClient:
    entered = False
    failure: AppError | None = None

    def __init__(self) -> None:
        pass

    async def __aenter__(self) -> Self:
        FakeClient.entered = True
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
    ("command", "operation"),
    [("auth", "mcp_auth"), ("status", "mcp_status"), ("tools", "mcp_tools")],
)
def test_cli_success_json_once(
    command: str, operation: str,
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    FakeClient.failure = None
    FakeClient.entered = False
    monkeypatch.setattr(cli, "TradingViewClient", FakeClient)

    async def fake_bootstrap() -> None:
        pass

    monkeypatch.setattr(cli, "bootstrap_oauth", fake_bootstrap)
    assert cli.main(["mcp", command]) == 0
    captured = capsys.readouterr()
    assert len(captured.out.splitlines()) == 1
    payload = json.loads(captured.out)
    assert payload["status"] == "success"
    assert payload["operation"] == operation
    assert captured.err == ""
    assert FakeClient.entered is (command != "auth")
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


def test_cli_transient_transport_failure_is_not_hidden(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def failed_bootstrap() -> None:
        raise TransientRequestError("Temporary MCP transport failure")

    monkeypatch.setattr(cli, "bootstrap_oauth", failed_bootstrap)
    assert cli.main(["mcp", "auth"]) == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["error"] == {
        "code": "MCP_CONNECTION_ERROR",
        "message": "Temporary MCP transport failure",
    }
    assert "Temporary MCP transport failure" in captured.err


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


def test_cli_auth_real_sdk_finishes_without_mcp_session(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(auth.sys, "platform", "win32")
    storage = auth.KeyringTokenStorage(_keyring=NativeKeyring())
    callback = FakeCallback()
    urls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        url = str(request.url)
        urls.append(url)
        if url == cli.ENDPOINT:
            assert request.method == "GET"
            return httpx2.Response(401, headers={"www-authenticate": f'Bearer resource_metadata="{PRM}"'})
        if url == PRM:
            return httpx2.Response(200, json={"resource": cli.ENDPOINT, "authorization_servers": ["https://www.tradingview.com"]})
        if url == ASM:
            return httpx2.Response(200, json={
                "issuer": "https://www.tradingview.com", "authorization_endpoint": "https://www.tradingview.com/mcp/oauth/authorize",
                "token_endpoint": TOKEN, "registration_endpoint": REGISTER,
                "code_challenge_methods_supported": ["S256"], "token_endpoint_auth_methods_supported": ["none"],
            })
        if url == REGISTER:
            data = json.loads(request.content)
            data["client_id"] = "issued-client"
            return httpx2.Response(201, json=data)
        if url == TOKEN:
            return httpx2.Response(200, json={"access_token": "secret", "token_type": "Bearer"})
        raise AssertionError(url)

    async def sdk_bootstrap() -> None:
        await real_bootstrap(
            _storage=storage, _callback=callback, _http_transport=httpx2.MockTransport(handler),
        )

    monkeypatch.setattr(cli, "bootstrap_oauth", sdk_bootstrap)
    monkeypatch.setattr(cli, "TradingViewClient", lambda: pytest.fail("MCP session created during auth"))
    assert cli.main(["mcp", "auth"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"schemaVersion": 1, "status": "success", "operation": "mcp_auth", "authenticated": True}
    assert callback.url is not None
    assert urls.count(cli.ENDPOINT) == 2
    assert ("secret" not in str(payload))
