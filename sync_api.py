#!/usr/bin/env python3
"""
Media Sync API Server
Provides web API endpoints for syncing media from local Docker containers and VastAI instances.
"""

import os
import subprocess
import logging
from flask import Flask, jsonify, render_template_string, request
from vast_manager import VastManager

# Import SSH test functionality
try:
    from ssh_test import SSHTester
except ImportError:
    SSHTester = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    """Add CORS headers to allow cross-origin requests from browsers"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Handle preflight OPTIONS requests
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    """Handle preflight OPTIONS requests for any endpoint"""
    return '', 200

# Configuration
SYNC_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), 'sync_outputs.sh')
FORGE_HOST = "10.0.78.108"
FORGE_PORT = "2222"
COMFY_HOST = "10.0.78.108"
COMFY_PORT = "2223"

def run_sync(host, port, sync_type="unknown"):
    """Run the sync_outputs.sh script with specified host and port"""
    try:
        logger.info(f"Starting {sync_type} sync to {host}:{port}")
        
        cmd = [
            'bash', SYNC_SCRIPT_PATH,
            '-p', port,
            '--host', host
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            logger.info(f"{sync_type} sync completed successfully")
            return {
                'success': True,
                'message': f'{sync_type} sync completed successfully',
                'output': result.stdout
            }
        else:
            logger.error(f"{sync_type} sync failed with return code {result.returncode}")
            return {
                'success': False,
                'message': f'{sync_type} sync failed',
                'error': result.stderr,
                'output': result.stdout
            }
            
    except subprocess.TimeoutExpired:
        logger.error(f"{sync_type} sync timed out")
        return {
            'success': False,
            'message': f'{sync_type} sync timed out after 5 minutes'
        }
    except Exception as e:
        logger.error(f"{sync_type} sync error: {str(e)}")
        return {
            'success': False,
            'message': f'{sync_type} sync error: {str(e)}'
        }

@app.route('/')
def index():
    """Simple web interface for testing"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Media Sync Tool</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            .button { 
                display: inline-block; 
                background: #007cba; 
                color: white; 
                padding: 15px 30px; 
                margin: 10px; 
                text-decoration: none; 
                border-radius: 5px; 
                border: none;
                font-size: 16px;
                cursor: pointer;
            }
            .button:hover { background: #005a8b; }
            .result { 
                margin: 20px 0; 
                padding: 15px; 
                border-radius: 5px; 
                display: none;
            }
            .success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
            .error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
            .loading { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; }
            pre { white-space: pre-wrap; }
        </style>
    </head>
    <body>
        <h1>🔄 Media Sync Tool</h1>
        <p>Click a button to sync media from the respective source:</p>
        
        <button class="button" onclick="sync('forge')">🔥 Sync Forge (10.0.78.108:2222)</button>
        <button class="button" onclick="sync('comfy')">🖼️ Sync Comfy (10.0.78.108:2223)</button>
        <button class="button" onclick="sync('vastai')">☁️ Sync VastAI (Auto-discover)</button>
        <button class="button" onclick="testSSH()">🔧 Test SSH Connectivity</button>
        
        <div id="result" class="result"></div>
        
        <script>
            async function sync(type) {
                const resultDiv = document.getElementById('result');
                resultDiv.className = 'result loading';
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `<strong>Starting ${type} sync...</strong><br>This may take several minutes.`;
                
                try {
                    const response = await fetch(`/sync/${type}`, { method: 'POST' });
                    const data = await response.json();
                    
                    if (data.success) {
                        resultDiv.className = 'result success';
                        resultDiv.innerHTML = `<strong>✅ ${data.message}</strong><br><pre>${data.output || ''}</pre>`;
                    } else {
                        resultDiv.className = 'result error';
                        resultDiv.innerHTML = `<strong>❌ ${data.message}</strong><br><pre>${data.error || data.output || ''}</pre>`;
                    }
                } catch (error) {
                    resultDiv.className = 'result error';
                    resultDiv.innerHTML = `<strong>❌ Request failed:</strong><br>${error.message}`;
                }
            }
            
            async function testSSH() {
                const resultDiv = document.getElementById('result');
                resultDiv.className = 'result loading';
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = '<strong>Testing SSH connectivity...</strong><br>Checking connections to all configured hosts.';
                
                try {
                    const response = await fetch('/test/ssh', { method: 'POST' });
                    const data = await response.json();
                    
                    if (data.success) {
                        let output = `<strong>✅ SSH connectivity test completed</strong><br><br>`;
                        output += `<strong>Summary:</strong><br>`;
                        output += `Total hosts: ${data.summary.total_hosts}<br>`;
                        output += `Successful: ${data.summary.successful}<br>`;
                        output += `Failed: ${data.summary.failed}<br>`;
                        output += `Success rate: ${data.summary.success_rate}<br><br>`;
                        output += `<strong>Results:</strong><br>`;
                        
                        for (const [host, result] of Object.entries(data.results)) {
                            const status = result.success ? '✅' : '❌';
                            output += `${status} ${host}: ${result.message}<br>`;
                            if (!result.success && result.error) {
                                output += `&nbsp;&nbsp;&nbsp;&nbsp;Error: ${result.error}<br>`;
                            }
                        }
                        
                        resultDiv.className = 'result success';
                        resultDiv.innerHTML = output;
                    } else {
                        resultDiv.className = 'result error';
                        resultDiv.innerHTML = `<strong>❌ SSH test failed:</strong><br>${data.message}<br><pre>${data.error || ''}</pre>`;
                    }
                } catch (error) {
                    resultDiv.className = 'result error';
                    resultDiv.innerHTML = `<strong>❌ Request failed:</strong><br>${error.message}`;
                }
            }
        </script>
    </body>
    </html>
    """
    return html

@app.route('/sync/forge', methods=['POST'])
def sync_forge():
    """Sync from Forge (Stable Diffusion WebUI Forge)"""
    result = run_sync(FORGE_HOST, FORGE_PORT, "Forge")
    return jsonify(result)

@app.route('/sync/comfy', methods=['POST'])
def sync_comfy():
    """Sync from ComfyUI"""
    result = run_sync(COMFY_HOST, COMFY_PORT, "ComfyUI")
    return jsonify(result)

@app.route('/sync/vastai', methods=['POST'])
def sync_vastai():
    """Sync from VastAI (auto-discover running instance)"""
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
        result = run_sync(ssh_host, ssh_port, "VastAI")
        
        # Add instance details to the result
        if result['success']:
            result['instance_info'] = {
                'id': running_instance.get('id'),
                'gpu': running_instance.get('gpu_name'),
                'host': ssh_host,
                'port': ssh_port
            }
        
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

@app.route('/test/ssh', methods=['POST'])
def test_ssh():
    """Test SSH connectivity to configured hosts"""
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

if __name__ == '__main__':
    # Check if sync script exists
    if not os.path.exists(SYNC_SCRIPT_PATH):
        logger.error(f"Sync script not found at {SYNC_SCRIPT_PATH}")
        exit(1)
    
    logger.info("Starting Media Sync API Server")
    app.run(host='0.0.0.0', port=5000, debug=False)