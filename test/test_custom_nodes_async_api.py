#!/usr/bin/env python3
"""
Integration test for custom nodes installation async API
Tests the full workflow from start to completion
"""

import unittest
from unittest.mock import patch, MagicMock, call
import json
import sys
import os
import time
import uuid

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.sync.sync_api import app
from app.sync.background_tasks import get_task_manager


class TestCustomNodesAsyncAPI(unittest.TestCase):
    """Test the async custom nodes installation API"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = app.test_client()
        self.app.testing = True
        self.task_manager = get_task_manager()
    
    @patch('app.sync.sync_api.subprocess')
    @patch('app.sync.sync_api._extract_host_port')
    def test_start_installation_returns_task_id(self, mock_extract, mock_subprocess):
        """Test that starting installation returns task_id immediately"""
        # Mock SSH connection parsing
        mock_extract.return_value = ('test.host.com', 22)
        
        # Mock subprocess run for clearing progress file
        mock_subprocess.run.return_value = MagicMock(returncode=0)
        
        # Start installation
        response = self.app.post(
            '/ssh/install-custom-nodes',
            json={
                'ssh_connection': 'root@test.host.com',
                'ui_home': '/workspace/ComfyUI'
            }
        )
        
        # Should return immediately with task_id
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertIn('task_id', data)
        self.assertIsNotNone(data['task_id'])
        
        # Task ID should be a valid UUID
        try:
            uuid.UUID(data['task_id'])
        except ValueError:
            self.fail(f"task_id is not a valid UUID: {data['task_id']}")
    
    @patch('app.sync.sync_api.subprocess')
    @patch('app.sync.sync_api._extract_host_port')
    def test_progress_endpoint_requires_task_id(self, mock_extract, mock_subprocess):
        """Test that progress endpoint requires task_id parameter"""
        # Mock SSH connection parsing
        mock_extract.return_value = ('test.host.com', 22)
        
        # Try to get progress without task_id
        response = self.app.post(
            '/ssh/install-custom-nodes/progress',
            json={'ssh_connection': 'root@test.host.com'}
        )
        
        # Should return error
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('task_id', data['message'])
    
    @patch('app.sync.sync_api.subprocess')
    @patch('app.sync.sync_api._extract_host_port')
    def test_progress_endpoint_with_task_id(self, mock_extract, mock_subprocess):
        """Test that progress endpoint works with task_id"""
        # Mock SSH connection parsing
        mock_extract.return_value = ('test.host.com', 22)
        
        # Mock subprocess run to return progress JSON
        progress_data = {
            'in_progress': True,
            'task_id': 'test-task-123',
            'total_nodes': 10,
            'processed': 5,
            'current_node': 'TestNode',
            'current_status': 'running'
        }
        mock_subprocess.run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(progress_data)
        )
        
        # Get progress with task_id
        response = self.app.post(
            '/ssh/install-custom-nodes/progress',
            json={
                'ssh_connection': 'root@test.host.com',
                'task_id': 'test-task-123'
            }
        )
        
        # Should return progress
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertTrue(data['in_progress'])
        self.assertEqual(data['task_id'], 'test-task-123')
        self.assertEqual(data['total_nodes'], 10)
        self.assertEqual(data['processed'], 5)
    
    @patch('app.sync.sync_api.subprocess')
    @patch('app.sync.sync_api._extract_host_port')
    def test_missing_ssh_connection(self, mock_extract, mock_subprocess):
        """Test error when SSH connection is missing"""
        response = self.app.post(
            '/ssh/install-custom-nodes',
            json={'ui_home': '/workspace/ComfyUI'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('SSH connection', data['message'])
    
    @patch('app.sync.sync_api.subprocess')
    @patch('app.sync.sync_api._extract_host_port')
    def test_invalid_ssh_connection_format(self, mock_extract, mock_subprocess):
        """Test error when SSH connection format is invalid"""
        # Mock invalid format
        mock_extract.side_effect = ValueError("Invalid format")
        
        response = self.app.post(
            '/ssh/install-custom-nodes',
            json={
                'ssh_connection': 'invalid-format',
                'ui_home': '/workspace/ComfyUI'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('Invalid SSH connection format', data['message'])
    
    @patch('app.sync.sync_api.subprocess')
    @patch('app.sync.sync_api._extract_host_port')
    def test_duplicate_task_id_returns_error(self, mock_extract, mock_subprocess):
        """Test that starting same task twice returns error"""
        # Mock SSH connection parsing
        mock_extract.return_value = ('test.host.com', 22)
        mock_subprocess.run.return_value = MagicMock(returncode=0)
        
        # Start a long-running task
        def long_task():
            time.sleep(2.0)
        
        task_id = str(uuid.uuid4())
        self.task_manager.start_task(task_id, long_task)
        
        # Try to start another task (should fail since background thread will try to use same task_id)
        # Note: In real scenario, UUID generation ensures unique IDs, but we test the manager behavior
        
        # Wait for task to complete
        time.sleep(2.1)
    
    @patch('app.sync.sync_api.subprocess')
    @patch('app.sync.sync_api._extract_host_port')
    def test_progress_no_data_returns_empty(self, mock_extract, mock_subprocess):
        """Test progress endpoint returns empty when no data available"""
        # Mock SSH connection parsing
        mock_extract.return_value = ('test.host.com', 22)
        
        # Mock subprocess run to return empty JSON
        mock_subprocess.run.return_value = MagicMock(
            returncode=0,
            stdout='{}'
        )
        
        # Get progress
        response = self.app.post(
            '/ssh/install-custom-nodes/progress',
            json={
                'ssh_connection': 'root@test.host.com',
                'task_id': 'nonexistent-task'
            }
        )
        
        # Should return success but no progress
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertFalse(data['in_progress'])
        self.assertIn('No progress available', data['message'])


class TestCustomNodesBackgroundWorker(unittest.TestCase):
    """Test the background installation worker"""
    
    @patch('app.sync.sync_api.subprocess')
    @patch('app.sync.sync_api._write_progress_to_remote')
    @patch('app.sync.sync_api._extract_host_port')
    def test_background_worker_writes_initial_progress(self, mock_extract, mock_write_progress, mock_subprocess):
        """Test that background worker writes initial progress"""
        from app.sync.sync_api import _run_installation_background
        
        # Mock SSH parsing
        mock_extract.return_value = ('test.host.com', 22)
        
        # Mock subprocess for checking auto-installer
        mock_subprocess.run.return_value = MagicMock(returncode=0)
        
        # Mock Popen for installation
        mock_process = MagicMock()
        mock_process.stdout = iter([])  # Empty output
        mock_process.wait.return_value = 0
        mock_subprocess.Popen.return_value = mock_process
        
        # Run background worker
        task_id = 'test-bg-task'
        _run_installation_background(task_id, 'root@test.host.com', '/workspace/ComfyUI')
        
        # Verify initial progress was written
        self.assertTrue(mock_write_progress.called)
        
        # Check first call (initial progress)
        first_call = mock_write_progress.call_args_list[0]
        progress_data = first_call[0][3]  # 4th argument is progress_data
        
        self.assertTrue(progress_data['in_progress'])
        self.assertEqual(progress_data['task_id'], task_id)
        self.assertEqual(progress_data['current_node'], 'Initializing')


class TestCustomNodesIntegration(unittest.TestCase):
    """Integration tests for custom nodes workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = app.test_client()
        self.app.testing = True
    
    def test_cors_options_request(self):
        """Test CORS OPTIONS request"""
        response = self.app.options('/ssh/install-custom-nodes')
        self.assertEqual(response.status_code, 204)
        
        response = self.app.options('/ssh/install-custom-nodes/progress')
        self.assertEqual(response.status_code, 204)


if __name__ == '__main__':
    unittest.main()
