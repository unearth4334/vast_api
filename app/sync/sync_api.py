#!/usr/bin/env python3
"""
Media Sync API Server
Provides web API endpoints for syncing media from local Docker containers and VastAI instances.
"""

import os
import requests
import subprocess
import logging
import uuid
import json
import glob
import re
from datetime import datetime
from flask import Flask, jsonify, request  # request added for after_request hook
from flask_cors import CORS

# Handle imports for both module and direct execution
try:
    from ..vastai.vast_manager import VastManager
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from vastai.vast_manager import VastManager

# Import SSH test functionality
try:
    from .ssh_test import SSHTester
except ImportError:
    try:
        from ssh_test import SSHTester
    except ImportError:
        SSHTester = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- CORS setup (allow local HTTP origins) ---
ALLOWED_ORIGINS = [
    "http://10.0.78.66",  # your NAS/API base
    "http://localhost",
    "http://127.0.0.1",
]
CORS(
    app,
    resources={
        r"/sync/*": {"origins": ALLOWED_ORIGINS},
        r"/vastai/*": {"origins": ALLOWED_ORIGINS},
        r"/status": {"origins": ALLOWED_ORIGINS},
        r"/test/*": {"origins": ALLOWED_ORIGINS},
        r"/logs/*": {"origins": ALLOWED_ORIGINS},
        r"/": {"origins": ALLOWED_ORIGINS},
    },
    supports_credentials=False,
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# Add Private Network Access header for Chromium-based apps
@app.after_request
def add_pna_header(resp):
    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Private-Network"] = "true"
        resp.headers["Vary"] = "Origin"
    return resp

# Configuration
SYNC_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'sync_outputs.sh')
MEDIA_BASE = '/media'
SYNC_LOG_DIR = os.path.join(MEDIA_BASE, '.sync_log')
FORGE_HOST = "10.0.78.108"
FORGE_PORT = "2222"
COMFY_HOST = "10.0.78.108"
COMFY_PORT = "2223"


def ensure_sync_log_dir():
    """Ensure the sync log directory exists"""
    try:
        os.makedirs(SYNC_LOG_DIR, exist_ok=True)
        logger.info(f"Sync log directory ensured at: {SYNC_LOG_DIR}")
    except Exception as e:
        logger.error(f"Failed to create sync log directory {SYNC_LOG_DIR}: {str(e)}")

def _parse_int(s, default=0):
    try:
        return int(s)
    except Exception:
        return default

def parse_sync_stats(output):
    """
    Parse sync statistics from script output. Supports:
      SYNC_SUMMARY: Files transferred: X, Folders synced: Y, Data transferred: Z bytes; BY_EXT: jpg=10,png=5,mp4=2
    Falls back gracefully if BY_EXT is absent.
    """
    stats = {
        'files_transferred': 0,
        'folders_synced': 0,
        'bytes_transferred': 0,
        'by_ext': {}
    }
    if not output:
        return stats

    for line in output.split('\n'):
        if 'SYNC_SUMMARY:' not in line:
            continue

        files_match = re.search(r'Files transferred:\s*(\d+)', line)
        folders_match = re.search(r'Folders synced:\s*(\d+)', line)
        bytes_match = re.search(r'Data transferred:\s*(\d+)', line)
        if files_match:   stats['files_transferred'] = _parse_int(files_match.group(1))
        if folders_match: stats['folders_synced']   = _parse_int(folders_match.group(1))
        if bytes_match:   stats['bytes_transferred'] = _parse_int(bytes_match.group(1))

        m_ext = re.search(r'BY_EXT:\s*([^\n]+)', line)
        if m_ext:
            by_ext = {}
            for pair in [p.strip() for p in m_ext.group(1).split(',') if p.strip()]:
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    k = k.strip().lower()
                    v = _parse_int(v.strip())
                    if k:
                        by_ext[k] = v
            stats['by_ext'] = by_ext
        break

    return stats

def save_sync_log(sync_type, result, start_time, end_time):
    """Save sync result to a timestamped JSON log file"""
    try:
        ensure_sync_log_dir()
        
        # Format: sync_log_yyyymmdd_hhmm.json
        timestamp = start_time.strftime("%Y%m%d_%H%M")
        log_filename = f"sync_log_{timestamp}.json"
        log_path = os.path.join(SYNC_LOG_DIR, log_filename)
        
        # Parse sync statistics from output
        sync_stats = parse_sync_stats(result.get('output', ''))
        
        log_data = {
            "timestamp": start_time.isoformat(),
            "end_timestamp": end_time.isoformat(),
            "sync_type": sync_type,
            "sync_id": result.get('sync_id', ''),
            "success": result.get('success', False),
            "message": result.get('message', ''),
            "output": result.get('output', ''),
            "error": result.get('error', ''),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "cleanup": result.get('cleanup', None),
            "cmd": result.get('cmd', None),
            # File transfer statistics
            "files_transferred": sync_stats['files_transferred'],
            "folders_synced": sync_stats['folders_synced'],
            "bytes_transferred": sync_stats['bytes_transferred'],
            "files_by_type": sync_stats['by_ext'],
        }

        
        # Add instance info if available (for VastAI syncs)
        if 'instance_info' in result:
            log_data['instance_info'] = result['instance_info']
        
        # Save to file
        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        logger.info(f"Sync log saved to: {log_path}")
        return log_filename
        
    except Exception as e:
        logger.error(f"Failed to save sync log: {str(e)}")
        return None

def run_sync(host, port, sync_type="unknown", cleanup=True):
    start_time = datetime.now()

    try:
        sync_id = str(uuid.uuid4())
        logger.info(f"Starting {sync_type} sync to {host}:{port} with ID {sync_id} (cleanup: {cleanup})")

        # Always pass an explicit cleanup argument
        cleanup_arg = "--cleanup" if cleanup else "--no-cleanup"

        cmd = [
            'bash', SYNC_SCRIPT_PATH,
            '-p', str(port),
            '--host', str(host),
            '--sync-id', sync_id,
            cleanup_arg,
        ]

        # Also export an env var in case your script prefers it
        env = os.environ.copy()
        env["SYNC_CLEANUP"] = "1" if cleanup else "0"
        env["SYNC_ID"] = sync_id  # often handy on the script side

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
        end_time = datetime.now()

        # Build common payload
        base = {
            'cleanup': bool(cleanup),
            'sync_id': sync_id,
            'cmd': " ".join(cmd),  # visible in logs for debugging
        }

        # Parse summary even on failure so UI can still show metrics
        sync_stats = parse_sync_stats(result.stdout)

        if result.returncode == 0:
            logger.info(f"{sync_type} sync completed successfully")
            sync_result = {
                **base,
                'success': True,
                'message': f'{sync_type} sync completed successfully',
                'output': result.stdout,
                'summary': {
                    'files_transferred': sync_stats['files_transferred'],
                    'folders_synced': sync_stats['folders_synced'],
                    'bytes_transferred': sync_stats['bytes_transferred'],
                    'by_ext': sync_stats['by_ext'],
                    'cleanup_enabled': bool(cleanup),
                    'duration_seconds': None  # Will be calculated and added later
                }
            }
        else:
            logger.error(f"{sync_type} sync failed with return code {result.returncode}")
            # Prefer stderr; if empty, show trimmed stdout to avoid the "Identity added…" confusion
            err = (result.stderr or "").strip() or (result.stdout or "").strip()
            sync_result = {
                **base,
                'success': False,
                'message': f'{sync_type} sync failed',
                'error': err,
                'output': result.stdout,
                'summary': {
                    'files_transferred': sync_stats['files_transferred'],
                    'folders_synced': sync_stats['folders_synced'],
                    'bytes_transferred': sync_stats['bytes_transferred'],
                    'by_ext': sync_stats['by_ext'],
                    'cleanup_enabled': bool(cleanup),
                    'duration_seconds': None
                }
            }

        # Add duration to summary if it exists
        if 'summary' in sync_result:
            sync_result['summary']['duration_seconds'] = (end_time - start_time).total_seconds()

        log_filename = save_sync_log(sync_type, sync_result, start_time, end_time)
        if log_filename:
            sync_result['log_filename'] = log_filename

        return sync_result

    except subprocess.TimeoutExpired:
        end_time = datetime.now()
        logger.error(f"{sync_type} sync timed out")
        sync_result = {
            'success': False,
            'message': f'{sync_type} sync timed out after 5 minutes',
            'cleanup': bool(cleanup),
            'sync_id': sync_id,
        }
        save_sync_log(sync_type, sync_result, start_time, end_time)
        return sync_result
    except Exception as e:
        end_time = datetime.now()
        logger.error(f"{sync_type} sync error: {str(e)}")
        sync_result = {
            'success': False,
            'message': f'{sync_type} sync error: {str(e)}',
            'cleanup': bool(cleanup),
            'sync_id': sync_id,
        }
        save_sync_log(sync_type, sync_result, start_time, end_time)
        return sync_result


@app.route('/')
def index():
    """Web interface for testing"""
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Media Sync Tool</title>
        <style>
                        :root {
                /* Modern dark theme color scheme */
                --color-accent: #7c3aed;
                --color-accent-hover: #8b5cf6;
                --color-accent-muted: #a78bfa;
                
                /* Backgrounds */
                --background-primary: #1e1e1e;
                --background-secondary: #2d2d2d;
                --background-secondary-alt: #363636;
                --background-modifier-border: #404040;
                --background-modifier-form-field: #2d2d2d;
                --background-modifier-box-shadow: rgba(0, 0, 0, 0.3);
                
                /* Text colors */
                --text-normal: #dcddde;
                --text-muted: #999999;
                --text-faint: #666666;
                --text-on-accent: #ffffff;
                
                /* Status colors */
                --text-success: #00c853;
                --text-warning: #ffb300;
                --text-error: #ff5722;
                --background-success: rgba(0, 200, 83, 0.1);
                --background-warning: rgba(255, 179, 0, 0.1);
                --background-error: rgba(255, 87, 34, 0.1);
                
                /* Interactive elements */
                --interactive-normal: #464749;
                --interactive-hover: #4a4d52;
                --interactive-accent: var(--color-accent);
                --interactive-accent-hover: var(--color-accent-hover);
                
                /* Sizes */
                --font-ui-smaller: 12px;
                --font-ui-small: 13px;
                --font-ui-medium: 14px;
                --font-ui-large: 16px;
                --font-ui-larger: 18px;
                
                --size-4-1: 4px;
                --size-4-2: 8px;
                --size-4-3: 12px;
                --size-4-4: 16px;
                --size-4-5: 20px;
                --size-4-6: 24px;
                --size-4-8: 32px;
                --size-4-12: 48px;
                
                --radius-s: 6px;
                --radius-m: 8px;
                --radius-l: 10px;
            }
            
            /* Light theme (default) */
            @media (prefers-color-scheme: light) {
                :root {
                    --background-primary: #ffffff;
                    --background-secondary: #f7f7f7;
                    --background-secondary-alt: #e3e3e3;
                    --background-modifier-border: #e3e3e3;
                    --background-modifier-form-field: #ffffff;
                    --background-modifier-box-shadow: rgba(0, 0, 0, 0.05);
                    
                    --text-normal: #2e3338;
                    --text-muted: #7c7c7c;
                    --text-faint: #b3b3b3;
                    
                    --interactive-normal: #f3f3f3;
                    --interactive-hover: #e8e8e8;
                }
            }
            
            * {
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background: var(--background-primary);
                color: var(--text-normal);
                margin: 0;
                padding: var(--size-4-4);
                line-height: 1.6;
                min-height: 100vh;
            }
            
            .container {
                max-width: 600px;
                margin: 0 auto;
                padding: var(--size-4-6);
            }
            
            .header {
                text-align: center;
                margin-bottom: var(--size-4-8);
            }
            
            .header h1 {
                font-size: var(--font-ui-larger);
                font-weight: 600;
                margin: 0 0 var(--size-4-2) 0;
                color: var(--text-normal);
                display: flex;
                align-items: center;
                justify-content: center;
                gap: var(--size-4-2);
            }
            
            .header p {
                color: var(--text-muted);
                font-size: var(--font-ui-medium);
                margin: 0;
            }
            
            .options-panel {
                background: var(--background-secondary);
                border: 1px solid var(--background-modifier-border);
                border-radius: var(--radius-m);
                padding: var(--size-4-4);
                margin-bottom: var(--size-4-6);
                box-shadow: 0 2px 8px var(--background-modifier-box-shadow);
            }
            
            .checkbox-container {
                display: flex;
                align-items: center;
                gap: var(--size-4-2);
                cursor: pointer;
                user-select: none;
            }
            
            .checkbox-container input[type="checkbox"] {
                width: 16px;
                height: 16px;
                accent-color: var(--interactive-accent);
                cursor: pointer;
            }
            
            .checkbox-container span {
                font-size: var(--font-ui-medium);
                color: var(--text-normal);
            }
            
            .sync-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: var(--size-4-4);
                margin-bottom: var(--size-4-6);
            }
            
            @media (max-width: 768px) {
                .sync-grid {
                    grid-template-columns: 1fr;
                }
            }
            
            .sync-button {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: var(--size-4-2);
                background: var(--interactive-accent);
                color: var(--text-on-accent);
                border: none;
                border-radius: var(--radius-m);
                padding: var(--size-4-4) var(--size-4-6);
                font-size: var(--font-ui-medium);
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
                box-shadow: 0 2px 4px var(--background-modifier-box-shadow);
                min-height: 48px;
                text-decoration: none;
            }
            
            .sync-button:hover {
                background: var(--interactive-accent-hover);
                transform: translateY(-1px);
                box-shadow: 0 4px 8px var(--background-modifier-box-shadow);
            }
            
            .sync-button:active {
                transform: translateY(0);
                box-shadow: 0 2px 4px var(--background-modifier-box-shadow);
            }
            
            .sync-button.secondary {
                background: var(--interactive-normal);
                color: var(--text-normal);
            }
            
            .sync-button.secondary:hover {
                background: var(--interactive-hover);
            }
            
            .result-panel {
                background: var(--background-secondary);
                border: 1px solid var(--background-modifier-border);
                border-radius: var(--radius-m);
                padding: var(--size-4-4);
                margin: var(--size-4-4) 0;
                box-shadow: 0 2px 8px var(--background-modifier-box-shadow);
                display: none;
            }
            
            .result-panel.success {
                border-color: var(--text-success);
                background: var(--background-success);
            }
            
            .result-panel.error {
                border-color: var(--text-error);
                background: var(--background-error);
            }
            
            .result-panel.loading {
                border-color: var(--color-accent);
                background: rgba(124, 58, 237, 0.1);
            }
            
            .result-panel h3 {
                margin: 0 0 var(--size-4-2) 0;
                font-size: var(--font-ui-medium);
                font-weight: 600;
            }
            
            .result-panel pre {
                white-space: pre-wrap;
                font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
                font-size: var(--font-ui-small);
                background: var(--background-modifier-form-field);
                padding: var(--size-4-3);
                border-radius: var(--radius-s);
                margin: var(--size-4-2) 0 0 0;
                overflow-x: auto;
            }
            
            .progress-panel {
                background: var(--background-secondary);
                border: 1px solid var(--background-modifier-border);
                border-radius: var(--radius-m);
                padding: var(--size-4-4);
                margin: var(--size-4-4) 0;
                box-shadow: 0 2px 8px var(--background-modifier-box-shadow);
                display: none;
            }
            
            .progress-panel h3 {
                margin: 0 0 var(--size-4-3) 0;
                font-size: var(--font-ui-medium);
                font-weight: 600;
            }
            
            .progress-bar {
                position: relative;
                height: 8px;
                background: var(--background-modifier-border);
                border-radius: var(--radius-s);
                overflow: hidden;
                margin: var(--size-4-2) 0;
            }
            
            .progress-fill {
                height: 100%;
                background: var(--interactive-accent);
                width: 0%;
                transition: width 0.3s ease;
                border-radius: var(--radius-s);
            }
            
            .progress-text {
                font-size: var(--font-ui-small);
                color: var(--text-muted);
                margin: var(--size-4-1) 0;
            }
            
            /* Loading animation */
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            
            .loading .sync-button {
                animation: pulse 2s infinite;
                pointer-events: none;
            }
            
            /* Focus styles for accessibility */
            .sync-button:focus {
                outline: 2px solid var(--interactive-accent);
                outline-offset: 2px;
            }
            
            .checkbox-container input:focus {
                outline: 2px solid var(--interactive-accent);
                outline-offset: 2px;
            }
            
            /* Logs panel styles */
            .logs-panel {
                background: var(--background-secondary);
                border: 1px solid var(--background-modifier-border);
                border-radius: var(--radius-m);
                padding: var(--size-4-4);
                margin: var(--size-4-4) 0;
                box-shadow: 0 2px 8px var(--background-modifier-box-shadow);
            }
            
            .logs-panel h3 {
                margin: 0 0 var(--size-4-3) 0;
                font-size: var(--font-ui-medium);
                font-weight: 600;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .refresh-logs-btn {
                background: var(--interactive-normal);
                color: var(--text-normal);
                border: none;
                border-radius: var(--radius-s);
                padding: var(--size-4-1) var(--size-4-3);
                font-size: var(--font-ui-small);
                cursor: pointer;
                transition: background 0.2s ease;
            }
            
            .refresh-logs-btn:hover {
                background: var(--interactive-hover);
            }
            
            .logs-list {
                display: flex;
                flex-direction: column;
                gap: var(--size-4-2);
                margin-top: var(--size-4-3);
            }
            
            .log-item {
                background: var(--background-primary);
                border: 1px solid var(--background-modifier-border);
                border-radius: var(--radius-s);
                padding: var(--size-4-3);
                cursor: pointer;
                transition: all 0.2s ease;
                box-shadow: 0 1px 3px var(--background-modifier-box-shadow);
            }
            
            .log-item:hover {
                background: var(--background-modifier-hover);
                transform: translateY(-1px);
                box-shadow: 0 2px 6px var(--background-modifier-box-shadow);
            }
            
            .log-item.success {
                border-left: 4px solid var(--text-success);
            }
            
            .log-item.error {
                border-left: 4px solid var(--text-error);
            }
            
            .log-summary {
                font-size: var(--font-ui-small);
                color: var(--text-normal);
                margin: 0;
                line-height: 1.4;
            }
            
            .log-meta {
                font-size: var(--font-ui-smaller);
                color: var(--text-muted);
                margin-top: var(--size-4-1);
            }
            
            /* Log overlay modal */
            .log-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: rgba(0, 0, 0, 0.5);
                display: none;
                justify-content: center;
                align-items: center;
                z-index: 1000;
                backdrop-filter: blur(2px);
            }
            
            .log-modal {
                background: var(--background-primary);
                border: 1px solid var(--background-modifier-border);
                border-radius: var(--radius-m);
                width: 90vw;
                max-width: 800px;
                max-height: 80vh;
                box-shadow: 0 8px 32px var(--background-modifier-box-shadow);
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }
            
            .log-modal-header {
                padding: var(--size-4-4);
                border-bottom: 1px solid var(--background-modifier-border);
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: var(--background-secondary);
            }
            
            .log-modal-title {
                font-size: var(--font-ui-medium);
                font-weight: 600;
                margin: 0;
                color: var(--text-normal);
            }
            
            .close-modal-btn {
                background: var(--interactive-normal);
                color: var(--text-normal);
                border: none;
                border-radius: var(--radius-s);
                padding: var(--size-4-2);
                cursor: pointer;
                font-size: var(--font-ui-medium);
                line-height: 1;
                transition: background 0.2s ease;
            }
            
            .close-modal-btn:hover {
                background: var(--interactive-hover);
            }
            
            .log-modal-content {
                padding: var(--size-4-4);
                overflow-y: auto;
                flex: 1;
            }
            
            .log-detail-section {
                margin-bottom: var(--size-4-4);
            }
            
            .log-detail-section h4 {
                margin: 0 0 var(--size-4-2) 0;
                font-size: var(--font-ui-small);
                font-weight: 600;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .log-detail-content {
                background: var(--background-modifier-form-field);
                border: 1px solid var(--background-modifier-border);
                border-radius: var(--radius-s);
                padding: var(--size-4-3);
                font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
                font-size: var(--font-ui-small);
                white-space: pre-wrap;
                word-wrap: break-word;
                max-height: 300px;
                overflow-y: auto;
            }
            
            .no-logs-message {
                text-align: center;
                color: var(--text-muted);
                font-style: italic;
                padding: var(--size-4-6);
            }
            
            /* Tab navigation styles */
            .tab-navigation {
                display: flex;
                background: var(--background-secondary);
                border: 1px solid var(--background-modifier-border);
                border-radius: var(--radius-m) var(--radius-m) 0 0;
                margin-bottom: 0;
                overflow: hidden;
            }
            
            .tab-button {
                background: transparent;
                border: none;
                padding: var(--size-4-3) var(--size-4-4);
                font-size: var(--font-ui-medium);
                font-weight: 500;
                color: var(--text-muted);
                cursor: pointer;
                transition: all 0.2s ease;
                flex: 1;
                text-align: center;
                border-bottom: 2px solid transparent;
            }
            
            .tab-button:hover {
                color: var(--text-normal);
                background: var(--background-secondary-alt);
            }
            
            .tab-button.active {
                color: var(--text-on-accent);
                background: var(--interactive-accent);
                border-bottom-color: var(--color-accent-hover);
            }
            
            .tab-content {
                display: none;
                background: var(--background-secondary);
                border: 1px solid var(--background-modifier-border);
                border-top: none;
                border-radius: 0 0 var(--radius-m) var(--radius-m);
                padding: var(--size-4-4);
                box-shadow: 0 2px 8px var(--background-modifier-box-shadow);
            }
            
            .tab-content.active {
                display: block;
            }
            
            /* VastAI Setup specific styles */
            .setup-field {
                margin-bottom: var(--size-4-4);
            }
            
            .setup-field label {
                display: block;
                margin-bottom: var(--size-4-2);
                font-weight: 500;
                color: var(--text-normal);
            }
            
            .setup-field input[type="text"] {
                width: 100%;
                padding: var(--size-4-3);
                border: 1px solid var(--background-modifier-border);
                border-radius: var(--radius-s);
                background: var(--background-modifier-form-field);
                color: var(--text-normal);
                font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
                font-size: var(--font-ui-small);
            }
            
            .setup-field input[type="text"]:focus {
                outline: 2px solid var(--interactive-accent);
                outline-offset: 2px;
                border-color: var(--interactive-accent);
            }
            
            .setup-buttons {
                display: flex;
                gap: var(--size-4-3);
                flex-wrap: wrap;
            }
            
            .setup-button {
                background: var(--interactive-accent);
                color: var(--text-on-accent);
                border: none;
                border-radius: var(--radius-s);
                padding: var(--size-4-2) var(--size-4-4);
                font-size: var(--font-ui-small);
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .setup-button:hover {
                background: var(--interactive-accent-hover);
            }
            
            .setup-button.secondary {
                background: var(--interactive-normal);
                color: var(--text-normal);
            }
            
            .setup-button.secondary:hover {
                background: var(--interactive-hover);
            }
            
            .setup-button.danger {
                background: var(--text-error);
                color: white;
            }
            
            .setup-button.danger:hover {
                background: #e53e3e;
            }
            
            .setup-result {
                margin-top: var(--size-4-3);
                padding: var(--size-4-3);
                border-radius: var(--radius-s);
                border: 1px solid var(--background-modifier-border);
                background: var(--background-modifier-form-field);
                font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
                font-size: var(--font-ui-small);
                display: none;
            }
            
            .setup-result.success {
                border-color: var(--text-success);
                background: var(--background-success);
            }
            
            .setup-result.error {
                border-color: var(--text-error);
                background: var(--background-error);
            }
            
            /* VastAI Instances Display */
            .vastai-instances-section {
                margin-bottom: var(--size-4-6);
                padding: var(--size-4-4);
                border: 1px solid var(--background-modifier-border);
                border-radius: var(--radius-s);
                background: var(--background-modifier-form-field);
            }
            
            .vastai-instances-section h4 {
                margin: 0 0 var(--size-4-3) 0;
                color: var(--text-normal);
            }
            
            .instances-list {
                margin-top: var(--size-4-3);
            }
            
            .no-instances-message {
                color: var(--text-muted);
                font-style: italic;
                text-align: center;
                padding: var(--size-4-4);
            }
            
            .instance-item {
                border: 1px solid var(--background-modifier-border);
                border-radius: var(--radius-s);
                padding: var(--size-4-3);
                margin-bottom: var(--size-4-2);
                background: var(--background-primary);
            }
            
            .instance-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: var(--size-4-2);
            }
            
            .instance-title {
                font-weight: 600;
                color: var(--text-normal);
            }
            
            .instance-status {
                padding: var(--size-4-1) var(--size-4-2);
                border-radius: var(--radius-s);
                font-size: var(--font-ui-smaller);
                font-weight: 500;
            }
            
            .instance-status.running {
                background: var(--background-success);
                color: var(--text-success);
            }
            
            .instance-status.stopped {
                background: var(--background-error);
                color: var(--text-error);
            }
            
            .instance-status.starting {
                background: var(--background-warning);
                color: var(--text-warning);
            }
            
            .instance-details {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: var(--size-4-2);
                font-size: var(--font-ui-small);
            }
            
            .instance-detail {
                color: var(--text-muted);
            }
            
            .instance-detail strong {
                color: var(--text-normal);
            }
            
            .instance-actions {
                margin-top: var(--size-4-3);
                display: flex;
                gap: var(--size-4-2);
            }
            
            .use-instance-btn {
                background: var(--interactive-accent);
                color: var(--text-on-accent);
                border: none;
                border-radius: var(--radius-s);
                padding: var(--size-4-1) var(--size-4-3);
                font-size: var(--font-ui-smaller);
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .use-instance-btn:hover {
                background: var(--interactive-accent-hover);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>
                    <span>🔄</span>
                    Media Sync Tool
                </h1>
                <p>Sync media from your configured sources</p>
            </div>
            
            <div class="tab-navigation">
                <button class="tab-button active" onclick="showTab('sync')">
                    🔄 Sync Operations
                </button>
                <button class="tab-button" onclick="showTab('vastai-setup')">
                    ⚙️ VastAI Setup
                </button>
            </div>
            
            <div id="sync-tab" class="tab-content active">
                <div class="options-panel">
                    <label class="checkbox-container">
                        <input type="checkbox" id="cleanupCheckbox" checked>
                        <span>🧹 Enable cleanup (delete remote folders older than 2 days)</span>
                    </label>
                </div>
                
                <div class="sync-grid">
                    <button class="sync-button" onclick="sync('forge')">
                        <span>🔥</span>
                        Sync Forge
                    </button>
                    <button class="sync-button" onclick="sync('comfy')">
                        <span>🖼️</span>
                        Sync Comfy
                    </button>
                    <button class="sync-button" onclick="sync('vastai')">
                        <span>☁️</span>
                        Sync VastAI
                    </button>
                    <button class="sync-button secondary" onclick="testSSH()">
                        <span>🔧</span>
                        Test SSH
                    </button>
                </div>
            </div>
            
            <div id="vastai-setup-tab" class="tab-content">
                <h3>VastAI SSH Connection Setup</h3>
                <p>Configure your VastAI SSH connection and manage UI_HOME settings.</p>
                
                <!-- VastAI Instances Section -->
                <div class="vastai-instances-section">
                    <h4>🖥️ Active VastAI Instances</h4>
                    <button class="setup-button secondary" onclick="loadVastaiInstances()">
                        🔄 Load Instances
                    </button>
                    <div id="vastai-instances-list" class="instances-list">
                        <!-- Instances will be displayed here -->
                        <div class="no-instances-message">Click "Load Instances" to see your active VastAI instances</div>
                    </div>
                </div>
                
                <hr style="margin: 20px 0; border: 1px solid var(--background-modifier-border);">
                
                <div class="setup-field">
                    <label for="sshConnectionString">SSH Connection String:</label>
                    <input type="text" id="sshConnectionString" 
                           placeholder="ssh -p 2838 root@104.189.178.116 -L 8080:localhost:8080"
                           title="Enter the SSH connection string from your VastAI instance">
                </div>
                
                <div class="setup-buttons">
                    <button class="setup-button" onclick="syncFromConnectionString()">
                        🔄 Sync Instance
                    </button>
                    <button class="setup-button" onclick="setUIHome()">
                        📁 Set UI_HOME to /workspace/ComfyUI/
                    </button>
                    <button class="setup-button secondary" onclick="getUIHome()">
                        📖 Read UI_HOME
                    </button>
                    <button class="setup-button" onclick="setupCivitDL()">
                        🎨 Setup CivitDL
                    </button>
                    <button class="setup-button danger" onclick="terminateConnection()">
                        🔌 Terminate Connection
                    </button>
                </div>
                
                <div id="setup-result" class="setup-result">
                    <!-- Results will be displayed here -->
                </div>
            </div>
            
            <div id="result" class="result-panel" title="Click to view full report"></div>
            
            <div id="progress" class="progress-panel">
                <h3>Sync Progress</h3>
                <div class="progress-bar">
                    <div id="progressBar" class="progress-fill"></div>
                </div>
                <div id="progressText" class="progress-text">Initializing...</div>
                <div id="progressDetails" class="progress-text"></div>
            </div>
            
            <div id="logs" class="logs-panel">
                <h3>
                    Recent Sync Logs
                    <button class="refresh-logs-btn" onclick="refreshLogs()">🔄 Refresh</button>
                </h3>
                <div id="logsList" class="logs-list">
                    <div class="no-logs-message">Click refresh to load recent logs</div>
                </div>
            </div>
        </div>
        
        <!-- Log detail overlay -->
        <div id="logOverlay" class="log-overlay">
            <div class="log-modal">
                <div class="log-modal-header">
                    <h3 id="logModalTitle" class="log-modal-title">Log Details</h3>
                    <button class="close-modal-btn" onclick="closeLogModal()">✕</button>
                </div>
                <div id="logModalContent" class="log-modal-content">
                    <!-- Content will be populated by JavaScript -->
                </div>
            </div>
        </div>
        
        <script>
            // Keep a copy of the last API response to show full output on click
            let lastFullReport = null;

            async function sync(type) {
                const resultDiv = document.getElementById('result');
                const progressDiv = document.getElementById('progress');
                const progressBar = document.getElementById('progressBar');
                const progressText = document.getElementById('progressText');
                const progressDetails = document.getElementById('progressDetails');
                const cleanupCheckbox = document.getElementById('cleanupCheckbox');
                
                lastFullReport = null;
                resultDiv.className = 'result-panel loading';
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `<h3>Starting ${type} sync...</h3><p>This may take several minutes.</p>`;
                
                // Show progress bar
                progressDiv.style.display = 'block';
                progressBar.style.width = '0%';
                progressText.textContent = 'Starting sync...';
                progressDetails.textContent = '';
                
                try {
                    const response = await fetch(`/sync/${type}`, { 
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            cleanup: cleanupCheckbox.checked
                        })
                    });
                    const data = await response.json();

                    // remember full response for the overlay
                    lastFullReport = data;
                    
                    // Start polling for progress if sync_id is available (regardless of initial success)
                    if (data.sync_id) {
                        pollProgress(data.sync_id);
                    } else {
                        progressDiv.style.display = 'none';
                    }
                    
                    if (data.success) {
                        resultDiv.className = 'result-panel success';
                        
                        // Show condensed summary if available, otherwise fall back to message
                        if (data.summary) {
                            const duration = data.summary.duration_seconds ? 
                                `${Math.round(data.summary.duration_seconds)}s` : 'Unknown';
                            const bytesFormatted = data.summary.bytes_transferred > 0 ?
                                formatBytes(data.summary.bytes_transferred) : '0 bytes';
                            const cleanupStatus = data.summary.cleanup_enabled ? 'enabled' : 'disabled';

                            // optional per-extension line (top 4)
                            let byExtLine = '';
                            if (data.summary.by_ext) {
                                const pairs = Object.entries(data.summary.by_ext)
                                  .sort((a,b)=>b[1]-a[1]).slice(0,4)
                                  .map(([k,v]) => `${k}:${v}`).join(' · ');
                                if (pairs) byExtLine = `<br>🧩 By type: ${pairs}`;
                            }
                            
                            resultDiv.innerHTML = `
                                <h3>✅ ${data.message}</h3>
                                <div style="margin-top: 12px;">
                                    <strong>Summary:</strong><br>
                                    📁 Folders synced: ${data.summary.folders_synced}<br>
                                    📄 Files transferred: ${data.summary.files_transferred}<br>
                                    💾 Data transferred: ${bytesFormatted}<br>
                                    ⏱️ Duration: ${duration}<br>
                                    🧹 Cleanup: ${cleanupStatus}
                                    ${byExtLine}
                                    <div style="margin-top:8px;color:var(--text-muted);font-size:12px;">Click to view full report</div>
                                </div>
                            `;
                        } else {
                            // Fallback for older format
                            resultDiv.innerHTML = `<h3>✅ ${data.message}</h3><pre>${data.output || ''}</pre>`;
                        }
                    } else {
                        resultDiv.className = 'result-panel error';
                        const brief = (data.error || data.output || '').split('\\n').slice(0,6).join('\\n');
                        resultDiv.innerHTML = `<h3>❌ ${data.message}</h3><pre>${brief}\\n\\n(Click for full report)</pre>`;
                    }
                } catch (error) {
                    resultDiv.className = 'result-panel error';
                    resultDiv.innerHTML = `<h3>❌ Request failed</h3><p>${error.message}</p>`;
                    // Keep progress bar visible if we might have a sync running
                    progressDiv.style.display = 'none';
                }
            }
            
            // Helper function to format bytes
            function formatBytes(bytes) {
                if (bytes === 0) return '0 bytes';
                const k = 1024;
                const sizes = ['bytes', 'KB', 'MB', 'GB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
            }
            
            function pollProgress(syncId) {
                let pollCount = 0;
                const maxPolls = 60; // 5 minutes at 5-second intervals
                
                const progressBar = document.getElementById('progressBar');
                const progressText = document.getElementById('progressText');
                const progressDetails = document.getElementById('progressDetails');
                const progressDiv = document.getElementById('progress');
                
                const poll = async () => {
                    try {
                        const response = await fetch(`/sync/progress/${syncId}`);
                        const data = await response.json();
                        
                        if (data.success && data.progress) {
                            const progress = data.progress;
                            
                            // Update progress bar
                            progressBar.style.width = `${progress.progress_percent}%`;
                            
                            // Update progress text
                            progressText.textContent = `${progress.current_stage}: ${progress.progress_percent}%`;
                            
                            // Update progress details
                            let details = "";
                            if (progress.total_folders > 0) {
                                details += `Folders: ${progress.completed_folders}/${progress.total_folders} `;
                            }
                            if (progress.current_folder) {
                                details += `Current: ${progress.current_folder}`;
                            }
                            progressDetails.textContent = details;
                            
                            // Show recent messages
                            if (progress.messages && progress.messages.length > 0) {
                                const lastMessage = progress.messages[progress.messages.length - 1];
                                if (lastMessage && lastMessage.message) {
                                    progressDetails.textContent = lastMessage.message;
                                }
                            }
                            
                            // Check if completed or failed
                            if (progress.status === 'completed' || progress.progress_percent >= 100) {
                                progressText.textContent = "Sync completed successfully!";
                                setTimeout(() => {
                                    progressDiv.style.display = 'none';
                                }, 3000);
                                return;
                            } else if (progress.status === 'error' || progress.status === 'failed') {
                                progressText.textContent = "Sync failed";
                                if (progress.messages && progress.messages.length > 0) {
                                    const lastMessage = progress.messages[progress.messages.length - 1];
                                    if (lastMessage && lastMessage.message) {
                                        progressDetails.textContent = lastMessage.message;
                                    }
                                }
                                setTimeout(() => {
                                    progressDiv.style.display = 'none';
                                }, 3000);
                                return;
                            }
                            
                            // Continue polling if not completed and under max polls
                            if (pollCount < maxPolls && progress.status !== 'error') {
                                pollCount++;
                                setTimeout(poll, 5000); // Poll every 5 seconds
                            } else {
                                // Timeout or error
                                if (pollCount >= maxPolls) {
                                    progressText.textContent = "Progress polling timed out";
                                }
                                setTimeout(() => {
                                    progressDiv.style.display = 'none';
                                }, 3000);
                            }
                        } else {
                            // Progress not found or error
                            progressText.textContent = "Progress tracking unavailable";
                            setTimeout(() => {
                                progressDiv.style.display = 'none';
                            }, 3000);
                        }
                    } catch (error) {
                        console.error("Error polling progress:", error);
                        progressText.textContent = `Progress error: ${error.message}`;
                        setTimeout(() => {
                            progressDiv.style.display = 'none';
                        }, 3000);
                    }
                };
                
                // Start polling immediately
                poll();
            }

            // Clicking the green/red callout opens the full overlay with all output
            (function attachResultClick(){
              const resultDiv = document.getElementById('result');
              resultDiv.addEventListener('click', () => {
                if (!lastFullReport) return;

                const overlay = document.getElementById('logOverlay');
                const modalTitle = document.getElementById('logModalTitle');
                const modalContent = document.getElementById('logModalContent');

                modalTitle.textContent = 'Sync Report';

                let content = '';
                // summary
                content += '<div class="log-detail-section"><h4>Summary</h4><div class="log-detail-content">';
                content += (lastFullReport.message || '') + '\\n';
                if (lastFullReport.summary) {
                    const s = lastFullReport.summary;
                    const bytes = s.bytes_transferred > 0 ? formatBytes(s.bytes_transferred) : '0 bytes';
                    content += `Files: ${s.files_transferred}\\nFolders: ${s.folders_synced}\\nBytes: ${bytes}\\n`;
                    if (s.by_ext) {
                        const extLine = Object.entries(s.by_ext).sort((a,b)=>b[1]-a[1]).map(([k,v])=>k+': '+v).join(', ');
                        if (extLine) content += `By type: ${extLine}\\n`;
                    }
                }
                content += '</div></div>';

                // stdout
                if (lastFullReport.output) {
                    content += '<div class="log-detail-section"><h4>Output</h4><div class="log-detail-content">';
                    content += String(lastFullReport.output).replace(/</g,'&lt;');
                    content += '</div></div>';
                }
                // stderr
                if (lastFullReport.error) {
                    content += '<div class="log-detail-section"><h4>Error</h4><div class="log-detail-content">';
                    content += String(lastFullReport.error).replace(/</g,'&lt;');
                    content += '</div></div>';
                }

                modalContent.innerHTML = content;
                overlay.style.display = 'flex';
              });
            })();
            
            async function testSSH() {
                const resultDiv = document.getElementById('result');
                resultDiv.className = 'result-panel loading';
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = '<h3>Testing SSH connectivity...</h3><p>Checking connections to all configured hosts.</p>';
                
                try {
                    const response = await fetch('/test/ssh', { method: 'POST' });
                    const data = await response.json();
                    
                    if (data.success) {
                        let output = `<h3>✅ SSH connectivity test completed</h3>`;
                        output += `<p><strong>Summary:</strong><br>`;
                        output += `Total hosts: ${data.summary.total_hosts}<br>`;
                        output += `Successful: ${data.summary.successful}<br>`;
                        output += `Failed: ${data.summary.failed}<br>`;
                        output += `Success rate: ${data.summary.success_rate}</p>`;
                        output += `<p><strong>Results:</strong></p><pre>`;
                        
                        for (const [host, result] of Object.entries(data.results)) {
                            const status = result.success ? '✅' : '❌';
                            output += `${status} ${host}: ${result.message}\\n`;
                            if (!result.success && result.error) {
                                output += `    Error: ${result.error}\\n`;
                            }
                        }
                        output += `</pre>`;
                        
                        resultDiv.className = 'result-panel success';
                        resultDiv.innerHTML = output;
                    } else {
                        resultDiv.className = 'result-panel error';
                        resultDiv.innerHTML = `<h3>❌ SSH test failed</h3><p>${data.message}</p><pre>${data.error || ''}</pre>`;
                    }
                } catch (error) {
                    resultDiv.className = 'result-panel error';
                    resultDiv.innerHTML = `<h3>❌ Request failed</h3><p>${error.message}</p>`;
                }
            }
            
            // Logs functionality (unchanged)
 async function refreshLogs() {
                const logsList = document.getElementById('logsList');
                const refreshBtn = document.querySelector('.refresh-logs-btn');
                
                // Show loading state
                refreshBtn.textContent = '⟳ Loading...';
                refreshBtn.disabled = true;
                logsList.innerHTML = '<div class="no-logs-message">Loading logs...</div>';
                
                try {
                    const response = await fetch('/logs/manifest');
                    const data = await response.json();
                    
                    if (data.success && data.logs && data.logs.length > 0) {
                        // Get latest 5 logs
                        const recentLogs = data.logs.slice(0, 5);
                        displayLogs(recentLogs);
                    } else {
                        logsList.innerHTML = '<div class="no-logs-message">No logs available</div>';
                    }
                } catch (error) {
                    logsList.innerHTML = '<div class="no-logs-message">Failed to load logs: ' + error.message + '</div>';
                } finally {
                    refreshBtn.textContent = '🔄 Refresh';
                    refreshBtn.disabled = false;
                }
            }
            
            function displayLogs(logs) {
                const logsList = document.getElementById('logsList');
                logsList.innerHTML = '';
                
                logs.forEach(log => {
                    const logItem = document.createElement('div');
                    logItem.className = `log-item ${log.success ? 'success' : 'error'}`;
                    logItem.onclick = () => showLogDetails(log.filename);
                    
                    // Format timestamp
                    const date = new Date(log.timestamp);
                    const formattedDate = date.toLocaleDateString('en-US', { 
                        month: '2-digit', 
                        day: '2-digit', 
                        year: 'numeric' 
                    });
                    const formattedTime = date.toLocaleTimeString('en-US', { 
                        hour12: false,
                        hour: '2-digit', 
                        minute: '2-digit', 
                        second: '2-digit' 
                    });
                    
                    // Format duration
                    const duration = log.duration_seconds ? `(${log.duration_seconds}s)` : '';
                    
                    // Create log summary in the requested format
                    const statusIcon = log.success ? '✅' : '❌';
                    const syncType = log.sync_type ? log.sync_type.charAt(0).toUpperCase() + log.sync_type.slice(1) : 'Unknown';
                    
                    logItem.innerHTML = `
                        <div class="log-summary">
                            ${statusIcon} ${syncType} - ${formattedDate}, ${formattedTime}<br>
                            ${log.message} ${duration}
                        </div>
                        <div class="log-meta">Click to view details</div>
                    `;
                    
                    logsList.appendChild(logItem);
                });
            }
            
            async function showLogDetails(filename) {
                const overlay = document.getElementById('logOverlay');
                const modalTitle = document.getElementById('logModalTitle');
                const modalContent = document.getElementById('logModalContent');
                
                // Show loading state
                modalTitle.textContent = 'Loading log details...';
                modalContent.innerHTML = '<div class="no-logs-message">Loading...</div>';
                overlay.style.display = 'flex';
                
                try {
                    const response = await fetch(`/logs/${filename}`);
                    const data = await response.json();
                    
                    if (data.success && data.log) {
                        const log = data.log;
                        
                        // Update modal title
                        const syncType = log.sync_type ? log.sync_type.charAt(0).toUpperCase() + log.sync_type.slice(1) : 'Unknown';
                        const date = new Date(log.timestamp);
                        const formattedDateTime = date.toLocaleString('en-US');
                        modalTitle.textContent = `${syncType} Sync - ${formattedDateTime}`;
                        
                        // Build modal content
                        let content = '';
                        
                        // Basic info section
                        content += '<div class="log-detail-section">';
                        content += '<h4>Summary</h4>';
                        content += '<div class="log-detail-content">';
                        content += `Status: ${log.success ? '✅ Success' : '❌ Failed'}\n`;
                        content += `Type: ${syncType}\n`;
                        content += `Message: ${log.message}\n`;
                        if (log.duration_seconds) {
                            content += `Duration: ${log.duration_seconds} seconds\n`;
                        }
                        if (log.sync_id) {
                            content += `Sync ID: ${log.sync_id}\n`;
                        }
                        content += '</div>';
                        content += '</div>';
                        
                        // Output section (scrollable callout as requested)
                        if (log.output) {
                            content += '<div class="log-detail-section">';
                            content += '<h4>Output</h4>';
                            content += '<div class="log-detail-content">';
                            content += log.output;
                            content += '</div>';
                            content += '</div>';
                        }
                        
                        // Error section if there's an error
                        if (log.error) {
                            content += '<div class="log-detail-section">';
                            content += '<h4>Error</h4>';
                            content += '<div class="log-detail-content">';
                            content += log.error;
                            content += '</div>';
                            content += '</div>';
                        }
                        
                        modalContent.innerHTML = content;
                    } else {
                        modalTitle.textContent = 'Error';
                        modalContent.innerHTML = '<div class="no-logs-message">Failed to load log details</div>';
                    }
                } catch (error) {
                    modalTitle.textContent = 'Error';
                    modalContent.innerHTML = '<div class="no-logs-message">Failed to load log details: ' + error.message + '</div>';
                }
            }
            function closeLogModal() {
                const overlay = document.getElementById('logOverlay');
                overlay.style.display = 'none';
            }
            document.addEventListener('DOMContentLoaded', function() {
                const overlay = document.getElementById('logOverlay');
                overlay.addEventListener('click', function(e) {
                    if (e.target === overlay) {
                        closeLogModal();
                    }
                });
            });
            
            // Tab switching functionality
            function showTab(tabName) {
                // Hide all tab contents
                const tabContents = document.querySelectorAll('.tab-content');
                tabContents.forEach(tab => tab.classList.remove('active'));
                
                // Remove active class from all tab buttons
                const tabButtons = document.querySelectorAll('.tab-button');
                tabButtons.forEach(button => button.classList.remove('active'));
                
                // Show selected tab content
                const selectedTab = document.getElementById(tabName + '-tab');
                if (selectedTab) {
                    selectedTab.classList.add('active');
                }
                
                // Add active class to clicked tab button
                const clickedButton = event.target;
                clickedButton.classList.add('active');
            }
            
            // VastAI Setup functions
            async function setUIHome() {
                const sshConnectionString = document.getElementById('sshConnectionString').value.trim();
                const resultDiv = document.getElementById('setup-result');
                
                if (!sshConnectionString) {
                    showSetupResult('Please enter an SSH connection string first.', 'error');
                    return;
                }
                
                showSetupResult('Setting UI_HOME to /workspace/ComfyUI/...', 'info');
                
                try {
                    const response = await fetch('/vastai/set-ui-home', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            ssh_connection: sshConnectionString,
                            ui_home: '/workspace/ComfyUI/'
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        showSetupResult(data.message, 'success');
                    } else {
                        showSetupResult('Error: ' + data.message, 'error');
                    }
                } catch (error) {
                    showSetupResult('Request failed: ' + error.message, 'error');
                }
            }
            
            async function getUIHome() {
                const sshConnectionString = document.getElementById('sshConnectionString').value.trim();
                
                if (!sshConnectionString) {
                    showSetupResult('Please enter an SSH connection string first.', 'error');
                    return;
                }
                
                showSetupResult('Reading UI_HOME...', 'info');
                
                try {
                    const response = await fetch('/vastai/get-ui-home', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            ssh_connection: sshConnectionString
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        showSetupResult('UI_HOME: ' + data.ui_home, 'success');
                    } else {
                        showSetupResult('Error: ' + data.message, 'error');
                    }
                } catch (error) {
                    showSetupResult('Request failed: ' + error.message, 'error');
                }
            }
            
            async function terminateConnection() {
                const sshConnectionString = document.getElementById('sshConnectionString').value.trim();
                
                if (!sshConnectionString) {
                    showSetupResult('Please enter an SSH connection string first.', 'error');
                    return;
                }
                
                if (!confirm('Are you sure you want to terminate the SSH connection?')) {
                    return;
                }
                
                showSetupResult('Terminating SSH connection...', 'info');
                
                try {
                    const response = await fetch('/vastai/terminate-connection', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            ssh_connection: sshConnectionString
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        showSetupResult(data.message, 'success');
                    } else {
                        showSetupResult('Error: ' + data.message, 'error');
                    }
                } catch (error) {
                    showSetupResult('Request failed: ' + error.message, 'error');
                }
            }
            
            async function setupCivitDL() {
                const sshConnectionString = document.getElementById('sshConnectionString').value.trim();
                
                if (!sshConnectionString) {
                    showSetupResult('Please enter an SSH connection string first.', 'error');
                    return;
                }
                
                showSetupResult('Installing and configuring CivitDL...', 'info');
                
                try {
                    const response = await fetch('/vastai/setup-civitdl', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            ssh_connection: sshConnectionString
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        // Show output with newlines preserved
                        const outputDiv = document.getElementById('setup-result');
                        outputDiv.innerHTML = '<strong>CivitDL Setup Completed Successfully!</strong><br><br>' +
                                            '<strong>Output:</strong><pre style="white-space: pre-wrap; margin-top: 8px;">' + 
                                            (data.output || '').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</pre>';
                        outputDiv.className = 'setup-result success';
                        outputDiv.style.display = 'block';
                    } else {
                        showSetupResult('Error: ' + data.message + (data.output ? '\\n\\nOutput:\\n' + data.output : ''), 'error');
                    }
                } catch (error) {
                    showSetupResult('Request failed: ' + error.message, 'error');
                }
            }
            
            async function syncFromConnectionString() {
                const sshConnectionString = document.getElementById('sshConnectionString').value.trim();
                
                if (!sshConnectionString) {
                    showSetupResult('Please enter an SSH connection string first.', 'error');
                    return;
                }
                
                showSetupResult('Starting sync from connection string...', 'info');
                
                try {
                    const response = await fetch('/sync/vastai-connection', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            ssh_connection: sshConnectionString,
                            cleanup: true  // Default cleanup to true
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        // Show success message first
                        showSetupResult('Sync started successfully! Check sync tab for progress.', 'success');
                        
                        // Switch to sync tab to show progress
                        showTab('sync');
                        
                        // Show sync results in the main result panel
                        const resultDiv = document.getElementById('result');
                        const progressDiv = document.getElementById('progress');
                        
                        resultDiv.className = 'result-panel loading';
                        resultDiv.style.display = 'block';
                        resultDiv.innerHTML = '<h3>Starting VastAI sync from connection string...</h3><p>This may take several minutes.</p>';
                        
                        // Start polling for progress if sync_id is available 
                        if (data.sync_id) {
                            progressDiv.style.display = 'block';
                            const progressBar = document.getElementById('progressBar');
                            const progressText = document.getElementById('progressText');
                            const progressDetails = document.getElementById('progressDetails');
                            progressBar.style.width = '0%';
                            progressText.textContent = 'Starting sync...';
                            progressDetails.textContent = '';
                            
                            pollProgress(data.sync_id);
                        }
                        
                        // Update result panel with final result after a short delay
                        setTimeout(() => {
                            if (data.summary) {
                                const duration = data.summary.duration_seconds ? 
                                    `${Math.round(data.summary.duration_seconds)}s` : 'Unknown';
                                const bytesFormatted = data.summary.bytes_transferred > 0 ?
                                    formatBytes(data.summary.bytes_transferred) : '0 bytes';
                                const cleanupStatus = data.summary.cleanup_enabled ? 'enabled' : 'disabled';

                                let byExtLine = '';
                                if (data.summary.by_ext) {
                                    const pairs = Object.entries(data.summary.by_ext)
                                      .sort((a,b)=>b[1]-a[1]).slice(0,4)
                                      .map(([k,v]) => `${k}:${v}`).join(' · ');
                                    if (pairs) byExtLine = `<br>🧩 By type: ${pairs}`;
                                }
                                
                                resultDiv.className = 'result-panel success';
                                resultDiv.innerHTML = `
                                    <h3>✅ ${data.message}</h3>
                                    <div style="margin-top: 12px;">
                                        <strong>Summary:</strong><br>
                                        📁 Folders synced: ${data.summary.folders_synced}<br>
                                        📄 Files transferred: ${data.summary.files_transferred}<br>
                                        💾 Data transferred: ${bytesFormatted}<br>
                                        ⏱️ Duration: ${duration}<br>
                                        🧹 Cleanup: ${cleanupStatus}
                                        ${byExtLine}
                                        <div style="margin-top:8px;color:var(--text-muted);font-size:12px;">Click to view full report</div>
                                    </div>
                                `;
                            } else {
                                resultDiv.className = 'result-panel success';
                                resultDiv.innerHTML = `<h3>✅ ${data.message}</h3><pre>${data.output || ''}</pre>`;
                            }
                        }, 1000);
                        
                    } else {
                        showSetupResult('Error: ' + data.message, 'error');
                    }
                } catch (error) {
                    showSetupResult('Request failed: ' + error.message, 'error');
                }
            }
            
            async function loadVastaiInstances() {
                const instancesList = document.getElementById('vastai-instances-list');
                instancesList.innerHTML = '<div class="no-instances-message">Loading instances...</div>';
                
                try {
                    const response = await fetch('/vastai/instances', {
                        method: 'GET',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        displayVastaiInstances(data.instances);
                    } else {
                        instancesList.innerHTML = '<div class="no-instances-message" style="color: var(--text-error);">Error: ' + data.message + '</div>';
                    }
                } catch (error) {
                    instancesList.innerHTML = '<div class="no-instances-message" style="color: var(--text-error);">Request failed: ' + error.message + '</div>';
                }
            }
            
            function displayVastaiInstances(instances) {
            const instancesList = document.getElementById('vastai-instances-list');

            if (!instances || instances.length === 0) {
                instancesList.innerHTML = '<div class="no-instances-message">No active VastAI instances found</div>';
                return;
            }

            let html = '';
            instances.forEach(instance => {
                const statusClass = instance.status ? instance.status.toLowerCase() : 'unknown';
                const sshConnection = instance.ssh_host && instance.ssh_port
                ? `ssh -p ${instance.ssh_port} root@${instance.ssh_host} -L 8080:localhost:8080`
                : 'N/A';

                html += `
                <div class="instance-item" data-instance-id="${instance.id}">
                    <div class="instance-header">
                    <div class="instance-title">Instance #${instance.id}</div>
                    <div class="instance-status ${statusClass}" data-field="status">${instance.status || 'Unknown'}</div>
                    </div>
                    <div class="instance-details">
                    <div class="instance-detail"><strong>GPU:</strong> ${instance.gpu || 'N/A'} ${instance.gpu_count ? '(' + instance.gpu_count + 'x)' : ''}</div>
                    <div class="instance-detail"><strong>GPU RAM:</strong> ${instance.gpu_ram_gb || 0} GB</div>
                    <div class="instance-detail"><strong>Location:</strong> <span data-field="geolocation">${instance.geolocation || 'N/A'}</span></div>
                    <div class="instance-detail"><strong>Cost:</strong> $${instance.cost_per_hour || 0}/hr</div>
                    <div class="instance-detail"><strong>SSH Host:</strong> <span data-field="ssh_host">${instance.ssh_host || 'N/A'}</span></div>
                    <div class="instance-detail"><strong>SSH Port:</strong> <span data-field="ssh_port">${instance.ssh_port || 'N/A'}</span></div>
                    </div>
                    <div class="instance-actions">
                    ${instance.ssh_host && instance.ssh_port && (instance.status || '').toLowerCase() === 'running' ? `
                        <button class="use-instance-btn" onclick="useInstance('${sshConnection}')">
                        📋 Use This Instance
                        </button>
                    ` : ``}
                    <button class="use-instance-btn" onclick="resolveInstanceParams(${instance.id})">
                        🔄 Refresh details
                    </button>
                    </div>
                </div>
                `;
            });

            instancesList.innerHTML = html;

            // OPTIONAL: auto-refresh each card once, to pull authoritative ssh_host/ssh_port
            instances.forEach(i => {
                // Fire-and-forget; errors surface through showSetupResult
                resolveInstanceParams(i.id);
            });
            }

            
            function useInstance(sshConnection) {
                const sshInput = document.getElementById('sshConnectionString');
                sshInput.value = sshConnection;
                showSetupResult('SSH connection string copied to input field', 'success');
            }
            
            function showSetupResult(message, type) {
                const resultDiv = document.getElementById('setup-result');
                resultDiv.textContent = message;
                resultDiv.className = 'setup-result ' + type;
                resultDiv.style.display = 'block';
                
                // Auto-hide info messages after 5 seconds
                if (type === 'info') {
                    setTimeout(() => {
                        if (resultDiv.classList.contains('info')) {
                            resultDiv.style.display = 'none';
                        }
                    }, 5000);
                }
            }

            async function fetchVastaiInstanceDetails(instanceId) {
            const resp = await fetch(`/vastai/instances/${instanceId}`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await resp.json();
            if (!resp.ok || !data.success) {
                throw new Error(data.message || `Failed to fetch details for ${instanceId}`);
            }
            return data.instance;
            }

            async function resolveInstanceParams(instanceId) {
            try {
                const inst = await fetchVastaiInstanceDetails(instanceId);

                const sshHost = inst.ssh_host || inst.public_ipaddr || null;
                const sshPort = inst.ssh_port || 22;
                const sshConnection = (sshHost && sshPort)
                ? `ssh -p ${sshPort} root@${sshHost} -L 8080:localhost:8080`
                : 'N/A';

                // Find the already-rendered card
                const card = document.querySelector(`[data-instance-id="${instanceId}"]`);
                if (card) {
                const hostEl = card.querySelector('[data-field="ssh_host"]');
                const portEl = card.querySelector('[data-field="ssh_port"]');
                const statEl = card.querySelector('[data-field="status"]');
                const locEl  = card.querySelector('[data-field="geolocation"]');

                if (hostEl) hostEl.textContent = sshHost || 'N/A';
                if (portEl) portEl.textContent = sshPort || 'N/A';
                if (statEl) {
                    const state = inst.cur_state || 'Unknown';
                    statEl.textContent = state;
                    statEl.className = `instance-status ${String(state).toLowerCase()}`;
                }
                if (locEl) locEl.textContent = inst.geolocation || 'N/A';

                const actions = card.querySelector('.instance-actions');
                if (actions) {
                    if (sshHost && sshPort && String(inst.cur_state).toLowerCase() === 'running') {
                    actions.innerHTML = `
                        <button class="use-instance-btn" onclick="useInstance('${sshConnection}')">
                        📋 Use This Instance
                        </button>
                        <button class="use-instance-btn" onclick="resolveInstanceParams(${instanceId})">
                        🔄 Refresh details
                        </button>
                    `;
                    } else {
                    actions.innerHTML = `
                        <button class="use-instance-btn" onclick="resolveInstanceParams(${instanceId})">
                        🔄 Refresh details
                        </button>
                    `;
                    }
                }
                }

                showSetupResult(`Instance #${instanceId} details refreshed.`, 'success');
                return inst;
            } catch (err) {
                showSetupResult(`Failed to refresh instance #${instanceId}: ${err.message}`, 'error');
                throw err;
            }
            }

        </script>
    </body>
    </html>
    """
    return html

@app.route('/sync/forge', methods=['POST', 'OPTIONS'])
def sync_forge():
    """Sync from Forge (Stable Diffusion WebUI Forge)"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    # Get cleanup setting from request body, default to True
    cleanup = True
    if request.is_json:
        data = request.get_json()
        cleanup = data.get('cleanup', True) if data else True
    
    result = run_sync(FORGE_HOST, FORGE_PORT, "Forge", cleanup=cleanup)
    return jsonify(result)

@app.route('/sync/comfy', methods=['POST', 'OPTIONS'])
def sync_comfy():
    """Sync from ComfyUI"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    # Get cleanup setting from request body, default to True
    cleanup = True
    if request.is_json:
        data = request.get_json()
        cleanup = data.get('cleanup', True) if data else True
    
    result = run_sync(COMFY_HOST, COMFY_PORT, "ComfyUI", cleanup=cleanup)
    return jsonify(result)

@app.route('/sync/vastai', methods=['POST', 'OPTIONS'])
def sync_vastai():
    """Sync from VastAI (auto-discover running instance)"""
    if request.method == 'OPTIONS':
        return ("", 204)
    try:
        # Initialize VastManager to find running instance
        vast_manager = VastManager()
        running_instance = vast_manager.get_running_instance()
        
        if not running_instance:
            return jsonify({
                'success': False,
                'message': 'No running VastAI instance found'
            })
        
        # Extract SSH connection details
        ssh_host = running_instance.get('ssh_host')
        ssh_port = str(running_instance.get('ssh_port', 22))
        
        if not ssh_host:
            return jsonify({
                'success': False,
                'message': 'Running VastAI instance found but no SSH host available'
            })
        
        logger.info(f"Found running VastAI instance: {ssh_host}:{ssh_port}")
        
        # Get cleanup setting from request body, default to True
        cleanup = True
        if request.is_json:
            data = request.get_json()
            cleanup = data.get('cleanup', True) if data else True
        
        result = run_sync(ssh_host, ssh_port, "VastAI", cleanup=cleanup)
        
        # Add instance details to the result
        instance_info = {
            'id': running_instance.get('id'),
            'gpu': running_instance.get('gpu_name'),
            'host': ssh_host,
            'port': ssh_port
        }
        
        if result['success']:
            result['instance_info'] = instance_info
        
        return jsonify(result)
        
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'message': 'VastAI configuration files not found (config.yaml or api_key.txt)'
        })
    except Exception as e:
        logger.error(f"VastAI sync error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'VastAI sync error: {str(e)}'
        })

@app.route('/sync/vastai-connection', methods=['POST', 'OPTIONS'])
def sync_vastai_connection():
    """Sync from VastAI using specific SSH connection string"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        # Get request data
        data = request.get_json()
        if not data or 'ssh_connection' not in data:
            return jsonify({
                'success': False,
                'message': 'SSH connection string is required'
            }), 400
        
        ssh_connection = data['ssh_connection'].strip()
        cleanup = data.get('cleanup', True)
        
        # Parse SSH connection string
        ssh_parts = parse_ssh_connection(ssh_connection)
        if not ssh_parts:
            return jsonify({
                'success': False,
                'message': 'Invalid SSH connection string format. Expected format: ssh -p PORT user@host [additional options]'
            }), 400
        
        ssh_host = ssh_parts['host']
        ssh_port = str(ssh_parts['port'])
        
        logger.info(f"Starting VastAI sync from connection string: {ssh_host}:{ssh_port}")
        
        # Use the existing run_sync function
        result = run_sync(ssh_host, ssh_port, "VastAI-Connection", cleanup=cleanup)
        
        # Add connection details to the result
        connection_info = {
            'host': ssh_host,
            'port': ssh_port,
            'user': ssh_parts['user']
        }
        
        if result['success']:
            result['connection_info'] = connection_info
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"VastAI connection sync error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'VastAI connection sync error: {str(e)}'
        })

@app.route('/test/ssh', methods=['POST', 'OPTIONS'])
def test_ssh():
    """Test SSH connectivity to configured hosts"""
    if request.method == 'OPTIONS':
        return ("", 204)
    try:
        if SSHTester is None:
            return jsonify({
                'success': False,
                'message': 'SSH test functionality not available'
            })
        
        logger.info("Starting SSH connectivity tests")
        tester = SSHTester()
        
        # Test all default hosts
        results = tester.test_all_hosts(timeout=10)
        
        # Format response
        response = {
            'success': True,
            'message': 'SSH connectivity test completed',
            'summary': results['summary'],
            'results': results['results']
        }
        
        # Log results
        logger.info(f"SSH test summary: {results['summary']}")
        for host, result in results['results'].items():
            status = "PASS" if result['success'] else "FAIL"
            logger.info(f"SSH test {host}: {status} - {result['message']}")
        
        return jsonify(response)
        
    except FileNotFoundError as e:
        logger.error(f"SSH configuration error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'SSH configuration files not found',
            'error': str(e)
        })
    except Exception as e:
        logger.error(f"SSH test error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'SSH test error: {str(e)}',
            'error': str(e)
        })

@app.route('/sync/progress/<sync_id>')
def get_sync_progress(sync_id):
    """Get progress of a sync operation"""
    try:
        progress_file = f"/tmp/sync_progress_{sync_id}.json"
        
        if not os.path.exists(progress_file):
            return jsonify({
                'success': False,
                'message': 'Progress file not found',
                'sync_id': sync_id
            }), 404
        
        with open(progress_file, 'r') as f:
            progress_data = json.load(f)
        
        return jsonify({
            'success': True,
            'progress': progress_data
        })
        
    except json.JSONDecodeError:
        return jsonify({
            'success': False,
            'message': 'Invalid progress data',
            'sync_id': sync_id
        }), 500
    except Exception as e:
        logger.error(f"Error reading progress for {sync_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error reading progress: {str(e)}',
            'sync_id': sync_id
        }), 500

@app.route('/logs/manifest', methods=['GET', 'OPTIONS'])
def get_logs_manifest():
    """Get manifest of available sync log files"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        ensure_sync_log_dir()
        
        # Get all log files sorted by modification time (newest first)
        log_pattern = os.path.join(SYNC_LOG_DIR, 'sync_log_*.json')
        log_files = sorted(glob.glob(log_pattern), key=os.path.getmtime, reverse=True)
        
        manifest = []
        for log_file in log_files:
            try:
                # Read basic info from each log file
                with open(log_file, 'r') as f:
                    log_data = json.load(f)
                
                manifest.append({
                    'filename': os.path.basename(log_file),
                    'timestamp': log_data.get('timestamp'),
                    'sync_type': log_data.get('sync_type'),
                    'success': log_data.get('success', False),
                    'message': log_data.get('message', ''),
                    'duration_seconds': log_data.get('duration_seconds'),
                    'files_transferred': log_data.get('files_transferred', 0),
                    'folders_synced': log_data.get('folders_synced', 0),
                    'bytes_transferred': log_data.get('bytes_transferred', 0)
                })
            except Exception as e:
                logger.warning(f"Failed to read log file {log_file}: {str(e)}")
                continue
        
        return jsonify({
            'success': True,
            'logs': manifest
        })
        
    except Exception as e:
        logger.error(f"Failed to get logs manifest: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to get logs manifest: {str(e)}'
        }), 500

@app.route('/logs/<filename>', methods=['GET', 'OPTIONS'])
def get_log_file(filename):
    """Get contents of a specific log file"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        # Validate filename format for security
        if not filename.startswith('sync_log_') or not filename.endswith('.json'):
            return jsonify({
                'success': False,
                'message': 'Invalid log filename format'
            }), 400
        
        log_path = os.path.join(SYNC_LOG_DIR, filename)
        
        if not os.path.exists(log_path):
            return jsonify({
                'success': False,
                'message': 'Log file not found'
            }), 404
        
        # Security check - ensure file is within sync log directory
        if not os.path.abspath(log_path).startswith(os.path.abspath(SYNC_LOG_DIR)):
            return jsonify({
                'success': False,
                'message': 'Invalid log file path'
            }), 400
        
        with open(log_path, 'r') as f:
            log_data = json.load(f)
        
        return jsonify({
            'success': True,
            'log': log_data
        })
        
    except json.JSONDecodeError:
        return jsonify({
            'success': False,
            'message': 'Invalid log file format'
        }), 500
    except Exception as e:
        logger.error(f"Failed to read log file {filename}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to read log file: {str(e)}'
        }), 500

@app.route('/status')
def status():
    """Get status of available sync targets"""
    try:
        vast_manager = VastManager()
        running_instance = vast_manager.get_running_instance()
        vastai_status = {
            'available': running_instance is not None,
            'instance': running_instance
        }
    except:
        vastai_status = {
            'available': False,
            'error': 'VastAI configuration error'
        }
    
    return jsonify({
        'forge': {
            'available': True,
            'host': FORGE_HOST,
            'port': FORGE_PORT
        },
        'comfy': {
            'available': True,
            'host': COMFY_HOST,
            'port': COMFY_PORT
        },
        'vastai': vastai_status
    })

# --- add with the other imports ---
import glob as _glob  # avoid shadowing
from datetime import datetime as _dt

# --- helper: load json safely ---
def _load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None

# --- helper: pick latest, preferring running/starting ---
def _find_latest_progress():
    files = sorted(_glob.glob("/tmp/sync_progress_*.json"), key=os.path.getmtime, reverse=True)
    if not files:
        return None, None
    # prefer first file whose status != completed/error
    for fp in files:
        data = _load_json(fp)
        if data and data.get("status") not in ("completed", "error"):
            return os.path.basename(fp)[len("sync_progress_"):-5], data
    # otherwise return newest by mtime
    newest = files[0]
    return os.path.basename(newest)[len("sync_progress_"):-5], _load_json(newest)

@app.route("/sync/latest")
def sync_latest():
    """Return the most recent (prefer running) sync progress + id"""
    sync_id, data = _find_latest_progress()
    if not sync_id or not data:
        return jsonify({"success": False, "message": "No progress files found"}), 404
    return jsonify({"success": True, "sync_id": sync_id, "progress": data})

@app.route("/sync/active")
def sync_active():
    """List all known progress files with brief status for debugging/menus"""
    out = []
    for fp in sorted(_glob.glob("/tmp/sync_progress_*.json"), key=os.path.getmtime, reverse=True):
        data = _load_json(fp) or {}
        out.append({
            "sync_id": os.path.basename(fp)[len("sync_progress_"):-5],
            "status": data.get("status"),
            "progress_percent": data.get("progress_percent"),
            "last_update": data.get("last_update"),
        })
    return jsonify({"success": True, "items": out})

# VastAI Setup API endpoints
@app.route('/vastai/set-ui-home', methods=['POST', 'OPTIONS'])
def set_ui_home():
    """Set UI_HOME environment variable on VastAI instance"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json()
        if not data or 'ssh_connection' not in data or 'ui_home' not in data:
            return jsonify({
                'success': False,
                'message': 'SSH connection string and UI_HOME path are required'
            }), 400
        
        ssh_connection = data['ssh_connection'].strip()
        ui_home = data['ui_home'].strip()
        
        # Parse SSH connection string to extract host, port, and user
        ssh_parts = parse_ssh_connection(ssh_connection)
        if not ssh_parts:
            return jsonify({
                'success': False,
                'message': 'Invalid SSH connection string format'
            }), 400
        
        # Build SSH command to set UI_HOME
        ssh_cmd = [
            'ssh', 
            '-p', str(ssh_parts['port']), 
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=no',
            f"{ssh_parts['user']}@{ssh_parts['host']}"
        ]
        
        # Command to set UI_HOME in the environment
        remote_cmd = f'echo "export UI_HOME={ui_home}" >> ~/.bashrc && echo "UI_HOME={ui_home}" >> /etc/environment'
        ssh_cmd.append(remote_cmd)
        
        logger.info(f"Setting UI_HOME to {ui_home} on {ssh_parts['host']}:{ssh_parts['port']}")
        
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': f'UI_HOME set to {ui_home} successfully'
            })
        else:
            error_msg = result.stderr.strip() if result.stderr else 'Unknown SSH error'
            return jsonify({
                'success': False,
                'message': f'Failed to set UI_HOME: {error_msg}'
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'message': 'SSH connection timed out'
        })
    except Exception as e:
        logger.error(f"Error setting UI_HOME: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error setting UI_HOME: {str(e)}'
        })

@app.route('/vastai/get-ui-home', methods=['POST', 'OPTIONS'])
def get_ui_home():
    """Get UI_HOME environment variable from VastAI instance"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json()
        if not data or 'ssh_connection' not in data:
            return jsonify({
                'success': False,
                'message': 'SSH connection string is required'
            }), 400
        
        ssh_connection = data['ssh_connection'].strip()
        
        # Parse SSH connection string
        ssh_parts = parse_ssh_connection(ssh_connection)
        if not ssh_parts:
            return jsonify({
                'success': False,
                'message': 'Invalid SSH connection string format'
            }), 400
        
        # Build SSH command to get UI_HOME
        ssh_cmd = [
            'ssh', 
            '-p', str(ssh_parts['port']), 
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=no',
            f"{ssh_parts['user']}@{ssh_parts['host']}"
        ]
        
        # Command to get UI_HOME from environment
        remote_cmd = 'source /etc/environment 2>/dev/null || true; source ~/.bashrc 2>/dev/null || true; echo "UI_HOME=${UI_HOME:-not set}"'
        ssh_cmd.append(remote_cmd)
        
        logger.info(f"Reading UI_HOME from {ssh_parts['host']}:{ssh_parts['port']}")
        
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            output = result.stdout.strip()
            return jsonify({
                'success': True,
                'ui_home': output,
                'message': f'UI_HOME retrieved successfully'
            })
        else:
            error_msg = result.stderr.strip() if result.stderr else 'Unknown SSH error'
            return jsonify({
                'success': False,
                'message': f'Failed to read UI_HOME: {error_msg}'
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'message': 'SSH connection timed out'
        })
    except Exception as e:
        logger.error(f"Error reading UI_HOME: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error reading UI_HOME: {str(e)}'
        })

@app.route('/vastai/terminate-connection', methods=['POST', 'OPTIONS'])
def terminate_connection():
    """Terminate SSH connection to VastAI instance"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json()
        if not data or 'ssh_connection' not in data:
            return jsonify({
                'success': False,
                'message': 'SSH connection string is required'
            }), 400
        
        ssh_connection = data['ssh_connection'].strip()
        
        # Parse SSH connection string
        ssh_parts = parse_ssh_connection(ssh_connection)
        if not ssh_parts:
            return jsonify({
                'success': False,
                'message': 'Invalid SSH connection string format'
            }), 400
        
        logger.info(f"Terminating connections to {ssh_parts['host']}:{ssh_parts['port']}")
        
        # Find and kill SSH processes to this host/port
        try:
            # Use pkill to find and terminate SSH connections
            pkill_cmd = ['pkill', '-f', f"ssh.*{ssh_parts['host']}.*{ssh_parts['port']}"]
            result = subprocess.run(pkill_cmd, capture_output=True, text=True, timeout=10)
            
            # Also try to find processes with the user@host pattern
            pkill_cmd2 = ['pkill', '-f', f"ssh.*{ssh_parts['user']}@{ssh_parts['host']}"]
            result2 = subprocess.run(pkill_cmd2, capture_output=True, text=True, timeout=10)
            
            return jsonify({
                'success': True,
                'message': 'SSH connections terminated successfully'
            })
            
        except subprocess.TimeoutExpired:
            return jsonify({
                'success': False,
                'message': 'Timeout while terminating connections'
            })
        except Exception as e:
            return jsonify({
                'success': True,  # Still report success as the command ran
                'message': 'Termination command executed (no active connections found)'
            })
            
    except Exception as e:
        logger.error(f"Error terminating connection: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error terminating connection: {str(e)}'
        })

@app.route('/vastai/instances', methods=['GET', 'OPTIONS'])
def get_vastai_instances():
    """Get list of active VastAI instances"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        # Initialize VastManager to get instances
        vast_manager = VastManager()
        instances = vast_manager.list_instances()
        
        # Format instances for display
        formatted_instances = []
        for instance in instances:
            formatted_instances.append({
                'id': instance.get('id'),
                'status': instance.get('cur_state'),
                'gpu': instance.get('gpu_name'),
                'gpu_count': instance.get('num_gpus'),
                'gpu_ram_gb': round(instance.get('gpu_ram', 0) / 1024, 1) if instance.get('gpu_ram') else 0,
                'ssh_host': instance.get('ssh_host'),
                'ssh_port': instance.get('ssh_port'),
                'public_ip': instance.get('public_ipaddr'),
                'geolocation': instance.get('geolocation'),
                'template': instance.get('template_name'),
                'cost_per_hour': instance.get('dph_total')
            })
        
        return jsonify({
            'success': True,
            'instances': formatted_instances,
            'count': len(formatted_instances)
        })
        
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'message': 'VastAI configuration files not found (config.yaml or api_key.txt)'
        })
    except Exception as e:
        logger.error(f"Error getting VastAI instances: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting VastAI instances: {str(e)}'
        })

@app.route('/vastai/setup-civitdl', methods=['POST', 'OPTIONS'])
def setup_civitdl():
    """Install and configure CivitDL on VastAI instance"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json()
        if not data or 'ssh_connection' not in data:
            return jsonify({
                'success': False,
                'message': 'SSH connection string is required'
            }), 400
        
        ssh_connection = data['ssh_connection'].strip()
        
        # Parse SSH connection string
        ssh_parts = parse_ssh_connection(ssh_connection)
        if not ssh_parts:
            return jsonify({
                'success': False,
                'message': 'Invalid SSH connection string format'
            }), 400
        
        # Read CivitDL API key from file
        civitdl_api_key = read_api_key_from_file()
        if not civitdl_api_key:
            return jsonify({
                'success': False,
                'message': 'CivitDL API key not found in api_key.txt. Please ensure the file contains a line like "civitdl: your_api_key"'
            }), 400
        
        logger.info(f"Setting up CivitDL on {ssh_parts['host']}:{ssh_parts['port']}")
        
        # Build SSH command base
        ssh_cmd_base = [
            'ssh', 
            '-p', str(ssh_parts['port']), 
            '-o', 'ConnectTimeout=30',
            '-o', 'StrictHostKeyChecking=no',
            f"{ssh_parts['user']}@{ssh_parts['host']}"
        ]
        
        all_output = []
        
        # Step 1: Install civitdl
        all_output.append("=== Installing CivitDL ===")
        install_cmd = ssh_cmd_base + ['pip3 install civitdl']
        
        result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            error_output = f"Install failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            all_output.append(error_output)
            return jsonify({
                'success': False,
                'message': 'Failed to install CivitDL',
                'output': '\n'.join(all_output)
            })
        
        all_output.append(f"Install output: {result.stdout}")
        if result.stderr:
            all_output.append(f"Install stderr: {result.stderr}")
        
        # Step 2: Configure civitdl with API key
        all_output.append("\n=== Configuring CivitDL ===")
        
        # Use expect or printf to automate the API key input
        config_script = f'''
echo "{civitdl_api_key}" | civitconfig default --api-key
'''
        
        config_cmd = ssh_cmd_base + [f'bash -c "{config_script}"']
        
        result = subprocess.run(config_cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            error_output = f"Configuration failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            all_output.append(error_output)
            return jsonify({
                'success': False,
                'message': 'Failed to configure CivitDL',
                'output': '\n'.join(all_output)
            })
        
        all_output.append(f"Config output: {result.stdout}")
        if result.stderr:
            all_output.append(f"Config stderr: {result.stderr}")
        
        # Step 3: Verify installation
        all_output.append("\n=== Verifying Installation ===")
        verify_cmd = ssh_cmd_base + ['civitconfig list']
        
        result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            all_output.append(f"Verification output: {result.stdout}")
            all_output.append("\nCivitDL setup completed successfully!")
        else:
            all_output.append(f"Verification warning: {result.stderr}")
            all_output.append("CivitDL installed but verification had issues.")
        
        return jsonify({
            'success': True,
            'message': 'CivitDL setup completed successfully',
            'output': '\n'.join(all_output)
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'message': 'SSH command timed out during CivitDL setup'
        })
    except Exception as e:
        logger.error(f"Error setting up CivitDL: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error setting up CivitDL: {str(e)}'
        })

@app.route('/vastai/instances/<int:instance_id>', methods=['GET', 'OPTIONS'])
def get_vastai_instance_detail(instance_id):
    if request.method == 'OPTIONS':
        return ("", 204)
    try:
        vast_key = load_vast_api_key_from_file()
        url = f"https://console.vast.ai/api/v0/instances/{instance_id}/"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {vast_key}",
        }
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        data = r.json()
        instance = data.get("instances", {}) or {}
        return jsonify({"success": True, "instance": instance})
    except Exception as e:
        logger.error(f"Error fetching instance {instance_id}: {str(e)}")
        return jsonify({"success": False, "message": f"{e}"}), 500

def parse_ssh_connection(ssh_connection):
    """Parse SSH connection string to extract host, port, and user"""
    try:
        # Handle format like: ssh -p 2838 root@104.189.178.116 -L 8080:localhost:8080
        import re
        
        # Extract port from -p flag
        port_match = re.search(r'-p\s+(\d+)', ssh_connection)
        port = int(port_match.group(1)) if port_match else 22
        
        # Extract user@host
        user_host_match = re.search(r'(\w+)@([0-9.]+|[\w.-]+)', ssh_connection)
        if not user_host_match:
            return None
            
        user = user_host_match.group(1)
        host = user_host_match.group(2)
        
        return {
            'user': user,
            'host': host,
            'port': port
        }
        
    except Exception as e:
        logger.error(f"Error parsing SSH connection string: {str(e)}")
        return None

def read_api_key_from_file():
    """Read CivitDL API key from api_key.txt file"""
    try:
        api_key_path = os.path.join(os.path.dirname(__file__), '..', '..', 'api_key.txt')
        if not os.path.exists(api_key_path):
            logger.warning(f"API key file not found at {api_key_path}")
            return None
        
        with open(api_key_path, 'r') as f:
            content = f.read().strip()
        
        # Parse file content to find civitdl API key
        # Expected format: "civitdl: api_key_abcdef"
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('civitdl:'):
                # Extract the key after "civitdl:"
                key = line.split(':', 1)[1].strip()
                logger.info("Found CivitDL API key in api_key.txt")
                return key
        
        logger.warning("CivitDL API key not found in api_key.txt")
        return None
        
    except Exception as e:
        logger.error(f"Error reading API key file: {str(e)}")
        return None

def load_vast_api_key_from_file():
    """Read VastAI API key from ../../api_key.txt (line 'vastai: <key>')"""
    api_key_path = os.path.join(os.path.dirname(__file__), '..', '..', 'api_key.txt')
    with open(api_key_path, 'r') as f:
        for line in f:
            s = line.strip()
            if s.startswith('vastai:'):
                return s.split(':', 1)[1].strip()
    raise FileNotFoundError(f"VastAI key not found in {api_key_path}")


if __name__ == '__main__':
    # Check if sync script exists
    if not os.path.exists(SYNC_SCRIPT_PATH):
        logger.error(f"Sync script not found at {SYNC_SCRIPT_PATH}")
        exit(1)
    
    logger.info("Starting Media Sync API Server")
    app.run(host='0.0.0.0', port=5000, debug=False)
