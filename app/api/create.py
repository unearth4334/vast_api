"""
Create Tab API Blueprint
Handles workflow listing, generation, and execution endpoints
"""

from flask import Blueprint, request, jsonify, send_file
import logging
from datetime import datetime
import uuid
import base64
import tempfile
import subprocess
import re
from pathlib import Path
import time
import os
from PIL import Image
import io

from app.create.workflow_loader import WorkflowLoader
from app.create.workflow_generator import WorkflowGenerator
from app.create.workflow_validator import WorkflowValidator
from app.create.workflow_history import WorkflowHistory

logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('create', __name__, url_prefix='/create')

# In-memory store for workflow queue timestamps
# Maps prompt_id -> queue_timestamp
workflow_queue_times = {}

# In-memory store for workflow thumbnails
# Maps prompt_id -> thumbnail_filename
workflow_thumbnails = {}

# In-memory store for workflow metadata
# Maps prompt_id -> {'workflow_id': str, 'min_time': int}
workflow_metadata = {}

# Thumbnail directory
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
THUMBNAIL_DIR = Path(os.path.join(BASE_DIR, 'downloads', 'thumbnails'))
THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)


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
    
    This endpoint processes inputs exactly as they would be for execution,
    including converting base64 images to filenames for debugging purposes.
    
    Request JSON:
        {
            "workflow_id": "IMG_to_VIDEO",
            "inputs": {
                "positive_prompt": "...",
                "input_image": "data:image/jpeg;base64,...",
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
        
        # Process image inputs - replace base64 with filenames (for debugging)
        image_fields = [f for f in workflow_config.inputs if f.type == 'image']
        processed_inputs = inputs.copy()
        
        for field in image_fields:
            field_value = inputs.get(field.id)
            if field_value and isinstance(field_value, str) and field_value.startswith('data:image/'):
                # Generate a placeholder filename that would be used during execution
                filename = _generate_image_filename(field_value)
                processed_inputs[field.id] = filename
                logger.debug(f"Replaced base64 image for {field.id} with filename: {filename}")
        
        # Validate processed inputs
        validator = WorkflowValidator(workflow_config)
        validation_result = validator.validate_inputs(processed_inputs)
        
        if not validation_result.is_valid:
            return jsonify({
                'success': False,
                'message': 'Input validation failed',
                'errors': validation_result.errors
            }), 400
        
        # Generate workflow JSON with processed inputs
        generator = WorkflowGenerator(workflow_config, workflow_template)
        generated_workflow = generator.generate(processed_inputs)
        
        # Add metadata
        metadata = {
            'workflow_id': workflow_id,
            'version': workflow_config.version,
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'input_summary': generator.get_input_summary(processed_inputs)
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
        thumbnail_saved = False
        thumbnail_filename = None
        
        for field in image_fields:
            field_value = inputs.get(field.id)
            if field_value and isinstance(field_value, str) and field_value.startswith('data:image/'):
                # This is a base64 image - upload it and replace with filename
                filename = _upload_image_to_remote(field_value, ssh_connection, host, port)
                processed_inputs[field.id] = filename
                logger.info(f"Uploaded image for {field.id}: {filename}")
                
                # Save thumbnail from first image input (typically input_image)
                if not thumbnail_saved:
                    thumbnail_filename = _save_thumbnail(field_value)
                    thumbnail_saved = True
                    logger.info(f"Saved thumbnail: {thumbnail_filename}")
        
        # Generate workflow JSON with processed inputs
        generator = WorkflowGenerator(workflow_config, workflow_template)
        generated_workflow = generator.generate(processed_inputs)
        
        # Upload workflow JSON to remote instance
        workflow_path = _upload_workflow_to_remote(generated_workflow, ssh_connection, host, port)
        logger.info(f"Uploaded workflow to: {workflow_path}")
        
        # Queue workflow on ComfyUI
        prompt_id = _queue_workflow_on_comfyui(workflow_path, ssh_connection, host, port)
        
        # Save queue timestamp
        workflow_queue_times[prompt_id] = time.time()
        
        # Save thumbnail reference
        if thumbnail_filename:
            workflow_thumbnails[prompt_id] = thumbnail_filename
        
        # Save workflow metadata for validation
        min_expected_time = workflow_config.time_estimate.get('min', 60) if workflow_config.time_estimate else 60
        workflow_metadata[prompt_id] = {
            'workflow_id': workflow_id,
            'min_time': min_expected_time
        }
        
        # Generate task ID for tracking
        task_id = str(uuid.uuid4())
        
        # Save to history
        try:
            WorkflowHistory.save_history_record(
                workflow_id=workflow_id,
                inputs=inputs,  # Save original inputs (with base64 images)
                thumbnail=thumbnail_filename,
                prompt_id=prompt_id,
                task_id=task_id
            )
            logger.info(f"Saved workflow execution to history")
        except Exception as e:
            logger.error(f"Failed to save workflow history: {e}", exc_info=True)
            # Don't fail the execution if history save fails
        
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


def _generate_image_filename(base64_data):
    """
    Generate a filename for an image from base64 data
    Returns a filename like: upload_abc12345.jpeg
    """
    if not base64_data.startswith('data:image/'):
        raise ValueError("Invalid image data format")
    
    # Extract image format
    header = base64_data.split(',', 1)[0]
    image_format = header.split('/')[1].split(';')[0]  # e.g., 'jpeg', 'png'
    
    # Generate unique filename
    filename = f"upload_{uuid.uuid4().hex[:8]}.{image_format}"
    return filename


def _upload_image_to_remote(base64_data, ssh_connection, host, port):
    """
    Upload base64 image to remote ComfyUI input directory
    
    Returns: filename of uploaded image
    """
    # Generate filename using the same logic as export
    filename = _generate_image_filename(base64_data)
    
    # Extract image data
    header, encoded = base64_data.split(',', 1)
    image_format = header.split('/')[1].split(';')[0]
    
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


@bp.route('/execution-queue', methods=['POST'])
def get_execution_queue():
    """
    Get execution queue status from ComfyUI instance
    
    Expected POST body:
    {
        "ssh_connection": "ssh -p 40538 root@198.53.64.194"
    }
    
    Returns:
        JSON with queue status, running workflows, and recent history
    """
    data = request.get_json()
    ssh_connection = data.get('ssh_connection')
    
    if not ssh_connection:
        return jsonify({
            'success': False,
            'message': 'ssh_connection is required'
        }), 400
    
    try:
        # Parse SSH connection details
        host, port = _parse_ssh_connection(ssh_connection)
        
        # Get queue status and history from ComfyUI
        queue_status = _get_comfyui_queue_status(ssh_connection, host, port)
        
        return jsonify({
            'success': True,
            'queue': queue_status
        })
        
    except Exception as e:
        logger.error(f"Error fetching execution queue: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Failed to fetch execution queue: {str(e)}'
        }), 500


@bp.route('/execution-outputs/<prompt_id>', methods=['POST'])
def get_execution_outputs(prompt_id):
    """
    Get output files for a specific execution
    
    Expected POST body:
    {
        "ssh_connection": "ssh -p 40538 root@198.53.64.194"
    }
    
    Returns:
        JSON with list of output files
    """
    data = request.get_json()
    ssh_connection = data.get('ssh_connection')
    
    if not ssh_connection:
        return jsonify({
            'success': False,
            'message': 'ssh_connection is required'
        }), 400
    
    try:
        # Parse SSH connection details
        host, port = _parse_ssh_connection(ssh_connection)
        
        # Get outputs from ComfyUI history
        outputs = _get_execution_outputs(prompt_id, ssh_connection, host, port)
        
        return jsonify({
            'success': True,
            'outputs': outputs
        })
        
    except Exception as e:
        logger.error(f"Error fetching execution outputs: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Failed to fetch execution outputs: {str(e)}'
        }), 500


@bp.route('/download-output', methods=['POST'])
def download_output():
    """
    Download an output file from remote instance
    
    Expected POST body:
    {
        "ssh_connection": "ssh -p 40538 root@198.53.64.194",
        "file_path": "/workspace/ComfyUI/output/...",
        "filename": "output_file.mp4"
    }
    
    Returns:
        File download or JSON error
    """
    data = request.get_json()
    ssh_connection = data.get('ssh_connection')
    file_path = data.get('file_path')
    filename = data.get('filename')
    
    if not ssh_connection:
        return jsonify({
            'success': False,
            'message': 'ssh_connection is required'
        }), 400
    
    if not file_path or not filename:
        return jsonify({
            'success': False,
            'message': 'file_path and filename are required'
        }), 400
    
    try:
        # Parse SSH connection details
        host, port = _parse_ssh_connection(ssh_connection)
        
        # Download file from remote
        local_path = _download_output_file(file_path, filename, ssh_connection, host, port)
        
        # Determine MIME type
        import mimetypes
        mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        
        # Send file
        from flask import send_file
        return send_file(
            local_path,
            mimetype=mime_type,
            as_attachment=False,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error downloading output file: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Failed to download output file: {str(e)}'
        }), 500


def _get_execution_outputs(prompt_id, ssh_connection, host, port):
    """
    Get output files for a specific execution from ComfyUI history
    
    Returns list of output file objects with filename, path, type, etc.
    """
    import json
    
    # Get history for specific prompt_id
    history_cmd = [
        'ssh',
        '-p', port,
        '-o', 'StrictHostKeyChecking=yes',
        '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
        f'root@{host}',
        f'curl -s http://localhost:18188/history/{prompt_id}'
    ]
    
    result = subprocess.run(history_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get execution history: {result.stderr}")
    
    # Parse history response
    lines = result.stdout.split('\n')
    json_lines = [line for line in lines if line.strip().startswith('{')]
    
    if not json_lines:
        raise ValueError(f"No JSON response found in history output")
    
    history_data = json.loads(json_lines[0].strip())
    
    # Extract outputs from history
    outputs = []
    if prompt_id in history_data:
        prompt_outputs = history_data[prompt_id].get('outputs', {})
        
        for node_id, node_outputs in prompt_outputs.items():
            # Check for different output types (images, gifs, videos)
            for output_type in ['images', 'gifs', 'videos']:
                if output_type in node_outputs:
                    for output_file in node_outputs[output_type]:
                        outputs.append({
                            'node_id': node_id,
                            'filename': output_file.get('filename'),
                            'subfolder': output_file.get('subfolder', ''),
                            'type': output_file.get('type', 'output'),
                            'format': output_file.get('format', ''),
                            'fullpath': output_file.get('fullpath', ''),
                            'output_type': output_type
                        })
    
    return outputs


def _download_output_file(file_path, filename, ssh_connection, host, port):
    """
    Download an output file from remote instance to local temp directory
    
    Returns: local path to downloaded file
    """
    import os
    
    # Create downloads directory if it doesn't exist
    downloads_dir = Path('/app/downloads/outputs')
    downloads_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique local filename to avoid conflicts
    local_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
    local_path = downloads_dir / local_filename
    
    # Download file via SCP
    scp_cmd = [
        'scp',
        '-P', port,
        '-o', 'StrictHostKeyChecking=yes',
        '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
        f'root@{host}:{file_path}',
        str(local_path)
    ]
    
    result = subprocess.run(scp_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to download file: {result.stderr}")
    
    logger.info(f"Downloaded output file: {filename} -> {local_path}")
    return str(local_path)


def _get_comfyui_queue_status(ssh_connection, host, port):
    """
    Get ComfyUI queue status and recent execution history
    
    Returns dict with:
    - queue_running: list of running workflows
    - queue_pending: list of pending workflows
    - recent_history: list of recently completed workflows
    """
    import json
    
    # Get queue status
    queue_cmd = [
        'ssh',
        '-p', port,
        '-o', 'StrictHostKeyChecking=yes',
        '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
        f'root@{host}',
        'curl -s http://localhost:18188/queue'
    ]
    
    result = subprocess.run(queue_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get queue status: {result.stderr}")
    
    # Parse queue response
    lines = result.stdout.split('\n')
    json_lines = [line for line in lines if line.strip().startswith('{')]
    
    if not json_lines:
        raise ValueError(f"No JSON response found in queue output")
    
    queue_data = json.loads(json_lines[0].strip())
    
    # Get recent history (last 10 executions)
    history_cmd = [
        'ssh',
        '-p', port,
        '-o', 'StrictHostKeyChecking=yes',
        '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
        f'root@{host}',
        'curl -s http://localhost:18188/history?max_items=10'
    ]
    
    result = subprocess.run(history_cmd, capture_output=True, text=True)
    
    history_data = {}
    if result.returncode == 0:
        lines = result.stdout.split('\n')
        json_lines = [line for line in lines if line.strip().startswith('{')]
        if json_lines:
            history_data = json.loads(json_lines[0].strip())
    
    # Process queue items
    running_items = []
    for item in queue_data.get('queue_running', []):
        prompt_id = item[1] if isinstance(item, list) and len(item) > 1 else str(item)
        
        # Prefer queue time (when we submitted) over history timestamp
        # History may contain stale data from previous executions
        start_time = None
        if prompt_id in workflow_queue_times:
            start_time = workflow_queue_times[prompt_id]
        elif prompt_id in history_data:
            # Fallback to history only if we don't have queue time
            status = history_data[prompt_id].get('status', {})
            messages = status.get('messages', [])
            for msg in messages:
                if isinstance(msg, list) and len(msg) >= 2:
                    msg_type = msg[0]
                    msg_data = msg[1]
                    if msg_type == 'execution_start' and 'timestamp' in msg_data:
                        start_time = msg_data['timestamp'] / 1000
                        break
        
        # Get thumbnail if available
        thumbnail = workflow_thumbnails.get(prompt_id)
        
        running_items.append({
            'prompt_id': prompt_id,
            'status': 'running',
            'start_time': start_time,
            'thumbnail': thumbnail
        })
    
    pending_items = []
    for item in queue_data.get('queue_pending', []):
        prompt_id = item[1] if isinstance(item, list) and len(item) > 1 else str(item)
        
        # Get queue time for pending items
        queue_time = workflow_queue_times.get(prompt_id)
        
        # Get thumbnail if available
        thumbnail = workflow_thumbnails.get(prompt_id)
        
        pending_items.append({
            'prompt_id': prompt_id,
            'status': 'pending',
            'queue_time': queue_time,
            'thumbnail': thumbnail
        })
    
    # Process history items
    recent_items = []
    for prompt_id, history_item in history_data.items():
        status = history_item.get('status', {})
        messages = status.get('messages', [])
        
        # Extract timestamps
        start_time = None
        end_time = None
        
        for msg in messages:
            if isinstance(msg, list) and len(msg) >= 2:
                msg_type = msg[0]
                msg_data = msg[1]
                
                if msg_type == 'execution_start' and 'timestamp' in msg_data:
                    start_time = msg_data['timestamp'] / 1000  # Convert to seconds
                elif msg_type in ['execution_success', 'execution_error'] and 'timestamp' in msg_data:
                    end_time = msg_data['timestamp'] / 1000
        
        # Determine status
        status_str = status.get('status_str', 'unknown')
        if status_str == 'success':
            item_status = 'success'
        elif status_str == 'error':
            item_status = 'failed'
        else:
            item_status = status_str
        
        # Calculate execution time
        execution_time = None
        if start_time and end_time:
            execution_time = end_time - start_time
        
        # Detect suspiciously fast completion (likely cached/not actually executed)
        cached_execution_detected = False
        if item_status == 'success' and execution_time is not None:
            # Check if workflow has expected minimum time
            if prompt_id in workflow_metadata:
                min_expected_time = workflow_metadata[prompt_id]['min_time']
                # If execution was less than 10% of expected minimum time, flag it
                if execution_time < (min_expected_time * 0.1):
                    logger.warning(
                        f"Workflow {prompt_id} completed suspiciously fast: "
                        f"{execution_time:.1f}s (expected min: {min_expected_time}s). "
                        f"Likely cached/not executed."
                    )
                    item_status = 'failed'
                    cached_execution_detected = True
        
        # Clean up queue time for completed workflows
        if status.get('completed', False) and prompt_id in workflow_queue_times:
            del workflow_queue_times[prompt_id]
        
        # Clean up metadata for completed workflows
        if status.get('completed', False) and prompt_id in workflow_metadata:
            del workflow_metadata[prompt_id]
        
        # Get thumbnail if available
        thumbnail = workflow_thumbnails.get(prompt_id)
        
        # Clean up thumbnail for completed workflows (optional - keep for history)
        # if status.get('completed', False) and prompt_id in workflow_thumbnails:
        #     del workflow_thumbnails[prompt_id]
        
        recent_items.append({
            'prompt_id': prompt_id,
            'status': item_status,
            'start_time': start_time,
            'end_time': end_time,
            'execution_time': execution_time,
            'completed': status.get('completed', False),
            'thumbnail': thumbnail,
            'cached_execution': cached_execution_detected
        })
    
    # Sort recent items by start time (most recent first)
    recent_items.sort(key=lambda x: x.get('start_time', 0), reverse=True)
    
    return {
        'queue_running': running_items,
        'queue_pending': pending_items,
        'recent_history': recent_items[:10]  # Limit to 10 most recent
    }


def _queue_workflow_on_comfyui(workflow_path, ssh_connection, host, port):
    """
    Queue workflow on remote ComfyUI instance via API
    
    Returns: ComfyUI prompt_id
    """
    # Create the API payload by wrapping the workflow in a "prompt" key
    # ComfyUI expects: {"prompt": {...workflow nodes...}, "client_id": "optional"}
    payload_cmd = f'jq -c \'. | {{prompt: .}}\' {workflow_path}'
    
    # Execute curl command on remote to queue workflow
    queue_cmd = [
        'ssh',
        '-p', port,
        '-o', 'StrictHostKeyChecking=yes',
        '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
        f'root@{host}',
        f'bash -c "{payload_cmd} | curl -s -X POST http://localhost:18188/prompt -H \'Content-Type: application/json\' -d @-"'
    ]
    
    result = subprocess.run(queue_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to queue workflow: {result.stderr}")
    
    # Parse response to get prompt_id
    import json
    try:
        # Filter out vast.ai welcome message from stdout
        lines = result.stdout.split('\n')
        # Find the JSON response (starts with '{')
        json_lines = [line for line in lines if line.strip().startswith('{')]
        
        if not json_lines:
            raise ValueError(f"No JSON response found in output: {result.stdout}")
        
        response_text = json_lines[0].strip()
        response = json.loads(response_text)
        
        prompt_id = response.get('prompt_id')
        if not prompt_id:
            # Check if there's an error in the response
            if 'error' in response:
                raise ValueError(f"ComfyUI error: {response.get('error')}")
            raise ValueError(f"No prompt_id in ComfyUI response: {response}")
        
        logger.info(f"Queued workflow with prompt_id: {prompt_id}")
        return prompt_id
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse ComfyUI response: {result.stdout}")
        raise RuntimeError(f"Invalid response from ComfyUI: {str(e)}")


def _save_thumbnail(base64_image):
    """
    Save a thumbnail from a base64 encoded image
    
    Args:
        base64_image: Base64 encoded image data (data:image/jpeg;base64,...)
    
    Returns:
        Thumbnail filename
    """
    try:
        # Extract base64 data
        if ',' in base64_image:
            base64_data = base64_image.split(',')[1]
        else:
            base64_data = base64_image
        
        # Decode image
        image_data = base64.b64decode(base64_data)
        image = Image.open(io.BytesIO(image_data))
        
        # Create thumbnail (max 200x200)
        image.thumbnail((200, 200), Image.Resampling.LANCZOS)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        thumbnail_filename = f"thumb_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
        thumbnail_path = THUMBNAIL_DIR / thumbnail_filename
        
        # Save as JPEG
        image.convert('RGB').save(thumbnail_path, 'JPEG', quality=85)
        
        logger.info(f"Saved thumbnail: {thumbnail_filename}")
        return thumbnail_filename
    except Exception as e:
        logger.error(f"Error saving thumbnail: {e}", exc_info=True)
        return None


@bp.route('/thumbnail/<filename>', methods=['GET'])
def get_thumbnail(filename):
    """
    Serve a thumbnail image
    
    Args:
        filename: Thumbnail filename
    
    Returns:
        Thumbnail image file
    """
    try:
        thumbnail_path = THUMBNAIL_DIR / filename
        
        if not thumbnail_path.exists():
            return jsonify({
                'success': False,
                'message': 'Thumbnail not found'
            }), 404
        
        return send_file(
            thumbnail_path,
            mimetype='image/jpeg',
            as_attachment=False
        )
    except Exception as e:
        logger.error(f"Error serving thumbnail: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Failed to serve thumbnail: {str(e)}'
        }), 500


@bp.route('/history/list', methods=['GET'])
def list_history():
    """
    List workflow execution history with pagination and filtering
    
    Query parameters:
        - workflow_id: Filter by workflow ID (optional)
        - limit: Number of records to return (default: 10)
        - offset: Number of records to skip (default: 0)
    
    Returns:
        JSON with history records and pagination info
    """
    try:
        workflow_id = request.args.get('workflow_id')
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('offset', 0))
        
        # Get history records
        records = WorkflowHistory.get_history_records(
            workflow_id=workflow_id,
            limit=limit,
            offset=offset
        )
        
        # Get total count for pagination
        total_count = WorkflowHistory.count_history_records(workflow_id=workflow_id)
        
        return jsonify({
            'success': True,
            'records': records,
            'pagination': {
                'offset': offset,
                'limit': limit,
                'total': total_count,
                'has_more': (offset + limit) < total_count
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing history: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Failed to list history: {str(e)}'
        }), 500


@bp.route('/history/<record_id>', methods=['GET'])
def get_history_record(record_id):
    """
    Get a specific history record by ID
    
    Args:
        record_id: History record ID
    
    Returns:
        JSON with history record details
    """
    try:
        record = WorkflowHistory.get_history_record(record_id)
        
        if not record:
            return jsonify({
                'success': False,
                'message': 'History record not found'
            }), 404
        
        return jsonify({
            'success': True,
            'record': record
        })
        
    except Exception as e:
        logger.error(f"Error getting history record: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Failed to get history record: {str(e)}'
        }), 500

