<!-- URL: https://www.tradingview.com/mcp/docs -->

# TradingView MCP Server — setup and tools reference

> Snapshot retained for implementation reference. Source URL: https://www.tradingview.com/mcp/docs
> Captured in project planning on 2026-09-18.
> Phase 4 verification: 2026-09-25. Current official docs retain the same endpoint, OAuth 2.1, Streamable HTTP, 35-tool catalog, and Essential-or-higher eligibility excluding trials. SDK integration details are recorded in the implementation specification §17.1; live account access and discovered schemas require a separate smoke test.

## Phase 4 OAuth調査注記（2026-09-25、公式本文とは別の実測）

- [path付きPRM](https://mcp.tradingview.com/.well-known/oauth-protected-resource/mcp) は200。resourceはMCP endpoint、authorization serverは `https://www.tradingview.com`。root PRMは404。
- [AS metadata](https://www.tradingview.com/.well-known/oauth-authorization-server) はauthorize/token/register endpointを広告。public client `none` とPKCE `S256` に対応し、CIMD対応fieldとresponse `iss` 対応fieldは未広告。
- 本アプリのnative/public metadataによる正規DCRは201。CIMD必須・事前登録必須という証拠は得られていない。
- SDK生成HTTP RequestのUser-Agent欠落でAS metadataが403となることを再現。自アプリ名のUser-Agent補完後、実SDKが正規DCRを経てredirect handlerへ到達した。ユーザー認可以降の実機確認は別途必要。
- [Codex登録実装](https://github.com/openai/codex/blob/main/codex-rs/rmcp-client/src/oauth_client_registration.rs) はMCPセッション外でmetadataを解決し、対応metadataとnative callback条件が揃えばCIMD、それ以外はDCRを選ぶ。これは公開実装の確認であり、ユーザーのDesktop接続で実際に選択された方式を証明するものではない。
- [Codex callback実装](https://github.com/openai/codex/blob/main/codex-rs/rmcp-client/src/oauth_callback.rs) はissuer応答を検証できる場合にshared `/callback`、それ以外はサーバー固有 `/callback/{id}` を用いる。本アプリは独自の単一TradingView callbackを維持し、Codexのclient identityを流用しない。

仕様根拠: [MCP Authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)、[Client Registration](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/client-registration)、[SDK OAuth](https://py.sdk.modelcontextprotocol.io/client/oauth-clients/)。

## Connect TradingView to your AI assistant

Use TradingView data and analytics inside Claude, ChatGPT and any MCP-compatible client through the official MCP server. Included in Essential and above; trial plans don’t include MCP access.

Server URL

https://mcp.tradingview.com/mcp

One URL for every client. Authentication is OAuth 2.1 — you sign in with your TradingView account, no API keys to manage.

## Claude — web, desktop and mobile

Web connectors are available on claude.ai and in the desktop and mobile apps; a connector added once works everywhere you use Claude.

1. Open Claude → Settings → Connectors
2. Click “Add custom connector”
3. Paste the server URL → Add
4. Authorize with your TradingView account

## Claude Code

1. Add the server in your terminal: `claude mcp add --transport http mcp-tradingview https://mcp.tradingview.com/mcp`
2. Run `/mcp` in Claude Code and authorize with your TradingView account in the browser

## ChatGPT and Codex desktop UI

1. Open ChatGPT → Settings → Plugins → Add → MCPs → Add → Add MCP Server
2. Set name to Tradingview Official MCP Server
3. Set Type to “Streamable HTTP”
4. Paste `https://mcp.tradingview.com/mcp` as URL
5. Hit “Save”
6. Open Plugins → MCPs
7. Hit “Authenticate” on “Tradingview Official MCP Server”
8. Authorise in paid TradingView account if prompted
9. Allow the access for the tools

## ChatGPT and Codex terminal

1. Add the server in your terminal: `codex mcp add tradingview --url https://mcp.tradingview.com/mcp`
2. Authorize with your TradingView account in the browser
3. Start a new Codex task and ask it to use TradingView

## Other MCP clients

Any client that supports MCP over streamable HTTP with OAuth 2.1 authorization works: point it at the server URL and complete the sign-in when prompted. A typical JSON configuration:

`"mcpServers": { "tradingview": { "type": "http", "url": "https://mcp.tradingview.com/mcp" } }`

TradingView data and platform operations, exposed as MCP tools. Your assistant picks the right tool for the question — you just ask in plain language.

Tool calls are rate-limited to ~100 requests per minute per user.

* [Watchlists8](#watchlists)
* [Market data3](#market-data)
* [Symbol search1](#search)
* [Screener5](#screener)
* [News2](#news)
* [Fundamentals & forecasts3](#fundamentals)
* [Documents2](#documents)
* [Calendars3](#calendars)
* [Alerts8](#alerts)

The toolset is in beta and expands over time — ask your assistant to list the available TradingView tools to see the current set.

Read-only tools never modify the account; Write tools create, change or delete user data.

## Watchlists

### `list_watchlists`

Read-only

List the user's watchlists.

No parameters.

### `get_watchlist`

Read-only

Get a watchlist data with its companies by id.

- `watchlist_id` string required — Numeric id of the watchlist

### `get_active_watchlist`

Read-only

Get the active watchlist with its companies. If no watchlist is active, the first custom one is activated; if the user has no watchlists at all, a default one is created.

No parameters.

### `create_watchlist`

Write

Create a new watchlist.

- `name` string — Optional name of the new watchlist (max 500 chars)
- `symbols` string[] — Optional initial symbols in EXCHANGE:TICKER format, e.g. NASDAQ:AAPL

### `delete_watchlist`

Write

Delete a watchlist.

- `watchlist_id` string required — Numeric id of the watchlist

### `add_to_watchlist`

Write

Add symbols to a watchlist. A symbol already present in the watchlist is moved to the end.

- `watchlist_id` string required — Numeric id of the watchlist
- `symbols` string[] required — Symbols in EXCHANGE:TICKER format, e.g. NASDAQ:AAPL

### `remove_from_watchlist`

Write

Remove companies from a watchlist.

- `watchlist_id` string required — Numeric id of the watchlist
- `symbols` string[] required — Symbols in EXCHANGE:TICKER format, e.g. NASDAQ:AAPL

### `update_watchlist`

Write

Update an existing watchlist: change its name and/or description. At least one of name / description must be provided.

- `watchlist_id` string required — Numeric id of the watchlist
- `name` string — New name of the watchlist (max 500 chars)
- `description` string — New description text for the watchlist

## Market data

### `get_ohlcv`

Read-only

Fetch historical OHLCV bars for a symbol at an interval. Returns aggregate summary and (unless summary=true) the raw bars `[{t (unix sec UTC), o, h, l, c, v}]`.

- `symbol` string required — Symbol in EXCHANGE:TICKER format, e.g. NASDAQ:NVDA or BINANCE:BTCUSDT
- `interval` string — Options: `1m 5m 15m 30m 1h 4h 1D 1W M`, default `1D`
- `count` integer — Number of bars, max 5000, default 300
- `summary` boolean — If true, omit the raw bars array and return aggregate statistics only

### `get_economic_data`

Read-only

Time series for an economic indicator (e.g. ECONOMICS:USIRYY): `[{date, value}]` where value is the actual release value, plus unit/scale when available. Tickers are ECONOMICS:<COUNTRY><INDICATOR>; use get_economic_symbols to discover the available countries and indicator codes instead of guessing.

- `symbol` string required — Economic ticker ECONOMICS:<COUNTRY><INDICATOR>, e.g. ECONOMICS:USIRYY
- `date_from` string — ISO date, start of the series window (inclusive)
- `date_to` string — ISO date, end of the series window (inclusive)

### `get_economic_symbols`

Read-only

Catalog of economic tickers accepted by get_economic_data. Without arguments returns a compact overview: indicator categories with counts plus every country code. Pass category or search for indicator codes and names; add country to get ready-to-use tickers.

- `country` string — Two-letter country/region code, e.g. US, DE, EU, CN
- `category` string — Options: `gdp lbr prce hlth mny trd gov bsnss cnsm hse txs enrg clmt`
- `search` string — Indicator code/name substring search

## Search

### `search_symbols`

Read-only

Resolve a ticker or company name into routable EXCHANGE:TICKER symbols via fuzzy search. Returns symbol, description, type, exchange, logoid.

- `query` string required — Ticker, company name or description to fuzzy-search
- `type_filter` string — Options: `stock etf bond forex index futures crypto`, default all

## Screener

### `get_symbol_data`

Read-only

Fetch arbitrary TradingView screener columns for one symbol. Use get_screener_columns to discover valid column names.

- `symbol` string required
- `columns` string[] — TradingView screener columns to fetch
- Default columns: `name description close change change_abs volume market_cap_basic price_earnings_ttm sector industry`

### `run_screener`

Read-only

Run the TradingView screener with filters (`{field: [min, max]}` plus index/sector/industry/analyst_rating), sorting, presets and column selection. Returns rows and totalCount. Use get_screener_columns to discover valid column names for columns and filters.

- `market` string — Screener market: america, crypto, forex, futures, bonds, cfd, uk, germany, india, japan, …; default `america`
- `filters` object — Filters as `{field: [min, max]}` with null side = unbounded, plus special keys index / sector / industry / analyst_rating
- `sort_by` string — Column to sort by, default `volume`
- `sort_order` string — `asc` or `desc`, default `desc`
- `limit` integer — Max rows, cap 1000, default 100
- `columns` string[] — Screener columns to return
- `symbol_types` string[] — Instrument types to include, e.g. `["stock"]`
- `filter_preset` string — Options: `pullback_with_reversal breakout_with_volume oversold_healthy earnings_runup relative_strength new_highs`
- `symbolset` string[] — Explicit symbol universe, e.g. `["SYML:SP;SPX"]`

### `get_symbol_data_batch`

Read-only

Quotes/columns for up to 50 symbols in one call; unresolved symbols are reported in `missing` instead of fabricated zeros. Use get_screener_columns to discover valid column names.

- `symbols` string[] required — Symbols in EXCHANGE:TICKER format, up to 50, deduplicated
- `columns` string[] — TradingView screener columns to fetch
- Default columns: `name description close change change_abs volume market_cap_basic price_earnings_ttm sector industry`

### `get_screener_columns`

Read-only

Catalog of all TradingView screener column names accepted by get_symbol_data, get_symbol_data_batch and run_screener. Without group/search returns a compact overview: groups with column names only. Pass group or search to get descriptions and period/timeframe variants; market narrows the catalog.

- `market` string — Options: `stock etf crypto bond all`, default `all`
- `group` string — Return full details for one group, e.g. valuation, technicals, income_statement
- `search` string — Return details for matching columns, e.g. margin

### `get_technicals_rating`

Read-only

Full single-timeframe indicator snapshot: RSI, Stoch K/D, CCI20, ADX, MACD, Momentum, AO, EMA/SMA 10-200, VWMA, HullMA9 plus 3 Recommend aggregates (summary/MA/other).

- `symbol` string required
- `interval` string — Options: `1m 5m 15m 30m 1h 2h 4h 1D 1W 1M`, default `1D`

## News

### `get_news`

Read-only

Latest news headlines for a symbol: id, title, published, provider, urgency, storyPath, link, permission, relatedSymbols, paywall. Paginated and can expose up to 200 total.

- `symbol` string required
- `lang` string — Supported language code, default `en`
- `limit` integer — Max headlines per call, cap 200, default 25
- `offset` integer — Pagination offset

### `get_news_story`

Read-only

Full text of a news story by id from get_news: ast_description, short_description, summary, permission, provider, copyright.

- `id` string required — Story id from get_news
- `lang` string — default `en`
- `user_prostatus` string — `pro` or `non_pro`, default `non_pro`
- `user_country` string — ISO country code

## Fundamentals & forecasts

### `get_forecasts`

Read-only

Analyst consensus: recommendation + score, buy/hold/sell distribution, price targets with upside_pct, EPS/revenue estimates.

- `symbol` string required

### `get_financials`

Read-only

Current fundamental snapshot: P/E, P/B, margins, ROE/ROA, TTM revenue/income/EBITDA/FCF and YoY growth. Optional metric subset and reporting period.

- `symbol` string required
- `metric` string[] — Optional subset of financial metrics
- `period` string — Options: `fy fq ttm fh current`, default `ttm`

### `get_financial_history`

Read-only

Quarterly/annual history of fundamentals with yoy_pct and period labels.

- `symbol` string required
- `period` string — `fq` or `fy`, default `fq`
- `date_from` string — ISO start date
- `date_to` string — ISO end date

## Documents

### `get_documents`

Read-only

List filings and transcripts for a symbol with view ids for get_document_view. Supports category/event filters and historical event-date windows.

- `symbol` string required
- `category` string — Options: `all annual_reports quarterly_reports interim_reports company_events insider_transactions transcripts presentations press_releases other`; also accepts 10-K / 10-Q / 8-K aliases
- `event` string — Options: `earning corporate_event`
- `start_date` string — RFC3339 start date
- `end_date` string — RFC3339 end date
- `limit` integer — default 20

### `get_document_view`

Read-only

Text of a specific document view by views[].id from get_documents. Never construct view ids manually.

- `view_id` string required

## Calendars

### `get_earnings_calendar`

Read-only

Future/past earnings dates for a list of symbols with EPS and revenue consensus forecasts.

- `symbols` string[] required
- `date_from` string — ISO date, default today
- `date_to` string — ISO date, default +180d

### `get_economic_calendar`

Read-only

Macro events filtered by countries, currencies, category and importance. Past windows work from 2003-09-01; forward approximately 31 days.

- `countries` string — default `US`
- `currencies` string — comma-separated ISO currencies
- `category` string — Options: `gdp bonds business consumer goverment health housing labor money prices trade taxes`, default all
- `date_from` string — default today 00:00 UTC
- `date_to` string — default today 23:59 UTC
- `min_importance` integer — `-1` all, `0` medium+high, `1` high only; default `-1`

### `get_dividends_calendar`

Read-only

Dividend data: ex-dates, amount, yield, payment date. Per-symbol mode via symbols[] or market screening mode via date window.

- `symbols` string[] — Per-symbol mode
- `market` string — Market screening mode
- `date_from` string — default now
- `date_to` string — default +30d
- `limit` integer — cap 200, default 50

## Alerts

### `create_alert`

Write

Create a TradingView alert with a simple price condition. Returns the created alert payload with alert_id.

- `symbol` string required
- `price` number
- `condition` string — Options: `cross cross_up cross_down greater less`, default `cross`
- `message` string — max 4000 chars
- `name` string — max 300 chars
- `resolution` string — default `1`
- `expiration` string — default now+30d
- `auto_deactivate` boolean — default false
- `email` boolean — default false
- `mobile_push` boolean — default true
- `popup` boolean — default true
- `webhook` string — webhook URL; requires supported plan and 2FA
- `monitor` boolean — opt-in monitoring webhook for LLM analysis on fire

### `update_alert`

Write

Update settings of an existing alert and reactivate it. Conditions/symbol/timeframe cannot be changed — delete and create instead.

- `alert_id` integer required
- `message` string
- `name` string
- `expiration` string
- `auto_deactivate` boolean
- `email` boolean
- `mobile_push` boolean
- `popup` boolean
- `webhook` string

### `delete_alert`

Write

Delete alerts by ids; their fire history is deleted too.

- `alert_ids` integer[] required

### `stop_alerts`

Write

Pause alerts without deleting them.

- `alert_ids` integer[] required

### `restart_alerts`

Write

Resume paused alerts without recreating them.

- `alert_ids` integer[] required

### `list_alerts`

Read-only

List all user alerts in normalized form.

- `symbol` string — Optional EXCHANGE:TICKER filter
- `active` boolean — Optional active state filter

### `get_alerts`

Read-only

Full payload of specific alerts by id including raw conditions. Message and webhook URL fields are filtered out; a has_webhook flag is returned instead.

- `alert_ids` integer[] required

### `get_alerts_log`

Read-only

Alert fire history with symbol, message and webhook delivery status.

- `days` integer — Look-back window, default 7
- `symbol` string — Optional symbol filter
- `limit` integer — cap 2000, default 100

---

The toolset is in beta and expands over time — ask your assistant to list the available TradingView tools to see the current set.

Read-only tools never modify the account; Write tools create, change or delete user data.

TradingView MCP Server is in beta. MCP access is included in Essential and above.
