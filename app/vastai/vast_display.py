import json
import yaml
import requests
from tabulate import tabulate

import fnmatch
import operator
import re
from ..utils.match_filter import match_filter
from ..utils.vastai_api import query_offers as api_query_offers, VastAIAPIError


def parse_numeric_filter(expr):
    ops = {
        ">=": operator.ge,
        "<=": operator.le,
        ">": operator.gt,
        "<": operator.lt,
        "==": operator.eq
    }
    for op_str, op_func in ops.items():
        if expr.startswith(op_str):
            try:
                value = float(expr[len(op_str):].strip())
                return op_func, value
            except ValueError:
                return None, None
    return None, None


def display_vast_offers(resp_json, config):
    offers = resp_json.get("offers", [])
    if not offers:
        print("No offers found.")
        return []

    columns = [col for col in config["columns"] if col.strip()]
    headers = ["Index"] + [config["column_headers"].get(col, col) for col in columns]
    max_rows = config.get("max_rows", 10)
    filters = config.get("column_filters", {})

    filtered_offers = []
    for offer in offers:
        if all(match_filter(offer.get(k, ""), v, column=k) for k, v in filters.items()):
            filtered_offers.append(offer)

    if not filtered_offers:
        print("No matching offers found after filtering.")
        return []

    rows = []
    for i, offer in enumerate(filtered_offers[:max_rows]):
        row = [i]
        for col in columns:
            val = offer.get(col, "N/A")
            if col in ["gpu_ram", "cpu_ram", "disk_space"] and isinstance(val, (int, float)):
                val = round(val / 1024, 1)
            elif col == "dph_total" and isinstance(val, float):
                val = round(val, 5)
            elif col == "score" and isinstance(val, float):
                val = round(val, 2)
            elif col == "reliability" and isinstance(val, float):
                val = round(val, 4)
            row.append(val)
        rows.append(row)

    print(tabulate(rows, headers=headers, tablefmt="fancy_grid"))
    return filtered_offers[:max_rows]



if __name__ == "__main__":
    # Load API key
    with open('api_key.txt', 'r') as file:
        api_key = file.read().strip()

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Query Vast.ai using the new API module
    try:
        resp_json = api_query_offers(api_key, gpu_ram=10, sort='score')
        
        # Save raw response (optional)
        with open('output.json', 'w') as outfile:
            json.dump(resp_json, outfile)

        # Display formatted output
        display_vast_offers(resp_json, config)
    except VastAIAPIError as e:
        print(f"❌ Failed to query offers: {e}")
