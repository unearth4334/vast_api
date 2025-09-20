#!/usr/bin/env python3
"""
Test to reproduce the SSH data mismatch issue described in the problem statement.

The issue: API response contains correct SSH host/port, but UI displays different values.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.sync.sync_api import app
from app.vastai.vast_manager import VastManager


class TestSSHDataMismatch(unittest.TestCase):
    """Test to reproduce SSH data mismatch issue"""

    def setUp(self):
        """Set up test fixtures"""
        self.app = app.test_client()
        self.app.testing = True

    @patch('app.sync.sync_api.VastManager')
    def test_ssh_data_consistency(self, mock_vast_manager_class):
        """Test that SSH data from API is correctly passed to UI"""
        # Mock VastManager instance
        mock_vm = MagicMock()
        mock_vast_manager_class.return_value = mock_vm
        
        # Mock instance data matching the problem statement
        # API returns correct SSH data: ssh_host="104.189.178.116", ssh_port=2838
        mock_instances = [
            {
                'id': 26070143,
                'cur_state': 'running',
                'gpu_name': 'RTX PRO 6000 WS',  # Correct GPU name
                'num_gpus': 1,
                'gpu_ram': 97996.8,  # 95.6 GB in MB (95.6 * 1024 = 97996.8)
                'ssh_host': '104.189.178.116',  # Correct SSH host from API
                'ssh_port': 2838,  # Correct SSH port from API
                'public_ipaddr': '104.189.178.116',
                'geolocation': 'Kansas, US',
                'template_name': 'pytorch/pytorch:latest',
                'dph_total': 1.116999999999998  # Correct cost
            }
        ]
        
        mock_vm.list_instances.return_value = mock_instances
        
        # Make request to the API endpoint
        response = self.app.get('/vastai/instances')
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 1)
        self.assertEqual(len(data['instances']), 1)
        
        # Check that the instance data is correctly formatted
        instance = data['instances'][0]
        self.assertEqual(instance['id'], 26070143)
        self.assertEqual(instance['status'], 'running')
        self.assertEqual(instance['gpu'], 'RTX PRO 6000 WS')
        self.assertEqual(instance['gpu_count'], 1)
        self.assertEqual(instance['gpu_ram_gb'], 95.7)  # Should be correctly converted from MB to GB (95.6 * 1024 = 97996.8 MB -> 95.7 GB)
        
        # This is the critical test - SSH data should match API response
        self.assertEqual(instance['ssh_host'], '104.189.178.116', 
                        "SSH host should match API response, not display different value")
        self.assertEqual(instance['ssh_port'], 2838, 
                        "SSH port should match API response, not display different value")
        
        self.assertEqual(instance['geolocation'], 'Kansas, US')
        self.assertEqual(instance['cost_per_hour'], 1.116999999999998)

    @patch('app.vastai.vast_manager.requests.get')
    def test_show_instance_ssh_data(self, mock_get):
        """Test that show_instance returns correct SSH data from API"""
        # Mock the API response to match problem statement
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "instances": {
                "cur_state": "running",
                "gpu_name": "RTX 4090",  # Note: this is wrong in API response per problem statement
                "id": "26070143",
                "ssh_host": "104.189.178.116",  # This is correct
                "ssh_port": 2838,  # This is correct
                "gpu_ram": 97996.8,  # 95.6 GB in MB
                "num_gpus": 1,
                "geolocation": "Kansas, US",
                "dph_total": 1.116999999999998
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test the show_instance method directly
        with patch('app.vastai.vast_manager.VastManager._load_yaml'), \
             patch('app.vastai.vast_manager.VastManager._load_api_key'):
            vm = VastManager()
            result = vm.show_instance("26070143")
            
            # Verify that the raw API data contains correct SSH info
            self.assertEqual(result.get('ssh_host'), '104.189.178.116')
            self.assertEqual(result.get('ssh_port'), 2838)


if __name__ == '__main__':
    unittest.main()