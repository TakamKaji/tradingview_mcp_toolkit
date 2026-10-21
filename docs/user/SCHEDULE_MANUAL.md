# 自分のJobを作り、必要なら定期実行する

**Job RunnerとWindows Schedulerは共通機能です。** `jobs/`内のJSONは使い方のサンプルで、特定条件や実行時刻が製品共通の監視サービスとして固定されているわけではありません。

Jobは実行対象のScreening、保存・同期、任意の定期登録時刻をまとめます。`screen`はScreeningを直接実行し、`run`はJobを実行します。Job名とScreening名は別に管理します。

## 自分のJobを作る

1. [Screeningマニュアル](SCREENING_MANUAL.md#自分の条件を追加する)に従い、`screenings/my_japan_value.json`を作成し、`screen my_japan_value`で結果を確認します。
2. `jobs/public_japan_value_daily.json`をコピーし、`jobs/my_japan_value_daily.json`へ保存します。
3. Job内部の`name`をファイル名と同じ`my_japan_value_daily`に、`task.definition`をScreening名`my_japan_value`にします。
4. `schedule.time`を希望時刻へ設定します。下の`16:10`は**説明用の任意の例**で、推奨・固定時刻ではありません。
5. 最初は`enabled=false`、`watchlistSync=false`のまま保存し、手動実行します。
6. 保存された結果、取得件数、対象Screening、同期設定を確認します。
7. 定期実行したい場合だけ、後述の注意を確認し、必要なJobを有効化して登録します。

ファイルはUTF-8 BOMなしで保存します。名前は半角英数字で始め、以後は半角英数字・`_`・`-`を使います。サブフォルダや拡張子を`task.definition`に含めず、未知のキーを追加しません。

`jobs/my_japan_value_daily.json`の全文：

```json
{
  "schemaVersion": 1,
  "name": "my_japan_value_daily",
  "enabled": false,
  "task": {
    "type": "screening",
    "definition": "my_japan_value"
  },
  "schedule": {
    "type": "daily",
    "time": "16:10",
    "timezone": "Asia/Tokyo"
  },
  "output": {
    "save": true,
    "watchlistSync": false
  }
}
```

| 設定 | 意味 |
| --- | --- |
| schemaVersion | 整数1 |
| name | `.json`を除くJobファイル名と一致 |
| enabled | 定期登録の対象にするか。falseでも明示した手動runは実行する |
| task.type / definition | 自分のScreeningを呼ぶ場合は`screening`とScreening名。任意の公式Tool名は指定できない |
| schedule.type / time / timezone | 定期登録は`daily`・24時間表記`HH:MM`・`Asia/Tokyo`のみ |
| output.save | 結果JSONをPCへ保存するか |
| output.watchlistSync | 管理Watchlist同期を呼ぶか。Screening側も有効なら実Writeを行う |

手動runでもschedule項目は必要です。ただし手動実行はその場で動き、設定時刻まで待ちません。Schemaが他のIANA timezoneを読めても、現在のScheduler登録はAsia/Tokyo以外に対応しません。

## 手動で実行・結果確認する

次は上のScreeningとJobを作成してから使うコマンドです。コマンドプロンプトでは`app.bat`、PowerShellでは`.\app.bat`を使います。

```bat
app.bat jobs list
app.bat run my_japan_value_daily
app.bat results latest my_japan_value
```

`run`に渡すのは**Job名**、`results`に渡すのは**Screening名**です。例はTradingView Read＋ローカル保存だけで、Watchlist WriteやTask登録は行いません。`jobs list`は全Jobの定義・参照を検証し、不正なものが1つでもあればexit 2になります。

`app.bat schedule list`は登録済みの管理Taskを列挙するだけで、登録・削除は行いません。

## 定期実行を登録する（作成・更新操作）

**`schedule apply`は有効な全JobのTaskを作成・更新します。特定Jobだけを選ぶコマンドではありません。** 同梱の`sample_screen_daily`は`enabled=true`かつ`watchlistSync=true`で、参照ScreeningのWatchlist設定も有効です。そのままapplyすると、**Watchlist Writeを伴うサンプルの定期実行も登録されます。**

登録前に、自分の環境で次を確認してください。

1. `jobs list`で全Jobを確認し、不要なサンプル（特に`sample_screen_daily`）のJSONを`enabled=false`にします。
2. 使いたい`my_japan_value_daily`だけを`enabled=true`にします。時刻、保存先のある展開フォルダ、Watchlist同期設定を再確認します。
3. 利用者が登録と副作用を意図する場合だけ、以下を実行します。AIへ依頼する場合も対象と登録の許可を明示します。

```bat
app.bat jobs list
app.bat schedule apply
app.bat schedule list
```

既存TaskはJSONを無効にしただけでは停止・削除されません。すでにサンプルを登録していた場合は、次の明示removeが必要です。Watchlist同期の有効化は[Watchlistマニュアル](WATCHLIST_SYNC.md)で対象と追加・削除の意味を確認してから判断してください。

## 定期実行を止める（削除操作）

**次は自分で作成したJobの管理Taskを削除する操作です。** 削除を意図する場合だけ実行します。

```bat
app.bat schedule remove my_japan_value_daily
app.bat schedule list
```

対象Task名は`TradingViewMcpSupport__<Job名>`です。Job JSONが削除済みでも、指定名と一致する管理Taskを削除できます。不要な既存サンプルを止める場合は、そのJob名を指定してください。結果JSONやTradingView Watchlist自体を削除する操作ではありません。

## 同梱Jobは使用例

| Job名 | 参照するScreening／処理 | 同梱設定 |
| --- | --- | --- |
| public_sample_screen_daily | sample_standard_screen | enabled=false、save=true、同期なし |
| public_japan_value_daily | public_japan_value | enabled=false、save=true、同期なし |
| public_sp500_daily | public_sp500 | enabled=false、save=true、同期なし |
| public_oversold_healthy_daily | public_oversold_healthy | enabled=false、save=true、同期なし |
| public_sp500_symbolset_daily | public_sp500_symbolset | enabled=false、save=true、同期なし |
| sample_screen_daily | sample_standard_screen | **enabled=true、save=true、Watchlist同期あり** |
| us_sector_morning | builtin us_sector_daily | enabled=false。条件なし全米株取得をProviderが拒否するため現在未対応 |

日次Jobの`15:40`、全米株例の`07:00`、このマニュアルの`16:10`はいずれも設定例です。市場営業日・休日・早期終了を判断して時刻を自動補正する機能ではありません。

Jobの種類は`screening`と明示実装された`builtin`です。builtinは現在`us_sector_daily`だけで、任意のToolを指定して定期取得する汎用機能ではありません。**ローソク足・ニュース・財務などの定期取得Jobは未実装です。** [公式ToolとPython APIの範囲](FEATURES.md#c-公式toolと本ツールの接続範囲)を参照してください。

## 実行条件と失敗時

- Windowsで登録したユーザーがログオン中に実行します。管理者・パスワード登録は不要です。PC停止・スリープ中の定刻実行は保証しません。
- 定期登録はdaily / Asia/Tokyoのみ。weekly、monthly、cron、他timezone・DST、macOS/Linux Schedulerは非対応です。
- 保存済み認証を使い、認証切れでもブラウザを自動起動しません。`AUTH_REQUIRED`なら利用者が手動で認証します。
- 同じJobが実行中なら`already_running`でスキップし、exit 0です。
- `status`、`errors`、保存・同期済みの情報を確認します。終了コード0でも部分成功の場合があります。Write途中の失敗を自動rollbackしません。
- JSON・名前・参照のエラーは[Screeningの対処](SCREENING_MANUAL.md#失敗したとき)も参照し、Job名とScreening名の取り違えを確認してください。

[結果を見る](RESULTS.md) / [利用者マニュアル一覧](README.md)
