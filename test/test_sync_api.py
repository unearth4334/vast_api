#!/usr/bin/env python3
"""
Test the sync API endpoints
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.sync.sync_api import app


class TestSyncAPI(unittest.TestCase):
    """Test the Flask API endpoints"""

    def setUp(self):
        """Set up test fixtures"""
        self.app = app.test_client()
        self.app.testing = True

    def test_index_endpoint(self):
        """Test the main web interface"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Media Sync Tool', response.data)
        self.assertIn(b'Sync Forge', response.data)
        self.assertIn(b'Sync Comfy', response.data)
        self.assertIn(b'Sync VastAI', response.data)

    @patch('app.sync.sync_api.VastManager')
    def test_status_endpoint_success(self, mock_vast_manager):
        """Test status endpoint with successful VastAI connection"""
        mock_instance = MagicMock()
        mock_instance.get_running_instance.return_value = {
            'id': 123,
            'cur_state': 'running',
            'ssh_host': 'test.host'
        }
        mock_vast_manager.return_value = mock_instance

        response = self.app.get('/status')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['forge']['available'])
        self.assertTrue(data['comfy']['available'])
        self.assertTrue(data['vastai']['available'])
        self.assertEqual(data['forge']['host'], '10.0.78.108')
        self.assertEqual(data['forge']['port'], '2222')
        self.assertEqual(data['comfy']['port'], '2223')

    def test_status_endpoint_health_check(self):
        """Test status endpoint with health check request (should not call VastAI API)"""
        response = self.app.get('/status', headers={'User-Agent': 'curl/7.68.0'})
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['forge']['available'])
        self.assertTrue(data['comfy']['available'])
        self.assertFalse(data['vastai']['available'])  # Should be False for health checks
        self.assertIn('not checked during health check', data['vastai']['message'])

    @patch('app.sync.sync_api.VastManager')
    def test_status_endpoint_vastai_error(self, mock_vast_manager):
        """Test status endpoint with VastAI connection error"""
        mock_vast_manager.side_effect = Exception("API error")

        # Test with a regular user agent (not curl)
        response = self.app.get('/status', headers={'User-Agent': 'Mozilla/5.0'})
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertFalse(data['vastai']['available'])
        self.assertIn('error', data['vastai'])

    @patch('app.sync.sync_api.run_sync')
    def test_sync_forge_success(self, mock_run_sync):
        """Test successful Forge sync"""
        mock_run_sync.return_value = {
            'success': True,
            'message': 'Forge sync completed successfully',
            'output': 'test output'
        }

        response = self.app.post('/sync/forge')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('Forge sync completed', data['message'])
        
        mock_run_sync.assert_called_once_with('10.0.78.108', '2222', 'Forge', cleanup=True)

    @patch('app.sync.sync_api.run_sync')
    def test_sync_comfy_success(self, mock_run_sync):
        """Test successful ComfyUI sync"""
        mock_run_sync.return_value = {
            'success': True,
            'message': 'ComfyUI sync completed successfully',
            'output': 'test output'
        }

        response = self.app.post('/sync/comfy')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('ComfyUI sync completed', data['message'])
        
        mock_run_sync.assert_called_once_with('10.0.78.108', '2223', 'ComfyUI', cleanup=True)

    @patch('app.sync.sync_api.VastManager')
    @patch('app.sync.sync_api.run_sync')
    def test_sync_vastai_success(self, mock_run_sync, mock_vast_manager):
        """Test successful VastAI sync"""
        # Mock VastManager
        mock_instance = MagicMock()
        mock_instance.get_running_instance.return_value = {
            'id': 123,
            'ssh_host': 'vast.example.com',
            'ssh_port': 12345,
            'gpu_name': 'RTX 4090'
        }
        mock_vast_manager.return_value = mock_instance

        # Mock run_sync
        mock_run_sync.return_value = {
            'success': True,
            'message': 'VastAI sync completed successfully',
            'output': 'test output'
        }

        response = self.app.post('/sync/vastai')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('VastAI sync completed', data['message'])
        self.assertIn('instance_info', data)
        self.assertEqual(data['instance_info']['id'], 123)
        self.assertEqual(data['instance_info']['host'], 'vast.example.com')
        
        mock_run_sync.assert_called_once_with('vast.example.com', '12345', 'VastAI', cleanup=True)

    @patch('app.sync.sync_api.VastManager')
    def test_sync_vastai_no_instance(self, mock_vast_manager):
        """Test VastAI sync when no running instance found"""
        mock_instance = MagicMock()
        mock_instance.get_running_instance.return_value = None
        mock_vast_manager.return_value = mock_instance

        response = self.app.post('/sync/vastai')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('No running VastAI instance', data['message'])

    @patch('app.sync.sync_api.VastManager')
    def test_sync_vastai_config_error(self, mock_vast_manager):
        """Test VastAI sync with configuration error"""
        mock_vast_manager.side_effect = FileNotFoundError("Config not found")

        response = self.app.post('/sync/vastai')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('configuration files not found', data['message'])

    @patch('app.sync.sync_api.SSHTester')
    def test_ssh_test_endpoint_success(self, mock_ssh_tester):
        """Test SSH test endpoint with successful connections"""
        mock_instance = MagicMock()
        mock_instance.test_all_hosts.return_value = {
            'summary': {
                'total_hosts': 2,
                'successful': 2,
                'failed': 0,
                'success_rate': '100.0%'
            },
            'results': {
                'forge': {
                    'host': 'forge',
                    'success': True,
                    'message': 'Connection successful'
                },
                'comfy': {
                    'host': 'comfy',
                    'success': True,
                    'message': 'Connection successful'
                }
            }
        }
        mock_ssh_tester.return_value = mock_instance

        response = self.app.post('/test/ssh')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('summary', data)
        self.assertIn('results', data)
        self.assertEqual(data['summary']['total_hosts'], 2)
        self.assertEqual(data['summary']['successful'], 2)

    @patch('app.sync.sync_api.SSHTester')
    def test_ssh_test_endpoint_partial_failure(self, mock_ssh_tester):
        """Test SSH test endpoint with partial failures"""
        mock_instance = MagicMock()
        mock_instance.test_all_hosts.return_value = {
            'summary': {
                'total_hosts': 2,
                'successful': 1,
                'failed': 1,
                'success_rate': '50.0%'
            },
            'results': {
                'forge': {
                    'host': 'forge',
                    'success': True,
                    'message': 'Connection successful'
                },
                'comfy': {
                    'host': 'comfy',
                    'success': False,
                    'message': 'Connection failed',
                    'error': 'Connection timeout'
                }
            }
        }
        mock_ssh_tester.return_value = mock_instance

        response = self.app.post('/test/ssh')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])  # Endpoint succeeded even with partial failures
        self.assertEqual(data['summary']['successful'], 1)
        self.assertEqual(data['summary']['failed'], 1)

    def test_ssh_test_endpoint_unavailable(self):
        """Test SSH test endpoint when SSHTester is not available"""
        # Temporarily replace SSHTester with None
        sync_api_module = __import__('app.sync.sync_api', fromlist=[''])
        original_ssh_tester = getattr(sync_api_module, 'SSHTester', None)
        setattr(sync_api_module, 'SSHTester', None)
        
        try:
            response = self.app.post('/test/ssh')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertFalse(data['success'])
            self.assertIn('SSH test functionality not available', data['message'])
        finally:
            # Restore original SSHTester
            setattr(sync_api_module, 'SSHTester', original_ssh_tester)

    @patch('app.sync.sync_api.run_sync')
    def test_sync_forge_with_cleanup_disabled(self, mock_run_sync):
        """Test Forge sync with cleanup disabled"""
        mock_run_sync.return_value = {
            'success': True,
            'message': 'Forge sync completed successfully',
            'output': 'test output'
        }

        response = self.app.post('/sync/forge', 
                                json={'cleanup': False},
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('Forge sync completed', data['message'])
        
        mock_run_sync.assert_called_once_with('10.0.78.108', '2222', 'Forge', cleanup=False)

    @patch('app.sync.sync_api.run_sync')
    def test_sync_comfy_with_cleanup_enabled(self, mock_run_sync):
        """Test ComfyUI sync with cleanup explicitly enabled"""
        mock_run_sync.return_value = {
            'success': True,
            'message': 'ComfyUI sync completed successfully',
            'output': 'test output'
        }

        response = self.app.post('/sync/comfy', 
                                json={'cleanup': True},
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('ComfyUI sync completed', data['message'])
        
        mock_run_sync.assert_called_once_with('10.0.78.108', '2223', 'ComfyUI', cleanup=True)

    @patch('app.sync.sync_api.VastManager')
    @patch('app.sync.sync_api.run_sync')
    def test_sync_vastai_with_cleanup_disabled(self, mock_run_sync, mock_vast_manager):
        """Test VastAI sync with cleanup disabled"""
        # Setup VastManager mock
        mock_instance = MagicMock()
        mock_instance.get_running_instance.return_value = {
            'id': 123,
            'gpu_name': 'RTX 4090',
            'ssh_host': 'vast.example.com',
            'ssh_port': 12345
        }
        mock_vast_manager.return_value = mock_instance

        mock_run_sync.return_value = {
            'success': True,
            'message': 'VastAI sync completed successfully',
            'output': 'test output'
        }

        response = self.app.post('/sync/vastai', 
                                json={'cleanup': False},
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('VastAI sync completed', data['message'])
        
        mock_run_sync.assert_called_once_with('vast.example.com', '12345', 'VastAI', cleanup=False)

    @patch('app.sync.sync_api.subprocess.run')
    def test_vastai_set_ui_home_success(self, mock_subprocess):
        """Test successful VastAI UI_HOME setting"""
        # Mock successful subprocess execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ''
        mock_subprocess.return_value = mock_result

        response = self.app.post('/vastai/set-ui-home',
                                json={
                                    'ssh_connection': 'ssh -p 2838 root@104.189.178.116',
                                    'ui_home': '/workspace/ComfyUI/'
                                },
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('UI_HOME set to /workspace/ComfyUI/ successfully', data['message'])
        
        # Verify SSH command was called correctly
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        self.assertIn('ssh', call_args)
        self.assertIn('-p', call_args)
        self.assertIn('2838', call_args)
        self.assertIn('root@104.189.178.116', call_args)

    @patch('app.sync.sync_api.subprocess.run')
    def test_vastai_set_ui_home_invalid_connection(self, mock_subprocess):
        """Test VastAI UI_HOME setting with invalid SSH connection"""
        response = self.app.post('/vastai/set-ui-home',
                                json={
                                    'ssh_connection': 'invalid connection string',
                                    'ui_home': '/workspace/ComfyUI/'
                                },
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('Invalid SSH connection string format', data['message'])
        
        # Verify subprocess was not called
        mock_subprocess.assert_not_called()

    @patch('app.sync.sync_api.subprocess.run')
    def test_vastai_get_ui_home_success(self, mock_subprocess):
        """Test successful VastAI UI_HOME retrieval"""
        # Mock successful subprocess execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = 'UI_HOME=/workspace/ComfyUI/'
        mock_result.stderr = ''
        mock_subprocess.return_value = mock_result

        response = self.app.post('/vastai/get-ui-home',
                                json={'ssh_connection': 'ssh -p 2838 root@104.189.178.116'},
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['ui_home'], 'UI_HOME=/workspace/ComfyUI/')
        self.assertIn('UI_HOME retrieved successfully', data['message'])

    @patch('app.sync.sync_api.subprocess.run')
    def test_vastai_get_ui_home_ssh_failure(self, mock_subprocess):
        """Test VastAI UI_HOME retrieval with SSH failure"""
        # Mock failed subprocess execution
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = 'Connection refused'
        mock_subprocess.return_value = mock_result

        response = self.app.post('/vastai/get-ui-home',
                                json={'ssh_connection': 'ssh -p 2838 root@104.189.178.116'},
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('Failed to read UI_HOME: Connection refused', data['message'])

    @patch('app.sync.sync_api.subprocess.run')
    def test_vastai_terminate_connection_success(self, mock_subprocess):
        """Test successful VastAI connection termination"""
        # Mock successful subprocess execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        response = self.app.post('/vastai/terminate-connection',
                                json={'ssh_connection': 'ssh -p 2838 root@104.189.178.116'},
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('SSH connections terminated successfully', data['message'])

    def test_vastai_endpoints_missing_data(self):
        """Test VastAI endpoints with missing request data"""
        # Test set-ui-home without data
        response = self.app.post('/vastai/set-ui-home',
                                json={},
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        # Test get-ui-home without data
        response = self.app.post('/vastai/get-ui-home',
                                json={},
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        # Test terminate-connection without data
        response = self.app.post('/vastai/terminate-connection',
                                json={},
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_parse_ssh_connection_function(self):
        """Test SSH connection string parsing function"""
        from app.sync.sync_api import parse_ssh_connection
        
        # Test valid connection string
        result = parse_ssh_connection('ssh -p 2838 root@104.189.178.116 -L 8080:localhost:8080')
        self.assertIsNotNone(result)
        self.assertEqual(result['user'], 'root')
        self.assertEqual(result['host'], '104.189.178.116')
        self.assertEqual(result['port'], 2838)
        
        # Test connection string without port (should default to 22)
        result = parse_ssh_connection('ssh user@example.com')
        self.assertIsNotNone(result)
        self.assertEqual(result['port'], 22)
        
        # Test invalid connection string
        result = parse_ssh_connection('invalid string')
        self.assertIsNone(result)

    def test_sync_vastai_connection_endpoint(self):
        """Test the new VastAI connection sync endpoint"""
        # Test with valid SSH connection string
        response = self.app.post('/sync/vastai-connection', 
                                json={'ssh_connection': 'ssh -p 2838 root@104.189.178.116 -L 8080:localhost:8080'})
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        # The sync will fail because we can't actually connect, but the endpoint should work
        self.assertFalse(data['success'])  # Expected to fail in test environment
        self.assertIn('message', data)
        
        # Test with invalid SSH connection string
        response = self.app.post('/sync/vastai-connection', 
                                json={'ssh_connection': 'invalid'})
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('Invalid SSH connection string format', data['message'])
        
        # Test with missing SSH connection string
        response = self.app.post('/sync/vastai-connection', json={})
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('SSH connection string is required', data['message'])


if __name__ == '__main__':
    unittest.main()