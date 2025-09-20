#!/usr/bin/env python3
"""
Test to reproduce and verify fix for SSH data mismatch issue.

The issue: API response contains correct SSH host/port, but UI displays different values.
The fix: Fetch detailed instance data for each instance in list_instances().
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
    """Test to reproduce and verify fix for SSH data mismatch issue"""

    def setUp(self):
        """Set up test fixtures"""
        self.app = app.test_client()
        self.app.testing = True

    @patch('app.sync.sync_api.VastManager')
    def test_ssh_data_missing_from_list_instances(self, mock_vast_manager_class):
        """Test reproducing the real issue: /instances/ API doesn't return SSH data"""
        # Mock VastManager instance
        mock_vm = MagicMock()
        mock_vast_manager_class.return_value = mock_vm
        
        # Mock instance data matching the ACTUAL problem:
        # /instances/ API returns limited data (no SSH info)
        mock_instances = [
            {
                'id': 26070143,
                'cur_state': 'running',
                # Note: NO ssh_host, ssh_port, gpu_name, etc. - this is the real issue!
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
        
        # This demonstrates the REAL issue - SSH data is missing!
        self.assertIsNone(instance['ssh_host'], 
                        "SSH host is None because /instances/ API doesn't return it")
        self.assertIsNone(instance['ssh_port'], 
                        "SSH port is None because /instances/ API doesn't return it")
        # Other fields are also missing
        self.assertIsNone(instance['gpu'])
        self.assertEqual(instance['gpu_count'], None)
        self.assertEqual(instance['gpu_ram_gb'], 0)

    @patch('app.vastai.vast_manager.requests.get')
    def test_list_instances_with_detailed_data(self, mock_get):
        """Test that the fixed list_instances method fetches detailed data"""
        # Mock responses for both /instances/ and /instances/{id}/ calls
        def side_effect(url, headers=None):
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            
            if url.endswith('/instances/'):
                # Basic list response - limited data
                mock_response.json.return_value = {
                    "instances": [
                        {
                            "id": 26070143,
                            "cur_state": "running"
                        }
                    ]
                }
            elif url.endswith('/instances/26070143/'):
                # Detailed instance response - complete data
                mock_response.json.return_value = {
                    "instances": {
                        "cur_state": "running",
                        "gpu_name": "RTX 4090",
                        "id": 26070143,
                        "ssh_host": "104.189.178.116",
                        "ssh_port": 2838,
                        "gpu_ram": 97996.8,
                        "num_gpus": 1,
                        "public_ipaddr": "104.189.178.116",
                        "geolocation": "Kansas, US",
                        "template_name": "pytorch/pytorch:latest",
                        "dph_total": 1.116999999999998
                    }
                }
            return mock_response
        
        mock_get.side_effect = side_effect
        
        # Test the fixed list_instances method
        with patch('app.vastai.vast_manager.VastManager._load_yaml'), \
             patch('app.vastai.vast_manager.VastManager._load_api_key'):
            vm = VastManager()
            instances = vm.list_instances()
            
            # Verify that we get detailed data including SSH info
            self.assertEqual(len(instances), 1)
            instance = instances[0]
            self.assertEqual(instance.get('id'), 26070143)
            self.assertEqual(instance.get('cur_state'), 'running')
            self.assertEqual(instance.get('ssh_host'), '104.189.178.116')
            self.assertEqual(instance.get('ssh_port'), 2838)
            self.assertEqual(instance.get('gpu_name'), 'RTX 4090')
            
            # Verify that both API calls were made
            self.assertEqual(mock_get.call_count, 2)

    @patch('app.sync.sync_api.VastManager')
    def test_fixed_ssh_data_in_api_response(self, mock_vast_manager_class):
        """Test that after the fix, SSH data is correctly returned to UI"""
        # Mock VastManager instance
        mock_vm = MagicMock()
        mock_vast_manager_class.return_value = mock_vm
        
        # Mock instance data with detailed data (after fix)
        mock_instances = [
            {
                'id': 26070143,
                'cur_state': 'running',
                'gpu_name': 'RTX 4090',
                'num_gpus': 1,
                'gpu_ram': 97996.8,
                'ssh_host': '104.189.178.116',  # Now available!
                'ssh_port': 2838,  # Now available!
                'public_ipaddr': '104.189.178.116',
                'geolocation': 'Kansas, US',
                'template_name': 'pytorch/pytorch:latest',
                'dph_total': 1.116999999999998
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
        
        # Check that the instance data now includes SSH data
        instance = data['instances'][0]
        self.assertEqual(instance['id'], 26070143)
        self.assertEqual(instance['status'], 'running')
        self.assertEqual(instance['gpu'], 'RTX 4090')
        self.assertEqual(instance['gpu_count'], 1)
        self.assertEqual(instance['gpu_ram_gb'], 95.7)
        
        # The fix: SSH data should now be available!
        self.assertEqual(instance['ssh_host'], '104.189.178.116')
        self.assertEqual(instance['ssh_port'], 2838)
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