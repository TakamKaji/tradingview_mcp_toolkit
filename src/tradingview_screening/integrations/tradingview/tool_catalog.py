"""Expected public-beta tool names; wrappers are added in Phase 5."""

EXPECTED_TOOLS = frozenset(
    (
        "list_watchlists", "get_watchlist", "get_active_watchlist", "create_watchlist",
        "delete_watchlist", "add_to_watchlist", "remove_from_watchlist", "update_watchlist",
        "get_ohlcv", "get_economic_data", "get_economic_symbols", "search_symbols",
        "get_symbol_data", "run_screener", "get_symbol_data_batch", "get_screener_columns",
        "get_technicals_rating", "get_news", "get_news_story", "get_forecasts",
        "get_financials", "get_financial_history", "get_documents", "get_document_view",
        "get_earnings_calendar", "get_economic_calendar", "get_dividends_calendar",
        "create_alert", "update_alert", "delete_alert", "stop_alerts", "restart_alerts",
        "list_alerts", "get_alerts", "get_alerts_log",
    )
)
