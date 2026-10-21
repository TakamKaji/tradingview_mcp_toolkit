# AGENTS.md

このリポジトリのCodex向け共通指示。主対象はGPT-6 Astra。

## 作業原則

- 出力、レビュー、コミットメッセージ、PR説明は原則日本語。
- タスクが明確なら、不要な計画文書を作らず、必要なファイルを確認して実装・検証まで進める。
- リポジトリ全体や全仕様書を毎回読み込まない。変更対象の境界を判断するために必要な文書だけ読む。
- 変更は依頼範囲に限定する。関連箇所の大規模リファクタや将来機能の先回り実装をしない。
- コードについて断定する前に、該当実装を確認する。
- 実装後は変更に対応するテストとlintを実行し、失敗した場合は原因を直してから完了報告する。
- 実行できない検証は、未実行であることと理由を明記する。

## ブランチ同期ルール

- 開発正本は`develop`、配布は`main`。同じ変更を両方で別々に実装せず、配布対象だけを独立コミットに分け、もう一方へ`git cherry-pick -x`で同期する。
- 通常のコード作業は`develop`先行、共通README等の文書は`main`先行も可。tests・開発資料を含むコミットを`main`へcherry-pickしない。
- `develop`全体を`main`へmergeしない。main/devともにPRでレビューし、直接push・自動マージ・公開・tag/Releaseをしない。
- 詳細手順は[ブランチ運用](docs/development/BRANCH_WORKFLOW.md)を参照する。

## プロジェクト境界

- TradingView連携は公式MCP `https://mcp.tradingview.com/mcp` を本線とする。
- 非公式TradingView API、スクレイピング、Playwright/SeleniumによるTradingView操作を追加しない。
- AIからMCPを直接操作する仕組みではなく、共通Python CLI / 型付きラッパー / 定義ファイルを実装する。
- MCP Provider固有処理は `src/tradingview_screening/integrations/<provider>/` に閉じ込める。
- Rate Limit / Retry / Timeout / Concurrency / Cacheは共通通信層へ集約する。
- スクリーニング追加は定義ファイルを優先し、条件ごとのPythonスクリプトを増やさない。
- Job追加時にBATへJob名をハードコードしない。
- Public版コアでOHLCVからRSI・移動平均等を再計算しない。
- 依存は最小限にし、標準ライブラリで十分な機能へ外部依存を追加しない。
- 依存の正本は `pyproject.toml`。
- `runtime/`、`.local/`、`results/` は生成物またはローカル情報。認証情報やtokenをコミットしない。


## Windows Embedded Python の環境設計Invariant

- Windows Embedded Pythonを使う目的は、利用者へシステムPythonのインストールを要求しないことにある。
- Windowsユーザー環境全体を仮想化・隔離することは目的ではない。
- `USERPROFILE`、`HOME`、`HOMEPATH`、`APPDATA`、`LOCALAPPDATA`、`TEMP`、`TMP` をプロジェクト配下へ置き換えない。
- `keyring`、Windows Credential Manager、既定ブラウザ、OAuth認証は通常のWindowsユーザー環境を利用する。
- ローカル化する対象は、原則としてPython Runtimeとアプリ固有データのみとする。
- `PYTHONHOME` / `PYTHONPATH` はシステムPython設定との混線防止のため、起動プロセス内でクリアしてよい。
- Embedded Pythonを `PATH` の先頭へ追加する場合も、`setup.bat` / `console.bat` 等から起動したプロセス内だけに限定する。
- OS環境変数の恒久変更、レジストリへのPythonパス登録、システムPythonへのpip installを行わない。
- `.local/` はOAuth補助情報、lock、cache等のアプリ固有ローカルデータ用であり、Windowsユーザープロファイルの代替ディレクトリとして使わない。
- 「ポータブル化」を理由に上記方針を変更しない。変更が必要な場合は、実装より先に仕様上の理由を明示する。
- Windows Embeddable Pythonでは `pythonXY._pth` によるisolated modeを前提とする。ローカルプロジェクトのeditable installでは、build backendをEmbedded Pythonへ明示インストールした上で `pip install --no-build-isolation -e .[dev]` 相当を使う。通常Python/macOSにはこの制約を広げない。

## 文書の読み分け

- 通常のコード変更: 変更対象と近接テストを優先。
- アーキテクチャ変更: 実装仕様書と関連docsを確認。
- MCP Tool変更: TradingView公式MCPリファレンスとTool Discovery仕様を確認。
- Job / Screening定義変更: 各マニュアルとSchemaを確認。
- Windows bootstrap変更: `setup.bat`、`setenv.bat`、`console.bat`をまとめて確認。

## 検証

Windows Embedded Python環境では `console.bat` を開いて:

```bat
python -m pytest
python -m ruff check .
```

非対話実行ではシステムPythonを暗黙に使わず、プロジェクトの `setenv.bat` 経由を優先する。

macOS / 通常Pythonでは:

```bash
python -m pytest
python -m ruff check .
```


## Codexの役割分担

- Root / 司令塔は GPT-6 Astra とする。
- Astraは仕様確認、タスク分解、Acceptance Criteria、実装レビュー、最終検証を担当する。
- `src/` と `tests/` の実装は原則として `implementer` roleへ委任し、実装担当は GPT-6 Sol とする。
- Astra自身が本実装を抱え込まない。説明文・仕様・設定の小変更はAstraが直接変更してよい。
- 同一ファイルを複数subagentへ同時編集させない。通常はSol implementerを1つだけ動かす。
- Solは指定範囲の実装、Unit Test、pytest/ruff、変更結果の報告まで担当し、依頼外の大規模リファクタを行わない。
- multi-agent機能が利用できない場合、Astraは黙って単独実装へ切り替えず、その状態をユーザーへ明示する。
- 操作マニュアルは `docs/user/README.md`、開発資料は `docs/development/README.md` を参照する。
- 詳細な実装契約は `docs/development/tradingview_screening_system_spec.md` を参照する。
