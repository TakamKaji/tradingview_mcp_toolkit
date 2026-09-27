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
5. `requirements.txt` 経由でproject + dev依存をeditable install
6. 最後に共通 `app.bat --help` が起動できることを検証

システムPythonは参照しません。`setenv.bat` が起動プロセス内だけEmbedded PythonをPATH先頭へ置き、`PYTHONHOME` / `PYTHONPATH` をクリアします。Windowsのユーザープロファイル、Credential Manager、既定ブラウザ、TEMPは置き換えません。

途中で壊れたruntime directoryだけが残っている場合、`python.exe` が存在しなければそのdirectoryを削除して再構築します。正常な `python.exe` がある場合はruntimeを再利用し、依存導入は再実行します。

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
python -m pytest -rs
python -m ruff check .
```

通常利用は `app.bat <command>` を優先してください。JobごとのBATは作りません。

## 再セットアップ

通常は `setup.bat` の再実行で十分です。

Embedded Python本体が破損し、`python.exe` 自体は残っている場合だけ、アプリを終了した上で `runtime/python-3.12.8/` を削除してから `setup.bat` を再実行します。

`.local/` はOAuth補助情報・lock・cache等のアプリ固有ローカルデータです。runtime再構築のために削除する必要はありません。認証情報の本体はWindows Credential Manager側です。

## Phase 9との関係

Phase 10のWindows bootstrap / DocsはPhase 9の米国セクター集計から独立しています。Phase 9 builtinが未実装でも、MCP認証、通常Screening、Job、Scheduler、公開read-only sampleは利用できます。
