#!/usr/bin/env python3
"""
Create Tab API - Workflow Management and Execution
Provides endpoints for listing workflows, getting workflow details, 
generating workflow JSON, and executing workflows on remote instances.
"""

import os
import logging
import json
import uuid
import random
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    yaml = None

from flask import Blueprint, jsonify, request

# Import new components
try:
    from ..create.workflow_loader import WorkflowLoader
    from ..create.workflow_generator import WorkflowGenerator
    from ..create.workflow_validator import WorkflowValidator
    from ..create.task_manager import TaskManager, TaskStatus
except ImportError:
    # Handle both module and direct execution
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from create.workflow_loader import WorkflowLoader
    from create.workflow_generator import WorkflowGenerator
    from create.workflow_validator import WorkflowValidator
    from create.task_manager import TaskManager, TaskStatus

logger = logging.getLogger(__name__)

# Create Blueprint for Create Tab API
create_bp = Blueprint('create', __name__, url_prefix='/create')

# Path to workflows directory
WORKFLOWS_DIR = Path(__file__).parent.parent.parent / 'workflows'

# Initialize workflow loader
workflow_loader = WorkflowLoader(str(WORKFLOWS_DIR))


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


@create_bp.route('/generate-workflow', methods=['POST', 'OPTIONS'])
def generate_workflow():
    """Generate workflow JSON from user inputs"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json() if request.is_json else {}
        
        workflow_id = data.get('workflow_id')
        inputs = data.get('inputs', {})
        
        if not workflow_id:
            return jsonify({
                'success': False,
                'message': 'workflow_id is required'
            }), 400
        
        # Load workflow config and template using the new loader
        workflow_config = workflow_loader.load_workflow(workflow_id)
        if not workflow_config:
            return jsonify({
                'success': False,
                'message': f'Workflow not found: {workflow_id}'
            }), 404
        
        workflow_template = workflow_loader.load_workflow_json(workflow_id)
        if not workflow_template:
            return jsonify({
                'success': False,
                'message': f'Workflow JSON template not found for: {workflow_id}'
            }), 404
        
        # Validate inputs
        validator = WorkflowValidator(workflow_config)
        validation_result = validator.validate_inputs(inputs)
        
        if not validation_result.is_valid:
            return jsonify({
                'success': False,
                'message': 'Input validation failed',
                'errors': validation_result.errors,
                'warnings': validation_result.warnings
            }), 400
        
        # Generate workflow JSON
        generator = WorkflowGenerator(workflow_config, workflow_template)
        generated_workflow = generator.generate(inputs)
        
        # Build metadata
        metadata = {
            'workflow_id': workflow_id,
            'version': workflow_config.version,
            'generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'input_summary': generator.get_input_summary(inputs)
        }
        
        return jsonify({
            'success': True,
            'workflow': generated_workflow,
            'metadata': metadata,
            'warnings': validation_result.warnings if validation_result.warnings else None
        })
        
    except Exception as e:
        logger.error(f"Error generating workflow: {e}")
        return jsonify({
            'success': False,
            'message': f'Error generating workflow: {str(e)}'
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
        options = data.get('options', {})
        
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
        
        # Load workflow config and template
        workflow_config = workflow_loader.load_workflow(workflow_id)
        if not workflow_config:
            return jsonify({
                'success': False,
                'message': f'Workflow not found: {workflow_id}'
            }), 404
        
        workflow_template = workflow_loader.load_workflow_json(workflow_id)
        if not workflow_template:
            return jsonify({
                'success': False,
                'message': f'Workflow JSON template not found for: {workflow_id}'
            }), 404
        
        # Validate inputs
        validator = WorkflowValidator(workflow_config)
        validation_result = validator.validate_inputs(inputs)
        
        if not validation_result.is_valid:
            return jsonify({
                'success': False,
                'message': 'Input validation failed',
                'errors': validation_result.errors
            }), 400
        
        # Generate workflow JSON
        generator = WorkflowGenerator(workflow_config, workflow_template)
        generated_workflow = generator.generate(inputs)
        
        # Create task for tracking
        task = TaskManager.create_task(
            workflow_id=workflow_id,
            ssh_connection=ssh_connection,
            options=options,
            metadata={
                'input_summary': generator.get_input_summary(inputs),
                'version': workflow_config.version
            }
        )
        
        logger.info(f"Created execution task: {task.task_id} for workflow: {workflow_id}")
        
        # Return success with task ID
        # Full execution would:
        # 1. Save filled workflow to temp file
        # 2. SCP to instance
        # 3. Queue via ComfyUI API
        # 4. Track progress via WebSocket
        
        return jsonify({
            'success': True,
            'task_id': task.task_id,
            'message': 'Workflow queued successfully',
            'estimated_time': workflow_config.time_estimate.get('max', 300) if workflow_config.time_estimate else 300,
            'status_url': f'/create/status/{task.task_id}'
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
        task = TaskManager.get_task(task_id)
        
        if not task:
            # Return a default pending status for unknown tasks (backward compatibility)
            return jsonify({
                'success': True,
                'task_id': task_id,
                'status': 'pending',
                'progress': {
                    'current_step': 0,
                    'total_steps': 0,
                    'percent': 0,
                    'message': ''
                },
                'started_at': None,
                'elapsed_seconds': 0,
                'estimated_remaining_seconds': None,
                'outputs': [],
                'metadata': {},
                'error': None
            })
        
        return jsonify({
            'success': True,
            **task.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error getting status for task {task_id}: {e}")
        return jsonify({
            'success': False,
            'message': f'Error getting status: {str(e)}'
        }), 500


@create_bp.route('/cancel/<task_id>', methods=['POST', 'OPTIONS'])
def cancel_task(task_id: str):
    """Cancel a running workflow execution"""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        task = TaskManager.get_task(task_id)
        
        if not task:
            return jsonify({
                'success': False,
                'message': f'Task not found: {task_id}'
            }), 404
        
        # Check if task can be cancelled
        if task.status in (TaskStatus.COMPLETE, TaskStatus.FAILED, TaskStatus.CANCELLED):
            return jsonify({
                'success': False,
                'message': f'Cannot cancel task with status: {task.status.value}'
            }), 400
        
        # Cancel the task
        success = TaskManager.cancel_task(task_id)
        
        if success:
            logger.info(f"Task {task_id} cancelled successfully")
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': 'Workflow cancelled successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to cancel task'
            }), 500
        
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        return jsonify({
            'success': False,
            'message': f'Error cancelling task: {str(e)}'
        }), 500
