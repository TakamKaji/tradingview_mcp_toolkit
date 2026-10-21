"""Observed TradingView Watchlist Tool response boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tradingview_screening.common.errors import AppError

from .client import TradingViewClient
from .schemas import (
    AddToWatchlistRequest,
    CreateWatchlistRequest,
    GetWatchlistRequest,
    RemoveFromWatchlistRequest,
    TypedToolResponse,
)


@dataclass(frozen=True, slots=True)
class WatchlistSnapshot:
    watchlist_id: str
    name: str
    symbols: tuple[str, ...]


def valid_watchlist_symbol(symbol: Any) -> bool:
    if not isinstance(symbol, str) or symbol.count(":") != 1:
        return False
    exchange, ticker = symbol.split(":", 1)
    return bool(exchange and ticker) and not any(character.isspace() for character in symbol)


def _structured(response: TypedToolResponse) -> dict[str, Any]:
    data = response.structured_content
    if not isinstance(data, dict):
        raise AppError("MCP_SCHEMA_MISMATCH", "Watchlist response has no structured data")
    if "success" in data and type(data["success"]) is not bool:
        raise AppError("MCP_SCHEMA_MISMATCH", "Watchlist response schema changed")
    if "error" in data and data["error"] is not None and not isinstance(data["error"], str):
        raise AppError("MCP_SCHEMA_MISMATCH", "Watchlist response schema changed")
    if data.get("success") is True and data.get("error"):
        raise AppError("MCP_SCHEMA_MISMATCH", "Watchlist response schema changed")
    if data.get("success") is False or data.get("error"):
        raise AppError("WATCHLIST_PROVIDER_ERROR", "TradingView Watchlist operation failed")
    return data


def normalize_watchlist(response: TypedToolResponse, *, requested_id: str | None = None) -> WatchlistSnapshot:
    """Parse the observed create/get `{watchlist:{id,name,symbols}}` shape."""
    watchlist = _structured(response).get("watchlist")
    if not isinstance(watchlist, dict):
        raise AppError("MCP_SCHEMA_MISMATCH", "Watchlist response schema changed")
    identifier = watchlist.get("id")
    name = watchlist.get("name")
    symbols = watchlist.get("symbols")
    if (
        type(identifier) is not int or identifier <= 0
        or not isinstance(name, str) or not name.strip()
        or not isinstance(symbols, list)
        or any(not valid_watchlist_symbol(symbol) for symbol in symbols)
    ):
        raise AppError("MCP_SCHEMA_MISMATCH", "Watchlist response schema changed")
    normalized_id = str(identifier)
    if requested_id is not None and normalized_id != requested_id:
        raise AppError("MCP_SCHEMA_MISMATCH", "Watchlist response ID changed")
    return WatchlistSnapshot(normalized_id, name, tuple(symbols))


def normalize_watchlist_mutation(response: TypedToolResponse, *, requested_id: str) -> None:
    """Validate the observed add/remove response without assuming `symbols` meaning."""
    data = _structured(response)
    symbols = data.get("symbols")
    if (
        data.get("watchlist_id") != requested_id
        or not isinstance(symbols, list)
        or any(not valid_watchlist_symbol(symbol) for symbol in symbols)
    ):
        raise AppError("MCP_SCHEMA_MISMATCH", "Watchlist mutation response schema changed")


async def create_managed_watchlist(client: TradingViewClient, name: str) -> WatchlistSnapshot:
    response = await client.create_watchlist(CreateWatchlistRequest(name=name, symbols=[]))
    return normalize_watchlist(response)


async def get_managed_watchlist(client: TradingViewClient, watchlist_id: str) -> WatchlistSnapshot:
    response = await client.get_watchlist(GetWatchlistRequest(watchlist_id=watchlist_id))
    return normalize_watchlist(response, requested_id=watchlist_id)


async def add_managed_symbols(
    client: TradingViewClient, watchlist_id: str, symbols: tuple[str, ...],
) -> None:
    response = await client.add_to_watchlist(
        AddToWatchlistRequest(watchlist_id=watchlist_id, symbols=list(symbols))
    )
    normalize_watchlist_mutation(response, requested_id=watchlist_id)


async def remove_managed_symbols(
    client: TradingViewClient, watchlist_id: str, symbols: tuple[str, ...],
) -> None:
    response = await client.remove_from_watchlist(
        RemoveFromWatchlistRequest(watchlist_id=watchlist_id, symbols=list(symbols))
    )
    normalize_watchlist_mutation(response, requested_id=watchlist_id)
