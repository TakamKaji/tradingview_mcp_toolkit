"""Small official TradingView MCP client foundation."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Hashable
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any, Self
from urllib.parse import urlsplit

import httpx2
from mcp import Client, MCPError
from mcp.client.auth import (
    OAuthClientProvider,
    OAuthFlowError,
    OAuthRegistrationError,
    OAuthTokenError,
)
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientMetadata
from mcp.types import INVALID_PARAMS, METHOD_NOT_FOUND

from tradingview_screening.common.errors import AppError, TransientRequestError
from tradingview_screening.common.request_governor import RequestGovernor

from .auth import (
    CALLBACK_PATH,
    CALLBACK_PORT,
    KeyringTokenStorage,
    noninteractive_callback,
    noninteractive_redirect,
)
from .tool_catalog import EXPECTED_TOOLS

ENDPOINT = "https://mcp.tradingview.com/mcp"
_TEMPORARY_HTTP = -32029
_PERMISSION_HTTP = -32043
_ARGUMENT_HTTP = -32040
_AUTH_HTTP = -32041
_CREDENTIAL_HTTP = -32042
_CONNECTION_HTTP = -32001
_OAUTH_REGISTRATION = -32044
_OAUTH_TOKEN = -32045
_OAUTH_FLOW = -32046
_TEMPORARY_STATUSES = frozenset({429, 500, 502, 503, 504})
APP_USER_AGENT = "TradingView-MCP-Support/0.0.0"


@dataclass(frozen=True)
class ToolInfo:
    name: str
    title: str | None
    description: str | None
    input_schema: dict[str, Any]
    expected: bool
    implemented: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": self.input_schema,
            "expected": self.expected,
            "implemented": self.implemented,
        }


@dataclass(frozen=True)
class ToolCatalog:
    tools: tuple[ToolInfo, ...]
    expected_missing: tuple[str, ...]
    unexpected_available: tuple[str, ...]

    @property
    def available_count(self) -> int:
        return len(self.tools)


@dataclass(frozen=True)
class ToolCallData:
    """Structured machine data and separate unstructured MCP content."""

    structured_content: Any
    content: list[dict[str, Any]]


class _DropOAuthLogs(logging.Filter):
    def filter(self, _record: logging.LogRecord) -> bool:
        return False


def _exception_type_names(exc: BaseException) -> tuple[str, ...]:
    """Return exception class names only; never include exception text or provider data."""
    if isinstance(exc, BaseExceptionGroup):
        names: list[str] = []
        for member in exc.exceptions:
            for name in _exception_type_names(member):
                if name not in names:
                    names.append(name)
        return tuple(names)
    return (type(exc).__name__,)


def _normalize_error(exc: BaseException) -> Exception:
    """Map provider/transport errors without exposing body, headers or token values."""
    if isinstance(exc, BaseExceptionGroup):
        # AnyIO/transport teardown can wrap the actionable OAuth/HTTP failure together
        # with secondary cancellation/cleanup exceptions. Inspect every leaf first.
        # Prefer a specific application error, then a transient transport failure, and
        # only then fall back to a generic connection error.
        specific: AppError | None = None
        transient: TransientRequestError | None = None
        generic: AppError | None = None
        for member in exc.exceptions:
            mapped = _normalize_error(member)
            if isinstance(mapped, AppError):
                if mapped.code != "MCP_CONNECTION_ERROR" and specific is None:
                    specific = mapped
                elif generic is None:
                    generic = mapped
            elif isinstance(mapped, TransientRequestError) and transient is None:
                transient = mapped
        return specific or transient or generic or AppError("MCP_CONNECTION_ERROR", "MCP connection failed")
    if isinstance(exc, (AppError, TransientRequestError)):
        return exc
    if isinstance(exc, httpx2.HTTPStatusError):
        status = exc.response.status_code
        if status in _TEMPORARY_STATUSES:
            return TransientRequestError("Temporary MCP server failure")
        if status == 401:
            return AppError("AUTH_REQUIRED", "TradingView authorization is required")
        if status == 403:
            return AppError("MCP_PERMISSION_DENIED", "TradingView access is denied")
        return AppError("MCP_CONNECTION_ERROR", "MCP server rejected the request")
    if isinstance(exc, MCPError):
        if exc.code == _AUTH_HTTP:
            return AppError("AUTH_REQUIRED", "TradingView authorization is required")
        if exc.code == _CREDENTIAL_HTTP:
            return AppError("CREDENTIAL_STORE_ERROR", "Credential Store is unavailable")
        if exc.code == _CONNECTION_HTTP:
            return AppError("MCP_CONNECTION_ERROR", "MCP connection failed")
        if exc.code == _OAUTH_REGISTRATION:
            return AppError("MCP_OAUTH_REGISTRATION_ERROR", "OAuth client registration failed")
        if exc.code == _OAUTH_TOKEN:
            return AppError("MCP_OAUTH_TOKEN_ERROR", "OAuth token exchange failed")
        if exc.code == _OAUTH_FLOW:
            return AppError("MCP_OAUTH_FLOW_ERROR", "OAuth authorization flow failed")
        if exc.code == _TEMPORARY_HTTP:
            return TransientRequestError("Temporary MCP server failure")
        if exc.code == _PERMISSION_HTTP:
            return AppError("MCP_PERMISSION_DENIED", "TradingView access is denied")
        if exc.code == _ARGUMENT_HTTP:
            return AppError("MCP_ARGUMENT_ERROR", "MCP request arguments were rejected")
        if exc.code == METHOD_NOT_FOUND:
            return AppError("MCP_TOOL_UNAVAILABLE", "MCP tool is unavailable")
        if exc.code == INVALID_PARAMS:
            return AppError("MCP_ARGUMENT_ERROR", "MCP tool arguments were rejected")
        return AppError("MCP_CONNECTION_ERROR", "MCP protocol request failed")
    if isinstance(exc, (httpx2.TimeoutException, httpx2.NetworkError,
                        httpx2.RemoteProtocolError, ConnectionResetError, TimeoutError)):
        return TransientRequestError("Temporary MCP transport failure")
    if isinstance(exc, OAuthRegistrationError):
        return AppError("MCP_OAUTH_REGISTRATION_ERROR", "OAuth client registration failed")
    if isinstance(exc, OAuthTokenError):
        return AppError("MCP_OAUTH_TOKEN_ERROR", "OAuth token exchange failed")
    if isinstance(exc, OAuthFlowError):
        return AppError("MCP_OAUTH_FLOW_ERROR", "OAuth authorization flow failed")
    return AppError("MCP_CONNECTION_ERROR", "MCP connection failed")


def _error_response(request: httpx2.Request, code: int) -> httpx2.Response | None:
    try:
        request_id = json.loads(request.content).get("id")
    except (ValueError, UnicodeError, AttributeError):
        return None
    if request_id is None:
        return None
    return httpx2.Response(
        200,
        headers={"content-type": "application/json"},
        json={"jsonrpc": "2.0", "id": request_id,
              "error": {"code": code, "message": "MCP request failed"}},
        request=request,
    )


class ClassifyingTransport(httpx2.AsyncBaseTransport):
    """Preserve HTTP error class through the SDK's JSON-RPC error path."""

    def __init__(self, inner: httpx2.AsyncBaseTransport) -> None:
        self.inner = inner

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        # SDK-created auth requests bypass AsyncClient's default User-Agent header.
        request.headers.setdefault("User-Agent", APP_USER_AGENT)
        try:
            response = await self.inner.handle_async_request(request)
        except (httpx2.TimeoutException, httpx2.NetworkError, httpx2.RemoteProtocolError):
            if str(request.url).split("?", 1)[0] == ENDPOINT:
                replacement = _error_response(request, _TEMPORARY_HTTP)
                if replacement is not None:
                    return replacement
            raise
        if str(request.url).split("?", 1)[0] != ENDPOINT:
            return response
        status = response.status_code
        if status in _TEMPORARY_STATUSES:
            code = _TEMPORARY_HTTP
        elif status == 403 and "insufficient_scope" not in response.headers.get("www-authenticate", ""):
            code = _PERMISSION_HTTP
        elif status == 400:
            code = _ARGUMENT_HTTP
        else:
            return response
        replacement = _error_response(request, code)
        if replacement is None:
            return response
        await response.aclose()
        return replacement

    async def aclose(self) -> None:
        await self.inner.aclose()


class NoninteractiveTransport(httpx2.AsyncBaseTransport):
    """Allow saved-token refresh, never OAuth discovery or registration from MCP commands."""

    def __init__(self, inner: httpx2.AsyncBaseTransport, token_endpoint: str | None) -> None:
        self.inner = inner
        parsed = urlsplit(token_endpoint) if token_endpoint else None
        self.token_endpoint = token_endpoint if (
            parsed is not None and parsed.scheme == "https"
            and parsed.netloc == "www.tradingview.com" and parsed.fragment == ""
            and parsed.username is None and parsed.password is None
        ) else None

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        if str(request.url) != ENDPOINT and not (
            self.token_endpoint is not None
            and request.method == "POST"
            and str(request.url) == self.token_endpoint
        ):
            raise AppError("AUTH_REQUIRED", "TradingView authorization is required")
        return await self.inner.handle_async_request(request)

    async def aclose(self) -> None:
        await self.inner.aclose()


class SafeOAuthHTTPClient(httpx2.AsyncClient):
    """Keep SDK auth failures on its request/result path instead of tearing down transport tasks."""

    async def send(self, request: httpx2.Request, **kwargs: Any) -> httpx2.Response:
        try:
            return await super().send(request, **kwargs)
        except Exception as exc:
            if str(request.url).split("?", 1)[0] != ENDPOINT:
                raise
            mapped = _normalize_error(exc)
            if isinstance(mapped, TransientRequestError):
                code = _TEMPORARY_HTTP
            elif isinstance(mapped, AppError) and mapped.code == "AUTH_REQUIRED":
                code = _AUTH_HTTP
            elif isinstance(mapped, AppError) and mapped.code == "CREDENTIAL_STORE_ERROR":
                code = _CREDENTIAL_HTTP
            elif isinstance(mapped, AppError) and mapped.code == "MCP_PERMISSION_DENIED":
                code = _PERMISSION_HTTP
            elif isinstance(mapped, AppError) and mapped.code == "MCP_OAUTH_REGISTRATION_ERROR":
                code = _OAUTH_REGISTRATION
            elif isinstance(mapped, AppError) and mapped.code == "MCP_OAUTH_TOKEN_ERROR":
                code = _OAUTH_TOKEN
            elif isinstance(mapped, AppError) and mapped.code == "MCP_OAUTH_FLOW_ERROR":
                code = _OAUTH_FLOW
            else:
                code = _CONNECTION_HTTP
            replacement = _error_response(request, code)
            if replacement is None:
                raise
            return replacement


def _oauth_client_metadata(redirect_uri: str) -> OAuthClientMetadata:
    """Build native/public OAuth registration metadata for PKCE authorization."""
    return OAuthClientMetadata(
        client_name="TradingView MCP Support",
        redirect_uris=[redirect_uri],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        token_endpoint_auth_method="none",
    )


class TradingViewClient:
    """Own one authenticated Streamable HTTP MCP session per async context."""

    def __init__(
        self,
        *,
        governor: RequestGovernor | None = None,
        _storage: KeyringTokenStorage | None = None,
        _sdk_factory: Callable[..., Any] | None = None,
        _http_transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self.governor = governor or RequestGovernor()
        self._storage = _storage or KeyringTokenStorage()
        self._sdk_factory = _sdk_factory or (
            lambda transport, **kwargs: Client(transport, mode="auto", **kwargs)
        )
        self._http_transport = _http_transport
        self._stack: AsyncExitStack | None = None
        self._sdk: Any = None
        self._catalog: ToolCatalog | None = None

    async def __aenter__(self) -> Self:
        if self._sdk is not None:
            raise RuntimeError("TradingViewClient is already connected")
        token = await self._storage.get_tokens()
        client_info = await self._storage.get_client_info()
        if token is None or client_info is None or (not token.access_token and not token.refresh_token):
            raise AppError("AUTH_REQUIRED", "TradingView authorization is required")

        stack = AsyncExitStack()
        self._stack = stack
        stage = "oauth_setup"
        try:
            redirect_uri = f"http://127.0.0.1:{CALLBACK_PORT}{CALLBACK_PATH}"
            metadata = _oauth_client_metadata(redirect_uri)
            provider = OAuthClientProvider(
                ENDPOINT,
                metadata,
                self._storage,
                redirect_handler=noninteractive_redirect,
                callback_handler=noninteractive_callback,
            )
            saved_metadata = await self._storage.get_oauth_metadata()
            provider.context.oauth_metadata = saved_metadata
            provider.context.token_expiry_time = await self._storage.get_token_expiry()
            self._storage.metadata_source = lambda: provider.context.oauth_metadata

            # SDK exception text may contain callback state or response bodies.
            log_filter = _DropOAuthLogs()
            for logger_name in (
                "mcp.client.auth.oauth2", "mcp.client.streamable_http",
                "mcp.client.client", "client", "httpx2",
            ):
                sdk_logger = logging.getLogger(logger_name)
                sdk_logger.addFilter(log_filter)
                stack.callback(sdk_logger.removeFilter, log_filter)

            stage = "http_client"
            http_client = await stack.enter_async_context(
                SafeOAuthHTTPClient(
                    auth=provider,
                    timeout=httpx2.Timeout(30, read=300),
                    transport=NoninteractiveTransport(
                        ClassifyingTransport(self._http_transport or httpx2.AsyncHTTPTransport()),
                        str(saved_metadata.token_endpoint) if saved_metadata is not None else None,
                    ),
                )
            )
            transport = streamable_http_client(ENDPOINT, http_client=http_client)
            stage = "mcp_session"
            self._sdk = await stack.enter_async_context(self._sdk_factory(transport, cache=None))
            return self
        except BaseException as exc:
            await stack.aclose()
            self._stack = None
            self._sdk = None
            if not isinstance(exc, Exception):
                raise
            mapped = _normalize_error(exc)
            if (
                isinstance(mapped, AppError)
                and mapped.code == "MCP_CONNECTION_ERROR"
                and mapped.message == "MCP connection failed"
            ):
                names = ",".join(_exception_type_names(exc)[:4])
                mapped = AppError(
                    "MCP_CONNECTION_ERROR",
                    f"MCP connection failed during {stage} ({names})",
                )
            raise mapped from exc

    async def __aexit__(self, *_args: object) -> None:
        try:
            if self._stack is not None:
                await self._stack.aclose()
        finally:
            self._sdk = None
            self._stack = None
            self._catalog = None

    def _connected(self) -> Any:
        if self._sdk is None:
            raise RuntimeError("TradingViewClient requires an active async context")
        return self._sdk

    @property
    def protocol_version(self) -> str | None:
        return self._connected().protocol_version

    @property
    def server_info(self) -> dict[str, Any] | None:
        info = self._connected().server_info
        return info.model_dump(mode="json", by_alias=True) if info is not None else None

    async def list_tools(self) -> ToolCatalog:
        sdk = self._connected()
        cursor: str | None = None
        seen_cursors: set[str] = set()
        tools: dict[str, ToolInfo] = {}
        try:
            while True:
                async def fetch_page(page_cursor: str | None = cursor):
                    try:
                        return await sdk.list_tools(cursor=page_cursor)
                    except Exception as exc:
                        mapped = _normalize_error(exc)
                        if mapped is exc:
                            raise
                        raise mapped from exc

                page = await self.governor.execute(fetch_page)
                for tool in page.tools:
                    tools[tool.name] = ToolInfo(
                        name=tool.name,
                        title=tool.title,
                        description=tool.description,
                        input_schema=tool.input_schema,
                        expected=tool.name in EXPECTED_TOOLS,
                    )
                cursor = page.next_cursor
                if cursor is None:
                    break
                if cursor in seen_cursors:
                    raise AppError("MCP_SCHEMA_MISMATCH", "MCP tool pagination is invalid")
                seen_cursors.add(cursor)
        except Exception as exc:
            mapped = _normalize_error(exc)
            if mapped is exc:
                raise
            raise mapped from exc
        available = set(tools)
        self._catalog = ToolCatalog(
            tools=tuple(tools[name] for name in sorted(tools)),
            expected_missing=tuple(sorted(EXPECTED_TOOLS - available)),
            unexpected_available=tuple(sorted(available - EXPECTED_TOOLS)),
        )
        return self._catalog

    async def _call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        retry: bool = True,
        cache_key: Hashable | None = None,
    ) -> ToolCallData:
        sdk = self._connected()
        catalog = self._catalog or await self.list_tools()
        if name not in {tool.name for tool in catalog.tools}:
            raise AppError("MCP_TOOL_UNAVAILABLE", "MCP tool is unavailable")

        async def operation() -> ToolCallData:
            try:
                result = await sdk.call_tool(name, arguments)
            except Exception as exc:
                raise _normalize_error(exc) from exc
            if result.is_error:
                raise AppError("MCP_TOOL_ERROR", "MCP tool returned an error")
            return ToolCallData(
                structured_content=result.structured_content,
                content=[block.model_dump(mode="json", by_alias=True) for block in result.content],
            )

        return await self.governor.execute(
            operation,
            retry=retry,
            cache_key=cache_key if retry else None,
        )
