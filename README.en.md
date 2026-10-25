# TradingView MCP Support

[日本語](README.md) | **English**

A local CLI tool built around the official TradingView MCP server. **Run screeners with your own JSON-defined criteria, save results, and compare runs.** You control the screening rules and job schedules.

> **Unofficial project.** This tool is not an official TradingView product and is not affiliated with, approved by, or endorsed by TradingView.

## What you can do

| Feature | Description |
| --- | --- |
| Screening | Query markets such as Japan and the US using JSON-defined filters and columns |
| Results | Save JSON, view latest results and history, compare runs using the same definition |
| Jobs | Configure operations in JSON and run them manually |
| Watchlist sync | Add or remove symbols from a managed Watchlist (**write operation**) |
| Scheduling | Register daily jobs with Windows Task Scheduler (native Windows only) |

The package also provides **typed Python wrappers for 35 official MCP tools**. Not all of these tools are directly available through the CLI. Dedicated CLI commands and scheduled jobs for OHLCV, news, and financial data are not implemented ([feature coverage](docs/user/FEATURES.md), in Japanese).

## Quick start

You need internet access and a [TradingView plan with access to its official MCP server](https://www.tradingview.com/mcp/docs). You do **not** need to install Python on your host computer.

On the repository's [main branch](https://github.com/TakamKaji/tradingview_mcp_support), choose **Code → Download ZIP**, then extract it. When a GitHub Release is available, its **Source code (zip)** can also be used.

### Native Windows

1. On 64-bit Windows, **double-click `setup.bat`** in the extracted folder. Administrator privileges are not required.
2. Follow the prompts to authorize access to TradingView in your browser.
3. In File Explorer, type `cmd` in the extracted folder's address bar, then run:

```bat
app.bat run public_sample_screen_daily
app.bat results latest sample_standard_screen
```

This sample performs a **read-only TradingView operation and saves its result locally**. Native Windows results are saved under `results/` in the extracted folder.

[Detailed Windows setup (Japanese)](docs/user/WINDOWS_SETUP.md)

### Docker (Windows, macOS, and other hosts)

Install Docker Desktop or a compatible Docker environment with Compose. From a terminal in the extracted folder, run:

```sh
docker compose -f compose.docker.yml build app
docker compose -f compose.docker.yml run --rm app --version
docker compose -f compose.docker.yml run --rm --service-ports app mcp auth
```

While the authentication command is running, follow its instructions and open `http://127.0.0.1:8765/oauth/authorize` in your host browser. Once authorized, try a read-only screening and inspect its saved result:

```sh
docker compose -f compose.docker.yml run --rm app screen public_japan_value
docker compose -f compose.docker.yml run --rm app results latest public_japan_value
```

Results and OAuth credentials are stored in **Docker volumes**, not the host's `results/` folder. `mac.command` is an optional macOS launcher; the Docker configuration itself is not Mac-specific. Live OAuth, screening, and persistence were verified using Docker Desktop on Windows with Linux/amd64. Physical Mac and arm64 testing are still unverified.

[Docker authentication, storage, and troubleshooting (Japanese)](docs/user/DOCKER.md)

## Create screenings with ChatGPT or Codex

Ask ChatGPT or Codex to read the [AI screening generation guide](docs/user/AI_JSON_GUIDE.md), the actual schemas, Provider capabilities and bundled examples, then describe your request. The AI chooses between two approaches:

- **A (always preferred when sufficient): standard Screening JSON.** Create `screenings/*.json`; add `jobs/*.json` only when needed. Simple conditions do not need custom Python or BAT files.
- **B: advanced composite Python processing.** Use this only when a single JSON definition cannot express the request, such as filtering by another timeframe after fixing a ranking, or joining an external universe. Explain why Python is needed and reuse the existing official MCP client, authentication, request controls, compatible storage and Watchlist safeguards where applicable. A generic pipeline engine and dedicated CLI are not implemented.

**End users do not need Git or Codex.** ChatGPT provides complete files and save instructions; Codex saves and validates in an accessible local environment. Python requires an environment that can edit and validate the code. Report retrieval limits, missing data and unverified steps; never describe partial retrieval as complete coverage. File creation and live retrieval are separate actions. Start with Watchlist writes and scheduling disabled, and never write to TradingView or register scheduled tasks without explicit user instructions. Japanese documentation is authoritative; the guide includes an English note.

## Create your own screening and job

1. Copy `screenings/public_japan_value.json` to `screenings/my_japan_value.json` and change its internal `name` to `my_japan_value`.
2. Edit the market, filters, and output columns. On Windows, run `app.bat screen my_japan_value`.
3. For a reusable daily job, copy an example from `jobs/` and set `task.definition` to your screening name. Start with `enabled=false` and `watchlistSync=false` and test manually.

When viewing results, use the **screening name**, not the job name.

[Screening guide (Japanese)](docs/user/SCREENING_MANUAL.md#自分の条件を追加する) / [Job guide (Japanese)](docs/user/SCHEDULE_MANUAL.md#自分のjobを作る)

## Safety notes and limitations

- **Write operations:** The bundled `sample_screen_daily` job starts with `enabled=true` and `watchlistSync=true`. `schedule apply` registers or updates **all enabled jobs**. Check the job definitions and target Watchlist before using it. The `public_sample_screen_daily` example above does not write to Watchlists.
- **Full US-stock universe unavailable:** The official TradingView MCP provider rejects an unrestricted all-US-stock request. Its 1,000-row limit and lack of a verified full-universe enumeration method prevent complete coverage. `us_sector_morning` is disabled ([details in Japanese](docs/user/SCREENING_MANUAL.md#公式mcp-beta版のスクリーニング制限2026-10-18実機確認)).
- **Credentials:** The Docker credentials volume is **not an encrypted OS keychain**. Avoid deleting persistent volumes with commands such as `docker compose down -v` ([storage and security details, Japanese](docs/user/DOCKER.md#データと認証情報の保存場所)).

## Four ways to use results

- **JSON (default):** The authoritative saved result under `results/`, used for history and comparisons.
- **HTML (optional):** Convert a saved JSON file with a separate script into a browser-friendly table with chart links.
- **CSV (optional):** Convert the same JSON into a spreadsheet-friendly file.
- **TradingView Watchlist (explicit action only):** A managed Job can synchronize symbols with a Watchlist. **This is a write operation that adds/removes symbols, not a file conversion.**

For CSV or HTML, use `export-results.bat` on Windows or the `tradingview_screening.export_results` Python module inside Docker. See the [results export instructions (Japanese)](docs/user/RESULTS.md#保存jsonからcsvhtmlを作る任意の後変換). Normal screenings continue to save JSON only; other formats are never generated automatically.

## Documentation

Detailed manuals are currently written in **Japanese**.

| Topic | Guides |
| --- | --- |
| Setup and authentication | [Windows](docs/user/WINDOWS_SETUP.md) / [Docker](docs/user/DOCKER.md) |
| Features and configuration | [Feature coverage](docs/user/FEATURES.md) / [Screening](docs/user/SCREENING_MANUAL.md) |
| Results and automation | [Results/history/compare](docs/user/RESULTS.md) / [Jobs/Scheduler](docs/user/SCHEDULE_MANUAL.md) |
| More | [Watchlist sync](docs/user/WATCHLIST_SYNC.md) / [Using the CLI with AI](docs/user/AI_USAGE.md) / [Troubleshooting](docs/user/TROUBLESHOOTING.md) |

## License

[MIT License](LICENSE). Third-party documentation and libraries remain subject to their respective terms.
