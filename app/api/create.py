"""
Create Tab API Blueprint
Handles workflow listing, generation, and execution endpoints
"""

from flask import Blueprint, request, jsonify
import logging
from datetime import datetime
import uuid

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
