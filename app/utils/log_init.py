"""
Log directory initialization utilities
"""

import os
import logging

logger = logging.getLogger(__name__)

# Configuration constants
LOG_BASE = os.environ.get('LOG_BASE', '/app/logs')


def ensure_all_log_directories():
    """Ensure all log directories exist with proper structure"""
    try:
        # Create main log directory
        os.makedirs(LOG_BASE, exist_ok=True)
        
        # Create VastAI log directories
        vastai_dir = os.path.join(LOG_BASE, 'vastai')
        os.makedirs(vastai_dir, exist_ok=True)
        os.makedirs(os.path.join(vastai_dir, 'api'), exist_ok=True)
        os.makedirs(os.path.join(vastai_dir, 'instances'), exist_ok=True)
        
        # Create sync log directories  
        sync_dir = os.path.join(LOG_BASE, 'sync')
        os.makedirs(sync_dir, exist_ok=True)
        os.makedirs(os.path.join(sync_dir, 'operations'), exist_ok=True)
        os.makedirs(os.path.join(sync_dir, 'progress'), exist_ok=True)
        
        # Create general application logs directory
        os.makedirs(os.path.join(LOG_BASE, 'app'), exist_ok=True)
        
        logger.info(f"Log directories initialized at {LOG_BASE}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize log directories: {e}")
        return False


def get_log_directory_info():
    """Get information about log directory structure"""
    info = {
        "log_base": LOG_BASE,
        "directories": {},
        "exists": os.path.exists(LOG_BASE)
    }
    
    if info["exists"]:
        subdirs = ["vastai/api", "vastai/instances", "sync/operations", "sync/progress", "app"]
        for subdir in subdirs:
            full_path = os.path.join(LOG_BASE, subdir)
            info["directories"][subdir] = {
                "path": full_path,
                "exists": os.path.exists(full_path),
                "writable": os.access(full_path, os.W_OK) if os.path.exists(full_path) else False
            }
    
    return info