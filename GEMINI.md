# Gemini CLI：利用者向け入口

最初に[README](README.md)、次に詳細規則の唯一の正本である[AIによるScreening生成ガイド](docs/user/AI_JSON_GUIDE.md)と、その参照先の実Schema・サンプルを読んでください。

- 利用者が指定した母集団・抽出条件・処理順序を変更しない。
- 実装方式と外部データ利用は正本の[方式選択フロー](docs/user/AI_JSON_GUIDE.md#aiによる方式選択フロー)に従う。外部データの取得・導入は利用者の明示的な選択・承認後に限る。
- 全件取得とランキング・部分取得を区別し、完全性を検証する。
- Provider未対応の市場区分・指標・列・APIを創作しない。単一Screeningで表せるなら標準JSONを優先する。
- 「作成して実行」の依頼は、生成物に加えstdout・stderr・exit code・新しい保存結果まで確認する。未実行・失敗・部分成功を成功と報告しない。
- 依頼されたTradingViewからのデータ読み取り（Read）とローカルへの結果保存は、実行範囲に含む。Watchlist・Alert Write、Scheduler登録・削除、認証情報削除は明示依頼なしに行わない。

README.mdがあるプロジェクトルートを作業ディレクトリとして、対応するAIのCLIを起動する。自動読込の条件と限界は[AI利用手順](docs/user/AI_USAGE.md)を参照。
