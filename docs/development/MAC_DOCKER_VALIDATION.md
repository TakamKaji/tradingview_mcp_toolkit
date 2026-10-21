# Issue #40 Mac Docker検証記録（2026-10-21）

## 実装と保護境界

- `Dockerfile.mac`、`compose.mac.yml`、`mac.command`を追加。既定はヘルプ表示のみで、Job・Watchlist Write・定期登録は自動実行しない。
- Linuxに限る明示containerモードと、通常のOS-native keyringモードを分離。Windows backendの検査を緩和しない。
- 認証は固定`/credentials`の専用Docker volume。UID10001所有・dir0700/file0600・通常ファイル・link数1を要求し、原子的に更新する。破損JSON、symlink、hardlink、FIFO、不適切な権限を拒否する。
- 認証volumeは暗号化Keychainではない。Docker管理権限者・同じUIDの悪意あるプロセス・VMバックアップからの秘匿を保証しない。ホストKeychain中継やtoken環境変数は導入しない。利用者向けの説明は[Mac Docker](../user/MAC_DOCKER.md)。
- SDKの認可URLはメモリに保持し、localhostの固定入口からHTTP 302でブラウザへ渡す。SDKのPKCE・state・issuer検証を維持。localhostのみport公開し、通常コマンドはport公開しない。
- 定義はホストのread-only bind mount、results・.local・credentialsは別volume。root filesystemは読み取り専用、非root、capability全削除。Docker socket、host network、privileged、cronは使わない。

## 実施環境

Windows上のDocker Desktop 4.92.0 / Linux Engine 29.8.0（amd64）、Compose v5.5.1。Mac実機は使用していない。Windows回帰はEmbedded Python 3.12.8 / MCP SDK 2.2.0、コンテナはPython 3.12.15 / MCP SDK 2.3.0 / httpx2 2.16.0で確認した。

公式`python:3.12-slim-bookworm`のmulti-architecture manifestにlinux/amd64とlinux/arm64/v8が存在することを確認。確認時index digestは`sha256:5d9e6adc9abd558bc0ce05f9ab16cef71328916fc9728f6b81e337af86a737e2`。Dockerfileは更新可能な公式tagを参照するため、将来のbuildで同じ依存バージョンを固定再現する契約ではない。

## 通過した検証

| 項目 | 結果 |
| --- | --- |
| Compose設定 | `docker compose -f compose.mac.yml config --quiet`成功。localhost限定、volume分離、既定--help等も解析して確認 |
| shell | `bash -n mac.command`成功。Git実行bitとLF改行を指定 |
| amd64 build / CLI | 実イメージbuild成功。ネットワークなしの`--version`で0.1.0b1 |
| イメージ収録 | `.git`・ホスト.local・results・credential・testsなし、pytest/ruffなし、USER10001:10001 |
| 未認証 | 空volumeでstatus/tools/screen/runはいずれもAUTH_REQUIRED・exit 3。ブラウザ起動や認証エラーの成功化なし |
| Job一覧 | 同梱Jobの検証・列挙成功。Jobのenabled/Write設定は変更なし |
| callback | ホスト127.0.0.1:8765→Docker転送→固定authorize入口→模擬callbackが成功。公開HostIp、200/302応答、秘密を本文・通常ログへ出さないことを確認 |
| 再作成・永続化 | 専用検証projectで架空token・results・.localを保存し、別のrun --rmコンテナで再読成功。dir0700/file0600確認。実tokenは使用せず |
| Windows全件回帰 | `python -m pytest -rs`相当（JUnit出力追加）：681件、674 passed・7 skipped・0 failed。後から既存の防御境界テストに直接呼出のassertionを追加し、その1件も単独再実行で成功（件数の加算なし） |
| Linux近接回帰 | 完成イメージへtestsをread-only mount、一時領域だけへpytest導入。認証・模擬SDK OAuth・CLI・履歴比較の88件すべて成功、skipなし |
| lint / 差分 | Windows Embedded経由の`python -m ruff check .`、`git diff --check`成功 |
| 文書・互換性 | 15文書の相対リンク158件・見出し39件、Mac CLI例9種類を静的照合。Windows BAT/PS1、Job/Screening定義、依存定義の変更なし |

Windowsのskip 7件は、Linux専用認証2件と、非管理者環境でsymlink作成不可の5件。Linux専用認証2件は上記Linux近接回帰で通過した。Windowsの既存Credential Manager・認証情報・Watchlist mapping・保存結果には触れていない。

検証projectは`-p tvmcp-issue40-check`を指定し、利用者向け既定projectと分離した。模擬データを実TradingViewへ送信していない。Watchlist/Alert Write、Scheduler登録・削除、全米株条件なしJobは実行していない。

## 未実施・失敗を残す項目

- **arm64実build・実行：未確認。** `docker buildx build --platform linux/arm64 --load ...`を試行したがRUNで`exec format error`。`docker buildx inspect`の利用可能platformがamd64/v2/v3のみで、arm64エミュレーションがない環境だった。特権コンテナやホスト設定変更によるemulation導入は行わなかった。arm64対応base manifestの存在をarm64 build成功とは扱わない。
- **Mac実機の初回OAuth：未実施。** Finderダブルクリック、macOS `/usr/bin/open`、Docker Desktop for Macのbind mount所有権、Apple Silicon/Intel実機を確認していない。
- **実TradingViewの認証後status/tools・Screening・Read-only Job：未実施。** 新規コンテナに実credentialを導入せず、Windowsの保存済みcredentialをexportしていない。未認証CLIと模擬SDKの成功をライブ取得成功とは扱わない。
- **実サービス上のrefresh/失効/再利用：未実施。** 模擬SDK、期限切れrecord、再作成後の保存読取は検証したが、実サービスの有効期限や同意取消後の動作は別の受入確認が必要。

Mac配布の実機受入完了・リリースGOとは判定しない。実装レビュー用のPRを作成し、上記のMac・arm64・ライブOAuth Gateを残す。main配布PRにはtests・この記録・開発仕様を含めず、必要な起動構成・本体差分・利用者文書だけを反映する。

本記録はIssue #40の実装契約と実測を保持する。Google Drive仕様正本は今回更新しておらず、同期済みとは扱わない。正本の更新は既存のDrive先行・読み戻し契約に従う別の同期作業として残す。
