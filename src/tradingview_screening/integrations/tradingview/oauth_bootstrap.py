"""Complete SDK OAuth without opening an MCP session or consuming its event stream."""

from __future__ import annotations

import logging
import os
from contextlib import AsyncExitStack
from urllib.parse import urlsplit

import httpx2
from mcp.client.auth import (
    OAuthClientProvider,
    OAuthFlowError,
    OAuthRegistrationError,
    OAuthTokenError,
)
from mcp.client.auth.utils import (
    build_oauth_authorization_server_metadata_discovery_urls,
    build_protected_resource_metadata_discovery_urls,
    handle_auth_metadata_response,
    handle_protected_resource_response,
    is_valid_client_metadata_url,
    validate_metadata_issuer,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthMetadata, ProtectedResourceMetadata

from tradingview_screening.common.errors import AppError

from .auth import (
    ContainerCallback,
    KeyringTokenStorage,
    LoopbackCallback,
    auth_mode,
    create_token_storage,
)
from .client import APP_USER_AGENT, ENDPOINT, _DropOAuthLogs, _oauth_client_metadata

_ISSUER = "https://www.tradingview.com"
_CIMD_ENV = "TRADINGVIEW_MCP_CLIENT_METADATA_URL"
_CLIENT_ID_ENV = "TRADINGVIEW_MCP_CLIENT_ID"
_LOGGERS = ("mcp.client.auth.oauth2", "mcp.client.streamable_http", "mcp.client.client", "client", "httpx2")


class _FreshAuthorizationStorage:
    """Reuse a client registration while requiring a new authorization and token save."""

    def __init__(self, storage: KeyringTokenStorage, *, reuse_client_info: bool) -> None:
        self.storage = storage
        self.reuse_client_info = reuse_client_info
        self.token_saved = False

    async def get_tokens(self):
        return None

    async def set_tokens(self, tokens):
        await self.storage.set_tokens(tokens)
        self.token_saved = True

    async def get_client_info(self):
        return await self.storage.get_client_info() if self.reuse_client_info else None

    async def set_client_info(self, info):
        await self.storage.set_client_info(info)

    async def get_oauth_metadata(self):
        return await self.storage.get_oauth_metadata()

    async def set_oauth_metadata(self, metadata):
        await self.storage.set_oauth_metadata(metadata)


def _safe_https(url: str, origin: str | None = None) -> bool:
    parsed = urlsplit(url)
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and parsed.fragment == ""
        and (origin is None or f"{parsed.scheme}://{parsed.netloc}" == origin)
    )


async def _discover(client: httpx2.AsyncClient) -> tuple[ProtectedResourceMetadata, OAuthMetadata]:
    try:
        challenge = await client.get(ENDPOINT, headers={"Accept": "application/json, text/event-stream"})
        if challenge.status_code != 401:
            raise AppError("MCP_OAUTH_DISCOVERY_ERROR", "MCP authorization challenge is unavailable")
        challenge_url = None
        # The SDK helper parses the challenge safely and gives its URL discovery order.
        from mcp.client.auth.utils import extract_resource_metadata_from_www_auth

        challenge_url = extract_resource_metadata_from_www_auth(challenge)
        prm = None
        for url in build_protected_resource_metadata_discovery_urls(challenge_url, ENDPOINT):
            if not _safe_https(url, "https://mcp.tradingview.com"):
                raise AppError("MCP_OAUTH_DISCOVERY_ERROR", "OAuth resource metadata URL is invalid")
            response = await client.get(url)
            prm = await handle_protected_resource_response(response)
            if prm is not None:
                break
            if response.status_code not in (404,):
                raise AppError("MCP_OAUTH_DISCOVERY_ERROR", "OAuth resource metadata discovery failed")
        if prm is None or str(prm.resource) != ENDPOINT:
            raise AppError("MCP_OAUTH_DISCOVERY_ERROR", "OAuth resource metadata is invalid")
        if len(prm.authorization_servers) != 1 or str(prm.authorization_servers[0]).rstrip("/") != _ISSUER:
            raise AppError("MCP_OAUTH_DISCOVERY_ERROR", "OAuth authorization server is unexpected")

        asm = None
        for url in build_oauth_authorization_server_metadata_discovery_urls(_ISSUER, ENDPOINT):
            if not _safe_https(url, _ISSUER):
                raise AppError("MCP_OAUTH_DISCOVERY_ERROR", "OAuth server metadata URL is invalid")
            response = await client.get(url)
            ok, asm = await handle_auth_metadata_response(response)
            if asm is not None:
                break
            if not ok:
                raise AppError("MCP_OAUTH_DISCOVERY_ERROR", "OAuth server metadata discovery failed")
        if asm is None:
            raise AppError("MCP_OAUTH_DISCOVERY_ERROR", "OAuth server metadata is unavailable")
        validate_metadata_issuer(asm, _ISSUER)
        for endpoint in (asm.authorization_endpoint, asm.token_endpoint):
            if not _safe_https(str(endpoint), _ISSUER):
                raise AppError("MCP_OAUTH_DISCOVERY_ERROR", "OAuth server endpoint is invalid")
        if asm.registration_endpoint is not None and not _safe_https(str(asm.registration_endpoint), _ISSUER):
            raise AppError("MCP_OAUTH_DISCOVERY_ERROR", "OAuth registration endpoint is invalid")
        if "code" not in asm.response_types_supported:
            raise AppError("MCP_OAUTH_DISCOVERY_ERROR", "OAuth authorization code is unsupported")
        if asm.code_challenge_methods_supported is None or "S256" not in asm.code_challenge_methods_supported:
            raise AppError("MCP_OAUTH_DISCOVERY_ERROR", "OAuth PKCE S256 is unsupported")
        if asm.token_endpoint_auth_methods_supported is None or "none" not in asm.token_endpoint_auth_methods_supported:
            raise AppError("MCP_OAUTH_DISCOVERY_ERROR", "OAuth public client is unsupported")
        return prm, asm
    except AppError:
        raise
    except Exception as exc:
        raise AppError("MCP_OAUTH_DISCOVERY_ERROR", "OAuth metadata discovery failed") from exc


def _strategy(asm: OAuthMetadata, client_id: str | None, cimd_url: str | None) -> str:
    if client_id is not None:
        if not client_id.strip() or "://" in client_id:
            raise AppError("MCP_OAUTH_CLIENT_REGISTRATION_UNAVAILABLE", "Configured OAuth client ID is invalid")
        return "pre_registered"
    if cimd_url:
        host = urlsplit(cimd_url).hostname
        if (
            not is_valid_client_metadata_url(cimd_url)
            or not _safe_https(cimd_url)
            or host is None
            or host in {"chatgpt.com", "openai.com"}
            or host.endswith((".chatgpt.com", ".openai.com"))
        ):
            raise AppError("MCP_OAUTH_CLIENT_REGISTRATION_UNAVAILABLE", "Configured client metadata URL is invalid")
        if asm.client_id_metadata_document_supported is True:
            return "cimd"
    if asm.registration_endpoint is not None:
        return "dcr"
    raise AppError(
        "MCP_OAUTH_CLIENT_REGISTRATION_UNAVAILABLE",
        "OAuth client registration is unavailable",
    )


async def bootstrap_oauth(
    *,
    _storage: KeyringTokenStorage | None = None,
    _http_transport: httpx2.AsyncBaseTransport | None = None,
    _callback: LoopbackCallback | None = None,
    _client_id: str | None = None,
    _client_metadata_url: str | None = None,
) -> None:
    """Run the public SDK authorization flow and stop after durable token storage."""
    storage = _storage or create_token_storage()
    client_id = _client_id if _client_id is not None else os.environ.get(_CLIENT_ID_ENV)
    cimd_url = _client_metadata_url if _client_metadata_url is not None else os.environ.get(_CIMD_ENV)
    async with AsyncExitStack() as stack:
        log_filter = _DropOAuthLogs()
        for name in _LOGGERS:
            logger = logging.getLogger(name)
            logger.addFilter(log_filter)
            stack.callback(logger.removeFilter, log_filter)
        callback_type = ContainerCallback if auth_mode() == "container" else LoopbackCallback
        callback = _callback or await stack.enter_async_context(callback_type())
        client = await stack.enter_async_context(httpx2.AsyncClient(
            timeout=httpx2.Timeout(30), transport=_http_transport,
            headers={"User-Agent": APP_USER_AGENT},
        ))
        prm, asm = await _discover(client)
        saved_client_info = await storage.get_client_info()
        reuse_client_info = (
            saved_client_info is not None and saved_client_info.issuer == _ISSUER
            and client_id is None and cimd_url is None
        )
        strategy = "stored" if reuse_client_info else _strategy(asm, client_id, cimd_url)
        if strategy == "pre_registered":
            await storage.set_client_info(OAuthClientInformationFull(
                client_id=client_id, token_endpoint_auth_method="none", issuer=_ISSUER,
                redirect_uris=[callback.redirect_uri],
            ))
        fresh_storage = _FreshAuthorizationStorage(
            storage, reuse_client_info=reuse_client_info or strategy == "pre_registered"
        )
        provider = OAuthClientProvider(
            ENDPOINT, _oauth_client_metadata(callback.redirect_uri), fresh_storage,
            redirect_handler=callback.redirect, callback_handler=callback.callback,
            client_metadata_url=cimd_url if strategy == "cimd" else None,
        )
        provider.context.oauth_metadata = await storage.get_oauth_metadata()
        provider.context.token_expiry_time = None
        storage.metadata_source = lambda: provider.context.oauth_metadata
        request = httpx2.Request("GET", ENDPOINT, headers={"Accept": "application/json, text/event-stream"})
        flow = provider.async_auth_flow(request)
        stage = "flow"
        try:
            outgoing = await flow.__anext__()
            while True:
                url = str(outgoing.url)
                if outgoing is request and outgoing.headers.get("authorization", "").startswith("Bearer "):
                    if not fresh_storage.token_saved:
                        raise AppError("MCP_OAUTH_TOKEN_ERROR", "OAuth token was not saved")
                    return
                # SDK-authored Request objects do not inherit AsyncClient's User-Agent.
                outgoing.headers.setdefault("User-Agent", APP_USER_AGENT)
                if outgoing.method == "POST" and url == str(asm.registration_endpoint):
                    stage = "registration"
                elif outgoing.method == "POST" and url == str(asm.token_endpoint):
                    stage = "token"
                elif outgoing.method == "GET" and url == ENDPOINT:
                    stage = "flow"
                elif outgoing.method == "GET" and url in (
                    *build_protected_resource_metadata_discovery_urls(None, ENDPOINT),
                    *build_oauth_authorization_server_metadata_discovery_urls(_ISSUER, ENDPOINT),
                ):
                    stage = "discovery"
                else:
                    raise AppError("MCP_OAUTH_DISCOVERY_ERROR", "Unexpected OAuth request destination")
                if stage == "registration" and strategy != "dcr":
                    raise AppError("MCP_OAUTH_CLIENT_REGISTRATION_UNAVAILABLE", "OAuth registration was not selected")
                try:
                    response = await client.send(outgoing, follow_redirects=False)
                except AppError:
                    raise
                except Exception as exc:
                    code = {
                        "discovery": "MCP_OAUTH_DISCOVERY_ERROR",
                        "registration": "MCP_OAUTH_REGISTRATION_ERROR",
                        "token": "MCP_OAUTH_TOKEN_ERROR",
                        "flow": "MCP_OAUTH_FLOW_ERROR",
                    }[stage]
                    raise AppError(code, "OAuth request failed") from exc
                if stage == "discovery" and response.status_code != 200:
                    raise AppError("MCP_OAUTH_DISCOVERY_ERROR", "OAuth metadata discovery failed")
                if stage == "discovery":
                    try:
                        if url in build_oauth_authorization_server_metadata_discovery_urls(_ISSUER, ENDPOINT):
                            candidate = OAuthMetadata.model_validate_json(await response.aread())
                            if candidate.model_dump(mode="json") != asm.model_dump(mode="json"):
                                raise ValueError("authorization server changed")
                        else:
                            candidate_prm = ProtectedResourceMetadata.model_validate_json(await response.aread())
                            if candidate_prm.model_dump(mode="json") != prm.model_dump(mode="json"):
                                raise ValueError("protected resource changed")
                    except (ValueError, TypeError) as exc:
                        raise AppError("MCP_OAUTH_DISCOVERY_ERROR", "OAuth metadata changed during authorization") from exc
                outgoing = await flow.asend(response)
        except StopAsyncIteration as exc:
            raise AppError("MCP_OAUTH_FLOW_ERROR", "OAuth authorization ended without a token") from exc
        except AppError:
            raise
        except OAuthRegistrationError as exc:
            raise AppError("MCP_OAUTH_REGISTRATION_ERROR", "OAuth client registration failed") from exc
        except OAuthTokenError as exc:
            raise AppError("MCP_OAUTH_TOKEN_ERROR", "OAuth token exchange failed") from exc
        except OAuthFlowError as exc:
            raise AppError("MCP_OAUTH_FLOW_ERROR", "OAuth authorization flow failed") from exc
        except Exception as exc:
            raise AppError("MCP_OAUTH_FLOW_ERROR", "OAuth authorization failed") from exc
        finally:
            await flow.aclose()
