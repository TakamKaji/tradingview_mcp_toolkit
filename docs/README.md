# ドキュメント

[利用者マニュアル一覧](user/README.md)から必要な操作を参照できます。

開発者向けの設計仕様・テスト・検証資料は同じリポジトリの `develop` ブランチで管理します。

## 開発・リリースの流れ

1. `develop`で開発・テストし、設計仕様と検証記録を保持します。
2. 完成した変更のうち、実行コード・BAT・依存定義・Job/Screening定義・利用者文書だけをmain向けのPRへ反映します。
3. mainの配布対象に必要なファイル、リンク、WindowsセットアップとRead-only動作を検証します。
4. 公開前の確認と所有者判断を終えた後、対象mainコミットへ`v0.1.0b1`などのバージョンタグを付けます。
5. そのタグでGitHub Releaseを作成します。
6. 利用者はReleaseの**Assets → Source code (zip)**を取得・展開し、`setup.bat`を実行します。

**developをmainへ丸ごとmergeしません。** main用PRは配布ファイルだけを選んで反映し、`tests/`・開発仕様・検証資料・開発ツールを復活させないことを差分で確認します。専用ZIP生成ツール・Actions・独立リポジトリ・独立履歴は使用しません。

現在はRelease・tag・Public公開とも未実施です。developや過去の履歴も公開後に閲覧可能になります。所有者はこの可視性を了承していますが、[Issue #32](https://github.com/TakamKaji/tradingview_mcp_support/issues/32)の第三者資料の転載・権利確認は別の未解決事項であり、mainの整理だけでは解消しません。

[トップREADME](../README.md)
