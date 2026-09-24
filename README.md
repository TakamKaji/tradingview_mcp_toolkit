# tradingview_mcp_support

TradingView公式MCPを、AIアプリから共通CLI経由で扱うための軽量Pythonバックエンドです。

現在は実装開始前のbootstrap段階です。Windowsではプロジェクト内のEmbedded Pythonを使い、システムPythonを要求しない構成を主対象とします。macOSなどでは通常のPython環境からも利用できる設計にします。

## 開発方針

- TradingView公式MCP `https://mcp.tradingview.com/mcp` を利用する。
- 非公式TradingView API、スクレイピング、Desktop自動操作を本線にしない。
- AIモデル差を減らすため、取得・条件判定・保存はPython側で決定論的に行う。
- 依存は最小限にし、標準ライブラリで十分な機能には追加パッケージを導入しない。
- WindowsではEmbedded Python、macOSでは通常のPython + venvを想定する。
- 実装仕様は今後 `docs/` 配下へ追加し、Codex / Claude Codeから参照できるようにする。

## Windows セットアップ

1. リポジトリをcloneする。
2. `setup.bat` を実行する。
3. 完了後、`console.bat` を開く。

`setup.bat` は初回のみEmbedded Pythonを取得します。Python本体が既にある場合も、依存パッケージの更新処理は継続して実行します。

### 開発用コマンド

`console.bat` で開いたコンソールから実行します。

```bat
python -m tradingview_screening --help
python -m pytest
python -m ruff check .
```

## macOS / 通常Python

Python 3.11〜3.13を想定します。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m tradingview_screening --help
python -m pytest
python -m ruff check .
```

## 依存関係

依存の正本は `pyproject.toml` です。

Runtime:

- `mcp>=2,<3`
- `pydantic>=2,<3`
- `aiolimiter>=1.3,<2`
- `tenacity>=9,<10`
- `cachetools>=5,<8`
- `keyring>=25,<26`
- `filelock>=3,<5`

Development:

- `pytest>=8,<10`
- `ruff>=0.9,<1`

`requirements.txt` はWindows bootstrap互換のため `-e .[dev]` を指定します。

## ライセンス

MIT License。
