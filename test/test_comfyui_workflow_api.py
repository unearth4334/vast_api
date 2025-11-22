"""
Unit tests for ComfyUI Workflow API endpoints
Tests all REST API endpoints for workflow execution, progress, cancellation, and outputs.
"""

import unittest
import json
import os
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Import Flask app
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.sync.sync_api import app
from app.sync.comfyui_workflow_state import (
    ComfyUIWorkflowState,
    ComfyUINodeState,
    ComfyUIOutputFile,
    WorkflowStatus,
    NodeStatus
)


class TestComfyUIWorkflowAPI(unittest.TestCase):
    """Test cases for ComfyUI workflow API endpoints."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Create temp directory and workflow file
        self.temp_dir = tempfile.mkdtemp()
        self.workflow_file = os.path.join(self.temp_dir, "test_workflow.json")
        
        workflow_data = {
            "1": {"class_type": "LoadImage", "inputs": {}},
            "2": {"class_type": "KSampler", "inputs": {}},
            "3": {"class_type": "SaveImage", "inputs": {}}
        }
        
        with open(self.workflow_file, 'w') as f:
            json.dump(workflow_data, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('app.sync.sync_api.get_executor')
    def test_execute_workflow_success(self, mock_get_executor):
        """Test successful workflow execution."""
        # Mock executor
        mock_executor = Mock()
        mock_executor.execute_workflow.return_value = (
            True,
            "comfyui_workflow_123",
            "Workflow execution started"
        )
        mock_get_executor.return_value = mock_executor
        
        # Make request
        response = self.client.post(
            '/comfyui/workflow/execute',
            json={
                'ssh_connection': 'ssh -p 40738 root@198.53.64.194',
                'workflow_file': self.workflow_file,
                'workflow_name': 'Test Workflow'
            }
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['workflow_id'], 'comfyui_workflow_123')
        self.assertEqual(data['message'], 'Workflow execution started')
        
        # Verify executor was called
        mock_executor.execute_workflow.assert_called_once()
    
    def test_execute_workflow_missing_ssh_connection(self):
        """Test execute endpoint with missing SSH connection."""
        response = self.client.post(
            '/comfyui/workflow/execute',
            json={
                'workflow_file': self.workflow_file
            }
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('ssh_connection', data['message'])
    
    def test_execute_workflow_missing_workflow_file(self):
        """Test execute endpoint with missing workflow file."""
        response = self.client.post(
            '/comfyui/workflow/execute',
            json={
                'ssh_connection': 'ssh -p 40738 root@198.53.64.194'
            }
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('workflow_file', data['message'])
    
    def test_execute_workflow_empty_body(self):
        """Test execute endpoint with empty request body."""
        response = self.client.post(
            '/comfyui/workflow/execute',
            json={}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
    
    @patch('app.sync.sync_api.get_executor')
    def test_execute_workflow_executor_failure(self, mock_get_executor):
        """Test workflow execution with executor failure."""
        # Mock executor failure
        mock_executor = Mock()
        mock_executor.execute_workflow.return_value = (
            False,
            "",
            "Workflow file not found"
        )
        mock_get_executor.return_value = mock_executor
        
        response = self.client.post(
            '/comfyui/workflow/execute',
            json={
                'ssh_connection': 'ssh -p 40738 root@198.53.64.194',
                'workflow_file': self.workflow_file
            }
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('not found', data['message'])
    
    @patch('app.sync.sync_api.get_executor')
    def test_get_workflow_progress_success(self, mock_get_executor):
        """Test getting workflow progress."""
        # Create mock state
        mock_state = ComfyUIWorkflowState(
            workflow_id="comfyui_workflow_123",
            workflow_name="Test Workflow",
            prompt_id="prompt_abc",
            ssh_connection="ssh -p 40738 root@198.53.64.194",
            workflow_file=self.workflow_file,
            status=WorkflowStatus.EXECUTING,
            queue_position=None,
            current_node="2",
            total_nodes=3,
            completed_nodes=1,
            progress_percent=33.3,
            nodes=[
                ComfyUINodeState(
                    node_id="1",
                    node_type="LoadImage",
                    status=NodeStatus.EXECUTED,
                    progress=100.0,
                    message="Loaded"
                )
            ],
            queue_time=datetime.now(),
            start_time=datetime.now(),
            end_time=None,
            last_update=datetime.now(),
            outputs=[],
            error_message=None,
            failed_node=None
        )
        
        # Mock executor
        mock_executor = Mock()
        mock_executor.get_workflow_state.return_value = mock_state
        mock_get_executor.return_value = mock_executor
        
        # Make request
        response = self.client.get('/comfyui/workflow/comfyui_workflow_123/progress')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        progress = data['progress']
        self.assertEqual(progress['workflow_id'], 'comfyui_workflow_123')
        self.assertEqual(progress['status'], 'executing')
        self.assertEqual(progress['progress_percent'], 33.3)
        self.assertEqual(progress['current_node'], '2')
    
    @patch('app.sync.sync_api.get_executor')
    def test_get_workflow_progress_not_found(self, mock_get_executor):
        """Test getting progress for non-existent workflow."""
        # Mock executor
        mock_executor = Mock()
        mock_executor.get_workflow_state.return_value = None
        mock_get_executor.return_value = mock_executor
        
        response = self.client.get('/comfyui/workflow/nonexistent/progress')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('not found', data['message'])
    
    @patch('app.sync.sync_api.get_executor')
    def test_cancel_workflow_success(self, mock_get_executor):
        """Test successful workflow cancellation."""
        # Mock executor
        mock_executor = Mock()
        mock_executor.cancel_workflow.return_value = True
        mock_get_executor.return_value = mock_executor
        
        response = self.client.post('/comfyui/workflow/comfyui_workflow_123/cancel')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('cancellation initiated', data['message'])
        
        mock_executor.cancel_workflow.assert_called_once_with('comfyui_workflow_123')
    
    @patch('app.sync.sync_api.get_executor')
    def test_cancel_workflow_not_found(self, mock_get_executor):
        """Test cancelling non-existent workflow."""
        # Mock executor
        mock_executor = Mock()
        mock_executor.cancel_workflow.return_value = False
        mock_get_executor.return_value = mock_executor
        
        response = self.client.post('/comfyui/workflow/nonexistent/cancel')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
    
    @patch('app.sync.sync_api.get_executor')
    def test_get_workflow_outputs_success(self, mock_get_executor):
        """Test getting workflow outputs."""
        # Create mock state with outputs
        mock_state = ComfyUIWorkflowState(
            workflow_id="comfyui_workflow_123",
            workflow_name="Test Workflow",
            prompt_id="prompt_abc",
            ssh_connection="ssh -p 40738 root@198.53.64.194",
            workflow_file=self.workflow_file,
            status=WorkflowStatus.COMPLETED,
            queue_position=None,
            current_node=None,
            total_nodes=3,
            completed_nodes=3,
            progress_percent=100.0,
            nodes=[],
            queue_time=datetime.now(),
            start_time=datetime.now(),
            end_time=datetime.now(),
            last_update=datetime.now(),
            outputs=[
                ComfyUIOutputFile(
                    filename="output1.png",
                    file_type="image",
                    remote_path="/workspace/output/output1.png",
                    local_path="/tmp/output1.png",
                    downloaded=True
                ),
                ComfyUIOutputFile(
                    filename="output2.png",
                    file_type="image",
                    remote_path="/workspace/output/output2.png",
                    local_path="/tmp/output2.png",
                    downloaded=True
                )
            ],
            error_message=None,
            failed_node=None
        )
        
        # Mock executor
        mock_executor = Mock()
        mock_executor.get_workflow_state.return_value = mock_state
        mock_get_executor.return_value = mock_executor
        
        response = self.client.get('/comfyui/workflow/comfyui_workflow_123/outputs')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        outputs = data['outputs']
        self.assertEqual(len(outputs), 2)
        self.assertEqual(outputs[0]['filename'], 'output1.png')
        self.assertTrue(outputs[0]['downloaded'])
    
    @patch('app.sync.sync_api.get_executor')
    def test_get_workflow_outputs_not_found(self, mock_get_executor):
        """Test getting outputs for non-existent workflow."""
        # Mock executor
        mock_executor = Mock()
        mock_executor.get_workflow_state.return_value = None
        mock_get_executor.return_value = mock_executor
        
        response = self.client.get('/comfyui/workflow/nonexistent/outputs')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
    
    @patch('app.sync.sync_api.get_executor')
    def test_get_workflow_state_exists(self, mock_get_executor):
        """Test loading workflow state from disk."""
        # Create mock state
        mock_state = ComfyUIWorkflowState(
            workflow_id="comfyui_workflow_123",
            workflow_name="Test Workflow",
            prompt_id="prompt_abc",
            ssh_connection="ssh -p 40738 root@198.53.64.194",
            workflow_file=self.workflow_file,
            status=WorkflowStatus.EXECUTING,
            queue_position=None,
            current_node="2",
            total_nodes=3,
            completed_nodes=1,
            progress_percent=33.3,
            nodes=[],
            queue_time=datetime.now(),
            start_time=datetime.now(),
            end_time=None,
            last_update=datetime.now(),
            outputs=[],
            error_message=None,
            failed_node=None
        )
        
        # Mock executor
        mock_executor = Mock()
        mock_executor.load_state.return_value = mock_state
        mock_get_executor.return_value = mock_executor
        
        response = self.client.get('/comfyui/workflow/state')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIsNotNone(data['state'])
        self.assertEqual(data['state']['workflow_id'], 'comfyui_workflow_123')
    
    @patch('app.sync.sync_api.get_executor')
    def test_get_workflow_state_not_exists(self, mock_get_executor):
        """Test loading workflow state when none exists."""
        # Mock executor
        mock_executor = Mock()
        mock_executor.load_state.return_value = None
        mock_get_executor.return_value = mock_executor
        
        response = self.client.get('/comfyui/workflow/state')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIsNone(data['state'])
    
    @patch('app.sync.sync_api.get_executor')
    def test_check_workflow_active(self, mock_get_executor):
        """Test checking if workflow is active."""
        # Mock executor
        mock_executor = Mock()
        mock_executor.is_workflow_active.return_value = True
        mock_get_executor.return_value = mock_executor
        
        response = self.client.get('/comfyui/workflow/comfyui_workflow_123/active')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertTrue(data['active'])
        
        mock_executor.is_workflow_active.assert_called_once_with('comfyui_workflow_123')
    
    @patch('app.sync.sync_api.get_executor')
    def test_check_workflow_not_active(self, mock_get_executor):
        """Test checking if workflow is not active."""
        # Mock executor
        mock_executor = Mock()
        mock_executor.is_workflow_active.return_value = False
        mock_get_executor.return_value = mock_executor
        
        response = self.client.get('/comfyui/workflow/comfyui_workflow_123/active')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertFalse(data['active'])
    
    def test_options_requests(self):
        """Test CORS preflight OPTIONS requests."""
        endpoints = [
            '/comfyui/workflow/execute',
            '/comfyui/workflow/test_id/progress',
            '/comfyui/workflow/test_id/cancel',
            '/comfyui/workflow/test_id/outputs',
            '/comfyui/workflow/state',
            '/comfyui/workflow/test_id/active'
        ]
        
        for endpoint in endpoints:
            response = self.client.options(endpoint)
            self.assertEqual(response.status_code, 204, f"Failed for {endpoint}")
    
    @patch('app.sync.sync_api.get_executor')
    def test_execute_workflow_with_optional_params(self, mock_get_executor):
        """Test workflow execution with all optional parameters."""
        # Mock executor
        mock_executor = Mock()
        mock_executor.execute_workflow.return_value = (
            True,
            "comfyui_workflow_123",
            "Workflow execution started"
        )
        mock_get_executor.return_value = mock_executor
        
        # Make request with all parameters
        response = self.client.post(
            '/comfyui/workflow/execute',
            json={
                'ssh_connection': 'ssh -p 40738 root@198.53.64.194',
                'workflow_file': self.workflow_file,
                'workflow_name': 'Test Workflow',
                'input_images': ['/tmp/image1.png', '/tmp/image2.png'],
                'output_dir': '/custom/output',
                'comfyui_port': 8188,
                'comfyui_input_dir': '/custom/input',
                'comfyui_output_dir': '/custom/output'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify all parameters were passed to executor
        call_args = mock_executor.execute_workflow.call_args
        self.assertEqual(call_args.kwargs['comfyui_port'], 8188)
        self.assertEqual(call_args.kwargs['output_dir'], '/custom/output')
        self.assertEqual(len(call_args.kwargs['input_images']), 2)
    
    @patch('app.sync.sync_api.get_executor')
    def test_api_error_handling(self, mock_get_executor):
        """Test API error handling when executor raises exception."""
        # Mock executor to raise exception
        mock_executor = Mock()
        mock_executor.execute_workflow.side_effect = Exception("Unexpected error")
        mock_get_executor.return_value = mock_executor
        
        response = self.client.post(
            '/comfyui/workflow/execute',
            json={
                'ssh_connection': 'ssh -p 40738 root@198.53.64.194',
                'workflow_file': self.workflow_file
            }
        )
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('error', data['message'].lower())


if __name__ == '__main__':
    unittest.main()
