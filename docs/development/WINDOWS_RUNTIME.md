# Windows Runtime・bootstrap内部構造

一般利用の導入・認証・更新は[Windowsマニュアル](../user/WINDOWS_SETUP.md)、開発依存と検証は[開発手順](DEVELOPMENT.md)へ分離しています。

## BATとPowerShellの責務

**日本語の文字化け対策:** 入口の`setup.bat`はASCIIだけで記述した起動用ファイルです。従来のPython導入処理は`setup-runtime.bat`に分け、日本語の案内と認証制御はUTF-8 BOM付き`scripts/setup-ui.ps1`（Windows PowerShell）から行います。Windowsの`cmd.exe`でUTF-8の日本語を直接解釈させないため、文字化けや日本語がコマンドとして実行される問題を回避します。ダブルクリックするファイルは引き続き**`setup.bat`だけ**です。


通常起動は`mcp status`で未認証（exit 3）と通信失敗を区別し、未認証時だけ共通CLIの`mcp auth`を呼びます。既存認証があれば再利用し、status/toolsに失敗した場合は成功表示をせず停止します。`--no-pause`は待機と認証を、`--skip-auth`は認証を省略します。

## Runtimeの構成と再構築

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


## データ・認証境界

OAuth tokenは通常ユーザーのWindows Credential Managerへkeyring経由で保存し、平文ファイルへfallbackしません。`.local/`はOAuth補助情報・lock・cache・管理Watchlist mapping用です。ユーザープロファイルの代替ではなく、runtimeの再構築時に削除する必要もありません。

正常なruntimeを再利用しても依存導入を継続し、一般setupではrequirements.txt（runtimeのみ）を使います。開発用pytest/ruffはrequirements-dev.txtから明示導入します。Job別BAT・system Python・恒久PATH変更は追加しません。

新しい展開先へ旧Taskやmappingを自動移行せず、フォルダ削除でcredentialやTaskを自動削除することもありません。更新・利用終了は[利用者向け注意](../user/WINDOWS_SETUP.md#更新利用終了)を確認します。

## 過去の確認と実装境界

[2026-10-18実機記録](../archive/WINDOWS_VERIFICATION_2026-10-18.md)と[RC判定履歴](../archive/RELEASE_CANDIDATE.md)を参照します。独立した新規Windowsユーザーの初回OAuthは未検証です。保存済み認証での成功と混同しません。全米株builtinはProvider制約で未対応のまま、us_sector_morningはenabled=falseです。

[開発索引](README.md)
