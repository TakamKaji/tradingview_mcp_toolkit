# CLAUDE.md

このリポジトリでは、まずルートの `AGENTS.md` を共通開発ポリシーとして読み、その内容に従ってください。

Claude Code固有の追加ルールは以下だけです。

- 共通ルールをこのファイルへ重複コピーしない。変更が必要な場合は原則 `AGENTS.md` を更新する。
- `.claude/settings.json` の共有権限設定を尊重する。
- `.local/` の認証情報や `runtime/` のEmbedded Python実体を解析対象として読み込まない。
- WindowsでPythonコマンドを実行する場合、Embedded Python環境があるなら `setenv.bat` 経由を優先する。
- タスクが明確な場合、計画だけを繰り返さず、実装・テスト・差分確認まで進める。
