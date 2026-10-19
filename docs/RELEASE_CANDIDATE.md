# v0.1.0b1 Windows Beta — Release Candidate Gate

このページは**公開済みリリースではなく、リリース候補の確認手順**です。Windows向け最初のβ版の可否を判定するために使用します。テスト未実行項目を完了と報告しません。

## 対象・契約

- 対象：Windows 64-bit（amd64）／一般ユーザー権限／PowerShell、インターネット接続が必要。Pythonのシステムインストール不要。
- 配布ソースから `setup.bat --no-pause` がCPython 3.12.8 Embedded、pip、Runtime依存を導入する。**完全オフライン版ではありません。**
- PythonパッケージはPEP 440 `0.1.0b1`。Git tagを作る場合は `v0.1.0b1` を候補とし、テスト合格・明示承認前に作成しません。
- TradingView公式MCPはBetaです。利用には対象のTradingView有料プランが必要です。公式Providerの制約は[SCREENING_MANUAL.md](SCREENING_MANUAL.md)を参照。
- `us_sector_morning` のsampleは `enabled=false`。公式MCPが条件なし全米株取得を拒否するため、全米株セクター集計は提供しません。S&P 500限定の503件集計成功は実測確認であって製品内の全米株集計成功ではありません。
- SchedulerはWindowsでユーザーがログオン中・Asia/Tokyo dailyのみ。既存の `sample_screen_daily` はWatchlistへWriteする設定があるため、read-only smokeには使いません。

## Gate A: ソースと配布安全性（公開前）

- [ ] GitHubの対象commit/branchを固定し、公開対象ソース一式と `LICENSE` を確認
- [ ] パッケージ `0.1.0b1` と `__version__` が一致。release notes、tag候補の表示が整合
- [ ] `runtime/`、`.local/`、`results/`、`.pytest-tmp/`、`.git/`、token・Credential・所有Watchlist mapping・実マーケットデータ保存物を配布物へ混入させない
- [ ] 公開前の秘密情報・個人情報・ライセンス点検を実施
- [ ] ソースZIP/リポジトリ取得から起動できることを実機確認し、依存のネット接続先を案内

## Gate B: 新規Windows環境でのセットアップ（要実機）

既存tokenを流用しない**新しいWindowsユーザーまたは独立したテスト環境**で検証します。パスに空白を含む展開先でも確認します。

```bat
setup.bat --no-pause
app.bat --help
app.bat mcp status
```

期待結果：システムPython不使用でインストール成功。`mcp status` は未認証なら `AUTH_REQUIRED`（exit 3）。この操作は自動的にブラウザを開かない。

次に**明示的に初回OAuth**を行います。

```bat
app.bat mcp auth
app.bat mcp status
app.bat mcp tools
app.bat jobs list
```

期待結果：ブラウザ認可→Windows Credential Manager保存→statusとTool Discovery成功。検証時の既知Toolは35件だが、BetaのTool増減は差分として確認し、追加Toolだけで全機能が故障したと判断しない。プロセス再起動後もstatus成功を確認。秘密・token・認可codeをテストログに保存しない。

## Gate C: Read-onlyシナリオ（要実機）

```bat
app.bat run public_sample_screen_daily
app.bat results latest sample_standard_screen
app.bat results history sample_standard_screen --limit 10
app.bat results compare sample_standard_screen
```

`public_sample_screen_daily`は `enabled=false / save=true / watchlistSync=false`。手動実行は可能で結果JSONを保存します。`compare` は初回の1件だけなら `NO_BASELINE` で非成功（仕様通り）。同じ定義で2回成功した後は銘柄・指標値の前回比較ができることを確認。`completeCoverage=false` の場合に、観測されない銘柄を「条件脱落」と断定しない。Providerが一時的な業務エラーを返した場合は、その事実と再検証条件を記録する。

```bat
app.bat schedule list
```

これはread-onlyの列挙のみ。`schedule apply`、`schedule remove`、Watchlist/AlertのWrite系操作はこのGateで実行しません。`app.bat run us_sector_morning` をリリース成功テストにしない。

## Gate D: 回帰テスト（統合main＋候補HEADで1回）

開発者用コンソールで開発依存を**明示インストール**して実行する（一般利用者の`setup.bat`はpytest/ruffを導入しません）。

```bat
console.bat
python -m pip install --no-build-isolation -r requirements-dev.txt
python -m pytest -rs
python -m ruff check .
git diff --check
```

- [ ] Python Unit Testとruffの結果・実行HEADを記録
- [ ] symlink権限でskipした件数と理由を区別し、権限あり環境での再確認要否を判断
- [ ] 既存Phase 10/11とPhase 9 builtin統合の回帰を確認
- [ ] テスト・ビルドによる不要な生成物、認証情報、ローカルデータをコミットしていないことを確認

## Gate E: 仕様・記録・リリース判断

- [ ] Google Drive正本の`tradingview_screening_system_spec.md`とRepository版を同期し、読み戻し一致を確認する。**2026-10-19時点で正本のPhase 9 `enabled=true` が残っており、未完了。**
- [ ] [Issue #18](https://github.com/TakamKaji/tradingview_mcp_support/issues/18)には全米株UniverseのProvider制約を追跡対象として残す
- [ ] 配布先・プライベートRepoの公開方法・更新／削除／認証失効時の利用案内を確認
- [ ] `v0.1.0b1` を公開するか明示判断する。承認前は公開設定・tag・GitHub Release・mergeを自動で実行しない

## Release Candidate判定

**Go**：Gate A〜Eの必要項目が実際に検証済みで、既知の公式MCP Beta制限をユーザー向けマニュアルに記載し、公開物に秘密情報がない。

**No-Go**：初回OAuth不可、read-only基本Jobの永続的な失敗、バージョン／配布ファイル不整合、secret混入、未対応機能を成功と偽って表示する状態。実機未実施項目を成功扱いした場合もNo-Go。

検証結果は[Issue #28](https://github.com/TakamKaji/tradingview_mcp_support/issues/28)に実行環境・HEAD・結果・未実施理由とともに記録する。
