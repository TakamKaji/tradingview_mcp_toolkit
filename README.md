# TradingView MCP Support

**日本語** | [English](README.en.md)

TradingView公式MCPを使い、**自分で設定した条件で銘柄をスクリーニングし、結果を保存・比較できる**ローカルCLIツールです。条件や実行時刻はJSONで変更できます。

> **非公式ツールです。** TradingView社の公式製品ではなく、提携・承認を受けたものでもありません。

## できること

| 機能 | 概要 |
| --- | --- |
| スクリーニング | 日本株・米国株など、JSONで指定した市場・条件・取得列で検索 |
| 結果の管理 | JSON保存、最新結果・履歴の表示、同条件での前回比較 |
| Job | 複数の操作を設定ファイルで管理して手動実行 |
| Watchlist同期 | 管理対象Watchlistへ銘柄を追加・削除（**書き込み操作**） |
| 定期実行 | Windows Task Schedulerに日次Jobを登録（Windowsネイティブのみ） |

TradingView公式MCPの**35 Toolに対応するPythonラッパー**もあります。ただし、すべてをCLIから直接実行できるわけではありません。OHLCV・ニュース・財務などの専用CLIや定期取得Jobは未実装です（[機能の対応範囲](docs/user/FEATURES.md)）。

## まず使ってみる

必要なものは、インターネット接続と[TradingView公式MCPを利用できるプラン](https://www.tradingview.com/mcp/docs)です。ホストPCへのPythonの事前インストールは不要です。

[GitHubのmainブランチ](https://github.com/TakamKaji/tradingview_mcp_support)で **Code → Download ZIP** から取得し、ZIPを展開してください。GitHub Releaseが公開された場合は、その**Source code (zip)**も利用できます。

### Windows（ネイティブ）

1. Windows 64-bit環境で、展開フォルダ内の **`setup.bat` をダブルクリック**します。管理者権限は不要です。
2. 画面の案内に従ってTradingViewのOAuth認証を完了します。
3. 展開フォルダのエクスプローラーのアドレス欄に`cmd`と入力し、以下を実行します。

```bat
app.bat run public_sample_screen_daily
app.bat results latest sample_standard_screen
```

このJobは**Read-only＋ローカル保存**のサンプルです。Windowsでは結果を展開先の`results/`に保存します。

[Windowsの詳しい導入手順](docs/user/WINDOWS_SETUP.md)

### Docker（Windows・macOSなど）

Docker Desktop等とDocker Composeが必要です。展開フォルダのターミナルで実行します。

```sh
docker compose -f compose.docker.yml build app
docker compose -f compose.docker.yml run --rm app --version
docker compose -f compose.docker.yml run --rm --service-ports app mcp auth
```

認証コマンド実行中に、表示される案内に従ってホストのブラウザから`http://127.0.0.1:8765/oauth/authorize`を開きます。認証後、以下で読み取りと保存結果を確認できます。

```sh
docker compose -f compose.docker.yml run --rm app screen public_japan_value
docker compose -f compose.docker.yml run --rm app results latest public_japan_value
```

コンテナの結果・認証情報は**Docker volume**に保存されます。`mac.command`はmacOS向けの補助起動ファイルですが、Docker構成自体はMac専用ではありません。Windows Docker Desktop／Linux amd64で実OAuth・取得・永続化を確認済みで、Mac実機・arm64は未検証です。

[Dockerの認証・保存先・トラブル対応](docs/user/DOCKER.md)

## AIとの会話からScreeningを作る

ChatGPT・Codexに[AIによるScreening生成ガイド](docs/user/AI_JSON_GUIDE.md)と実仕様・Schema・サンプルを読ませ、希望を自然な言葉で伝えます。AIは次の2方式から選択します。

- **方式A（最優先）：標準Screening JSON。** 単一Screeningで表現できる条件は`screenings/*.json`を作り、Jobが必要な場合だけ`jobs/*.json`も作ります。簡単な条件にPythonやBATは不要です。
- **方式B：高度な複合Python処理。** ランキング確定後の別時間足判定、外部母集団との照合など、単一JSONで表現できない処理だけ選び、理由を説明します。既存の公式MCPクライアント・認証・通信制御・保存・Watchlist安全機構を可能な範囲で再利用します。汎用pipelineエンジンや専用CLIは未実装です。

**一般ユーザーはGitやCodexをインストールする必要はありません。** ChatGPTは完成ファイルと保存手順を提供し、Codexはアクセス可能なローカル環境への保存・検証まで対応します。Python方式は編集・検証できる実行環境が必要です。取得制限・欠損・未確認事項を明示し、不完全な取得を全件と扱いません。ファイル作成と実取得は別操作です。明示依頼なしにTradingViewへの実書き込みやScheduler登録を実行せず、初期はWatchlist同期・定期登録を無効にします。

## 自分のスクリーニング・Jobを作る

1. `screenings/public_japan_value.json`を`screenings/my_japan_value.json`へコピーし、JSON内の`name`も`my_japan_value`に変更します。
2. 市場・条件・取得列などを編集し、`app.bat screen my_japan_value`（Windows）で実行します。
3. 日次Jobにする場合は`jobs/`のサンプルをコピーし、`task.definition`に自分のScreening名を指定します。まず`enabled=false`・`watchlistSync=false`で手動確認してください。

結果を参照するコマンドには**Job名ではなくScreening名**を指定します。

[Screeningの作成手順](docs/user/SCREENING_MANUAL.md#自分の条件を追加する) / [Jobの作成手順](docs/user/SCHEDULE_MANUAL.md#自分のjobを作る)

## 安全上の注意と制限

- **書き込みに注意：** `sample_screen_daily`は初期状態で`enabled=true`かつ`watchlistSync=true`です。`schedule apply`は有効な**すべてのJob**を登録・更新します。利用前に設定と同期先を確認してください。上記の`public_sample_screen_daily`はWatchlistへ書き込みません。
- **全米株の無条件一括取得は未対応：** TradingView公式MCP Providerが要求を拒否し、取得上限1,000行と全件列挙手段の制約があります。`us_sector_morning`は無効です（[詳細](docs/user/SCREENING_MANUAL.md#公式mcp-beta版のスクリーニング制限2026-10-18実機確認)）。
- **認証情報：** Dockerのcredential volumeはOSの暗号化Keychainではありません。`docker compose down -v`等によるvolume削除にも注意してください（[保存と保護](docs/user/DOCKER.md#データと認証情報の保存場所)）。

## マニュアル

各マニュアルの本文は**日本語**です。

| 目的 | マニュアル |
| --- | --- |
| 導入・認証 | [Windows](docs/user/WINDOWS_SETUP.md) / [Docker](docs/user/DOCKER.md) |
| 機能・条件作成 | [機能一覧](docs/user/FEATURES.md) / [Screening](docs/user/SCREENING_MANUAL.md) |
| 保存・自動化 | [結果・履歴・比較](docs/user/RESULTS.md) / [Job・Scheduler](docs/user/SCHEDULE_MANUAL.md) |
| その他 | [Watchlist同期](docs/user/WATCHLIST_SYNC.md) / [AIからのCLI利用](docs/user/AI_USAGE.md) / [トラブル対応](docs/user/TROUBLESHOOTING.md) |

## ライセンス

[MIT License](LICENSE)。第三者の資料・ライブラリには、それぞれの利用条件が適用されます。
