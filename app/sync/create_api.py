#!/usr/bin/env python3
"""
Create Tab API - Workflow Management and Execution
Provides endpoints for listing workflows, getting workflow details, and executing workflows.
"""

import os
import logging
import json
import uuid
import random
from pathlib import Path
from typing import Optional, Dict, List, Any

try:
    import yaml
except ImportError:
    yaml = None

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

# Create Blueprint for Create Tab API
create_bp = Blueprint('create', __name__, url_prefix='/create')

# Path to workflows directory
WORKFLOWS_DIR = Path(__file__).parent.parent.parent / 'workflows'


def get_workflow_icon(category: str) -> str:
    """Get icon for workflow category"""
    icons = {
        'video': '🎬',
        'image': '🖼️',
        'audio': '🎵',
        'text': '📝',
        'upscale': '🔍',
        'default': '⚙️'
    }
    return icons.get(category, icons['default'])


def load_webui_wrapper(workflow_id: str) -> Optional[Dict]:
    """Load a workflow's webui wrapper YAML file"""
    if yaml is None:
        logger.warning("PyYAML not installed, cannot load webui wrappers")
        return None
    
    # Try different naming patterns
    patterns = [
        f"{workflow_id}.webui.yml",
        f"{workflow_id}.webui.yaml",
        f"{workflow_id.replace('-', '_')}.webui.yml",
        f"{workflow_id.replace('_', '-')}.webui.yml",
    ]
    
    for pattern in patterns:
        yaml_path = WORKFLOWS_DIR / pattern
        if yaml_path.exists():
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logger.error(f"Error loading webui wrapper {yaml_path}: {e}")
                return None
    
    return None


def load_workflow_json(workflow_file: str) -> Optional[Dict]:
    """Load a workflow JSON file"""
    json_path = WORKFLOWS_DIR / workflow_file
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading workflow JSON {json_path}: {e}")
            return None
    return None


def normalize_workflow_id(filename_stem: str) -> str:
    """Normalize a filename stem to a workflow ID"""
    return filename_stem.replace('.webui', '').replace(' ', '_').lower()


def build_workflow_entry(wrapper: Dict, workflow_id: str) -> Dict:
    """Build a workflow entry dictionary from wrapper and ID"""
    return {
        'id': workflow_id,
        'name': wrapper.get('name', workflow_id),
        'description': wrapper.get('description', ''),
        'category': wrapper.get('category', 'other'),
        'tags': wrapper.get('tags', []),
        'icon': get_workflow_icon(wrapper.get('category', 'default')),
        'thumbnail': wrapper.get('thumbnail'),
        'vram_estimate': wrapper.get('vram_estimate'),
        'time_estimate': wrapper.get('time_estimate'),
        'has_webui': True
    }


def list_available_workflows() -> List[Dict]:
    """List all available workflows with webui wrappers"""
    workflows = []
    
    if not WORKFLOWS_DIR.exists():
        logger.warning(f"Workflows directory does not exist: {WORKFLOWS_DIR}")
        return workflows
    
    # Find all .webui.yml files
    for yaml_file in WORKFLOWS_DIR.glob("*.webui.yml"):
        wrapper = load_webui_wrapper(yaml_file.stem.replace('.webui', ''))
        if wrapper:
            workflow_id = normalize_workflow_id(yaml_file.stem)
            workflows.append(build_workflow_entry(wrapper, workflow_id))
    
    # Also look for .webui.yaml files
    for yaml_file in WORKFLOWS_DIR.glob("*.webui.yaml"):
        wrapper = load_webui_wrapper(yaml_file.stem.replace('.webui', ''))
        if wrapper:
            workflow_id = normalize_workflow_id(yaml_file.stem)
            # Check if already added
            if not any(w['id'] == workflow_id for w in workflows):
                workflows.append(build_workflow_entry(wrapper, workflow_id))
    
    return workflows


def get_workflow_details(workflow_id: str) -> Optional[Dict]:
    """Get full details of a workflow including UI configuration"""
    # Try to find the webui wrapper
    # Convert workflow_id back to possible file names
    possible_ids = [
        workflow_id,
        workflow_id.replace('_', ' '),
        workflow_id.replace('_', '-'),
        workflow_id.upper(),
        workflow_id.title().replace('_', ' '),
        'IMG_to_VIDEO' if workflow_id == 'img_to_video' else workflow_id
    ]
    
    wrapper = None
    for pid in possible_ids:
        wrapper = load_webui_wrapper(pid)
        if wrapper:
            break
    
    if not wrapper:
        logger.warning(f"Could not find webui wrapper for workflow: {workflow_id}")
        return None
    
    # Load the workflow JSON if specified
    workflow_json = None
    workflow_file = wrapper.get('workflow_file')
    if workflow_file:
        workflow_json = load_workflow_json(workflow_file)
    
    return {
        'id': workflow_id,
        'name': wrapper.get('name', workflow_id),
        'description': wrapper.get('description', ''),
        'version': wrapper.get('version', '1.0.0'),
        'category': wrapper.get('category', 'other'),
        'tags': wrapper.get('tags', []),
        'icon': get_workflow_icon(wrapper.get('category', 'default')),
        'thumbnail': wrapper.get('thumbnail'),
        'vram_estimate': wrapper.get('vram_estimate'),
        'time_estimate': wrapper.get('time_estimate'),
        'layout': wrapper.get('layout'),  # Section-based layout configuration
        'inputs': wrapper.get('inputs', []),
        'advanced': wrapper.get('advanced', []),
        'outputs': wrapper.get('outputs', []),
        'requirements': wrapper.get('requirements', {}),
        'presets': wrapper.get('presets', []),
        'workflow_json': workflow_json
    }


def fill_workflow_json(workflow_json: Dict, inputs: Dict, wrapper: Dict) -> Dict:
    """Fill workflow JSON with user-provided input values"""
    if not workflow_json:
        return {}
    
    # Deep copy the workflow to avoid modifying the original
    filled_workflow = json.loads(json.dumps(workflow_json))
    
    # Get input and advanced field definitions
    all_fields = wrapper.get('inputs', []) + wrapper.get('advanced', [])
    
    for field in all_fields:
        field_id = field.get('id')
        if field_id not in inputs:
            continue
        
        value = inputs[field_id]
        node_id = str(field.get('node_id'))
        
        if node_id not in filled_workflow:
            logger.warning(f"Node {node_id} not found in workflow for field {field_id}")
            continue
        
        node = filled_workflow[node_id]
        
        # Handle different field types
        field_type = field.get('type')
        
        if field_type == 'image':
            # Image inputs require special handling (base64 decode, save to temp file)
            # For now, just set the filename/path
            if 'inputs' in node:
                target_field = field.get('field', 'image')
                node['inputs'][target_field] = value
        
        elif field_type == 'seed':
            if 'inputs' in node:
                target_field = field.get('field', 'noise_seed')
                # Handle random seed (-1)
                if value == -1:
                    value = random.randint(0, 2**63 - 1)
                node['inputs'][target_field] = value
        
        elif field_type in ('slider', 'text', 'textarea', 'select', 'checkbox'):
            if 'inputs' in node:
                # Check if multiple fields need to be updated (e.g., Xi and Xf for mxSlider)
                fields_to_update = field.get('fields', [field.get('field')])
                if not isinstance(fields_to_update, list):
                    fields_to_update = [fields_to_update]
                
                for target_field in fields_to_update:
                    if target_field and target_field in node['inputs']:
                        node['inputs'][target_field] = value
        
        elif field_type == 'size_2d':
            # Handle size with width/height
            if isinstance(value, dict) and 'inputs' in node:
                width_field = field.get('fields', {}).get('width', 'Xi')
                height_field = field.get('fields', {}).get('height', 'Yi')
                if width_field:
                    node['inputs'][width_field] = value.get('width')
                if height_field:
                    node['inputs'][height_field] = value.get('height')
    
    return filled_workflow


# --- API Endpoints ---

@create_bp.route('/workflows/list', methods=['GET', 'OPTIONS'])
def workflows_list():
    """List all available workflows with their metadata"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        workflows = list_available_workflows()
        return jsonify({
            'success': True,
            'count': len(workflows),
            'workflows': workflows
        })
    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        return jsonify({
            'success': False,
            'message': f'Error listing workflows: {str(e)}'
        }), 500


@create_bp.route('/workflows/<workflow_id>', methods=['GET', 'OPTIONS'])
def workflow_get(workflow_id: str):
    """Get full workflow details including UI configuration"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        workflow = get_workflow_details(workflow_id)
        
        if not workflow:
            return jsonify({
                'success': False,
                'message': f'Workflow not found: {workflow_id}'
            }), 404
        
        return jsonify({
            'success': True,
            'workflow': workflow
        })
    except Exception as e:
        logger.error(f"Error getting workflow {workflow_id}: {e}")
        return jsonify({
            'success': False,
            'message': f'Error getting workflow: {str(e)}'
        }), 500


@create_bp.route('/execute', methods=['POST', 'OPTIONS'])
def execute_workflow():
    """Execute a workflow on a cloud instance"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json() if request.is_json else {}
        
        ssh_connection = data.get('ssh_connection')
        workflow_id = data.get('workflow_id')
        inputs = data.get('inputs', {})
        
        if not ssh_connection:
            return jsonify({
                'success': False,
                'message': 'SSH connection string is required'
            }), 400
        
        if not workflow_id:
            return jsonify({
                'success': False,
                'message': 'Workflow ID is required'
            }), 400
        
        # Get workflow details
        workflow = get_workflow_details(workflow_id)
        if not workflow:
            return jsonify({
                'success': False,
                'message': f'Workflow not found: {workflow_id}'
            }), 404
        
        # Generate task ID for tracking
        task_id = str(uuid.uuid4())
        
        logger.info(f"Starting workflow execution: {workflow_id}, task_id: {task_id}")
        
        # Fill the workflow JSON with user inputs
        if workflow.get('workflow_json'):
            filled_workflow = fill_workflow_json(
                workflow['workflow_json'],
                inputs,
                workflow
            )
        else:
            filled_workflow = None
        
        # For now, return success with task ID
        # Full execution implementation would:
        # 1. Save filled workflow to temp file
        # 2. SCP to instance
        # 3. Queue via ComfyUI API
        # 4. Track progress via WebSocket
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Workflow queued successfully',
            'workflow_id': workflow_id,
            'inputs_received': list(inputs.keys())
        })
        
    except Exception as e:
        logger.error(f"Error executing workflow: {e}")
        return jsonify({
            'success': False,
            'message': f'Error executing workflow: {str(e)}'
        }), 500


@create_bp.route('/status/<task_id>', methods=['GET', 'OPTIONS'])
def get_execution_status(task_id: str):
    """Get execution status for a task"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        # TODO: Implement actual status tracking
        # For now, return a placeholder response
        return jsonify({
            'success': True,
            'task_id': task_id,
            'status': 'pending',
            'progress': {
                'current_node': None,
                'percent': 0,
                'eta_seconds': None
            },
            'outputs': None
        })
        
    except Exception as e:
        logger.error(f"Error getting status for task {task_id}: {e}")
        return jsonify({
            'success': False,
            'message': f'Error getting status: {str(e)}'
        }), 500
