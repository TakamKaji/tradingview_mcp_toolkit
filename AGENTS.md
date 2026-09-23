# AGENTS.md

このリポジトリで作業するAIエージェント向けの共通ルール。

## 基本方針

- 出力、レビュー、コミットメッセージ、PR説明は原則日本語にする。
- タスクが明確な場合、長い計画作成だけで止まらず実装・検証まで進める。
- 必要な文書だけを読む。タスクと無関係な仕様書を毎回すべて読み込まない。
- 変更は依頼範囲に限定し、V1対象外機能を先回り実装しない。
- TradingView連携は公式MCP `https://mcp.tradingview.com/mcp` を前提とする。
- 非公式TradingView API、スクレイピング、Playwright/SeleniumによるTradingView操作を追加しない。
- 依存関係は最小限にする。標準ライブラリで十分な機能に外部依存を追加しない。
- 依存の正本は `pyproject.toml` とし、同じ依存定義を複数箇所へ重複させない。
- `runtime/`、`.local/`、`results/` は生成物・ローカル情報として扱い、ソースとして編集しない。
- 認証情報、OAuth token、Cookie、セッション情報をコミットしない。

## 実装上の境界

- AIからTradingView MCPを直接操作する機能ではなく、Pythonの共通CLI/ラッパーを実装する。
- MCP Provider固有処理は `src/tradingview_screening/integrations/<provider>/` に閉じ込める。
- Rate Limit / Retry / Timeout / Concurrency / Cacheは共通通信層に集約し、Toolごとに重複実装しない。
- スクリーニング条件は可能な限り定義ファイルで表現し、条件ごとのPythonスクリプトを増やさない。
- Job追加時にBATファイルへ個別Job名をハードコードしない。
- Public版コアでOHLCVからRSI・移動平均等を再計算する機能を追加しない。

## Windowsでの検証

Embedded Pythonをセットアップ済みの場合は `console.bat` を開き、次を実行する。

```bat
python -m pytest
python -m ruff check .
```

AIから非対話で実行する必要がある場合は、プロジェクトの `setenv.bat` を経由してEmbedded Python環境を有効にすること。システムPythonを暗黙に前提としない。

## macOS / 通常Pythonでの検証

```bash
python -m pytest
python -m ruff check .
```

## 変更完了時

- 変更に対応するテストを実行する。
- 実行できなかった検証は「未実行」と理由を明記する。
- 既存テストを削除・無効化して成功扱いにしない。
- 仕様と実装が衝突した場合、勝手に仕様を変更せず差分を明示する。
