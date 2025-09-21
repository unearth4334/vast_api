import requests
import yaml
import time
import json
from .vast_display import display_vast_offers
from ..utils.vastai_api import (
    query_offers as api_query_offers,
    create_instance as api_create_instance,
    show_instance as api_show_instance,
    destroy_instance as api_destroy_instance,
    list_instances as api_list_instances,
    get_running_instance as api_get_running_instance,
    parse_instance_details,
    VastAIAPIError
)

VAST_BASE = "https://console.vast.ai/api/v0"

class VastManager:
    def __init__(self, config_path="config.yaml", api_key_path="api_key.txt"):
        self.config = self._load_yaml(config_path)
        self.api_key = self._load_api_key(api_key_path)
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

    def _load_yaml(self, path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def _load_api_key(self, path):
        with open(path, 'r') as f:
            content = f.read().strip()
            
        # Handle multi-line format: "vastai: <key>"
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('vastai:'):
                return line.split(':', 1)[1].strip()
        
        # Fallback to entire content if no "vastai:" prefix found
        return content

    def query_offers(self):
        gpu_ram_gb = self.config.get("gpu_ram", 10240) // 1024  # Convert MB to GB, default to 10 GB
        sort_criteria = self.config.get("sort", "dph_total")
        
        try:
            self.last_offers = api_query_offers(self.api_key, gpu_ram_gb, sort_criteria)
            return self.last_offers
        except VastAIAPIError as e:
            print(f"❌ Failed to query offers: {e}")
            raise

    def display_offers(self):
        if not hasattr(self, "last_offers"):
            self.query_offers()
        return display_vast_offers(self.last_offers, self.config)

    def create_instance(self, offer_id):
        template_hash_id = self.config.get("template_hash_id")
        ui_home = self.config.get("ui_home_env")
        disk = self.config.get("disk_size_gb", 32)

        if not template_hash_id or not ui_home:
            raise ValueError("Missing template_hash_id or ui_home_env in config.yaml")

        try:
            result = api_create_instance(self.api_key, offer_id, template_hash_id, ui_home, disk)
            return result
        except VastAIAPIError as e:
            print("❌ Failed to create instance.")
            print(f"Details: {e}")
            # Return empty dict to maintain compatibility
            return {}

    def show_instance(self, instance_id):
        try:
            response_data = api_show_instance(self.api_key, instance_id)
            instance_details = parse_instance_details(response_data)

            from tabulate import tabulate
            print("\n🖥️ Instance Summary:\n")
            print(tabulate(instance_details.items(), tablefmt="fancy_grid"))
            
            # Return the raw instance data for compatibility
            return response_data.get("instances", response_data)
        except VastAIAPIError as e:
            print(f"❌ Failed to get instance details: {e}")
            return {}

    def destroy_instance(self, instance_id):
        try:
            return api_destroy_instance(self.api_key, instance_id)
        except VastAIAPIError as e:
            print(f"❌ Failed to destroy instance: {e}")
            raise

    def list_instances(self):
        """List all instances for the current user"""
        try:
            return api_list_instances(self.api_key)
        except VastAIAPIError as e:
            print(f"❌ Failed to list instances: {e}")
            return []

    def get_running_instance(self):
        """Get the first running instance (for VastAI sync)"""
        try:
            return api_get_running_instance(self.api_key)
        except VastAIAPIError as e:
            print(f"❌ Failed to get running instance: {e}")
            return None


