from __future__ import annotations

import asyncio

import httpx2
import pytest
from mcp.client.auth import OAuthClientProvider
from mcp.shared.auth import (
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthMetadata,
    OAuthToken,
)

from tradingview_screening.common.errors import AppError
from tradingview_screening.integrations.tradingview import auth
from tradingview_screening.integrations.tradingview.client import ENDPOINT, ClassifyingTransport


class NativeKeyring:
    __module__ = "keyring.backends.Windows"

    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def get_keyring(self) -> NativeKeyring:
        return self

    def get_password(self, service: str, name: str) -> str | None:
        return self.values.get((service, name))

    def set_password(self, service: str, name: str, value: str) -> None:
        self.values[(service, name)] = value


def _storage() -> tuple[auth.KeyringTokenStorage, NativeKeyring]:
    fake = NativeKeyring()
    return auth.KeyringTokenStorage(_keyring=fake), fake


def test_token_client_info_and_metadata_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth.sys, "platform", "win32")

    async def scenario() -> None:
        storage, fake = _storage()
        assert await storage.get_tokens() is None
        assert await storage.get_client_info() is None
        token = OAuthToken(access_token="secret-access", refresh_token="secret-refresh", expires_in=60)
        info = OAuthClientInformationFull(client_id="client-id", client_secret="secret-client")
        metadata = OAuthMetadata(
            issuer="https://accounts.example",
            authorization_endpoint="https://accounts.example/authorize",
            token_endpoint="https://accounts.example/token",
        )
        await storage.set_tokens(token)
        await storage.set_client_info(info)
        await storage.set_oauth_metadata(metadata)
        assert (await storage.get_tokens()).access_token == "secret-access"
        assert (await storage.get_client_info()).client_id == "client-id"
        assert str((await storage.get_oauth_metadata()).token_endpoint) == "https://accounts.example/token"
        assert await storage.get_token_expiry() is not None
        assert len(fake.values) == 3

    asyncio.run(scenario())


def test_expired_token_withholds_access_for_sdk_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth.sys, "platform", "win32")
    now = [1000.0]
    monkeypatch.setattr(auth.time, "time", lambda: now[0])

    async def scenario() -> None:
        storage, _ = _storage()
        await storage.set_tokens(OAuthToken(access_token="old", refresh_token="refresh", expires_in=10))
        assert (await storage.get_tokens()).access_token == "old"
        now[0] = 1011.0
        restored = await storage.get_tokens()
        assert restored.access_token == ""
        assert restored.refresh_token == "refresh"
        assert await storage.get_token_expiry() == 1010.0

    asyncio.run(scenario())


@pytest.mark.parametrize("invalid", ["not json", "[]", '{"token": {}}', '{"token": {"access_token": "x"}, "expires_at": true}', '{"token": {"access_token": "x"}, "expires_at": NaN}'])
def test_malformed_stored_record_is_sanitized(invalid: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth.sys, "platform", "win32")

    async def scenario() -> None:
        storage, fake = _storage()
        fake.values[(auth.SERVICE, "tokens")] = invalid
        with pytest.raises(AppError) as caught:
            await storage.get_tokens()
        assert caught.value.code == "CREDENTIAL_STORE_ERROR"
        assert invalid not in caught.value.message

    asyncio.run(scenario())


def test_non_native_backend_and_backend_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth.sys, "platform", "win32")

    class Other(NativeKeyring):
        __module__ = "keyring.backends.fail"

    class Broken(NativeKeyring):
        def get_password(self, _service: str, _name: str) -> str:
            raise RuntimeError("secret backend text")

    async def scenario() -> None:
        with pytest.raises(AppError, match="OS Credential Store"):
            await auth.KeyringTokenStorage(_keyring=Other()).get_tokens()
        with pytest.raises(AppError) as caught:
            await auth.KeyringTokenStorage(_keyring=Broken()).get_tokens()
        assert caught.value.code == "CREDENTIAL_STORE_ERROR"
        assert "secret" not in caught.value.message

    asyncio.run(scenario())


def test_noninteractive_handlers_never_open_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth.webbrowser, "open", lambda _url: pytest.fail("browser opened"))

    async def scenario() -> None:
        with pytest.raises(AppError, match="Interactive authorization"):
            await auth.noninteractive_redirect("https://example")
        with pytest.raises(AppError, match="Interactive authorization"):
            await auth.noninteractive_callback()

    asyncio.run(scenario())


def test_interactive_redirect_opens_browser_only_here(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(auth.webbrowser, "open", lambda url: opened.append(url) or True)

    async def scenario() -> None:
        callback = auth.LoopbackCallback()
        await callback.redirect("https://example/authorize")
        assert opened == ["https://example/authorize"]
        monkeypatch.setattr(auth.webbrowser, "open", lambda _url: (_ for _ in ()).throw(RuntimeError("secret")))
        with pytest.raises(AppError) as caught:
            await callback.redirect("https://example")
        assert "secret" not in caught.value.message

    asyncio.run(scenario())


def test_callback_preserves_state_and_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    bound: list[tuple[str, int]] = []

    class FakeSocket:
        def getsockname(self) -> tuple[str, int]:
            return ("127.0.0.1", auth.CALLBACK_PORT)

    class FakeServer:
        def __init__(self) -> None:
            self.sockets = [FakeSocket()]
            self.closed = False

        def close(self) -> None:
            self.closed = True

        async def wait_closed(self) -> None:
            pass

    class FakeWriter:
        def __init__(self) -> None:
            self.output = bytearray()

        def write(self, data: bytes) -> None:
            self.output.extend(data)

        async def drain(self) -> None:
            pass

        def close(self) -> None:
            pass

        async def wait_closed(self) -> None:
            pass

    server = FakeServer()

    async def fake_start_server(_handler, host: str, port: int) -> FakeServer:
        bound.append((host, port))
        return server

    monkeypatch.setattr(auth.asyncio, "start_server", fake_start_server)

    async def scenario() -> None:
        async with auth.LoopbackCallback() as callback:
            assert callback.redirect_uri == "http://127.0.0.1:8765/oauth/callback"
            assert bound == [("127.0.0.1", auth.CALLBACK_PORT)]
            reader = asyncio.StreamReader()
            reader.feed_data(
                b"GET /oauth/callback?code=abc&state=a%2Bb&iss=https%3A%2F%2Fissuer.example "
                b"HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n"
            )
            reader.feed_eof()
            writer = FakeWriter()
            await callback._handle(reader, writer)
            assert b"200 OK" in writer.output
            result = await callback.callback()
            assert (result.code, result.state, result.iss) == ("abc", "a+b", "https://issuer.example")
            assert server.closed

    asyncio.run(scenario())


def test_sdk_refresh_uses_stored_external_authorization_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SDK's real OAuth flow refreshes across restart without a browser or /token fallback."""
    monkeypatch.setattr(auth.sys, "platform", "win32")
    seen: list[tuple[str, str | None]] = []

    def response(request: httpx2.Request) -> httpx2.Response:
        seen.append((str(request.url), request.headers.get("authorization")))
        if str(request.url) == "https://accounts.example/token":
            return httpx2.Response(
                200,
                json={"access_token": "new-access", "token_type": "Bearer", "refresh_token": "new-refresh"},
                request=request,
            )
        if str(request.url) == ENDPOINT:
            if request.headers.get("authorization") == "Bearer new-access":
                return httpx2.Response(200, json={"ok": True}, request=request)
            return httpx2.Response(401, request=request)
        raise AssertionError(f"unexpected request {request.url}")

    async def scenario() -> None:
        storage, _ = _storage()
        await storage.set_tokens(OAuthToken(access_token="expired", refresh_token="refresh", expires_in=0))
        await storage.set_client_info(OAuthClientInformationFull(client_id="client"))
        await storage.set_oauth_metadata(OAuthMetadata(
            issuer="https://accounts.example",
            authorization_endpoint="https://accounts.example/authorize",
            token_endpoint="https://accounts.example/token",
        ))
        metadata = OAuthClientMetadata(redirect_uris=["http://127.0.0.1:8765/oauth/callback"])
        provider = OAuthClientProvider(
            ENDPOINT, metadata, storage,
            redirect_handler=auth.noninteractive_redirect,
            callback_handler=auth.noninteractive_callback,
        )
        provider.context.oauth_metadata = await storage.get_oauth_metadata()
        provider.context.token_expiry_time = await storage.get_token_expiry()
        storage.metadata_source = lambda: provider.context.oauth_metadata
        async with httpx2.AsyncClient(
            auth=provider, transport=ClassifyingTransport(httpx2.MockTransport(response)),
        ) as client:
            result = await client.get(ENDPOINT)
        assert result.status_code == 200
        assert seen[0][0] == "https://accounts.example/token"
        assert seen[1] == (ENDPOINT, "Bearer new-access")
        assert (await storage.get_tokens()).access_token == "new-access"

    asyncio.run(scenario())
