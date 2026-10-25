# Gemini CLI：developの入口

開発作業では[AGENTS.mdの開発ルール](AGENTS.md)を先に読み、既存の役割分担・実装/テスト契約に従ってください。

利用者のScreening作成・実行では、[README](README.md)→詳細規則の唯一の正本である[AIによるScreening生成ガイド](docs/user/AI_JSON_GUIDE.md)と実Schema・サンプルを読んでください。

- 指定された母集団・抽出条件・処理順序を変更せず、全件取得とランキング・部分取得を区別する。
- Provider未対応の市場区分・指標・列・APIを創作せず、単一Screeningで表せるなら標準JSONを優先する。
- 「作成して実行」は生成物に加えstdout・stderr・exit code・新しい保存結果まで検証し、未実行・失敗・部分成功を成功としない。
- 依頼されたTradingView Readとローカル結果保存を実行範囲とし、明示依頼のないWatchlist・Alert Write、Scheduler登録・削除、認証情報削除を行わない。

プロジェクトルートを起点に起動する。自動読込の条件と限界は[AI利用手順](docs/user/AI_USAGE.md)を参照。
