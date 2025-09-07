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
from ..vastai.vast_manager import VastManager

# Import SSH test functionality
try:
    from .ssh_test import SSHTester
except ImportError:
    SSHTester = None

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

def save_sync_log(sync_type, result, start_time, end_time):
    """Save sync result to a timestamped JSON log file"""
    try:
        ensure_sync_log_dir()
        
        # Format: sync_log_yyyymmdd_hhmm.json
        timestamp = start_time.strftime("%Y%m%d_%H%M")
        log_filename = f"sync_log_{timestamp}.json"
        log_path = os.path.join(SYNC_LOG_DIR, log_filename)
        
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

        if result.returncode == 0:
            logger.info(f"{sync_type} sync completed successfully")
            sync_result = {
                **base,
                'success': True,
                'message': f'{sync_type} sync completed successfully',
                'output': result.stdout,
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
            
            /* Logs Panel Styles */
            .logs-panel {
                background: var(--background-secondary);
                border: 1px solid var(--background-modifier-border);
                border-radius: var(--radius-m);
                padding: var(--size-4-4);
                margin-top: var(--size-4-6);
                box-shadow: 0 2px 8px var(--background-modifier-box-shadow);
            }
            
            .logs-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: var(--size-4-4);
                gap: var(--size-4-4);
            }
            
            .logs-header h3 {
                margin: 0;
                font-size: var(--font-ui-medium);
                font-weight: 600;
                color: var(--text-normal);
                display: flex;
                align-items: center;
                gap: var(--size-4-2);
            }
            
            .logs-header .sync-button {
                min-height: auto;
                padding: var(--size-4-2) var(--size-4-3);
                font-size: var(--font-ui-small);
            }
            
            .logs-loading {
                text-align: center;
                color: var(--text-muted);
                font-style: italic;
                padding: var(--size-4-4);
            }
            
            .logs-list {
                max-height: 300px;
                overflow-y: auto;
            }
            
            .log-item {
                background: var(--background-modifier-form-field);
                border: 1px solid var(--background-modifier-border);
                border-radius: var(--radius-s);
                padding: var(--size-4-3);
                margin-bottom: var(--size-4-2);
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .log-item:hover {
                background: var(--interactive-hover);
                border-color: var(--interactive-accent);
                transform: translateY(-1px);
                box-shadow: 0 2px 4px var(--background-modifier-box-shadow);
            }
            
            .log-item:active {
                transform: translateY(0);
            }
            
            .log-item-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: var(--size-4-2);
                margin-bottom: var(--size-4-1);
            }
            
            .log-item-title {
                font-weight: 600;
                color: var(--text-normal);
                font-size: var(--font-ui-medium);
                display: flex;
                align-items: center;
                gap: var(--size-4-1);
            }
            
            .log-item-timestamp {
                font-size: var(--font-ui-smaller);
                color: var(--text-muted);
            }
            
            .log-item-details {
                font-size: var(--font-ui-small);
                color: var(--text-muted);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .log-details {
                background: var(--background-primary);
                border: 2px solid var(--interactive-accent);
                border-radius: var(--radius-m);
                margin-top: var(--size-4-4);
                box-shadow: 0 4px 12px var(--background-modifier-box-shadow);
                max-height: 400px;
                overflow-y: auto;
            }
            
            .log-details-header {
                background: var(--background-secondary-alt);
                padding: var(--size-4-3);
                border-bottom: 1px solid var(--background-modifier-border);
                display: flex;
                justify-content: flex-end;
                border-radius: var(--radius-m) var(--radius-m) 0 0;
            }
            
            .close-button {
                background: var(--text-error);
                color: var(--text-on-accent);
                border: none;
                border-radius: var(--radius-s);
                padding: var(--size-4-1) var(--size-4-2);
                font-size: var(--font-ui-smaller);
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .close-button:hover {
                background: #e53e3e;
                transform: translateY(-1px);
            }
            
            .log-details-content {
                padding: var(--size-4-4);
            }
            
            .log-details-content h4 {
                margin: 0 0 var(--size-4-3) 0;
                font-size: var(--font-ui-medium);
                font-weight: 600;
                color: var(--text-normal);
                display: flex;
                align-items: center;
                gap: var(--size-4-1);
            }
            
            .log-details-section {
                margin-bottom: var(--size-4-3);
            }
            
            .log-details-section strong {
                color: var(--text-normal);
                font-weight: 600;
            }
            
            .log-details-section pre {
                background: var(--background-secondary);
                border: 1px solid var(--background-modifier-border);
                border-radius: var(--radius-s);
                padding: var(--size-4-3);
                margin: var(--size-4-2) 0 0 0;
                overflow-x: auto;
                font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
                font-size: var(--font-ui-small);
                white-space: pre-wrap;
                max-height: 150px;
                overflow-y: auto;
            }
            
            .log-details-section.error pre {
                background: var(--background-error);
                border-color: var(--text-error);
                color: var(--text-error);
            }
            
            .log-details-meta {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: var(--size-4-2);
                margin-bottom: var(--size-4-3);
                font-size: var(--font-ui-small);
            }
            
            .log-details-meta-item {
                display: flex;
                flex-direction: column;
                gap: var(--size-4-1);
            }
            
            .log-details-meta-label {
                font-weight: 600;
                color: var(--text-normal);
            }
            
            .log-details-meta-value {
                color: var(--text-muted);
                font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
                word-break: break-all;
            }
            
            .empty-logs {
                text-align: center;
                color: var(--text-muted);
                font-style: italic;
                padding: var(--size-4-6);
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
            
            <div id="result" class="result-panel"></div>
            
            <div id="progress" class="progress-panel">
                <h3>Sync Progress</h3>
                <div class="progress-bar">
                    <div id="progressBar" class="progress-fill"></div>
                </div>
                <div id="progressText" class="progress-text">Initializing...</div>
                <div id="progressDetails" class="progress-text"></div>
            </div>
            
            <!-- Logs Panel -->
            <div class="logs-panel">
                <div class="logs-header">
                    <h3>
                        <span>📋</span>
                        Sync Logs
                    </h3>
                    <button id="refreshLogsBtn" class="sync-button secondary">
                        <span>🔄</span>
                        Refresh
                    </button>
                </div>
                <div id="logsLoading" class="logs-loading">Loading logs...</div>
                <div id="logsList" class="logs-list" style="display: none;"></div>
                <div id="logDetails" class="log-details" style="display: none;">
                    <div class="log-details-header">
                        <button id="closeLogBtn" class="close-button">✕ Close</button>
                    </div>
                    <div id="logDetailsContent" class="log-details-content"></div>
                </div>
            </div>
        </div>
        
        <script>
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
                    
                    // Start polling for progress if sync_id is available (regardless of initial success)
                    if (data.sync_id) {
                        pollProgress(data.sync_id);
                    } else {
                        progressDiv.style.display = 'none';
                    }
                    
                    if (data.success) {
                        resultDiv.className = 'result-panel success';
                        resultDiv.innerHTML = `<h3>✅ ${data.message}</h3><pre>${data.output || ''}</pre>`;
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
            function formatDuration(seconds) {
                if (!seconds) return '0s';
                if (seconds < 60) {
                    return `${Math.round(seconds)}s`;
                } else if (seconds < 3600) {
                    return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
                } else {
                    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
                }
            }
            
            function formatTimestamp(isoString) {
                try {
                    const date = new Date(isoString);
                    return date.toLocaleString();
                } catch (e) {
                    return 'Invalid date';
                }
            }
            
            async function loadLogs() {
                const logsLoading = document.getElementById('logsLoading');
                const logsList = document.getElementById('logsList');
                const logDetails = document.getElementById('logDetails');
                
                logsLoading.style.display = 'block';
                logsList.style.display = 'none';
                logDetails.style.display = 'none';
                logsLoading.textContent = 'Loading logs...';
                
                try {
                    const response = await fetch('/logs/manifest');
                    const data = await response.json();
                    
                    logsLoading.style.display = 'none';
                    
                    if (data.success && data.logs && data.logs.length > 0) {
                        // Show last 5 logs
                        const recentLogs = data.logs.slice(0, 5);
                        
                        let logsHTML = '';
                        if (recentLogs.length === 0) {
                            logsHTML = '<div class="empty-logs">No sync logs found.</div>';
                        } else {
                            recentLogs.forEach((log) => {
                                const statusIcon = log.success ? '✅' : '❌';
                                const timestamp = formatTimestamp(log.timestamp);
                                const duration = formatDuration(log.duration_seconds);
                                
                                logsHTML += `
                                    <div class="log-item" data-filename="${log.filename}">
                                        <div class="log-item-header">
                                            <div class="log-item-title">
                                                ${statusIcon} ${log.sync_type}
                                            </div>
                                            <div class="log-item-timestamp">${timestamp}</div>
                                        </div>
                                        <div class="log-item-details">
                                            <span>${log.message}</span>
                                            <span>${duration}</span>
                                        </div>
                                    </div>
                                `;
                            });
                        }
                        
                        logsList.innerHTML = logsHTML;
                        logsList.style.display = 'block';
                        
                        // Add click handlers to log items
                        const logItems = logsList.querySelectorAll('.log-item');
                        logItems.forEach(item => {
                            item.addEventListener('click', () => {
                                const filename = item.getAttribute('data-filename');
                                showLogDetails(filename);
                            });
                        });
                        
                    } else {
                        logsList.innerHTML = '<div class="empty-logs">No sync logs found.</div>';
                        logsList.style.display = 'block';
                    }
                    
                } catch (error) {
                    logsLoading.style.display = 'none';
                    logsList.innerHTML = `<div class="empty-logs" style="color: var(--text-error);">Failed to load logs: ${error.message}</div>`;
                    logsList.style.display = 'block';
                }
            }
            
            async function showLogDetails(filename) {
                const logDetails = document.getElementById('logDetails');
                const logDetailsContent = document.getElementById('logDetailsContent');
                
                logDetailsContent.innerHTML = 'Loading log details...';
                logDetails.style.display = 'block';
                
                try {
                    const response = await fetch(`/logs/${filename}`);
                    const data = await response.json();
                    
                    if (data.success && data.log) {
                        const log = data.log;
                        const statusIcon = log.success ? '✅' : '❌';
                        const statusText = log.success ? 'Success' : 'Failed';
                        
                        let detailsHTML = `
                            <h4>${statusIcon} ${log.sync_type} Sync - ${statusText}</h4>
                            
                            <div class="log-details-meta">
                                <div class="log-details-meta-item">
                                    <div class="log-details-meta-label">Timestamp</div>
                                    <div class="log-details-meta-value">${formatTimestamp(log.timestamp)}</div>
                                </div>
                                <div class="log-details-meta-item">
                                    <div class="log-details-meta-label">Duration</div>
                                    <div class="log-details-meta-value">${formatDuration(log.duration_seconds)}</div>
                                </div>
                                <div class="log-details-meta-item">
                                    <div class="log-details-meta-label">Sync ID</div>
                                    <div class="log-details-meta-value">${log.sync_id || 'N/A'}</div>
                                </div>
                            </div>
                            
                            <div class="log-details-section">
                                <strong>Message:</strong> ${log.message}
                            </div>
                        `;
                        
                        // Add instance info for VastAI syncs
                        if (log.instance_info) {
                            detailsHTML += `
                                <div class="log-details-section">
                                    <strong>Instance Info:</strong><br>
                                    ID: ${log.instance_info.id}<br>
                                    GPU: ${log.instance_info.gpu || 'N/A'}<br>
                                    Host: ${log.instance_info.host}:${log.instance_info.port}
                                </div>
                            `;
                        }
                        
                        // Add output if available
                        if (log.output) {
                            detailsHTML += `
                                <div class="log-details-section">
                                    <strong>Output:</strong>
                                    <pre>${log.output}</pre>
                                </div>
                            `;
                        }
                        
                        // Add error if available
                        if (log.error) {
                            detailsHTML += `
                                <div class="log-details-section error">
                                    <strong>Error:</strong>
                                    <pre>${log.error}</pre>
                                </div>
                            `;
                        }
                        
                        logDetailsContent.innerHTML = detailsHTML;
                    } else {
                        logDetailsContent.innerHTML = `<p style="color: var(--text-error);">Failed to load log details: ${data.message || 'Unknown error'}</p>`;
                    }
                } catch (error) {
                    logDetailsContent.innerHTML = `<p style="color: var(--text-error);">Error loading log details: ${error.message}</p>`;
                }
            }
            
            async function refreshLogs() {
                const refreshBtn = document.getElementById('refreshLogsBtn');
                const originalHTML = refreshBtn.innerHTML;
                
                refreshBtn.innerHTML = '<span>🔄</span>Refreshing...';
                refreshBtn.disabled = true;
                refreshBtn.style.background = 'var(--text-warning)';
                
                try {
                    await loadLogs();
                    refreshBtn.style.background = 'var(--text-success)';
                    refreshBtn.innerHTML = '<span>✅</span>Refreshed';
                    
                    // Reset button after 2 seconds
                    setTimeout(() => {
                        refreshBtn.innerHTML = originalHTML;
                        refreshBtn.style.background = '';
                        refreshBtn.disabled = false;
                    }, 2000);
                } catch (error) {
                    refreshBtn.style.background = 'var(--text-error)';
                    refreshBtn.innerHTML = '<span>❌</span>Error';
                    
                    // Reset button after 3 seconds
                    setTimeout(() => {
                        refreshBtn.innerHTML = originalHTML;
                        refreshBtn.style.background = '';
                        refreshBtn.disabled = false;
                    }, 3000);
                }
            }
            
            // Initialize logs on page load
            document.addEventListener('DOMContentLoaded', () => {
                loadLogs();
                
                // Add event listeners
                document.getElementById('refreshLogsBtn').addEventListener('click', refreshLogs);
                document.getElementById('closeLogBtn').addEventListener('click', () => {
                    document.getElementById('logDetails').style.display = 'none';
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
                    'duration_seconds': log_data.get('duration_seconds')
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
