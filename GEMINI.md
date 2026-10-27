# Gemini CLI：developの入口

開発作業では[AGENTS.mdの開発ルール](AGENTS.md)を先に読み、既存の役割分担・実装/テスト契約に従ってください。

利用者のScreening作成・実行では、[README](README.md)→詳細規則の唯一の正本である[AIによるScreening生成ガイド](docs/user/AI_JSON_GUIDE.md)と実Schema・サンプルを読んでください。

- 公式MCPを優先し、母集団・抽出条件・処理順序を保持する。外部データ利用・条件変更は明示的な依頼・承諾後だけ行う。
- 未確認を非対応と断定せず、未知の市場区分・指標・列・APIを創作しない。単一Screeningで表せるなら標準JSONを優先する。
- 「作成して実行」は環境と権限があればRead取得・計算を行い、stdout・stderr・exit code・新しい保存結果まで検証する。未実行・失敗・部分成功を全件成功としない。
- 依頼されたTradingView Readとローカル結果保存を実行範囲とし、明示依頼のないWatchlist・Alert Write、Scheduler登録・削除、認証情報削除を行わない。

プロジェクトルートを起点に起動する。自動読込の条件と限界は[AI利用手順](docs/user/AI_USAGE.md)を参照。
