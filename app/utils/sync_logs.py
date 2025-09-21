"""
Sync log management utilities
"""

import os
import json
import glob
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuration constants
MEDIA_BASE = os.environ.get('MEDIA_BASE', '/media')
SYNC_LOG_DIR = os.path.join(MEDIA_BASE, '.sync_log')


def _load_json(path):
    """Load JSON from file, return None if file doesn't exist or is invalid"""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _find_latest_progress():
    """Find the most recent progress file"""
    import glob as _glob
    
    progress_files = _glob.glob("/tmp/sync_progress_*.json")
    if not progress_files:
        return None
    
    # Sort by modification time, most recent first
    latest_file = max(progress_files, key=os.path.getmtime)
    return _load_json(latest_file)


def get_logs_manifest():
    """Get list of available log files with metadata"""
    try:
        if not os.path.exists(SYNC_LOG_DIR):
            return {"success": True, "logs": []}
        
        log_files = []
        for filename in sorted(os.listdir(SYNC_LOG_DIR), reverse=True):
            if filename.endswith('.json'):
                filepath = os.path.join(SYNC_LOG_DIR, filename)
                try:
                    stat = os.stat(filepath)
                    with open(filepath, 'r') as f:
                        log_data = json.load(f)
                    
                    # Extract result data
                    result = log_data.get('result', {})
                    
                    log_files.append({
                        'filename': filename,
                        'timestamp': log_data.get('timestamp'),
                        'sync_type': log_data.get('sync_type'),
                        'success': result.get('success', False),
                        'message': result.get('message', ''),
                        'duration_seconds': log_data.get('duration'),
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"Skipping invalid log file {filename}: {e}")
                    continue
        
        # Limit to most recent 50 logs
        return {"success": True, "logs": log_files[:50]}
        
    except Exception as e:
        logger.error(f"Error getting logs manifest: {e}")
        return {"success": False, "error": str(e)}


def get_log_file_content(filename):
    """Get the content of a specific log file"""
    try:
        # Security check - only allow files in the sync log directory
        if not filename.endswith('.json') or '/' in filename or '\\' in filename:
            return {"success": False, "error": "Invalid filename"}
        
        filepath = os.path.join(SYNC_LOG_DIR, filename)
        
        if not os.path.exists(filepath):
            return {"success": False, "error": "Log file not found"}
        
        with open(filepath, 'r') as f:
            log_data = json.load(f)
        
        # Extract result data and flatten for frontend
        result = log_data.get('result', {})
        
        # Create flattened log object with all fields frontend expects
        flattened_log = {
            'timestamp': log_data.get('timestamp'),
            'end_time': log_data.get('end_time'),
            'sync_type': log_data.get('sync_type'),
            'duration_seconds': log_data.get('duration'),
            'success': result.get('success', False),
            'message': result.get('message', ''),
            'output': result.get('output', ''),
            'error': result.get('error', ''),
            'sync_id': result.get('sync_id', ''),
            'filename': filename
        }
        
        return {"success": True, "log": flattened_log}
        
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON in log file"}
    except Exception as e:
        logger.error(f"Error reading log file {filename}: {e}")
        return {"success": False, "error": str(e)}


def get_active_syncs():
    """List all known progress files with brief status for debugging/menus"""
    import glob as _glob
    
    out = []
    for fp in sorted(_glob.glob("/tmp/sync_progress_*.json"), key=os.path.getmtime, reverse=True):
        data = _load_json(fp) or {}
        out.append({
            "sync_id": os.path.basename(fp)[len("sync_progress_"):-5],
            "status": data.get("status"),
            "progress_percent": data.get("progress_percent"),
            "last_update": data.get("last_update"),
        })
    return {"success": True, "items": out}


def get_latest_sync():
    """Get the most recent sync progress"""
    latest = _find_latest_progress()
    if latest:
        return {"success": True, "sync": latest}
    else:
        return {"success": False, "message": "No sync progress found"}


def get_sync_progress(sync_id):
    """Get progress for a specific sync operation"""
    progress_file = f"/tmp/sync_progress_{sync_id}.json"
    data = _load_json(progress_file)
    
    if data:
        return {"success": True, "progress": data}
    else:
        return {"success": False, "message": "Sync progress not found"}