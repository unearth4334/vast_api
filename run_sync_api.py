#!/usr/bin/env python3
"""
Convenience script to run sync_api from new location
"""
import sys
import os

# Add current directory to path to import from app
sys.path.insert(0, os.path.dirname(__file__))

from app.sync.sync_api import app
import logging

if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Check if sync script exists
    from app.sync.sync_api import SYNC_SCRIPT_PATH
    if not os.path.exists(SYNC_SCRIPT_PATH):
        logger.error(f"Sync script not found at {SYNC_SCRIPT_PATH}")
        sys.exit(1)
    
    logger.info("Starting Media Sync API Server")
    app.run(host='0.0.0.0', port=5000, debug=False)