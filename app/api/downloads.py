"""
Flask API endpoints for download queue and status
"""
import os
import json
from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid

bp = Blueprint('downloads', __name__, url_prefix='/downloads')
QUEUE_PATH = os.path.join(os.path.dirname(__file__), '../../downloads/download_queue.json')
STATUS_PATH = os.path.join(os.path.dirname(__file__), '../../downloads/download_status.json')

@bp.route('/queue', methods=['POST'])
def add_to_queue():
    data = request.get_json()
    job = {
        'id': str(uuid.uuid4()),
        'instance_id': data['instance_id'],
        'ssh_connection': data['ssh_connection'],
        'resource_paths': data['resource_paths'],
        'commands': data['commands'],
        'added_at': datetime.utcnow().isoformat() + 'Z',
        'status': 'PENDING',
    }
    queue = []
    if os.path.exists(QUEUE_PATH):
        with open(QUEUE_PATH, 'r') as f:
            queue = json.load(f)
    queue.append(job)
    with open(QUEUE_PATH, 'w') as f:
        json.dump(queue, f, indent=2)
    return jsonify({'success': True, 'job': job})

@bp.route('/status', methods=['GET'])
def get_status():
    instance_id = request.args.get('instance_id')
    status = []
    if os.path.exists(STATUS_PATH):
        with open(STATUS_PATH, 'r') as f:
            status = json.load(f)
    if instance_id:
        status = [j for j in status if str(j.get('instance_id')) == str(instance_id)]
    return jsonify(status)
