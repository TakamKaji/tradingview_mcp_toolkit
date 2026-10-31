# 新規Windows配布環境の依存ライセンス（2026-10-31）

対象main：`d5f3536f12c1743562082fc64e1629143a36f8ee`。GitHub標準ZIPの新規展開先で`setup.bat --no-pause`を実行したWindows Embedded Python 3.12.8環境の観測値。アプリ1、runtime40、pip1、build backend1の計43 distributionを列挙し、全件のmetadataと付属LICENSE/NOTICEの存在を確認した。開発用pytest/ruffをこの配布環境へ追加していない。

| Distribution | 解決版 | 主たるライセンス | 役割 |
| --- | --- | --- | --- |
| aiolimiter | 1.3.0 | MIT | Runtime |
| annotated-types | 0.8.0 | MIT | Runtime |
| anyio | 4.15.1 | MIT | Runtime |
| attrs | 26.1.0 | MIT | Runtime |
| cachetools | 7.2.7 | MIT | Runtime |
| cffi | 2.1.1 | MIT-0 | Runtime |
| click | 8.5.0 | BSD-3-Clause | Runtime |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | Runtime |
| filelock | 4.2.5 | MIT | Runtime |
| h11 | 0.16.0 | MIT | Runtime |
| httpcore2 | 2.16.0 | BSD-3-Clause | Runtime |
| httpx2 | 2.16.0 | BSD-3-Clause | Runtime |
| idna | 3.20 | BSD-3-Clause | Runtime |
| jaraco.classes | 3.4.0 | MIT（付属LICENSE確認） | Runtime |
| jaraco.context | 6.1.2 | MIT | Runtime |
| jaraco.functools | 4.6.0 | MIT | Runtime |
| jsonschema | 4.26.0 | MIT | Runtime |
| jsonschema-specifications | 2025.9.1 | MIT | Runtime |
| keyring | 25.7.0 | MIT | Runtime |
| mcp | 2.3.0 | MIT | Runtime |
| mcp-types | 2.3.0 | MIT | Runtime |
| more-itertools | 11.2.1 | MIT | Runtime |
| opentelemetry-api | 1.45.2 | Apache-2.0 | Runtime |
| pip | 26.2.2 | MIT | 導入用 |
| pycparser | 3.12 | BSD-3-Clause | Runtime |
| pydantic | 2.14.2 | MIT | Runtime |
| pydantic_core | 2.50.2 | MIT | Runtime |
| PyJWT | 2.15.1 | MIT | Runtime |
| python-multipart | 0.0.32 | Apache-2.0 | Runtime |
| pywin32 | 312 | PSF | Runtime |
| pywin32-ctypes | 0.2.3 | BSD-3-Clause | Runtime |
| referencing | 0.37.0 | MIT | Runtime |
| rpds-py | 2026.9.1 | MIT | Runtime |
| setuptools | 80.10.2 | MIT | Build |
| sse-starlette | 3.6.0 | BSD-3-Clause | Runtime |
| starlette | 1.10.0 | BSD-3-Clause | Runtime |
| tenacity | 9.2.1 | Apache-2.0 | Runtime |
| tradingview-mcp-support | 0.1.0b1 | MIT | アプリ |
| truststore | 0.10.5 | MIT | Runtime |
| typing-inspection | 0.4.4 | MIT | Runtime |
| typing_extensions | 4.16.0 | PSF-2.0 | Runtime |
| tzdata | 2026.6 | Apache-2.0 | Runtime |
| uvicorn | 0.54.0 | BSD-3-Clause | Runtime |

## 適用範囲と複合ライセンス

- 配布ZIPはソースのみで、これらのwheel・DLL・runtimeを同梱しない。MITの対象は自作部分であり、第三者の利用条件を上書きしない。
- `pywin32`の主表記はPSFだが、`adodbapi`にLGPL文書を含む。`setuptools`のvendored `autocommand`にもLGPL文書を再確認した。全体をMITだけと要約しない。
- `pip`はvendored依存の複数LICENSE、`cryptography`は選択ライセンスとnotice、`tzdata`はIANA由来データの表示を含む。今回の確認はすべてのtransitive/native subcomponentの法的審査ではない。
- CPython 3.12.8はPSF等の別条件を持つオンライン取得Runtime。将来runtimeやwheelを同梱する場合は、対象版の再配布条件と表示を別途確認する。
- 依存範囲はlockされていないため、今後のsetup・別OS・異なるindexでは解決版が変わり得る。ライセンス・互換性・供給元の真正性や脆弱性の将来保証ではない。
- 旧観測版との差異を[2026-10-20表](PUBLIC_DEPENDENCY_LICENSES_2026-10-20.md)と区別し、公式資料転載の許諾問題は[再監査B1](PUBLIC_RELEASE_REAUDIT_2026-10-31.md#2-b1公式資料とschema--no-go)で扱う。
