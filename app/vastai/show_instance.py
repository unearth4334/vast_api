#!/usr/bin/env python3
import argparse
import requests
from tabulate import tabulate

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
    url = f"{VAST_BASE}/instances/{instance_id}/"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    instance = data.get("instances", {})

    return {
        "Instance ID": instance.get("id"),
        "Status": instance.get("cur_state"),
        "GPU": instance.get("gpu_name"),
        "GPU Count": instance.get("num_gpus"),
        "GPU RAM (GB)": round(instance.get("gpu_ram", 0) / 1024, 1),
        "CPU": instance.get("cpu_name"),
        "CPU Cores": instance.get("cpu_cores_effective"),
        "Disk (GB)": instance.get("disk_space"),
        "Download (Mbps)": instance.get("inet_down"),
        "Upload (Mbps)": instance.get("inet_up"),
        "Public IP": instance.get("public_ipaddr"),
        "SSH Host": instance.get("ssh_host"),
        "SSH Port": instance.get("ssh_port"),
        "Template": instance.get("template_name"),
        "Geolocation": instance.get("geolocation"),
        "OS": instance.get("os_version"),
    }


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
