# TradingView公式MCPの参照先

公式資料の本文は再掲載せず、以下の公式URLを参照してください。本ページは本プロジェクト独自の実装上の要点だけを記載します。

- [TradingView公式MCP資料](https://www.tradingview.com/mcp/docs)
- 公式MCPの接続先：`https://mcp.tradingview.com/mcp`
- 本体の対応範囲：[Python API](API.md) / [利用者向け機能一覧](../user/FEATURES.md)

## 実装で確認すること

- Tool名とRequestの技術契約は`src/tradingview_screening/integrations/tradingview/`を参照します。公式Toolが存在することと、利用者CLIや定期Jobから呼べることは区別します。
- OAuthのdiscovery・PKCE・state・issuer・token交換はSDKを使います。認証情報や認可codeをログ・テストfixtureへ保存しません。
- Toolの型検査だけで実サービスの成功や利用権限を保証しません。未測定の応答項目やenumを推測で必須にしません。
- 上限付きの取得を全Universeの完全取得とは扱いません。全米株の条件なし取得はProvider制約により未対応で、対象Jobは無効です。
- Watchlist・Alertの変更は副作用を伴います。Read-only検証では変更Toolやactive切替を使いません。
- テストfixtureは機械的な入力契約に絞り、Providerの説明文や公式ページ全文を収録しません。構造・型・必須性・数値上限・列挙値を独立したテストデータとして検証します。

旧版の公式資料全文・生schema保存物は、公開候補から除去し、所有者のローカルbundleにのみ保管します。既存GitHub PR参照や第三者のコピーから消えたことを保証するものではありません。最新の仕様・利用条件は常に公式資料で確認してください。

## 旧リンクの入口

旧見出しへのリンクは以下のアンカーで受けます。転載していた説明本文は保持しません。

<a id="tradingview-mcp-server--setup-and-tools-reference"></a>
<a id="phase-9-read-only注記2026-09-27"></a>
<a id="phase-5-live-schema注記2026-09-25保存版本文より優先"></a>
<a id="phase-4-oauth調査注記2026-09-25公式本文とは別の実測"></a>
<a id="connect-tradingview-to-your-ai-assistant"></a>
<a id="claude--web-desktop-and-mobile"></a>
<a id="claude-code"></a>
<a id="chatgpt-and-codex-desktop-ui"></a>
<a id="chatgpt-and-codex-terminal"></a>
<a id="other-mcp-clients"></a>
<a id="watchlists"></a>
<a id="list_watchlists"></a>
<a id="get_watchlist"></a>
<a id="get_active_watchlist"></a>
<a id="create_watchlist"></a>
<a id="delete_watchlist"></a>
<a id="add_to_watchlist"></a>
<a id="remove_from_watchlist"></a>
<a id="update_watchlist"></a>
<a id="market-data"></a>
<a id="get_ohlcv"></a>
<a id="get_economic_data"></a>
<a id="get_economic_symbols"></a>
<a id="search"></a>
<a id="search_symbols"></a>
<a id="screener"></a>
<a id="get_symbol_data"></a>
<a id="run_screener"></a>
<a id="get_symbol_data_batch"></a>
<a id="get_screener_columns"></a>
<a id="get_technicals_rating"></a>
<a id="news"></a>
<a id="get_news"></a>
<a id="get_news_story"></a>
<a id="fundamentals--forecasts"></a>
<a id="get_forecasts"></a>
<a id="get_financials"></a>
<a id="get_financial_history"></a>
<a id="documents"></a>
<a id="get_documents"></a>
<a id="get_document_view"></a>
<a id="calendars"></a>
<a id="get_earnings_calendar"></a>
<a id="get_economic_calendar"></a>
<a id="get_dividends_calendar"></a>
<a id="alerts"></a>
<a id="create_alert"></a>
<a id="update_alert"></a>
<a id="delete_alert"></a>
<a id="stop_alerts"></a>
<a id="restart_alerts"></a>
<a id="list_alerts"></a>
<a id="get_alerts"></a>
<a id="get_alerts_log"></a>

[開発索引](README.md)
