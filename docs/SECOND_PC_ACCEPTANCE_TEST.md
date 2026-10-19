# 別PCでの初回導入〜全テスト（Windows / v0.1.0b1 / PR #29）

## 推奨：BATファイル1本で全自動実行

**現在はこちらを使用してください。** [second_pc_full_test.bat](../second_pc_full_test.bat) をGitHub上で開き、右上の「Download raw file」で別PCへ保存したら、**管理者として実行せず普通にダブルクリック**するだけです。

バッチ内でGit確認／未導入ならwinget導入、Private GitHubリポジトリclone、Embedded Pythonセットアップ、初回TradingView OAuth、公式MCP read-only、公開Job2回・JSON保存・履歴比較、pytest全件、ruff・git差分、認証永続性まで順次実行します。BATは`setup.bat --no-pause`を指定して**そこでブラウザ認証を起動せず**、直後にOAuthだけを独立した受入テストとして実行します。一般利用者の通常`setup.bat`ダブルクリックでは、初回OAuthもセットアップ内に含まれます。GitHubとTradingViewの認証だけブラウザ操作が必要です。wingetを利用できない場合はGitの手動導入が必要になるため、その場合だけバッチ画面の案内に従ってください。

終了後に `%USERPROFILE%\TV_MCP_BETA_TEST_RESULT.txt` が作成されます。**このレポートだけ本チャットに貼ってください。** pytestの成功・skip件数も自動記録されます。OAuth tokenやGitHub認証情報はレポートに出しません。失敗時はバッチが止まり、既存フォルダや認証情報を削除せず失敗理由を報告します。

以下の手動コピペ手順は、BATが途中で失敗した場合の切り分け用として残します。

この手順は、自分の**別PC**で初めてTradingView MCP Supportを導入し、実際のTradingViewログイン、Read-only実MCP、保存・履歴比較、全pytest/ruffを行うためのものです。**通常のPowerShell（管理者として実行しない）**に、各コードブロックを上から順番に貼り付けます。途中で失敗したら、次へ進まずその結果を確認します。

- Windows 10/11 64-bit、インターネット接続、TradingView公式MCP対象プランが必要。**システムPythonのインストールは不要**。
- リポジトリはPrivateなので、自分のGitHubアカウントのアクセス権が必要。
- **mainではなく、PR #29ブランチ**を取得する。ダウンロード先は自分のユーザーフォルダの「TV MCP Beta Test」（空白入り）。
- 元のPCから認証情報・.local・保存結果をコピーしない。Watchlist/Alert Write、Task Scheduler登録/削除は実行しない。

## 0. Git for Windowsの準備（初回だけ）

PowerShellで次を実行。

~~~powershell
git --version
~~~

Gitのバージョンが表示されればOK。見つからなければ次を実行して、**完了後にPowerShellを閉じて開き直す**。

~~~powershell
winget install --id Git.Git -e --source winget
~~~

wingetがない場合はGit公式 https://git-scm.com/downloads/win からインストールする。

## 1. GitHubからPR #29を初回ダウンロード

新しいPowerShellで以下を**まとめて貼り付け**。

~~~powershell
$ErrorActionPreference = 'Stop'
$TestDir = Join-Path $env:USERPROFILE 'TV MCP Beta Test'
if (Test-Path -LiteralPath $TestDir) { throw "フォルダが既にあります。削除せず内容を確認: $TestDir" }
git clone --branch chore/issue-28-release-candidate-b1 --single-branch https://github.com/TakamKaji/tradingview_mcp_support.git $TestDir
if ($LASTEXITCODE -ne 0) { throw 'GitHub clone失敗。Private repoにアクセスできるGitHubアカウントで認証してください。' }
Set-Location -LiteralPath $TestDir
git branch --show-current
git rev-parse HEAD
git status --short
~~~

GitHubの認証画面が出たら自分のアカウントでログイン。ブランチがchore/issue-28-release-candidate-b1で、git status --shortが空ならOK。表示されたHEAD SHAを最後に報告する。既存フォルダを削除しない。

## 2. 初回セットアップ（Pythonは自動取得）

同じPowerShellに貼り付け。

~~~powershell
& .\setup.bat --no-pause
if ($LASTEXITCODE -ne 0) { throw 'setup失敗。ここで中止してください。' }
& .\app.bat --help
if ($LASTEXITCODE -ne 0) { throw 'app起動失敗。' }
& .\runtime\python-3.12.8\python.exe -I -c 'import sys,importlib.metadata as m,tradingview_screening as t; print("Python",sys.version.split()[0],"isolated",sys.flags.isolated,"installed",m.version("tradingview-mcp-support"),"package",t.__version__)'
if ($LASTEXITCODE -ne 0) { throw 'version確認失敗。' }
~~~

期待：Setup complete、Python 3.12.8、isolated 1、installed/package とも0.1.0b1。

## 3. 初回TradingViewログイン（新PCでは重要）

まず未認証の状態を確かめる。

~~~powershell
& .\app.bat mcp status
$BeforeAuth = $LASTEXITCODE
"認証前exit code: $BeforeAuth"
if ($BeforeAuth -eq 3) {
  'PASS: AUTH_REQUIRED（初回未認証の正常結果）'
} elseif ($BeforeAuth -eq 0) {
  '注意：既にcredentialあり。ゼロからの初回OAuth試験ではない。'
} else {
  throw '未認証以外のエラー。次の手順に進まない。'
}
~~~

新しいユーザー環境ならAUTH_REQUIRED / exit 3が期待結果。statusだけではブラウザは開かない。

**次のブロックでブラウザ認証が始まる**。TradingViewにログインし、認可画面を操作する。

~~~powershell
& .\app.bat mcp auth
if ($LASTEXITCODE -ne 0) { throw '初回OAuthに失敗。' }
& .\app.bat mcp status
if ($LASTEXITCODE -ne 0) { throw '認証後statusに失敗。' }
& .\app.bat mcp tools
if ($LASTEXITCODE -ne 0) { throw 'Tool Discoveryに失敗。' }
~~~

期待：auth / status / tools成功。2026-10-19時点の既知Toolは35件。TradingView公式Betaなので実際の増減は内容を確認すること。tokenやブラウザ認可codeをログ・チャットに貼らない。

## 4. 実MCP read-only、JSON保存、履歴、比較

このブロックはTradingViewの**Readのみ＋PC内のJSON保存**。意図しないWatchlist WriteやScheduler Task作成はしない。初回compareのNO_BASELINE/exit1は正常。

~~~powershell
& .\app.bat jobs list
if ($LASTEXITCODE -ne 0) { throw 'jobs list失敗。' }
$Sector = Get-Content .\jobs\us_sector_morning.json -Raw | ConvertFrom-Json
if ($Sector.enabled -ne $false -or $Sector.output.watchlistSync -ne $false) {
  throw '全米株Jobの安全設定が異なります。'
}
'PASS: 全米株Jobはdisabled'

& .\app.bat run public_sample_screen_daily
if ($LASTEXITCODE -ne 0) { throw '公開read-only Job 1回目失敗。' }
& .\app.bat results latest sample_standard_screen
if ($LASTEXITCODE -ne 0) { throw 'latest失敗。' }
& .\app.bat results history sample_standard_screen --limit 10
if ($LASTEXITCODE -ne 0) { throw 'history失敗。' }
& .\app.bat results compare sample_standard_screen
if ($LASTEXITCODE -ne 1) { throw '初回compareはNO_BASELINE/exit1を想定。出力を確認。' }
'PASS: 1件目のcompareはNO_BASELINE（出力にNO_BASELINEがあることも確認）'

& .\app.bat run public_sample_screen_daily
if ($LASTEXITCODE -ne 0) { throw '公開read-only Job 2回目失敗。' }
& .\app.bat results history sample_standard_screen --limit 10
if ($LASTEXITCODE -ne 0) { throw '2回分のhistory失敗。' }
& .\app.bat results compare sample_standard_screen
if ($LASTEXITCODE -ne 0) { throw '2件比較に失敗。' }
& .\app.bat schedule list
if ($LASTEXITCODE -ne 0) { throw 'Schedulerのread-only列挙に失敗。' }
'PASS: Read-only・保存・履歴比較・Task列挙'
~~~

期待：公開Jobが2回ともstatus=success / saved=true / watchlistSync=null、historyで2件、2件目のcompareはfingerprint一致・成功。Provider件数や市場データ値は日によって変動するので完全一致を条件としない。初回比較はNO_BASELINE。schedule listは登録せず列挙するだけ。

## 5. 全pytest・ruff・差分チェック

通常のセットアップには開発用pytest/ruffが入っていない。今回の**全テスト**のためだけにEmbedded Pythonへ追加する。

~~~powershell
$Py = '.\runtime\python-3.12.8\python.exe'
& $Py -m pip install --no-build-isolation -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw '開発依存の導入失敗。' }
& $Py -m pytest -rs
if ($LASTEXITCODE -ne 0) { throw 'pytest失敗。原因を確認。' }
& $Py -m ruff check .
if ($LASTEXITCODE -ne 0) { throw 'ruff失敗。' }
git diff --check
if ($LASTEXITCODE -ne 0) { throw 'git diff --check失敗。' }
git status --short
git rev-parse HEAD
'PASS: pytest / ruff / diff check'
~~~

**過去の基準**：674 collected / 669 passed / 0 failed / 5 skipped。5 skipはWindowsのsymlink権限制約。別PCの権限次第で件数は変わるため、pytestの実際の結果とskip理由を記録する。ruffが成功し、git status --shortが空ならOK。

## 6. 新しいPowerShellで認証保持を確認

PowerShellを閉じて普通に開き直し、次を貼る。

~~~powershell
Set-Location -LiteralPath (Join-Path $env:USERPROFILE 'TV MCP Beta Test')
& .\app.bat mcp status
if ($LASTEXITCODE -ne 0) { throw '再起動後の認証復元に失敗。' }
& .\app.bat mcp tools
if ($LASTEXITCODE -ne 0) { throw '再起動後のTool取得に失敗。' }
'PASS: プロセスをまたいだ認証保持'
~~~

ブラウザで再認証せずstatus/toolsが成功すればOK。

## 7. ChatGPTへ報告（下だけコピペでよい）

~~~text
別PC初回受入テスト / PR #29
Windowsのバージョン：
git HEAD：
setup：PASS / FAIL
Python 3.12.8・isolated 1・0.1.0b1：PASS / FAIL
OAuth前 AUTH_REQUIRED / exit3：PASS / FAIL
初回TradingViewブラウザ認証：PASS / FAIL
status / tools：PASS / FAIL（Tool件数）
公開read-only Job 2回：PASS / FAIL
latest/history/compare（初回NO_BASELINE、2回目成功）：PASS / FAIL
schedule list：PASS / FAIL
pytest：____ passed / ____ failed / ____ skipped
ruff：PASS / FAIL
git diff --check / clean：PASS / FAIL
新PowerShellでstatus/tools：PASS / FAIL
エラーの概要：
~~~

この報告を基に、[Issue #28](https://github.com/TakamKaji/tradingview_mcp_support/issues/28)の新規環境Gate Bを判定する。

**実行禁止：** app.bat run sample_screen_daily（Watchlist Writeあり）、app.bat schedule apply/remove、Alert/WatchlistのWrite、全米株Job us_sector_morning（現行Provider拒否）。この段階ではGitHubのmerge、tag作成、リポジトリ公開設定変更もしない。
