> **過去の検証・受入手順の保存版**：本文のブランチ・PR状態・未実施項目・判定は記録当時のものです。PR #19・#29はその後mainへ統合済みです。この文書は今回の再試験結果や公開済みリリースを示しません。現在の導入は[Windowsマニュアル](../user/WINDOWS_SETUP.md)、記録の時系列は[履歴索引](README.md)を参照してください。

# v0.1.0b1 Windows Beta — Release Candidate Gate

このページは**公開済みリリースではなく、リリース候補の確認手順**です。Windows向け最初のβ版の可否を判定するために使用します。テスト未実行項目を完了と報告しません。

**最新の判断（2026-10-19 JST）**：所有者本人が**文字化け修正版の通常 `setup.bat` ダブルクリックをWindows実機で確認し「オッケー」と報告**。既存credential利用でのMCP接続・Tool Discoveryを含む日本語案内のスモークはPASS。個人利用に限り、新規独立Windowsユーザーの初回OAuth再試験は未実施リスクを受容し、必須Blockerから外した。**PR #29はレビュー可能／main統合判断対象**。これはGitHub Release公開・tag発行の承認ではない。


## 対象・契約

- 対象：Windows 64-bit（amd64）／一般ユーザー権限／PowerShell、インターネット接続が必要。Pythonのシステムインストール不要。
- 配布ソースから `setup.bat --no-pause` がCPython 3.12.8 Embedded、pip、Runtime依存を導入する。**完全オフライン版ではありません。**
- PythonパッケージはPEP 440 `0.1.0b1`。Git tagを作る場合は `v0.1.0b1` を候補とし、テスト合格・明示承認前に作成しません。
- TradingView公式MCPはBetaです。利用には対象のTradingView有料プランが必要です。公式Providerの制約は[SCREENING_MANUAL.md](../user/SCREENING_MANUAL.md)を参照。
- `us_sector_morning` のsampleは `enabled=false`。公式MCPが条件なし全米株取得を拒否するため、全米株セクター集計は提供しません。S&P 500限定の503件集計成功は実測確認であって製品内の全米株集計成功ではありません。
- SchedulerはWindowsでユーザーがログオン中・Asia/Tokyo dailyのみ。既存の `sample_screen_daily` はWatchlistへWriteする設定があるため、read-only smokeには使いません。

## Gate A: ソースと配布安全性（公開前）

- [x] GitHubの対象commit/branchを固定し、公開対象ソース一式と `LICENSE` を確認
- [x] パッケージ `0.1.0b1` と `__version__` が一致。release notes、tag候補の表示が整合
- [x] `runtime/`、`.local/`、`results/`、`.pytest-tmp/`、`.git/`、token・Credential・所有Watchlist mapping・実マーケットデータ保存物を配布物へ混入させない
- [x] 公開前の秘密情報・個人情報・ライセンス点検を実施
- [x] ソースZIP/リポジトリ取得から起動できることを実機確認し、依存のネット接続先を案内

2026-10-19確認：基点mainは `4bf338b391fd735a011ea566108ec3135c2f215d`、実行対象は本ブランチの `66a5e77d4acd45686cfb3a97652ff5f2c815aafb`。今回の追加変更は文書だけです。Git管理対象96ファイルを `git archive` した検証用ソースZIPで起動しました。最終文書commitと候補ZIPのSHA-256はIssue #28 / PR #29に記録します。

検証ZIPに禁止ディレクトリはなく、秘密情報・個人パスのパターン検出は0件。設定・LICENSE・fixture構成も点検しました。fixtureは公式ToolのinputSchemaメタデータ2件で、実銘柄結果の保存物ではありません。MITのLICENSEを含み、第三者依存のバイナリはZIPへ同梱せずsetupで取得します。公開先の承認はGate Eで別に判定します。

別PCのユーザー本人による一括テストは、[second_pc_full_test.bat](../../second_pc_full_test.bat) を1本ダウンロードして通常ユーザーで実行してください。GitHub/TradingViewのブラウザ認証だけ手動操作が必要です。失敗時のコピペ式切り分け手順は[別PC受入手順](SECOND_PC_ACCEPTANCE_TEST.md)にあります。初回OAuth未実施のGate判定は、利用者の実測報告まで変更しません。

## Gate B: 新規Windows環境でのセットアップ（要実機）

**配布向け操作はダウンロード・展開後に `setup.bat` のダブルクリックのみ**です。2026-10-19の所有者判断で、独立OSユーザーでの初回OAuth再試験は**未検証リスクを受け入れる**方針です。これを「初回OAuth成功」と記録しません。新しいワンクリックセットアップのWindows実機スモークは、今回の変更後に別途確認します。

既存tokenを流用しない**新しいWindowsユーザーまたは独立したテスト環境**があれば追加検証できます。パスに空白を含む展開先でも確認します。

```bat
setup.bat
```

これでMCPのログイン・接続確認まで行います。**無人テスト時のみ** `setup.bat --no-pause` で認証を省略してbootstrap部分を検証できます。その場合は上記`mcp status`・`mcp auth`・`mcp tools`を別途確認します。

期待結果：システムPython不使用でインストール成功。`mcp status` は未認証なら `AUTH_REQUIRED`（exit 3）。この操作は自動的にブラウザを開かない。

次に**明示的に初回OAuth**を行います。

```bat
app.bat mcp auth
app.bat mcp status
app.bat mcp tools
app.bat jobs list
```

期待結果：ブラウザ認可→Windows Credential Manager保存→statusとTool Discovery成功。検証時の既知Toolは35件だが、BetaのTool増減は差分として確認し、追加Toolだけで全機能が故障したと判断しない。プロセス再起動後もstatus成功を確認。秘密・token・認可codeをテストログに保存しない。

**2026-10-19 当時の実測（以下は旧時点の記録）**：新規OSユーザーによる初回OAuth未実施は維持。所有者が個人利用に限り未検証リスクを了承したため、最終PR判断では必須Blockerとしていない。

- [x] 通常ユーザー権限、空白入りパス、空runtime、PATHをWindows標準のみとしてsetup成功・help成功
- [x] Python 3.12.8 / isolated=1、project・package・installed versionが0.1.0b1、pytest/ruff未導入
- [x] setup再実行で正常runtimeを再利用。通常のWindowsユーザープロファイルを維持
- [x] 別CLIプロセスのstatus成功（**同じWindowsユーザーの保存済みcredentialを使用**）
- [x] プロセス内の空storageを使う補助検証でAUTH_REQUIRED / exit3、browser呼出0・対話認証開始0・永続書込み0を確認
- [ ] 任意の追加検証：独立した新規Windowsユーザー/環境で、初回OAuth→Credential Manager保存→再起動後status/toolsを実機確認（未実施をPASSとしない）

利用可能な実行環境は既存の通常Windowsユーザーです。別ユーザーの資格情報や独立VMは利用できず、既存credential削除やOSアカウント新設で代用していません。空storageの補助検証も初回OAuth成功とは扱いません。この未実施項目がリリースBlockerです。

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

**2026-10-19判定：完了（保存済みOAuth）。** 新規setupしたruntime依存だけの専用コピーで、status / tools / jobs list / 公開Job / latest / history / compare / schedule listを確認しました。

| 確認 | 実測 |
| --- | --- |
| status / tools | success、protocol 2025-11-25 / server 1.30.0、35 Tool、missing/unexpectedとも空 |
| public sample 1回目 | success / exit0、totalCount=1860、returnedCount=50、saved=true、同期なし |
| latest / history 1件 | success / exit0 |
| compare 1件 | not_comparable / NO_BASELINE / exit1（仕様どおり） |
| public sample 2回目 | success / exit0、同一定義で50件保存 |
| history / compare 2件 | success / exit0、fingerprint一致、observed_set_only、共通50件、追加・未観測・指標変化0、総件数差0 |
| schedule list | success / exit0、管理Task 0件。列挙のみ |
| us_sector_morning | enabled=falseを確認。今回実行していない |

既存開発環境の保存結果・mappingは変更せず、検証コピー内だけに結果を保存しました。Watchlist/Alert Write、Scheduler登録・削除なし。S&P 500限定503件・20分類の過去の実測を、全米株成功とは扱いません。

## Gate D: 回帰テスト（統合main＋候補HEADで1回）

開発者用コンソールで開発依存を**明示インストール**して実行する（一般利用者の`setup.bat`はpytest/ruffを導入しません）。

```bat
console.bat
python -m pip install --no-build-isolation -r requirements-dev.txt
python -m pytest -rs
python -m ruff check .
git diff --check
```

- [x] Python Unit Testとruffの結果・実行HEADを記録
- [x] symlink権限でskipした件数と理由を区別し、権限あり環境での再確認要否を判断
- [x] 既存Phase 10/11とPhase 9 builtin統合の回帰を確認
- [x] テスト・ビルドによる不要な生成物、認証情報、ローカルデータをコミットしていないことを確認

2026-10-19、setenv.bat経由のWindows Embedded Python 3.12.8へ指定の開発依存を明示導入後、全テストを1回実行：**674 collected / 669 passed / 0 failed / 5 skipped**、ruff / git diff --check成功。実行対象の機能コードは上記66a5e77から変更していません。

skipはtest_jobsの3件、test_screening_history_compareの1件、test_validationの1件で、すべて実symlinkを作成する権限がないためです。パス逸脱はmonkeypatchでも検証済み。権限が利用できるWindowsで5件を再確認することを推奨し、未実行分をPASSとは扱いません。

## Gate E: 仕様・記録・リリース判断

- [x] Google Drive正本の`tradingview_screening_system_spec.md`とRepository版を同期し、読み戻し一致を確認する
- [x] [Issue #18](https://github.com/TakamKaji/tradingview_mcp_support/issues/18)には全米株UniverseのProvider制約を追跡対象として残す
- [x] 更新／削除／認証失効時の利用案内をWindows Setupへ記載
- [x] 個人利用は現Private Repositoryで継続すると所有者が判断
- [ ] 外部向けGitHub Release・tag・Publicへの変更は別途所有者承認（現時点では実施しない）
- [x] GitHub Release・tag・公開設定変更は未承認。PRのレビュー可能判断と一般公開承認を分離する

2026-10-19、正本19.3/19.5をenabled=false、本番Provider拒否、S&P 500限定503件成功の契約へ同期しました。全件読戻し一致を確認し、Phase 11と他セクションの不変も照合済み。Issue #18はOPEN、RepoはPRIVATEのままです。**Gate Eの仕様同期・記録は完了**。個人利用のPrivate運用は所有者確認済みだが、一般公開の承認は未取得（公開作業はしない）。

## Release Candidate判定

**Go**：Gate A〜Eの必要項目が実際に検証済みで、既知の公式MCP Beta制限をユーザー向けマニュアルに記載し、公開物に秘密情報がない。

**No-Go**：実際に試した認証やread-only基本Jobの失敗、バージョン／配布ファイル不整合、secret混入、未対応機能を成功と偽る状態。未実施項目を成功扱いした場合もNo-Go。

**PRのmain統合判断と公開リリース判断は別**。今回の所有者向けPrivate利用では独立新規Windowsユーザー初回OAuthを任意検証とする一方、一般公開の可否は将来別途承認する。

検証結果は[Issue #28](https://github.com/TakamKaji/tradingview_mcp_support/issues/28)に実行環境・HEAD・結果・未実施理由とともに記録する。

### 2026-10-19 実機報告からの日本語文字化け修正

- 実機ログでsetup自体は完了し認証・Tool Discoveryも成功。ただしUTF-8日本語を含む`setup.bat`を`cmd.exe`が誤解析し、日本語の二重化・「コマンドとして認識されません」を発生させた。
- 修正：`setup.bat`はASCII専用ランチャー、`setup-runtime.bat`は既存のPython導入（ASCIIのみ）、`scripts/setup-ui.ps1`はBOM付き日本語PowerShell UIと公式OAuth・status/tools確認に分離。
- `setup.bat`の通常ダブルクリック操作・既存認証の再利用・未認証時だけOAuth・`--no-pause`でブラウザ認証なし、という仕様は維持。
- この分離修正後のWindows実機再テストは**未実施**。静的テストとPowerShell構文テストを追加したが、旧実機結果を文字化け修正の実測PASSとは扱わない。

### 2026-10-19 ワンクリックsetup対応（追加差分）

- `setup.bat`の通常実行をPythonセットアップ→未認証時のみブラウザOAuth→status/tools確認まで統合。日本語案内、再実行時の認証スキップ、失敗時の停止・診断案内を追加。
- `--no-pause`は従来の自動化用途を保護するため認証なしのセットアップとする。一般向けは引数なしでダブルクリック。
- **この追加実装はWindows実機のクリックによるスモークテスト前**。元の2026-10-19検証結果は今回追加のsetup認証分岐を検証した証拠ではない。

### 2026-10-19 最新判定（文字化け修正後のWindows実機確認済み）

| 項目 | 判定 |
| --- | --- |
| A | 完了：配布構成・版・LICENSE・旧候補ZIPの混入点検。最終公開物は公開前に再検証 |
| B | **所有者の通常ダブルクリック実機スモークPASS**：日本語表示・既存OAuth再利用・MCP接続を確認。独立新規Windowsユーザーでの初回OAuthのみ未実施・リスク受容済み |
| C | 完了：read-only Job×2、JSON保存、最新・履歴・前回比較、Scheduler列挙 |
| D | Windows Embedded Pythonで**669 passed / 0 failed / 5 skipped**、ruff・差分成功（旧HEADでの実測）。最新のBAT/PowerShell分離後に全pytest/ruff再実行したという意味ではない |
| E | Drive正本同期・個人用Private Repo利用方針は確定。一般公開・Release・tagは未承認 |

**PR #29のレビュー／main統合判断：GO（所有者の実機スモーク結果に基づく）。**

**GitHub Release／tag／Public公開：未承認・実施しない。** これは個人用Private版のPRをReadyにすることと矛盾しない。

2026-10-19の所有者実機報告により、文字化け修正版の通常 `setup.bat` ダブルクリック経路は正常動作した。既存credentialが利用されたため、新規ユーザー初回OAuthが成功したと主張しない。残るMinorはWindows実symlink権限によりskipされた5件。全米株条件なし取得は公式Providerの制約により未対応で、Issue #18で継続する。
