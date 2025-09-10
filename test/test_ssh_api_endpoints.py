#!/usr/bin/env python3
"""
Tests for SSH API endpoints
"""

import unittest
import json
import sys
import os
from unittest.mock import patch, MagicMock

# Add the app directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from app.sync.sync_api import app
except ImportError:
    # Try alternative import
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
    from sync.sync_api import app


class TestSSHAPIEndpoints(unittest.TestCase):
    """Test SSH API endpoints"""
    
    def setUp(self):
        """Set up test client"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
    
    @patch('app.sync.sync_api.SSHIdentityManager')
    def test_ssh_status_endpoint_success(self, mock_ssh_manager_class):
        """Test successful SSH status endpoint"""
        # Mock SSH manager
        mock_manager = MagicMock()
        mock_manager.get_ssh_status.return_value = {
            'ready_for_sync': True,
            'validation': {
                'valid': True,
                'ssh_key_exists': True,
                'ssh_key_readable': True,
                'ssh_agent_running': True,
                'identity_loaded': True,
                'permissions_ok': True
            }
        }
        mock_ssh_manager_class.return_value = mock_manager
        
        response = self.client.get('/ssh/status')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('status', data)
        self.assertTrue(data['status']['ready_for_sync'])
    
    def test_ssh_status_endpoint_unavailable(self):
        """Test SSH status endpoint when SSH manager unavailable"""
        with patch('app.sync.sync_api.SSHIdentityManager', None):
            response = self.client.get('/ssh/status')
            data = json.loads(response.data)
            
            self.assertEqual(response.status_code, 500)
            self.assertFalse(data['success'])
            self.assertIn('not available', data['message'])
    
    @patch('app.sync.sync_api.SSHIdentityManager')
    def test_ssh_setup_endpoint_success(self, mock_ssh_manager_class):
        """Test successful SSH setup endpoint"""
        # Mock SSH manager
        mock_manager = MagicMock()
        mock_manager.ensure_ssh_permissions.return_value = {
            'success': True,
            'changes_made': ['Fixed SSH key permissions: 644 -> 600']
        }
        mock_manager.setup_ssh_agent.return_value = {
            'success': True,
            'identity_added': True,
            'message': 'SSH identity added successfully',
            'requires_user_confirmation': False
        }
        mock_ssh_manager_class.return_value = mock_manager
        
        response = self.client.post('/ssh/setup',
                                   data=json.dumps({'confirmed': True}),
                                   content_type='application/json')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertTrue(data['identity_added'])
        self.assertIn('permissions_fixed', data)
    
    @patch('app.sync.sync_api.SSHIdentityManager')
    def test_ssh_setup_endpoint_requires_confirmation(self, mock_ssh_manager_class):
        """Test SSH setup endpoint when user confirmation required"""
        # Mock SSH manager
        mock_manager = MagicMock()
        mock_manager.ensure_ssh_permissions.return_value = {
            'success': True,
            'changes_made': []
        }
        mock_manager.setup_ssh_agent.return_value = {
            'success': False,
            'requires_user_confirmation': True,
            'message': 'SSH key setup requires user confirmation'
        }
        mock_ssh_manager_class.return_value = mock_manager
        
        response = self.client.post('/ssh/setup',
                                   data=json.dumps({'confirmed': False}),
                                   content_type='application/json')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(data['success'])
        self.assertTrue(data['requires_confirmation'])
        self.assertIn('confirmation_message', data)
    
    @patch('app.sync.sync_api.SSHIdentityManager')
    def test_ssh_setup_endpoint_permission_failure(self, mock_ssh_manager_class):
        """Test SSH setup endpoint when permission fix fails"""
        # Mock SSH manager
        mock_manager = MagicMock()
        mock_manager.ensure_ssh_permissions.return_value = {
            'success': False,
            'errors': ['Permission denied']
        }
        mock_ssh_manager_class.return_value = mock_manager
        
        response = self.client.post('/ssh/setup')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
        self.assertIn('Failed to fix SSH permissions', data['message'])
    
    @patch('app.sync.sync_api.SSHIdentityManager')
    def test_ssh_test_endpoint_success(self, mock_ssh_manager_class):
        """Test successful SSH connection test endpoint"""
        # Mock SSH manager
        mock_manager = MagicMock()
        mock_manager.test_ssh_connection.return_value = {
            'success': True,
            'host': 'localhost',
            'port': 22,
            'user': 'root',
            'message': 'Connection successful in 0.5s',
            'response_time': 0.5
        }
        mock_ssh_manager_class.return_value = mock_manager
        
        response = self.client.post('/ssh/test',
                                   data=json.dumps({
                                       'host': 'localhost',
                                       'port': 22,
                                       'user': 'root',
                                       'timeout': 10
                                   }),
                                   content_type='application/json')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('result', data)
        self.assertTrue(data['result']['success'])
        self.assertEqual(data['result']['host'], 'localhost')
    
    @patch('app.sync.sync_api.SSHIdentityManager')
    def test_ssh_test_endpoint_missing_host(self, mock_ssh_manager_class):
        """Test SSH test endpoint with missing host parameter"""
        response = self.client.post('/ssh/test',
                                   data=json.dumps({'port': 22}),
                                   content_type='application/json')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('Host parameter required', data['message'])
    
    def test_ssh_test_endpoint_no_json(self):
        """Test SSH test endpoint without JSON body"""
        response = self.client.post('/ssh/test')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('JSON request body required', data['message'])
    
    @patch('app.sync.sync_api.SSHIdentityManager')
    def test_ssh_test_endpoint_connection_failure(self, mock_ssh_manager_class):
        """Test SSH test endpoint with connection failure"""
        # Mock SSH manager
        mock_manager = MagicMock()
        mock_manager.test_ssh_connection.return_value = {
            'success': False,
            'host': 'badhost',
            'port': 22,
            'user': 'root',
            'message': 'Connection failed: Connection refused'
        }
        mock_ssh_manager_class.return_value = mock_manager
        
        response = self.client.post('/ssh/test',
                                   data=json.dumps({'host': 'badhost'}),
                                   content_type='application/json')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(data['success'])
        self.assertFalse(data['result']['success'])
        self.assertIn('Connection failed', data['result']['message'])
    
    @patch('app.sync.sync_api.SSHIdentityManager')
    def test_ssh_cleanup_endpoint_success(self, mock_ssh_manager_class):
        """Test successful SSH cleanup endpoint"""
        # Mock SSH manager
        mock_manager = MagicMock()
        mock_manager.cleanup_ssh_agent.return_value = True
        mock_ssh_manager_class.return_value = mock_manager
        
        response = self.client.post('/ssh/cleanup')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('cleaned up', data['message'])
    
    @patch('app.sync.sync_api.SSHIdentityManager')
    def test_ssh_cleanup_endpoint_failure(self, mock_ssh_manager_class):
        """Test SSH cleanup endpoint failure"""
        # Mock SSH manager
        mock_manager = MagicMock()
        mock_manager.cleanup_ssh_agent.return_value = False
        mock_ssh_manager_class.return_value = mock_manager
        
        response = self.client.post('/ssh/cleanup')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(data['success'])
        self.assertIn('Failed to clean up', data['message'])
    
    def test_ssh_cleanup_endpoint_unavailable(self):
        """Test SSH cleanup endpoint when SSH manager unavailable"""
        with patch('app.sync.sync_api.SSHIdentityManager', None):
            response = self.client.post('/ssh/cleanup')
            data = json.loads(response.data)
            
            self.assertEqual(response.status_code, 500)
            self.assertFalse(data['success'])
            self.assertIn('not available', data['message'])
    
    def test_ssh_endpoints_options_requests(self):
        """Test OPTIONS requests for SSH endpoints"""
        endpoints = ['/ssh/status', '/ssh/setup', '/ssh/test', '/ssh/cleanup']
        
        for endpoint in endpoints:
            response = self.client.options(endpoint)
            self.assertEqual(response.status_code, 204)


if __name__ == '__main__':
    unittest.main()