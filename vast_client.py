import requests
import json

class VastClient:
    BASE_URL = "https://console.vast.ai/api/v0"

    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

    def query_offers(self, gpu_ram=10, sort="dph_total"):
        params = {
            "gpu_ram": gpu_ram,
            "sort": sort,
            "api_key": self.api_key
        }
        resp = requests.get(f"{self.BASE_URL}/bundles", params=params)
        resp.raise_for_status()
        return resp.json().get("offers", [])

    def create_instance(self, offer_id, template_hash_id, ui_home_env, disk_size_gb=32):
        url = f"{self.BASE_URL}/asks/{offer_id}/"
        payload = json.dumps({
            "template_hash_id": template_hash_id,
            "disk": disk_size_gb,
            "extra_env": f'{{"UI_HOME": "{ui_home_env}"}}',
            "target_state": "running",
            "cancel_unavail": True
        })
        resp = requests.put(url, headers=self.headers, data=payload)
        resp.raise_for_status()
        return resp.json()

    def show_instance(self, instance_id):
        url = f"{self.BASE_URL}/instances/{instance_id}/"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def destroy_instance(self, instance_id):
        url = f"{self.BASE_URL}/instances/{instance_id}/"
        resp = requests.delete(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def list_instances(self):
        """List all instances for the current user"""
        url = f"{self.BASE_URL}/instances/"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json().get("instances", [])
