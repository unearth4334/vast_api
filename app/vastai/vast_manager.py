import requests
import yaml
import time
import json
from .vast_display import display_vast_offers

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
        params = {
            # gpu_ram from config is in MB, so convert MB to GB
            "gpu_ram": self.config.get("gpu_ram", 10240) // 1024,  # Default to 10 GB if not set
            "sort": self.config.get("sort", "dph_total"),
            "api_key": self.api_key
        }
        resp = requests.get(f"{VAST_BASE}/bundles", params=params)
        resp.raise_for_status()
        self.last_offers = resp.json()
        return self.last_offers

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

        payload = json.dumps({
            "template_hash_id": template_hash_id,
            "disk": disk,
            "extra_env": json.dumps({"UI_HOME": ui_home}),
            "target_state": "running",
            "cancel_unavail": True
        })

        url = f"{VAST_BASE}/asks/{offer_id}/"
        response = requests.put(url, headers=self.headers, data=payload)
        
        # Check for errors in the response. Give error message if not 200 OK but dont quit
        if response.status_code != 200:
            data = response.json()
            print("❌ Failed to create instance.")
            print("Details:")
            print(f"  Error: {data.get('error', 'Unknown error')}")
            print(f"  Message: {data.get('msg', 'No message provided')}")
            print(f"  Ask ID: {data.get('ask_id', 'No ask ID provided')}")

        return response.json()

    def show_instance(self, instance_id):
        url = f"{VAST_BASE}/instances/{instance_id}/"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        instance = response.json().get("instances", {})

        from tabulate import tabulate
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
        return instance

    def destroy_instance(self, instance_id):
        url = f"{VAST_BASE}/instances/{instance_id}/"
        response = requests.delete(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def list_instances(self):
        """List all instances for the current user"""
        url = f"{VAST_BASE}/instances/"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json().get("instances", [])

    def get_running_instance(self):
        """Get the first running instance (for VastAI sync)"""
        instances = self.list_instances()
        for instance in instances:
            if instance.get("cur_state") == "running":
                return instance
        return None


