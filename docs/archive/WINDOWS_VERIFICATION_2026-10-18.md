# Windows導入の実機確認（2026-10-18）

> 当時の保存済みcredentialによる検証です。新規Windowsユーザーの初回OAuth成功を示しません。[記録索引](README.md)へ戻る。

## 2026-10-18の実機確認

Windows実機のソース検証コピーに空のruntimeから導入しました。プロセスのPATHをWindows標準ディレクトリだけにし、system Pythonを利用しない状態で以下を確認しています。

- `setup.bat --no-pause`: Python 3.12.8、pip、依存導入、共通CLI起動まで成功。
- 同じsetupの再実行: 正常runtimeを再利用して成功。
- 検証コピーの `python312.zip` だけを退避した状態: `python.exe` が残っていてもruntimeを再構築し、`.local` 内の確認用ファイルを保持。
- `python312._pth` のCRLF/LF双方: `import site` 補正と再実行のテストに成功。
- `app.bat mcp status` / `app.bat mcp tools`: 通常ユーザーの保存済みcredentialで認証、35 ToolのDiscoveryに成功。
- `app.bat run public_sample_screen_daily`: success、50件をJSON保存、Watchlist同期なし、errors空。

これは既存Windowsユーザー上でのPython未導入相当の検証です。新規OS・新規アカウントでの初回OAuthは実施していません。既存credentialとownership mappingは保持し、Watchlist/Alert WriteやTask Scheduler登録・削除は行っていません。
