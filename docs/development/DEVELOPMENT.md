# 開発と検証

まず[AGENTS.md](../../AGENTS.md)と対象の設計契約を確認します。一般利用者のセットアップは実行用依存だけを入れ、pytest・ruffを導入しません。依存の正本は[pyproject.toml](../../pyproject.toml)です。

## Windows Embedded Python

`setup.bat`で環境を準備してから、`scripts/development/console.bat`で開いたコンソールで次を実行します。

```bat
python -m pip install --no-build-isolation -r requirements-dev.txt
python -m pytest -rs
python -m ruff check .
git diff --check
```

非対話実行では`scripts/setenv.bat`経由でプロジェクトのPythonを選びます。システムPythonへpip installせず、Windowsユーザーの環境変数やプロファイルを恒久変更しません。Embedded Pythonのisolated modeを前提に、build backendを明示導入した環境で`--no-build-isolation`を使います。通常Python/macOSにはこの制約を広げません。

pytestの一時領域はGit管理外の`.pytest-tmp/`です。実symlinkを作成できないWindowsでは権限依存テストがskipされる場合があります。skip理由を記録し、未実行を成功と扱いません。全テストを通すために管理者実行を標準にしません。

## macOS / 通常Python

Python 3.11〜3.13が対象です。Windows向けのリリース実機検証と同一視しません。macOS/Linux Schedulerは提供していません。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m tradingview_screening --help
python -m pytest -rs
python -m ruff check .
```

## 実機検証と文書変更

Unit Testは保存済みinputSchemaとmockを使うオフライン検証です。実MCPは対象プラン・利用者の認証と依頼範囲を確認して、Read-onlyを優先します。Watchlist/Alert WriteやTask登録・削除は明示承認された対象だけで行い、既存のmapping・credential・保存結果を削除しません。

過去のTool応答とテスト件数は[履歴索引](../archive/README.md)から確認します。過去の結果を新しいHEADでの合格として流用しません。文書だけの変更ではリンク・アンカー・CLI例・差分範囲を確認し、コードに変更がなければ全pytest/ruffの再実行は不要です。

[開発索引](README.md)
