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
        """Test that IMG to VIDEO workflow has workflow_json"""
        response = self.app.get('/create/workflows/img_to_video')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        workflow = data['workflow']
        self.assertIsNotNone(workflow.get('workflow_json'))
        self.assertIn('73', workflow['workflow_json'])  # Seed node

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
                                        'duration': 5
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


if __name__ == '__main__':
    unittest.main()
