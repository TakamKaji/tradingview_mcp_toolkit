from __future__ import annotations

import asyncio
import os
import stat
import sys
from pathlib import Path

import pytest
from mcp.shared.auth import OAuthToken

from tradingview_screening.common.errors import AppError
from tradingview_screening.integrations.tradingview import auth


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


def _request(path: str, host: str = "127.0.0.1:8765") -> asyncio.StreamReader:
    reader = asyncio.StreamReader()
    reader.feed_data(f"GET {path} HTTP/1.1\r\nHost: {host}\r\n\r\n".encode("ascii"))
    reader.feed_eof()
    return reader


def test_auth_mode_fails_closed_on_windows_and_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth.sys, "platform", "win32")
    monkeypatch.delenv("TRADINGVIEW_MCP_AUTH_MODE", raising=False)
    assert isinstance(auth.create_token_storage(), auth.KeyringTokenStorage)
    assert not isinstance(auth.create_token_storage(), auth.ContainerTokenStorage)
    for mode in ("container", "invalid", "", "CONTAINER"):
        monkeypatch.setenv("TRADINGVIEW_MCP_AUTH_MODE", mode)
        with pytest.raises(AppError) as caught:
            auth.create_token_storage()
        assert caught.value.code == "CREDENTIAL_STORE_ERROR"

    async def direct_storage() -> None:
        with pytest.raises(AppError) as caught:
            await auth.ContainerTokenStorage().get_tokens()
        assert caught.value.code == "CREDENTIAL_STORE_ERROR"
        assert "AttributeError" not in caught.value.message

    asyncio.run(direct_storage())


def test_container_browser_entry_keeps_sdk_url_out_of_body_and_stderr(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    class FakeServer:
        def close(self) -> None:
            pass

        async def wait_closed(self) -> None:
            pass

    bound: list[tuple[str, int]] = []

    async def fake_start_server(_handler, host: str, port: int) -> FakeServer:
        bound.append((host, port))
        return FakeServer()

    monkeypatch.setattr(auth.asyncio, "start_server", fake_start_server)

    async def response(callback: auth.ContainerCallback, path: str, host: str = "127.0.0.1:8765") -> bytes:
        writer = FakeWriter()
        await callback._handle(_request(path, host), writer)
        return bytes(writer.output)

    async def scenario() -> None:
        async with auth.ContainerCallback() as callback:
            assert bound == [("0.0.0.0", 8765)]
            assert callback.redirect_uri == "http://127.0.0.1:8765/oauth/callback"
            waiting = await response(callback, "/oauth/authorize")
            assert b"503 Service Unavailable" in waiting
            assert b"Cache-Control: no-store" in waiting
            secret_url = (
                "https://www.tradingview.com/mcp/oauth/authorize?"
                "redirect_uri=http%3A%2F%2F127.0.0.1%3A8765%2Foauth%2Fcallback"
                "&response_type=code&code_challenge_method=S256&code_challenge=challenge"
                "&state=secret-state"
            )
            await callback.redirect(secret_url)
            redirect = await response(callback, "/oauth/authorize")
            assert b"302 Found" in redirect
            assert b"Location: " + secret_url.encode() in redirect
            assert b"Cache-Control: no-store" in redirect
            assert redirect.endswith(b"\r\n\r\n")
            bad_host = await response(callback, "/oauth/authorize", "evil.example")
            assert b"400 Bad Request" in bad_host
            assert b"Cache-Control: no-store" in bad_host
            assert b"400 Bad Request" in await response(callback, "http://evil.example/oauth/authorize")
            assert b"400 Bad Request" in await response(callback, "/oauth/authorize?next=https://evil.example")
            assert b"400 Bad Request" in await response(callback, "/oauth/callback?code=x&state=y&state=z")
            assert b"400 Bad Request" in await response(
                callback, "/oauth/callback?code=x&state=y", "evil.example",
            )
            assert not callback._result.done()
            callback._authorization_deadline = 0
            assert b"503 Service Unavailable" in await response(callback, "/oauth/authorize")
            callback_result = await response(
                callback,
                "/oauth/callback?code=secret-code&state=secret-state&iss=https%3A%2F%2Fwww.tradingview.com",
            )
            assert b"200 OK" in callback_result
            assert b"secret-code" not in callback_result
            assert b"secret-state" not in callback_result
            result = await asyncio.wait_for(callback.callback(), 1)
            assert (result.code, result.state, result.iss) == (
                "secret-code", "secret-state", "https://www.tradingview.com",
            )

    asyncio.run(scenario())
    captured = capsys.readouterr()
    assert "http://127.0.0.1:8765/oauth/authorize" in captured.err
    assert "secret-state" not in captured.out + captured.err


def test_container_authorization_rejects_external_url(monkeypatch: pytest.MonkeyPatch) -> None:
    callback = auth.ContainerCallback()
    callback._server = object()

    async def scenario() -> None:
        for url in (
            "http://www.tradingview.com/mcp/oauth/authorize",
            "https://evil.example/mcp/oauth/authorize",
            "https://www.tradingview.com.evil.example/mcp/oauth/authorize",
            "https://www.tradingview.com/other?state=x",
            "https://www.tradingview.com/mcp/oauth/authorize?state=x\r\nBad: yes",
        ):
            with pytest.raises(AppError) as caught:
                await callback.redirect(url)
            assert caught.value.code == "MCP_OAUTH_FLOW_ERROR"

    asyncio.run(scenario())


@pytest.mark.skipif(sys.platform != "linux", reason="Linux file permissions required")
def test_container_file_storage_security(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRADINGVIEW_MCP_AUTH_MODE", "container")
    private = tmp_path / "credentials"
    private.mkdir(mode=0o700)
    private.chmod(0o700)
    monkeypatch.setattr(
        auth.ContainerTokenStorage, "_directory_fd",
        staticmethod(lambda: auth.ContainerTokenStorage._open_private_directory(private)),
    )
    storage = auth.ContainerTokenStorage()

    async def scenario() -> None:
        await storage.set_tokens(OAuthToken(access_token="secret", refresh_token="refresh"))
        record = private / "tokens"
        assert (await storage.get_tokens()).access_token == "secret"
        assert stat.S_IMODE(record.stat().st_mode) == 0o600
        assert not list(private.glob(".tokens.*"))
        await storage.set_tokens(OAuthToken(access_token="expired", refresh_token="refresh", expires_in=0))
        assert (await storage.get_tokens()).access_token == ""
        assert (await storage.get_tokens()).refresh_token == "refresh"
        record.write_text("broken json", encoding="utf-8")
        with pytest.raises(AppError) as caught:
            await storage.get_tokens()
        assert "broken json" not in caught.value.message
        await storage.set_tokens(OAuthToken(access_token="recreated"))
        assert (await storage.get_tokens()).access_token == "recreated"
        record.chmod(0o644)
        with pytest.raises(AppError, match="Container Credential Store"):
            await storage.get_tokens()
        with pytest.raises(AppError, match="Container Credential Store"):
            await storage.set_tokens(OAuthToken(access_token="another"))
        record.unlink()
        outside = tmp_path / "outside"
        outside.write_text("sensitive", encoding="utf-8")
        record.symlink_to(outside)
        with pytest.raises(AppError):
            await storage.get_tokens()
        with pytest.raises(AppError):
            await storage.set_tokens(OAuthToken(access_token="another"))
        assert outside.read_text(encoding="utf-8") == "sensitive"
        record.unlink()
        os.link(outside, record)
        record.chmod(0o600)
        with pytest.raises(AppError):
            await storage.get_tokens()
        record.unlink()
        fifo = private / "tokens"
        os.mkfifo(fifo, mode=0o600)
        with pytest.raises(AppError):
            await storage.get_tokens()
        with pytest.raises(AppError):
            await storage.set_tokens(OAuthToken(access_token="another"))
        fifo.unlink()
        private.chmod(0o755)
        with pytest.raises(AppError):
            await storage.get_tokens()
        private.chmod(0o700)
        real_uid = os.geteuid()
        monkeypatch.setattr(auth.os, "geteuid", lambda: real_uid + 1)
        with pytest.raises(AppError):
            await storage.get_tokens()
        monkeypatch.setattr(auth.os, "geteuid", lambda: real_uid)
        private.rename(tmp_path / "real_credentials")
        private.symlink_to(tmp_path / "real_credentials", target_is_directory=True)
        with pytest.raises(AppError):
            await storage.get_tokens()

    asyncio.run(scenario())
