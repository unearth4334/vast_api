"""
Application-level logging utilities for vast_api
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Configuration constants
LOG_BASE = os.environ.get('LOG_BASE', '/app/logs')
APP_LOG_DIR = os.path.join(LOG_BASE, 'app')


def ensure_app_log_dir():
    """Ensure the application log directory exists"""
    try:
        os.makedirs(APP_LOG_DIR, exist_ok=True)
        return True
    except PermissionError:
        logger.error(f"Failed to create app log directory {APP_LOG_DIR}: Permission denied")
        return False


def log_application_event(event_type: str, message: str, details: Dict[Any, Any] = None) -> None:
    """
    Log an application-level event to daily log files.
    
    Args:
        event_type (str): Type of event (startup, shutdown, error, info, etc.)
        message (str): Human-readable message
        details (dict, optional): Additional event details
    """
    if not ensure_app_log_dir():
        return
    
    timestamp = datetime.now()
    date_str = timestamp.strftime('%Y%m%d')
    log_filepath = os.path.join(APP_LOG_DIR, f"app_log_{date_str}.json")
    
    log_entry = {
        "timestamp": timestamp.isoformat(),
        "event_type": event_type,
        "message": message
    }
    
    if details:
        log_entry["details"] = details
    
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
        
        logger.debug(f"Application event logged to: {log_filepath}")
        
    except Exception as e:
        logger.error(f"Failed to log application event: {str(e)}")


def log_startup():
    """Log application startup event"""
    log_application_event(
        "startup",
        "VastAI Sync API application started",
        {
            "log_base": LOG_BASE,
            "pid": os.getpid()
        }
    )


def log_shutdown():
    """Log application shutdown event"""  
    log_application_event(
        "shutdown",
        "VastAI Sync API application shutdown",
        {
            "pid": os.getpid()
        }
    )


def log_error(error_type: str, error_message: str, details: Dict[Any, Any] = None):
    """Log an application error"""
    log_application_event(
        f"error.{error_type}",
        error_message,
        details
    )


def log_info(info_type: str, message: str, details: Dict[Any, Any] = None):
    """Log an informational event"""
    log_application_event(
        f"info.{info_type}",
        message,
        details
    )