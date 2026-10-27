# AIから共通CLIを使う

AIには展開フォルダで共通`app.bat`を使うよう依頼します。通常のScreening・結果管理・Job実行に、別のTradingView connectorや条件ごとのPythonスクリプトは不要です。初回導入は[Windows導入](WINDOWS_SETUP.md)を完了してください。

## プロジェクトルートでAIを起動する

`README.md`と`app.bat`があるフォルダを作業場所にして、対応CLIを起動します。配布mainの[GEMINI.md](../../GEMINI.md)・[AGENTS.md](../../AGENTS.md)・[CLAUDE.md](../../CLAUDE.md)は短い利用者向け入口、developの入口は開発規則も保持します。詳細なScreening規則の正本は両ブランチ共通の[AI生成ガイド](AI_JSON_GUIDE.md)です。

| 製品 | 自動読込と起動条件 | ルート起動時の確認方法・限界 |
| --- | --- | --- |
| Gemini CLI | 既定の`GEMINI.md`をワークスペース・親階層等から探索。設定の`context.fileName`や信頼範囲に依存 | ルートで`gemini`を起動し、`/memory show`で入口の本文を確認。入口があってもリンク先本文まで自動展開されるとは限らない |
| Codex | 起動時にプロジェクトルートから作業場所まで探索。同一階層は`AGENTS.override.md`優先、次に`AGENTS.md`。全体サイズ上限・設定の影響あり | ルートで`codex`を起動し、適用された指示の出典と要点を確認。途中で作成/切替したファイルは新しいセッションで確認する |
| Claude Code | 作業場所と親階層の`CLAUDE.md`等を起動時に読込。除外・追加ディレクトリ設定等に依存 | ルートで`claude`を起動し、`/memory`または`/context`で読込対象を確認。Markdownリンクだけで参照先全文の読込済みとは扱わない |

公式の読込仕様：[Gemini CLI](https://geminicli.com/docs/cli/gemini-md/)、[Codex](https://developers.openai.com/codex/guides/agents-md)、[Claude Code](https://code.claude.com/docs/en/memory)（2026-10-25確認）。この表は仕様の確認と利用者の確認手順です。**Gemini/Claude CLIは現環境のPATHに該当CLIがなく、実起動は未検証**。Codex CLI 0.163.0-alpha.10.2は存在を確認しましたが、ルートでの新規セッション試行は状態DB/初期化へのアクセス拒否（exit 1）で読込を実証できませんでした。3製品とも対応IDEでの動作は未検証です。静的な入口/リンク検査を3製品の動作確認と呼びません。

AIにはREADME→共通ガイド→必要な実仕様を読むよう入口で指示しています。最初に参照したファイルと未確認事項を確かめてください。一般のAIチャットへフォルダ名だけを送ってもPC内の指示ファイルは自動適用されません。通常チャットには必要な本文やアクセス可能な資料を渡します。製品・IDE・設定の違いがあり、3製品の完全な遵守を保証しません。

## 共通機能と依頼範囲を確認する

[機能一覧](FEATURES.md)のとおり、CLIは定義済みScreeningの実行、結果の参照、Job、Scheduler、MCP認証・一覧確認を扱います。公式Toolの全操作を任意に呼ぶCLIではありませんが、既存PythonラッパーのRead機能を組み合わせたPythonは作成・実行できます。**利用者にTradingView公式MCPサーバーをAIへ別途登録・設定させず、既存のClient・認証・通信制御を使います。** ローソク足・ニュース・財務の専用CLIや定期取得Jobの未実装を、ラッパーからの取得も実現不可能という意味にしないでください。

## 会話からScreeningを作成し、方式を選ぶ

Gemini CLI・Codex・Claude Code・ChatGPTのいずれでも、最初に[AIによるScreening生成ガイド](AI_JSON_GUIDE.md)と実際のSchema・公式Provider対応項目・サンプルを読み、希望を整理します。公開URLだけで必ず本文を読めるとは限らないため、アクセスできなければ必要資料を渡してください。

- **方式A（最優先）**：単一Screeningで表現できれば`screenings/*.json`を作り、Jobが必要な場合だけ`jobs/*.json`も作ります。通常の条件に独自Python・BATを追加しません。
- **方式B**：標準JSONの直接対応を調査して表せない場合、既存`TradingViewClient`と型付きRequestによる候補抽出・直接指標・一括取得を調べ、必要なら公式OHLCVから計算するPythonを作成します。元の母集団・条件が成立しなければ制約を報告し、外部データや条件変更は明示的な依頼・承諾後だけ利用します。候補の取りこぼし、応答形式、欠損・失敗・完全性を確認し、実用可能なら元条件を保つPythonを作成・起動します。調査順序・再実装禁止・検証契約の正本は共通ガイドです。

ChatGPTは完成ファイルと保存手順を提供し、通常チャットから利用者PCへ自動設置しません。Gemini CLI・Codex・Claude Codeはアクセス可能なローカル環境へ保存・検証します。Python方式では実際の保存先・依存・実行環境・正確な実行コマンド・結果の保存先と確認方法を明示し、実行も依頼され環境が利用可能なら実行・検証します。できない場合は理由と未実行状態を示します。外部データの出典・取得時刻・欠損・制限を示し、不完全な結果を全件取得と報告しません。

ファイル作成・ローカル検証・実取得・Writeは別操作です。利用者から指示されない限りTradingViewへの実書き込みやScheduler登録・削除を実行しません。以下のCLI例は方式Aに対する操作です。

## 自分の条件・Jobを作る依頼例

> public_japan_value.jsonを別名のmy_japan_value.jsonへコピーし、nameも一致させてください。日本株、PER 0〜15、予想配当利回り3%以上、出来高降順、limit 20、Watchlist無効にします。JSONを確認し、既存サンプルは変更しないでください。

全文と許可される設定は[Screeningマニュアル](SCREENING_MANUAL.md#自分の条件を追加する)を参照します。定期実行も必要なら、[Jobの作成手順](SCHEDULE_MANUAL.md#自分のjobを作る)に従い別名のJobを作り、最初は`enabled=false`・`watchlistSync=false`で手動確認します。定義作成とTask登録は別の依頼です。

## Read-only実行の依頼例

上のScreeningを作成してから、次のように依頼できます。

> my_japan_valueをscreenで実行し、最新結果と直近10件の履歴を表示してください。Watchlist・Alert WriteとScheduler登録・削除は行わないでください。

```bat
app.bat screen my_japan_value
app.bat results latest my_japan_value
app.bat results history my_japan_value --limit 10
```

TradingView ReadとPC内への保存です。Jobを作った場合は`run my_japan_value_daily`で実行しますが、結果参照には引き続きScreening名`my_japan_value`を使います。`enabled=false`でも手動runは実行します。

## 前回差分を確認する

> 保存済みmy_japan_valueの直近2件を比較してください。条件のfingerprintとcoverageを確認し、比較できなければ理由を説明してください。新規取得は不要です。

```bat
app.bat results compare my_japan_value
```

ローカル読み取りのみです。1件以下は`NO_BASELINE`、条件変更・旧形式等は比較不能です。古い比較可能ペアへの差し替えや、旧結果へのfingerprintの後付けは行いません。`observed_set_only`なら「今回未観測」と説明し、条件不適合と断定しません。Provider総件数`totalCount`と実取得行数`returnedCount`を区別します。

## 同梱例で試す場合

同梱JSONは共通機能の使用例です。Jobの初回試用を依頼するなら`public_sample_screen_daily`を指定できます。これはRead-only＋ローカル保存で、結果名は`sample_standard_screen`です。`sample_screen_daily`は別のWrite付き例なので、名前を取り違えないでください。

## Write・登録・削除を依頼する場合

利用者が対象と副作用を理解して明示依頼する場合だけ行います。[Watchlist](WATCHLIST_SYNC.md)と[Scheduler](SCHEDULE_MANUAL.md)を先に確認します。`schedule apply`は**有効な全Job**を登録・更新するため、自分のJobだけでなく同梱の`sample_screen_daily`も点検してください。無効化だけでは既存Taskは削除されません。

## 出力と失敗時

stdoutはJSON、stderrは診断です。exit 0でも部分成功・重複スキップがあり、`status`、`errors`、`metadata`を確認します。exit 1は実行時失敗、2は引数・定義不正、3は再認証要求です。

token・認可code・credential・Providerの生応答全文をチャットへ貼りません。Write失敗を自動再送・rollbackせず、確認済み結果を報告します。全米株の条件なし取得は公式Providerが拒否するため、S&P 500や先頭1000件へ縮小して全米株成功と説明しないでください。

[結果の読み方](RESULTS.md) / [トラブル対応](TROUBLESHOOTING.md) / [利用者マニュアル一覧](README.md)
