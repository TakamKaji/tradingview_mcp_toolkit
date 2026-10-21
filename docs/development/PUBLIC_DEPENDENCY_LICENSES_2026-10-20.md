# 依存ライセンス調査（2026-10-20 / Issue #32）

対象は基点main `e38a547251d66baeec14a5133755a29bcbf213e3`の依存定義と、Windows Embedded Python 3.12.8の既存環境で解決済みのdistributionです。新たなpip installはしていません。ライセンス表記は各distributionの`License-Expression`、metadata、付属license/noticeを確認した観測値です。上限・下限で許容する将来版、macOS等の別環境、すべてのvendored subcomponentの法的適否まで承認するものではありません。

Runtime 40、開発7、build backend 1の合計48 distributionを列挙し、未導入の依存は0でした。表はパッケージ全体の主たるmetadata表記であり、下記の複合ライセンスの注記を必ず併せて確認してください。現存ソースの追跡対象に、これらのwheel・DLL・ライセンス文書のコピーは含まれません。

| Distribution | 観測版 | 役割 | 主たるライセンス表記 |
| --- | --- | --- | --- |
| aiolimiter | 1.3.0 | Runtime | MIT |
| annotated-types | 0.8.0 | Runtime | MIT |
| anyio | 4.15.1 | Runtime | MIT |
| attrs | 26.1.0 | Runtime | MIT |
| cachetools | 7.2.0 | Runtime | MIT |
| cffi | 2.1.1 | Runtime | MIT-0 |
| click | 8.5.0 | Runtime | BSD-3-Clause |
| colorama | 0.4.6 | 開発 | BSD（付属条項を確認） |
| cryptography | 50.0.1 | Runtime | Apache-2.0 OR BSD-3-Clause |
| filelock | 4.0.3 | Runtime | MIT |
| h11 | 0.16.0 | Runtime | MIT |
| httpcore2 | 2.13.1 | Runtime | BSD-3-Clause |
| httpx2 | 2.13.1 | Runtime | BSD-3-Clause |
| idna | 3.20 | Runtime | BSD-3-Clause |
| iniconfig | 2.3.0 | 開発 | MIT |
| jaraco-classes | 3.4.0 | Runtime | MIT License |
| jaraco-context | 6.1.2 | Runtime | MIT |
| jaraco-functools | 4.6.0 | Runtime | MIT |
| jsonschema | 4.26.0 | Runtime | MIT |
| jsonschema-specifications | 2025.9.1 | Runtime | MIT |
| keyring | 25.7.0 | Runtime | MIT |
| mcp | 2.2.0 | Runtime | MIT |
| mcp-types | 2.2.0 | Runtime | MIT |
| more-itertools | 11.1.0 | Runtime | MIT |
| opentelemetry-api | 1.44.0 | Runtime | Apache-2.0 |
| packaging | 26.3 | 開発 | Apache-2.0 OR BSD-2-Clause |
| pluggy | 1.6.0 | 開発 | MIT |
| pycparser | 3.0 | Runtime | BSD-3-Clause |
| pydantic | 2.13.5 | Runtime | MIT |
| pydantic-core | 2.46.5 | Runtime | MIT |
| pygments | 2.21.0 | 開発 | BSD-2-Clause |
| pyjwt | 2.15.0 | Runtime | MIT |
| pytest | 9.1.1 | 開発 | MIT |
| python-multipart | 0.0.32 | Runtime | Apache-2.0 |
| pywin32 | 312 | Runtime | PSF |
| pywin32-ctypes | 0.2.3 | Runtime | BSD-3-Clause |
| referencing | 0.37.0 | Runtime | MIT |
| rpds-py | 2026.6.3 | Runtime | MIT |
| ruff | 0.16.8 | 開発 | MIT |
| setuptools | 80.10.2 | Build | MIT |
| sse-starlette | 3.4.11 | Runtime | BSD-3-Clause |
| starlette | 1.7.0 | Runtime | BSD-3-Clause |
| tenacity | 9.1.4 | Runtime | Apache 2.0 |
| truststore | 0.10.4 | Runtime | MIT |
| typing-extensions | 4.16.0 | Runtime | PSF-2.0 |
| typing-inspection | 0.4.4 | Runtime | MIT |
| tzdata | 2026.4 | Runtime | Apache-2.0 |
| uvicorn | 0.53.0 | Runtime | BSD-3-Clause |

## 複合ライセンス・配布時の注意

- `pywin32`のmetadataはPSFですが、同梱の`adodbapi`にはLGPL 2.1のライセンス文書があり、ほかにBSD、MIT、Scintillaのライセンス/NOTICE等もあります。パッケージ全体を単純にMIT/PSFだけで再配布可能と要約しません。
- `setuptools`の主たる表記はMITですが、vendored `autocommand`にはLGPL v3のライセンス文書があります。ほかのvendored依存も各LICENSE/NOTICEを保持します。これはbuild依存であり、予定するソースZIPへvendor wheelを同梱する設計ではありません。
- `typing-extensions`のPSF-2.0文書にはPythonライセンスの歴史とGPL互換性の説明が含まれます。GPLという語の単純検索だけで、そのdistribution全体がGPLだと判定しません。
- `cryptography`、`packaging`は複数ライセンスの選択・追加noticeを持ちます。`tzdata`はApache-2.0で、IANA由来データを含む付属権利表示も配布物側で保持する必要があります。
- permissive licenseでも著作権・許諾表示の保持等の条件があります。LGPL componentをバイナリ配布する設計へ変える場合は、その版と収録物に対応した条件を別途確認してください。依存をオンライン取得する方式でも利用条件がなくなるわけではありません。
- WindowsのCPython 3.12.8 Embeddedは別途オンライン取得するRuntimeです。プロジェクトのMITとは別のPSFおよび付属第三者ライセンスを持ち、予定する配布ZIPにはRuntimeを同梱しません。CPythonやpipを同梱する設計に変更した場合は、それらの再配布条件も再点検します。

## 範囲外と次回確認

この調査は脆弱性・供給元の真正性・すべてのtransitive native componentを保証するSBOM/法的審査ではありません。dependency範囲はlockされていないため、Release候補の実際の解決版が変わればライセンスとnoticeを再確認してください。非Windows用marker・optional extraをすべてインストールして比較する検証はしていません。

第三者の公式資料転載とProvider schema snapshotの許諾はこの依存表では解決せず、[公開前監査のBlocker B1](PUBLIC_RELEASE_AUDIT.md#blocker-b1第三者資料の再公開許諾が未確認)で別管理します。

[公開前監査](PUBLIC_RELEASE_AUDIT.md) / [開発索引](README.md)
