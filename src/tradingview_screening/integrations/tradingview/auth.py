"""MCP SDK OAuth wiring and OS-native credential storage."""

from __future__ import annotations

import asyncio
import json
import math
import sys
import time
import webbrowser
from collections.abc import Callable
from typing import Self
from urllib.parse import parse_qs, urlsplit

import keyring
from mcp.client.auth import AuthorizationCodeResult
from mcp.shared.auth import OAuthClientInformationFull, OAuthMetadata, OAuthToken
from pydantic import ValidationError

from tradingview_screening.common.errors import AppError

SERVICE = "tradingview-mcp-support/oauth"
CALLBACK_PATH = "/oauth/callback"
CALLBACK_PORT = 8765


class KeyringTokenStorage:
    """Persist SDK token and registration records in an OS-native keyring."""

    def __init__(self, *, _keyring: object = keyring) -> None:
        self._keyring = _keyring
        self.metadata_source: Callable[[], OAuthMetadata | None] | None = None

    def _check_backend(self) -> None:
        try:
            module = type(self._keyring.get_keyring()).__module__
        except Exception as exc:
            raise AppError("CREDENTIAL_STORE_ERROR", "Credential Store is unavailable") from exc
        expected = {"win32": "keyring.backends.Windows", "darwin": "keyring.backends.macOS"}
        if module != expected.get(sys.platform):
            raise AppError("CREDENTIAL_STORE_ERROR", "OS Credential Store is unavailable")

    def _read(self, name: str) -> dict[str, object] | None:
        self._check_backend()
        try:
            value = self._keyring.get_password(SERVICE, name)
            if value is None:
                return None
            decoded = json.loads(value)
            if not isinstance(decoded, dict):
                raise TypeError("invalid credential record")
            return decoded
        except AppError:
            raise
        except Exception as exc:
            raise AppError("CREDENTIAL_STORE_ERROR", "Credential Store record is unavailable") from exc

    def _write(self, name: str, record: dict[str, object]) -> None:
        self._check_backend()
        try:
            self._keyring.set_password(SERVICE, name, json.dumps(record))
        except Exception as exc:
            raise AppError("CREDENTIAL_STORE_ERROR", "Cannot save Credential Store record") from exc

    async def get_tokens(self) -> OAuthToken | None:
        record = self._read("tokens")
        if record is None:
            return None
        try:
            token = OAuthToken.model_validate(record["token"])
            expires_at = self._expiry_from_record(record)
            if expires_at is not None and expires_at <= time.time():
                # SDK 2.2.0 does not restore expiry after loading stored tokens.
                # Withhold the expired access token so its public auth flow refreshes it.
                token = token.model_copy(update={"access_token": ""})
            return token
        except (KeyError, ValueError, TypeError, ValidationError) as exc:
            raise AppError("CREDENTIAL_STORE_ERROR", "Credential Store token record is invalid") from exc

    @staticmethod
    def _expiry_from_record(record: dict[str, object]) -> float | None:
        value = record.get("expires_at")
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("invalid expiry")
        return float(value)

    async def get_token_expiry(self) -> float | None:
        record = self._read("tokens")
        if record is None:
            return None
        try:
            return self._expiry_from_record(record)
        except ValueError as exc:
            raise AppError("CREDENTIAL_STORE_ERROR", "Credential Store token record is invalid") from exc

    async def set_tokens(self, tokens: OAuthToken) -> None:
        expires_at = time.time() + tokens.expires_in if tokens.expires_in is not None else None
        self._write("tokens", {"token": tokens.model_dump(mode="json"), "expires_at": expires_at})
        if callable(self.metadata_source):
            metadata = self.metadata_source()
            if metadata is not None:
                await self.set_oauth_metadata(metadata)

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        record = self._read("client_info")
        if record is None:
            return None
        try:
            return OAuthClientInformationFull.model_validate(record)
        except ValidationError as exc:
            raise AppError("CREDENTIAL_STORE_ERROR", "Credential Store client record is invalid") from exc

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self._write("client_info", client_info.model_dump(mode="json"))

    async def get_oauth_metadata(self) -> OAuthMetadata | None:
        record = self._read("oauth_metadata")
        if record is None:
            return None
        try:
            return OAuthMetadata.model_validate(record)
        except ValidationError as exc:
            raise AppError("CREDENTIAL_STORE_ERROR", "Credential Store OAuth metadata is invalid") from exc

    async def set_oauth_metadata(self, metadata: OAuthMetadata) -> None:
        self._write("oauth_metadata", metadata.model_dump(mode="json"))


async def noninteractive_redirect(_url: str) -> None:
    raise AppError("AUTH_REQUIRED", "Interactive authorization is required")


async def noninteractive_callback() -> AuthorizationCodeResult:
    raise AppError("AUTH_REQUIRED", "Interactive authorization is required")


class LoopbackCallback:
    """One-shot loopback HTTP listener for the SDK authorization callback."""

    def __init__(self) -> None:
        self._server: asyncio.Server | None = None
        self._result: asyncio.Future[AuthorizationCodeResult] | None = None
        self.redirect_uri = ""

    async def __aenter__(self) -> Self:
        self._result = asyncio.get_running_loop().create_future()
        try:
            self._server = await asyncio.start_server(self._handle, "127.0.0.1", CALLBACK_PORT)
        except OSError as exc:
            raise AppError("MCP_CONNECTION_ERROR", "OAuth loopback listener cannot start") from exc
        self.redirect_uri = f"http://127.0.0.1:{CALLBACK_PORT}{CALLBACK_PATH}"
        return self

    async def __aexit__(self, *_args: object) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            line = await asyncio.wait_for(reader.readline(), 5)
            if len(line) > 8192:
                raise ValueError("request too long")
            parts = line.decode("ascii").split()
            if len(parts) != 3 or parts[0] != "GET":
                raise ValueError("invalid callback")
            target = urlsplit(parts[1])
            if target.path != CALLBACK_PATH:
                raise ValueError("invalid callback path")
            params = parse_qs(target.query, keep_blank_values=True)
            if any(len(params.get(name, [])) != 1 for name in ("code", "state")):
                raise ValueError("missing callback parameter")
            if len(params.get("iss", [])) > 1:
                raise ValueError("duplicate issuer")
            result = AuthorizationCodeResult(
                code=params["code"][0],
                state=params["state"][0],
                iss=params.get("iss", [None])[0],
            )
            if self._result is not None and not self._result.done():
                self._result.set_result(result)
                if self._server is not None:
                    self._server.close()
            body = b"Authorization received. You may close this window."
            status = b"200 OK"
        except (TimeoutError, ValueError, UnicodeError):
            body = b"Invalid OAuth callback."
            status = b"400 Bad Request"
        writer.write(
            b"HTTP/1.1 " + status + b"\r\nContent-Type: text/plain\r\nContent-Length: "
            + str(len(body)).encode("ascii") + b"\r\nConnection: close\r\n\r\n" + body
        )
        try:
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def redirect(self, url: str) -> None:
        try:
            opened = webbrowser.open(url)
        except Exception as exc:
            raise AppError("AUTH_REQUIRED", "Browser could not open for authorization") from exc
        if not opened:
            raise AppError("AUTH_REQUIRED", "Browser could not open for authorization")

    async def callback(self) -> AuthorizationCodeResult:
        if self._result is None:
            raise AppError("AUTH_REQUIRED", "OAuth callback listener is unavailable")
        try:
            return await asyncio.wait_for(self._result, 120)
        except TimeoutError as exc:
            raise AppError("AUTH_REQUIRED", "OAuth callback timed out") from exc
