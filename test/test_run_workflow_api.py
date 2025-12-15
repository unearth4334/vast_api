#!/usr/bin/env python3
"""
Test Run Workflow API Endpoint

Tests the /create/queue-workflow endpoint that:
1. Generates workflow JSON from inputs
2. Uploads workflow to remote instance
3. Queues workflow via BrowserAgent
4. Returns prompt_id for tracking

Usage:
    python3 test/test_run_workflow_api.py
"""

import sys
import json
import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.sync.create_api import create_bp
from flask import Flask


class TestRunWorkflowAPI(unittest.TestCase):
    """Test the Run Workflow API endpoint"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = Flask(__name__)
        self.app.register_blueprint(create_bp, url_prefix='/create')
        self.client = self.app.test_client()
        
        # Sample workflow inputs
        self.valid_inputs = {
            'ssh_connection': 'ssh -p 12345 root@example.com',
            'workflow_id': 'IMG_to_VIDEO_canvas',
            'inputs': {
                'input_image': 'data:image/jpeg;base64,/9j/4AAQSkZJRg...',
                'positive_prompt': 'A beautiful scene',
                'negative_prompt': 'blurry',
                'seed': 42,
                'cfg': 3.5,
                'steps': 20,
                'duration': 5.0
            }
        }
        
        # Mock workflow template
        self.mock_workflow_template = {
            'nodes': [
                {
                    'id': 85,
                    'type': 'mxSlider',
                    'widgets_values': ['{{CFG}}', '{{CFG}}', 1]
                },
                {
                    'id': 408,
                    'type': 'PrimitiveStringMultiline',
                    'widgets_values': ['{{POSITIVE_PROMPT}}']
                }
            ],
            'links': []
        }
        
        # Mock webui config
        self.mock_webui_config = {
            'inputs': [
                {
                    'id': 'cfg',
                    'token': '{{CFG}}',
                    'type': 'slider',
                    'default': 3.5
                },
                {
                    'id': 'positive_prompt',
                    'token': '{{POSITIVE_PROMPT}}',
                    'type': 'textarea',
                    'default': ''
                }
            ]
        }
    
    @patch('app.sync.create_api.paramiko.SSHClient')
    @patch('app.sync.create_api.load_workflow_json')
    @patch('app.sync.create_api.load_webui_wrapper')
    @patch('app.sync.create_api.WorkflowGenerator')
    @patch('app.sync.create_api.WorkflowValidator')
    def test_queue_workflow_success(self, mock_validator, mock_generator, 
                                    mock_load_webui, mock_load_json, mock_ssh):
        """Test successful workflow queueing"""
        
        # Setup mocks
        mock_load_json.return_value = self.mock_workflow_template
        mock_load_webui.return_value = self.mock_webui_config
        
        # Mock generator
        mock_gen_instance = MagicMock()
        mock_gen_instance.generate_workflow.return_value = self.mock_workflow_template
        mock_generator.return_value = mock_gen_instance
        
        # Mock validator
        mock_val_instance = MagicMock()
        mock_val_instance.validate_workflow.return_value = {'valid': True}
        mock_validator.return_value = mock_val_instance
        
        # Mock SSH connection
        mock_ssh_instance = MagicMock()
        mock_ssh.return_value = mock_ssh_instance
        
        # Mock SFTP
        mock_sftp = MagicMock()
        mock_ssh_instance.open_sftp.return_value = mock_sftp
        
        # Mock exec_command for browser server check
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b'browser_server is running'
        mock_ssh_instance.exec_command.return_value = (None, mock_stdout, MagicMock())
        
        # Mock exec_command for queueing workflow
        def exec_command_side_effect(cmd, **kwargs):
            if 'queue_workflow_ui_click.py' in cmd:
                mock_queue_stdout = MagicMock()
                mock_queue_stdout.read.return_value = b'Workflow queued successfully!\nPrompt ID: abc-123-def-456'
                mock_queue_stderr = MagicMock()
                mock_queue_stderr.read.return_value = b''
                return (None, mock_queue_stdout, mock_queue_stderr)
            return (None, mock_stdout, MagicMock())
        
        mock_ssh_instance.exec_command.side_effect = exec_command_side_effect
        
        # Make request
        response = self.client.post(
            '/create/queue-workflow',
            json=self.valid_inputs,
            content_type='application/json'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['prompt_id'], 'abc-123-def-456')
        self.assertIn('queued successfully', data['message'])
        
        # Verify SSH was called correctly
        mock_ssh_instance.connect.assert_called_once()
        mock_sftp.put.assert_called_once()
        
    def test_queue_workflow_missing_ssh_connection(self):
        """Test missing SSH connection"""
        invalid_inputs = self.valid_inputs.copy()
        del invalid_inputs['ssh_connection']
        
        response = self.client.post(
            '/create/queue-workflow',
            json=invalid_inputs,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('SSH connection', data['message'])
    
    def test_queue_workflow_missing_workflow_id(self):
        """Test missing workflow ID"""
        invalid_inputs = self.valid_inputs.copy()
        del invalid_inputs['workflow_id']
        
        response = self.client.post(
            '/create/queue-workflow',
            json=invalid_inputs,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('Workflow ID', data['message'])
    
    @patch('app.sync.create_api.load_workflow_json')
    def test_queue_workflow_not_found(self, mock_load_json):
        """Test workflow file not found"""
        mock_load_json.return_value = None
        
        response = self.client.post(
            '/create/queue-workflow',
            json=self.valid_inputs,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('not found', data['message'])
    
    @patch('app.sync.create_api.paramiko.SSHClient')
    @patch('app.sync.create_api.load_workflow_json')
    @patch('app.sync.create_api.load_webui_wrapper')
    @patch('app.sync.create_api.WorkflowGenerator')
    @patch('app.sync.create_api.WorkflowValidator')
    def test_queue_workflow_validation_failure(self, mock_validator, mock_generator,
                                               mock_load_webui, mock_load_json, mock_ssh):
        """Test workflow validation failure"""
        
        # Setup mocks
        mock_load_json.return_value = self.mock_workflow_template
        mock_load_webui.return_value = self.mock_webui_config
        
        # Mock generator
        mock_gen_instance = MagicMock()
        mock_gen_instance.generate_workflow.return_value = self.mock_workflow_template
        mock_generator.return_value = mock_gen_instance
        
        # Mock validator - return validation failure
        mock_val_instance = MagicMock()
        mock_val_instance.validate_workflow.return_value = {
            'valid': False,
            'errors': ['Missing required node', 'Invalid link']
        }
        mock_validator.return_value = mock_val_instance
        
        response = self.client.post(
            '/create/queue-workflow',
            json=self.valid_inputs,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('validation', data['message'].lower())
        self.assertIn('errors', data)
    
    @patch('app.sync.create_api.paramiko.SSHClient')
    @patch('app.sync.create_api.load_workflow_json')
    @patch('app.sync.create_api.load_webui_wrapper')
    @patch('app.sync.create_api.WorkflowGenerator')
    @patch('app.sync.create_api.WorkflowValidator')
    def test_queue_workflow_ssh_auth_failure(self, mock_validator, mock_generator,
                                             mock_load_webui, mock_load_json, mock_ssh):
        """Test SSH authentication failure"""
        
        # Setup mocks
        mock_load_json.return_value = self.mock_workflow_template
        mock_load_webui.return_value = self.mock_webui_config
        
        mock_gen_instance = MagicMock()
        mock_gen_instance.generate_workflow.return_value = self.mock_workflow_template
        mock_generator.return_value = mock_gen_instance
        
        mock_val_instance = MagicMock()
        mock_val_instance.validate_workflow.return_value = {'valid': True}
        mock_validator.return_value = mock_val_instance
        
        # Mock SSH - raise authentication error
        import paramiko
        mock_ssh_instance = MagicMock()
        mock_ssh_instance.connect.side_effect = paramiko.AuthenticationException('Auth failed')
        mock_ssh.return_value = mock_ssh_instance
        
        response = self.client.post(
            '/create/queue-workflow',
            json=self.valid_inputs,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('authentication', data['message'].lower())
    
    @patch('app.sync.create_api.paramiko.SSHClient')
    @patch('app.sync.create_api.load_workflow_json')
    @patch('app.sync.create_api.load_webui_wrapper')
    @patch('app.sync.create_api.WorkflowGenerator')
    @patch('app.sync.create_api.WorkflowValidator')
    def test_queue_workflow_no_prompt_id(self, mock_validator, mock_generator,
                                         mock_load_webui, mock_load_json, mock_ssh):
        """Test queueing succeeds but no prompt ID returned"""
        
        # Setup mocks
        mock_load_json.return_value = self.mock_workflow_template
        mock_load_webui.return_value = self.mock_webui_config
        
        mock_gen_instance = MagicMock()
        mock_gen_instance.generate_workflow.return_value = self.mock_workflow_template
        mock_generator.return_value = mock_gen_instance
        
        mock_val_instance = MagicMock()
        mock_val_instance.validate_workflow.return_value = {'valid': True}
        mock_validator.return_value = mock_val_instance
        
        mock_ssh_instance = MagicMock()
        mock_ssh.return_value = mock_ssh_instance
        
        mock_sftp = MagicMock()
        mock_ssh_instance.open_sftp.return_value = mock_sftp
        
        # Mock queueing output without prompt ID
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b'browser_server is running'
        
        def exec_command_side_effect(cmd, **kwargs):
            if 'queue_workflow_ui_click.py' in cmd:
                mock_queue_stdout = MagicMock()
                mock_queue_stdout.read.return_value = b'Workflow sent but no response'
                mock_queue_stderr = MagicMock()
                mock_queue_stderr.read.return_value = b''
                return (None, mock_queue_stdout, mock_queue_stderr)
            return (None, mock_stdout, MagicMock())
        
        mock_ssh_instance.exec_command.side_effect = exec_command_side_effect
        
        response = self.client.post(
            '/create/queue-workflow',
            json=self.valid_inputs,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('no prompt ID', data['message'])


def run_tests():
    """Run all tests"""
    print("=" * 80)
    print("Run Workflow API Tests")
    print("=" * 80)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestRunWorkflowAPI)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())
