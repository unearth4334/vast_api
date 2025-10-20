"""
VastAI API Logging Module

This module provides comprehensive logging for all VastAI API interactions.
It creates date-based JSON log files in the VASTAI_LOG_DIR directory.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

# Configure logging
logger = logging.getLogger(__name__)

# Configuration constants
LOG_BASE = os.environ.get('LOG_BASE', '/app/logs')
VASTAI_LOG_DIR = os.path.join(LOG_BASE, 'vastai')


def ensure_vastai_log_dir():
    """Ensure the VastAI log directory exists"""
    try:
        os.makedirs(VASTAI_LOG_DIR, exist_ok=True)
        # Also create subdirectories for better organization
        os.makedirs(os.path.join(VASTAI_LOG_DIR, 'api'), exist_ok=True)
        os.makedirs(os.path.join(VASTAI_LOG_DIR, 'instances'), exist_ok=True)
        return True
    except PermissionError:
        logger.error(f"Failed to create VastAI log directory {VASTAI_LOG_DIR}: Permission denied")
        return False


def get_log_filename(date: datetime = None) -> str:
    """
    Get the log filename for a given date.
    
    Args:
        date (datetime, optional): Date for the log file. Defaults to current date.
        
    Returns:
        str: Log filename in format "api_log_yyyymmdd.json"
    """
    if date is None:
        date = datetime.now()
    return f"api_log_{date.strftime('%Y%m%d')}.json"


def get_log_filepath(date: datetime = None) -> str:
    """
    Get the full path to a log file for a given date.
    
    Args:
        date (datetime, optional): Date for the log file. Defaults to current date.
        
    Returns:
        str: Full path to the log file
    """
    filename = get_log_filename(date)
    return os.path.join(VASTAI_LOG_DIR, 'api', filename)


def log_api_interaction(method: str, endpoint: str, request_data: Dict[Any, Any] = None, 
                       response_data: Dict[Any, Any] = None, status_code: int = None,
                       error: str = None, duration_ms: float = None) -> None:
    """
    Log a VastAI API interaction to the daily log file.
    
    Args:
        method (str): HTTP method (GET, POST, PUT, DELETE)
        endpoint (str): VastAI API endpoint
        request_data (dict, optional): Request payload/parameters
        response_data (dict, optional): Response data from API
        status_code (int, optional): HTTP status code
        error (str, optional): Error message if request failed
        duration_ms (float, optional): Request duration in milliseconds
    """
    if not ensure_vastai_log_dir():
        return
    
    timestamp = datetime.now()
    log_entry = {
        "timestamp": timestamp.isoformat(),
        "method": method,
        "endpoint": endpoint,
        "status_code": status_code,
        "duration_ms": duration_ms
    }
    
    # Add request data if provided (sanitize sensitive info)
    if request_data:
        sanitized_request = _sanitize_data(request_data)
        log_entry["request"] = sanitized_request
    
    # Add response data if provided (sanitize sensitive info)
    if response_data:
        sanitized_response = _sanitize_data(response_data)
        log_entry["response"] = sanitized_response
    
    # Add error if provided
    if error:
        log_entry["error"] = error
    
    log_filepath = get_log_filepath(timestamp)
    
    try:
        # Load existing log entries for the day
        log_entries = []
        if os.path.exists(log_filepath):
            with open(log_filepath, 'r') as f:
                log_entries = json.load(f)
        
        # Append new entry
        log_entries.append(log_entry)
        
        # Write back to file
        with open(log_filepath, 'w') as f:
            json.dump(log_entries, f, indent=2)
        
        logger.debug(f"VastAI API interaction logged to: {log_filepath}")
        
    except Exception as e:
        logger.error(f"Failed to log VastAI API interaction: {str(e)}")


def _sanitize_data(data: Dict[Any, Any]) -> Dict[Any, Any]:
    """
    Sanitize sensitive data from request/response.
    
    Args:
        data (dict): Data to sanitize
        
    Returns:
        dict: Sanitized data with sensitive values masked
    """
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    sensitive_keys = ['api_key', 'password', 'token', 'authorization', 'secret']
    
    for key, value in data.items():
        key_lower = str(key).lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_data(value)
        elif isinstance(value, list):
            sanitized[key] = [_sanitize_data(item) if isinstance(item, dict) else item for item in value]
        else:
            sanitized[key] = value
    
    return sanitized


def get_vastai_logs(max_lines: int = 100, date_filter: str = None) -> List[Dict[Any, Any]]:
    """
    Retrieve VastAI API logs.
    
    Args:
        max_lines (int): Maximum number of log entries to return
        date_filter (str, optional): Date filter in YYYYMMDD format
        
    Returns:
        list: List of log entries
    """
    if not ensure_vastai_log_dir():
        return []
    
    all_entries = []
    
    try:
        if date_filter:
            # Load specific date file
            log_filepath = os.path.join(VASTAI_LOG_DIR, 'api', f"api_log_{date_filter}.json")
            if os.path.exists(log_filepath):
                with open(log_filepath, 'r') as f:
                    entries = json.load(f)
                    all_entries.extend(entries)
        else:
            # Load all log files, sorted by date (newest first)
            api_log_dir = os.path.join(VASTAI_LOG_DIR, 'api')
            if not os.path.exists(api_log_dir):
                return []
                
            log_files = []
            for filename in os.listdir(api_log_dir):
                if filename.startswith('api_log_') and filename.endswith('.json'):
                    filepath = os.path.join(api_log_dir, filename)
                    log_files.append((os.path.getmtime(filepath), filepath))
            
            # Sort by modification time (newest first)
            log_files.sort(reverse=True)
            
            for _, filepath in log_files:
                try:
                    with open(filepath, 'r') as f:
                        entries = json.load(f)
                        all_entries.extend(entries)
                except Exception as e:
                    logger.error(f"Error reading log file {filepath}: {str(e)}")
        
        # Sort entries by timestamp (newest first) and limit
        all_entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return all_entries[:max_lines]
        
    except Exception as e:
        logger.error(f"Error retrieving VastAI logs: {str(e)}")
        return []


def get_vastai_log_manifest() -> List[Dict[str, Any]]:
    """
    Get a manifest of available VastAI log files.
    
    Returns:
        list: List of log file information
    """
    if not ensure_vastai_log_dir():
        return []
    
    manifest = []
    
    try:
        api_log_dir = os.path.join(VASTAI_LOG_DIR, 'api')
        if not os.path.exists(api_log_dir):
            return []
            
        for filename in os.listdir(api_log_dir):
            if filename.startswith('api_log_') and filename.endswith('.json'):
                filepath = os.path.join(api_log_dir, filename)
                try:
                    stat = os.stat(filepath)
                    with open(filepath, 'r') as f:
                        entries = json.load(f)
                    
                    # Extract date from filename
                    date_str = filename[8:16]  # api_log_YYYYMMDD.json
                    
                    manifest.append({
                        'filename': filename,
                        'date': date_str,
                        'size': stat.st_size,
                        'entry_count': len(entries),
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                except Exception as e:
                    logger.error(f"Error processing log file {filename}: {str(e)}")
        
        # Sort by date (newest first)
        manifest.sort(key=lambda x: x['date'], reverse=True)
        return manifest
        
    except Exception as e:
        logger.error(f"Error getting VastAI log manifest: {str(e)}")
        return []