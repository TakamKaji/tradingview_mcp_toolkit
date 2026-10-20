# Publicソース候補の作成（Issue #35）

現行のPrivateリポジトリや過去のGit履歴をPublicへそのまま移さず、**確認済みの必要ファイルだけを新しい初期履歴の候補ディレクトリへ抽出**する準備用ツールです。新リポジトリの作成・公開・pushは行いません。

## 実行

Python 3.11〜3.13とローカルGitが使える開発環境で、リポジトリのルートから：

```bash
python scripts/prepare_public_snapshot.py --repo . --ref HEAD
```

特定のコミットを再現する場合は`--ref <commit-sha>`を指定。出力は`dist/public-source-<pyproject version>/`です。**既存出力がある場合は上書きせずエラー**にします。再生成時は別の`--out`ディレクトリを指定します。絶対／相対pathとも使えますが、git metadata内への出力は拒否します。

## 公開候補に入るもの

- 実行必須の`setup.bat`、`setup-runtime.bat`、`app.bat`、`setenv.bat`、`scripts/setup-ui.ps1`、`requirements.txt`、`pyproject.toml`、`LICENSE`
- `src/tradingview_screening/`、`jobs/`、`screenings/`
- `docs/user/`と公開候補専用に作り直した`README.md`・`docs/README.md`・`.gitignore`
- setup UIが案内する旧`docs/WINDOWS_SETUP.md`への短い案内
- `PUBLIC_SOURCE_MANIFEST.json`（ファイルごとのSHA-256。Private側の元commit SHAは含めない）

抽出対象は**完全一致の許可リスト**で、新しい実装ファイルが自動混入しません。新規ファイルはコードレビューで明示追加が必要です。symlink・Git LFS pointerを拒否します。Private repoの元Git履歴・枝・PR・Issueはコピーしません。

## 初期候補に入れないもの

- 第三者の公式資料の長文転載：`docs/development/TRADINGVIEW_MCP_OFFICIAL_REFERENCE.md`
- Providerが作成した説明文を含むschema snapshot：`tests/fixtures/tradingview_input_schemas_*.json`
- 上記fixtureに依存するテスト、およびその他のテスト群（**今後、権利を確認済みのテスト・自作fixtureへ移行するまで非収録**）
- Privateの開発仕様、過去の受入／検証履歴、非共有Driveへのリンク、PrivateリポジトリのURL
- `.git/`、`.claude/`、`.codex/`、`AGENTS.md`、`CLAUDE.md`、`second_pc_full_test.bat`、`runtime/`、`.local/`、`results/`、token、credential、GitHub Actions履歴

この候補は**一般ユーザー向けソース＋最小マニュアル**であり、従来の「テスト付き完全版」をまだ再現していません。公開可能な独自のschemaテストを整備する作業は後続Gateです。

## 仕組みと限界

- `git ls-tree`と`git cat-file`で指定commitの追跡オブジェクトだけを読み、Gitの履歴を一切コピーしない。
- Markdown相対リンクは収録済みの対象だけを保持し、除外されたPrivate文書へのリンクを通常テキストへ変更。古いPrivate URL・非共有Driveリンクは配布物のリンクに残さない。
- Windows起動BATのASCII、PowerShell日本語UIのUTF-8 BOM、基本JobのRead-only設定と全米株Jobの無効設定を検査。
- 簡易秘密パターン／実メールらしきものの検査を行い、疑わしい場合は候補生成を停止。検出値・行内容は出力しない。**本検査はGitleaksや権利監査の代替ではない。**
- 生成処理自体はOAuth、MCP通信、Watchlist Write、Task登録、GitHub APIやネットワークにアクセスしない。

## 公開まで残る作業

1. 生成したソース候補を**独立した検査対象**として、秘密・第三者権利・ユーザー体験・GitHub向け説明を再監査する。候補スクリプトの許可リストやテキスト除去だけで合法性や安全性の証明にはならない。
2. 自作の公開可能なschema fixture等でテストを再構成するか、公開用テスト収録範囲を所有者が決定する。
3. Windowsで候補を展開し`setup.bat`から認証・Read-onlyサンプルまで実機確認。新規Windowsユーザーの初回OAuthは未実施扱いを維持する。
4. [Issue #32](https://github.com/TakamKaji/tradingview_mcp_support/issues/32)の未解決公開リスクと、新規Publicリポジトリのリポジトリ名・設定・運用ルールについて所有者が判断する。
5. GO判定後に初めて新規Publicリポジトリを独立履歴で作成し、[Issue #33](https://github.com/TakamKaji/tradingview_mcp_support/issues/33)の配布ZIPを実装する。

**このIssueのPRマージはPublic公開の許可ではありません。** 既存Privateリポジトリは変更せず保持します。
