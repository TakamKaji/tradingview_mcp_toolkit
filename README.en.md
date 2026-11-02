# TradingView MCP Toolkit

[日本語](README.md) | **English**

A **Python CLI and library for using the official TradingView MCP server without AI agents**. Run JSON-defined stock screenings, access market data, and incorporate these operations into external automation. No AI installation or subscription is required.

> **Unofficial project.** Not an official TradingView product; not affiliated with, approved by, or endorsed by TradingView.

## Typical uses

| Use | Approach |
| --- | --- |
| Save daily screenings and compare with the previous run | Standard CLI and JSON definitions, triggered by Windows Task Scheduler or an external scheduler |
| Incorporate symbol data and OHLCV into your own processing | Write a custom program using the Python wrappers |
| Repeat operations from a job management tool | Configure the external tool to invoke the CLI |
| Separate Python and dependencies from the host | Run data acquisition in a Docker container |
| Use saved results in a browser or spreadsheet | Convert saved JSON to CSV or HTML with the existing exporter |

## Available functionality

**Standard CLI:** execute Screening JSON, save result JSON, view history and compare runs with the same definition, and run Jobs manually. Native Windows supports daily Job registration with Task Scheduler. Managed Watchlist synchronization is an **explicit write operation** performed through a configured Job.

**Python API:** reuse existing authentication and communication through `TradingViewClient` methods such as `get_symbol_data`, `get_symbol_data_batch`, and `get_ohlcv` in custom programs. See [coverage of the 35 tool wrappers](docs/user/FEATURES.md#c-公式toolと本ツールの接続範囲) and the actual [Request definitions](src/tradingview_screening/integrations/tradingview/schemas.py).

**Dedicated CLI commands for individual symbol data or OHLCV, and Jobs for periodically saving them, are not included.** Arbitrary Python API responses do not automatically enter the standard Screening storage and comparison workflow.

## Installation

Internet access and a [TradingView plan supporting the official MCP server](https://www.tradingview.com/mcp/docs) are required. Download and extract **Code → Download ZIP** from [main](https://github.com/TakamKaji/tradingview_mcp_toolkit). If a specific GitHub Release exists, its Source code (zip) is another option.

### Native Windows

No system Python installation is required. On 64-bit Windows, double-click `setup.bat` and follow the prompts to authorize OAuth in TradingView's browser interface. Administrator privileges are not required.

Type `cmd` in File Explorer's address bar in the extracted folder, then run the read-only sample:

```bat
app.bat run public_sample_screen_daily
app.bat results latest sample_standard_screen
```

This Job saves results under the extracted folder's `results/` and does not write to Watchlists. See [Windows setup](docs/user/WINDOWS_SETUP.md).

### Docker (Windows, macOS, and other hosts)

Docker Desktop or a compatible environment with Compose is required. No host Python installation is needed. From the extracted folder, run:

```sh
docker compose -f compose.docker.yml build app
docker compose -f compose.docker.yml run --rm app --version
docker compose -f compose.docker.yml run --rm --service-ports app mcp auth
```

While authentication is running, follow the instructions and open `http://127.0.0.1:8765/oauth/authorize` in the host browser. Then check read-only retrieval and the saved result:

```sh
docker compose -f compose.docker.yml run --rm app screen public_japan_value
docker compose -f compose.docker.yml run --rm app results latest public_japan_value
```

Results and credentials are stored in dedicated Docker volumes. `mac.command` is an optional macOS launcher. See [Docker setup and storage](docs/user/DOCKER.md).

## Saved results and CSV/HTML export

JSON is the authoritative saved result used for history and comparisons. Convert saved JSON to **CSV or HTML** with the bundled `export-results.bat`: CSV for spreadsheets such as Excel, or HTML for a browser table with links to TradingView charts.

On Windows, replace the example path with your own saved result:

```bat
export-results.bat "results\2026-10-22\my_japan_value_153000.json" --format csv
export-results.bat "results\2026-10-22\my_japan_value_153000.json" --format html
```

Japanese is the default. Add `--lang en` for English CSV headers or the initial HTML language. Generated HTML also supports offline switching between Japanese and English. CSV uses UTF-8 with BOM; the source JSON and retrieved values remain unchanged. Normal screenings save JSON only; export is a separate, optional operation.

The same exporter is available in Docker. Use an input path inside the results volume:

```sh
docker compose -f compose.docker.yml run --rm --entrypoint python app -m tradingview_screening.export_results /workspace/results/2026-10-22/my_japan_value_153000.json --format csv
```

Export does not connect to TradingView or write to Watchlists. **Watchlist sync is a separate write operation that adds or removes symbols.** See [result export options](docs/user/RESULTS.md#保存jsonからcsvhtmlを作る任意の後変換) for output paths and overwrite handling.

## External automation

External systems can invoke the CLI repeatedly to run Screenings or Jobs. Windows Task Scheduler registration is built in. Calling commands from host-side cron, job managers, or workflow tools is a **user-configured integration**, not a dedicated connector supplied by this toolkit.

Configure the extracted folder as the working directory, the command, execution user, storage location, and access to credentials. Check stdout, stderr, exit codes, and newly saved results. **The Docker version has no built-in scheduler.** Schedule Compose commands or other invocations on the host.

Periodic symbol-data or OHLCV retrieval requires **custom processing using the Python wrappers plus an external scheduler**. Your program must define retrieval conditions, timestamps, storage format, and failure handling.

See the [Screening guide](docs/user/SCREENING_MANUAL.md#自分の条件を追加する) for your own criteria, [Jobs and Scheduler](docs/user/SCHEDULE_MANUAL.md) for Jobs and Windows scheduling, and [result exports](docs/user/RESULTS.md#保存jsonからcsvhtmlを作る任意の後変換) for CSV/HTML. Result commands take a Screening name, not a Job name.

## Optional AI assistance

[Instruction files and usage guidance](docs/user/AI_USAGE.md#プロジェクトルートでaiを起動する) are available for Gemini CLI, Codex, and Claude Code. AI can optionally help create criteria JSON or custom processing where standard functionality is insufficient. See the [shared AI guide](docs/user/AI_JSON_GUIDE.md). Independent agent acceptance still has [unverified items](docs/user/NATURAL_LANGUAGE_ACCEPTANCE.md); instruction files alone are not proof of successful execution.

## Limitations and safety

- **Provider coverage:** markets, indicators, and retrieval limits vary. Successful retrieval does not imply complete coverage. Check ignored conditions, nulls, row counts, retrieval timestamps, and OHLCV bar completion and price adjustments. See [observed limitations](docs/user/PROVIDER_VERIFICATION.md).
- **Unrestricted all-US-stock retrieval is unavailable:** the Provider rejects it; a 1,000-row limit and enumeration limitations prevent full coverage. `us_sector_morning` is disabled. See [details](docs/user/SCREENING_MANUAL.md#公式mcp-beta版のスクリーニング制限2026-10-18実機確認).
- **Writes and scheduling:** Watchlist sync writes to TradingView. `sample_screen_daily` starts with `enabled=true` and `watchlistSync=true`. `schedule apply` registers or updates all enabled Jobs; review definitions and targets before explicitly running it. The `public_sample_screen_daily` example above is read-only.
- **Credentials:** the Docker credential volume is not an encrypted OS keychain. Avoid sharing it or deleting it with commands such as `docker compose down -v`. See [storage and protection](docs/user/DOCKER.md#データと認証情報の保存場所).
- **Verification:** live OAuth, retrieval, and persistence were verified on Windows Docker Desktop / Linux amd64. Physical Mac, arm64, and first OAuth under a new Windows user remain unverified.

See the [manual index](docs/user/README.md) and [troubleshooting](docs/user/TROUBLESHOOTING.md). Manuals are in Japanese; the Japanese README is authoritative.

## License

[MIT License](LICENSE). Third-party materials and libraries retain their respective terms.
