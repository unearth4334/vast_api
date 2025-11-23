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
import re
import json
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
    from .background_tasks import get_task_manager
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
    from background_tasks import get_task_manager
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
        r"/resources/*": {"origins": ALLOWED_ORIGINS},
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


# Constants for custom nodes installation
PROGRESS_FILE_TEMPLATE = '/tmp/custom_nodes_progress_{task_id}.json'


def _get_progress_file_path(task_id: str) -> str:
    """Get the progress file path for a given task ID"""
    return PROGRESS_FILE_TEMPLATE.format(task_id=task_id)


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
            "test_ssh_start",
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
                "test_ssh_success",
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


@app.route('/ssh/test', methods=['POST', 'OPTIONS'])
def ssh_test():
    """Test SSH connection with provided connection string"""
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
                'message': f'Invalid SSH connection format: {str(e)}'
            })
        
        logger.info(f"Testing SSH connection to {ssh_host}:{ssh_port}")
        
        # Test basic SSH connectivity
        ssh_key = '/root/.ssh/id_ed25519'
        ssh_cmd = [
            'ssh',
            '-p', str(ssh_port),
            '-i', ssh_key,
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
            '-o', 'IdentitiesOnly=yes',
            f'root@{ssh_host}',
            'echo "SSH connection successful"'
        ]
        
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            logger.info(f"SSH connection test successful for {ssh_host}:{ssh_port}")
            return jsonify({
                'success': True,
                'message': 'SSH connection successful',
                'output': result.stdout
            })
        else:
            # Check if the error is due to host key verification failure
            stderr = result.stderr.lower()
            if 'host key verification failed' in stderr or 'no matching host key type found' in stderr or 'connection refused' not in stderr and result.returncode == 255:
                logger.warning(f"Host key verification needed for {ssh_host}:{ssh_port}")
                return jsonify({
                    'success': False,
                    'message': 'Host key verification required',
                    'error': result.stderr,
                    'host_verification_needed': True,
                    'host': ssh_host,
                    'port': ssh_port
                })
            
            logger.error(f"SSH connection test failed for {ssh_host}:{ssh_port}: {result.stderr}")
            return jsonify({
                'success': False,
                'message': 'SSH connection failed',
                'error': result.stderr
            })
            
    except subprocess.TimeoutExpired:
        logger.error(f"SSH connection test timed out")
        return jsonify({
            'success': False,
            'message': 'SSH connection test timed out'
        })
    except Exception as e:
        logger.error(f"SSH test error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'SSH test error: {str(e)}'
        })


@app.route('/ssh/verify-host', methods=['POST', 'OPTIONS'])
def ssh_verify_host():
    """Get host key fingerprint and optionally add to known_hosts"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json() if request.is_json else {}
        ssh_connection = data.get('ssh_connection')
        accept = data.get('accept', False)  # True to add host key to known_hosts
        
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
                'message': f'Invalid SSH connection format: {str(e)}'
            })
        
        logger.info(f"Verifying host key for {ssh_host}:{ssh_port}")
        
        # Get host key fingerprint using ssh-keyscan
        keyscan_cmd = ['ssh-keyscan', '-p', str(ssh_port), ssh_host]
        keyscan_result = subprocess.run(keyscan_cmd, capture_output=True, text=True, timeout=10)
        
        if keyscan_result.returncode != 0 or not keyscan_result.stdout:
            logger.error(f"Failed to get host key: {keyscan_result.stderr}")
            return jsonify({
                'success': False,
                'message': 'Failed to retrieve host key',
                'error': keyscan_result.stderr
            })
        
        # Parse the host key to get fingerprint
        host_keys = [line for line in keyscan_result.stdout.split('\n') if line and not line.startswith('#')]
        if not host_keys:
            return jsonify({
                'success': False,
                'message': 'No host keys found'
            })
        
        # Get fingerprint using ssh-keygen
        fingerprints = []
        for host_key in host_keys:
            # Write key to temp file for fingerprint calculation
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pub') as f:
                f.write(host_key)
                temp_key_file = f.name
            
            try:
                fingerprint_cmd = ['ssh-keygen', '-lf', temp_key_file]
                fp_result = subprocess.run(fingerprint_cmd, capture_output=True, text=True)
                if fp_result.returncode == 0:
                    fingerprints.append(fp_result.stdout.strip())
            finally:
                os.unlink(temp_key_file)
        
        # If accept=True, add host key to known_hosts
        if accept:
            known_hosts_file = '/root/.ssh/known_hosts'
            
            # Ensure .ssh directory exists
            os.makedirs('/root/.ssh', mode=0o700, exist_ok=True)
            
            # Check if host key already exists
            check_cmd = ['ssh-keygen', '-F', f'[{ssh_host}]:{ssh_port}', '-f', known_hosts_file]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if check_result.returncode == 0:
                # Host key already exists
                logger.info(f"Host key for {ssh_host}:{ssh_port} already in known_hosts")
                return jsonify({
                    'success': True,
                    'message': 'Host key already trusted',
                    'fingerprints': fingerprints,
                    'already_known': True
                })
            
            # Add the host keys to known_hosts
            # Format: [host]:port key-type key-data
            with open(known_hosts_file, 'a') as f:
                for host_key in host_keys:
                    # Reformat to include port in brackets
                    parts = host_key.split(' ', 2)
                    if len(parts) >= 3:
                        # Format: [host]:port ssh-rsa/ed25519 key
                        formatted_key = f"[{ssh_host}]:{ssh_port} {parts[1]} {parts[2]}\n"
                        f.write(formatted_key)
            
            logger.info(f"Added host key for {ssh_host}:{ssh_port} to known_hosts")
            return jsonify({
                'success': True,
                'message': 'Host key added to known_hosts',
                'fingerprints': fingerprints,
                'added': True
            })
        else:
            # Just return fingerprints for user confirmation
            return jsonify({
                'success': True,
                'message': 'Host key retrieved',
                'host': ssh_host,
                'port': ssh_port,
                'fingerprints': fingerprints,
                'needs_confirmation': True
            })
            
    except subprocess.TimeoutExpired:
        logger.error(f"Host key verification timed out")
        return jsonify({
            'success': False,
            'message': 'Host key verification timed out'
        })
    except Exception as e:
        logger.error(f"Host verification error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Host verification error: {str(e)}'
        })


@app.route('/ssh/get-ui-home', methods=['POST', 'OPTIONS'])
def ssh_get_ui_home():
    """Get UI_HOME value from remote instance"""
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
                'message': f'Invalid SSH connection format: {str(e)}'
            })
        
        logger.info(f"Getting UI_HOME from {ssh_host}:{ssh_port}")
        
        # Get UI_HOME from remote instance
        ssh_key = '/root/.ssh/id_ed25519'
        ssh_cmd = [
            'ssh',
            '-p', str(ssh_port),
            '-i', ssh_key,
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
            '-o', 'IdentitiesOnly=yes',
            f'root@{ssh_host}',
            'source /etc/environment 2>/dev/null || true; echo "${UI_HOME:-Not set}"'
        ]
        
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            ui_home = result.stdout.strip()
            logger.info(f"UI_HOME retrieved: {ui_home}")
            return jsonify({
                'success': True,
                'message': 'UI_HOME retrieved successfully',
                'ui_home': ui_home,
                'output': result.stdout
            })
        else:
            logger.error(f"Failed to get UI_HOME from {ssh_host}:{ssh_port}: {result.stderr}")
            return jsonify({
                'success': False,
                'message': 'Failed to get UI_HOME',
                'error': result.stderr
            })
            
    except subprocess.TimeoutExpired:
        logger.error(f"Get UI_HOME timed out")
        return jsonify({
            'success': False,
            'message': 'Get UI_HOME request timed out'
        })
    except Exception as e:
        logger.error(f"Get UI_HOME error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Get UI_HOME error: {str(e)}'
        })


@app.route('/ssh/set-ui-home', methods=['POST', 'OPTIONS'])
def ssh_set_ui_home():
    """Set UI_HOME value on remote instance"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json() if request.is_json else {}
        ssh_connection = data.get('ssh_connection')
        ui_home = data.get('ui_home', '/workspace/ComfyUI')
        
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
                'message': f'Invalid SSH connection format: {str(e)}'
            })
        
        logger.info(f"Setting UI_HOME={ui_home} on {ssh_host}:{ssh_port}")
        
        # Set UI_HOME on remote instance
        ssh_key = '/root/.ssh/id_ed25519'
        ssh_cmd = [
            'ssh',
            '-p', str(ssh_port),
            '-i', ssh_key,
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
            '-o', 'IdentitiesOnly=yes',
            f'root@{ssh_host}',
            f'echo "UI_HOME={ui_home}" | sudo tee -a /etc/environment && source /etc/environment && echo "UI_HOME set to: $UI_HOME"'
        ]
        
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            logger.info(f"UI_HOME set successfully on {ssh_host}:{ssh_port}")
            return jsonify({
                'success': True,
                'message': 'UI_HOME set successfully',
                'output': result.stdout
            })
        else:
            logger.error(f"Failed to set UI_HOME on {ssh_host}:{ssh_port}: {result.stderr}")
            return jsonify({
                'success': False,
                'message': 'Failed to set UI_HOME',
                'error': result.stderr
            })
            
    except subprocess.TimeoutExpired:
        logger.error(f"Set UI_HOME timed out")
        return jsonify({
            'success': False,
            'message': 'Set UI_HOME request timed out'
        })
    except Exception as e:
        logger.error(f"Set UI_HOME error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Set UI_HOME error: {str(e)}'
        })


@app.route('/ssh/setup-civitdl', methods=['POST', 'OPTIONS'])
def ssh_setup_civitdl():
    """Install and configure CivitDL on remote instance"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json() if request.is_json else {}
        ssh_connection = data.get('ssh_connection')
        
        # Try to get API key from request, or load from api_key.txt
        api_key = data.get('api_key', '')
        if not api_key:
            try:
                with open('/app/api_key.txt', 'r') as f:
                    for line in f:
                        if line.startswith('civitdl:'):
                            api_key = line.split(':', 1)[1].strip()
                            logger.info("Loaded CivitAI API key from api_key.txt")
                            break
            except Exception as e:
                logger.warning(f"Could not read API key from file: {e}")
        
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
                'message': f'Invalid SSH connection format: {str(e)}'
            })
        
        logger.info(f"Setting up CivitDL on {ssh_host}:{ssh_port}")
        
        ssh_key = '/root/.ssh/id_ed25519'
        
        # Phase 1: Install CivitDL package
        logger.info(f"Installing CivitDL package...")
        install_cmd = [
            'ssh',
            '-p', str(ssh_port),
            '-i', ssh_key,
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
            '-o', 'IdentitiesOnly=yes',
            f'root@{ssh_host}',
            '/venv/main/bin/python -m pip install --root-user-action=ignore civitdl'
        ]
        
        install_result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=60)
        
        if install_result.returncode != 0:
            logger.error(f"CivitDL installation failed: {install_result.stderr}")
            return jsonify({
                'success': False,
                'message': 'CivitDL installation failed',
                'error': install_result.stderr,
                'phase': 'install'
            })
        
        logger.info(f"CivitDL installed successfully")
        
        # Phase 2: Configure API key (if provided)
        if api_key:
            logger.info(f"Configuring CivitDL API key...")
            config_cmd = [
                'ssh',
                '-p', str(ssh_port),
                '-i', ssh_key,
                '-o', 'ConnectTimeout=10',
                '-o', 'StrictHostKeyChecking=yes',
                '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
                '-o', 'IdentitiesOnly=yes',
                f'root@{ssh_host}',
                f'echo "{api_key}" | /venv/main/bin/civitconfig default --api-key'
            ]
            
            config_result = subprocess.run(config_cmd, capture_output=True, text=True, timeout=15)
            
            if config_result.returncode != 0:
                logger.warning(f"API key configuration failed: {config_result.stderr}")
                return jsonify({
                    'success': True,  # Installation succeeded
                    'warning': True,
                    'message': 'CivitDL installed but API key configuration failed',
                    'error': config_result.stderr,
                    'phase': 'config'
                })
            
            logger.info(f"API key configured successfully")
        
        # Phase 3: Verify installation
        logger.info(f"Verifying CivitDL installation...")
        verify_cmd = [
            'ssh',
            '-p', str(ssh_port),
            '-i', ssh_key,
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
            '-o', 'IdentitiesOnly=yes',
            f'root@{ssh_host}',
            '/venv/main/bin/civitdl --version 2>&1 || /venv/main/bin/python -c "import civitdl; print(\'civitdl module imported successfully\')"'
        ]
        
        verify_result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=15)
        
        if verify_result.returncode != 0:
            logger.error(f"CivitDL verification failed: {verify_result.stderr}")
            return jsonify({
                'success': False,
                'message': 'CivitDL verification failed',
                'error': verify_result.stderr,
                'phase': 'verify'
            })
        
        output = verify_result.stdout.strip()
        # Extract version if available, otherwise just confirm it's installed
        if 'civitdl module imported successfully' in output:
            version = 'installed'
        else:
            version = output.split('\n')[0] if output else 'installed'
        
        logger.info(f"CivitDL setup completed successfully. Version: {version}")
        
        return jsonify({
            'success': True,
            'message': 'CivitDL installed and configured successfully',
            'version': version,
            'api_key_configured': bool(api_key)
        })
            
    except subprocess.TimeoutExpired:
        logger.error(f"CivitDL setup timed out")
        return jsonify({
            'success': False,
            'message': 'CivitDL setup timed out'
        })
    except Exception as e:
        logger.error(f"CivitDL setup error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'CivitDL setup error: {str(e)}'
        })


@app.route('/ssh/test-civitdl', methods=['POST', 'OPTIONS'])
def ssh_test_civitdl():
    """Test CivitDL installation on remote instance"""
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
        
        ssh_key = '/root/.ssh/id_ed25519'
        logger.info(f"Testing CivitDL on {ssh_host}:{ssh_port}")
        
        # Test 1: Check CLI is functional
        logger.info(f"Test 1: Checking CivitDL CLI...")
        cli_test_cmd = [
            'ssh',
            '-p', str(ssh_port),
            '-i', ssh_key,
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
            '-o', 'IdentitiesOnly=yes',
            f'root@{ssh_host}',
            '/venv/main/bin/civitdl --help'
        ]
        
        cli_result = subprocess.run(cli_test_cmd, capture_output=True, text=True, timeout=15)
        
        if cli_result.returncode != 0:
            logger.error(f"CivitDL CLI test failed: {cli_result.stderr}")
            return jsonify({
                'success': False,
                'message': 'CivitDL CLI test failed',
                'error': cli_result.stderr,
                'tests': {
                    'cli': False,
                    'config': None,
                    'api': None
                }
            })
        
        logger.info(f"CivitDL CLI test passed")
        
        # Test 2: Check API key configuration
        logger.info(f"Test 2: Validating API configuration...")
        config_test_cmd = [
            'ssh',
            '-p', str(ssh_port),
            '-i', ssh_key,
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
            '-o', 'IdentitiesOnly=yes',
            f'root@{ssh_host}',
            '/venv/main/bin/civitconfig settings'
        ]
        
        config_result = subprocess.run(config_test_cmd, capture_output=True, text=True, timeout=15)
        
        # civitconfig settings often returns empty output even when configured
        # We'll validate by checking if we can read the config file directly
        api_key_valid = False
        if config_result.returncode == 0:
            output = config_result.stdout.strip()
            logger.info(f"civitconfig settings output: {repr(output)}")
            
            # If output is not empty and looks like config, that's good
            if output and len(output) > 10:
                api_key_valid = True
                logger.info(f"API key validation: valid (config output present)")
            else:
                # Empty output - check the config file directly
                logger.info(f"civitconfig returned empty, checking config file directly...")
                check_config_cmd = [
                    'ssh',
                    '-p', str(ssh_port),
                    '-i', ssh_key,
                    '-o', 'ConnectTimeout=10',
                    '-o', 'StrictHostKeyChecking=yes',
                    '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
                    '-o', 'IdentitiesOnly=yes',
                    f'root@{ssh_host}',
                    'cat ~/.config/civitdl/config.json 2>/dev/null || echo "no config"'
                ]
                config_file_result = subprocess.run(check_config_cmd, capture_output=True, text=True, timeout=10)
                config_file_content = config_file_result.stdout.strip()
                logger.info(f"Config file content: {repr(config_file_content[:200])}")
                
                # Check if config file exists and has api_key
                if config_file_content and 'no config' not in config_file_content and 'api_key' in config_file_content:
                    api_key_valid = True
                    logger.info(f"API key validation: valid (config file present with api_key)")
                else:
                    logger.info(f"API key validation: not set or invalid")
        else:
            logger.warning(f"Config check stderr: {config_result.stderr}")
        
        # Test 3: Test API connectivity
        logger.info(f"Test 3: Testing API connectivity...")
        api_test_cmd = [
            'ssh',
            '-p', str(ssh_port),
            '-i', ssh_key,
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
            '-o', 'IdentitiesOnly=yes',
            f'root@{ssh_host}',
            '/venv/main/bin/python -c "import requests; r = requests.get(\'https://civitai.com/api/v1/models\', timeout=10); print(r.status_code)"'
        ]
        
        api_result = subprocess.run(api_test_cmd, capture_output=True, text=True, timeout=20)
        
        api_reachable = False
        api_status = None
        if api_result.returncode == 0:
            try:
                api_status = int(api_result.stdout.strip())
                api_reachable = api_status == 200
                logger.info(f"API connectivity test: status {api_status}")
            except ValueError:
                logger.warning(f"Could not parse API status: {api_result.stdout}")
        else:
            logger.warning(f"API test failed: {api_result.stderr}")
        
        # CLI and config tests must pass, API test is optional (can be slow/rate-limited)
        all_passed = cli_result.returncode == 0 and api_key_valid
        has_warning = not api_reachable
        
        logger.info(f"CivitDL tests completed. CLI: {cli_result.returncode == 0}, Config: {api_key_valid}, API: {api_reachable}")
        
        return jsonify({
            'success': all_passed,
            'message': 'CivitDL tests passed' if all_passed and not has_warning else 
                      'CivitDL tests passed (API test skipped due to timeout)' if all_passed and has_warning else
                      'Some CivitDL tests failed',
            'has_warning': has_warning,
            'tests': {
                'cli': cli_result.returncode == 0,
                'config': api_key_valid,
                'api': api_reachable
            },
            'api_status': api_status,
            'api_note': 'API connectivity test is optional and may timeout due to rate limiting' if not api_reachable else None
        })
    
    except subprocess.TimeoutExpired:
        logger.error("CivitDL test timed out")
        return jsonify({
            'success': False,
            'message': 'CivitDL test timed out'
        })
    except Exception as e:
        logger.error(f"Error testing CivitDL: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'CivitDL test error: {str(e)}'
        })


def _write_progress_to_remote(ssh_host, ssh_port, ssh_key, progress_file, progress_data):
    """Helper to write progress JSON to remote instance"""
    try:
        logger.debug(f"Writing progress to remote: {progress_data.get('current_node')} - {progress_data.get('processed')}/{progress_data.get('total_nodes')}")
        # Write to local temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
            json.dump(progress_data, tmp)
            tmp_path = tmp.name
        
        # SCP to remote
        scp_cmd = [
            'scp',
            '-P', str(ssh_port),
            '-i', ssh_key,
            '-o', 'ConnectTimeout=5',
            '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
            '-o', 'IdentitiesOnly=yes',
            tmp_path,
            f'root@{ssh_host}:{progress_file}'
        ]
        result = subprocess.run(scp_cmd, timeout=5, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.warning(f"SCP failed: {result.stderr}")
        else:
            logger.debug(f"Progress written successfully")
        
        # Clean up local temp file
        import os
        os.unlink(tmp_path)
    except Exception as e:
        logger.error(f"Failed to write progress: {e}", exc_info=True)


def _run_installation_background(task_id: str, ssh_connection: str, ui_home: str):
    """
    Background worker that runs custom nodes installation.
    Writes progress to remote file as installation proceeds.
    """
    try:
        ssh_host, ssh_port = _extract_host_port(ssh_connection)
    except ValueError as e:
        logger.error(f"Invalid SSH connection format: {e}")
        return
    
    ssh_key = '/root/.ssh/id_ed25519'
    progress_file = _get_progress_file_path(task_id)
    
    logger.info(f"Starting background installation for task {task_id} on {ssh_host}:{ssh_port}")
    
    try:
        # Write initial progress
        initial_progress = {
            'in_progress': True,
            'task_id': task_id,
            'total_nodes': 0,
            'processed': 0,
            'current_node': 'Initializing',
            'current_status': 'running',
            'successful': 0,
            'failed': 0,
            'has_requirements': False
        }
        _write_progress_to_remote(ssh_host, ssh_port, ssh_key, progress_file, initial_progress)
        
        # Check if ComfyUI-Auto_installer exists, clone if needed
        check_cmd = [
            'ssh',
            '-p', str(ssh_port),
            '-i', ssh_key,
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
            '-o', 'IdentitiesOnly=yes',
            f'root@{ssh_host}',
            'test -d /workspace/ComfyUI-Auto_installer'
        ]
        
        check_result = subprocess.run(check_cmd, timeout=10, capture_output=True)
        
        if check_result.returncode != 0:
            logger.info("ComfyUI-Auto_installer not found, cloning repository...")
            
            # Update progress
            clone_progress = initial_progress.copy()
            clone_progress['current_node'] = 'Cloning Auto-installer'
            _write_progress_to_remote(ssh_host, ssh_port, ssh_key, progress_file, clone_progress)
            
            clone_cmd = [
                'ssh',
                '-p', str(ssh_port),
                '-i', ssh_key,
                '-o', 'ConnectTimeout=10',
                '-o', 'StrictHostKeyChecking=yes',
                '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
                '-o', 'IdentitiesOnly=yes',
                f'root@{ssh_host}',
                'cd /workspace && git clone https://github.com/unearth4334/ComfyUI-Auto_installer'
            ]
            
            clone_result = subprocess.run(clone_cmd, timeout=300, capture_output=True, text=True)
            
            if clone_result.returncode != 0:
                logger.error(f"Failed to clone ComfyUI-Auto_installer: {clone_result.stderr}")
                error_progress = {
                    'in_progress': False,
                    'task_id': task_id,
                    'error': f'Failed to clone ComfyUI-Auto_installer: {clone_result.stderr}',
                    'completed': False
                }
                _write_progress_to_remote(ssh_host, ssh_port, ssh_key, progress_file, error_progress)
                return
            
            logger.info("ComfyUI-Auto_installer cloned successfully")
        else:
            logger.info("ComfyUI-Auto_installer already exists")
        
        # Run the custom nodes installer
        install_cmd = [
            'ssh',
            '-p', str(ssh_port),
            '-i', ssh_key,
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
            '-o', 'IdentitiesOnly=yes',
            f'root@{ssh_host}',
            f'source /etc/environment 2>/dev/null; cd /workspace/ComfyUI-Auto_installer/scripts && ./install-custom-nodes.sh {ui_home} --venv-path /venv/main/bin/python 2>&1'
        ]
        
        # Use Popen for real-time output streaming
        process = subprocess.Popen(
            install_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Parse output to track progress
        total_nodes = 0
        processed_nodes = 0
        successful_clones = 0
        failed_clones = 0
        successful_requirements = 0
        failed_requirements = 0
        current_node = None
        current_node_has_requirements = False
        output_lines = []
        
        for line in process.stdout:
            output_lines.append(line.rstrip())
            logger.debug(f"Install output: {line.rstrip()}")
            
            # Parse progress: [X/Y] Processing custom node: NodeName
            if 'Processing custom node:' in line:
                match = re.search(r'\[(\d+)/(\d+)\]\s+Processing custom node:\s+(.+)', line)
                if match:
                    processed_nodes = int(match.group(1))
                    total_nodes = int(match.group(2))
                    current_node = match.group(3).strip()
                    current_node_has_requirements = False
                    logger.info(f"Processing node {processed_nodes}/{total_nodes}: {current_node}")
                    
                    # Write progress to file
                    progress_data = {
                        'in_progress': True,
                        'task_id': task_id,
                        'total_nodes': total_nodes,
                        'processed': processed_nodes,
                        'current_node': current_node,
                        'current_status': 'running',
                        'successful': successful_clones,
                        'failed': failed_clones,
                        'has_requirements': False
                    }
                    _write_progress_to_remote(ssh_host, ssh_port, ssh_key, progress_file, progress_data)
            
            # Detect when installing requirements
            elif 'Installing requirements' in line and current_node:
                current_node_has_requirements = True
                progress_data = {
                    'in_progress': True,
                    'task_id': task_id,
                    'total_nodes': total_nodes,
                    'processed': processed_nodes,
                    'current_node': current_node,
                    'current_status': 'running',
                    'successful': successful_clones,
                    'failed': failed_clones,
                    'has_requirements': True,
                    'requirements_status': 'running'
                }
                _write_progress_to_remote(ssh_host, ssh_port, ssh_key, progress_file, progress_data)
            
            # Track successes and failures
            elif 'Successfully cloned' in line:
                successful_clones += 1
                if current_node:
                    progress_data = {
                        'in_progress': True,
                        'task_id': task_id,
                        'total_nodes': total_nodes,
                        'processed': processed_nodes,
                        'current_node': current_node,
                        'current_status': 'success',
                        'successful': successful_clones,
                        'failed': failed_clones,
                        'has_requirements': current_node_has_requirements,
                        'requirements_status': 'pending' if current_node_has_requirements else None
                    }
                    _write_progress_to_remote(ssh_host, ssh_port, ssh_key, progress_file, progress_data)
                        
            elif 'Failed to clone' in line:
                failed_clones += 1
                if current_node:
                    progress_data = {
                        'in_progress': True,
                        'task_id': task_id,
                        'total_nodes': total_nodes,
                        'processed': processed_nodes,
                        'current_node': current_node,
                        'current_status': 'failed',
                        'successful': successful_clones,
                        'failed': failed_clones,
                        'has_requirements': False
                    }
                    _write_progress_to_remote(ssh_host, ssh_port, ssh_key, progress_file, progress_data)
            elif 'Successfully installed requirements' in line:
                successful_requirements += 1
                if current_node and current_node_has_requirements:
                    progress_data = {
                        'in_progress': True,
                        'task_id': task_id,
                        'total_nodes': total_nodes,
                        'processed': processed_nodes,
                        'current_node': current_node,
                        'current_status': 'success',
                        'successful': successful_clones,
                        'failed': failed_clones,
                        'has_requirements': True,
                        'requirements_status': 'success'
                    }
                    _write_progress_to_remote(ssh_host, ssh_port, ssh_key, progress_file, progress_data)
            elif 'Failed to install requirements' in line:
                failed_requirements += 1
                if current_node and current_node_has_requirements:
                    progress_data = {
                        'in_progress': True,
                        'task_id': task_id,
                        'total_nodes': total_nodes,
                        'processed': processed_nodes,
                        'current_node': current_node,
                        'current_status': 'success',  # Node cloned but reqs failed
                        'successful': successful_clones,
                        'failed': failed_clones,
                        'has_requirements': True,
                        'requirements_status': 'failed'
                    }
                    _write_progress_to_remote(ssh_host, ssh_port, ssh_key, progress_file, progress_data)
        
        # Wait for process to complete
        return_code = process.wait(timeout=1800)  # 30 minute timeout
        
        # Write completion progress
        installation_succeeded = return_code == 0 or (failed_requirements > 0 and failed_clones == 0)
        
        completion_progress = {
            'in_progress': False,
            'task_id': task_id,
            'completed': True,
            'success': installation_succeeded,
            'total_nodes': total_nodes,
            'processed': processed_nodes,
            'successful_clones': successful_clones,
            'failed_clones': failed_clones,
            'successful_requirements': successful_requirements,
            'failed_requirements': failed_requirements,
            'return_code': return_code
        }
        _write_progress_to_remote(ssh_host, ssh_port, ssh_key, progress_file, completion_progress)
        
        logger.info(f"Installation task {task_id} completed. Success: {installation_succeeded}, " +
                   f"Processed: {processed_nodes}/{total_nodes}")
        
    except subprocess.TimeoutExpired:
        logger.error(f"Installation task {task_id} timed out")
        error_progress = {
            'in_progress': False,
            'task_id': task_id,
            'completed': False,
            'error': 'Installation timed out (exceeded 30 minutes)'
        }
        _write_progress_to_remote(ssh_host, ssh_port, ssh_key, progress_file, error_progress)
    except Exception as e:
        logger.error(f"Installation task {task_id} failed: {e}", exc_info=True)
        error_progress = {
            'in_progress': False,
            'task_id': task_id,
            'completed': False,
            'error': str(e)
        }
        _write_progress_to_remote(ssh_host, ssh_port, ssh_key, progress_file, error_progress)


@app.route('/ssh/install-custom-nodes', methods=['POST', 'OPTIONS'])
def ssh_install_custom_nodes():
    """Start custom nodes installation asynchronously and return task ID"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json() if request.is_json else {}
        ssh_connection = data.get('ssh_connection')
        ui_home = data.get('ui_home', '/workspace/ComfyUI')
        
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
                'message': f'Invalid SSH connection format: {str(e)}'
            })
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        logger.info(f"Starting async custom nodes installation with task_id: {task_id}")
        
        # Clear any existing progress files for this connection
        ssh_key = '/root/.ssh/id_ed25519'
        clear_progress_cmd = [
            'ssh',
            '-p', str(ssh_port),
            '-i', ssh_key,
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
            '-o', 'IdentitiesOnly=yes',
            f'root@{ssh_host}',
            f'rm -f /tmp/custom_nodes_progress_{task_id}.json'
        ]
        subprocess.run(clear_progress_cmd, timeout=10, capture_output=True)
        
        # Start installation in background
        task_manager = get_task_manager()
        try:
            task_manager.start_task(
                task_id,
                _run_installation_background,
                task_id,
                ssh_connection,
                ui_home
            )
        except ValueError as e:
            # Task already running
            return jsonify({
                'success': False,
                'message': str(e)
            }), 409
        
        # Return immediately with task ID
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Installation started in background'
        })
        
    except Exception as e:
        logger.error(f"Error starting custom nodes installation: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error starting installation: {str(e)}'
        })


@app.route('/ssh/install-custom-nodes/progress', methods=['POST', 'OPTIONS'])
def ssh_install_custom_nodes_progress():
    """Get real-time progress of custom nodes installation by task_id"""
    if request.method == 'OPTIONS':
        return handle_cors_preflight()
    
    try:
        data = request.get_json()
        ssh_connection = data.get('ssh_connection')
        task_id = data.get('task_id')
        
        if not ssh_connection:
            return jsonify({
                'success': False,
                'message': 'Missing ssh_connection parameter'
            }), 400
        
        if not task_id:
            return jsonify({
                'success': False,
                'message': 'Missing task_id parameter'
            }), 400
        
        # Parse SSH connection using the same helper function
        try:
            ssh_host, ssh_port = _extract_host_port(ssh_connection)
        except ValueError as e:
            return jsonify({
                'success': False,
                'message': f'Invalid SSH connection format: {str(e)}'
            }), 400
        
        # SSH key path
        ssh_key = '/root/.ssh/id_ed25519'
        
        # Read the progress file for this specific task_id
        progress_file = _get_progress_file_path(task_id)
        
        try:
            # Use subprocess SSH like all other operations in this file
            cmd = [
                'ssh',
                '-i', ssh_key,
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-p', str(ssh_port),
                ssh_connection,
                f"cat {progress_file} 2>/dev/null || echo '{{}}'"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            progress_json = result.stdout.strip()
            
            logger.debug(f"Progress file content for task {task_id}: {progress_json}")
            
            if not progress_json or progress_json == '{}':
                logger.debug(f"No progress found for task {task_id}")
                return jsonify({
                    'success': True,
                    'in_progress': False,
                    'task_id': task_id,
                    'message': 'No progress available for this task'
                })
            
            progress_data = json.loads(progress_json)
            logger.info(f"Returning progress for task {task_id}: {progress_data.get('current_node')} - {progress_data.get('processed')}/{progress_data.get('total_nodes')}")
            return jsonify({
                'success': True,
                **progress_data
            })
            
        except Exception as e:
            logger.error(f"Error reading progress for task {task_id}: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error reading progress: {str(e)}'
            })
            
    except Exception as e:
        logger.error(f"Error in progress endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error in progress endpoint: {str(e)}'
        })


@app.route('/ssh/verify-dependencies', methods=['POST', 'OPTIONS'])
def ssh_verify_dependencies():
    """Verify and install missing Python dependencies for custom nodes"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json() if request.is_json else {}
        ssh_connection = data.get('ssh_connection')
        ui_home = data.get('ui_home', '/workspace/ComfyUI')
        
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
                'message': f'Invalid SSH connection format: {str(e)}'
            })
        
        logger.info(f"Verifying dependencies on {ssh_host}:{ssh_port}")
        
        ssh_key = '/root/.ssh/id_ed25519'
        
        # Check ComfyUI logs for import failures
        check_log_cmd = [
            'ssh',
            '-p', str(ssh_port),
            '-i', ssh_key,
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
            '-o', 'IdentitiesOnly=yes',
            f'root@{ssh_host}',
            'tail -500 /var/log/portal/comfyui.log 2>/dev/null | grep -E "ModuleNotFoundError|ImportError|IMPORT FAILED" || echo ""'
        ]
        
        result = subprocess.run(
            check_log_cmd,
            timeout=30,
            capture_output=True,
            text=True
        )
        
        import_errors = []
        missing_modules = set()
        failed_nodes = set()
        
        if result.returncode == 0 and result.stdout.strip():
            # Parse errors to find missing modules
            for line in result.stdout.split('\n'):
                if 'ModuleNotFoundError' in line or 'No module named' in line:
                    match = re.search(r"No module named ['\"]([^'\"]+)['\"]", line)
                    if match:
                        missing_modules.add(match.group(1))
                    import_errors.append(line.strip())
                elif 'IMPORT FAILED' in line:
                    match = re.search(r'IMPORT FAILED.*?([^/]+)$', line)
                    if match:
                        failed_nodes.add(match.group(1).strip())
                # Check for custom error messages like "Can't import color-matcher"
                elif "Can't import" in line or "did you install requirements" in line:
                    match = re.search(r"Can't import ([a-zA-Z0-9_-]+)", line)
                    if match:
                        missing_modules.add(match.group(1))
                    import_errors.append(line.strip())
        
        if not missing_modules:
            logger.info("No missing dependencies found")
            return jsonify({
                'success': True,
                'message': 'All dependencies are satisfied',
                'missing_modules': [],
                'failed_nodes': list(failed_nodes),
                'installed': []
            })
        
        logger.info(f"Found {len(missing_modules)} missing modules: {missing_modules}")
        
        # Map of module import names to pip package names
        module_to_package = {
            'colour_matcher': 'color-matcher',
            'color_matcher': 'color-matcher',
        }
        
        # Try to install missing modules
        installed_modules = []
        failed_installs = []
        
        for module in missing_modules:
            # Convert module name to package name if needed
            package_name = module_to_package.get(module, module)
            logger.info(f"Installing missing module: {module} (package: {package_name})")
            
            install_cmd = [
                'ssh',
                '-p', str(ssh_port),
                '-i', ssh_key,
                '-o', 'ConnectTimeout=10',
                '-o', 'StrictHostKeyChecking=yes',
                '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
                '-o', 'IdentitiesOnly=yes',
                f'root@{ssh_host}',
                f'source /venv/main/bin/activate && pip install {package_name}'
            ]
            
            install_result = subprocess.run(
                install_cmd,
                timeout=120,
                capture_output=True,
                text=True
            )
            
            if install_result.returncode == 0:
                installed_modules.append(package_name)
                logger.info(f"Successfully installed {package_name}")
            else:
                failed_installs.append(package_name)
                logger.error(f"Failed to install {package_name}: {install_result.stderr}")
        
        # Restart ComfyUI to load the new dependencies
        if installed_modules:
            logger.info("Restarting ComfyUI to load new dependencies")
            restart_cmd = [
                'ssh',
                '-p', str(ssh_port),
                '-i', ssh_key,
                '-o', 'ConnectTimeout=10',
                '-o', 'StrictHostKeyChecking=yes',
                '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
                '-o', 'IdentitiesOnly=yes',
                f'root@{ssh_host}',
                'supervisorctl restart comfyui'
            ]
            
            subprocess.run(
                restart_cmd,
                timeout=30,
                capture_output=True,
                text=True
            )
            
            # Wait for ComfyUI to start
            import time
            time.sleep(10)
        
        success = len(failed_installs) == 0
        message = f"Installed {len(installed_modules)} missing dependencies" if success else f"Installed {len(installed_modules)}, failed {len(failed_installs)}"
        
        return jsonify({
            'success': success,
            'message': message,
            'missing_modules': list(missing_modules),
            'installed': installed_modules,
            'failed': failed_installs,
            'failed_nodes': list(failed_nodes)
        })
        
    except subprocess.TimeoutExpired:
        logger.error("Dependency verification timed out")
        return jsonify({
            'success': False,
            'message': 'Dependency verification timed out'
        })
    except Exception as e:
        logger.error(f"Dependency verification error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Dependency verification error: {str(e)}'
        })


@app.route('/ssh/reboot-instance', methods=['POST', 'OPTIONS'])
def ssh_reboot_instance():
    """Reboot a VastAI instance using the VastAI API"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json() if request.is_json else {}
        instance_id = data.get('instance_id')
        
        if not instance_id:
            return jsonify({
                'success': False,
                'message': 'Instance ID is required'
            })
        
        logger.info(f"Rebooting VastAI instance {instance_id}")
        
        # Import VastAI API function
        from ..utils.vastai_api import reboot_instance
        from ..utils.config_loader import load_api_key
        
        # Load API key
        api_key = load_api_key()
        if not api_key:
            return jsonify({
                'success': False,
                'message': 'VastAI API key not found'
            })
        
        # Call the VastAI API to reboot the instance
        result = reboot_instance(api_key, instance_id)
        
        if result.get('success'):
            logger.info(f"Successfully initiated reboot for instance {instance_id}")
            return jsonify({
                'success': True,
                'message': f'Instance {instance_id} is rebooting',
                'instance_id': instance_id
            })
        else:
            logger.error(f"Failed to reboot instance {instance_id}: {result}")
            return jsonify({
                'success': False,
                'message': 'Failed to initiate instance reboot',
                'error': result
            })
            
    except Exception as e:
        logger.error(f"Reboot instance error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Reboot instance error: {str(e)}'
        })


# --- Progress and Logging Routes ---

@app.route('/sync/progress/<sync_id>')
def get_sync_progress_route(sync_id):
    """Get progress for a specific sync operation"""
    logger.debug(f"Progress requested for sync_id: {sync_id}")
    result = get_sync_progress(sync_id)
    logger.debug(f"Progress result: {result}")
    return jsonify(result)


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
    # Check if this is a health check request (based on User-Agent)
    user_agent = request.headers.get('User-Agent', '')
    is_health_check = 'curl' in user_agent.lower()
    
    if is_health_check:
        # Return static status for health checks to avoid VastAI API calls
        vastai_status = {
            'available': False,
            'message': 'VastAI status not checked during health check'
        }
    else:
        # For web UI requests, get actual VastAI status
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
            enhanced_logger.log_error(
                "UI_HOME read failed - no SSH connection string provided",
                "validation_error",
                context=LogContext(
                    operation_id=f"get_ui_home_{int(time.time())}",
                    user_agent="vast_api/1.0 (get_ui_home)",
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
                f"UI_HOME read failed - invalid SSH connection format: {str(e)}",
                "validation_error",
                context=LogContext(
                    operation_id=f"get_ui_home_{int(time.time())}",
                    user_agent="vast_api/1.0 (get_ui_home)",
                    session_id=f"session_{int(time.time())}",
                    ip_address=request.remote_addr or "localhost"
                )
            )
            return jsonify({
                'success': False,
                'message': str(e)
            })
        
        enhanced_logger.log_operation(
            f"Reading UI_HOME from {ssh_host}:{ssh_port}",
            "get_ui_home_start",
            context=LogContext(
                operation_id=f"get_ui_home_{int(time.time())}",
                user_agent="vast_api/1.0 (get_ui_home)",
                session_id=f"session_{int(time.time())}",
                ip_address=request.remote_addr or "localhost"
            )
        )
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
            enhanced_logger.log_operation(
                f"✅ Successfully read UI_HOME from {ssh_host}:{ssh_port} - {ui_home if ui_home else 'Not set'}",
                "get_ui_home_success",
                context=LogContext(
                    operation_id=f"get_ui_home_{int(time.time())}",
                    user_agent="vast_api/1.0 (get_ui_home)",
                    session_id=f"session_{int(time.time())}",
                    ip_address=request.remote_addr or "localhost"
                )
            )
            return jsonify({
                'success': True,
                'ui_home': ui_home if ui_home else 'Not set',
                'output': result.stdout
            })
        else:
            enhanced_logger.log_error(
                f"❌ Failed to read UI_HOME from {ssh_host}:{ssh_port} - SSH command failed",
                "connection_error",
                context=LogContext(
                    operation_id=f"get_ui_home_{int(time.time())}",
                    user_agent="vast_api/1.0 (get_ui_home)",
                    session_id=f"session_{int(time.time())}",
                    ip_address=request.remote_addr or "localhost"
                )
            )
            logger.error(f"SSH command failed with return code {result.returncode}")
            logger.error(f"SSH stderr: {result.stderr}")
            return jsonify({
                'success': False,
                'message': 'Failed to get UI_HOME',
                'error': result.stderr,
                'return_code': result.returncode
            })
            
    except subprocess.TimeoutExpired:
        enhanced_logger.log_error(
            "UI_HOME read operation timed out",
            "timeout_error",
            context=LogContext(
                operation_id=f"get_ui_home_{int(time.time())}",
                user_agent="vast_api/1.0 (get_ui_home)",
                session_id=f"session_{int(time.time())}",
                ip_address=request.remote_addr or "localhost"
            )
        )
        return jsonify({
            'success': False,
            'message': 'SSH command timed out'
        })
    except Exception as e:
        enhanced_logger.log_error(
            f"UI_HOME read unexpected error: {str(e)}",
            "unexpected_error",
            context=LogContext(
                operation_id=f"get_ui_home_{int(time.time())}",
                user_agent="vast_api/1.0 (get_ui_home)",
                session_id=f"session_{int(time.time())}",
                ip_address=request.remote_addr or "localhost"
            )
        )
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
        
        # Try to read CivitDL API key
        try:
            civitdl_api_key = read_api_key_from_file(vendor="civitdl")
        except Exception as e:
            logger.warning(f"Could not read CivitDL API key: {str(e)}")
            civitdl_api_key = None
        
        # Setup commands for CivitDL using the ComfyUI virtual environment
        setup_commands = [
            '/venv/main/bin/python -m pip install --root-user-action=ignore civitdl',
            '/venv/main/bin/python -c "import civitdl; print(\\"CivitDL installed successfully\\")"'
        ]
        
        # Add API key configuration if available
        if civitdl_api_key:
            setup_commands.extend([
                f'echo "{civitdl_api_key}" | /venv/main/bin/civitconfig default --api-key',
                'echo "CivitDL API key configured successfully"'
            ])
        else:
            setup_commands.append('echo "Warning: No CivitDL API key found in api_key.txt"')
            
        setup_commands.append('echo "CivitDL setup complete"')
        
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


@app.route('/vastai/instances/<int:instance_id>', methods=['DELETE', 'OPTIONS'])
def destroy_vastai_instance(instance_id):
    """Destroy a VastAI instance"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        # Import the API function
        from ..utils.vastai_api import destroy_instance, VastAIAPIError
        
        # Read API key
        api_key = read_api_key_from_file()
        if not api_key:
            return jsonify({
                'success': False,
                'message': 'VastAI API key not found. Please check api_key.txt file.'
            })
        
        # Destroy the instance
        logger.info(f"Destroying VastAI instance {instance_id}")
        result = destroy_instance(api_key, instance_id)
        
        return jsonify({
            'success': True,
            'message': f'Instance {instance_id} destroyed successfully',
            'result': result
        })
        
    except VastAIAPIError as e:
        logger.error(f"VastAI API error destroying instance {instance_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'VastAI API error: {str(e)}'
        })
    except Exception as e:
        logger.error(f"Error destroying VastAI instance {instance_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error destroying instance: {str(e)}'
        })


# --- Configuration Routes ---

@app.route('/config/workflow', methods=['GET', 'OPTIONS'])
def get_workflow_config():
    """Get workflow configuration"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        config = load_config()
        workflow_step_delay = config.get('workflow_step_delay', 5)
        
        return jsonify({
            'success': True,
            'workflow_step_delay': workflow_step_delay
        })
    except Exception as e:
        logger.error(f"Error getting workflow config: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting workflow config: {str(e)}',
            'workflow_step_delay': 5  # Default fallback
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
    """Execute CivitDL setup with enhanced logging"""
    operation_id = f"civitdl_setup_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    session_id = f"session_{int(time.time())}"
    
    # Create log context for this operation
    context = LogContext(
        operation_id=operation_id,
        user_agent="vast_api/1.0 (template_civitdl_setup)",
        session_id=session_id,
        ip_address="localhost",
        template_name="comfyui"
    )
    
    try:
        # Log start of operation
        enhanced_logger.log_operation(
            "🎨 Starting CivitDL installation and setup",
            "template_civitdl_setup_start",
            context=context,
            extra_data={"ssh_connection": ssh_connection}
        )
        
        ssh_info = parse_ssh_connection(ssh_connection)
        if not ssh_info:
            enhanced_logger.log_error(
                "Invalid SSH connection string format for CivitDL setup",
                "ssh_parse_error",
                context=context,
                extra_data={"ssh_connection": ssh_connection}
            )
            return {
                'success': False,
                'message': 'Invalid SSH connection string format'
            }
        
        host, port, user = ssh_info['host'], ssh_info['port'], ssh_info.get('user', 'root')
        if not host or not port:
            enhanced_logger.log_error(
                "Missing host or port in SSH connection",
                "ssh_connection_incomplete",
                context=context,
                extra_data={"host": host, "port": port}
            )
            return {
                'success': False,
                'message': 'Invalid SSH connection string format'
            }
        
        # Log SSH connection attempt
        enhanced_logger.log_operation(
            f"🔌 Connecting to {user}@{host}:{port} for CivitDL setup",
            "ssh_connection_attempt",
            context=context,
            extra_data={"host": host, "port": port, "user": user}
        )
        
        # Use pip install for CivitDL setup as per template specification
        # First, try to read CivitDL API key
        try:
            civitdl_api_key = read_api_key_from_file(vendor="civitdl")
        except Exception as e:
            enhanced_logger.log_error(
                f"Could not read CivitDL API key: {str(e)}",
                "civitdl_api_key_read_error",
                context=context
            )
            civitdl_api_key = None
        
        # Build the installation command
        install_commands = [
            'echo "Installing CivitDL package using pip..."',
            '/venv/main/bin/python -m pip install --root-user-action=ignore civitdl',
            'echo "Verifying CivitDL installation..."',
            '/venv/main/bin/python -c "import civitdl; print(\\"CivitDL installed successfully\\")"'
        ]
        
        # Add API key configuration if available
        if civitdl_api_key:
            install_commands.extend([
                'echo "Configuring CivitDL API key..."',
                f'echo "{civitdl_api_key}" | /venv/main/bin/civitconfig default --api-key',
                'echo "API key configured successfully"'
            ])
        else:
            install_commands.append('echo "Warning: No CivitDL API key found in api_key.txt"')
        
        install_commands.append('echo "CivitDL installation completed successfully"')
        
        # Create a simple command string without complex escaping
        command_str = " && ".join(install_commands)
        
        cmd = [
            'ssh', '-p', str(port), 
            '-o', 'StrictHostKeyChecking=no', 
            '-o', 'ConnectTimeout=10',
            f'{user}@{host}',
            f'set -e && {command_str}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            # Log successful operation
            enhanced_logger.log_operation(
                "✅ CivitDL setup completed successfully",
                "template_civitdl_setup_success",
                context=context,
                extra_data={
                    "ssh_output": result.stdout.strip(),
                    "return_code": result.returncode
                }
            )
            return {
                'success': True,
                'message': 'CivitDL setup completed successfully',
                'output': result.stdout
            }
        else:
            # Log failure
            enhanced_logger.log_error(
                f"CivitDL setup failed: {result.stderr.strip()}",
                "template_civitdl_setup_failed",
                context=context,
                extra_data={
                    "return_code": result.returncode,
                    "stderr": result.stderr.strip(),
                    "stdout": result.stdout.strip()
                }
            )
            return {
                'success': False,
                'message': f'CivitDL setup failed with return code {result.returncode}',
                'error': result.stderr
            }
            
    except subprocess.TimeoutExpired:
        enhanced_logger.log_error(
            "CivitDL setup timed out",
            "ssh_timeout",
            context=context,
            extra_data={"timeout_seconds": 300}
        )
        return {
            'success': False,
            'message': 'SSH command timed out during CivitDL setup'
        }
    except Exception as e:
        enhanced_logger.log_error(
            f"Unexpected error during CivitDL setup: {str(e)}",
            "template_civitdl_setup_error",
            context=context,
            extra_data={"error_type": type(e).__name__, "error_message": str(e)}
        )
        return {
            'success': False,
            'message': f'Error during CivitDL setup: {str(e)}'
        }


def execute_set_ui_home(ssh_connection, ui_home_path):
    """Execute UI_HOME setup with enhanced logging"""
    operation_id = f"set_ui_home_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    session_id = f"session_{int(time.time())}"
    
    # Create log context for this operation
    context = LogContext(
        operation_id=operation_id,
        user_agent="vast_api/1.0 (template_set_ui_home)",
        session_id=session_id,
        ip_address="localhost",
        template_name="comfyui"
    )
    
    try:
        # Log start of operation
        enhanced_logger.log_operation(
            f"🏠 Setting UI_HOME to {ui_home_path}",
            "template_set_ui_home_start",
            context=context,
            extra_data={"ui_home_path": ui_home_path, "ssh_connection": ssh_connection}
        )
        
        ssh_info = parse_ssh_connection(ssh_connection)
        if not ssh_info:
            enhanced_logger.log_error(
                "Invalid SSH connection string format for UI_HOME setup",
                "ssh_parse_error",
                context=context,
                extra_data={"ssh_connection": ssh_connection}
            )
            return {
                'success': False,
                'message': 'Invalid SSH connection string format'
            }
        
        host, port, user = ssh_info['host'], ssh_info['port'], ssh_info.get('user', 'root')
        if not host or not port:
            enhanced_logger.log_error(
                "Missing host or port in SSH connection",
                "ssh_connection_incomplete",
                context=context,
                extra_data={"host": host, "port": port}
            )
            return {
                'success': False,
                'message': 'Invalid SSH connection string format'
            }
        
        # Log SSH connection attempt
        enhanced_logger.log_operation(
            f"🔌 Connecting to {user}@{host}:{port} to set UI_HOME",
            "ssh_connection_attempt",
            context=context,
            extra_data={"host": host, "port": port, "user": user}
        )
        
        # Build SSH command with proper escaping
        cmd = f'''ssh -p {port} -o StrictHostKeyChecking=no -o ConnectTimeout=10 {user}@{host} "
        echo 'export UI_HOME={ui_home_path}' >> ~/.bashrc && 
        export UI_HOME={ui_home_path} && 
        echo 'UI_HOME successfully set to {ui_home_path}'"'''
        
        # Execute SSH command
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # Log successful operation
            enhanced_logger.log_operation(
                f"✅ UI_HOME successfully set to {ui_home_path}",
                "template_set_ui_home_success",
                context=context,
                extra_data={
                    "ui_home_path": ui_home_path,
                    "ssh_output": result.stdout.strip(),
                    "return_code": result.returncode
                }
            )
            return {
                'success': True,
                'message': f'UI_HOME set to {ui_home_path}',
                'output': result.stdout
            }
        else:
            # Log failure
            enhanced_logger.log_error(
                f"Failed to set UI_HOME: {result.stderr.strip()}",
                "template_set_ui_home_failed",
                context=context,
                extra_data={
                    "return_code": result.returncode,
                    "stderr": result.stderr.strip(),
                    "stdout": result.stdout.strip()
                }
            )
            return {
                'success': False,
                'message': f'Failed to set UI_HOME with return code {result.returncode}',
                'error': result.stderr
            }
            
    except subprocess.TimeoutExpired:
        enhanced_logger.log_error(
            "UI_HOME setup timed out",
            "ssh_timeout",
            context=context,
            extra_data={"timeout_seconds": 60}
        )
        return {
            'success': False,
            'message': 'SSH command timed out while setting UI_HOME'
        }
    except Exception as e:
        enhanced_logger.log_error(
            f"Unexpected error during UI_HOME setup: {str(e)}",
            "template_set_ui_home_error",
            context=context,
            extra_data={"error_type": type(e).__name__, "error_message": str(e)}
        )
        return {
            'success': False,
            'message': f'Error setting UI_HOME: {str(e)}'
        }


def execute_git_clone(ssh_connection, repository, destination):
    """Execute git clone with enhanced logging"""
    operation_id = f"git_clone_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    session_id = f"session_{int(time.time())}"
    
    # Create log context for this operation
    context = LogContext(
        operation_id=operation_id,
        user_agent="vast_api/1.0 (template_git_clone)",
        session_id=session_id,
        ip_address="localhost",
        template_name="comfyui"
    )
    
    try:
        # Log start of operation
        enhanced_logger.log_operation(
            f"📥 Cloning repository {repository} to {destination}",
            "template_git_clone_start",
            context=context,
            extra_data={"repository": repository, "destination": destination, "ssh_connection": ssh_connection}
        )
        
        ssh_info = parse_ssh_connection(ssh_connection)
        if not ssh_info:
            enhanced_logger.log_error(
                "Invalid SSH connection string format for git clone",
                "ssh_parse_error",
                context=context,
                extra_data={"ssh_connection": ssh_connection}
            )
            return {
                'success': False,
                'message': 'Invalid SSH connection string format'
            }
        
        host, port, user = ssh_info['host'], ssh_info['port'], ssh_info.get('user', 'root')
        if not host or not port:
            enhanced_logger.log_error(
                "Missing host or port in SSH connection",
                "ssh_connection_incomplete",
                context=context,
                extra_data={"host": host, "port": port}
            )
            return {
                'success': False,
                'message': 'Invalid SSH connection string format'
            }
        
        # Log SSH connection attempt
        enhanced_logger.log_operation(
            f"🔌 Connecting to {user}@{host}:{port} for git clone",
            "ssh_connection_attempt",
            context=context,
            extra_data={"host": host, "port": port, "user": user}
        )
        
        cmd = f'''ssh -p {port} -o StrictHostKeyChecking=no -o ConnectTimeout=10 {user}@{host} "
        set -e
        if [ ! -d '{destination}' ]; then
            echo 'Cloning repository {repository}...'
            git clone {repository} {destination}
            echo 'Repository cloned successfully to {destination}'
        else
            echo 'Repository already exists at {destination}'
            cd {destination}
            git pull origin main || git pull origin master || echo 'Repository updated or pull not needed'
        fi
        "'''
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            # Log successful operation
            enhanced_logger.log_operation(
                f"✅ Git clone completed: {repository} -> {destination}",
                "template_git_clone_success",
                context=context,
                extra_data={
                    "repository": repository,
                    "destination": destination,
                    "ssh_output": result.stdout.strip(),
                    "return_code": result.returncode
                }
            )
            return {
                'success': True,
                'message': f'Repository cloned to {destination}',
                'output': result.stdout
            }
        else:
            # Log failure
            enhanced_logger.log_error(
                f"Git clone failed: {result.stderr.strip()}",
                "template_git_clone_failed",
                context=context,
                extra_data={
                    "repository": repository,
                    "destination": destination,
                    "return_code": result.returncode,
                    "stderr": result.stderr.strip(),
                    "stdout": result.stdout.strip()
                }
            )
            return {
                'success': False,
                'message': f'Git clone failed with return code {result.returncode}',
                'error': result.stderr
            }
            
    except subprocess.TimeoutExpired:
        enhanced_logger.log_error(
            "Git clone timed out",
            "ssh_timeout",
            context=context,
            extra_data={"timeout_seconds": 300, "repository": repository, "destination": destination}
        )
        return {
            'success': False,
            'message': 'SSH command timed out during git clone'
        }
    except Exception as e:
        enhanced_logger.log_error(
            f"Unexpected error during git clone: {str(e)}",
            "template_git_clone_error",
            context=context,
            extra_data={"error_type": type(e).__name__, "error_message": str(e)}
        )
        return {
            'success': False,
            'message': f'Error during git clone: {str(e)}'
        }


def execute_python_venv_setup(ssh_connection, venv_path):
    """Execute Python virtual environment setup with enhanced logging"""
    operation_id = f"python_venv_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    session_id = f"session_{int(time.time())}"
    
    # Create log context for this operation
    context = LogContext(
        operation_id=operation_id,
        user_agent="vast_api/1.0 (template_python_venv)",
        session_id=session_id,
        ip_address="localhost",
        template_name="comfyui"
    )
    
    try:
        # Log start of operation
        enhanced_logger.log_operation(
            f"🐍 Setting up Python virtual environment at {venv_path}",
            "template_python_venv_start",
            context=context,
            extra_data={"venv_path": venv_path, "ssh_connection": ssh_connection}
        )
        
        ssh_info = parse_ssh_connection(ssh_connection)
        if not ssh_info:
            enhanced_logger.log_error(
                "Invalid SSH connection string format for Python venv setup",
                "ssh_parse_error",
                context=context,
                extra_data={"ssh_connection": ssh_connection}
            )
            return {
                'success': False,
                'message': 'Invalid SSH connection string format'
            }
        
        host, port, user = ssh_info['host'], ssh_info['port'], ssh_info.get('user', 'root')
        if not host or not port:
            enhanced_logger.log_error(
                "Missing host or port in SSH connection",
                "ssh_connection_incomplete",
                context=context,
                extra_data={"host": host, "port": port}
            )
            return {
                'success': False,
                'message': 'Invalid SSH connection string format'
            }
        
        # Log SSH connection attempt
        enhanced_logger.log_operation(
            f"🔌 Connecting to {user}@{host}:{port} for Python venv setup",
            "ssh_connection_attempt",
            context=context,
            extra_data={"host": host, "port": port, "user": user}
        )
        
        cmd = f'''ssh -p {port} -o StrictHostKeyChecking=no -o ConnectTimeout=10 {user}@{host} "
        set -e
        if [ ! -d '{venv_path}' ]; then
            echo 'Creating Python virtual environment...'
            python3 -m venv {venv_path}
            echo 'Python virtual environment created at {venv_path}'
        else
            echo 'Virtual environment already exists at {venv_path}'
        fi
        echo 'Activating virtual environment and upgrading pip...'
        source {venv_path}/bin/activate
        pip install --upgrade pip
        echo 'Virtual environment setup completed successfully'
        "'''
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
        
        if result.returncode == 0:
            # Log successful operation
            enhanced_logger.log_operation(
                f"✅ Python virtual environment setup completed at {venv_path}",
                "template_python_venv_success",
                context=context,
                extra_data={
                    "venv_path": venv_path,
                    "ssh_output": result.stdout.strip(),
                    "return_code": result.returncode
                }
            )
            return {
                'success': True,
                'message': f'Python virtual environment setup at {venv_path}',
                'output': result.stdout
            }
        else:
            # Log failure
            enhanced_logger.log_error(
                f"Python venv setup failed: {result.stderr.strip()}",
                "template_python_venv_failed",
                context=context,
                extra_data={
                    "venv_path": venv_path,
                    "return_code": result.returncode,
                    "stderr": result.stderr.strip(),
                    "stdout": result.stdout.strip()
                }
            )
            return {
                'success': False,
                'message': f'Python venv setup failed with return code {result.returncode}',
                'error': result.stderr
            }
            
    except subprocess.TimeoutExpired:
        enhanced_logger.log_error(
            "Python venv setup timed out",
            "ssh_timeout",
            context=context,
            extra_data={"timeout_seconds": 180, "venv_path": venv_path}
        )
        return {
            'success': False,
            'message': 'SSH command timed out during Python venv setup'
        }
    except Exception as e:
        enhanced_logger.log_error(
            f"Unexpected error during Python venv setup: {str(e)}",
            "template_python_venv_error",
            context=context,
            extra_data={"error_type": type(e).__name__, "error_message": str(e)}
        )
        return {
            'success': False,
            'message': f'Error setting up Python virtual environment: {str(e)}'
        }


# --- SSH Host Key Management Routes ---

@app.route('/ssh/host-keys/check', methods=['POST', 'OPTIONS'])
def check_host_key_error():
    """Check if SSH output contains a host key error"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        from .ssh_host_key_manager import SSHHostKeyManager
        
        data = request.get_json() if request.is_json else {}
        ssh_output = data.get('ssh_output', '')
        
        if not ssh_output:
            return jsonify({
                'success': False,
                'message': 'SSH output is required'
            }), 400
        
        manager = SSHHostKeyManager()
        error = manager.detect_host_key_error(ssh_output)
        
        if error:
            return jsonify({
                'success': True,
                'has_error': True,
                'error': {
                    'host': error.host,
                    'port': error.port,
                    'known_hosts_file': error.known_hosts_file,
                    'line_number': error.line_number,
                    'new_fingerprint': error.new_fingerprint,
                    'detected_at': error.detected_at
                }
            })
        else:
            return jsonify({
                'success': True,
                'has_error': False
            })
    
    except Exception as e:
        logger.error(f"Error checking host key error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error checking host key: {str(e)}'
        }), 500


@app.route('/ssh/host-keys/resolve', methods=['POST', 'OPTIONS'])
def resolve_host_key_error():
    """Resolve a host key error by removing old key and accepting new one"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        from .ssh_host_key_manager import SSHHostKeyManager, HostKeyError
        
        data = request.get_json() if request.is_json else {}
        host = data.get('host')
        port = data.get('port')
        known_hosts_file = data.get('known_hosts_file')
        user = data.get('user', 'root')
        
        if not host or not port:
            return jsonify({
                'success': False,
                'message': 'Host and port are required'
            }), 400
        
        # Create a minimal HostKeyError object for resolution
        from datetime import datetime
        error = HostKeyError(
            host=host,
            port=int(port),
            known_hosts_file=known_hosts_file or os.path.expanduser("~/.ssh/known_hosts"),
            line_number=0,
            new_fingerprint="",
            error_message="",
            detected_at=datetime.now().isoformat()
        )
        
        manager = SSHHostKeyManager()
        success, message = manager.resolve_host_key_error(error, user)
        
        if success:
            logger.info(f"Successfully resolved host key error for {host}:{port}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            logger.error(f"Failed to resolve host key error for {host}:{port}: {message}")
            return jsonify({
                'success': False,
                'message': message
            }), 500
    
    except Exception as e:
        logger.error(f"Error resolving host key error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error resolving host key: {str(e)}'
        }), 500


@app.route('/ssh/host-keys/remove', methods=['POST', 'OPTIONS'])
def remove_host_key():
    """Remove a specific host key from known_hosts"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        from .ssh_host_key_manager import SSHHostKeyManager
        
        data = request.get_json() if request.is_json else {}
        host = data.get('host')
        port = data.get('port')
        known_hosts_file = data.get('known_hosts_file')
        
        if not host or not port:
            return jsonify({
                'success': False,
                'message': 'Host and port are required'
            }), 400
        
        manager = SSHHostKeyManager()
        success, message = manager.remove_old_host_key(
            host, 
            int(port), 
            known_hosts_file
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
    
    except Exception as e:
        logger.error(f"Error removing host key: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error removing host key: {str(e)}'
        }), 500


# Initialize WebSocket support for real-time progress
try:
    from .websocket_progress import init_socketio
    socketio = init_socketio(app)
    logger.info("WebSocket support initialized")
except Exception as e:
    logger.warning(f"Failed to initialize WebSocket support: {e}")
    socketio = None

# Register v2 API
try:
    from .sync_api_v2 import register_v2_api
    register_v2_api(app)
    logger.info("Registered Sync API v2")
except Exception as e:
    logger.warning(f"Failed to register Sync API v2: {e}")

# --- Resource Management Routes ---

# Initialize resource management
resources_path = '/app/resources'
resource_manager = None
resource_installer = None

try:
    from ..resources import ResourceManager, ResourceInstaller
    resource_manager = ResourceManager(resources_path)
    resource_installer = ResourceInstaller()
    logger.info("Resource management initialized")
except Exception as e:
    logger.warning(f"Failed to initialize resource management: {e}")

@app.route('/resources/list', methods=['GET', 'OPTIONS'])
def resources_list():
    """List available resources with optional filtering"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    if not resource_manager:
        return jsonify({
            'success': False,
            'message': 'Resource management not available'
        }), 503
    
    resource_type = request.args.get('type')
    ecosystem = request.args.get('ecosystem')
    tags_str = request.args.get('tags', '')
    tags = [t.strip() for t in tags_str.split(',') if t.strip()] if tags_str else None
    search = request.args.get('search')
    
    try:
        resources = resource_manager.list_resources(
            resource_type=resource_type,
            ecosystem=ecosystem,
            tags=tags,
            search=search
        )
        
        return jsonify({
            'success': True,
            'count': len(resources),
            'resources': resources
        })
    except Exception as e:
        logger.error(f"Error listing resources: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/resources/get/<path:resource_path>', methods=['GET', 'OPTIONS'])
def resources_get(resource_path):
    """Get details of a specific resource"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    if not resource_manager:
        return jsonify({
            'success': False,
            'message': 'Resource management not available'
        }), 503
    
    try:
        resource = resource_manager.get_resource(resource_path)
        
        if not resource:
            return jsonify({
                'success': False,
                'message': f'Resource not found: {resource_path}'
            }), 404
        
        return jsonify({
            'success': True,
            'resource': resource
        })
    except Exception as e:
        logger.error(f"Error getting resource: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/resources/install', methods=['POST', 'OPTIONS'])
def resources_install():
    """Install resources to remote instance"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    if not resource_manager or not resource_installer:
        return jsonify({
            'success': False,
            'message': 'Resource management not available'
        }), 503
    
    try:
        data = request.get_json()
        ssh_connection = data.get('ssh_connection')
        resource_paths = data.get('resources', [])
        ui_home = data.get('ui_home', '/workspace/ComfyUI')
        
        if not ssh_connection:
            return jsonify({
                'success': False,
                'message': 'SSH connection string is required'
            }), 400
        
        if not resource_paths:
            return jsonify({
                'success': False,
                'message': 'At least one resource is required'
            }), 400
        
        try:
            ssh_host, ssh_port = _extract_host_port(ssh_connection)
        except ValueError as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400
        
        # Parse all requested resources
        resources = []
        for path in resource_paths:
            resource = resource_manager.get_resource(path)
            if not resource:
                return jsonify({
                    'success': False,
                    'message': f'Resource not found: {path}'
                }), 404
            resources.append(resource)
        
        # Install
        logger.info(f"Installing {len(resources)} resources to {ssh_host}:{ssh_port}")
        result = resource_installer.install_multiple(
            ssh_host,
            ssh_port,
            ui_home,
            resources
        )
        
        return jsonify({
            'success': result['success'],
            'installed': result['installed'],
            'total': result['total'],
            'details': result['results']
        })
        
    except Exception as e:
        logger.error(f"Error installing resources: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/resources/ecosystems', methods=['GET', 'OPTIONS'])
def resources_ecosystems():
    """Get list of all available ecosystems"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    if not resource_manager:
        return jsonify({
            'success': False,
            'message': 'Resource management not available'
        }), 503
    
    try:
        ecosystems = resource_manager.get_ecosystems()
        return jsonify({
            'success': True,
            'ecosystems': ecosystems
        })
    except Exception as e:
        logger.error(f"Error getting ecosystems: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/resources/types', methods=['GET', 'OPTIONS'])
def resources_types():
    """Get list of all available resource types"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    if not resource_manager:
        return jsonify({
            'success': False,
            'message': 'Resource management not available'
        }), 503
    
    try:
        types = resource_manager.get_types()
        return jsonify({
            'success': True,
            'types': types
        })
    except Exception as e:
        logger.error(f"Error getting types: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/resources/tags', methods=['GET', 'OPTIONS'])
def resources_tags():
    """Get list of all available tags"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    if not resource_manager:
        return jsonify({
            'success': False,
            'message': 'Resource management not available'
        }), 503
    
    try:
        tags = resource_manager.get_tags()
        return jsonify({
            'success': True,
            'tags': tags
        })
    except Exception as e:
        logger.error(f"Error getting tags: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/resources/search', methods=['GET', 'OPTIONS'])
def resources_search():
    """Search resources by query string"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    if not resource_manager:
        return jsonify({
            'success': False,
            'message': 'Resource management not available'
        }), 503
    
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({
            'success': False,
            'message': 'Search query is required'
        }), 400
    
    try:
        resources = resource_manager.search_resources(query)
        return jsonify({
            'success': True,
            'count': len(resources),
            'resources': resources
        })
    except Exception as e:
        logger.error(f"Error searching resources: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# --- Workflow Execution Routes ---

@app.route('/workflow/start', methods=['POST', 'OPTIONS'])
def workflow_start():
    """Start a workflow execution in the background"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        from .workflow_executor import get_workflow_executor
        
        data = request.get_json() if request.is_json else {}
        workflow_id = data.get('workflow_id') or str(uuid.uuid4())
        steps = data.get('steps', [])
        ssh_connection = data.get('ssh_connection')
        step_delay = data.get('step_delay', 5)
        instance_id = data.get('instance_id')
        
        if not ssh_connection:
            return jsonify({
                'success': False,
                'message': 'SSH connection string is required'
            })
        
        if not steps:
            return jsonify({
                'success': False,
                'message': 'Workflow steps are required'
            })
        
        logger.info(f"Starting workflow {workflow_id} with {len(steps)} steps, instance_id: {instance_id}")
        
        # Get executor and start workflow
        executor = get_workflow_executor()
        success = executor.start_workflow(workflow_id, steps, ssh_connection, step_delay, instance_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Workflow started successfully',
                'workflow_id': workflow_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Workflow is already running'
            })
            
    except Exception as e:
        logger.error(f"Error starting workflow: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error starting workflow: {str(e)}'
        })


@app.route('/workflow/stop', methods=['POST', 'OPTIONS'])
def workflow_stop():
    """Stop a running workflow"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        from .workflow_executor import get_workflow_executor
        
        data = request.get_json() if request.is_json else {}
        workflow_id = data.get('workflow_id')
        
        if not workflow_id:
            return jsonify({
                'success': False,
                'message': 'Workflow ID is required'
            })
        
        logger.info(f"Stopping workflow {workflow_id}")
        
        # Get executor and stop workflow
        executor = get_workflow_executor()
        success = executor.stop_workflow(workflow_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Workflow stop requested'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Workflow not found or already stopped'
            })
            
    except Exception as e:
        logger.error(f"Error stopping workflow: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error stopping workflow: {str(e)}'
        })


@app.route('/workflow/resume', methods=['POST', 'OPTIONS'])
def workflow_resume():
    """Resume a blocked workflow after user interaction (e.g., host key verification)"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        from .workflow_state import get_workflow_state_manager
        
        data = request.get_json() if request.is_json else {}
        workflow_id = data.get('workflow_id')
        
        if not workflow_id:
            return jsonify({
                'success': False,
                'message': 'Workflow ID is required'
            })
        
        logger.info(f"Resuming workflow {workflow_id}")
        
        # Get state manager and update state
        state_manager = get_workflow_state_manager()
        state = state_manager.load_state()
        
        if not state or state.get('workflow_id') != workflow_id:
            return jsonify({
                'success': False,
                'message': 'Workflow not found'
            })
        
        if state.get('status') != 'blocked':
            return jsonify({
                'success': False,
                'message': f'Workflow is not in blocked state (current: {state.get("status")})'
            })
        
        # Change state back to running and clear block_info
        state['status'] = 'running'
        state.pop('block_info', None)
        state_manager.save_state(state)
        
        return jsonify({
            'success': True,
            'message': 'Workflow resumed'
        })
            
    except Exception as e:
        logger.error(f"Error resuming workflow: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error resuming workflow: {str(e)}'
        })


@app.route('/workflow/state', methods=['GET', 'OPTIONS'])
def workflow_state():
    """Get the full state of a workflow or the current workflow"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        from .workflow_state import get_workflow_state_manager
        
        workflow_id = request.args.get('workflow_id')
        
        # Get state manager
        state_manager = get_workflow_state_manager()
        state = state_manager.load_state()
        
        if not state:
            return jsonify({
                'success': False,
                'message': 'No workflow state found'
            })
        
        # If workflow_id specified, check if it matches
        if workflow_id and state.get('workflow_id') != workflow_id:
            return jsonify({
                'success': False,
                'message': f'Workflow {workflow_id} not found'
            })
        
        return jsonify({
            'success': True,
            'state': state
        })
            
    except Exception as e:
        logger.error(f"Error getting workflow state: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting workflow state: {str(e)}'
        })


@app.route('/workflow/state/summary', methods=['GET', 'OPTIONS'])
def workflow_state_summary():
    """Get a summary of the workflow state (lighter weight than full state)"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        from .workflow_state import get_workflow_state_manager
        from .workflow_executor import get_workflow_executor
        
        workflow_id = request.args.get('workflow_id')
        
        # Get state manager and executor
        state_manager = get_workflow_state_manager()
        executor = get_workflow_executor()
        
        state = state_manager.load_state()
        
        if not state:
            return jsonify({
                'success': True,
                'has_workflow': False,
                'summary': None
            })
        
        # If workflow_id specified, check if it matches
        if workflow_id and state.get('workflow_id') != workflow_id:
            return jsonify({
                'success': True,
                'has_workflow': False,
                'summary': None
            })
        
        # Get summary information
        summary = state_manager.get_state_summary()
        
        # Add running status
        is_running = executor.is_workflow_running(state.get('workflow_id'))
        summary['is_running'] = is_running
        
        return jsonify({
            'success': True,
            'has_workflow': True,
            'summary': summary
        })
            
    except Exception as e:
        logger.error(f"Error getting workflow summary: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting workflow summary: {str(e)}'
        })


@app.route('/workflow/clear', methods=['POST', 'OPTIONS'])
def workflow_clear():
    """Clear the workflow state"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        from .workflow_state import get_workflow_state_manager
        
        state_manager = get_workflow_state_manager()
        state_manager.clear_state()
        
        logger.info("Workflow state cleared")
        
        return jsonify({
            'success': True,
            'message': 'Workflow state cleared'
        })
            
    except Exception as e:
        logger.error(f"Error clearing workflow state: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error clearing workflow state: {str(e)}'
        })


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