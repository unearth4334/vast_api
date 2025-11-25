"""
Flask API endpoints for download queue and status
"""
import os
import json
import re
from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid
from pathlib import Path

bp = Blueprint('downloads', __name__, url_prefix='/downloads')

# Paths to queue and status files
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOWNLOADS_DIR = BASE_DIR / 'downloads'
QUEUE_PATH = DOWNLOADS_DIR / 'download_queue.json'
STATUS_PATH = DOWNLOADS_DIR / 'download_status.json'

# Ensure downloads directory exists
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Import resource manager to read resource files
try:
    from ..resources import ResourceManager
    resource_manager = ResourceManager(resources_path=BASE_DIR / 'resources')
except Exception as e:
    print(f"Warning: Could not initialize ResourceManager: {e}")
    resource_manager = None


def extract_commands_from_resource(resource):
    """Extract bash commands from resource's download_command field"""
    # The ResourceParser already extracted the download_command
    download_command = resource.get('download_command', '')
    
    if not download_command:
        return []
    
    # Split by newlines and handle line continuations (\)
    lines = download_command.split('\n')
    commands = []
    current_command = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        if line.endswith('\\'):
            current_command.append(line[:-1].strip())
        else:
            current_command.append(line)
            commands.append(' '.join(current_command))
            current_command = []
    
    # Handle any remaining command
    if current_command:
        commands.append(' '.join(current_command))
    
    return commands


def extract_instance_id_from_ssh(ssh_connection):
    """Extract instance ID from SSH connection string"""
    # Try to extract from format: ssh -p PORT root@HOST
    match = re.search(r'root@([\d.]+)', ssh_connection)
    if match:
        # Use IP address as instance ID for now
        return match.group(1).replace('.', '_')
    return 'unknown'


@bp.route('/queue', methods=['POST'])
def add_to_queue():
    """Add resources to download queue"""
    data = request.get_json()
    
    ssh_connection = data.get('ssh_connection')
    resource_paths = data.get('resources', [])
    ui_home = data.get('ui_home', '/workspace/ComfyUI')
    
    if not ssh_connection or not resource_paths:
        return jsonify({
            'success': False,
            'message': 'ssh_connection and resources are required'
        }), 400
    
    instance_id = extract_instance_id_from_ssh(ssh_connection)
    
    # Get resource details and extract commands
    all_commands = []
    for resource_obj in resource_paths:
        # Extract filepath from resource object (can be dict or string)
        resource_path = resource_obj.get('filepath') if isinstance(resource_obj, dict) else resource_obj
        
        if resource_manager:
            resource = resource_manager.get_resource(resource_path)
            if resource:
                commands = extract_commands_from_resource(resource)
                all_commands.extend(commands)
    
    if not all_commands:
        return jsonify({
            'success': False,
            'message': 'No download commands found in selected resources'
        }), 400
    
    # Create job
    job = {
        'id': str(uuid.uuid4()),
        'instance_id': instance_id,
        'ssh_connection': ssh_connection,
        'ui_home': ui_home,
        'resource_paths': resource_paths,
        'commands': all_commands,
        'added_at': datetime.utcnow().isoformat() + 'Z',
        'status': 'PENDING',
    }
    
    # Add to queue
    queue = []
    if QUEUE_PATH.exists():
        with open(QUEUE_PATH, 'r') as f:
            queue = json.load(f)
    
    queue.append(job)
    
    with open(QUEUE_PATH, 'w') as f:
        json.dump(queue, f, indent=2)
    
    # Initialize status entry
    status = []
    if STATUS_PATH.exists():
        with open(STATUS_PATH, 'r') as f:
            status = json.load(f)
    
    status.append({
        'id': job['id'],
        'instance_id': instance_id,
        'added_at': job['added_at'],
        'status': 'PENDING',
        'progress': {}
    })
    
    with open(STATUS_PATH, 'w') as f:
        json.dump(status, f, indent=2)
    
    return jsonify({
        'success': True,
        'job': job
    })


@bp.route('/status', methods=['GET'])
def get_status():
    """Get download status for an instance"""
    instance_id = request.args.get('instance_id')
    
    status = []
    if STATUS_PATH.exists():
        with open(STATUS_PATH, 'r') as f:
            status = json.load(f)
    
    if instance_id:
        status = [j for j in status if str(j.get('instance_id')) == str(instance_id)]
    
    return jsonify(status)
