# Windows Embedded Python セットアップ

Windowsでは、システムPythonをインストールせずにRepository内のEmbedded Pythonで実行できます。

## 対象

- 64-bit Windows（amd64）
- 通常ユーザー権限
- PowerShellが利用可能
- 初回セットアップ時に次のHTTPSアクセスが可能
  - `python.org`
  - `bootstrap.pypa.io`
  - Python package index / package配布先
- TradingView MCP利用時は対象TradingViewプランが必要

管理者権限、恒久的なPATH変更、Pythonのレジストリ登録は不要です。

## 初回セットアップ

Repository rootで `setup.bat` を実行します。

```bat
setup.bat
```

非対話実行ではpauseを抑止できます。

```bat
setup.bat --no-pause
```

セットアップは次を行います。

1. Python 3.12.8 Embedded packageを `runtime/python-3.12.8/` へ取得
2. Embedded Pythonの `python312._pth` で `import site` を有効化
3. 必要な場合だけpipをbootstrap
4. build backendをEmbedded Pythonへ導入
5. `requirements.txt` 経由でproject + runtime依存のみをeditable install。開発ツールは導入しません
6. 最後に共通 `app.bat --help` が起動できることを検証

システムPythonは参照しません。`setenv.bat` が起動プロセス内だけEmbedded PythonをPATH先頭へ置き、`PYTHONHOME` / `PYTHONPATH` をクリアします。Windowsのユーザープロファイル、Credential Manager、既定ブラウザ、TEMPは置き換えません。

runtimeの再利用前に、`python.exe`・`python312._pth`・標準ライブラリZIP・DLLを確認し、Python 3.12.8の起動とSSL・site設定も検査します。不完全な場合は`runtime/python-3.12.8/`だけを再構築します。正常なruntimeは再利用し、依存導入は再実行します。ZIP由来のCRLFとLFの両方でsite設定を補正できます。

## MCP認証

セットアップ直後は、まずCLIへ到達できることを確認できます。

```bat
app.bat mcp status
```

まだ認証していない場合、これは異常ではありません。`AUTH_REQUIRED` のJSONを返して終了コード3になります。`mcp status` 自体はブラウザ認証を開始しません。

初回認証は明示的に実行します。

```bat
app.bat mcp auth
```

既定ブラウザでTradingViewの認可を完了した後、再確認します。

```bat
app.bat mcp status
app.bat mcp tools
```

OAuth token等は平文Repositoryファイルへ保存せず、`keyring` 経由でWindows Credential Managerを利用します。

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

通常は `setup.bat` の再実行で十分です。

アプリを終了してから再実行してください。`python.exe`が残っていても、標準ライブラリやDLLの欠落・起動検査の失敗を検出した場合は自動再構築します。依存パッケージの導入に失敗した場合も、原因を解消して同じsetupを再実行できます。

`.local/` はOAuth補助情報・lock・cache等のアプリ固有ローカルデータです。runtime再構築のために削除する必要はありません。認証情報の本体はWindows Credential Manager側です。

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
