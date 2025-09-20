import requests
import yaml
import time
import json
import logging
from .vast_display import display_vast_offers

VAST_BASE = "https://console.vast.ai/api/v0"

# Set up logging for SSH data tracking
logger = logging.getLogger(__name__)

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

    def _validate_ssh_data(self, instance_data, instance_id=None):
        """Validate SSH data integrity and log any inconsistencies"""
        ssh_host = instance_data.get("ssh_host")
        ssh_port = instance_data.get("ssh_port")
        
        # Log SSH data for debugging
        instance_ref = f"instance {instance_id}" if instance_id else "instance data"
        logger.info(f"SSH data for {instance_ref}: host='{ssh_host}', port={ssh_port}")
        
        # Check for suspicious SSH host patterns that might indicate incorrect data
        if ssh_host and isinstance(ssh_host, str):
            if ssh_host.startswith("ssh") and ".vast.ai" in ssh_host:
                logger.warning(f"Suspicious SSH host detected for {instance_ref}: {ssh_host} - this might be incorrect")
                logger.warning(f"Expected format: IP address, got: {ssh_host}")
        
        # Check for suspicious SSH port patterns
        if ssh_port and isinstance(ssh_port, (int, str)):
            try:
                port_num = int(ssh_port)
                if port_num > 30000:  # Ports above 30000 might be mapped/forwarded ports
                    logger.warning(f"High SSH port detected for {instance_ref}: {port_num} - verify this is correct")
            except (ValueError, TypeError):
                logger.error(f"Invalid SSH port format for {instance_ref}: {ssh_port}")
        
        return ssh_host, ssh_port

    def show_instance(self, instance_id):
        url = f"{VAST_BASE}/instances/{instance_id}/"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        instance = response.json().get("instances", {})

        # Validate SSH data for consistency
        ssh_host, ssh_port = self._validate_ssh_data(instance, instance_id)

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
            "SSH Host": ssh_host,
            "SSH Port": ssh_port,
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
        basic_instances = response.json().get("instances", [])
        
        # Fetch detailed data for each instance to get SSH host/port and other details
        detailed_instances = []
        for basic_instance in basic_instances:
            instance_id = basic_instance.get("id")
            if instance_id:
                try:
                    # Get detailed instance data
                    detail_url = f"{VAST_BASE}/instances/{instance_id}/"
                    detail_response = requests.get(detail_url, headers=self.headers)
                    detail_response.raise_for_status()
                    detailed_data = detail_response.json().get("instances", {})
                    
                    # Validate SSH data for consistency
                    self._validate_ssh_data(detailed_data, instance_id)
                    
                    detailed_instances.append(detailed_data)
                except Exception as e:
                    # If we can't get detailed data, fall back to basic data
                    logger.warning(f"Failed to get detailed data for instance {instance_id}: {e}")
                    self._validate_ssh_data(basic_instance, instance_id)
                    detailed_instances.append(basic_instance)
            else:
                detailed_instances.append(basic_instance)
        
        return detailed_instances

    def get_running_instance(self):
        """Get the first running instance (for VastAI sync)"""
        instances = self.list_instances()
        for instance in instances:
            if instance.get("cur_state") == "running":
                return instance
        return None


