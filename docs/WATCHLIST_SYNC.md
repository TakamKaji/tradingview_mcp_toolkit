# 管理Watchlist差分同期（Phase 7）

## 所有権

所有権はアプリ自身のcreateが返したIDを `.local/managed_watchlists.json` に保存した記録だけで判定します。名前による検索・採用はしません。同名Watchlistがあっても、mappingがなければ別の新規Watchlistを作成します。

```json
{
  "schemaVersion": 1,
  "screenings": {
    "sample_standard_screen": {
      "watchlistId": "12345678",
      "expectedName": "[Auto] Sample Standard Screen"
    }
  }
}
```

上記IDは説明用ダミーです。mappingは未知field、バージョン、ID、名前等を厳格検証します。expectedNameは診断用であり、現在名が変わってもownershipの根拠はIDです。同期で名前変更はしません。

## Provider応答

2026-09-26、今回作成した専用テストWatchlistで確認したshape:

| 操作 | structured_contentの使用field |
| --- | --- |
| create/get | watchlist.id: int、watchlist.name: str、watchlist.symbols: list[str] |
| add/remove | watchlist_id: str、symbols: list[str] |

成功応答にsuccess fieldはありません。createのIDは10進文字列へ変換して保存します。追加fieldは許容しますが、raw SDK objectやProvider全文は同期層へ渡しません。contentをJSONとして再parseしません。

add/removeのsymbolsが全状態か操作対象かを推測せず、応答の型・IDを検証後、getで実状態を確認します。確認Readの失敗も成功とは扱いません。

削除済みテストIDへのgetはMCP is_error=true、structured_contentなしでした。エラーは不存在と所有権/公開アクセス不能を区別しないため、自動再作成しません。確実な `WATCHLIST_NOT_FOUND` をintegrationが識別できる場合だけ再作成する分岐がありますが、そのProvider応答は未実測です。一般のtransport/timeout/MCP_TOOL_ERROR/schema不整合はmappingを維持したまま停止します。

## 競合と保存

lockは `.local/watchlist_locks/` に置き、キーをSHA-256でhash化します。

| lock | 保護範囲 |
| --- | --- |
| Screening単位 | mapping再読込、ownership解決、初回createの競合 |
| Watchlist ID単位 | 現在状態Read、差分計算、Write、確認Read |
| mapping共通 | JSON再読込、1レコードmerge、atomic replaceのみ |

異なるWatchlistのリモート通信を共通mapping lockで直列化しません。filelockのtimeout/failureは明示的AppErrorです。lockファイルは残っていても保持中とは限らないため、実行中に手で削除しないでください。

`thread_local=False` を使用するため、依存は `filelock>=3.12.1,<5` です。thread-local切替は3.12.0、Python 3.12対応は3.12.1で導入されています（[公式変更履歴](https://py-filelock.readthedocs.io/en/latest/changelog.html#v3-12-0-2023-04-18)）。今回の実機検証はfilelock 4.0.3で行いました。

mappingは同じディレクトリのtempへwrite/flush/fsync後、atomic replaceします。symlink/junction/path escapeを拒否し、`.local/` 外へ書きません。mappingとlockは非secretですがGit管理外です。

## 差分と失敗回復

desired-currentだけをaddし、current-desiredだけをremoveします。完全一致・順序差だけならWriteしません。正常な0件のScreening結果は管理Watchlistを空にします。failed/partialのScreening結果、不正symbolはWrite前に拒否します。

create/add/removeは既存TradingViewClientとRequestGovernorを通し、retry=False/cacheなしです。通常同期からdelete、get_active、同名検索、名前変更を呼びません。

- create成功・mapping保存失敗: 作成済ID付きの明示エラー。自動deleteせず、add/removeも実行しません。再実行しても同名Watchlistを勝手に採用しません。
- add確認成功・remove失敗: partial、確認済addedだけを報告。未確認のremovedを作りません。
- timeout、応答不整合、確認Read失敗: 実際のProvider状態が不明な操作は完了扱いにしません。自動再送・rollbackは行いません。
- 再実行: 保存済IDの現在状態を再取得し、新しい差分だけを処理します。ローカルmappingが壊れている場合はcreateへ進みません。

同期結果はscreening、watchlistId/name、created、added、removed、unchangedCount、status、errorsを返します。無効設定によるskipはsuccessにskipped=trueとreasonを添えます。

## 実機検証の範囲

実response調査では、新規専用テストWatchlistへTSE:7203を1回追加し、取得確認、1回削除、空状態取得確認を行いました。そのテストIDだけをcleanup削除し、削除後の取得不能応答も調べました。ユーザー既存Watchlistは変更していません。実ID・テスト名・Provider全文をfixtureへ保存していません。

Unit Test後には別の新規専用テストWatchlistで、同期Python APIの一連の動作も確認しました。

| 確認 | 結果 |
| --- | --- |
| Windows Embedded Python / 権限 | 3.12.8 / 管理者権限なし |
| Phase 6 Engineから取得 | 実Screening結果1件 |
| 初回同期 | success、created=true、1件add、保存mappingと返却ID一致 |
| 同じ入力で再同期 | success、Write 0回、unchangedCount=1 |
| 制御した正常空Envelope入力 | success、1件remove、getで空状態確認 |
| Write policy | create/add/remove/cleanup deleteすべてretry=False、cacheなし |
| 通常syncの禁止Tool | delete/get_active/list/update呼出しなし |
| cleanup | この実行で作成したIDだけをdelete、deleted=trueとID一致を確認 |

空入力は削除経路の確認用に、取得した正常EnvelopeのresultsとreturnedCountを空へ変更したものです。Providerがその時点で0件を返したという意味ではありません。実partial、Write timeout/429、macOS実機は未確認で、失敗時処理はオフラインUnit Testで検証しています。

通常APIにWatchlist削除機能はありません。Job Runner/Scheduler等のPhase 8も実装していません。
