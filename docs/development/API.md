# 型付きAPIと通信境界

アプリからの操作入口は共通CLIです。Pythonから組み込む場合は既存の`TradingViewClient`とRequest modelを使います。[実装仕様13〜22節](tradingview_screening_system_spec.md#13-tradingviewclient-設計)が詳細な契約です。

## Read APIの例

保存済み認証が必要です。これは実MCPのReadを行う例であり、文書表示だけで自動実行するものではありません。

```python
from tradingview_screening.integrations.tradingview.client import TradingViewClient
from tradingview_screening.integrations.tradingview.schemas import RunScreenerRequest

async def example():
    async with TradingViewClient() as client:
        response = await client.run_screener(
            RunScreenerRequest(market="japan", symbolset=["TSE:7203"], limit=1)
        )
        return response.structured_content
```

公開asyncメソッド名は論理名です。`TOOL_NAME_MAP`が実サーバーのwire名（`mcp-tv-*` / `mcp-watchlist-*`）へ変換し、`_call_tool()`と共通`RequestGovernor`を通ります。Requestは必須・省略可・null許可を区別し、ResponseはPydanticで検証して`structured_content`と`content`を分離します。Providerの`success=false`をデータ取得成功として扱わず、本文をJSONへ推測変換しません。

## 35 Toolと安全境界

### OHLCVの日付範囲・形式（2026-10-27）

`GetOhlcvRequest`は`date_from`・`date_to`（有効なYYYY-MM-DD/時差付きRFC3339）と`format="rows"/"columns"`を受理します。両端を含む範囲内の新しい足からcount本まで取得し、返却順は実応答で検証します。count上限は形式省略/rowsで5000、columnsで8000。新引数の未指定は送信せず、明示Noneはstringとして不正です。日時文字列は変換せず送信します。既存の省略可nullableフィールドや追加応答の保持は変更しません。

```python
from tradingview_screening.integrations.tradingview.schemas import GetOhlcvRequest

async def read_window(client):
    return await client.get_ohlcv(GetOhlcvRequest(
        symbol="TSE:7203", interval="1D", count=3, summary=False,
        date_from="2026-10-05", date_to="2026-10-09", format="columns",
    ))
```

rows時の`bars`は足ごとの辞書配列、columns時は`t/o/h/l/c/v`の配列を持つ辞書として観測しました。`ObservedReadResponse.structured_content`はモデルなので、辞書で処理する場合は`response.model_dump(mode="json")["structured_content"]`を使います。`has_more/next_date_to`は追加フィールドとして保持しますが、自動ページングや保存機能の追加ではありません。Providerのsuccess=falseと不正な応答Schema、通信エラーを区別し、任意Toolの返却にsuccessキーがあるとは仮定しません（経済カレンダーではstatus/result）。

根拠・全35 Tool監査・未確認事項は[機能同等性監査](MCP_PARITY_AUDIT_2026-10-27.md)。PR #63の未マージ文書はこの作業へ取り込まず、同記録に後日の反映事項を記載します。

### 共通契約

[仕様書のTool一覧](tradingview_screening_system_spec.md#20-tradingview公式mcp-全35-toolラッパー)と[公式資料保存版](TRADINGVIEW_MCP_OFFICIAL_REFERENCE.md)を参照します。Watchlists 8、Market/Economic 3、Symbol 1、Screener 5、News 2、Fundamentals 3、Documents 2、Calendars 3、Alerts 8が実装対象です。Betaでの追加Toolを全体故障とせず、不足Toolは必要とする呼出しだけを失敗させます。

通常ReadはRetry対象ですが、Watchlist/Alert Writeは`retry=False`・cacheなしです。`get_active_watchlist`は分類上Readでもactivate/createの副作用があり、安全なRead-only確認には使いません。Webhook付きAlertの作成・更新など、Providerが未対応の操作をschema適合だけで成功保証しません。

共通Governorの既定は30要求/分、同時実行1、試行ごとTimeout 30秒、初回を含む最大3試行、Retry基本待機2秒、Cache TTL 60秒です。Cacheは呼出元が明示したキーに対する成功結果だけを対象にします。各ToolのPolicyとOAuth lifecycleは[仕様15〜17節](tradingview_screening_system_spec.md#15-requestgovernor)を確認してください。

Screening結果の取得は既存Engine、保存JSONは[Results](RESULTS.md)、Watchlist Write APIは[同期API](SCREENING_API.md)、Job/Taskは[Job契約](JOBS_SCHEDULER.md)へ接続します。直接MCPを呼ぶ別Engineや非公式TradingView APIは追加しません。

[開発索引](README.md)
