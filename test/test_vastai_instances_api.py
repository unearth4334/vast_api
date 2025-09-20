#!/usr/bin/env python3
"""
Test the new VastAI instances API endpoint
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


class TestVastAIInstancesAPI(unittest.TestCase):
    """Test the new VastAI instances API endpoint"""

    def setUp(self):
        """Set up test fixtures"""
        self.app = app.test_client()
        self.app.testing = True

    @patch('app.sync.sync_api.VastManager')
    def test_get_instances_success(self, mock_vast_manager_class):
        """Test successful retrieval of VastAI instances"""
        # Mock VastManager instance
        mock_vm = MagicMock()
        mock_vast_manager_class.return_value = mock_vm
        
        # Mock instance data
        mock_instances = [
            {
                'id': 123456,
                'cur_state': 'running',
                'gpu_name': 'RTX A6000',
                'num_gpus': 1,
                'gpu_ram': 49152,  # 48GB in MB
                'ssh_host': 'ssh1.example.com',
                'ssh_port': 12345,
                'public_ipaddr': '192.168.1.100',
                'geolocation': 'US-CA-1',
                'template_name': 'pytorch/pytorch:latest',
                'dph_total': 0.75
            },
            {
                'id': 789012,
                'cur_state': 'stopped',
                'gpu_name': 'RTX 4090',
                'num_gpus': 2,
                'gpu_ram': 24576,  # 24GB in MB
                'ssh_host': None,
                'ssh_port': None,
                'public_ipaddr': None,
                'geolocation': 'US-TX-2',
                'template_name': 'tensorflow/tensorflow:latest',
                'dph_total': 1.25
            }
        ]
        
        mock_vm.list_instances.return_value = mock_instances
        
        # Make request
        response = self.app.get('/vastai/instances')
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 1)  # Only running instance should be returned by default
        self.assertEqual(len(data['instances']), 1)
        self.assertTrue(data['filtered'])  # Should indicate filtering was applied
        
        # Check that only the running instance is returned
        instance = data['instances'][0]
        self.assertEqual(instance['id'], 123456)
        self.assertEqual(instance['status'], 'running')
        self.assertEqual(instance['gpu'], 'RTX A6000')
        self.assertEqual(instance['gpu_count'], 1)
        self.assertEqual(instance['gpu_ram_gb'], 48.0)
        self.assertEqual(instance['ssh_host'], 'ssh1.example.com')
        self.assertEqual(instance['ssh_port'], 12345)

    @patch('app.sync.sync_api.VastManager')
    def test_get_instances_empty(self, mock_vast_manager_class):
        """Test when no instances are found"""
        # Mock VastManager instance
        mock_vm = MagicMock()
        mock_vast_manager_class.return_value = mock_vm
        mock_vm.list_instances.return_value = []
        
        # Make request
        response = self.app.get('/vastai/instances')
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 0)
        self.assertEqual(len(data['instances']), 0)

    @patch('app.sync.sync_api.VastManager')
    def test_get_instances_file_not_found(self, mock_vast_manager_class):
        """Test when api_key.txt file is not found"""
        mock_vast_manager_class.side_effect = FileNotFoundError("api_key.txt not found")
        
        # Make request
        response = self.app.get('/vastai/instances')
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertFalse(data['success'])
        self.assertIn('configuration files not found', data['message'])

    @patch('app.sync.sync_api.VastManager')
    def test_get_instances_api_error(self, mock_vast_manager_class):
        """Test when VastAI API returns an error"""
        # Mock VastManager instance
        mock_vm = MagicMock()
        mock_vast_manager_class.return_value = mock_vm
        mock_vm.list_instances.side_effect = Exception("API Error: Unauthorized")
        
        # Make request
        response = self.app.get('/vastai/instances')
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertFalse(data['success'])
        self.assertIn('Error getting VastAI instances', data['message'])
        self.assertIn('API Error: Unauthorized', data['message'])

    @patch('app.sync.sync_api.VastManager')
    def test_get_instances_active_only_filtering(self, mock_vast_manager_class):
        """Test filtering for active instances only (default behavior)"""
        # Mock VastManager instance
        mock_vm = MagicMock()
        mock_vast_manager_class.return_value = mock_vm
        
        # Mock mixed instance data (running and stopped)
        mock_instances = [
            {
                'id': 123456,
                'cur_state': 'running',
                'gpu_name': 'RTX A6000',
                'num_gpus': 1,
                'gpu_ram': 49152,
                'ssh_host': 'ssh1.example.com',
                'ssh_port': 12345,
                'public_ipaddr': '192.168.1.100',
                'geolocation': 'US-CA-1',
                'template_name': 'pytorch/pytorch:latest',
                'dph_total': 0.75
            },
            {
                'id': 789012,
                'cur_state': 'stopped',
                'gpu_name': 'RTX 3090',
                'num_gpus': 1,
                'gpu_ram': 24576,
                'ssh_host': None,
                'ssh_port': None,
                'public_ipaddr': None,
                'geolocation': 'US-TX-1',
                'template_name': 'pytorch/pytorch:latest',
                'dph_total': 0.50
            }
        ]
        mock_vm.list_instances.return_value = mock_instances
        
        # Make request (default should filter for active only)
        response = self.app.get('/vastai/instances')
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 1)  # Only 1 running instance
        self.assertEqual(len(data['instances']), 1)
        self.assertTrue(data['filtered'])  # Should indicate filtering was applied
        
        # Check that only the running instance is returned
        instance = data['instances'][0]
        self.assertEqual(instance['id'], 123456)
        self.assertEqual(instance['status'], 'running')

    @patch('app.sync.sync_api.VastManager')
    def test_get_instances_all_instances(self, mock_vast_manager_class):
        """Test getting all instances when all=true parameter is used"""
        # Mock VastManager instance
        mock_vm = MagicMock()
        mock_vast_manager_class.return_value = mock_vm
        
        # Mock mixed instance data (running and stopped)
        mock_instances = [
            {
                'id': 123456,
                'cur_state': 'running',
                'gpu_name': 'RTX A6000',
                'num_gpus': 1,
                'gpu_ram': 49152,
                'ssh_host': 'ssh1.example.com',
                'ssh_port': 12345,
                'public_ipaddr': '192.168.1.100',
                'geolocation': 'US-CA-1',
                'template_name': 'pytorch/pytorch:latest',
                'dph_total': 0.75
            },
            {
                'id': 789012,
                'cur_state': 'stopped',
                'gpu_name': 'RTX 3090',
                'num_gpus': 1,
                'gpu_ram': 24576,
                'ssh_host': None,
                'ssh_port': None,
                'public_ipaddr': None,
                'geolocation': 'US-TX-1',
                'template_name': 'pytorch/pytorch:latest',
                'dph_total': 0.50
            }
        ]
        mock_vm.list_instances.return_value = mock_instances
        
        # Make request with all=true parameter
        response = self.app.get('/vastai/instances?all=true')
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 2)  # Both instances should be returned
        self.assertEqual(len(data['instances']), 2)
        self.assertFalse(data['filtered'])  # Should indicate no filtering was applied
        
        # Check that both instances are returned
        instance_ids = [instance['id'] for instance in data['instances']]
        self.assertIn(123456, instance_ids)
        self.assertIn(789012, instance_ids)

    def test_get_instances_options_request(self):
        """Test CORS OPTIONS request"""
        response = self.app.options('/vastai/instances')
        self.assertEqual(response.status_code, 204)


class TestVastManagerAPIKeyParsing(unittest.TestCase):
    """Test the updated API key parsing functionality"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary API key file
        self.test_api_key_path = '/tmp/test_api_key.txt'

    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.test_api_key_path):
            os.remove(self.test_api_key_path)

    def test_load_api_key_multiline_format(self):
        """Test loading API key from multi-line format"""
        # Create test file with multi-line format
        with open(self.test_api_key_path, 'w') as f:
            f.write("vastai: d74eddba22a86903c0de9af2fb3e337ce715cc7e3d249352e9faa54e648531d4\n")
            f.write("civitdl: 905ad9c17ed7f6ba43fd10c211981d8c\n")
        
        # Test the parsing directly
        vm = VastManager.__new__(VastManager)  # Create instance without calling __init__
        result = vm._load_api_key(self.test_api_key_path)
        
        self.assertEqual(result, "d74eddba22a86903c0de9af2fb3e337ce715cc7e3d249352e9faa54e648531d4")

    def test_load_api_key_single_line_fallback(self):
        """Test fallback to single line format"""
        # Create test file with single line format
        with open(self.test_api_key_path, 'w') as f:
            f.write("d74eddba22a86903c0de9af2fb3e337ce715cc7e3d249352e9faa54e648531d4")
        
        # Test the parsing directly
        vm = VastManager.__new__(VastManager)  # Create instance without calling __init__
        result = vm._load_api_key(self.test_api_key_path)
        
        self.assertEqual(result, "d74eddba22a86903c0de9af2fb3e337ce715cc7e3d249352e9faa54e648531d4")

    def test_load_api_key_whitespace_handling(self):
        """Test that whitespace is properly handled"""
        # Create test file with extra whitespace
        with open(self.test_api_key_path, 'w') as f:
            f.write("  vastai:   d74eddba22a86903c0de9af2fb3e337ce715cc7e3d249352e9faa54e648531d4  \n")
            f.write("  civitdl: 905ad9c17ed7f6ba43fd10c211981d8c  \n")
        
        # Test the parsing directly
        vm = VastManager.__new__(VastManager)  # Create instance without calling __init__
        result = vm._load_api_key(self.test_api_key_path)
        
        self.assertEqual(result, "d74eddba22a86903c0de9af2fb3e337ce715cc7e3d249352e9faa54e648531d4")


if __name__ == '__main__':
    unittest.main()