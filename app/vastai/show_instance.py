#!/usr/bin/env python3
import argparse
import requests
from tabulate import tabulate
from ..utils.vastai_api import show_instance as api_show_instance, parse_instance_details, VastAIAPIError

VAST_BASE = "https://console.vast.ai/api/v0"


def load_api_key(api_file: str, provider: str = "vastai") -> str:
    """Read the api_key.txt file and extract the Vast.ai key."""
    with open(api_file, "r") as f:
        for line in f:
            if line.strip().startswith(f"{provider}:"):
                return line.split(":", 1)[1].strip()
    raise ValueError(f"No API key found for provider '{provider}' in {api_file}")


def get_instance_details(api_key: str, instance_id: str) -> dict:
    """Fetch details of a specific Vast.ai instance."""
    try:
        response_data = api_show_instance(api_key, instance_id)
        return parse_instance_details(response_data)
    except VastAIAPIError as e:
        raise ValueError(f"Failed to get instance details: {e}") from e


def main():
    parser = argparse.ArgumentParser(description="Get Vast.ai instance details")
    parser.add_argument("api_key_file", help="Path to api_key.txt file")
    parser.add_argument("instance_id", help="Instance ID to query")
    args = parser.parse_args()

    api_key = load_api_key(args.api_key_file)
    summary = get_instance_details(api_key, args.instance_id)

    print("\n🖥️ Instance Summary:\n")
    print(tabulate(summary.items(), tablefmt="fancy_grid"))


if __name__ == "__main__":
    main()
