from __future__ import annotations

import asyncio
import json
from urllib.parse import parse_qs, urlsplit

import httpx2
import pytest
from mcp.client.auth import AuthorizationCodeResult
from mcp.shared.auth import OAuthToken
from test_tradingview_auth import NativeKeyring

from tradingview_screening.common.errors import AppError
from tradingview_screening.integrations.tradingview import auth
from tradingview_screening.integrations.tradingview.client import ENDPOINT, TradingViewClient
from tradingview_screening.integrations.tradingview.oauth_bootstrap import bootstrap_oauth

PRM = "https://mcp.tradingview.com/.well-known/oauth-protected-resource/mcp"
ASM = "https://www.tradingview.com/.well-known/oauth-authorization-server"
REGISTER = "https://www.tradingview.com/mcp/oauth/register"
TOKEN = "https://www.tradingview.com/mcp/oauth/token"


class FakeCallback:
    redirect_uri = "http://127.0.0.1:8765/oauth/callback"

    def __init__(self, *, wrong_state: bool = False, wrong_issuer: bool = False) -> None:
        self.url: str | None = None
        self.wrong_state = wrong_state
        self.wrong_issuer = wrong_issuer

    async def redirect(self, url: str) -> None:
        self.url = url

    async def callback(self) -> AuthorizationCodeResult:
        assert self.url is not None
        query = parse_qs(urlsplit(self.url).query)
        return AuthorizationCodeResult(
            code="code-secret",
            state="wrong" if self.wrong_state else query["state"][0],
            iss="https://other.example" if self.wrong_issuer else "https://www.tradingview.com",
        )


@pytest.mark.parametrize(
    ("advertise_cimd", "cimd_url", "registration", "client_id", "expected_strategy"),
    [
        (False, None, True, None, "dcr"),
        (True, "https://example.org/tradingview-client.json", True, None, "cimd"),
        (True, None, True, None, "dcr"),
        (False, None, True, "my-issued-client", "pre_registered"),
    ],
)
def test_sdk_bootstrap_to_saved_token_without_mcp_session(
    advertise_cimd: bool, cimd_url: str | None, registration: bool,
    client_id: str | None, expected_strategy: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth.sys, "platform", "win32")
    seen: list[tuple[str, str]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        url = str(request.url)
        seen.append((request.method, url))
        assert request.headers.get("authorization") != "Bearer old-token"
        assert request.headers.get("user-agent") == "TradingView-MCP-Support/0.0.0" or url == ENDPOINT
        if url == ENDPOINT:
            if request.headers.get("authorization") == "Bearer token-secret":
                if request.method == "GET":
                    return httpx2.Response(405)
                if request.method == "DELETE":
                    return httpx2.Response(204)
                body = json.loads(request.content)
                if "id" not in body:
                    return httpx2.Response(202)
                if body["method"] == "server/discover":
                    result = {"supportedVersions": ["2026-07-28"], "capabilities": {"tools": {}}}
                elif body["method"] == "tools/list":
                    result = {"tools": [{"name": "mcp-tv-run-screener", "inputSchema": {"type": "object"}}],
                              "cacheScope": "private", "resultType": "complete", "ttlMs": 0}
                else:
                    raise AssertionError(body["method"])
                return httpx2.Response(200, headers={"content-type": "application/json"}, json={
                    "jsonrpc": "2.0", "id": body["id"], "result": result,
                })
            assert request.method == "GET", "MCP session was opened before authorization"
            return httpx2.Response(401, headers={"www-authenticate": f'Bearer resource_metadata="{PRM}"'})
        if url == PRM:
            return httpx2.Response(200, json={"resource": ENDPOINT, "authorization_servers": ["https://www.tradingview.com"]})
        if url == ASM:
            metadata = {
                "issuer": "https://www.tradingview.com",
                "authorization_endpoint": "https://www.tradingview.com/mcp/oauth/authorize",
                "token_endpoint": TOKEN,
                "token_endpoint_auth_methods_supported": ["none"],
                "code_challenge_methods_supported": ["S256"],
                "client_id_metadata_document_supported": advertise_cimd,
            }
            if registration:
                metadata["registration_endpoint"] = REGISTER
            return httpx2.Response(200, json=metadata)
        if url == REGISTER:
            body = json.loads(request.content)
            assert body["token_endpoint_auth_method"] == "none"
            assert body["application_type"] == "native"
            assert body["response_types"] == ["code"]
            body["client_id"] = "issued-client"
            return httpx2.Response(201, json=body)
        if url == TOKEN:
            body = request.content.decode()
            assert "code=code-secret" in body
            assert "code_verifier=" in body
            return httpx2.Response(200, json={"access_token": "token-secret", "refresh_token": "refresh-secret", "token_type": "Bearer", "expires_in": 3600})
        raise AssertionError(f"unexpected request {request.method} {url}")

    async def scenario() -> None:
        storage = auth.KeyringTokenStorage(_keyring=NativeKeyring())
        if expected_strategy == "pre_registered":
            await storage.set_tokens(OAuthToken(access_token="old-token"))
        callback = FakeCallback()
        await bootstrap_oauth(
            _storage=storage, _callback=callback, _http_transport=httpx2.MockTransport(handler),
            _client_id=client_id, _client_metadata_url=cimd_url,
        )
        assert (await storage.get_tokens()).access_token == "token-secret"
        assert (await storage.get_tokens()).refresh_token == "refresh-secret"
        assert await storage.get_token_expiry() is not None
        assert str((await storage.get_oauth_metadata()).issuer) == "https://www.tradingview.com"
        assert callback.url is not None
        query = parse_qs(urlsplit(callback.url).query)
        assert query["code_challenge_method"] == ["S256"]
        assert query["resource"] == [ENDPOINT]
        assert (await storage.get_client_info()).client_id == {
            "dcr": "issued-client", "cimd": cimd_url, "pre_registered": client_id,
        }[expected_strategy]
        assert ("POST", REGISTER) in seen if expected_strategy == "dcr" else ("POST", REGISTER) not in seen
        assert ("POST", ENDPOINT) not in seen
        if expected_strategy == "dcr" and not advertise_cimd:
            async with TradingViewClient(
                _storage=storage, _http_transport=httpx2.MockTransport(handler),
            ) as mcp_client:
                assert (await mcp_client.list_tools()).available_count == 1
            assert ("POST", ENDPOINT) in seen

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("advertise_cimd", "cimd_url", "registration", "expected"),
    [
        (False, None, False, "MCP_OAUTH_CLIENT_REGISTRATION_UNAVAILABLE"),
        (True, None, False, "MCP_OAUTH_CLIENT_REGISTRATION_UNAVAILABLE"),
        (True, "https://chatgpt.com/oauth/client.json", True, "MCP_OAUTH_CLIENT_REGISTRATION_UNAVAILABLE"),
    ],
)
def test_registration_unavailable_never_guesses_endpoint(
    advertise_cimd: bool, cimd_url: str | None, registration: bool,
    expected: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth.sys, "platform", "win32")
    seen: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        url = str(request.url)
        seen.append(url)
        if url == ENDPOINT:
            return httpx2.Response(401, headers={"www-authenticate": f'Bearer resource_metadata="{PRM}"'})
        if url == PRM:
            return httpx2.Response(200, json={"resource": ENDPOINT, "authorization_servers": ["https://www.tradingview.com"]})
        if url == ASM:
            metadata = {"issuer": "https://www.tradingview.com", "authorization_endpoint": "https://www.tradingview.com/authorize", "token_endpoint": TOKEN, "client_id_metadata_document_supported": advertise_cimd, "code_challenge_methods_supported": ["S256"], "token_endpoint_auth_methods_supported": ["none"]}
            if registration:
                metadata["registration_endpoint"] = REGISTER
            return httpx2.Response(200, json=metadata)
        raise AssertionError(url)

    async def scenario() -> None:
        with pytest.raises(AppError) as caught:
            await bootstrap_oauth(
                _storage=auth.KeyringTokenStorage(_keyring=NativeKeyring()),
                _callback=FakeCallback(), _http_transport=httpx2.MockTransport(handler),
                _client_metadata_url=cimd_url,
            )
        assert caught.value.code == expected
        assert not any("register" in url for url in seen)

    asyncio.run(scenario())


@pytest.mark.parametrize(("wrong_state", "wrong_issuer"), [(True, False), (False, True)])
def test_sdk_rejects_callback_state_and_issuer(
    wrong_state: bool, wrong_issuer: bool, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth.sys, "platform", "win32")
    seen_token = False

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal seen_token
        url = str(request.url)
        if url == ENDPOINT:
            return httpx2.Response(401, headers={"www-authenticate": f'Bearer resource_metadata="{PRM}"'})
        if url == PRM:
            return httpx2.Response(200, json={"resource": ENDPOINT, "authorization_servers": ["https://www.tradingview.com"]})
        if url == ASM:
            return httpx2.Response(200, json={
                "issuer": "https://www.tradingview.com", "authorization_endpoint": "https://www.tradingview.com/mcp/oauth/authorize",
                "token_endpoint": TOKEN, "registration_endpoint": REGISTER,
                "token_endpoint_auth_methods_supported": ["none"], "code_challenge_methods_supported": ["S256"],
                "authorization_response_iss_parameter_supported": True,
            })
        if url == REGISTER:
            payload = json.loads(request.content)
            payload["client_id"] = "issued-client"
            return httpx2.Response(201, json=payload)
        if url == TOKEN:
            seen_token = True
            return httpx2.Response(200, json={"access_token": "token-secret", "token_type": "Bearer"})
        raise AssertionError(url)

    async def scenario() -> None:
        storage = auth.KeyringTokenStorage(_keyring=NativeKeyring())
        with pytest.raises(AppError) as caught:
            await bootstrap_oauth(
                _storage=storage, _callback=FakeCallback(wrong_state=wrong_state, wrong_issuer=wrong_issuer),
                _http_transport=httpx2.MockTransport(handler),
            )
        assert caught.value.code == "MCP_OAUTH_FLOW_ERROR"
        assert not seen_token
        assert await storage.get_tokens() is None

    asyncio.run(scenario())


def test_metadata_change_before_sdk_authorization_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth.sys, "platform", "win32")
    asm_reads = 0
    registered = False

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal asm_reads, registered
        url = str(request.url)
        if url == ENDPOINT:
            return httpx2.Response(401, headers={"www-authenticate": f'Bearer resource_metadata="{PRM}"'})
        if url == PRM:
            return httpx2.Response(200, json={"resource": ENDPOINT, "authorization_servers": ["https://www.tradingview.com"]})
        if url == ASM:
            asm_reads += 1
            return httpx2.Response(200, json={
                "issuer": "https://www.tradingview.com", "authorization_endpoint": "https://www.tradingview.com/mcp/oauth/authorize",
                "token_endpoint": TOKEN, "registration_endpoint": REGISTER,
                "token_endpoint_auth_methods_supported": ["none"], "code_challenge_methods_supported": ["S256"],
                "authorization_response_iss_parameter_supported": asm_reads == 1,
            })
        if url == REGISTER:
            registered = True
        raise AssertionError(url)

    async def scenario() -> None:
        with pytest.raises(AppError) as caught:
            await bootstrap_oauth(
                _storage=auth.KeyringTokenStorage(_keyring=NativeKeyring()),
                _callback=FakeCallback(), _http_transport=httpx2.MockTransport(handler),
            )
        assert caught.value.code == "MCP_OAUTH_DISCOVERY_ERROR"
        assert asm_reads == 2
        assert not registered

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        ("as_403", "MCP_OAUTH_DISCOVERY_ERROR"),
        ("registration", "MCP_OAUTH_REGISTRATION_ERROR"),
        ("token", "MCP_OAUTH_TOKEN_ERROR"),
        ("credential", "CREDENTIAL_STORE_ERROR"),
    ],
)
def test_bootstrap_stage_failures_are_secret_free(
    failure: str, expected: str, monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(auth.sys, "platform", "win32")
    seen: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        url = str(request.url)
        seen.append(url)
        if url == ENDPOINT:
            return httpx2.Response(401, headers={"www-authenticate": f'Bearer resource_metadata="{PRM}"'})
        if url == PRM:
            return httpx2.Response(200, json={"resource": ENDPOINT, "authorization_servers": ["https://www.tradingview.com"]})
        if url == ASM:
            if failure == "as_403":
                return httpx2.Response(403, text="SENTINEL_SECRET")
            return httpx2.Response(200, json={
                "issuer": "https://www.tradingview.com", "authorization_endpoint": "https://www.tradingview.com/mcp/oauth/authorize",
                "token_endpoint": TOKEN, "registration_endpoint": REGISTER,
                "code_challenge_methods_supported": ["S256"], "token_endpoint_auth_methods_supported": ["none"],
            })
        if url == "https://www.tradingview.com/.well-known/openid-configuration":
            return httpx2.Response(404)
        if url == REGISTER:
            if failure == "registration":
                return httpx2.Response(400, text="SENTINEL_SECRET")
            data = json.loads(request.content)
            data["client_id"] = "issued-client"
            return httpx2.Response(201, json=data)
        if url == TOKEN:
            if failure == "token":
                return httpx2.Response(400, text="SENTINEL_SECRET")
            return httpx2.Response(200, json={"access_token": "SENTINEL_SECRET", "token_type": "Bearer"})
        raise AssertionError(url)

    async def scenario() -> None:
        storage = auth.KeyringTokenStorage(_keyring=NativeKeyring())
        if failure == "credential":
            async def fail_save(_tokens: OAuthToken) -> None:
                raise AppError("CREDENTIAL_STORE_ERROR", "Credential Store is unavailable")

            storage.set_tokens = fail_save
        with pytest.raises(AppError) as caught:
            await bootstrap_oauth(
                _storage=storage, _callback=FakeCallback(), _http_transport=httpx2.MockTransport(handler),
            )
        assert caught.value.code == expected
        assert "SENTINEL_SECRET" not in caught.value.message
        assert "SENTINEL_SECRET" not in caplog.text
        if failure == "as_403":
            assert REGISTER not in seen

    asyncio.run(scenario())
