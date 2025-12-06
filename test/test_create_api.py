#!/usr/bin/env python3
"""
Test the Create API endpoints
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.sync.sync_api import app


class TestCreateAPI(unittest.TestCase):
    """Test the Create API endpoints"""

    def setUp(self):
        """Set up test fixtures"""
        self.app = app.test_client()
        self.app.testing = True

    def test_workflows_list_endpoint(self):
        """Test the workflow list endpoint"""
        response = self.app.get('/create/workflows/list')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('workflows', data)
        self.assertIn('count', data)
        self.assertIsInstance(data['workflows'], list)

    def test_workflows_list_contains_img_to_video(self):
        """Test that IMG_to_VIDEO workflow is in the list"""
        response = self.app.get('/create/workflows/list')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Find the IMG to VIDEO workflow
        workflow_names = [w['name'] for w in data['workflows']]
        self.assertIn('IMG to VIDEO', workflow_names)

    def test_workflow_get_img_to_video(self):
        """Test getting IMG to VIDEO workflow details"""
        response = self.app.get('/create/workflows/img_to_video')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('workflow', data)
        
        workflow = data['workflow']
        self.assertEqual(workflow['name'], 'IMG to VIDEO')
        self.assertIn('inputs', workflow)
        self.assertIn('advanced', workflow)
        self.assertIsInstance(workflow['inputs'], list)
        self.assertIsInstance(workflow['advanced'], list)
        self.assertGreater(len(workflow['inputs']), 0)

    def test_workflow_get_img_to_video_has_workflow_json(self):
        """Test that IMG to VIDEO workflow has workflow_json with nodes"""
        response = self.app.get('/create/workflows/img_to_video')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        workflow = data['workflow']
        self.assertIsNotNone(workflow.get('workflow_json'))
        # Verify workflow_json contains node entries (keys are node IDs)
        self.assertIsInstance(workflow['workflow_json'], dict)
        self.assertGreater(len(workflow['workflow_json']), 0)
        # Verify at least one node has expected structure
        for node_id, node_data in workflow['workflow_json'].items():
            self.assertIn('class_type', node_data)
            break  # Just check first node

    def test_workflow_get_not_found(self):
        """Test getting a non-existent workflow"""
        response = self.app.get('/create/workflows/nonexistent_workflow')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('message', data)

    def test_execute_missing_ssh_connection(self):
        """Test execute endpoint with missing SSH connection"""
        response = self.app.post('/create/execute',
                                json={'workflow_id': 'img_to_video'},
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('SSH connection string is required', data['message'])

    def test_execute_missing_workflow_id(self):
        """Test execute endpoint with missing workflow ID"""
        response = self.app.post('/create/execute',
                                json={'ssh_connection': 'ssh -p 2838 root@test'},
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('Workflow ID is required', data['message'])

    def test_execute_nonexistent_workflow(self):
        """Test execute endpoint with non-existent workflow"""
        response = self.app.post('/create/execute',
                                json={
                                    'ssh_connection': 'ssh -p 2838 root@test',
                                    'workflow_id': 'nonexistent'
                                },
                                content_type='application/json')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('Workflow not found', data['message'])

    def test_execute_valid_request(self):
        """Test execute endpoint with valid request"""
        response = self.app.post('/create/execute',
                                json={
                                    'ssh_connection': 'ssh -p 2838 root@test',
                                    'workflow_id': 'img_to_video',
                                    'inputs': {
                                        'positive_prompt': 'test prompt',
                                        'duration': 5,
                                        'input_image': 'test_image.png',
                                        'main_model': {
                                            'highNoisePath': 'test/high_noise.safetensors',
                                            'lowNoisePath': 'test/low_noise.safetensors'
                                        },
                                        'clip_model': 'test/clip_model.safetensors',
                                        'vae_model': 'test/vae_model.safetensors',
                                        'upscale_model': 'test/upscale_model.pth'
                                    }
                                },
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('task_id', data)
        self.assertIn('message', data)

    def test_status_endpoint(self):
        """Test status endpoint"""
        response = self.app.get('/create/status/test-task-id')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['task_id'], 'test-task-id')
        self.assertIn('status', data)
        self.assertIn('progress', data)

    def test_workflow_inputs_have_required_fields(self):
        """Test that workflow inputs have required fields"""
        response = self.app.get('/create/workflows/img_to_video')
        data = json.loads(response.data)
        
        for input_field in data['workflow']['inputs']:
            self.assertIn('id', input_field)
            self.assertIn('type', input_field)
            self.assertIn('label', input_field)

    def test_options_request_workflows_list(self):
        """Test OPTIONS request for CORS preflight"""
        response = self.app.options('/create/workflows/list')
        self.assertEqual(response.status_code, 204)

    def test_options_request_execute(self):
        """Test OPTIONS request for execute endpoint"""
        response = self.app.options('/create/execute')
        self.assertEqual(response.status_code, 204)

    # --- New tests for generate-workflow endpoint ---
    
    def test_generate_workflow_missing_workflow_id(self):
        """Test generate-workflow endpoint with missing workflow_id"""
        response = self.app.post('/create/generate-workflow',
                                json={'inputs': {}},
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('workflow_id is required', data['message'])

    def test_generate_workflow_nonexistent_workflow(self):
        """Test generate-workflow endpoint with non-existent workflow"""
        response = self.app.post('/create/generate-workflow',
                                json={'workflow_id': 'nonexistent'},
                                content_type='application/json')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])

    def test_generate_workflow_validation_failure(self):
        """Test generate-workflow endpoint with validation failure"""
        response = self.app.post('/create/generate-workflow',
                                json={
                                    'workflow_id': 'img_to_video',
                                    'inputs': {
                                        'duration': 5
                                        # Missing required fields
                                    }
                                },
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('errors', data)
        self.assertIsInstance(data['errors'], list)
        self.assertGreater(len(data['errors']), 0)

    def test_generate_workflow_valid_request(self):
        """Test generate-workflow endpoint with valid request"""
        response = self.app.post('/create/generate-workflow',
                                json={
                                    'workflow_id': 'img_to_video',
                                    'inputs': {
                                        'positive_prompt': 'test prompt',
                                        'duration': 5,
                                        'input_image': 'test_image.png',
                                        'main_model': {
                                            'highNoisePath': 'test/high_noise.safetensors',
                                            'lowNoisePath': 'test/low_noise.safetensors'
                                        },
                                        'clip_model': 'test/clip_model.safetensors',
                                        'vae_model': 'test/vae_model.safetensors',
                                        'upscale_model': 'test/upscale_model.pth'
                                    }
                                },
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('workflow', data)
        self.assertIn('metadata', data)
        self.assertIsInstance(data['workflow'], dict)
        self.assertIn('workflow_id', data['metadata'])
        self.assertIn('generated_at', data['metadata'])

    def test_generate_workflow_applies_inputs(self):
        """Test that generate-workflow actually applies input values"""
        response = self.app.post('/create/generate-workflow',
                                json={
                                    'workflow_id': 'img_to_video',
                                    'inputs': {
                                        'positive_prompt': 'test prompt for verification',
                                        'duration': 7.5,
                                        'steps': 25,
                                        'input_image': 'test_image.png',
                                        'main_model': {
                                            'highNoisePath': 'test/high_noise.safetensors',
                                            'lowNoisePath': 'test/low_noise.safetensors'
                                        },
                                        'clip_model': 'test/clip_model.safetensors',
                                        'vae_model': 'test/vae_model.safetensors',
                                        'upscale_model': 'test/upscale_model.pth'
                                    }
                                },
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        workflow = data['workflow']
        
        # Check that duration was applied (node 426, field Xi)
        self.assertEqual(workflow['426']['inputs']['Xi'], 7.5)
        
        # Check that steps were applied (node 82, fields Xi and Xf)
        self.assertEqual(workflow['82']['inputs']['Xi'], 25)
        self.assertEqual(workflow['82']['inputs']['Xf'], 25)
        
        # Check that image was applied (node 88, field image)
        self.assertEqual(workflow['88']['inputs']['image'], 'test_image.png')

    def test_options_request_generate_workflow(self):
        """Test OPTIONS request for generate-workflow endpoint"""
        response = self.app.options('/create/generate-workflow')
        self.assertEqual(response.status_code, 204)

    # --- New tests for cancel endpoint ---

    def test_cancel_nonexistent_task(self):
        """Test cancel endpoint with non-existent task"""
        response = self.app.post('/create/cancel/nonexistent-task-id',
                                content_type='application/json')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('Task not found', data['message'])

    def test_cancel_valid_task(self):
        """Test cancel endpoint with a valid task"""
        # First, create a task by executing a workflow
        execute_response = self.app.post('/create/execute',
                                json={
                                    'ssh_connection': 'ssh -p 2838 root@test',
                                    'workflow_id': 'img_to_video',
                                    'inputs': {
                                        'positive_prompt': 'test prompt',
                                        'duration': 5,
                                        'input_image': 'test_image.png',
                                        'main_model': {
                                            'highNoisePath': 'test/high_noise.safetensors',
                                            'lowNoisePath': 'test/low_noise.safetensors'
                                        },
                                        'clip_model': 'test/clip_model.safetensors',
                                        'vae_model': 'test/vae_model.safetensors',
                                        'upscale_model': 'test/upscale_model.pth'
                                    }
                                },
                                content_type='application/json')
        
        execute_data = json.loads(execute_response.data)
        task_id = execute_data['task_id']
        
        # Now cancel it
        cancel_response = self.app.post(f'/create/cancel/{task_id}',
                                content_type='application/json')
        self.assertEqual(cancel_response.status_code, 200)
        
        cancel_data = json.loads(cancel_response.data)
        self.assertTrue(cancel_data['success'])
        self.assertEqual(cancel_data['task_id'], task_id)
        self.assertIn('cancelled successfully', cancel_data['message'])

    def test_cancel_already_cancelled_task(self):
        """Test cancel endpoint with already cancelled task"""
        # First, create and cancel a task
        execute_response = self.app.post('/create/execute',
                                json={
                                    'ssh_connection': 'ssh -p 2838 root@test',
                                    'workflow_id': 'img_to_video',
                                    'inputs': {
                                        'positive_prompt': 'test prompt',
                                        'duration': 5,
                                        'input_image': 'test_image.png',
                                        'main_model': {
                                            'highNoisePath': 'test/high_noise.safetensors',
                                            'lowNoisePath': 'test/low_noise.safetensors'
                                        },
                                        'clip_model': 'test/clip_model.safetensors',
                                        'vae_model': 'test/vae_model.safetensors',
                                        'upscale_model': 'test/upscale_model.pth'
                                    }
                                },
                                content_type='application/json')
        
        execute_data = json.loads(execute_response.data)
        task_id = execute_data['task_id']
        
        # Cancel it first time
        self.app.post(f'/create/cancel/{task_id}', content_type='application/json')
        
        # Try to cancel again
        cancel_response = self.app.post(f'/create/cancel/{task_id}',
                                content_type='application/json')
        self.assertEqual(cancel_response.status_code, 400)
        
        cancel_data = json.loads(cancel_response.data)
        self.assertFalse(cancel_data['success'])
        self.assertIn('Cannot cancel task with status', cancel_data['message'])

    def test_options_request_cancel(self):
        """Test OPTIONS request for cancel endpoint"""
        response = self.app.options('/create/cancel/test-task-id')
        self.assertEqual(response.status_code, 204)

    # --- Tests for enhanced status endpoint ---

    def test_status_returns_task_details(self):
        """Test status endpoint returns full task details for registered task"""
        # First, create a task
        execute_response = self.app.post('/create/execute',
                                json={
                                    'ssh_connection': 'ssh -p 2838 root@test',
                                    'workflow_id': 'img_to_video',
                                    'inputs': {
                                        'positive_prompt': 'test prompt',
                                        'duration': 5,
                                        'input_image': 'test_image.png',
                                        'main_model': {
                                            'highNoisePath': 'test/high_noise.safetensors',
                                            'lowNoisePath': 'test/low_noise.safetensors'
                                        },
                                        'clip_model': 'test/clip_model.safetensors',
                                        'vae_model': 'test/vae_model.safetensors',
                                        'upscale_model': 'test/upscale_model.pth'
                                    }
                                },
                                content_type='application/json')
        
        execute_data = json.loads(execute_response.data)
        task_id = execute_data['task_id']
        
        # Get status
        status_response = self.app.get(f'/create/status/{task_id}')
        self.assertEqual(status_response.status_code, 200)
        
        status_data = json.loads(status_response.data)
        self.assertTrue(status_data['success'])
        self.assertEqual(status_data['task_id'], task_id)
        self.assertEqual(status_data['workflow_id'], 'img_to_video')
        self.assertIn('status', status_data)
        self.assertIn('progress', status_data)
        self.assertIn('started_at', status_data)
        self.assertIn('elapsed_seconds', status_data)


if __name__ == '__main__':
    unittest.main()
