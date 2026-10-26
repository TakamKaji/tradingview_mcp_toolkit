"""Compare a sanitized TradingView tools/list inputSchema snapshot with local Requests.

Run with the project Python: python scripts/development/compare_mcp_discovery.py PATH
The input is a JSON object with a ``tools`` map of wire name to inputSchema.
This inspection never connects to TradingView or modifies credentials.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("Usage: compare_mcp_discovery.py SNAPSHOT.json", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "tests"))
    from schema_contract import discovery_differences

    from tradingview_screening.integrations.tradingview.schemas import (
        REQUEST_MODELS,
    )

    snapshot = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    tools = snapshot["tools"]
    if not isinstance(tools, dict):
        raise TypeError("Snapshot tools must be a wire-name-to-inputSchema map")
    differences = discovery_differences(tools)
    print(json.dumps({
        "provider_tools": len(tools),
        "provider_parameters": sum(len(schema.get("properties", {})) for schema in tools.values()),
        "local_requests": len(REQUEST_MODELS),
        "local_parameters": sum(len(model.model_fields) for model in REQUEST_MODELS.values()),
        "differences": [asdict(item) for item in differences],
    }, ensure_ascii=False, indent=2))
    return 1 if any(item.kind != "default_review" for item in differences) else 0


if __name__ == "__main__":
    raise SystemExit(main())
