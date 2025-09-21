#!/usr/bin/env python3
from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Dict, Any

# ---- Optional tabulate fallback (don't make this script hard-fail if missing) ----
try:
    from tabulate import tabulate  # type: ignore
    def format_table(items):
        return tabulate(items, tablefmt="fancy_grid")
except Exception:
    def format_table(items):
        # Minimal fallback if tabulate isn't installed
        return "\n".join(f"{k}: {v}" for k, v in items)

# ---- Keep existing imports for package mode; add robust fallback for script mode ----
try:
    # When imported as part of the package (original behavior)
    from ..utils.vastai_api import (  # type: ignore
        show_instance as api_show_instance,
        parse_instance_details,
        VastAIAPIError,
    )
except ImportError:
    # When executed directly: add repo root to sys.path and import via absolute path
    # This assumes file is at: <repo_root>/app/vastai/show_instance.py
    _here = pathlib.Path(__file__).resolve()
    _repo_root = _here.parents[2]  # up from vastai/ -> app/ -> <repo_root>
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))
    from app.utils.vastai_api import (  # type: ignore
        show_instance as api_show_instance,
        parse_instance_details,
        VastAIAPIError,
    )

VAST_BASE = "https://console.vast.ai/api/v0"  # kept for compatibility, even if unused


def load_api_key(api_file: str, provider: str = "vastai") -> str:
    """Read the api_key.txt file and extract the Vast.ai key."""
    with open(api_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith(f"{provider}:"):
                return line.split(":", 1)[1].strip()
    raise ValueError(f"No API key found for provider '{provider}' in {api_file}")


def get_instance_details(api_key: str, instance_id: str) -> Dict[str, Any]:
    """Fetch details of a specific Vast.ai instance and parse to a summary dict."""
    try:
        response_data = api_show_instance(api_key, instance_id)
        return parse_instance_details(response_data)
    except VastAIAPIError as e:
        raise ValueError(f"Failed to get instance details: {e}") from e


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Get Vast.ai instance details")
    parser.add_argument("api_key_file", help="Path to api_key.txt file")
    parser.add_argument("instance_id", help="Instance ID to query")
    args = parser.parse_args(argv)

    api_key = load_api_key(args.api_key_file)
    summary = get_instance_details(api_key, args.instance_id)

    print("\n🖥️ Instance Summary:\n")
    print(format_table(summary.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
