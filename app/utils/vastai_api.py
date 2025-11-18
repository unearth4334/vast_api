"""
VastAI API Module

This module provides a centralized interface for all direct interactions with the VastAI API.
It consolidates API methods that were previously scattered across multiple files.
"""

import requests
import json
import logging
import time
import uuid
from .vastai_logging import log_api_interaction, enhanced_logger, LogContext
from ..vastai.vastai_utils import get_ssh_port

logger = logging.getLogger(__name__)

# VastAI API configuration
VAST_API_BASE_URL = "https://console.vast.ai/api/v0"

class VastAIAPIError(Exception):
    """Custom exception for VastAI API errors"""
    pass


def create_enhanced_context(operation_type: str = "api_call", instance_id: str = None, 
                          template_name: str = None) -> LogContext:
    """
    Create enhanced logging context for VastAI operations.
    
    Args:
        operation_type (str): Type of operation being performed
        instance_id (str, optional): VastAI instance ID if applicable
        template_name (str, optional): Template name if applicable
        
    Returns:
        LogContext: Enhanced context for logging
    """
    return LogContext(
        operation_id=f"{operation_type}_{int(time.time())}_{str(uuid.uuid4())[:8]}",
        user_agent=f"vast_api/1.0 ({operation_type})",
        session_id=f"session_{int(time.time())}",
        ip_address="localhost",  # Could be enhanced to capture real IP
        instance_id=instance_id,
        template_name=template_name
    )


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


def query_offers(api_key, gpu_ram=10, sort="dph_total", limit=100, 
                 verified=True, rentable=True, external=False, rented=False, 
                 type_filter="on-demand", pcie_bandwidth=None, net_up=None, 
                 net_down=None, price_max=None, gpu_model=None, locations=None):
    """
    Query available VastAI offers using the correct search/asks API endpoint with enhanced logging.
    
    Args:
        api_key (str): VastAI API key
        gpu_ram (int): Minimum GPU RAM in GB
        sort (str): Sort criteria for offers (e.g., "dph_total", "score")
        limit (int): Maximum number of offers to return
        verified (bool): Filter for verified offers
        rentable (bool): Filter for rentable offers
        external (bool): Filter for external offers
        rented (bool): Filter for rented offers
        type_filter (str): Type of offers ("on-demand", etc.)
        pcie_bandwidth (float): Minimum PCIe bandwidth in GB/s
        net_up (int): Minimum upload speed in Mbps
        net_down (int): Minimum download speed in Mbps
        price_max (float): Maximum price per hour in USD
        gpu_model (str): GPU model filter string
        locations (list): List of location/country codes to filter by
        
    Returns:
        dict: JSON response from VastAI API containing offers
        
    Raises:
        VastAIAPIError: If API request fails
    """
    context = create_enhanced_context("query_offers")
    start_time = time.time()
    endpoint = "/search/asks/"
    method = "PUT"

    headers = create_headers(api_key)
    url = f"{VAST_API_BASE_URL}{endpoint}"

    # Build the query object according to API documentation
    query_body = {
        "select_cols": ["*"],
        "q": {
            "verified": {"eq": verified},
            "rentable": {"eq": rentable},
            "external": {"eq": external},
            "rented": {"eq": rented},
            "order": [[sort, "asc"]],
            "type": type_filter,
            "limit": limit
        }
    }

    # Add gpu_ram filter if specified (API expects MiB)
    if gpu_ram and gpu_ram > 0:
        query_body["q"]["gpu_ram"] = {"gte": int(gpu_ram * 1024)}  # GB -> MiB
    
    # Add PCIe bandwidth filter if specified (API expects GB/s)
    if pcie_bandwidth and pcie_bandwidth > 0:
        query_body["q"]["pcie_bw"] = {"gte": float(pcie_bandwidth)}
    
    # Add network upload speed filter if specified (API expects Mbps)
    if net_up and net_up > 0:
        query_body["q"]["inet_up"] = {"gte": int(net_up)}
    
    # Add network download speed filter if specified (API expects Mbps)
    if net_down and net_down > 0:
        query_body["q"]["inet_down"] = {"gte": int(net_down)}
    
    # Add maximum price filter if specified (API expects USD per hour)
    if price_max and price_max > 0:
        query_body["q"]["dph_total"] = {"lte": float(price_max)}
    
    # Add GPU model filter if specified (API expects partial string match)
    if gpu_model and gpu_model.strip():
        query_body["q"]["gpu_name"] = {"ilike": f"%{gpu_model.strip()}%"}
    
    # Add location filters if specified (API expects country codes)
    if locations and len(locations) > 0:
        # Filter out empty strings and convert to uppercase
        valid_locations = [loc.upper().strip() for loc in locations if loc.strip()]
        if valid_locations:
            query_body["q"]["geolocation"] = {"in": valid_locations}

    enhanced_logger.log_operation(
        message="Querying VastAI offers",
        operation="query_offers",
        context=context,
        extra_data={
            "filters": {
                "gpu_ram": gpu_ram,
                "gpu_model": gpu_model,
                "price_max": price_max,
                "limit": limit,
                "sort": sort
            },
            "endpoint": endpoint
        }
    )

    try:
        response = requests.put(url, headers=headers, json=query_body)
        response.raise_for_status()
        response_data = response.json()
        duration_ms = (time.time() - start_time) * 1000

        # Determine offer count for logging (API may use "offers" or "asks")
        offers_list = []
        if isinstance(response_data, dict):
            if "offers" in response_data and isinstance(response_data["offers"], list):
                offers_list = response_data["offers"]
            elif "asks" in response_data and isinstance(response_data["asks"], list):
                offers_list = response_data["asks"]

        # Enhanced performance and API logging
        enhanced_logger.log_performance(
            message="VastAI offers query completed",
            operation="query_offers",
            duration=duration_ms / 1000,
            context=context,
            extra_data={
                "offers_found": len(offers_list),
                "response_size": len(str(response_data)),
                "status_code": response.status_code
            }
        )

        enhanced_logger.log_api(
            message=f"Successfully queried {len(offers_list)} VastAI offers",
            status_code=response.status_code,
            context=context,
            extra_data={
                "offers_count": len(offers_list),
                "response_time_ms": duration_ms,
                "filters_applied": sum(1 for k, v in query_body["q"].items() if v not in [True, False, "on-demand"])
            }
        )

        # Enhanced API interaction logging with complete request/response data
        enhanced_logger.log_api_interaction(
            method=method,
            endpoint=endpoint,
            context=context,
            request_data=query_body,
            response_data=response_data,
            status_code=response.status_code,
            duration_ms=duration_ms,
            headers=headers,
            url=url
        )

        # Log successful API interaction (backward compatibility)
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

        # Enhanced error logging
        enhanced_logger.log_error(
            message=f"Failed to query VastAI offers: {str(e)}",
            error_type="api_request_error",
            context=context,
            extra_data={
                "exception": str(e),
                "exception_type": type(e).__name__,
                "response_time_ms": duration_ms,
                "status_code": getattr(response, 'status_code', None) if 'response' in locals() else None
            }
        )

        # Enhanced API interaction logging for errors with complete request data
        enhanced_logger.log_api_interaction(
            method=method,
            endpoint=endpoint,
            context=context,
            request_data=query_body,
            response_data=getattr(response, 'text', None) if 'response' in locals() else None,
            status_code=getattr(response, 'status_code', None) if 'response' in locals() else None,
            error=str(e),
            duration_ms=duration_ms,
            headers=headers,
            url=url
        )

        # Log failed API interaction (backward compatibility)
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
    Create a new VastAI instance with enhanced logging.
    
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
    context = create_enhanced_context("create_instance", instance_id=offer_id)
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
    
    enhanced_logger.log_operation(
        message=f"Creating VastAI instance from offer {offer_id}",
        operation="create_instance",
        context=context,
        extra_data={
            "offer_id": offer_id,
            "template_hash_id": template_hash_id,
            "disk_size_gb": disk_size_gb,
            "ui_home_env": ui_home_env,
            "endpoint": endpoint
        }
    )
    
    try:
        response = requests.put(f"{VAST_API_BASE_URL}{endpoint}", headers=headers, data=json.dumps(payload))
        response_time = time.time() - start_time
        
        # Handle VastAI API error responses
        if response.status_code != 200:
            duration_ms = response_time * 1000
            error_data = response.json() if response.text else {}
            error_msg = f"Failed to create instance: {error_data.get('error', 'Unknown error')}"
            
            # Enhanced error logging
            enhanced_logger.log_error(
                message=error_msg,
                error_type="instance_creation_failed",
                context=context,
                extra_data={
                    "status_code": response.status_code,
                    "error_data": error_data,
                    "response_time_ms": duration_ms,
                    "offer_id": offer_id
                }
            )
            
            # Enhanced API interaction logging for errors with complete request/response data
            enhanced_logger.log_api_interaction(
                method=method,
                endpoint=endpoint,
                context=context,
                request_data=payload,
                response_data=error_data,
                status_code=response.status_code,
                error=error_msg,
                duration_ms=duration_ms,
                headers=headers,
                url=f"{VAST_API_BASE_URL}{endpoint}"
            )
            
            # Log failed API interaction (backward compatibility)
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
        duration_ms = response_time * 1000
        new_instance_id = response_data.get("new_contract")
        
        # Enhanced success logging
        enhanced_logger.log_api(
            message=f"Successfully created VastAI instance {new_instance_id}",
            status_code=response.status_code,
            context=context,
            extra_data={
                "new_instance_id": new_instance_id,
                "response_time_ms": duration_ms,
                "offer_id": offer_id,
                "template_hash_id": template_hash_id
            }
        )
        
        enhanced_logger.log_performance(
            message="Instance creation completed",
            operation="create_instance",
            duration=response_time,
            context=context,
            extra_data={
                "instance_id": new_instance_id,
                "status_code": response.status_code
            }
        )
        
        # Enhanced API interaction logging with complete request/response data
        enhanced_logger.log_api_interaction(
            method=method,
            endpoint=endpoint,
            context=context,
            request_data=payload,
            response_data=response_data,
            status_code=response.status_code,
            duration_ms=duration_ms,
            headers=headers,
            url=f"{VAST_API_BASE_URL}{endpoint}"
        )
        
        # Log successful API interaction (backward compatibility)
        log_api_interaction(
            method=method,
            endpoint=endpoint,
            request_data=payload,
            response_data={"instance_id": new_instance_id},
            status_code=response.status_code,
            duration_ms=duration_ms
        )
        
        return response_data
        
    except requests.RequestException as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # Enhanced error logging
        enhanced_logger.log_error(
            message=f"Network error creating VastAI instance: {str(e)}",
            error_type="network_error",
            context=context,
            extra_data={
                "exception": str(e),
                "exception_type": type(e).__name__,
                "response_time_ms": duration_ms,
                "offer_id": offer_id
            }
        )
        
        # Log failed API interaction (backward compatibility)
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
    Get details of a specific VastAI instance with enhanced logging.
    
    Args:
        api_key (str): VastAI API key
        instance_id (str): ID of the instance
        
    Returns:
        dict: Instance details from VastAI API
        
    Raises:
        VastAIAPIError: If API request fails
    """
    context = create_enhanced_context("show_instance", instance_id=instance_id)
    start_time = time.time()
    endpoint = f"/instances/{instance_id}/"
    method = "GET"
    
    headers = create_headers(api_key)
    
    enhanced_logger.log_operation(
        message=f"Fetching details for VastAI instance {instance_id}",
        operation="show_instance",
        context=context,
        extra_data={"instance_id": instance_id, "endpoint": endpoint}
    )
    
    try:
        response = requests.get(f"{VAST_API_BASE_URL}{endpoint}", headers=headers)
        response.raise_for_status()
        response_data = response.json()
        duration_ms = (time.time() - start_time) * 1000
        
        # Enhanced success logging
        instance_status = response_data.get("cur_state")
        gpu_info = response_data.get("gpu_name")
        
        enhanced_logger.log_api(
            message=f"Retrieved instance {instance_id} details - Status: {instance_status}",
            status_code=response.status_code,
            context=context,
            extra_data={
                "instance_status": instance_status,
                "gpu_info": gpu_info,
                "response_time_ms": duration_ms,
                "instance_id": instance_id
            }
        )
        
        enhanced_logger.log_performance(
            message="Instance details retrieval completed",
            operation="show_instance",
            duration=duration_ms / 1000,
            context=context,
            extra_data={
                "instance_id": instance_id,
                "status_code": response.status_code
            }
        )
        
        # Log successful API interaction (backward compatibility)
        log_api_interaction(
            method=method,
            endpoint=endpoint,
            request_data={"instance_id": instance_id},
            response_data={"status": instance_status, "gpu": gpu_info},
            status_code=response.status_code,
            duration_ms=duration_ms
        )
        
        return response_data
        
    except requests.RequestException as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # Enhanced error logging
        enhanced_logger.log_error(
            message=f"Failed to get VastAI instance {instance_id} details: {str(e)}",
            error_type="instance_details_error",
            context=context,
            extra_data={
                "exception": str(e),
                "exception_type": type(e).__name__,
                "response_time_ms": duration_ms,
                "instance_id": instance_id,
                "status_code": getattr(response, 'status_code', None) if 'response' in locals() else None
            }
        )
        
        # Log failed API interaction (backward compatibility)
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
    Destroy a VastAI instance with enhanced logging.
    
    Args:
        api_key (str): VastAI API key
        instance_id (str): ID of the instance to destroy
        
    Returns:
        dict: JSON response from VastAI API
        
    Raises:
        VastAIAPIError: If API request fails
    """
    context = create_enhanced_context("destroy_instance", instance_id=instance_id)
    start_time = time.time()
    endpoint = f"/instances/{instance_id}/"
    method = "DELETE"
    
    headers = create_headers(api_key)
    
    enhanced_logger.log_operation(
        message=f"Destroying VastAI instance {instance_id}",
        operation="destroy_instance",
        context=context,
        extra_data={"instance_id": instance_id, "endpoint": endpoint}
    )
    
    try:
        response = requests.delete(f"{VAST_API_BASE_URL}{endpoint}", headers=headers)
        response.raise_for_status()
        response_data = response.json()
        duration_ms = (time.time() - start_time) * 1000
        
        # Enhanced success logging
        enhanced_logger.log_api(
            message=f"Successfully destroyed VastAI instance {instance_id}",
            status_code=response.status_code,
            context=context,
            extra_data={
                "instance_id": instance_id,
                "response_time_ms": duration_ms,
                "response_data": response_data
            }
        )
        
        enhanced_logger.log_performance(
            message="Instance destruction completed",
            operation="destroy_instance",
            duration=duration_ms / 1000,
            context=context,
            extra_data={
                "instance_id": instance_id,
                "status_code": response.status_code
            }
        )
        
        # Log successful API interaction (backward compatibility)
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
        
        # Enhanced error logging
        enhanced_logger.log_error(
            message=f"Failed to destroy VastAI instance {instance_id}: {str(e)}",
            error_type="instance_destruction_error",
            context=context,
            extra_data={
                "exception": str(e),
                "exception_type": type(e).__name__,
                "response_time_ms": duration_ms,
                "instance_id": instance_id,
                "status_code": getattr(response, 'status_code', None) if 'response' in locals() else None
            }
        )
        
        # Log failed API interaction (backward compatibility)
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
    List all VastAI instances for the current user with enhanced logging.
    
    Args:
        api_key (str): VastAI API key
        
    Returns:
        list: List of instance dictionaries
        
    Raises:
        VastAIAPIError: If API request fails
    """
    context = create_enhanced_context("list_instances")
    start_time = time.time()
    endpoint = "/instances/"
    method = "GET"
    
    headers = create_headers(api_key)
    
    enhanced_logger.log_operation(
        message="Listing all VastAI instances",
        operation="list_instances",
        context=context,
        extra_data={"endpoint": endpoint}
    )
    
    try:
        response = requests.get(f"{VAST_API_BASE_URL}{endpoint}", headers=headers)
        response.raise_for_status()
        response_data = response.json()
        instances = response_data.get("instances", [])
        duration_ms = (time.time() - start_time) * 1000
        
        # Count instances by status for enhanced logging
        status_counts = {}
        for instance in instances:
            status = instance.get("cur_state", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Enhanced success logging
        enhanced_logger.log_api(
            message=f"Successfully listed {len(instances)} VastAI instances",
            status_code=response.status_code,
            context=context,
            extra_data={
                "instance_count": len(instances),
                "status_breakdown": status_counts,
                "response_time_ms": duration_ms
            }
        )
        
        enhanced_logger.log_performance(
            message="Instance listing completed",
            operation="list_instances",
            duration=duration_ms / 1000,
            context=context,
            extra_data={
                "instance_count": len(instances),
                "status_code": response.status_code
            }
        )
        
        # Enhanced API interaction logging with complete response data
        enhanced_logger.log_api_interaction(
            method=method,
            endpoint=endpoint,
            context=context,
            request_data=None,
            response_data=response_data,
            status_code=response.status_code,
            duration_ms=duration_ms,
            headers=headers,
            url=f"{VAST_API_BASE_URL}{endpoint}"
        )
        
        # Log successful API interaction (backward compatibility)
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
        
        # Enhanced error logging
        enhanced_logger.log_error(
            message=f"Failed to list VastAI instances: {str(e)}",
            error_type="instance_listing_error",
            context=context,
            extra_data={
                "exception": str(e),
                "exception_type": type(e).__name__,
                "response_time_ms": duration_ms,
                "status_code": getattr(response, 'status_code', None) if 'response' in locals() else None
            }
        )
        
        # Log failed API interaction (backward compatibility)
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
    Get the first running VastAI instance with enhanced logging.
    
    Args:
        api_key (str): VastAI API key
        
    Returns:
        dict or None: First running instance, or None if none found
        
    Raises:
        VastAIAPIError: If API request fails
    """
    context = create_enhanced_context("get_running_instance")
    
    enhanced_logger.log_operation(
        message="Searching for running VastAI instances",
        operation="get_running_instance",
        context=context
    )
    
    instances = list_instances(api_key)
    
    running_instances = []
    for instance in instances:
        if instance.get("cur_state") == "running":
            running_instances.append(instance)
    
    if running_instances:
        selected_instance = running_instances[0]
        enhanced_logger.log_operation(
            message=f"Found running instance {selected_instance.get('id')}",
            operation="get_running_instance",
            context=context,
            extra_data={
                "instance_id": selected_instance.get("id"),
                "total_running": len(running_instances),
                "total_instances": len(instances)
            }
        )
        return selected_instance
    else:
        enhanced_logger.log_operation(
            message="No running instances found",
            operation="get_running_instance", 
            context=context,
            extra_data={
                "total_instances": len(instances),
                "running_instances": 0
            }
        )
        return None


def reboot_instance(api_key, instance_id):
    """
    Reboot a VastAI instance (stops and starts without losing GPU priority).
    
    Args:
        api_key (str): VastAI API key
        instance_id (str): ID of the instance to reboot
        
    Returns:
        dict: JSON response from VastAI API
        
    Raises:
        VastAIAPIError: If API request fails
    """
    context = create_enhanced_context("reboot_instance", instance_id=instance_id)
    start_time = time.time()
    endpoint = f"/instances/reboot/{instance_id}/"
    method = "PUT"
    
    headers = create_headers(api_key)
    
    enhanced_logger.log_operation(
        message=f"Rebooting VastAI instance {instance_id}",
        operation="reboot_instance",
        context=context,
        extra_data={"instance_id": instance_id, "endpoint": endpoint}
    )
    
    try:
        response = requests.put(f"{VAST_API_BASE_URL}{endpoint}", headers=headers)
        response.raise_for_status()
        response_data = response.json()
        duration_ms = (time.time() - start_time) * 1000
        
        # Enhanced success logging
        enhanced_logger.log_api(
            message=f"Successfully initiated reboot for VastAI instance {instance_id}",
            status_code=response.status_code,
            context=context,
            extra_data={
                "instance_id": instance_id,
                "response_time_ms": duration_ms,
                "response_data": response_data
            }
        )
        
        enhanced_logger.log_performance(
            message="Instance reboot initiated",
            operation="reboot_instance",
            duration=duration_ms / 1000,
            context=context,
            extra_data={
                "instance_id": instance_id,
                "status_code": response.status_code
            }
        )
        
        # Log successful API interaction (backward compatibility)
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
        
        # Enhanced error logging
        enhanced_logger.log_error(
            message=f"Failed to reboot VastAI instance {instance_id}: {str(e)}",
            error_type="instance_reboot_error",
            context=context,
            extra_data={
                "exception": str(e),
                "exception_type": type(e).__name__,
                "response_time_ms": duration_ms,
                "instance_id": instance_id,
                "status_code": getattr(response, 'status_code', None) if 'response' in locals() else None
            }
        )
        
        # Log failed API interaction (backward compatibility)
        log_api_interaction(
            method=method,
            endpoint=endpoint,
            request_data={"instance_id": instance_id},
            status_code=getattr(response, 'status_code', None) if 'response' in locals() else None,
            error=str(e),
            duration_ms=duration_ms
        )
        
        logger.error(f"Failed to reboot VastAI instance: {e}")
        raise VastAIAPIError(f"Failed to reboot instance: {e}") from e


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
        "SSH Port": get_ssh_port(instance),
        "Template": instance.get("template_name"),
        "Geolocation": instance.get("geolocation"),
        "OS": instance.get("os_version"),
    }
