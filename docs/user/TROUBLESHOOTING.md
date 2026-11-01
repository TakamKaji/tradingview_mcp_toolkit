# トラブル対応

まずエラーの終了コードとJSONの`status`・`errors`・`reason`を確認します。token、認可code、credentialをログやチャットへ貼らないでください。既存の認証・mapping・結果を一括削除する必要はありません。

| 状況 | 確認・対処 |
| --- | --- |
| my_japan_valueが見つからない | [全文例](SCREENING_MANUAL.md#自分の条件を追加する)をscreenings/my_japan_value.jsonへ保存し、内部nameも一致させます。説明用の名前で、最初から同梱されていません |
| Jobから自分の条件を呼べない | task.typeをscreening、task.definitionを拡張子なしのScreening名にします。runにはJob名、resultsにはScreening名を指定します |
| get_ohlcv等をCLI/Jobで呼べない | [公式Tool・Python API・CLIの違い](FEATURES.md#c-公式toolと本ツールの接続範囲)を確認します。任意Tool実行CLIやローソク足の定期取得Jobは未実装です |
| GitHubのページを開けない／404 | URLとアクセス権を確認してください。Releaseの一覧に版がない場合はmainのCode → Download ZIPを利用します |
| setupが見つからない | ZIPを「すべて展開」し、setup.batとapp.batがあるフォルダを開きます |
| ダウンロード・依存導入に失敗 | [必要な通信先](WINDOWS_SETUP.md#通信先と未確認事項)とネットワーク設定を確認し、setupを再実行します |
| AUTH_REQUIRED / exit 3 | 未認証・失効のためです。setup.batを通常実行するか、明示的にapp.bat mcp authで認可します |
| statusが通信エラー | status自体はブラウザを開きません。通信やProviderの状況を確認し、credential削除・認証連打で代用しません |
| OAuthでブラウザ認可が戻らない | 公式画面での許可、利用プラン、127.0.0.1:8765のポート競合を確認します。独立新規ユーザーでの初回認証は未検証です |
| setupの日本語表示がおかしい | 最新mainのZIPで、setup.bat・setup-runtime.bat・scripts/setup-ui.ps1を一緒に取得してください。BATだけの古いコピーと混在させないでください |
| app.batをPowerShellが見つけない | 展開フォルダで`.\app.bat`と入力します。コマンドプロンプトでは`app.bat`です |
| exit 2 | コマンド引数・JSON定義を確認します。ファイル名と内部name、参照先、未知キーに注意してください |
| Provider拒否／条件無視／exit 1 | 通信成功と条件成立は別です。成功の空結果へ読み替えず、[Screeningの制約](SCREENING_MANUAL.md#公式mcp-beta版のスクリーニング制限2026-10-18実機確認)を確認します |
| results latestで結果なし | 成功結果が保存されているか、Job名ではなくScreening名を指定したか確認します |
| historyが空／一部ファイルが出ない | 対象名・保存先を確認します。壊れたJSONや危険なpathは採用されません。元ファイルを保持して診断します |
| compareがNO_BASELINE | 成功結果が2件未満です。同じ条件の新しい結果が2件揃ってから比較します |
| compareが条件不一致・旧形式 | [比較できない場合](RESULTS.md#比較できない場合)を確認します。古い結果を改変しません |
| 保存に失敗 | 書込み権限・空き容量と、ファイルシステムのhard link対応を確認します。既存結果の上書きで回避しません |
| Jobがalready_running | 同じJobの実行と競合しています。スキップはexit 0です。lockファイルを実行中に削除しません |
| 同期がpartial／mappingエラー | 一部Write済みの可能性があります。[Watchlist](WATCHLIST_SYNC.md#失敗したとき)を確認し、自動rollback・mapping削除をしません |
| Jobを無効にしたのにTaskが残る | enabled=falseやJSON削除では既存Taskを削除しません。[明示的な削除](SCHEDULE_MANUAL.md#定期実行を止める削除操作)を確認します |

接続確認は次の2つです。Watchlist/Alert WriteやTaskの登録・削除は行いません。

```bat
app.bat mcp status
app.bat mcp tools
```

比較だけを行う場合はMCP接続確認自体が不要です。`results history/compare`はPC内の保存結果だけを読みます。

[利用者マニュアル一覧](README.md)
