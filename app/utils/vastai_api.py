"""
VastAI API Module

This module provides a centralized interface for all direct interactions with the VastAI API.
It consolidates API methods that were previously scattered across multiple files.
"""

import requests
import json
import logging
import time
from .vastai_logging import log_api_interaction

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


def query_offers(api_key,
                 gpu_ram=10,
                 sort="dph_total",
                 limit=100,
                 verified=True,
                 rentable=True,
                 external=False,
                 rented=False,
                 type_filter="on-demand",
                 *,
                 # NEW filters
                 pcie_min=None,          # GB/s
                 gpu_model=None,         # string
                 net_up_min=None,        # Mbps
                 net_down_min=None,      # Mbps
                 locations=None,         # list of country codes, e.g. ["CA","US"]
                 price_max=None):        # $/hr
    start_time = time.time()
    endpoint = "/search/asks/"
    method = "PUT"

    headers = create_headers(api_key)
    url = f"{VAST_API_BASE_URL}{endpoint}"

    q = {
        "verified": {"eq": verified},
        "rentable": {"eq": rentable},
        "external": {"eq": external},
        "rented":   {"eq": rented},
        "order":    [[sort, "asc"]],
        "type":     type_filter,
        "limit":    limit
    }


    # GPU RAM in MiB
    if gpu_ram and gpu_ram > 0:
        q["gpu_ram"] = {"gte": int(gpu_ram * 1024)}  # GB -> MiB

    # PCIe bandwidth in GB/s
    if pcie_min is not None:
        q["pcie_bw"] = {"gte": float(pcie_min)}

    # ---------- FIX: gpu_name (no regexp; use exact/in candidates) ----------
    def _gpu_name_candidates(term: str):
        t = term.strip()
        if not t:
            return []
        # Normalize spaces/underscores
        base = t.replace('-', ' ').replace('_', ' ').upper()
        parts = [p for p in base.split() if p]

        # If user just typed a series like "6000", build common variants
        cands = set()

        # Raw inputs (exact forms users commonly see on Vast)
        cands.add(t)
        cands.add(base)
        cands.add(base.replace(' ', '_'))

        # Common 6000-family expansions
        # e.g., "6000" -> A6000 / RTX 6000 / RTX_6000 / RTX 6000 Ada / RTX_6000_Ada
        if len(parts) == 1 and parts[0].isdigit():
            num = parts[0]
            cands.update({
                f"A{num}", f"RTX {num}", f"RTX_{num}",
                f"RTX {num} Ada", f"RTX_{num}_Ada"
            })

        # If user typed something like "RTX 6000" or "RTX_6000", also add Ada forms
        if any(p.isdigit() for p in parts) and any("RTX" in p for p in parts):
            num = next((p for p in parts if p.isdigit()), None)
            if num:
                cands.update({f"RTX {num} Ada", f"RTX_{num}_Ada"})

        return [c for c in cands if c]

    if gpu_model:
        name_list = _gpu_name_candidates(gpu_model)
        if len(name_list) == 1:
            q["gpu_name"] = {"eq": name_list[0]}
        elif len(name_list) > 1:
            q["gpu_name"] = {"in": name_list}
        # If empty, omit gpu_name filter entirely

    # Network speeds: API uses MB/s; UI likely in Mbps -> convert
    def _mbps_to_mbs(x):
        try:
            return float(x) / 8.0
        except Exception:
            return None

    if net_up_min is not None:
        up_mbs = _mbps_to_mbs(net_up_min)
        if up_mbs is not None:
            q["inet_up"] = {"gte": up_mbs}
    if net_down_min is not None:
        down_mbs = _mbps_to_mbs(net_down_min)
        if down_mbs is not None:
            q["inet_down"] = {"gte": down_mbs}

    # Locations
    if locations:
        q["country_code"] = {"in": [cc.upper() for cc in locations if cc]}

    # Price cap ($/hr)
    if price_max is not None:
        q["dph_total"] = {"lte": float(price_max)}

    query_body = {"select_cols": ["*"], "q": q}

    try:
        response = requests.put(url, headers=headers, json=query_body)
        response.raise_for_status()
        response_data = response.json()
        duration_ms = (time.time() - start_time) * 1000

        # Extract offers/asks for logging
        offers_list = []
        if isinstance(response_data, dict):
            if "offers" in response_data and isinstance(response_data["offers"], list):
                offers_list = response_data["offers"]
            elif "asks" in response_data and isinstance(response_data["asks"], list):
                offers_list = response_data["asks"]

        log_api_interaction(
            method=method,
            endpoint=endpoint,
            request_data=query_body,
            response_data={"offers_count": len(offers_list) if offers_list else "unknown"},
            status_code=response.status_code,
            duration_ms=duration_ms
        )

        return response_data

    except requests.RequestException as e:
        duration_ms = (time.time() - start_time) * 1000
        log_api_interaction(
            method=method,
            endpoint=endpoint,
            request_data=query_body,
            status_code=getattr(response, 'status_code', None) if 'response' in locals() else None,
            error=str(e),
            duration_ms=duration_ms
        )
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
    start_time = time.time()
    endpoint = f"/asks/{offer_id}/"
    method = "PUT"
    
    headers = create_headers(api_key)
    
    payload = {
        "template_hash_id": template_hash_id,
        "disk": disk_size_gb,
        "extra_env": json.dumps({"UI_HOME": ui_home_env}),
        "target_state": "running",
        "cancel_unavail": True
    }
    
    try:
        response = requests.put(f"{VAST_API_BASE_URL}{endpoint}", headers=headers, data=json.dumps(payload))
        # Handle VastAI API error responses
        if response.status_code != 200:
            duration_ms = (time.time() - start_time) * 1000
            error_data = response.json() if response.text else {}
            error_msg = f"Failed to create instance: {error_data.get('error', 'Unknown error')}"
            
            # Log failed API interaction
            log_api_interaction(
                method=method,
                endpoint=endpoint,
                request_data=payload,
                response_data=error_data,
                status_code=response.status_code,
                error=error_msg,
                duration_ms=duration_ms
            )
            
            logger.error(f"{error_msg} - {error_data}")
            raise VastAIAPIError(error_msg)
        
        response_data = response.json()
        duration_ms = (time.time() - start_time) * 1000
        
        # Log successful API interaction
        log_api_interaction(
            method=method,
            endpoint=endpoint,
            request_data=payload,
            response_data={"instance_id": response_data.get("new_contract")},
            status_code=response.status_code,
            duration_ms=duration_ms
        )
        
        return response_data
        
    except requests.RequestException as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # Log failed API interaction
        log_api_interaction(
            method=method,
            endpoint=endpoint,
            request_data=payload,
            status_code=getattr(response, 'status_code', None) if 'response' in locals() else None,
            error=str(e),
            duration_ms=duration_ms
        )
        
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
    start_time = time.time()
    endpoint = f"/instances/{instance_id}/"
    method = "GET"
    
    headers = create_headers(api_key)
    
    try:
        response = requests.get(f"{VAST_API_BASE_URL}{endpoint}", headers=headers)
        response.raise_for_status()
        response_data = response.json()
        duration_ms = (time.time() - start_time) * 1000
        
        # Log successful API interaction
        log_api_interaction(
            method=method,
            endpoint=endpoint,
            request_data={"instance_id": instance_id},
            response_data={"status": response_data.get("cur_state"), "gpu": response_data.get("gpu_name")},
            status_code=response.status_code,
            duration_ms=duration_ms
        )
        
        return response_data
        
    except requests.RequestException as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # Log failed API interaction
        log_api_interaction(
            method=method,
            endpoint=endpoint,
            request_data={"instance_id": instance_id},
            status_code=getattr(response, 'status_code', None) if 'response' in locals() else None,
            error=str(e),
            duration_ms=duration_ms
        )
        
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
    start_time = time.time()
    endpoint = f"/instances/{instance_id}/"
    method = "DELETE"
    
    headers = create_headers(api_key)
    
    try:
        response = requests.delete(f"{VAST_API_BASE_URL}{endpoint}", headers=headers)
        response.raise_for_status()
        response_data = response.json()
        duration_ms = (time.time() - start_time) * 1000
        
        # Log successful API interaction
        log_api_interaction(
            method=method,
            endpoint=endpoint,
            request_data={"instance_id": instance_id},
            response_data=response_data,
            status_code=response.status_code,
            duration_ms=duration_ms
        )
        
        return response_data
        
    except requests.RequestException as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # Log failed API interaction
        log_api_interaction(
            method=method,
            endpoint=endpoint,
            request_data={"instance_id": instance_id},
            status_code=getattr(response, 'status_code', None) if 'response' in locals() else None,
            error=str(e),
            duration_ms=duration_ms
        )
        
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
    start_time = time.time()
    endpoint = "/instances/"
    method = "GET"
    
    headers = create_headers(api_key)
    
    try:
        response = requests.get(f"{VAST_API_BASE_URL}{endpoint}", headers=headers)
        response.raise_for_status()
        response_data = response.json()
        instances = response_data.get("instances", [])
        duration_ms = (time.time() - start_time) * 1000
        
        # Log successful API interaction
        log_api_interaction(
            method=method,
            endpoint=endpoint,
            request_data=None,
            response_data={"instance_count": len(instances)},
            status_code=response.status_code,
            duration_ms=duration_ms
        )
        
        return instances
        
    except requests.RequestException as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # Log failed API interaction
        log_api_interaction(
            method=method,
            endpoint=endpoint,
            request_data=None,
            status_code=getattr(response, 'status_code', None) if 'response' in locals() else None,
            error=str(e),
            duration_ms=duration_ms
        )
        
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
