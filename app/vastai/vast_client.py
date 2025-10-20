import requests
import json
from ..utils.vastai_api import (
    query_offers as api_query_offers,
    create_instance as api_create_instance,
    show_instance as api_show_instance,
    destroy_instance as api_destroy_instance,
    list_instances as api_list_instances,
    VastAIAPIError
)

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
        try:
            result = api_query_offers(self.api_key, gpu_ram, sort)
            return result.get("offers", [])
        except VastAIAPIError:
            return []

    def create_instance(self, offer_id, template_hash_id, ui_home_env, disk_size_gb=32):
        try:
            return api_create_instance(self.api_key, offer_id, template_hash_id, ui_home_env, disk_size_gb)
        except VastAIAPIError:
            raise

    def show_instance(self, instance_id):
        try:
            return api_show_instance(self.api_key, instance_id)
        except VastAIAPIError:
            raise

    def destroy_instance(self, instance_id):
        try:
            return api_destroy_instance(self.api_key, instance_id)
        except VastAIAPIError:
            raise

    def list_instances(self):
        """List all instances for the current user"""
        try:
            return api_list_instances(self.api_key)
        except VastAIAPIError:
            return []
