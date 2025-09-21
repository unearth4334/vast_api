#!/usr/bin/env python3
"""
Media Sync API Server
Provides web API endpoints for syncing media from local Docker containers and VastAI instances.
"""

import os
import subprocess
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS

# Import our refactored modules
try:
    from .sync_utils import run_sync, FORGE_HOST, FORGE_PORT, COMFY_HOST, COMFY_PORT
    from ..vastai.vast_manager import VastManager
    from ..vastai.vastai_utils import parse_ssh_connection, parse_host_port, read_api_key_from_file
    from ..utils.sync_logs import get_logs_manifest, get_log_file_content, get_active_syncs, get_latest_sync, get_sync_progress
    from ..webui.templates import get_index_template
    from .ssh_test import SSHTester
except ImportError:
    # Handle imports for both module and direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from sync_utils import run_sync, FORGE_HOST, FORGE_PORT, COMFY_HOST, COMFY_PORT
    from vastai.vast_manager import VastManager
    from vastai.vastai_utils import parse_ssh_connection, parse_host_port, read_api_key_from_file
    from utils.sync_logs import get_logs_manifest, get_log_file_content, get_active_syncs, get_latest_sync, get_sync_progress
    from webui.templates import get_index_template
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


def _extract_host_port(ssh_connection):
    """Helper function to extract host and port from SSH connection string"""
    return parse_host_port(ssh_connection)


# --- Web UI Routes ---

@app.route('/')
def index():
    """Web interface for testing"""
    return get_index_template()


# --- Sync API Routes ---

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
    """Sync from VastAI using manual connection string"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json() if request.is_json else {}
        ssh_connection = data.get('ssh_connection', '')
        cleanup = data.get('cleanup', True)
        
        if not ssh_connection:
            return jsonify({
                'success': False,
                'message': 'SSH connection string is required'
            })
        
        try:
            ssh_host, ssh_port = _extract_host_port(ssh_connection)
        except ValueError as e:
            return jsonify({
                'success': False,
                'message': str(e)
            })
        
        logger.info(f"Starting VastAI sync from connection string: {ssh_connection}")
        
        result = run_sync(ssh_host, ssh_port, "VastAI-Connection", cleanup=cleanup)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"VastAI connection sync error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'VastAI connection sync error: {str(e)}'
        })


# --- SSH Test Routes ---

@app.route('/test/ssh', methods=['POST', 'OPTIONS'])
def test_ssh():
    """Test SSH connectivity to configured hosts"""
    if request.method == 'OPTIONS':
        return ("", 204)
        
    if not SSHTester:
        return jsonify({
            'success': False,
            'message': 'SSH testing functionality not available'
        })
    
    try:
        tester = SSHTester()
        results = tester.test_all_hosts()
        
        return jsonify({
            'success': True,
            'results': results['results'],
            'summary': results['summary']
        })
        
    except Exception as e:
        logger.error(f"SSH test error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'SSH test error: {str(e)}'
        })


# --- Progress and Logging Routes ---

@app.route('/sync/progress/<sync_id>')
def get_sync_progress_route(sync_id):
    """Get progress for a specific sync operation"""
    return jsonify(get_sync_progress(sync_id))


@app.route('/logs/manifest', methods=['GET', 'OPTIONS'])
def get_logs_manifest_route():
    """Get list of available log files"""
    if request.method == 'OPTIONS':
        return ("", 204)
    return jsonify(get_logs_manifest())


@app.route('/logs/<filename>', methods=['GET', 'OPTIONS'])
def get_log_file_route(filename):
    """Get specific log file content"""
    if request.method == 'OPTIONS':
        return ("", 204)
    return jsonify(get_log_file_content(filename))


@app.route("/sync/latest")
def sync_latest():
    """Get the most recent sync progress"""
    return jsonify(get_latest_sync())


@app.route("/sync/active")
def sync_active():
    """List all known progress files with brief status for debugging/menus"""
    return jsonify(get_active_syncs())


# --- Status Routes ---

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
    except Exception as e:
        logger.error(f"VastAI status check error: {str(e)}")
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


# --- VastAI Management Routes ---

@app.route('/vastai/set-ui-home', methods=['POST', 'OPTIONS'])
def set_ui_home():
    """Set UI_HOME environment variable on VastAI instance"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json() if request.is_json else {}
        ssh_connection = data.get('ssh_connection')
        ui_home_path = data.get('ui_home_path', '/workspace/ComfyUI/')
        
        if not ssh_connection:
            return jsonify({
                'success': False,
                'message': 'SSH connection string is required'
            })
        
        try:
            ssh_host, ssh_port = _extract_host_port(ssh_connection)
        except ValueError as e:
            return jsonify({
                'success': False,
                'message': str(e)
            })
        
        logger.info(f"Setting UI_HOME to {ui_home_path} on {ssh_host}:{ssh_port}")
        
        # Execute the command to set UI_HOME
        cmd = [
            'ssh', '-p', ssh_port,
            f'root@{ssh_host}',
            f'echo "export UI_HOME={ui_home_path}" >> ~/.bashrc && echo "UI_HOME set successfully"'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': f'UI_HOME set to {ui_home_path}',
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to set UI_HOME',
                'error': result.stderr
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'message': 'SSH command timed out'
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
        data = request.get_json() if request.is_json else {}
        ssh_connection = data.get('ssh_connection')
        
        if not ssh_connection:
            return jsonify({
                'success': False,
                'message': 'SSH connection string is required'
            })
        
        try:
            ssh_host, ssh_port = _extract_host_port(ssh_connection)
        except ValueError as e:
            return jsonify({
                'success': False,
                'message': str(e)
            })
        
        logger.info(f"Reading UI_HOME from {ssh_host}:{ssh_port}")
        
        # Execute the command to get UI_HOME
        cmd = [
            'ssh', '-p', ssh_port,
            f'root@{ssh_host}',
            'echo $UI_HOME'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            ui_home = result.stdout.strip()
            return jsonify({
                'success': True,
                'ui_home': ui_home if ui_home else 'Not set',
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to get UI_HOME',
                'error': result.stderr
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'message': 'SSH command timed out'
        })
    except Exception as e:
        logger.error(f"Error getting UI_HOME: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting UI_HOME: {str(e)}'
        })


@app.route('/vastai/terminate-connection', methods=['POST', 'OPTIONS'])
def terminate_connection():
    """Terminate connections to VastAI instance"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json() if request.is_json else {}
        ssh_connection = data.get('ssh_connection')
        
        if not ssh_connection:
            return jsonify({
                'success': False,
                'message': 'SSH connection string is required'
            })
        
        try:
            ssh_host, ssh_port = _extract_host_port(ssh_connection)
        except ValueError as e:
            return jsonify({
                'success': False,
                'message': str(e)
            })
        
        logger.info(f"Terminating connections to {ssh_host}:{ssh_port}")
        
        # Kill any existing SSH connections to this host
        kill_cmd = ['pkill', '-f', f'{ssh_host}.*{ssh_port}']
        subprocess.run(kill_cmd, capture_output=True)
        
        return jsonify({
            'success': True,
            'message': f'Terminated connections to {ssh_host}:{ssh_port}'
        })
        
    except Exception as e:
        logger.error(f"Error terminating connections: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error terminating connections: {str(e)}'
        })


@app.route('/vastai/instances', methods=['GET', 'OPTIONS'])
def get_vastai_instances():
    """Get list of VastAI instances"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        vast_manager = VastManager()
        instances = vast_manager.list_instances()
        
        return jsonify({
            'success': True,
            'instances': instances
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
        data = request.get_json() if request.is_json else {}
        ssh_connection = data.get('ssh_connection')
        
        if not ssh_connection:
            return jsonify({
                'success': False,
                'message': 'SSH connection string is required'
            })
        
        try:
            ssh_host, ssh_port = _extract_host_port(ssh_connection)
        except ValueError as e:
            return jsonify({
                'success': False,
                'message': str(e)
            })
        
        logger.info(f"Setting up CivitDL on {ssh_host}:{ssh_port}")
        
        # Setup commands for CivitDL
        setup_commands = [
            'pip install civitdl',
            'mkdir -p /workspace/civitdl',
            'cd /workspace/civitdl',
            'echo "CivitDL setup complete"'
        ]
        
        command_string = ' && '.join(setup_commands)
        
        cmd = [
            'ssh', '-p', ssh_port,
            f'root@{ssh_host}',
            command_string
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': 'CivitDL setup completed successfully',
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'message': 'CivitDL setup failed',
                'error': result.stderr
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'message': 'CivitDL setup timed out'
        })
    except Exception as e:
        logger.error(f"Error setting up CivitDL: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error setting up CivitDL: {str(e)}'
        })


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1].replace('--port=', '').replace('--port', '')) if len(sys.argv) > 1 and '--port' in sys.argv[1] else 5000
    app.run(host='0.0.0.0', port=port, debug=False)