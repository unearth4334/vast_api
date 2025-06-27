import yaml
import requests
import time
import json
from tabulate import tabulate
from vast_display import display_vast_offers

VAST_BASE = "https://console.vast.ai/api/v0"

def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def load_api_key():
    with open("api_key.txt", "r") as f:
        return f.read().strip()

def query_offers(api_key, gpu_ram=10, sort="dph_total"):
    params = {
        "gpu_ram": gpu_ram,
        "sort": sort,
        "api_key": api_key
    }
    resp = requests.get(f"{VAST_BASE}/bundles", params=params)
    resp.raise_for_status()
    return resp.json()

def select_offer(offers):
    if not offers:
        print("❌ No offers to choose from.")
        return None
    try:
        index = int(input("Select offer index to launch: "))
        if 0 <= index < len(offers):
            return offers[index]
        else:
            print("❌ Index out of range.")
    except ValueError:
        print("❌ Please enter a valid integer.")
    return None

def create_instance(api_key, offer_id, template_hash_id, ui_home_env, disk_size_gb=32):

    # Set url = "https://console.vast.ai/api/v0/asks/1234/" where 1234 is the offer ID
    url = f"{VAST_BASE}/asks/{offer_id}/"
    
    payload = json.dumps({
    "template_hash_id": template_hash_id,
    "disk": disk_size_gb,
    "extra_env": f'{{"UI_HOME": "{ui_home_env}"}}',
    "target_state": "running",
    "cancel_unavail": True
    })
    headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}'
    }

    response = requests.request("PUT", url, headers=headers, data=payload)

    print(response.text)

    # If successful, the response will be like: {"success": true, "new_contract": 22035077}
    return response.json()

def destroy_instance(api_key, instance_id):

    url = f"{VAST_BASE}/instances/{instance_id}/"

    payload = {}
    headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}'
    }

    response = requests.request("DELETE", url, headers=headers, data=payload)

    print(response.text)

    return response.json()

def show_instance(api_key, instance_id):
    url = f"{VAST_BASE}/instances/{instance_id}/"

    payload = {}
    headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    data = response.json()
    instance = data.get("instances", {})

    summary = {
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

    print("\n🖥️ Instance Summary:\n")
    print(tabulate(summary.items(), tablefmt="fancy_grid"))
    
    return response.json()

def main():
    config = load_config()
    api_key = load_api_key()
    
    disk_size_gb = config.get("disk_size_gb", 32)
    template_hash_id = config.get("template_hash_id", "None")
    if template_hash_id == "None":
        print("❌ Template hash ID not set in config.yaml")
        return
    ui_home_env = config.get("ui_home_env", "None")
    if ui_home_env == "None":
        print("❌ UI_HOME environment variable not set in config.yaml")
        return

    offers_json = query_offers(api_key)
    filtered_offers = display_vast_offers(offers_json, config)
    if not filtered_offers:
        return

    selected = select_offer(filtered_offers)
    if not selected:
        return

    instance = create_instance(api_key, selected["id"], template_hash_id, ui_home_env, disk_size_gb)
    if  not instance.get("success"):
        print("❌ Failed to create instance.")
        print("Details:")
        print(f"  Error: {instance.get('error', 'Unknown error')}")
        print(f"  Message: {instance.get('msg', 'No message provided')}")
        print(f"  Ask ID: {instance.get('ask_id', 'No ask ID provided')}")
        return

    instance_id = instance.get("new_contract")
    print(f"🚀 Launched instance ID {instance_id} for offer {selected['id']}")

    # Wait a few second and then show the instance details
    time.sleep(5)
    instance_details = show_instance(api_key, instance_id)

    # Optionally destroy the instance after use
    destroy = input("Do you want to destroy the instance? (yes/no): ").strip().lower()
    if destroy == "yes":
        destroy_instance(api_key, instance_id)
        print(f"✅ Instance {instance_id} destroyed.")
    else:
        print("Instance not destroyed. You can manage it from the Vast.ai console.")


if __name__ == "__main__":
    main()
