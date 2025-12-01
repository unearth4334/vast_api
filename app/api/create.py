"""
Create Tab API Blueprint
Handles workflow listing, generation, and execution endpoints
"""

from flask import Blueprint, request, jsonify
import logging
from datetime import datetime
import uuid
import base64
import tempfile
import subprocess
import re
from pathlib import Path

from app.create.workflow_loader import WorkflowLoader
from app.create.workflow_generator import WorkflowGenerator
from app.create.workflow_validator import WorkflowValidator

logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('create', __name__, url_prefix='/create')


@bp.route('/workflows/list', methods=['GET'])
def list_workflows():
    """
    List all available workflows from workflows directory
    
    Returns:
        JSON with list of workflow metadata
    """
    try:
        workflows = WorkflowLoader.discover_workflows()
        return jsonify({
            'success': True,
            'workflows': [w.to_dict() for w in workflows]
        })
    except Exception as e:
        logger.error(f"Error listing workflows: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Failed to list workflows: {str(e)}'
        }), 500


@bp.route('/workflows/<workflow_id>', methods=['GET'])
def get_workflow_details(workflow_id):
    """
    Get full workflow configuration including all inputs, sections, and layout
    
    Args:
        workflow_id: Workflow identifier (e.g., "IMG_to_VIDEO")
        
    Returns:
        JSON with complete workflow configuration
    """
    try:
        workflow = WorkflowLoader.load_workflow(workflow_id)
        return jsonify({
            'success': True,
            'workflow': workflow.to_dict()
        })
    except FileNotFoundError as e:
        logger.warning(f"Workflow not found: {workflow_id}")
        return jsonify({
            'success': False,
            'message': f'Workflow not found: {workflow_id}'
        }), 404
    except Exception as e:
        logger.error(f"Error loading workflow {workflow_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Failed to load workflow: {str(e)}'
        }), 500


@bp.route('/generate-workflow', methods=['POST'])
def generate_workflow():
    """
    Generate a ComfyUI-compatible workflow JSON file with user inputs merged
    
    Request JSON:
        {
            "workflow_id": "IMG_to_VIDEO",
            "inputs": {
                "positive_prompt": "...",
                "main_model": {"highNoisePath": "...", "lowNoisePath": "..."},
                ...
            }
        }
        
    Returns:
        JSON with generated workflow and metadata
    """
    data = request.get_json()
    
    workflow_id = data.get('workflow_id')
    inputs = data.get('inputs', {})
    
    if not workflow_id:
        return jsonify({
            'success': False,
            'message': 'workflow_id is required'
        }), 400
    
    try:
        # Load workflow template and config
        workflow_config = WorkflowLoader.load_workflow(workflow_id)
        workflow_template = WorkflowLoader.load_workflow_json(workflow_id)
        
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
        
        # Add metadata
        metadata = {
            'workflow_id': workflow_id,
            'version': workflow_config.version,
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'input_summary': generator.get_input_summary(inputs)
        }
        
        return jsonify({
            'success': True,
            'workflow': generated_workflow,
            'metadata': metadata
        })
        
    except FileNotFoundError as e:
        logger.warning(f"Workflow not found: {workflow_id}")
        return jsonify({
            'success': False,
            'message': f'Workflow not found: {workflow_id}'
        }), 404
    except Exception as e:
        logger.error(f"Error generating workflow: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Failed to generate workflow: {str(e)}',
            'error_code': 'GENERATION_ERROR'
        }), 500


@bp.route('/execute', methods=['POST'])
def execute_workflow():
    """
    Execute workflow on remote ComfyUI instance
    
    This endpoint:
    1. Extracts and uploads image files to remote instance
    2. Generates workflow JSON with image filenames
    3. Uploads workflow JSON to remote instance
    4. Queues workflow execution via ComfyUI API
    
    Request JSON:
        {
            "ssh_connection": "ssh -p 12345 root@host",
            "workflow_id": "IMG_to_VIDEO",
            "inputs": {
                "input_image": "data:image/jpeg;base64,...",
                "positive_prompt": "...",
                ...
            }
        }
        
    Returns:
        JSON with task_id and execution status
    """
    data = request.get_json()
    
    ssh_connection = data.get('ssh_connection')
    workflow_id = data.get('workflow_id')
    inputs = data.get('inputs', {})
    
    if not ssh_connection:
        return jsonify({
            'success': False,
            'message': 'ssh_connection is required'
        }), 400
    
    if not workflow_id:
        return jsonify({
            'success': False,
            'message': 'workflow_id is required'
        }), 400
    
    try:
        # Parse SSH connection details
        host, port = _parse_ssh_connection(ssh_connection)
        
        # Load workflow template and config
        workflow_config = WorkflowLoader.load_workflow(workflow_id)
        workflow_template = WorkflowLoader.load_workflow_json(workflow_id)
        
        # Process image inputs - upload to remote and replace with filenames
        image_fields = [f for f in workflow_config.inputs if f.type == 'image']
        processed_inputs = inputs.copy()
        
        for field in image_fields:
            field_value = inputs.get(field.id)
            if field_value and isinstance(field_value, str) and field_value.startswith('data:image/'):
                # This is a base64 image - upload it and replace with filename
                filename = _upload_image_to_remote(field_value, ssh_connection, host, port)
                processed_inputs[field.id] = filename
                logger.info(f"Uploaded image for {field.id}: {filename}")
        
        # Generate workflow JSON with processed inputs
        generator = WorkflowGenerator(workflow_config, workflow_template)
        generated_workflow = generator.generate(processed_inputs)
        
        # Upload workflow JSON to remote instance
        workflow_path = _upload_workflow_to_remote(generated_workflow, ssh_connection, host, port)
        logger.info(f"Uploaded workflow to: {workflow_path}")
        
        # Queue workflow on ComfyUI
        prompt_id = _queue_workflow_on_comfyui(workflow_path, ssh_connection, host, port)
        
        # Generate task ID for tracking
        task_id = str(uuid.uuid4())
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'prompt_id': prompt_id,
            'message': 'Workflow queued successfully'
        })
        
    except Exception as e:
        logger.error(f"Error executing workflow: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Failed to execute workflow: {str(e)}'
        }), 500


def _parse_ssh_connection(ssh_connection):
    """Extract host and port from SSH connection string"""
    port_match = re.search(r'-p\s+(\d+)', ssh_connection)
    port = port_match.group(1) if port_match else '22'
    
    host_match = re.search(r'root@([\d.]+)', ssh_connection)
    if not host_match:
        raise ValueError("Could not parse host from SSH connection string")
    host = host_match.group(1)
    
    return host, port


def _upload_image_to_remote(base64_data, ssh_connection, host, port):
    """
    Upload base64 image to remote ComfyUI input directory
    
    Returns: filename of uploaded image
    """
    # Parse base64 data URL
    if not base64_data.startswith('data:image/'):
        raise ValueError("Invalid image data format")
    
    # Extract image format and data
    header, encoded = base64_data.split(',', 1)
    image_format = header.split('/')[1].split(';')[0]  # e.g., 'jpeg', 'png'
    
    # Generate unique filename
    filename = f"upload_{uuid.uuid4().hex[:8]}.{image_format}"
    
    # Decode base64 to bytes
    image_data = base64.b64decode(encoded)
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='wb', suffix=f'.{image_format}', delete=False) as tmp_file:
        tmp_file.write(image_data)
        tmp_path = tmp_file.name
    
    try:
        # Upload to remote instance
        remote_path = f"/workspace/ComfyUI/input/{filename}"
        scp_cmd = [
            'scp',
            '-P', port,
            '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
            tmp_path,
            f'root@{host}:{remote_path}'
        ]
        
        result = subprocess.run(scp_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to upload image: {result.stderr}")
        
        logger.info(f"Successfully uploaded image: {filename}")
        return filename
        
    finally:
        # Clean up temporary file
        Path(tmp_path).unlink(missing_ok=True)


def _upload_workflow_to_remote(workflow_json, ssh_connection, host, port):
    """
    Upload workflow JSON to remote instance
    
    Returns: remote path to workflow file
    """
    import json
    
    # Generate unique workflow filename
    filename = f"workflow_{uuid.uuid4().hex[:8]}.json"
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
        json.dump(workflow_json, tmp_file, indent=2)
        tmp_path = tmp_file.name
    
    try:
        # Upload to remote instance
        remote_path = f"/tmp/{filename}"
        scp_cmd = [
            'scp',
            '-P', port,
            '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
            tmp_path,
            f'root@{host}:{remote_path}'
        ]
        
        result = subprocess.run(scp_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to upload workflow: {result.stderr}")
        
        logger.info(f"Successfully uploaded workflow: {filename}")
        return remote_path
        
    finally:
        # Clean up temporary file
        Path(tmp_path).unlink(missing_ok=True)


def _queue_workflow_on_comfyui(workflow_path, ssh_connection, host, port):
    """
    Queue workflow on remote ComfyUI instance via API
    
    Returns: ComfyUI prompt_id
    """
    # Execute curl command on remote to queue workflow
    queue_cmd = [
        'ssh',
        '-p', port,
        '-o', 'StrictHostKeyChecking=yes',
        '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
        f'root@{host}',
        f'curl -s -X POST http://localhost:8188/prompt -H "Content-Type: application/json" -d @{workflow_path}'
    ]
    
    result = subprocess.run(queue_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to queue workflow: {result.stderr}")
    
    # Parse response to get prompt_id
    import json
    try:
        response = json.loads(result.stdout)
        prompt_id = response.get('prompt_id')
        if not prompt_id:
            raise ValueError("No prompt_id in ComfyUI response")
        logger.info(f"Queued workflow with prompt_id: {prompt_id}")
        return prompt_id
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse ComfyUI response: {result.stdout}")
        raise RuntimeError(f"Invalid response from ComfyUI: {str(e)}")
