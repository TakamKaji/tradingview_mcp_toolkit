"""MCP SDK OAuth wiring and OS-native credential storage."""

from __future__ import annotations

import asyncio
import json
import math
import os
import secrets
import stat
import sys
import time
import webbrowser
from collections.abc import Callable
from pathlib import Path
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
AUTHORIZE_PATH = "/oauth/authorize"
CONTAINER_CREDENTIAL_DIR = Path("/credentials")
_AUTH_MODE_ENV = "TRADINGVIEW_MCP_AUTH_MODE"


def auth_mode() -> str:
    mode = os.environ.get(_AUTH_MODE_ENV, "native")
    if mode == "native":
        return mode
    if mode == "container" and sys.platform.startswith("linux"):
        return mode
    raise AppError("CREDENTIAL_STORE_ERROR", "Credential Store mode is unavailable")


def create_token_storage() -> KeyringTokenStorage:
    if auth_mode() == "container":
        return ContainerTokenStorage()
    return KeyringTokenStorage()


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


class ContainerTokenStorage(KeyringTokenStorage):
    """Store the same SDK records in the dedicated, private container volume."""

    _NAMES = frozenset({"tokens", "client_info", "oauth_metadata"})

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def _directory_fd() -> int:
        if str(CONTAINER_CREDENTIAL_DIR) != "/credentials" or os.geteuid() != 10001:
            raise AppError("CREDENTIAL_STORE_ERROR", "Container Credential Store is unavailable")
        return ContainerTokenStorage._open_private_directory(CONTAINER_CREDENTIAL_DIR)

    @staticmethod
    def _open_private_directory(path: Path) -> int:
        try:
            if auth_mode() != "container":
                raise ValueError("container mode required")
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700:
                raise ValueError("unsafe credential directory")
            if info.st_uid != os.geteuid():
                raise ValueError("credential directory owner changed")
            fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            actual = os.fstat(fd)
            if (actual.st_dev, actual.st_ino) != (info.st_dev, info.st_ino):
                os.close(fd)
                raise ValueError("credential directory changed")
            return fd
        except Exception as exc:
            raise AppError("CREDENTIAL_STORE_ERROR", "Container Credential Store is unavailable") from exc

    @staticmethod
    def _checked_file(fd: int) -> None:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1
        ):
            raise ValueError("unsafe credential file")

    def _read(self, name: str) -> dict[str, object] | None:
        try:
            if name not in self._NAMES:
                raise ValueError("invalid credential name")
            dir_fd = self._directory_fd()
            try:
                try:
                    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
                except FileNotFoundError:
                    return None
                try:
                    self._checked_file(fd)
                    with os.fdopen(fd, "rb", closefd=False) as source:
                        raw = source.read(1024 * 1024 + 1)
                    if len(raw) > 1024 * 1024:
                        raise ValueError("credential record too large")
                    decoded = json.loads(raw)
                    if not isinstance(decoded, dict):
                        raise TypeError("invalid credential record")
                    return decoded
                finally:
                    os.close(fd)
            finally:
                os.close(dir_fd)
        except AppError:
            raise
        except Exception as exc:
            raise AppError("CREDENTIAL_STORE_ERROR", "Container Credential Store record is unavailable") from exc

    def _write(self, name: str, record: dict[str, object]) -> None:
        try:
            if name not in self._NAMES:
                raise ValueError("invalid credential name")
            raw = json.dumps(record, allow_nan=False).encode("utf-8")
            if len(raw) > 1024 * 1024:
                raise ValueError("credential record too large")
            dir_fd = self._directory_fd()
            temp_name: str | None = None
            try:
                try:
                    existing = os.open(
                        name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd,
                    )
                except FileNotFoundError:
                    pass
                else:
                    try:
                        self._checked_file(existing)
                    finally:
                        os.close(existing)
                temp_name = f".{name}.{secrets.token_hex(16)}"
                temp_fd = os.open(
                    temp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600, dir_fd=dir_fd,
                )
                try:
                    self._checked_file(temp_fd)
                    with os.fdopen(temp_fd, "wb", closefd=False) as destination:
                        destination.write(raw)
                        destination.flush()
                        os.fsync(temp_fd)
                finally:
                    os.close(temp_fd)
                os.replace(temp_name, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
                temp_name = None
                os.fsync(dir_fd)
            finally:
                if temp_name is not None:
                    os.unlink(temp_name, dir_fd=dir_fd)
                os.close(dir_fd)
        except AppError:
            raise
        except Exception as exc:
            raise AppError("CREDENTIAL_STORE_ERROR", "Cannot save Container Credential Store record") from exc


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


class ContainerCallback(LoopbackCallback):
    """Expose a fixed local browser entry while keeping the SDK URL out of logs."""

    def __init__(self) -> None:
        super().__init__()
        self._authorization_url: str | None = None
        self._authorization_deadline = 0.0

    async def __aenter__(self) -> Self:
        self._result = asyncio.get_running_loop().create_future()
        try:
            self._server = await asyncio.start_server(self._handle, "0.0.0.0", CALLBACK_PORT)
        except OSError as exc:
            raise AppError("MCP_CONNECTION_ERROR", "OAuth callback listener cannot start") from exc
        self.redirect_uri = f"http://127.0.0.1:{CALLBACK_PORT}{CALLBACK_PATH}"
        return self

    async def redirect(self, url: str) -> None:
        try:
            parsed = urlsplit(url)
            params = parse_qs(parsed.query, keep_blank_values=True)
            valid = (
                parsed.scheme == "https"
                and parsed.hostname == "www.tradingview.com"
                and parsed.port in (None, 443)
                and parsed.username is None
                and parsed.password is None
                and parsed.path == "/mcp/oauth/authorize"
                and not parsed.fragment
                and url.isascii()
                and not any(ord(char) < 32 or ord(char) == 127 for char in url)
                and params.get("redirect_uri") == [self.redirect_uri]
                and params.get("response_type") == ["code"]
                and params.get("code_challenge_method") == ["S256"]
                and len(params.get("code_challenge", [])) == 1
                and bool(params["code_challenge"][0])
                and len(params.get("state", [])) == 1
                and bool(params["state"][0])
            )
        except ValueError:
            valid = False
        if not valid or self._server is None:
            raise AppError("MCP_OAUTH_FLOW_ERROR", "OAuth authorization URL is invalid")
        self._authorization_url = url
        self._authorization_deadline = time.monotonic() + 120
        print(f"Open http://127.0.0.1:{CALLBACK_PORT}{AUTHORIZE_PATH}", file=sys.stderr)

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        status = b"400 Bad Request"
        headers = (
            b"Content-Type: text/plain; charset=utf-8\r\n"
            b"Cache-Control: no-store\r\nPragma: no-cache\r\n"
            b"Referrer-Policy: no-referrer\r\n"
        )
        body = b"Invalid OAuth request."
        try:
            line = await asyncio.wait_for(reader.readline(), 5)
            if len(line) > 8192:
                raise ValueError("request too long")
            parts = line.decode("ascii").split()
            if len(parts) != 3 or parts[0] != "GET" or parts[2] != "HTTP/1.1":
                raise ValueError("invalid request")
            header_lines: list[bytes] = []
            total = len(line)
            while True:
                header = await asyncio.wait_for(reader.readline(), 5)
                total += len(header)
                if total > 8192 or not header:
                    raise ValueError("invalid headers")
                if header in (b"\r\n", b"\n"):
                    break
                header_lines.append(header)
            hosts = [
                value.strip() for header in header_lines
                if header.lower().startswith(b"host:")
                for value in [header.split(b":", 1)[1]]
            ]
            if hosts != [b"127.0.0.1:8765"]:
                raise ValueError("invalid host")
            target = parts[1]
            if target == AUTHORIZE_PATH:
                if self._authorization_url is None or time.monotonic() >= self._authorization_deadline:
                    status = b"503 Service Unavailable"
                    body = b"OAuth authorization is not ready."
                else:
                    status = b"302 Found"
                    headers = (
                        b"Location: " + self._authorization_url.encode("ascii") + b"\r\n"
                        b"Cache-Control: no-store\r\nPragma: no-cache\r\n"
                        b"Referrer-Policy: no-referrer\r\n"
                    )
                    body = b""
            else:
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or parsed.path != CALLBACK_PATH or parsed.fragment:
                    raise ValueError("invalid callback path")
                params = parse_qs(parsed.query, keep_blank_values=True)
                if any(len(params.get(name, [])) != 1 for name in ("code", "state")):
                    raise ValueError("missing callback parameter")
                if len(params.get("iss", [])) > 1:
                    raise ValueError("duplicate issuer")
                result = AuthorizationCodeResult(
                    code=params["code"][0], state=params["state"][0],
                    iss=params.get("iss", [None])[0],
                )
                if self._result is not None and not self._result.done():
                    self._result.set_result(result)
                    if self._server is not None:
                        self._server.close()
                status = b"200 OK"
                body = b"Authorization received. You may close this window."
        except (TimeoutError, ValueError, UnicodeError, asyncio.LimitOverrunError):
            pass
        writer.write(
            b"HTTP/1.1 " + status + b"\r\n" + headers
            + b"Content-Length: " + str(len(body)).encode("ascii")
            + b"\r\nConnection: close\r\n\r\n" + body
        )
        try:
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()
