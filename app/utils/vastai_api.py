"""
VastAI API Module

This module provides a centralized interface for all direct interactions with the VastAI API.
It consolidates API methods that were previously scattered across multiple files.
"""

import requests
import json
import logging

logger = logging.getLogger(__name__)

# VastAI API configuration
VAST_API_BASE_URL = "https://console.vast.ai/api/v0"

class VastAIAPIError(Exception):
    """Custom exception for VastAI API errors"""
    pass


def create_headers(api_key):
    """
    Create standard headers for VastAI API requests.
    
    Args:
        api_key (str): VastAI API key
        
    Returns:
        dict: Headers dictionary for API requests
    """
    return {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }


def query_offers(api_key, gpu_ram=10, sort="dph_total"):
    """
    Query available VastAI offers.
    
    Args:
        api_key (str): VastAI API key
        gpu_ram (int): Minimum GPU RAM in GB
        sort (str): Sort criteria for offers
        
    Returns:
        dict: JSON response from VastAI API
        
    Raises:
        VastAIAPIError: If API request fails
    """
    try:
        params = {
            "gpu_ram": gpu_ram,
            "sort": sort,
            "api_key": api_key
        }
        
        response = requests.get(f"{VAST_API_BASE_URL}/bundles", params=params)
        response.raise_for_status()
        
        return response.json()
        
    except requests.RequestException as e:
        logger.error(f"Failed to query VastAI offers: {e}")
        raise VastAIAPIError(f"Failed to query offers: {e}") from e


def create_instance(api_key, offer_id, template_hash_id, ui_home_env, disk_size_gb=32):
    """
    Create a new VastAI instance.
    
    Args:
        api_key (str): VastAI API key
        offer_id (str): ID of the offer to use
        template_hash_id (str): Template hash for the instance
        ui_home_env (str): UI_HOME environment variable value
        disk_size_gb (int): Disk size in GB
        
    Returns:
        dict: JSON response from VastAI API
        
    Raises:
        VastAIAPIError: If API request fails
    """
    try:
        headers = create_headers(api_key)
        url = f"{VAST_API_BASE_URL}/asks/{offer_id}/"
        
        payload = json.dumps({
            "template_hash_id": template_hash_id,
            "disk": disk_size_gb,
            "extra_env": json.dumps({"UI_HOME": ui_home_env}),
            "target_state": "running",
            "cancel_unavail": True
        })
        
        response = requests.put(url, headers=headers, data=payload)
        
        # Handle VastAI API error responses
        if response.status_code != 200:
            error_data = response.json() if response.text else {}
            error_msg = f"Failed to create instance: {error_data.get('error', 'Unknown error')}"
            logger.error(f"{error_msg} - {error_data}")
            raise VastAIAPIError(error_msg)
        
        return response.json()
        
    except requests.RequestException as e:
        logger.error(f"Failed to create VastAI instance: {e}")
        raise VastAIAPIError(f"Failed to create instance: {e}") from e


def show_instance(api_key, instance_id):
    """
    Get details of a specific VastAI instance.
    
    Args:
        api_key (str): VastAI API key
        instance_id (str): ID of the instance
        
    Returns:
        dict: Instance details from VastAI API
        
    Raises:
        VastAIAPIError: If API request fails
    """
    try:
        headers = create_headers(api_key)
        url = f"{VAST_API_BASE_URL}/instances/{instance_id}/"
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()
        
    except requests.RequestException as e:
        logger.error(f"Failed to get VastAI instance details: {e}")
        raise VastAIAPIError(f"Failed to get instance details: {e}") from e


def destroy_instance(api_key, instance_id):
    """
    Destroy a VastAI instance.
    
    Args:
        api_key (str): VastAI API key
        instance_id (str): ID of the instance to destroy
        
    Returns:
        dict: JSON response from VastAI API
        
    Raises:
        VastAIAPIError: If API request fails
    """
    try:
        headers = create_headers(api_key)
        url = f"{VAST_API_BASE_URL}/instances/{instance_id}/"
        
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        
        return response.json()
        
    except requests.RequestException as e:
        logger.error(f"Failed to destroy VastAI instance: {e}")
        raise VastAIAPIError(f"Failed to destroy instance: {e}") from e


def list_instances(api_key):
    """
    List all VastAI instances for the current user.
    
    Args:
        api_key (str): VastAI API key
        
    Returns:
        list: List of instance dictionaries
        
    Raises:
        VastAIAPIError: If API request fails
    """
    try:
        headers = create_headers(api_key)
        url = f"{VAST_API_BASE_URL}/instances/"
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json().get("instances", [])
        
    except requests.RequestException as e:
        logger.error(f"Failed to list VastAI instances: {e}")
        raise VastAIAPIError(f"Failed to list instances: {e}") from e


def get_running_instance(api_key):
    """
    Get the first running VastAI instance.
    
    Args:
        api_key (str): VastAI API key
        
    Returns:
        dict or None: First running instance, or None if none found
        
    Raises:
        VastAIAPIError: If API request fails
    """
    instances = list_instances(api_key)
    
    for instance in instances:
        if instance.get("cur_state") == "running":
            return instance
    
    return None


def parse_instance_details(instance_data):
    """
    Parse and format instance details from VastAI API response.
    
    Args:
        instance_data (dict): Raw instance data from API
        
    Returns:
        dict: Formatted instance details
    """
    if not instance_data:
        return {}
    
    # Handle both direct instance data and wrapped response
    instance = instance_data.get("instances", instance_data)
    
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