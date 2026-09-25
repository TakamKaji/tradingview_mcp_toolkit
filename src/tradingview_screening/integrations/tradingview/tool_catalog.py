"""TradingView logical tool names mapped to current MCP wire names.

The public Python wrapper names stay stable and provider-neutral-ish within this
integration. Tool discovery, availability checks, and MCP calls use the live
wire names returned by TradingView's server.
"""

TOOL_NAME_MAP = {
    # Watchlists
    "list_watchlists": "mcp-watchlist-list-watchlists",
    "get_watchlist": "mcp-watchlist-get-watchlist",
    "get_active_watchlist": "mcp-watchlist-get-active-watchlist",
    "create_watchlist": "mcp-watchlist-create-watchlist",
    "delete_watchlist": "mcp-watchlist-delete-watchlist",
    "add_to_watchlist": "mcp-watchlist-add-to-watchlist",
    "remove_from_watchlist": "mcp-watchlist-remove-from-watchlist",
    "update_watchlist": "mcp-watchlist-update-watchlist",
    # TradingView market / screener / news / fundamentals / documents / calendars / alerts
    "get_ohlcv": "mcp-tv-get-ohlcv",
    "get_economic_data": "mcp-tv-get-economic-data",
    "get_economic_symbols": "mcp-tv-get-economic-symbols",
    "search_symbols": "mcp-tv-search-symbols",
    "get_symbol_data": "mcp-tv-get-symbol-data",
    "run_screener": "mcp-tv-run-screener",
    "get_symbol_data_batch": "mcp-tv-get-symbol-data-batch",
    "get_screener_columns": "mcp-tv-get-screener-columns",
    "get_technicals_rating": "mcp-tv-get-technicals-rating",
    "get_news": "mcp-tv-get-news",
    "get_news_story": "mcp-tv-get-news-story",
    "get_forecasts": "mcp-tv-get-forecasts",
    "get_financials": "mcp-tv-get-financials",
    "get_financial_history": "mcp-tv-get-financial-history",
    "get_documents": "mcp-tv-get-documents",
    "get_document_view": "mcp-tv-get-document-view",
    "get_earnings_calendar": "mcp-tv-get-earnings-calendar",
    "get_economic_calendar": "mcp-tv-get-economic-calendar",
    "get_dividends_calendar": "mcp-tv-get-dividends-calendar",
    "create_alert": "mcp-tv-create-alert",
    "update_alert": "mcp-tv-update-alert",
    "delete_alert": "mcp-tv-delete-alert",
    "stop_alerts": "mcp-tv-stop-alerts",
    "restart_alerts": "mcp-tv-restart-alerts",
    "list_alerts": "mcp-tv-list-alerts",
    "get_alerts": "mcp-tv-get-alerts",
    "get_alerts_log": "mcp-tv-get-alerts-log",
}

LOGICAL_TOOL_NAMES = frozenset(TOOL_NAME_MAP)
EXPECTED_TOOLS = frozenset(TOOL_NAME_MAP.values())
