# TradingView MCP Toolkit

**日本語** | [English](README.en.md)

TradingView公式MCPを**AIエージェントなしで利用するためのPython CLI・ライブラリ**です。JSONで定義した株式スクリーニングの実行、データ取得、外部ツールによる自動処理への組み込みに使えます。AIのインストールや契約は不要です。

> **非公式ツールです。** TradingView社の公式製品ではなく、提携・承認を受けたものでもありません。

## 主な利用例

| 用途 | 構成 |
| --- | --- |
| 日次スクリーニングを蓄積し、前回と比較する | 標準CLIとJSON定義を使い、Windows Task Schedulerまたは外部スケジューラで実行 |
| 指定銘柄の株価情報・OHLCVを自分の処理へ取り込む | Pythonラッパーを使った独自プログラムを作成 |
| 外部のジョブ管理ツールから繰り返し実行する | 利用者がCLIの呼び出しを設定 |
| ホストとPython実行環境・依存ライブラリを分離する | Dockerコンテナでデータ取得処理を実行 |
| 保存結果をブラウザや表計算ソフトで使う | 保存JSONを既存のエクスポート機能でCSV・HTMLへ変換 |

## 現在利用できる機能

**標準CLI**は、Screening JSONの実行、結果JSONの保存・履歴・同条件の前回比較、Jobの手動実行に対応します。WindowsネイティブではTask Schedulerへ日次Jobを登録できます。管理Watchlist同期は、設定したJobの実行に伴う**明示的な書き込み（Write）**です。

**Python API**は、既存の認証・通信処理を再利用し、`TradingViewClient`の`get_symbol_data`、`get_symbol_data_batch`、`get_ohlcv`等を独自プログラムから呼び出せます。35 Toolの対応範囲は[機能一覧](docs/user/FEATURES.md#c-公式toolと本ツールの接続範囲)、実際の入力は[Request定義](src/tradingview_screening/integrations/tradingview/schemas.py)を参照してください。

**個別銘柄の株価・OHLCV取得用CLIや、その定期保存Jobは標準搭載していません。** Python APIで取得した任意の応答が、標準Screeningの保存・比較へ自動接続されるわけでもありません。

## 導入方法

インターネット接続と[TradingView公式MCPを利用できる契約プラン](https://www.tradingview.com/mcp/docs)が必要です。[mainブランチ](https://github.com/TakamKaji/tradingview_mcp_toolkit)の **Code → Download ZIP** から取得・展開してください。特定バージョンのGitHub Releaseがある場合は、そのSource code (zip)も利用できます。

### Windows（ネイティブ）

システムPythonの事前導入は不要です。Windows 64-bitで`setup.bat`をダブルクリックし、案内に従って公式ブラウザ画面でOAuth認可を行います。管理者権限は不要です。

展開フォルダのエクスプローラーのアドレス欄に`cmd`と入力し、読み取り専用サンプルを実行します。

```bat
app.bat run public_sample_screen_daily
app.bat results latest sample_standard_screen
```

このJobはWatchlistへ書き込まず、結果を展開先の`results/`に保存します。[Windows導入手順](docs/user/WINDOWS_SETUP.md)を参照してください。

### Docker（Windows・macOSなど）

Docker Desktop等とComposeが必要です。ホストへのPython事前導入は不要です。展開フォルダのターミナルで実行します。

```sh
docker compose -f compose.docker.yml build app
docker compose -f compose.docker.yml run --rm app --version
docker compose -f compose.docker.yml run --rm --service-ports app mcp auth
```

認証コマンドの実行中に、案内に従ってホストのブラウザで`http://127.0.0.1:8765/oauth/authorize`を開きます。認証後、読み取りと保存結果を確認します。

```sh
docker compose -f compose.docker.yml run --rm app screen public_japan_value
docker compose -f compose.docker.yml run --rm app results latest public_japan_value
```

結果と認証情報は専用のDocker volumeに保存されます。`mac.command`はmacOS向けの補助起動スクリプトです。[Docker導入・保存先](docs/user/DOCKER.md)を参照してください。

## 他の自動化ツールとの連携

外部システムからCLIを呼び出すことで、ScreeningやJobを繰り返し実行できます。Windows Task Schedulerへの登録は標準機能です。cron等のホスト側スケジューラやジョブ管理・ワークフローツールからの呼び出しは、**利用者が設定する連携方式**であり、専用コネクターが実装されているわけではありません。

外部ツールには、展開フォルダを作業ディレクトリとして、実行コマンド・実行ユーザー・保存先・認証情報へのアクセスを設定し、stdout・stderr・終了コードと新しい保存結果を確認してください。**Docker版に組み込みSchedulerはありません。** ホスト側でComposeコマンド等の実行を設定します。

特定銘柄の株価・OHLCVを定期取得する場合は、**Pythonラッパーを使う独自処理と外部スケジューラを組み合わせます**。取得条件・時点・保存形式・失敗時の扱いは独自処理側で実装する必要があります。

自分の条件は[Screening作成手順](docs/user/SCREENING_MANUAL.md#自分の条件を追加する)、JobとWindows定期登録は[Job・Scheduler](docs/user/SCHEDULE_MANUAL.md)へ。結果の参照にはJob名ではなくScreening名を使います。CSV・HTMLへの変換は[結果のエクスポート](docs/user/RESULTS.md#保存jsonからcsvhtmlを作る任意の後変換)を参照してください。

## AIとの連携（任意）

Gemini CLI・Codex・Claude Code向けの[指示ファイルと利用手順](docs/user/AI_USAGE.md#プロジェクトルートでaiを起動する)を用意しています。AIは条件JSONや、標準機能で不足する独自処理の作成を補助するために任意で使えます。詳細は[AI共通ガイド](docs/user/AI_JSON_GUIDE.md)へ。各AIの独立実機受入には[未検証事項](docs/user/NATURAL_LANGUAGE_ACCEPTANCE.md)が残っており、指示ファイルの存在だけで動作確認済みとは扱いません。

## 制約・注意点

- **Providerの対応範囲：** 市場・指標・取得上限に制約があります。取得成功と全件取得は別です。条件の無視、null、行数、データ取得時点とOHLCVの確定足・価格調整を確認してください。[観測上の注意](docs/user/PROVIDER_VERIFICATION.md)を参照。
- **全米株の条件なし一括取得は未対応：** Providerの拒否、1,000行上限と全件列挙手段の制約があり、`us_sector_morning`は無効です。[詳細](docs/user/SCREENING_MANUAL.md#公式mcp-beta版のスクリーニング制限2026-10-18実機確認)を参照。
- **書き込みと定期登録：** Watchlist同期はTradingViewへのWriteです。`sample_screen_daily`は初期状態で`enabled=true`・`watchlistSync=true`です。`schedule apply`は有効な全Jobを登録・更新するため、設定と同期先を確認し、明示的に実行してください。上の`public_sample_screen_daily`はRead-onlyです。
- **認証情報：** Dockerの専用credential volumeはOSの暗号化Keychainではありません。volumeの共有や`docker compose down -v`等の削除に注意してください。[保存と保護](docs/user/DOCKER.md#データと認証情報の保存場所)を参照。
- **検証範囲：** Windows Docker Desktop／Linux amd64での実OAuth・取得・永続化は確認済みです。Mac実機・arm64、新規Windowsユーザーの初回OAuthは未検証です。

詳細は[利用者マニュアル一覧](docs/user/README.md)と[トラブル対応](docs/user/TROUBLESHOOTING.md)へ。マニュアルは日本語で、日本語READMEを正本とします。

## ライセンス

[MIT License](LICENSE)。第三者の資料・ライブラリには、それぞれの利用条件が適用されます。
