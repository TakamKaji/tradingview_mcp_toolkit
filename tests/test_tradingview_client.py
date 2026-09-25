from __future__ import annotations

import asyncio
import logging
from typing import Any, Self

import httpx2
import pytest
from mcp import MCPError
from mcp.client.auth import OAuthFlowError, OAuthRegistrationError, OAuthTokenError
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool
from test_tradingview_auth import NativeKeyring

from tradingview_screening.common.errors import AppError, TransientRequestError
from tradingview_screening.integrations.tradingview import auth
from tradingview_screening.integrations.tradingview.client import (
    ENDPOINT,
    ClassifyingTransport,
    TradingViewClient,
    _normalize_error,
    _oauth_client_metadata,
)
from tradingview_screening.integrations.tradingview.tool_catalog import EXPECTED_TOOLS


def _tool(name: str) -> Tool:
    return Tool(name=name, title=f"Title {name}", description="Description", input_schema={"type": "object"})


class FakeSDK:
    def __init__(self, pages: list[ListToolsResult] | None = None) -> None:
        self.pages = pages or [ListToolsResult(tools=[_tool("run_screener")])]
        self.entered = False
        self.exited = False
        self.cursors: list[str | None] = []
        self.calls: list[tuple[str, dict[str, Any] | None]] = []
        self.result = CallToolResult(
            content=[TextContent(type="text", text="model text")],
            structured_content={"rows": [1]},
        )
        self.error: Exception | None = None
        self.protocol_version = "2025-06-18"
        self.server_info = None

    async def __aenter__(self) -> Self:
        self.entered = True
        return self

    async def __aexit__(self, *_args: object) -> None:
        self.exited = True

    async def list_tools(self, *, cursor: str | None = None) -> ListToolsResult:
        self.cursors.append(cursor)
        return self.pages[len(self.cursors) - 1]

    async def call_tool(self, name: str, arguments: dict[str, Any] | None) -> CallToolResult:
        self.calls.append((name, arguments))
        if self.error:
            raise self.error
        return self.result


class RecordingGovernor:
    def __init__(self) -> None:
        self.policies: list[tuple[bool, object]] = []

    async def execute(self, operation, *, retry: bool = True, cache_key=None):
        self.policies.append((retry, cache_key))
        return await operation()


def _storage(monkeypatch: pytest.MonkeyPatch) -> auth.KeyringTokenStorage:
    monkeypatch.setattr(auth.sys, "platform", "win32")
    return auth.KeyringTokenStorage(_keyring=NativeKeyring())


def test_exception_group_prefers_specific_oauth_error() -> None:
    from mcp.client.auth import OAuthRegistrationError

    from tradingview_screening.integrations.tradingview.client import _normalize_error

    grouped = ExceptionGroup(
        "connection failed",
        [
            RuntimeError("secondary cleanup failure"),
            OAuthRegistrationError("provider body must stay hidden"),
        ],
    )

    mapped = _normalize_error(grouped)

    assert isinstance(mapped, AppError)
    assert mapped.code == "MCP_OAUTH_REGISTRATION_ERROR"
    assert "provider body" not in mapped.message


def test_oauth_client_metadata_is_public_native_pkce_registration() -> None:
    metadata = _oauth_client_metadata("http://127.0.0.1:8765/oauth/callback")
    payload = metadata.model_dump(mode="json", exclude_none=True)
    assert payload["response_types"] == ["code"]
    assert payload["grant_types"] == ["authorization_code", "refresh_token"]
    assert payload["token_endpoint_auth_method"] == "none"
    assert payload["application_type"] == "native"


def test_expected_catalog_is_unique_and_complete() -> None:
    assert len(EXPECTED_TOOLS) == 35
    assert "run_screener" in EXPECTED_TOOLS
    assert "get_alerts_log" in EXPECTED_TOOLS


def test_client_context_catalog_pagination_and_diff(monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        storage = _storage(monkeypatch)
        await storage.set_tokens(OAuthToken(access_token="token"))
        await storage.set_client_info(OAuthClientInformationFull(client_id="id"))
        sdk = FakeSDK([
            ListToolsResult(tools=[_tool("run_screener")], next_cursor="next"),
            ListToolsResult(tools=[_tool("future_tool")]),
        ])
        governor = RecordingGovernor()
        client = TradingViewClient(
            _storage=storage, _sdk_factory=lambda _transport, **_kwargs: sdk, governor=governor
        )
        with pytest.raises(RuntimeError, match="active async context"):
            await client.list_tools()
        async with client:
            catalog = await client.list_tools()
            assert sdk.entered
            assert sdk.cursors == [None, "next"]
            assert catalog.available_count == 2
            assert catalog.unexpected_available == ("future_tool",)
            assert "get_ohlcv" in catalog.expected_missing
            assert all(not tool.implemented for tool in catalog.tools)
            assert catalog.tools[0].input_schema == {"type": "object"}
            assert governor.policies == [(True, None), (True, None)]
        assert sdk.exited
        with pytest.raises(RuntimeError, match="active async context"):
            await client.list_tools()

    asyncio.run(scenario())


def test_call_tool_governor_read_write_cache_and_results(monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        storage = _storage(monkeypatch)
        await storage.set_tokens(OAuthToken(access_token="token"))
        await storage.set_client_info(OAuthClientInformationFull(client_id="id"))
        sdk = FakeSDK()
        governor = RecordingGovernor()
        async with TradingViewClient(
            _storage=storage, _sdk_factory=lambda _transport, **_kwargs: sdk, governor=governor
        ) as client:
            result = await client._call_tool("run_screener", {"market": "america"}, cache_key="key")
            assert result.structured_content == {"rows": [1]}
            assert result.content[0]["text"] == "model text"
            assert governor.policies[-1] == (True, "key")
            await client._call_tool("run_screener", {}, retry=False, cache_key="write-key")
            assert governor.policies[-1] == (False, None)
            assert sdk.calls == [("run_screener", {"market": "america"}), ("run_screener", {})]

            with pytest.raises(AppError) as caught:
                await client._call_tool("missing")
            assert caught.value.code == "MCP_TOOL_UNAVAILABLE"
            sdk.result = CallToolResult(content=[], is_error=True)
            with pytest.raises(AppError) as caught:
                await client._call_tool("run_screener")
            assert caught.value.code == "MCP_TOOL_ERROR"

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("status", "expected"),
    [(429, "transient"), (503, "transient"), (401, "AUTH_REQUIRED"),
     (403, "MCP_PERMISSION_DENIED"), (400, "MCP_CONNECTION_ERROR")],
)
def test_http_status_classification(status: int, expected: str) -> None:
    request = httpx2.Request("POST", ENDPOINT)
    response = httpx2.Response(status, request=request)
    error = httpx2.HTTPStatusError("secret response body", request=request, response=response)
    mapped = _normalize_error(error)
    if expected == "transient":
        assert isinstance(mapped, TransientRequestError)
    else:
        assert isinstance(mapped, AppError)
        assert mapped.code == expected
    assert "secret" not in str(mapped)


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (OAuthRegistrationError("secret registration body"), "MCP_OAUTH_REGISTRATION_ERROR"),
        (OAuthTokenError("secret token body"), "MCP_OAUTH_TOKEN_ERROR"),
        (OAuthFlowError("secret discovery detail"), "MCP_OAUTH_FLOW_ERROR"),
    ],
)
def test_oauth_errors_are_stage_specific_and_sanitized(error: Exception, code: str) -> None:
    mapped = _normalize_error(error)
    assert isinstance(mapped, AppError)
    assert mapped.code == code
    assert "secret" not in mapped.message


def test_mcp_error_classification_and_status_transport() -> None:
    assert _normalize_error(MCPError(-32601, "secret tool error")).code == "MCP_TOOL_UNAVAILABLE"
    assert _normalize_error(MCPError(-32602, "secret argument")).code == "MCP_ARGUMENT_ERROR"

    async def scenario() -> None:
        for status, code in ((429, "transient"), (503, "transient"),
                             (403, "MCP_PERMISSION_DENIED"), (400, "MCP_ARGUMENT_ERROR")):
            transport = ClassifyingTransport(
                httpx2.MockTransport(lambda request, code=status: httpx2.Response(code))
            )
            request = httpx2.Request("POST", ENDPOINT, json={"jsonrpc": "2.0", "id": 1})
            response = await transport.handle_async_request(request)
            assert response.status_code == 200
            caught = MCPError(response.json()["error"]["code"], "sanitized")
            mapped = _normalize_error(caught)
            if code == "transient":
                assert isinstance(mapped, TransientRequestError)
            else:
                assert isinstance(mapped, AppError)
                assert mapped.code == code
            await transport.aclose()
        transport = ClassifyingTransport(httpx2.MockTransport(
            lambda request: httpx2.Response(
                403, headers={"www-authenticate": 'Bearer error="insufficient_scope"'}
            )
        ))
        response = await transport.handle_async_request(
            httpx2.Request("POST", ENDPOINT, json={"jsonrpc": "2.0", "id": 1})
        )
        assert response.status_code == 403
        await transport.aclose()

    asyncio.run(scenario())


def test_noninteractive_without_credentials_never_connects(monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        storage = _storage(monkeypatch)
        client = TradingViewClient(_storage=storage, _sdk_factory=lambda *_a, **_k: pytest.fail("connected"))
        with pytest.raises(AppError) as caught:
            async with client:
                pass
        assert caught.value.code == "AUTH_REQUIRED"

    asyncio.run(scenario())


def test_sdk_error_logs_are_suppressed_while_connected(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    async def scenario() -> None:
        storage = _storage(monkeypatch)
        await storage.set_tokens(OAuthToken(access_token="token"))
        await storage.set_client_info(OAuthClientInformationFull(client_id="id"))
        sdk = FakeSDK()
        async with TradingViewClient(
            _storage=storage, _sdk_factory=lambda _transport, **_kwargs: sdk
        ):
            for logger_name in ("mcp.client.auth.oauth2", "mcp.client.streamable_http", "client"):
                logging.getLogger(logger_name).error("secret-token-state")
            assert "secret-token-state" not in caplog.text
        logging.getLogger("mcp.client.auth.oauth2").error("filter removed")
        assert "filter removed" in caplog.text

    asyncio.run(scenario())
