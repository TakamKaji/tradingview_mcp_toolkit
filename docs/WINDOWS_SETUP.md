# Windows Embedded Python セットアップ

Windowsでは、システムPythonをインストールせずにRepository内のEmbedded Pythonで実行できます。

## 対象

- 64-bit Windows（amd64）
- 通常ユーザー権限
- PowerShellが利用可能
- 初回セットアップ時に次のHTTPSアクセスが可能
  - `www.python.org`
  - `bootstrap.pypa.io`
  - 標準PyPI利用時は `pypi.org` / `files.pythonhosted.org`（独自indexを設定している環境ではその配布先）
- MCP利用時は `mcp.tradingview.com`、ブラウザ認証では `www.tradingview.com` 等の公式認証先へのHTTPS接続が必要
- 明示的な初回OAuthだけ、ローカルの `127.0.0.1:8765` で認可callbackを受信
- TradingView MCP利用時はEssential以上の対象有料プランが必要。試用プランは対象外（2026-10-19の[公式案内](https://www.tradingview.com/mcp/docs)を確認。条件は公式案内を優先）

管理者権限、恒久的なPATH変更、Pythonのレジストリ登録は不要です。

## 初回セットアップ

**利用者はRepositoryをダウンロード・展開したフォルダで `setup.bat` をダブルクリックするだけです。** 管理者として実行する必要はありません。通常実行では、Python導入から公式TradingViewのブラウザOAuth認証、MCP接続確認まで1回で進みます。

```bat
setup.bat
```

画面には日本語で進捗と対処法が表示されます。初回ログインが必要なときだけ既定ブラウザを開きます。TradingViewの認可画面でログイン・許可操作をしてください。ログイン後は自動で元のセットアップ画面に戻り、`mcp status`・`mcp tools`が正常かを検証します。

**検証・自動化用オプション：** `setup.bat --no-pause` は従来の無人テスト用途を維持するため、pauseだけでなくブラウザOAuthも**起動せず**、PythonおよびRuntime依存の導入とCLI起動のみ行います。`setup.bat --skip-auth` は画面を閉じずに同じ「認証を省いた導入」を行います。オプションを省略した通常のダブルクリックが、認証まで完了する利用者向けです。

```bat
setup.bat --no-pause
setup.bat --skip-auth
```

セットアップは次を行います。

1. Python 3.12.8 Embedded packageを `runtime/python-3.12.8/` へ取得
2. Embedded Pythonの `python312._pth` で `import site` を有効化
3. 必要な場合だけpipをbootstrap
4. build backendをEmbedded Pythonへ導入
5. `requirements.txt` 経由でproject + runtime依存のみをeditable install。開発ツールは導入しません
6. 共通 `app.bat --help` の起動を確認
7. 通常起動時は `mcp status` で認証状態を確認。未認証（`AUTH_REQUIRED` / exit 3）なら `mcp auth` を起動してブラウザ認可を開始
8. 認可後（または既に認証済みの場合）は `mcp status` と `mcp tools` の成功を確認して完了表示。MCPの失敗は成功扱いしない

システムPythonは参照しません。`setenv.bat` が起動プロセス内だけEmbedded PythonをPATH先頭へ置き、`PYTHONHOME` / `PYTHONPATH` をクリアします。Windowsのユーザープロファイル、Credential Manager、既定ブラウザ、TEMPは置き換えません。

runtimeの再利用前に、`python.exe`・`python312._pth`・標準ライブラリZIP・DLLを確認し、Python 3.12.8の起動とSSL・site設定も検査します。不完全な場合は`runtime/python-3.12.8/`だけを再構築します。正常なruntimeは再利用し、依存導入は再実行します。ZIP由来のCRLFとLFの両方でsite設定を補正できます。

## MCP認証

**通常の `setup.bat` をダブルクリックした場合、認証と接続確認は自動実行されます。** 初回起動時の `AUTH_REQUIRED` は想定された状態であり、ブラウザ認証へ進む合図です。認証が残っている再セットアップ時はブラウザを開かず、現在の認証を再利用します。

`mcp status`が通信障害・Providerエラーなどで失敗した場合は、認証情報を消したり新たなブラウザ認証を繰り返したりせず、その場でエラーを表示して停止します。MCP認可が失敗した場合にもRuntimeと既存認証情報は残すため、通信環境を整えて `setup.bat` を再実行できます。

ログイン済みの動作確認や認証失効時の診断が必要な場合のみ、手動CLIを使用します。

```bat
app.bat mcp status
app.bat mcp auth
app.bat mcp tools
```

`mcp status` 自体はブラウザを開きません。`mcp auth`は明示的な認可操作です。OAuth token等は平文Repositoryファイルへ保存せず、`keyring` 経由でWindows Credential Managerを利用します。セットアップはWatchlist書込み、Scheduler Task登録、実Screeningを自動実行しません。

## 公開用read-onlyサンプル

初回確認には `public_sample_screen_daily` を使えます。

```bat
app.bat run public_sample_screen_daily
```

このJobは既定で:

- `enabled=false` — `schedule apply` の登録対象外
- `save=true` — 結果JSONは保存
- `watchlistSync=false` — TradingView Watchlistへ書き込まない

手動 `run` はenabled=falseでも実行できます。参照するScreeningは `screenings/sample_standard_screen.json` です。

## 開発・診断

Embedded Pythonを選択したコンソールが必要なら:

```bat
console.bat
```

その中で:

```bat
python -m pip install --no-build-isolation -r requirements-dev.txt
python -m pytest -rs
python -m ruff check .
```

先頭のコマンドは開発・テスト環境で初回だけ実行します。一般利用の `setup.bat` には `pytest` / `ruff` を含めません。通常利用は `app.bat <command>` を優先してください。JobごとのBATは作りません。

## 再セットアップ

通常は `setup.bat` の再ダブルクリックで十分です。認証済みならログイン画面を再表示せず、MCP接続を確認します。未認証のときだけブラウザOAuthが必要です。

アプリを終了してから再実行してください。`python.exe`が残っていても、標準ライブラリやDLLの欠落・起動検査の失敗を検出した場合は自動再構築します。依存パッケージの導入に失敗した場合も、原因を解消して同じsetupを再実行できます。

`.local/` はOAuth補助情報・lock・cache等のアプリ固有ローカルデータです。runtime再構築のために削除する必要はありません。認証情報の本体はWindows Credential Manager側です。

## 更新・利用終了・認証失効

更新時は新しいソースを別ディレクトリへ展開し、setup後に定義を確認してください。既存のscreenings/jobs、保存結果、`.local/managed_watchlists.json` 等は必要に応じて利用者がバックアップし、更新のために旧環境を削除しないでください。新しいsetupは旧ディレクトリのTaskやmappingを自動移行しません。

利用終了時も、ディレクトリ削除だけでは登録済みScheduler TaskやCredential Managerの情報は消えません。登録状況を確認し、Taskの削除やTradingView側の連携解除は利用者が正規の手順で判断してください。このアプリは削除・失効を自動実行しません。

AUTH_REQUIREDになった場合は `app.bat mcp auth` で正規のブラウザ認証を明示的にやり直します。tokenをファイルに書き出して移行したり、再認証のために既存credentialを一括削除したりしないでください。

## 2026-10-18の実機確認

Windows実機のソース検証コピーに空のruntimeから導入しました。プロセスのPATHをWindows標準ディレクトリだけにし、system Pythonを利用しない状態で以下を確認しています。

- `setup.bat --no-pause`: Python 3.12.8、pip、依存導入、共通CLI起動まで成功。
- 同じsetupの再実行: 正常runtimeを再利用して成功。
- 検証コピーの `python312.zip` だけを退避した状態: `python.exe` が残っていてもruntimeを再構築し、`.local` 内の確認用ファイルを保持。
- `python312._pth` のCRLF/LF双方: `import site` 補正と再実行のテストに成功。
- `app.bat mcp status` / `app.bat mcp tools`: 通常ユーザーの保存済みcredentialで認証、35 ToolのDiscoveryに成功。
- `app.bat run public_sample_screen_daily`: success、50件をJSON保存、Watchlist同期なし、errors空。

これは既存Windowsユーザー上でのPython未導入相当の検証です。新規OS・新規アカウントでの初回OAuthは実施していません。既存credentialとownership mappingは保持し、Watchlist/Alert WriteやTask Scheduler登録・削除は行っていません。

## Phase 9との関係（実装境界）

Phase 9のbuiltin集計・Job統合は実装済みです。ただしTradingView公式MCP Betaが条件なし全米株Screenerを拒否し、全米株の完全取得手段も未確認のため、同梱の `us_sector_morning` は `enabled=false` です。S&P 500限定503銘柄での集計・保存は実機検証済みですが、全米株集計が利用可能という意味ではありません。一般Screening、認証、Job、Scheduler、read-only sampleは通常通り利用できます。公開前の確認は[Release Candidate Gate](RELEASE_CANDIDATE.md)に従ってください。
