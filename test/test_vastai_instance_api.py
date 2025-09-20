#!/usr/bin/env python3
"""
Tests for VastAI individual instance API endpoint
"""

import unittest
import json
import sys
import os
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from app.sync.sync_api import app
    from app.vastai.vast_manager import VastManager
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

class TestVastAIInstanceAPI(unittest.TestCase):
    """Test the VastAI individual instance API endpoints"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = app.test_client()
        self.app.testing = True
        
        # Mock instance data matching the problem statement example
        self.mock_instance_data = {
            "id": "26070143",
            "cur_state": "running",
            "gpu_name": "RTX 4090",
            "ssh_host": "104.189.178.116",
            "ssh_port": 2838,
            "public_ipaddr": "104.189.178.116",
            "geolocation": "US-West",
            "template_name": "pytorch",
            "num_gpus": 1,
            "gpu_ram": 24576
        }
    
    @patch('app.sync.sync_api.VastManager')
    def test_get_vastai_instance_success(self, mock_vast_manager_class):
        """Test successful retrieval of VastAI instance"""
        # Set up the mock
        mock_vast_manager = MagicMock()
        mock_vast_manager_class.return_value = mock_vast_manager
        mock_vast_manager.show_instance.return_value = self.mock_instance_data
        
        # Make the API call
        response = self.app.get('/vastai/instances/26070143')
        
        # Verify the response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Check the response structure matches the problem statement
        self.assertIn('instances', data)
        instances = data['instances']
        
        self.assertEqual(instances['cur_state'], 'running')
        self.assertEqual(instances['gpu_name'], 'RTX 4090')
        self.assertEqual(instances['id'], '26070143')
        self.assertEqual(instances['ssh_host'], '104.189.178.116')
        self.assertEqual(instances['ssh_port'], 2838)
        
        # Verify VastManager was called correctly
        mock_vast_manager.show_instance.assert_called_once_with('26070143')
    
    @patch('app.sync.sync_api.VastManager')
    def test_get_vastai_instance_not_found(self, mock_vast_manager_class):
        """Test handling of non-existent instance"""
        # Set up the mock to raise an exception
        mock_vast_manager = MagicMock()
        mock_vast_manager_class.return_value = mock_vast_manager
        mock_vast_manager.show_instance.side_effect = Exception("404: Instance not found")
        
        # Make the API call
        response = self.app.get('/vastai/instances/999999')
        
        # Verify the response
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        
        self.assertFalse(data['success'])
        self.assertIn('not found', data['message'])
    
    @patch('app.sync.sync_api.VastManager')
    def test_get_vastai_instance_config_missing(self, mock_vast_manager_class):
        """Test handling of missing configuration files"""
        # Set up the mock to raise FileNotFoundError
        mock_vast_manager_class.side_effect = FileNotFoundError("config.yaml not found")
        
        # Make the API call
        response = self.app.get('/vastai/instances/26070143')
        
        # Verify the response
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        
        self.assertFalse(data['success'])
        self.assertIn('configuration files not found', data['message'])
    
    def test_update_vastai_instance_success(self):
        """Test successful update of VastAI instance SSH details"""
        update_data = {
            'ssh_host': '192.168.1.100',
            'ssh_port': 3333
        }
        
        # Make the API call
        response = self.app.put('/vastai/instances/26070143',
                              data=json.dumps(update_data),
                              content_type='application/json')
        
        # Verify the response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('instances', data)
        instances = data['instances']
        
        self.assertEqual(instances['id'], '26070143')
        self.assertEqual(instances['ssh_host'], '192.168.1.100')
        self.assertEqual(instances['ssh_port'], 3333)
    
    def test_update_vastai_instance_missing_data(self):
        """Test update with missing data"""
        update_data = {
            'ssh_host': '192.168.1.100'
            # missing ssh_port
        }
        
        # Make the API call
        response = self.app.put('/vastai/instances/26070143',
                              data=json.dumps(update_data),
                              content_type='application/json')
        
        # Verify the response
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        
        self.assertFalse(data['success'])
        self.assertIn('Both ssh_host and ssh_port are required', data['message'])
    
    def test_update_vastai_instance_no_data(self):
        """Test update with no data"""
        # Make the API call with no data
        response = self.app.put('/vastai/instances/26070143',
                              content_type='application/json')
        
        # Verify the response
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        
        self.assertFalse(data['success'])
        self.assertIn('Request data is required', data['message'])
    
    def test_options_request(self):
        """Test OPTIONS request for CORS"""
        response = self.app.options('/vastai/instances/26070143')
        self.assertEqual(response.status_code, 204)


if __name__ == '__main__':
    unittest.main()