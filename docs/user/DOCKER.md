# Dockerコンテナで使う

Windows・macOS等のホストから既存CLIを手動実行する構成です。ホストへのPythonインストールは不要です。Windows上のDocker Desktop・Linux/amd64で実OAuth、Screening、Job、認証・結果の永続化を確認しています。Mac実機・arm64は未検証です。[共通機能とサンプル](FEATURES.md)の区別は同じで、コンテナ内のSchedulerには対応しません。

## 準備

1. ホストに合う[Docker Desktop](https://docs.docker.com/desktop/)等を導入し、起動します。Dockerの利用条件も確認してください。
2. リポジトリの配布ZIPを展開します。`compose.docker.yml`、`mac.command`、`screenings/`、`jobs/`が同じフォルダにあることを確認します。
3. 展開フォルダで[Composeのコマンド](#ターミナルからcomposeを直接使う)を実行します。macOSでは、以下の補助起動スクリプトも利用できます。

## macOSの補助起動スクリプト

`mac.command`をダブルクリックするとbuildし、ターミナルへCLIのヘルプを表示します。**認証・Job・Watchlist Write・定期登録は自動実行しません。**

展開方法によって実行権限が失われた場合は、ターミナルで`chmod +x mac.command`を実行します。Macのセキュリティ確認で開けない場合は、取得元とファイルを確認してFinderの「開く」を使ってください。セキュリティ機能全体を無効にする必要はありません。

### 初回TradingView認証

```sh
./mac.command mcp auth
./mac.command mcp status
./mac.command mcp tools
```

`mcp auth`のときだけ、Macのブラウザで認可開始URL`http://127.0.0.1:8765/oauth/authorize`を開きます。そこからTradingView公式の認可画面へ移動し、ログイン・許可するとcallbackを受信します。ブラウザが開かない場合は、認証コマンドの実行中にこの認可開始URLを自分で開いてください。認証完了後は認可開始URLの待ち受けも終了します。

認可URLのstate、認可code、tokenをターミナルへコピーしません。ブラウザを開くのは`mcp auth`だけです。`mcp status/tools`やJobは認証切れでも勝手にブラウザを開かず、`AUTH_REQUIRED`・exit 3なら手動で認証し直します。

ホストへの公開は**`127.0.0.1:8765`だけ**で、認証時だけ`--service-ports`を使います。コンテナ内部の待受はポート転送を受けるため`0.0.0.0`ですが、OAuth redirect URIは`http://127.0.0.1:8765/oauth/callback`のままです。`network_mode: host`、外部向けのポート公開、Docker socketの共有は使いません。

## ターミナルからComposeを直接使う

`mac.command`はフォルダを選び、buildしてCLIへ引数を渡す補助です。Composeだけでも実行できます。

```sh
docker compose -f compose.docker.yml build app
docker compose -f compose.docker.yml run --rm app --version
docker compose -f compose.docker.yml run --rm --service-ports app mcp auth
docker compose -f compose.docker.yml run --rm app mcp status
docker compose -f compose.docker.yml run --rm app mcp tools
```

Composeでのauthは、表示された認可開始URLをホストのブラウザで手動で開きます。通常の読み取りコマンドには`--service-ports`を付けません。イメージはPython 3.12公式イメージを使い、通常はホストのCPUに合うアーキテクチャでbuildします。

## Screening・手動Job・結果

Composeでは、以下の`./mac.command`を`docker compose -f compose.docker.yml run --rm app`に読み替えます。macOSの補助起動スクリプトではそのまま実行できます。

```sh
./mac.command screen public_japan_value
./mac.command results latest public_japan_value
./mac.command jobs list
./mac.command run public_sample_screen_daily
./mac.command results latest sample_standard_screen
```

これらは同梱のRead-only例です。`screen`は条件の実行、`run`はJobの実行で、保存結果の参照には**Screening名**を使います。上のJobは保存を行いますがWatchlistを同期しません。`sample_screen_daily`は別のWrite付き例なので取り違えないでください。

自分の条件・Jobは[Screeningの全文例](SCREENING_MANUAL.md#自分の条件を追加する)と[Jobの全文例](SCHEDULE_MANUAL.md#自分のjobを作る)をコピーします。ファイルはホスト上の`screenings/`と`jobs/`で編集でき、次回の実行から反映されます。定期登録の節はWindowsネイティブ専用です。

履歴・比較も`./mac.command results history 名前 --limit 10`、`./mac.command results compare 名前`で使えます。ローソク足・ニュース等の定期取得Jobはありません。全米株の条件なし取得はProvider拒否により未対応で、`us_sector_morning.enabled=false`を維持します。

## データと認証情報の保存場所

| 内容 | 保存先 | 保持・アクセス |
| --- | --- | --- |
| 自作Screening / Job | 展開フォルダのscreenings / jobs | ホスト上で編集。コンテナからはRead-only bind mount |
| 保存結果 | Docker volume `tradingview-mcp-support-mac_results` | コンテナ内`/workspace/results`。再作成後も保持 |
| Lock・Watchlist mapping等 | Docker volume `tradingview-mcp-support-mac_local` | コンテナ内`/workspace/.local`。認証tokenとは別 |
| OAuth token・client登録・OAuth metadata | Docker volume `tradingview-mcp-support-mac_credentials` | コンテナ内`/credentials`。専用ユーザーUID 10001の所有、ディレクトリ0700・ファイル0600 |

固定のCompose project名を使うので、展開先を変えても同じDocker Engineの同名volumeを再利用します。並行して別の利用者・別環境を動かす場合は、Composeの`-p`で別project名を明示します。その場合`mac.command`の既定volumeとは別になります。異なる環境でWatchlist mappingだけをコピーして使い回さないでください。

**コンテナの認証volumeは暗号化されたOS Keychainではありません。** ファイルの所有者・モードとDocker DesktopのVMで保護する方式です。ホストのDocker管理権限者・管理者・VMバックアップへのアクセス権者は内容を読めます。信頼できる個人用環境で使い、OSログイン・ディスク暗号化で保護し、認証volumeを共有・通常の結果バックアップへ同梱しないでください。Docker secretも書き込み・更新可能なOAuth永続ストアではないため採用していません。

LinuxコンテナからMac Keychainを直接使う構成にはしていません。ホスト側のCredential中継を追加すると通信・認可の境界が増えるため、今回は専用volumeを選びました。WindowsのCredential Manager、通常macOS PythonのOS keyring経路は変更しません。

イメージにはソースとパッケージ定義だけを収録し、`.git`、開発資料、テスト、ホストの`.local`、runtime、結果、credentialを含めません。コンテナは非root・root filesystem読み取り専用で動き、通常CLIはポートを公開しません。

## 終了・再実行・更新・バックアップ

`run --rm`は1コマンドごとの一時コンテナで、終了時にコンテナだけを削除します。実行中に止めるときはターミナルでCtrl+Cを使います。次のコマンドで新しいコンテナが同じvolumeを読みます。常駐サービスを起動する必要はなく、`compose up -d`やcronは使いません。

更新は新しいZIPを別フォルダへ展開し、古いフォルダを残して自作`screenings/`・`jobs/`をコピーし、そこでComposeのbuild・version確認を行います。同じproject名・Docker Engineなら結果と認証volumeは継続します。`docker compose -f compose.docker.yml build --pull app`でベースイメージも更新できます。

結果・mappingのバックアップ例（**認証volumeは含みません**）。Windowsではバイナリ出力を変換しないコマンドプロンプト（cmd）で実行してください。

```sh
docker compose -f compose.docker.yml run --rm --entrypoint tar app -czf - -C /workspace results .local > docker-results-backup.tgz
```

自作定義はホスト側で別途バックアップします。mappingには利用者固有のWatchlist ID等が含まれるので、バックアップも非公開で保管してください。認証volumeは再認証で再作成でき、平文での持ち出しを推奨しません。Docker Desktopのデータ初期化・アンインストール・volume削除では永続データを失います。`docker compose down -v`やvolume pruneを通常の終了・更新手順として使わないでください。

## トラブル対応・検証範囲

- Dockerに接続できない：Docker Desktopを起動し、`docker compose version`を確認します。ホストへのPython追加では解決しません。
- ポート8765が使用中：別の認証を終了してから再実行します。ポートを外部へ公開したりredirect URIを独自変更しません。
- ブラウザが開かない／認証タイムアウト：auth実行中に認可開始URLを開きます。古いページでなく新しい認証を使います。callbackのcode等は貼り付けません。
- `CREDENTIAL_STORE_ERROR`：専用volumeの所有UID10001・dir0700/file0600、symlinkでないことを確認します。読み出しや権限緩和、Windows credentialのエクスポートで回避しません。既存volumeを消す前に原因を診断します。
- `Mounts denied`・ファイルを読めない：展開フォルダだけをDocker DesktopのFile Sharingへ許可し、ホスト上のscreenings/jobsの存在・読み取り権限を確認します。ホーム全体の共有や`chmod -R 777`は不要です。これらのbind mountはコンテナから書き込めません。
- 結果がホストのresultsに見えない：コンテナ版は専用volumeです。`results latest/history`またはバックアップで確認します。
- Scheduler：Windowsネイティブ専用です。コンテナでは手動Jobまでを使い、`schedule apply/list/remove`を実行しません。

Windows上のDocker Desktop・Linux/amd64での実通信成功を、Mac実機・arm64の動作保証とは扱いません。Macのダブルクリック、Appleの`open`、ファイル共有・権限とOAuthは実機で別途確認が必要です。

参照：[Dockerのrunとポート公開](https://docs.docker.com/reference/cli/docker/compose/run/)、[Macのbind mount権限](https://docs.docker.com/desktop/setup/install/mac-permission-requirements/)、[macOS Keychain](https://support.apple.com/guide/keychain-access/what-is-keychain-access-kyca1083/mac)。

[機能一覧](FEATURES.md) / [利用者マニュアル一覧](README.md)
