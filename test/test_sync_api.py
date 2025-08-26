#!/usr/bin/env python3
"""
Test the sync API endpoints
"""

import unittest
from unittest.mock import patch, MagicMock
import json
from sync_api import app


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

    @patch('sync_api.VastManager')
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

    @patch('sync_api.VastManager')
    def test_status_endpoint_vastai_error(self, mock_vast_manager):
        """Test status endpoint with VastAI connection error"""
        mock_vast_manager.side_effect = Exception("API error")

        response = self.app.get('/status')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertFalse(data['vastai']['available'])
        self.assertIn('error', data['vastai'])

    @patch('sync_api.run_sync')
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
        
        mock_run_sync.assert_called_once_with('10.0.78.108', '2222', 'Forge')

    @patch('sync_api.run_sync')
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
        
        mock_run_sync.assert_called_once_with('10.0.78.108', '2223', 'ComfyUI')

    @patch('sync_api.VastManager')
    @patch('sync_api.run_sync')
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
        
        mock_run_sync.assert_called_once_with('vast.example.com', '12345', 'VastAI')

    @patch('sync_api.VastManager')
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

    @patch('sync_api.VastManager')
    def test_sync_vastai_config_error(self, mock_vast_manager):
        """Test VastAI sync with configuration error"""
        mock_vast_manager.side_effect = FileNotFoundError("Config not found")

        response = self.app.post('/sync/vastai')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('configuration files not found', data['message'])


if __name__ == '__main__':
    unittest.main()