#!/usr/bin/env python3
"""
Media Sync API Server
Provides web API endpoints for syncing media from local Docker containers and VastAI instances.
"""

import os
import subprocess
import logging
import time
import uuid
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Import our refactored modules
try:
    from .sync_utils import run_sync, FORGE_HOST, FORGE_PORT, COMFY_HOST, COMFY_PORT
    from ..vastai.vast_manager import VastManager
    from ..vastai.vastai_utils import parse_ssh_connection, parse_host_port, read_api_key_from_file, get_ssh_port
    from ..utils.sync_logs import get_logs_manifest, get_log_file_content, get_active_syncs, get_latest_sync, get_sync_progress
    from ..utils.config_loader import load_config, load_api_key
    from ..utils.vastai_logging import enhanced_logger, LogContext
    from ..webui.templates import get_index_template
    from ..webui.template_manager import template_manager
    from .ssh_test import SSHTester
except ImportError:
    # Handle imports for both module and direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from sync_utils import run_sync, FORGE_HOST, FORGE_PORT, COMFY_HOST, COMFY_PORT
    from vastai.vast_manager import VastManager
    from vastai.vastai_utils import parse_ssh_connection, parse_host_port, read_api_key_from_file, get_ssh_port
    from utils.sync_logs import get_logs_manifest, get_log_file_content, get_active_syncs, get_latest_sync, get_sync_progress
    from utils.config_loader import load_config, load_api_key
    from webui.templates import get_index_template
    try:
        from ssh_test import SSHTester
    except ImportError:
        SSHTester = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Cache for VastAI status to prevent excessive API calls from health checks
_vastai_status_cache = {
    'data': None,
    'timestamp': 0,
    'ttl': 300  # 5 minutes in seconds
}

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


def _get_cached_vastai_status():
    """Get VastAI status with caching to prevent excessive API calls from health checks"""
    current_time = time.time()
    
    # Check if we have valid cached data
    if (_vastai_status_cache['data'] is not None and 
        current_time - _vastai_status_cache['timestamp'] < _vastai_status_cache['ttl']):
        return _vastai_status_cache['data']
    
    # Cache is expired or empty, fetch fresh data
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
    
    # Update cache
    _vastai_status_cache['data'] = vastai_status
    _vastai_status_cache['timestamp'] = current_time
    
    return vastai_status


# --- Web UI Routes ---

@app.route('/')
def index():
    """Web interface for testing"""
    return get_index_template()

@app.route('/css/<path:filename>')
def serve_css(filename):
    """Serve CSS files"""
    try:
        from ..webui import css_path
        return send_from_directory(css_path, filename)
    except ImportError:
        # Handle both module and direct execution
        import os
        css_path = os.path.join(os.path.dirname(__file__), '..', 'webui', 'css')
        return send_from_directory(css_path, filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    """Serve JavaScript files"""
    try:
        from ..webui import js_path
        return send_from_directory(js_path, filename)
    except ImportError:
        # Handle both module and direct execution
        import os
        js_path = os.path.join(os.path.dirname(__file__), '..', 'webui', 'js')
        return send_from_directory(js_path, filename)


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
        ssh_port = str(get_ssh_port(running_instance) or 22)
        
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

@app.route('/test/ssh/vastai', methods=['POST', 'OPTIONS'])
def test_vastai_ssh():
    """Test SSH connectivity to a specific VastAI instance"""
    if request.method == 'OPTIONS':
        return ("", 204)
        
    try:
        data = request.get_json() if request.is_json else {}
        ssh_connection = data.get('ssh_connection')
        
        if not ssh_connection:
            enhanced_logger.log_error(
                "SSH test failed - no connection string provided",
                "validation_error",
                context=LogContext(
                    operation_id=f"test_ssh_{int(time.time())}",
                    user_agent="vast_api/1.0 (test_ssh)",
                    session_id=f"session_{int(time.time())}",
                    ip_address=request.remote_addr or "localhost"
                )
            )
            return jsonify({
                'success': False,
                'message': 'SSH connection string is required'
            })
        
        try:
            ssh_host, ssh_port = _extract_host_port(ssh_connection)
        except ValueError as e:
            enhanced_logger.log_error(
                f"SSH test failed - invalid connection format: {str(e)}",
                "validation_error",
                context=LogContext(
                    operation_id=f"test_ssh_{int(time.time())}",
                    user_agent="vast_api/1.0 (test_ssh)",
                    session_id=f"session_{int(time.time())}",
                    ip_address=request.remote_addr or "localhost"
                )
            )
            return jsonify({
                'success': False,
                'message': str(e)
            })
        
        enhanced_logger.log_operation(
            f"Testing SSH connection to {ssh_host}:{ssh_port}",
            context=LogContext(
                operation_id=f"test_ssh_{int(time.time())}",
                user_agent="vast_api/1.0 (test_ssh)",
                session_id=f"session_{int(time.time())}",
                ip_address=request.remote_addr or "localhost"
            )
        )
        logger.info(f"Testing SSH connection to {ssh_host}:{ssh_port}")
        
        # Test basic SSH connectivity
        cmd = [
            'ssh', 
            '-p', ssh_port,
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'LogLevel=ERROR',
            '-o', 'ConnectTimeout=10',
            '-o', 'BatchMode=yes',  # Fail if password authentication is required
            f'root@{ssh_host}',
            'echo "SSH connection successful" && whoami && pwd'
        ]
        
        logger.debug(f"Executing SSH test command: {' '.join(cmd[:8])} [command hidden]")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        logger.debug(f"SSH test return code: {result.returncode}")
        logger.debug(f"SSH test stdout: {result.stdout}")
        logger.debug(f"SSH test stderr: {result.stderr}")
        
        if result.returncode == 0:
            enhanced_logger.log_operation(
                f"✅ SSH connection successful to {ssh_host}:{ssh_port}",
                context=LogContext(
                    operation_id=f"test_ssh_{int(time.time())}",
                    user_agent="vast_api/1.0 (test_ssh)",
                    session_id=f"session_{int(time.time())}",
                    ip_address=request.remote_addr or "localhost"
                )
            )
            return jsonify({
                'success': True,
                'message': f'SSH connection to {ssh_host}:{ssh_port} successful',
                'output': result.stdout,
                'host': ssh_host,
                'port': ssh_port
            })
        else:
            # Provide more detailed error information
            error_msg = "SSH connection failed"
            if "Permission denied" in result.stderr:
                error_msg = "SSH authentication failed - check SSH keys"
            elif "Connection refused" in result.stderr:
                error_msg = "SSH connection refused - check host and port"
            elif "No route to host" in result.stderr:
                error_msg = "Network unreachable - check host address"
            elif "Connection timed out" in result.stderr:
                error_msg = "SSH connection timed out - check host and firewall"
            
            enhanced_logger.log_error(
                f"❌ SSH connection failed to {ssh_host}:{ssh_port} - {error_msg}",
                "connection_error",
                context=LogContext(
                    operation_id=f"test_ssh_{int(time.time())}",
                    user_agent="vast_api/1.0 (test_ssh)",
                    session_id=f"session_{int(time.time())}",
                    ip_address=request.remote_addr or "localhost"
                )
            )
            return jsonify({
                'success': False,
                'message': error_msg,
                'error': result.stderr,
                'return_code': result.returncode,
                'host': ssh_host,
                'port': ssh_port
            })
            
    except subprocess.TimeoutExpired:
        enhanced_logger.log_error(
            "SSH connection test timed out",
            "timeout_error",
            context=LogContext(
                operation_id=f"test_ssh_{int(time.time())}",
                user_agent="vast_api/1.0 (test_ssh)",
                session_id=f"session_{int(time.time())}",
                ip_address=request.remote_addr or "localhost"
            )
        )
        return jsonify({
            'success': False,
            'message': 'SSH connection test timed out'
        })
    except Exception as e:
        enhanced_logger.log_error(
            f"SSH test unexpected error: {str(e)}",
            "unexpected_error",
            context=LogContext(
                operation_id=f"test_ssh_{int(time.time())}",
                user_agent="vast_api/1.0 (test_ssh)",
                session_id=f"session_{int(time.time())}",
                ip_address=request.remote_addr or "localhost"
            )
        )
        logger.error(f"SSH test error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'SSH test error: {str(e)}'
        })


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


@app.route('/logs/info', methods=['GET', 'OPTIONS'])
def get_log_info_route():
    """Get log directory information and status"""
    if request.method == 'OPTIONS':
        return ("", 204)
    try:
        from ..utils.log_init import get_log_directory_info
        return jsonify(get_log_directory_info())
    except ImportError:
        from utils.log_init import get_log_directory_info
        return jsonify(get_log_directory_info())


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


# --- VastAI Logs Routes ---

@app.route('/vastai/logs', methods=['GET', 'OPTIONS'])
def get_vastai_logs():
    """Get VastAI API logs with optional parameters"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        # Import here to avoid circular imports
        from ..utils.vastai_logging import get_vastai_logs
        
        max_lines = request.args.get('lines', 100, type=int)
        date_filter = request.args.get('date', None)
        
        logs = get_vastai_logs(max_lines=max_lines, date_filter=date_filter)
        
        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs)
        })
        
    except Exception as e:
        logger.error(f"Error retrieving VastAI logs: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving VastAI logs: {str(e)}',
            'logs': [],
            'count': 0
        })


@app.route('/vastai/logs/manifest', methods=['GET', 'OPTIONS'])
def get_vastai_logs_manifest():
    """Get manifest of available VastAI log files"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        # Import here to avoid circular imports
        from ..utils.vastai_logging import get_vastai_log_manifest
        
        manifest = get_vastai_log_manifest()
        
        return jsonify({
            'success': True,
            'files': manifest
        })
        
    except Exception as e:
        logger.error(f"Error retrieving VastAI log manifest: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving VastAI log manifest: {str(e)}',
            'files': []
        })


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
    vastai_status = _get_cached_vastai_status()
    
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
        
        # Execute the command to set UI_HOME with proper SSH options
        cmd = [
            'ssh', 
            '-p', ssh_port,
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'LogLevel=ERROR',
            '-o', 'ConnectTimeout=10',
            f'root@{ssh_host}',
            f'echo "export UI_HOME={ui_home_path}" >> ~/.bashrc && echo "UI_HOME set successfully"'
        ]
        
        logger.debug(f"Executing SSH command: {' '.join(cmd[:7])} [command hidden]")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        logger.debug(f"SSH command return code: {result.returncode}")
        logger.debug(f"SSH stdout: {result.stdout}")
        logger.debug(f"SSH stderr: {result.stderr}")
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': f'UI_HOME set to {ui_home_path}',
                'output': result.stdout
            })
        else:
            logger.error(f"SSH command failed with return code {result.returncode}")
            logger.error(f"SSH stderr: {result.stderr}")
            return jsonify({
                'success': False,
                'message': 'Failed to set UI_HOME',
                'error': result.stderr,
                'return_code': result.returncode
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'message': 'SSH command timed out'
        })
    except Exception as e:
        logger.error(f"Error setting UI_HOME: {str(e)}")
        
        # Log the error to application logs
        try:
            from ..utils.app_logging import log_error
            log_error("ssh.ui_home_set", f"Failed to set UI_HOME: {str(e)}", {
                "ssh_host": ssh_host,
                "ssh_port": ssh_port, 
                "ui_home_path": ui_home_path,
                "error": str(e)
            })
        except ImportError:
            from utils.app_logging import log_error
            log_error("ssh.ui_home_set", f"Failed to set UI_HOME: {str(e)}", {
                "ssh_host": ssh_host,
                "ssh_port": ssh_port,
                "ui_home_path": ui_home_path,
                "error": str(e)
            })
        
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
        
        # Execute the command to get UI_HOME with proper SSH options
        cmd = [
            'ssh', 
            '-p', ssh_port,
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'LogLevel=ERROR',
            '-o', 'ConnectTimeout=10',
            f'root@{ssh_host}',
            'source ~/.bashrc && echo $UI_HOME'
        ]
        
        logger.debug(f"Executing SSH command: {' '.join(cmd[:7])} [command hidden]")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        logger.debug(f"SSH command return code: {result.returncode}")
        logger.debug(f"SSH stdout: {result.stdout}")
        logger.debug(f"SSH stderr: {result.stderr}")
        
        if result.returncode == 0:
            ui_home = result.stdout.strip()
            return jsonify({
                'success': True,
                'ui_home': ui_home if ui_home else 'Not set',
                'output': result.stdout
            })
        else:
            logger.error(f"SSH command failed with return code {result.returncode}")
            logger.error(f"SSH stderr: {result.stderr}")
            return jsonify({
                'success': False,
                'message': 'Failed to get UI_HOME',
                'error': result.stderr,
                'return_code': result.returncode
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
            'instances': instances,
            'count': len(instances)
        })
        
    except Exception as e:
        logger.error(f"Error getting VastAI instances: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting VastAI instances: {str(e)}'
        })


@app.route('/vastai/instances/<int:instance_id>', methods=['GET', 'OPTIONS'])
def get_vastai_instance_details(instance_id):
    """Get details of a specific VastAI instance"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        vast_manager = VastManager()
        # Get all instances and find the one with matching ID
        instances = vast_manager.list_instances()
        
        # Find the specific instance
        instance = next((inst for inst in instances if inst.get('id') == instance_id), None)
        
        if not instance:
            return jsonify({
                'success': False,
                'message': f'Instance {instance_id} not found'
            })
        
        return jsonify({
            'success': True,
            'instance': instance
        })
        
    except Exception as e:
        logger.error(f"Error getting VastAI instance {instance_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting VastAI instance {instance_id}: {str(e)}'
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


@app.route('/vastai/search-offers', methods=['GET', 'OPTIONS'])
def search_vastai_offers():
    """Search for available VastAI offers"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        # Get query parameters
        gpu_ram = request.args.get('gpu_ram', 10, type=int)
        sort = request.args.get('sort', 'dph_total')
        pcie_bandwidth = request.args.get('pcie_bandwidth', type=float)
        net_up = request.args.get('net_up', type=int)
        net_down = request.args.get('net_down', type=int)
        price_max = request.args.get('price_max', type=float)
        gpu_model = request.args.get('gpu_model', type=str)
        locations = request.args.get('locations', type=str)
        
        # Parse locations into a list if provided
        location_list = locations.split(',') if locations else None
        
        # Import the API function
        from ..utils.vastai_api import query_offers, VastAIAPIError
        
        # Read API key
        api_key = read_api_key_from_file()
        if not api_key:
            return jsonify({
                'success': False,
                'message': 'VastAI API key not found. Please check api_key.txt file.'
            })
        
        # Query offers using the VastAI API
        logger.info(f"Searching VastAI offers with gpu_ram={gpu_ram}, sort={sort}, pcie_bandwidth={pcie_bandwidth}, net_up={net_up}, net_down={net_down}, price_max={price_max}, gpu_model={gpu_model}, locations={location_list}")
        resp_json = query_offers(
            api_key, 
            gpu_ram=gpu_ram, 
            sort=sort, 
            pcie_bandwidth=pcie_bandwidth,
            net_up=net_up,
            net_down=net_down,
            price_max=price_max,
            gpu_model=gpu_model,
            locations=location_list
        )
        
        # Extract offers from response
        offers = resp_json.get('offers', []) if resp_json else []
        
        return jsonify({
            'success': True,
            'offers': offers,
            'count': len(offers)
        })
        
    except VastAIAPIError as e:
        logger.error(f"VastAI API error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'VastAI API error: {str(e)}'
        })
    except Exception as e:
        logger.error(f"Error searching VastAI offers: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error searching offers: {str(e)}'
        })


@app.route('/vastai/create-instance', methods=['POST', 'OPTIONS'])
def create_vastai_instance():
    """Create a VastAI instance from an offer"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json() if request.is_json else {}
        offer_id = data.get('offer_id')
        
        if not offer_id:
            return jsonify({
                'success': False,
                'message': 'Offer ID is required'
            })
        
        # Import the API function
        from ..utils.vastai_api import create_instance, VastAIAPIError
        
        # Read API key
        api_key = read_api_key_from_file()
        if not api_key:
            return jsonify({
                'success': False,
                'message': 'VastAI API key not found. Please check api_key.txt file.'
            })
        
        # Read configuration for template and environment
        try:
            config = load_config()
        except FileNotFoundError:
            return jsonify({
                'success': False,
                'message': 'config.yaml not found. Please ensure configuration file exists.'
            })
        
        template_hash_id = config.get('template_hash_id')
        ui_home_env = config.get('ui_home_env')
        disk_size_gb = config.get('disk_size_gb', 32)
        
        if not template_hash_id or template_hash_id == "None":
            return jsonify({
                'success': False,
                'message': 'Template hash ID not configured in config.yaml'
            })
        
        if not ui_home_env or ui_home_env == "None":
            return jsonify({
                'success': False,
                'message': 'UI_HOME environment variable not configured in config.yaml'
            })
        
        # Create the instance
        logger.info(f"Creating VastAI instance from offer {offer_id}")
        result = create_instance(api_key, offer_id, template_hash_id, ui_home_env, disk_size_gb)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': 'Instance created successfully',
                'instance_id': result.get('new_contract'),
                'result': result
            })
        else:
            return jsonify({
                'success': False,
                'message': f"Failed to create instance: {result.get('msg', 'Unknown error')}",
                'result': result
            })
        
    except VastAIAPIError as e:
        logger.error(f"VastAI API error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'VastAI API error: {str(e)}'
        })
    except Exception as e:
        logger.error(f"Error creating VastAI instance: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error creating instance: {str(e)}'
        })


# --- Template Management Routes ---

@app.route('/templates', methods=['GET', 'OPTIONS'])
def get_templates():
    """Get list of available setup templates"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        templates = template_manager.get_available_templates()
        return jsonify({
            'success': True,
            'templates': templates
        })
    except Exception as e:
        logger.error(f"Error getting templates: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting templates: {str(e)}'
        })


@app.route('/templates/<template_name>', methods=['GET', 'OPTIONS'])
def get_template(template_name):
    """Get specific template configuration"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        template_data = template_manager.load_template(template_name)
        if not template_data:
            return jsonify({
                'success': False,
                'message': f'Template "{template_name}" not found'
            })
        
        return jsonify({
            'success': True,
            'template': template_data
        })
    except Exception as e:
        logger.error(f"Error getting template {template_name}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting template: {str(e)}'
        })


@app.route('/templates/<template_name>/execute-step', methods=['POST', 'OPTIONS'])
def create_template_context(template_name: str, step_name: str = None) -> LogContext:
    """Create enhanced logging context for template operations"""
    operation_id = f"template_{template_name}_{step_name or 'general'}_{int(time.time())}_{str(uuid.uuid4())[:8]}"
    return LogContext(
        operation_id=operation_id,
        user_agent=f"template_executor/1.0 ({template_name})",
        session_id=f"template_session_{int(time.time())}",
        ip_address=request.remote_addr or "localhost",
        instance_id=None,
        template_name=template_name
    )


@app.route('/templates/<template_name>/execute-step', methods=['POST', 'OPTIONS'])
def execute_template_step(template_name):
    """Execute a specific step from a template with enhanced logging"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json()
        ssh_connection = data.get('ssh_connection')
        step_name = data.get('step_name')
        
        # Create enhanced logging context
        context = create_template_context(template_name, step_name)
        
        enhanced_logger.log_operation(
            message=f"Starting template step execution: {template_name} - {step_name}",
            operation="template_step_start",
            context=context,
            extra_data={
                "template_name": template_name,
                "step_name": step_name,
                "has_ssh_connection": bool(ssh_connection),
                "request_data": data
            }
        )
        
        if not ssh_connection:
            enhanced_logger.log_error(
                message="SSH connection string is required for template execution",
                error_type="missing_ssh_connection",
                context=context,
                extra_data={"template_name": template_name, "step_name": step_name}
            )
            return jsonify({
                'success': False,
                'message': 'SSH connection string is required'
            })
        
        if not step_name:
            enhanced_logger.log_error(
                message="Step name is required for template execution",
                error_type="missing_step_name",
                context=context,
                extra_data={"template_name": template_name}
            )
            return jsonify({
                'success': False,
                'message': 'Step name is required'
            })
        
        # Get template and find the step
        template_data = template_manager.load_template(template_name)
        if not template_data:
            enhanced_logger.log_error(
                message=f'Template "{template_name}" not found',
                error_type="template_not_found",
                context=context,
                extra_data={"template_name": template_name}
            )
            return jsonify({
                'success': False,
                'message': f'Template "{template_name}" not found'
            })
        
        setup_steps = template_data.get('setup_steps', [])
        step = next((s for s in setup_steps if s.get('name') == step_name), None)
        
        if not step:
            enhanced_logger.log_error(
                message=f'Step "{step_name}" not found in template "{template_name}"',
                error_type="step_not_found",
                context=context,
                extra_data={
                    "template_name": template_name,
                    "step_name": step_name,
                    "available_steps": [s.get('name') for s in setup_steps]
                }
            )
            return jsonify({
                'success': False,
                'message': f'Step "{step_name}" not found in template'
            })
        
        enhanced_logger.log_operation(
            message=f"Executing template step: {step_name} (type: {step.get('type')})",
            operation="template_step_execute",
            context=context,
            extra_data={
                "template_name": template_name,
                "step_name": step_name,
                "step_type": step.get('type'),
                "step_config": step,
                "ssh_connection_host": ssh_connection.split('@')[-1].split(':')[0] if '@' in ssh_connection else "unknown"
            }
        )
        
        # Execute the step based on its type
        start_time = time.time()
        result = execute_step(ssh_connection, step, template_data, context)
        execution_time = time.time() - start_time
        
        enhanced_logger.log_performance(
            message=f"Template step execution completed: {step_name}",
            operation="template_step_complete",
            duration=execution_time,
            context=context,
            extra_data={
                "template_name": template_name,
                "step_name": step_name,
                "step_type": step.get('type'),
                "success": result.get('success', False),
                "result": result
            }
        )
        
        if result.get('success'):
            enhanced_logger.log_operation(
                message=f"Template step '{step_name}' completed successfully",
                operation="template_step_success",
                context=context,
                extra_data={
                    "template_name": template_name,
                    "step_name": step_name,
                    "execution_time": execution_time,
                    "result": result
                }
            )
        else:
            enhanced_logger.log_error(
                message=f"Template step '{step_name}' failed: {result.get('message', 'Unknown error')}",
                error_type="template_step_failure",
                context=context,
                extra_data={
                    "template_name": template_name,
                    "step_name": step_name,
                    "execution_time": execution_time,
                    "result": result
                }
            )
        
        return jsonify(result)
        
    except Exception as e:
        context = create_template_context(template_name, step_name if 'step_name' in locals() else None)
        enhanced_logger.log_error(
            message=f"Unexpected error executing template step: {str(e)}",
            error_type="template_execution_exception",
            context=context,
            extra_data={
                "template_name": template_name,
                "exception": str(e),
                "exception_type": type(e).__name__
            }
        )
        logger.error(f"Error executing template step: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error executing step: {str(e)}'
        })


def execute_step(ssh_connection, step, template_data, context: LogContext):
    """Execute a single template step with enhanced logging"""
    step_type = step.get('type')
    step_name = step.get('name')
    
    enhanced_logger.log_operation(
        message=f"Executing step '{step_name}' of type '{step_type}'",
        operation="step_execution_start",
        context=context,
        extra_data={
            "step_name": step_name,
            "step_type": step_type,
            "step_config": step
        }
    )
    
    try:
        if step_type == 'civitdl_install':
            enhanced_logger.log_operation(
                message="Installing CivitDL via template step",
                operation="civitdl_install_step",
                context=context,
                extra_data={"ssh_connection_info": ssh_connection.split('@')[-1] if '@' in ssh_connection else ssh_connection}
            )
            # Use existing setup CivitDL functionality
            result = execute_civitdl_setup(ssh_connection)
            
        elif step_type == 'set_ui_home':
            ui_home = step.get('path') or template_data.get('environment', {}).get('ui_home')
            if ui_home:
                enhanced_logger.log_operation(
                    message=f"Setting UI_HOME to: {ui_home}",
                    operation="set_ui_home_step",
                    context=context,
                    extra_data={"ui_home_path": ui_home}
                )
                result = execute_set_ui_home(ssh_connection, ui_home)
            else:
                enhanced_logger.log_error(
                    message="No UI home path specified in step or template environment",
                    error_type="missing_ui_home_path",
                    context=context,
                    extra_data={"step_config": step, "template_environment": template_data.get('environment', {})}
                )
                result = {
                    'success': False,
                    'message': 'No UI home path specified in step or template environment'
                }
        
        elif step_type == 'git_clone':
            repository = step.get('repository')
            destination = step.get('destination')
            if repository and destination:
                enhanced_logger.log_operation(
                    message=f"Cloning repository {repository} to {destination}",
                    operation="git_clone_step",
                    context=context,
                    extra_data={"repository": repository, "destination": destination}
                )
                result = execute_git_clone(ssh_connection, repository, destination)
            else:
                enhanced_logger.log_error(
                    message="Repository and destination are required for git_clone step",
                    error_type="missing_git_clone_params",
                    context=context,
                    extra_data={"repository": repository, "destination": destination, "step_config": step}
                )
                result = {
                    'success': False,
                    'message': 'Repository and destination are required for git_clone step'
                }
        
        elif step_type == 'python_venv':
            venv_path = step.get('path') or template_data.get('environment', {}).get('python_venv')
            if venv_path:
                enhanced_logger.log_operation(
                    message=f"Setting up Python virtual environment at: {venv_path}",
                    operation="python_venv_step",
                    context=context,
                    extra_data={"venv_path": venv_path}
                )
                result = execute_python_venv_setup(ssh_connection, venv_path)
            else:
                enhanced_logger.log_error(
                    message="No Python venv path specified in step or template environment",
                    error_type="missing_venv_path",
                    context=context,
                    extra_data={"step_config": step, "template_environment": template_data.get('environment', {})}
                )
                result = {
                    'success': False,
                    'message': 'No Python venv path specified in step or template environment'
                }
        
        else:
            enhanced_logger.log_error(
                message=f"Unknown step type: {step_type}",
                error_type="unknown_step_type",
                context=context,
                extra_data={"step_type": step_type, "step_name": step_name, "step_config": step}
            )
            result = {
                'success': False,
                'message': f'Unknown step type: {step_type}'
            }
        
        # Log the step execution result
        if result.get('success'):
            enhanced_logger.log_operation(
                message=f"Step '{step_name}' completed successfully",
                operation="step_execution_success",
                context=context,
                extra_data={"step_name": step_name, "step_type": step_type, "result": result}
            )
        else:
            enhanced_logger.log_error(
                message=f"Step '{step_name}' failed: {result.get('message', 'Unknown error')}",
                error_type="step_execution_failure",
                context=context,
                extra_data={"step_name": step_name, "step_type": step_type, "result": result}
            )
        
        return result
            
    except Exception as e:
        enhanced_logger.log_error(
            message=f"Exception during step execution: {str(e)}",
            error_type="step_execution_exception",
            context=context,
            extra_data={
                "step_name": step_name,
                "step_type": step_type,
                "exception": str(e),
                "exception_type": type(e).__name__
            }
        )
        logger.error(f"Error executing step {step_name}: {str(e)}")
        return {
            'success': False,
            'message': f'Error executing {step_name}: {str(e)}'
        }


def execute_civitdl_setup(ssh_connection):
    """Execute CivitDL setup using existing functionality"""
    # This uses the existing setup-civitdl endpoint logic
    try:
        host, port = parse_ssh_connection(ssh_connection)
        if not host or not port:
            return {
                'success': False,
                'message': 'Invalid SSH connection string format'
            }
        
        # Use existing CivitDL setup logic
        cmd = f'''ssh -p {port} -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@{host} "
        set -e
        cd /workspace
        if [ ! -d civitdl ]; then
            git clone https://github.com/civitai/civitdl.git
        fi
        cd civitdl
        pip install -e .
        pip install requests tqdm
        echo 'CivitDL installation completed'
        "'''
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            return {
                'success': True,
                'message': 'CivitDL setup completed successfully',
                'output': result.stdout
            }
        else:
            return {
                'success': False,
                'message': f'CivitDL setup failed with return code {result.returncode}',
                'error': result.stderr
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Error during CivitDL setup: {str(e)}'
        }


def execute_set_ui_home(ssh_connection, ui_home_path):
    """Execute UI_HOME setup"""
    try:
        host, port = parse_ssh_connection(ssh_connection)
        if not host or not port:
            return {
                'success': False,
                'message': 'Invalid SSH connection string format'
            }
        
        cmd = f'''ssh -p {port} -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@{host} "
        echo 'export UI_HOME={ui_home_path}' >> ~/.bashrc
        export UI_HOME={ui_home_path}
        echo 'UI_HOME set to {ui_home_path}'
        "'''
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            return {
                'success': True,
                'message': f'UI_HOME set to {ui_home_path}',
                'output': result.stdout
            }
        else:
            return {
                'success': False,
                'message': f'Failed to set UI_HOME with return code {result.returncode}',
                'error': result.stderr
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Error setting UI_HOME: {str(e)}'
        }


def execute_git_clone(ssh_connection, repository, destination):
    """Execute git clone"""
    try:
        host, port = parse_ssh_connection(ssh_connection)
        if not host or not port:
            return {
                'success': False,
                'message': 'Invalid SSH connection string format'
            }
        
        cmd = f'''ssh -p {port} -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@{host} "
        set -e
        if [ ! -d '{destination}' ]; then
            git clone {repository} {destination}
            echo 'Repository cloned successfully to {destination}'
        else
            echo 'Repository already exists at {destination}'
        fi
        "'''
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            return {
                'success': True,
                'message': f'Repository cloned to {destination}',
                'output': result.stdout
            }
        else:
            return {
                'success': False,
                'message': f'Git clone failed with return code {result.returncode}',
                'error': result.stderr
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Error cloning repository: {str(e)}'
        }


def execute_python_venv_setup(ssh_connection, venv_path):
    """Execute Python virtual environment setup"""
    try:
        host, port = parse_ssh_connection(ssh_connection)
        if not host or not port:
            return {
                'success': False,
                'message': 'Invalid SSH connection string format'
            }
        
        cmd = f'''ssh -p {port} -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@{host} "
        set -e
        if [ ! -d '{venv_path}' ]; then
            python3 -m venv {venv_path}
            echo 'Python virtual environment created at {venv_path}'
        else
            echo 'Virtual environment already exists at {venv_path}'
        fi
        source {venv_path}/bin/activate
        pip install --upgrade pip
        echo 'Virtual environment setup completed'
        "'''
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
        
        if result.returncode == 0:
            return {
                'success': True,
                'message': f'Python virtual environment setup at {venv_path}',
                'output': result.stdout
            }
        else:
            return {
                'success': False,
                'message': f'Python venv setup failed with return code {result.returncode}',
                'error': result.stderr
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'Error setting up Python virtual environment: {str(e)}'
        }


if __name__ == '__main__':
    # Initialize log directories
    try:
        from ..utils.log_init import ensure_all_log_directories
        from ..utils.app_logging import log_startup
        ensure_all_log_directories()
        log_startup()
    except ImportError:
        from utils.log_init import ensure_all_log_directories
        from utils.app_logging import log_startup
        ensure_all_log_directories()
        log_startup()
    
    import sys
    port = int(sys.argv[1].replace('--port=', '').replace('--port', '')) if len(sys.argv) > 1 and '--port' in sys.argv[1] else 5000
    app.run(host='0.0.0.0', port=port, debug=False)