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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='/static')

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
        <link id="theme-css" rel="stylesheet" href="/static/css/base.css">
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>
                    <span>🔄</span>
                    Media Sync Tool
                </h1>
                <p>Sync media from your configured sources</p>
                <button class="theme-toggle" onclick="toggleTheme()">🌙 Dark Theme</button>
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
            
            // Close modal when clicking outside of it
            document.addEventListener('DOMContentLoaded', function() {
                const overlay = document.getElementById('logOverlay');
                overlay.addEventListener('click', function(e) {
                    if (e.target === overlay) {
                        closeLogModal();
                    }
                });
                
                // Load saved theme preference
                const savedTheme = localStorage.getItem('media-sync-theme') || 'base';
                if (savedTheme === 'dark') {
                    setTheme('dark');
                }
            });
            
            // Theme switching functionality
            function toggleTheme() {
                const currentTheme = getCurrentTheme();
                const newTheme = currentTheme === 'base' ? 'dark' : 'base';
                setTheme(newTheme);
            }
            
            function getCurrentTheme() {
                const themeLink = document.getElementById('theme-css');
                return themeLink.href.includes('dark-theme.css') ? 'dark' : 'base';
            }
            
            function setTheme(theme) {
                const themeLink = document.getElementById('theme-css');
                const themeToggle = document.querySelector('.theme-toggle');
                
                if (theme === 'dark') {
                    themeLink.href = '/static/css/dark-theme.css';
                    themeToggle.textContent = '☀️ Light Theme';
                    themeToggle.title = 'Switch to Light Theme';
                    localStorage.setItem('media-sync-theme', 'dark');
                } else {
                    themeLink.href = '/static/css/base.css';
                    themeToggle.textContent = '🌙 Dark Theme';
                    themeToggle.title = 'Switch to Dark Theme';
                    localStorage.setItem('media-sync-theme', 'base');
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
