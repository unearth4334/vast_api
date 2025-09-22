import yaml
import requests
import time
import json
from tabulate import tabulate
from .vast_display import display_vast_offers
from ..utils.vastai_api import (
    query_offers as api_query_offers,
    create_instance as api_create_instance,
    show_instance as api_show_instance,
    destroy_instance as api_destroy_instance,
    parse_instance_details,
    VastAIAPIError
)
from ..utils.config_loader import load_config, load_api_key

VAST_BASE = "https://console.vast.ai/api/v0"

def query_offers(api_key, gpu_ram=10, sort="dph_total"):
    try:
        return api_query_offers(api_key, gpu_ram, sort)
    except VastAIAPIError as e:
        print(f"❌ Failed to query offers: {e}")
        return {}

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
    try:
        result = api_create_instance(api_key, offer_id, template_hash_id, ui_home_env, disk_size_gb)
        print(json.dumps(result, indent=2))
        return result
    except VastAIAPIError as e:
        print(f"❌ Failed to create instance: {e}")
        return {"success": False, "error": str(e)}

def destroy_instance(api_key, instance_id):
    try:
        result = api_destroy_instance(api_key, instance_id)
        print(json.dumps(result, indent=2))
        return result
    except VastAIAPIError as e:
        print(f"❌ Failed to destroy instance: {e}")
        return {"success": False, "error": str(e)}

def show_instance(api_key, instance_id):
    try:
        response_data = api_show_instance(api_key, instance_id)
        summary = parse_instance_details(response_data)
        
        print("\n🖥️ Instance Summary:\n")
        print(tabulate(summary.items(), tablefmt="fancy_grid"))
        
        return response_data
    except VastAIAPIError as e:
        print(f"❌ Failed to get instance details: {e}")
        return {"success": False, "error": str(e)}

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
