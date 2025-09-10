#!/usr/bin/env python3
"""
Media Sync API Server
Provides web API endpoints for syncing media from local Docker containers and VastAI instances.
"""

import os
import subprocess
import logging
import uuid
import json
import glob
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

# Import SSH identity manager
try:
    from .ssh_manager import SSHIdentityManager
except ImportError:
    try:
        from ssh_manager import SSHIdentityManager
    except ImportError:
        SSHIdentityManager = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- CORS setup (allow Obsidian + local HTTP origins) ---
ALLOWED_ORIGINS = [
    "app://obsidian.md",
    "http://10.0.78.66",  # your NAS/API base used in Obsidian
    "http://localhost",
    "http://127.0.0.1",
]
CORS(
    app,
    resources={
        r"/sync/*": {"origins": ALLOWED_ORIGINS},
        r"/status": {"origins": ALLOWED_ORIGINS},
        r"/test/*": {"origins": ALLOWED_ORIGINS},
        r"/ssh/*": {"origins": ALLOWED_ORIGINS},
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

def parse_sync_stats(output):
    """Parse sync statistics from script output"""
    stats = {
        'files_transferred': 0,
        'folders_synced': 0,
        'bytes_transferred': 0
    }
    
    if not output:
        return stats
    
    # Look for the summary line format: "SYNC_SUMMARY: Files transferred: X, Folders synced: Y, Data transferred: Z bytes"
    for line in output.split('\n'):
        if 'SYNC_SUMMARY:' in line:
            try:
                # Extract numbers from the summary line
                import re
                files_match = re.search(r'Files transferred:\s*(\d+)', line)
                folders_match = re.search(r'Folders synced:\s*(\d+)', line)
                bytes_match = re.search(r'Data transferred:\s*(\d+)', line)
                
                if files_match:
                    stats['files_transferred'] = int(files_match.group(1))
                if folders_match:
                    stats['folders_synced'] = int(folders_match.group(1))
                if bytes_match:
                    stats['bytes_transferred'] = int(bytes_match.group(1))
                    
                break
            except (ValueError, AttributeError):
                # If parsing fails, keep defaults
                pass
    
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
            # NEW:
            "cleanup": result.get('cleanup', None),
            "cmd": result.get('cmd', None),
            # File transfer statistics
            "files_transferred": sync_stats['files_transferred'],
            "folders_synced": sync_stats['folders_synced'],
            "bytes_transferred": sync_stats['bytes_transferred'],
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

        # Pre-validate SSH setup if SSH manager is available
        if SSHIdentityManager is not None:
            ssh_manager = SSHIdentityManager()
            ssh_status = ssh_manager.get_ssh_status()
            
            if not ssh_status['ready_for_sync']:
                logger.warning(f"SSH not ready for sync: {ssh_status}")
                # Attempt to set up SSH automatically
                setup_result = ssh_manager.setup_ssh_agent()
                if not setup_result['success']:
                    end_time = datetime.now()
                    sync_result = {
                        'success': False,
                        'message': f'{sync_type} sync failed: SSH setup required',
                        'error': f"SSH setup failed: {setup_result['message']}",
                        'ssh_setup_required': True,
                        'requires_user_confirmation': setup_result.get('requires_user_confirmation', False),
                        'cleanup': bool(cleanup),
                        'sync_id': sync_id,
                    }
                    save_sync_log(sync_type, sync_result, start_time, end_time)
                    return sync_result

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

        if result.returncode == 0:
            logger.info(f"{sync_type} sync completed successfully")
            # Parse sync statistics for summary
            sync_stats = parse_sync_stats(result.stdout)
            
            sync_result = {
                **base,
                'success': True,
                'message': f'{sync_type} sync completed successfully',
                'output': result.stdout,
                # Add condensed summary for UI display
                'summary': {
                    'files_transferred': sync_stats['files_transferred'],
                    'folders_synced': sync_stats['folders_synced'],
                    'bytes_transferred': sync_stats['bytes_transferred'],
                    'cleanup_enabled': bool(cleanup),
                    'duration_seconds': None  # Will be calculated and added later
                }
            }
        else:
            logger.error(f"{sync_type} sync failed with return code {result.returncode}")
            sync_result = {
                **base,
                'success': False,
                'message': f'{sync_type} sync failed',
                'error': result.stderr,
                'output': result.stdout,
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
    """Obsidian-inspired web interface for testing"""
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Media Sync Tool</title>
        <style>
            :root {
                /* Obsidian-inspired color scheme */
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
            
            /* SSH Status Panel */
            .ssh-status-panel {
                background: var(--background-secondary);
                border: 1px solid var(--background-modifier-border);
                border-radius: var(--radius-m);
                padding: var(--size-4-4);
                margin: var(--size-4-4) 0;
                box-shadow: 0 2px 8px var(--background-modifier-box-shadow);
            }
            
            .ssh-status-panel h3 {
                margin: 0 0 var(--size-4-3) 0;
                font-size: var(--font-ui-medium);
                font-weight: 600;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            
            .refresh-ssh-btn {
                background: var(--interactive-normal);
                color: var(--text-normal);
                border: none;
                border-radius: var(--radius-s);
                padding: var(--size-4-1) var(--size-4-3);
                font-size: var(--font-ui-small);
                cursor: pointer;
                transition: background 0.2s ease;
            }
            
            .refresh-ssh-btn:hover {
                background: var(--interactive-hover);
            }
            
            .ssh-status-content {
                margin-top: var(--size-4-3);
            }
            
            .ssh-status-loading {
                text-align: center;
                color: var(--text-muted);
                font-style: italic;
                padding: var(--size-4-3);
            }
            
            .ssh-status-item {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: var(--size-4-2);
                border-radius: var(--radius-s);
                margin-bottom: var(--size-4-1);
                background: var(--background-primary);
                border: 1px solid var(--background-modifier-border);
            }
            
            .ssh-status-item.success {
                border-left: 4px solid var(--text-success);
            }
            
            .ssh-status-item.warning {
                border-left: 4px solid var(--text-warning);
            }
            
            .ssh-status-item.error {
                border-left: 4px solid var(--text-error);
            }
            
            .ssh-status-label {
                font-size: var(--font-ui-small);
                color: var(--text-normal);
                font-weight: 500;
            }
            
            .ssh-status-value {
                font-size: var(--font-ui-small);
                color: var(--text-muted);
            }
            
            .ssh-setup-btn {
                background: var(--interactive-accent);
                color: var(--text-on-accent);
                border: none;
                border-radius: var(--radius-s);
                padding: var(--size-4-2) var(--size-4-4);
                font-size: var(--font-ui-small);
                cursor: pointer;
                transition: background 0.2s ease;
                margin-top: var(--size-4-2);
                width: 100%;
            }
            
            .ssh-setup-btn:hover {
                background: var(--interactive-accent-hover);
            }
            
            .ssh-confirmation-dialog {
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: rgba(0, 0, 0, 0.5);
                display: none;
                justify-content: center;
                align-items: center;
                z-index: 1001;
                backdrop-filter: blur(2px);
            }
            
            .ssh-confirmation-modal {
                background: var(--background-primary);
                border: 1px solid var(--background-modifier-border);
                border-radius: var(--radius-m);
                width: 90vw;
                max-width: 500px;
                box-shadow: 0 8px 32px var(--background-modifier-box-shadow);
                overflow: hidden;
            }
            
            .ssh-confirmation-header {
                padding: var(--size-4-4);
                border-bottom: 1px solid var(--background-modifier-border);
                background: var(--background-secondary);
            }
            
            .ssh-confirmation-title {
                font-size: var(--font-ui-medium);
                font-weight: 600;
                margin: 0;
                color: var(--text-normal);
                display: flex;
                align-items: center;
                gap: var(--size-4-2);
            }
            
            .ssh-confirmation-content {
                padding: var(--size-4-4);
            }
            
            .ssh-confirmation-message {
                margin-bottom: var(--size-4-4);
                color: var(--text-normal);
                line-height: 1.5;
            }
            
            .ssh-confirmation-details {
                background: var(--background-modifier-form-field);
                border: 1px solid var(--background-modifier-border);
                border-radius: var(--radius-s);
                padding: var(--size-4-3);
                margin-bottom: var(--size-4-4);
                font-size: var(--font-ui-small);
                color: var(--text-muted);
            }
            
            .ssh-confirmation-buttons {
                display: flex;
                gap: var(--size-4-2);
                justify-content: flex-end;
            }
            
            .ssh-confirmation-btn {
                padding: var(--size-4-2) var(--size-4-4);
                border: none;
                border-radius: var(--radius-s);
                font-size: var(--font-ui-small);
                cursor: pointer;
                transition: background 0.2s ease;
            }
            
            .ssh-confirmation-btn.primary {
                background: var(--interactive-accent);
                color: var(--text-on-accent);
            }
            
            .ssh-confirmation-btn.primary:hover {
                background: var(--interactive-accent-hover);
            }
            
            .ssh-confirmation-btn.secondary {
                background: var(--interactive-normal);
                color: var(--text-normal);
            }
            
            .ssh-confirmation-btn.secondary:hover {
                background: var(--interactive-hover);
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
            
            <!-- SSH Status Panel -->
            <div id="sshStatus" class="ssh-status-panel">
                <h3>
                    <span>🔐</span>
                    SSH Connection Status
                    <button class="refresh-ssh-btn" onclick="refreshSSHStatus()">🔄 Refresh</button>
                </h3>
                <div id="sshStatusContent" class="ssh-status-content">
                    <div class="ssh-status-loading">Click refresh to check SSH status</div>
                </div>
            </div>
            
            <div id="result" class="result-panel"></div>
            
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
        
        <!-- SSH confirmation dialog -->
        <div id="sshConfirmationDialog" class="ssh-confirmation-dialog">
            <div class="ssh-confirmation-modal">
                <div class="ssh-confirmation-header">
                    <h3 class="ssh-confirmation-title">
                        <span>🔐</span>
                        SSH Identity Setup Required
                    </h3>
                </div>
                <div class="ssh-confirmation-content">
                    <div id="sshConfirmationMessage" class="ssh-confirmation-message">
                        Do you want to set up SSH identity for media sync? This will enable secure connections to your sync targets.
                    </div>
                    <div id="sshConfirmationDetails" class="ssh-confirmation-details">
                        <!-- Details will be populated by JavaScript -->
                    </div>
                    <div class="ssh-confirmation-buttons">
                        <button class="ssh-confirmation-btn secondary" onclick="cancelSSHSetup()">Cancel</button>
                        <button class="ssh-confirmation-btn primary" onclick="confirmSSHSetup()">Yes, Set Up SSH</button>
                    </div>
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
            // SSH Management Functions
            async function refreshSSHStatus() {
                const statusContent = document.getElementById('sshStatusContent');
                const refreshBtn = document.querySelector('.refresh-ssh-btn');
                
                // Show loading state
                refreshBtn.textContent = '⟳ Loading...';
                refreshBtn.disabled = true;
                statusContent.innerHTML = '<div class="ssh-status-loading">Checking SSH status...</div>';
                
                try {
                    const response = await fetch('/ssh/status');
                    const data = await response.json();
                    
                    if (data.success) {
                        displaySSHStatus(data.status);
                    } else {
                        statusContent.innerHTML = '<div class="ssh-status-loading">Failed to load SSH status: ' + data.message + '</div>';
                    }
                } catch (error) {
                    statusContent.innerHTML = '<div class="ssh-status-loading">Failed to load SSH status: ' + error.message + '</div>';
                } finally {
                    refreshBtn.textContent = '🔄 Refresh';
                    refreshBtn.disabled = false;
                }
            }
            
            function displaySSHStatus(status) {
                const statusContent = document.getElementById('sshStatusContent');
                let html = '';
                
                // Overall readiness
                const readyClass = status.ready_for_sync ? 'success' : 'error';
                const readyIcon = status.ready_for_sync ? '✅' : '❌';
                const readyText = status.ready_for_sync ? 'Ready for sync' : 'Setup required';
                
                html += `<div class="ssh-status-item ${readyClass}">
                    <span class="ssh-status-label">${readyIcon} Overall Status</span>
                    <span class="ssh-status-value">${readyText}</span>
                </div>`;
                
                // Individual status items
                const validation = status.validation;
                
                // SSH key
                const keyClass = validation.ssh_key_exists && validation.ssh_key_readable ? 'success' : 'error';
                const keyIcon = validation.ssh_key_exists && validation.ssh_key_readable ? '✅' : '❌';
                const keyText = validation.ssh_key_exists ? 
                    (validation.ssh_key_readable ? 'Available' : 'Not readable') : 'Not found';
                
                html += `<div class="ssh-status-item ${keyClass}">
                    <span class="ssh-status-label">${keyIcon} SSH Key</span>
                    <span class="ssh-status-value">${keyText}</span>
                </div>`;
                
                // SSH agent
                const agentClass = validation.ssh_agent_running ? 'success' : 'warning';
                const agentIcon = validation.ssh_agent_running ? '✅' : '⚠️';
                const agentText = validation.ssh_agent_running ? 'Running' : 'Not running';
                
                html += `<div class="ssh-status-item ${agentClass}">
                    <span class="ssh-status-label">${agentIcon} SSH Agent</span>
                    <span class="ssh-status-value">${agentText}</span>
                </div>`;
                
                // Identity loaded
                const identityClass = validation.identity_loaded ? 'success' : 'warning';
                const identityIcon = validation.identity_loaded ? '✅' : '⚠️';
                const identityText = validation.identity_loaded ? 'Loaded' : 'Not loaded';
                
                html += `<div class="ssh-status-item ${identityClass}">
                    <span class="ssh-status-label">${identityIcon} SSH Identity</span>
                    <span class="ssh-status-value">${identityText}</span>
                </div>`;
                
                // Permissions
                const permClass = validation.permissions_ok ? 'success' : 'warning';
                const permIcon = validation.permissions_ok ? '✅' : '⚠️';
                const permText = validation.permissions_ok ? 'Correct' : 'Needs fixing';
                
                html += `<div class="ssh-status-item ${permClass}">
                    <span class="ssh-status-label">${permIcon} Permissions</span>
                    <span class="ssh-status-value">${permText}</span>
                </div>`;
                
                // Add setup button if not ready
                if (!status.ready_for_sync) {
                    html += '<button class="ssh-setup-btn" onclick="setupSSH()">🔧 Set Up SSH</button>';
                }
                
                statusContent.innerHTML = html;
            }
            
            async function setupSSH(confirmed = false) {
                try {
                    const response = await fetch('/ssh/setup', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            confirmed: confirmed
                        })
                    });
                    const data = await response.json();
                    
                    if (data.requires_confirmation && !confirmed) {
                        // Show confirmation dialog
                        showSSHConfirmationDialog(data);
                    } else if (data.success) {
                        // Show success message
                        const resultDiv = document.getElementById('result');
                        resultDiv.className = 'result-panel success';
                        resultDiv.style.display = 'block';
                        
                        let message = `<h3>✅ ${data.message}</h3>`;
                        if (data.permissions_fixed && data.permissions_fixed.length > 0) {
                            message += '<p><strong>Permissions fixed:</strong><br>';
                            message += data.permissions_fixed.map(fix => `• ${fix}`).join('<br>');
                            message += '</p>';
                        }
                        
                        resultDiv.innerHTML = message;
                        
                        // Refresh SSH status
                        refreshSSHStatus();
                    } else {
                        // Show error
                        const resultDiv = document.getElementById('result');
                        resultDiv.className = 'result-panel error';
                        resultDiv.style.display = 'block';
                        resultDiv.innerHTML = `<h3>❌ SSH Setup Failed</h3><p>${data.message}</p>`;
                    }
                } catch (error) {
                    const resultDiv = document.getElementById('result');
                    resultDiv.className = 'result-panel error';
                    resultDiv.style.display = 'block';
                    resultDiv.innerHTML = `<h3>❌ SSH Setup Error</h3><p>${error.message}</p>`;
                }
            }
            
            function showSSHConfirmationDialog(data) {
                const dialog = document.getElementById('sshConfirmationDialog');
                const messageEl = document.getElementById('sshConfirmationMessage');
                const detailsEl = document.getElementById('sshConfirmationDetails');
                
                messageEl.textContent = data.confirmation_message || 'Do you want to set up SSH identity for media sync?';
                detailsEl.textContent = data.details || '';
                
                dialog.style.display = 'flex';
            }
            
            function confirmSSHSetup() {
                const dialog = document.getElementById('sshConfirmationDialog');
                dialog.style.display = 'none';
                setupSSH(true);
            }
            
            function cancelSSHSetup() {
                const dialog = document.getElementById('sshConfirmationDialog');
                dialog.style.display = 'none';
            }
            
            // Enhanced sync function with SSH validation
            async function sync(type) {
                const resultDiv = document.getElementById('result');
                const progressDiv = document.getElementById('progress');
                const progressBar = document.getElementById('progressBar');
                const progressText = document.getElementById('progressText');
                const progressDetails = document.getElementById('progressDetails');
                const cleanupCheckbox = document.getElementById('cleanupCheckbox');
                
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
                    
                    // Check if SSH setup is required
                    if (data.ssh_setup_required && data.requires_user_confirmation) {
                        progressDiv.style.display = 'none';
                        resultDiv.className = 'result-panel error';
                        resultDiv.innerHTML = `
                            <h3>🔐 SSH Setup Required</h3>
                            <p>${data.message}</p>
                            <p>Please set up SSH identity before syncing.</p>
                            <button class="ssh-setup-btn" onclick="setupSSH()" style="margin-top: 12px;">🔧 Set Up SSH Now</button>
                        `;
                        return;
                    }
                    
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
                            
                            resultDiv.innerHTML = `
                                <h3>✅ ${data.message}</h3>
                                <div style="margin-top: 12px;">
                                    <strong>Summary:</strong><br>
                                    📁 Folders synced: ${data.summary.folders_synced}<br>
                                    📄 Files transferred: ${data.summary.files_transferred}<br>
                                    💾 Data transferred: ${bytesFormatted}<br>
                                    ⏱️ Duration: ${duration}<br>
                                    🧹 Cleanup: ${cleanupStatus}
                                </div>
                            `;
                        } else {
                            // Fallback for older format
                            resultDiv.innerHTML = `<h3>✅ ${data.message}</h3><pre>${data.output || ''}</pre>`;
                        }
                    } else {
                        resultDiv.className = 'result-panel error';
                        resultDiv.innerHTML = `<h3>❌ ${data.message}</h3><pre>${data.error || data.output || ''}</pre>`;
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
                            output += `${status} ${host}: ${result.message}\n`;
                            if (!result.success && result.error) {
                                output += `    Error: ${result.error}\n`;
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
            
            // Logs functionality
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
                    
                    // Create log summary with file transfer info if available
                    const statusIcon = log.success ? '✅' : '❌';
                    const syncType = log.sync_type ? log.sync_type.charAt(0).toUpperCase() + log.sync_type.slice(1) : 'Unknown';
                    
                    // Add file transfer summary if available
                    let transferInfo = '';
                    if (log.files_transferred !== undefined || log.folders_synced !== undefined) {
                        const filesCount = log.files_transferred || 0;
                        const foldersCount = log.folders_synced || 0;
                        if (filesCount > 0 || foldersCount > 0) {
                            transferInfo = `<br>📄 ${filesCount} files, 📁 ${foldersCount} folders`;
                        }
                    }
                    
                    logItem.innerHTML = `
                        <div class="log-summary">
                            ${statusIcon} ${syncType} - ${formattedDate}, ${formattedTime}<br>
                            ${log.message} ${duration}${transferInfo}
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
                        
                        // Add file transfer statistics if available
                        if (log.files_transferred !== undefined) {
                            content += `Files transferred: ${log.files_transferred}\n`;
                        }
                        if (log.folders_synced !== undefined) {
                            content += `Folders synced: ${log.folders_synced}\n`;
                        }
                        if (log.bytes_transferred !== undefined && log.bytes_transferred > 0) {
                            // Format bytes using JavaScript
                            const bytesFormatted = formatBytes(log.bytes_transferred);
                            content += `Data transferred: ${bytesFormatted}\n`;
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
            
            // Close modal when clicking outside of it
            document.addEventListener('DOMContentLoaded', function() {
                const overlay = document.getElementById('logOverlay');
                overlay.addEventListener('click', function(e) {
                    if (e.target === overlay) {
                        closeLogModal();
                    }
                });
                
                // Close SSH confirmation dialog when clicking outside
                const sshDialog = document.getElementById('sshConfirmationDialog');
                sshDialog.addEventListener('click', function(e) {
                    if (e.target === sshDialog) {
                        cancelSSHSetup();
                    }
                });
            });
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

@app.route('/ssh/status', methods=['GET', 'OPTIONS'])
def get_ssh_status():
    """Get SSH setup status and validation"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        if SSHIdentityManager is None:
            return jsonify({
                'success': False,
                'message': 'SSH identity manager not available'
            }), 500
        
        ssh_manager = SSHIdentityManager()
        status = ssh_manager.get_ssh_status()
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Error getting SSH status: {e}")
        return jsonify({
            'success': False,
            'message': f'SSH status error: {str(e)}'
        }), 500

@app.route('/ssh/setup', methods=['POST', 'OPTIONS'])
def setup_ssh():
    """Setup SSH agent and add identity with user confirmation if needed"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        if SSHIdentityManager is None:
            return jsonify({
                'success': False,
                'message': 'SSH identity manager not available'
            }), 500
        
        # Get user confirmation if provided
        user_confirmed = False
        if request.is_json:
            data = request.get_json()
            user_confirmed = data.get('confirmed', False)
        
        ssh_manager = SSHIdentityManager()
        
        # First, ensure permissions are correct
        perm_result = ssh_manager.ensure_ssh_permissions()
        if not perm_result['success']:
            return jsonify({
                'success': False,
                'message': 'Failed to fix SSH permissions',
                'errors': perm_result['errors']
            }), 500
        
        # Setup SSH agent and identity
        setup_result = ssh_manager.setup_ssh_agent()
        
        if setup_result['requires_user_confirmation'] and not user_confirmed:
            # Return a response indicating user confirmation is needed
            return jsonify({
                'success': False,
                'requires_confirmation': True,
                'message': 'SSH key setup requires user confirmation',
                'confirmation_message': 'Do you want to add the SSH identity for media sync? This will enable secure connections to your sync targets.',
                'details': setup_result['message']
            }), 200
        
        if setup_result['success']:
            response = {
                'success': True,
                'message': setup_result['message'],
                'identity_added': setup_result['identity_added']
            }
            
            if perm_result['changes_made']:
                response['permissions_fixed'] = perm_result['changes_made']
            
            return jsonify(response)
        else:
            return jsonify({
                'success': False,
                'message': setup_result['message']
            }), 400
        
    except Exception as e:
        logger.error(f"Error setting up SSH: {e}")
        return jsonify({
            'success': False,
            'message': f'SSH setup error: {str(e)}'
        }), 500

@app.route('/ssh/test', methods=['POST', 'OPTIONS'])
def test_ssh_connection():
    """Test SSH connection to a specific host"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        if SSHIdentityManager is None:
            return jsonify({
                'success': False,
                'message': 'SSH identity manager not available'
            }), 500
        
        # Get connection parameters from request
        if not request.is_json:
            return jsonify({
                'success': False,
                'message': 'JSON request body required'
            }), 400
        
        data = request.get_json()
        host = data.get('host')
        port = data.get('port', 22)
        user = data.get('user', 'root')
        timeout = data.get('timeout', 10)
        
        if not host:
            return jsonify({
                'success': False,
                'message': 'Host parameter required'
            }), 400
        
        ssh_manager = SSHIdentityManager()
        test_result = ssh_manager.test_ssh_connection(host, port, user, timeout)
        
        return jsonify({
            'success': test_result['success'],
            'result': test_result
        })
        
    except Exception as e:
        logger.error(f"Error testing SSH connection: {e}")
        return jsonify({
            'success': False,
            'message': f'SSH test error: {str(e)}'
        }), 500

@app.route('/ssh/cleanup', methods=['POST', 'OPTIONS'])
def cleanup_ssh():
    """Clean up SSH agent"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        if SSHIdentityManager is None:
            return jsonify({
                'success': False,
                'message': 'SSH identity manager not available'
            }), 500
        
        ssh_manager = SSHIdentityManager()
        success = ssh_manager.cleanup_ssh_agent()
        
        return jsonify({
            'success': success,
            'message': 'SSH agent cleaned up' if success else 'Failed to clean up SSH agent'
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up SSH: {e}")
        return jsonify({
            'success': False,
            'message': f'SSH cleanup error: {str(e)}'
        }), 500

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
import glob
from datetime import datetime

# --- helper: load json safely ---
def _load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None

# --- helper: pick latest, preferring running/starting ---
def _find_latest_progress():
    files = sorted(glob.glob("/tmp/sync_progress_*.json"), key=os.path.getmtime, reverse=True)
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
    for fp in sorted(glob.glob("/tmp/sync_progress_*.json"), key=os.path.getmtime, reverse=True):
        data = _load_json(fp) or {}
        out.append({
            "sync_id": os.path.basename(fp)[len("sync_progress_"):-5],
            "status": data.get("status"),
            "progress_percent": data.get("progress_percent"),
            "last_update": data.get("last_update"),
        })
    return jsonify({"success": True, "items": out})


if __name__ == '__main__':
    # Check if sync script exists
    if not os.path.exists(SYNC_SCRIPT_PATH):
        logger.error(f"Sync script not found at {SYNC_SCRIPT_PATH}")
        exit(1)
    
    logger.info("Starting Media Sync API Server")
    app.run(host='0.0.0.0', port=5000, debug=False)
