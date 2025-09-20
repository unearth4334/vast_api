#!/usr/bin/env python3
"""
Test the new VastAI instance-specific sync functionality
"""
import unittest
import json
import sys
import os
from unittest.mock import patch, MagicMock

# Add the parent directory to the path to import the app
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.sync.sync_api import app

class TestVastAIInstanceSync(unittest.TestCase):
    def setUp(self):
        """Set up test client"""
        self.app = app.test_client()
        self.app.testing = True

    def test_sync_vastai_instance_success(self):
        """Test successful sync with specific instance"""
        with patch('app.sync.sync_api.run_sync') as mock_run_sync:
            # Mock successful sync result
            mock_run_sync.return_value = {
                'success': True,
                'message': 'VastAI Instance #123 sync completed successfully',
                'sync_id': 'test-sync-id-123'
            }
            
            response = self.app.post('/sync/vastai/instance',
                                   data=json.dumps({
                                       'ssh_host': 'test.example.com',
                                       'ssh_port': 2222,
                                       'instance_id': '123',
                                       'cleanup': True
                                   }),
                                   content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertIn('Instance #123', data['message'])
            self.assertEqual(data['instance_info']['id'], '123')
            self.assertEqual(data['instance_info']['host'], 'test.example.com')
            self.assertEqual(data['instance_info']['port'], '2222')
            
            # Verify run_sync was called with correct parameters
            mock_run_sync.assert_called_once_with(
                'test.example.com', '2222', 'VastAI Instance #123', cleanup=True
            )

    def test_sync_vastai_instance_missing_host(self):
        """Test sync fails when SSH host is missing"""
        response = self.app.post('/sync/vastai/instance',
                               data=json.dumps({
                                   'ssh_port': 2222,
                                   'instance_id': '123',
                                   'cleanup': True
                               }),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('SSH host is required', data['message'])

    def test_sync_vastai_instance_missing_instance_id(self):
        """Test sync fails when instance ID is missing"""
        response = self.app.post('/sync/vastai/instance',
                               data=json.dumps({
                                   'ssh_host': 'test.example.com',
                                   'ssh_port': 2222,
                                   'cleanup': True
                               }),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('Instance ID is required', data['message'])

    def test_sync_vastai_instance_invalid_json(self):
        """Test sync fails with invalid JSON"""
        response = self.app.post('/sync/vastai/instance',
                               data='invalid json',
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['success'])

    def test_sync_vastai_instance_no_json(self):
        """Test sync fails when no JSON data is provided"""
        response = self.app.post('/sync/vastai/instance')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('Request must contain JSON data', data['message'])

    def test_sync_vastai_instance_failure(self):
        """Test handling of sync failure"""
        with patch('app.sync.sync_api.run_sync') as mock_run_sync:
            # Mock failed sync result
            mock_run_sync.return_value = {
                'success': False,
                'message': 'Sync failed: SSH connection refused',
                'error': 'Connection failed'
            }
            
            response = self.app.post('/sync/vastai/instance',
                                   data=json.dumps({
                                       'ssh_host': 'bad.example.com',
                                       'ssh_port': 2222,
                                       'instance_id': '456',
                                       'cleanup': False
                                   }),
                                   content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertFalse(data['success'])
            self.assertIn('SSH connection refused', data['message'])
            
            # Verify run_sync was called with correct parameters including cleanup=False
            mock_run_sync.assert_called_once_with(
                'bad.example.com', '2222', 'VastAI Instance #456', cleanup=False
            )

    def test_sync_vastai_instance_default_port(self):
        """Test that default port 22 is used when not specified"""
        with patch('app.sync.sync_api.run_sync') as mock_run_sync:
            mock_run_sync.return_value = {
                'success': True,
                'message': 'Sync completed',
                'sync_id': 'test-sync-id'
            }
            
            response = self.app.post('/sync/vastai/instance',
                                   data=json.dumps({
                                       'ssh_host': 'test.example.com',
                                       'instance_id': '789'
                                   }),
                                   content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertEqual(data['instance_info']['port'], '22')
            
            # Verify run_sync was called with default port and cleanup
            mock_run_sync.assert_called_once_with(
                'test.example.com', '22', 'VastAI Instance #789', cleanup=True
            )

    def test_sync_vastai_instance_options_request(self):
        """Test OPTIONS request for CORS"""
        response = self.app.options('/sync/vastai/instance')
        self.assertEqual(response.status_code, 204)

if __name__ == '__main__':
    unittest.main()