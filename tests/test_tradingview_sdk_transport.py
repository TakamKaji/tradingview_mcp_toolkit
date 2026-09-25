"""Exercise the installed MCP Client and Streamable HTTP with fake HTTP only."""

from __future__ import annotations

import asyncio
import json

import httpx2
import pytest
from mcp import Client
from mcp.shared.auth import OAuthClientInformationFull, OAuthMetadata, OAuthToken
from test_tradingview_auth import NativeKeyring

from tradingview_screening.common.errors import AppError, TransientRequestError
from tradingview_screening.common.request_governor import RequestGovernor, RequestGovernorConfig
from tradingview_screening.integrations.tradingview import auth
from tradingview_screening.integrations.tradingview.client import TradingViewClient


@pytest.mark.parametrize(
    ("tool_status", "retry"),
    [(429, True), (503, True), (403, True), (501, True), ("timeout", True), (429, False)],
)
def test_real_sdk_streamable_http_status_classification_and_governor_retry(
    tool_status: int | str, retry: bool, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth.sys, "platform", "win32")
    counts: dict[str, int] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.method == "GET":
            return httpx2.Response(405)
        if request.method == "DELETE":
            return httpx2.Response(204)
        body = json.loads(request.content)
        method = body.get("method", "notification")
        counts[method] = counts.get(method, 0) + 1
        if "id" not in body:
            return httpx2.Response(202)
        if method == "initialize":
            result = {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fake-tradingview", "version": "1"},
            }
        elif method == "tools/list":
            result = {"tools": [{"name": "run_screener", "inputSchema": {"type": "object"}}]}
        elif method == "tools/call":
            if tool_status == "timeout" and counts[method] == 1:
                raise httpx2.ReadTimeout("fake timeout", request=request)
            if tool_status == 403 or counts[method] == 1:
                return httpx2.Response(tool_status)
            result = {"content": [], "structuredContent": {"ok": True}}
        else:
            raise AssertionError(f"unexpected method {method}")
        return httpx2.Response(
            200,
            headers={"content-type": "application/json"},
            json={"jsonrpc": "2.0", "id": body["id"], "result": result},
        )

    async def scenario() -> None:
        storage = auth.KeyringTokenStorage(_keyring=NativeKeyring())
        await storage.set_tokens(OAuthToken(access_token="token"))
        await storage.set_client_info(OAuthClientInformationFull(client_id="client"))
        governor = RequestGovernor(RequestGovernorConfig(
            requests_per_minute=100, retry_base_delay_seconds=0, timeout_seconds=1,
        ))
        async with TradingViewClient(
            _storage=storage,
            _http_transport=httpx2.MockTransport(handler),
            _sdk_factory=lambda transport, **kwargs: Client(transport, mode="legacy", **kwargs),
            governor=governor,
        ) as client:
            catalog = await client.list_tools()
            assert catalog.available_count == 1
            if tool_status in (403, 501):
                with pytest.raises(AppError) as caught:
                    await client._call_tool("run_screener", {}, retry=retry)
                assert caught.value.code == (
                    "MCP_PERMISSION_DENIED" if tool_status == 403 else "MCP_CONNECTION_ERROR"
                )
                assert counts["tools/call"] == 1
            elif not retry:
                with pytest.raises(TransientRequestError):
                    await client._call_tool("run_screener", {}, retry=False)
                assert counts["tools/call"] == 1
            else:
                result = await client._call_tool("run_screener", {})
                assert result.structured_content == {"ok": True}
                assert counts["tools/call"] == 2

    asyncio.run(scenario())


def test_sdk_refresh_credential_save_failure_keeps_error_class(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth.sys, "platform", "win32")

    def handler(request: httpx2.Request) -> httpx2.Response:
        if str(request.url) == "https://www.tradingview.com/mcp/oauth/token":
            return httpx2.Response(200, json={"access_token": "fresh", "token_type": "Bearer"})
        raise AssertionError(f"unexpected request {request.url}")

    async def scenario() -> None:
        storage = auth.KeyringTokenStorage(_keyring=NativeKeyring())
        await storage.set_tokens(OAuthToken(access_token="old", refresh_token="refresh", expires_in=0))
        await storage.set_client_info(OAuthClientInformationFull(client_id="client"))
        await storage.set_oauth_metadata(OAuthMetadata(
            issuer="https://www.tradingview.com",
            authorization_endpoint="https://www.tradingview.com/mcp/oauth/authorize",
            token_endpoint="https://www.tradingview.com/mcp/oauth/token",
        ))

        async def fail_save(_tokens: OAuthToken) -> None:
            raise AppError("CREDENTIAL_STORE_ERROR", "Credential Store is unavailable")

        storage.set_tokens = fail_save
        client = TradingViewClient(
            _storage=storage,
            _http_transport=httpx2.MockTransport(handler),
            _sdk_factory=lambda transport, **kwargs: Client(transport, mode="legacy", **kwargs),
            governor=RequestGovernor(RequestGovernorConfig(timeout_seconds=1)),
        )
        with pytest.raises(AppError) as caught:
            async with client:
                pass
        assert caught.value.code == "CREDENTIAL_STORE_ERROR"

    asyncio.run(scenario())


@pytest.mark.parametrize("modern", [True, False])
def test_default_sdk_auto_mode_modern_and_legacy_fallback(
    modern: bool, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth.sys, "platform", "win32")
    methods: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert str(request.url) == "https://mcp.tradingview.com/mcp"
        if request.method == "GET":
            return httpx2.Response(405)
        if request.method == "DELETE":
            return httpx2.Response(204)
        body = json.loads(request.content)
        method = body.get("method", "notification")
        methods.append(method)
        if "id" not in body:
            return httpx2.Response(202)
        if method == "server/discover":
            if modern:
                result = {"supportedVersions": ["2026-07-28"], "capabilities": {"tools": {}}}
            else:
                return httpx2.Response(200, headers={"content-type": "application/json"}, json={
                    "jsonrpc": "2.0", "id": body["id"],
                    "error": {"code": -32601, "message": "Method not found"},
                })
        elif method == "initialize":
            result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                      "serverInfo": {"name": "fake", "version": "1"}}
        elif method == "tools/list":
            result = {"tools": [{"name": "run_screener", "inputSchema": {"type": "object"}}]}
            if modern:
                result.update({"cacheScope": "private", "resultType": "complete", "ttlMs": 0})
        else:
            raise AssertionError(method)
        return httpx2.Response(200, headers={"content-type": "application/json"}, json={
            "jsonrpc": "2.0", "id": body["id"], "result": result,
        })

    async def scenario() -> None:
        storage = auth.KeyringTokenStorage(_keyring=NativeKeyring())
        await storage.set_tokens(OAuthToken(access_token="token"))
        await storage.set_client_info(OAuthClientInformationFull(client_id="client"))
        async with TradingViewClient(
            _storage=storage, _http_transport=httpx2.MockTransport(handler),
        ) as client:
            assert (await client.list_tools()).available_count == 1
        assert methods[0] == "server/discover"
        assert ("initialize" in methods) is not modern

    asyncio.run(scenario())


def test_real_sdk_401_noninteractive_becomes_auth_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth.sys, "platform", "win32")
    monkeypatch.setattr(auth.webbrowser, "open", lambda _url: pytest.fail("browser opened"))
    methods: list[str] = []
    urls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        urls.append(str(request.url))
        if request.method == "GET":
            return httpx2.Response(404)
        if request.method == "DELETE":
            return httpx2.Response(204)
        body = json.loads(request.content)
        method = body.get("method", "notification")
        methods.append(method)
        if "id" not in body:
            return httpx2.Response(202)
        if method == "initialize":
            return httpx2.Response(200, headers={"content-type": "application/json"}, json={
                "jsonrpc": "2.0", "id": body["id"], "result": {
                    "protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                    "serverInfo": {"name": "fake", "version": "1"},
                },
            })
        if method == "tools/list":
            return httpx2.Response(401, headers={"www-authenticate": "Bearer"})
        raise AssertionError(method)

    async def scenario() -> None:
        storage = auth.KeyringTokenStorage(_keyring=NativeKeyring())
        await storage.set_tokens(OAuthToken(access_token="revoked", refresh_token=None))
        await storage.set_client_info(OAuthClientInformationFull(client_id="client"))
        governor = RequestGovernor(RequestGovernorConfig(timeout_seconds=1))
        async with TradingViewClient(
            _storage=storage,
            _http_transport=httpx2.MockTransport(handler),
            _sdk_factory=lambda transport, **kwargs: Client(transport, mode="legacy", **kwargs),
            governor=governor,
        ) as client:
            with pytest.raises(AppError) as caught:
                await client.list_tools()
            assert caught.value.code == "AUTH_REQUIRED"
            assert methods.count("tools/list") == 1
            assert set(urls) == {"https://mcp.tradingview.com/mcp"}

    asyncio.run(scenario())
