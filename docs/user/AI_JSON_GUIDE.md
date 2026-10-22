# AIでScreening・JobのJSONを作る

この文書は**ChatGPT・Codexなど共通の作成ガイド**です。AIに公開リポジトリを読ませ、会話で決めた条件から本アプリ用JSONを作ります。利用者にCodex・GitHub・Pythonの導入は必須ではありません。

## AIが確認するファイル（この順）

1. [このガイド](AI_JSON_GUIDE.md)
2. [Screeningの全項目・条件・制約](SCREENING_MANUAL.md)
3. [Jobの全項目・時刻・副作用](SCHEDULE_MANUAL.md)
4. 実際のサンプル：[Screening](../../screenings/public_japan_value.json)・[読み取り専用Job](../../jobs/public_sample_screen_daily.json)
5. 必要なら検証用ソース：[Screening schema](../../src/tradingview_screening/screening/schema.py)・[Job schema](../../src/tradingview_screening/jobs/schema.py)

**必ず実際のファイルを読んでから作成してください。** リポジトリを読み込めないAIは、閲覧したふりをせず、利用者に上記資料の添付を求めてください。Privateの間は通常の公開URLでは閲覧できません。

## 利用者が送る依頼文

> https://github.com/TakamKaji/tradingview_mcp_support の `docs/user/AI_JSON_GUIDE.md` とリンク先の最新仕様、JSONサンプルを確認してください。私の希望を聞いて、アプリで動くScreening JSONを作成してください。必要ならJob JSONも作成してください。できない条件を推測で置き換えずに説明してください。最初はWatchlist書き込みと定期登録を無効にしてください。完成ファイルと保存場所・実行方法を教えてください。

例：「日本株でPER15倍以下、予想配当利回り3%以上、出来高順20件を検索したい」

- **ChatGPT**：`screenings/<name>.json`のダウンロードファイルを生成し、ユーザーがZIP展開先の`screenings/`へ保存します。Jobも希望する場合は`jobs/`へ。通常のチャットではユーザーPCのフォルダを直接編集しません。
- **Codex**：ローカルのアプリフォルダを開き、同じ仕様から新規JSONを作成・確認します。GitHubへのpush・PRは必要ありません。

## AIが守るルール

- **正しいJSONだけをファイルへ保存。** UTF-8（BOMなし）、コメント・余計な末尾カンマ・Markdownコードフェンスなし。JSON全文を省略しない。
- 新しいファイル名は英数字で始め、続きは英数字・`_`・`-`のみ。パス・空白・日本語・Windows予約名は使用禁止。`screenings/<name>.json`や`jobs/<name>.json`の`<name>`をJSON内の`name`と一致させ、既存サンプルを上書きしない。
- Screeningの`schemaVersion`は整数`1`、`limit`は整数1～1000、`columns`は空でない配列。通常の数値`filters`は`[下限, 上限]`で、片側の制限なしは`null`。例：`"pe":[0,15]`、`"div_yield":[3,null]`。フィルター名と取得列名は異なる場合がある。
- **Providerの未確認フィルター・列・市場・presetを創作しない。** 未対応・不明な希望は利用者に伝え、勝手に別条件や別Universeへ置き換えない。`mcp tools`はツール一覧表示であり、任意Toolの実行用CLIではない。
- ScreeningのWatchlistは最初`{"enabled":false}`。Jobは`schemaVersion=1`、`task.type="screening"`、`task.definition`に**Screening名**、`enabled=false`、`output.save=true`、`output.watchlistSync=false`。Jobの`schedule`は手動実行でも必須。現行Schedulerは`daily`、`HH:MM`、`Asia/Tokyo`のみに対応。時刻の希望がなければ例示時刻を明示し、実際の定期登録をしない。
- **Watchlistへの銘柄追加・削除やTask登録・削除はユーザーの明示依頼なしに行わない。** 同梱`sample_screen_daily`は`enabled=true`かつWriteあり。`schedule apply`は有効な**全Job**を登録・更新するため、自動実行しない。
- 全米株の条件なし全件取得はProvider制約で未対応。OHLCV・ニュース・財務を直接取得する専用CLI・定期取得Jobも未実装。Schemaに合うこととTradingViewで取得成功することは別。未実行の実機検証を成功扱いしない。

## 成果物と確認

1. 完全な`screenings/<name>.json`と、希望された場合は`jobs/<name>.json`を用意する。
2. 希望した条件とJSONフィールドの対応、未対応・未確認事項を短く説明する。
3. ChatGPTではダウンロード可能なファイル（環境上できなければ完全なJSON本文）、Codexでは指定フォルダへの新規保存を優先する。
4. 初回確認はWindowsなら`app.bat screen <screening_name>`、結果は`app.bat results latest <screening_name>`。Jobなら`app.bat run <job_name>`。結果参照は**Job名でなくScreening名**。Dockerは[Docker導入](DOCKER.md)を参照。
5. 修正依頼時は指定された条件だけを変え、既存ファイルを意図せず変更しない。

## English note

**For ChatGPT or Codex:** Read this guide, the linked Screening and Job manuals, and the actual example JSON files from the repository before generating files. Ask the user to describe a market, filters, columns and optional job schedule. Create full valid UTF-8 JSON files for `screenings/` and, if requested, `jobs/`. Keep Watchlist writes and scheduling disabled by default. Do not invent filter names or silently replace unsupported requests. ChatGPT can provide downloadable files; Codex can write into a local project folder. The source manuals are Japanese, but JSON keys are language-independent.

[AI CLI操作](AI_USAGE.md) / [利用者マニュアル](README.md)
