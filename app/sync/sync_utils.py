"""
Sync utilities for handling media synchronization operations
"""

import os
import subprocess
import logging
import uuid
import json
import glob
import re
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Configuration constants
MEDIA_BASE = os.environ.get('MEDIA_BASE', '/media')
SYNC_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'sync_outputs.sh')
SYNC_LOG_DIR = os.path.join(MEDIA_BASE, '.sync_log')
FORGE_HOST = "10.0.78.108"
FORGE_PORT = "2222"
COMFY_HOST = "10.0.78.108"
COMFY_PORT = "2223"


def ensure_sync_log_dir():
    """Ensure the sync log directory exists"""
    try:
        os.makedirs(SYNC_LOG_DIR, exist_ok=True)
        return True
    except PermissionError:
        logger.error(f"Failed to create sync log directory {SYNC_LOG_DIR}: Permission denied")
        return False


def _parse_int(s, default=0):
    """Parse integer from string, return default if parsing fails"""
    try:
        return int(s)
    except (ValueError, TypeError):
        return default


def parse_sync_stats(output):
    """Parse rsync statistics from output"""
    stats = {
        'files_transferred': 0,
        'total_size': 0,
        'total_time': 0,
        'transfer_rate': 0
    }
    
    lines = output.split('\n')
    for line in lines:
        line = line.strip()
        
        # Parse files transferred
        if 'files transferred:' in line.lower():
            parts = line.split()
            for i, part in enumerate(parts):
                if part.isdigit():
                    stats['files_transferred'] = int(part)
                    break
        
        # Parse total size
        elif 'total size is' in line.lower():
            match = re.search(r'total size is ([\d,]+)', line)
            if match:
                stats['total_size'] = _parse_int(match.group(1).replace(',', ''))
        
        # Parse transfer time
        elif 'sent' in line.lower() and 'received' in line.lower():
            # Look for time in format like "1.23 seconds"
            time_match = re.search(r'([\d.]+)\s+seconds?', line)
            if time_match:
                stats['total_time'] = float(time_match.group(1))
            
            # Look for transfer rate
            rate_match = re.search(r'([\d,]+\.?\d*)\s+bytes/sec', line)
            if rate_match:
                stats['transfer_rate'] = _parse_int(rate_match.group(1).replace(',', ''))
    
    return stats


def save_sync_log(sync_type, result, start_time, end_time):
    """Save sync result to a timestamped JSON log file"""
    try:
        if not ensure_sync_log_dir():
            return
        
        timestamp = start_time.strftime('%Y%m%d_%H%M')
        log_filename = f"sync_log_{timestamp}.json"
        log_path = os.path.join(SYNC_LOG_DIR, log_filename)
        
        log_entry = {
            'timestamp': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'sync_type': sync_type,
            'duration': (end_time - start_time).total_seconds(),
            'result': result
        }
        
        with open(log_path, 'w') as f:
            json.dump(log_entry, f, indent=2)
        
        logger.info(f"Sync log saved to {log_path}")
        
    except Exception as e:
        logger.error(f"Failed to save sync log: {e}")


def run_sync(host, port, sync_type="unknown", cleanup=True):
    """Run sync operation to specified host and port"""
    if not os.path.exists(SYNC_SCRIPT_PATH):
        return {
            'success': False,
            'message': f'Sync script not found at {SYNC_SCRIPT_PATH}',
            'output': ''
        }
    
    start_time = datetime.now()
    sync_id = str(uuid.uuid4())
    
    logger.info(f"Starting {sync_type} sync to {host}:{port} with ID {sync_id} (cleanup: {cleanup})")
    
    # Create progress file
    progress_file = f"/tmp/sync_progress_{sync_id}.json"
    progress_data = {
        "sync_id": sync_id,
        "status": "running",
        "progress_percent": 0,
        "last_update": start_time.isoformat(),
        "sync_type": sync_type,
        "host": host,
        "port": port
    }
    
    with open(progress_file, 'w') as f:
        json.dump(progress_data, f)
    
    try:
        # Build the command
        cmd = [SYNC_SCRIPT_PATH, host, port]
        if cleanup:
            cmd.append("cleanup")
        
        # Run the sync
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        end_time = datetime.now()
        
        # Parse stats from output
        stats = parse_sync_stats(result.stdout)
        
        # Update progress file with completion
        progress_data.update({
            "status": "completed" if result.returncode == 0 else "failed",
            "progress_percent": 100,
            "last_update": end_time.isoformat(),
            "return_code": result.returncode
        })
        
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f)
        
        if result.returncode != 0:
            logger.error(f"{sync_type} sync failed with return code {result.returncode}")
            sync_result = {
                'success': False,
                'message': f'{sync_type} sync failed',
                'output': result.stderr or result.stdout,
                'sync_id': sync_id,
                'stats': stats
            }
        else:
            logger.info(f"{sync_type} sync completed successfully")
            sync_result = {
                'success': True,
                'message': f'{sync_type} sync completed successfully',
                'output': result.stdout,
                'sync_id': sync_id,
                'stats': stats
            }
        
        # Save to log
        save_sync_log(sync_type, sync_result, start_time, end_time)
        return sync_result
        
    except subprocess.TimeoutExpired:
        end_time = datetime.now()
        logger.error(f"{sync_type} sync timed out after 1 hour")
        
        # Update progress file with timeout
        progress_data.update({
            "status": "timeout", 
            "progress_percent": 50,  # Assume partial completion
            "last_update": end_time.isoformat()
        })
        
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f)
        
        sync_result = {
            'success': False,
            'message': f'{sync_type} sync timed out after 1 hour',
            'output': 'Sync operation timed out',
            'sync_id': sync_id,
            'stats': {}
        }
        
        save_sync_log(sync_type, sync_result, start_time, end_time)
        return sync_result
        
    except Exception as e:
        end_time = datetime.now()
        logger.error(f"{sync_type} sync error: {str(e)}")
        
        # Update progress file with error
        progress_data.update({
            "status": "error",
            "progress_percent": 0,
            "last_update": end_time.isoformat(),
            "error": str(e)
        })
        
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f)
        
        sync_result = {
            'success': False,
            'message': f'{sync_type} sync error: {str(e)}',
            'output': str(e),
            'sync_id': sync_id,
            'stats': {}
        }
        
        save_sync_log(sync_type, sync_result, start_time, end_time)
        return sync_result