#!/usr/bin/env python3
"""
Comprehensive test for SSH data consistency across all VastAI instance retrieval methods.

This test ensures that SSH host and port information is correctly retrieved and displayed
consistently across different methods and interfaces.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
import logging

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.sync.sync_api import app
from app.vastai.vast_manager import VastManager
from app.vastai.vast_instance import VastInstance


class TestSSHDataConsistency(unittest.TestCase):
    """Comprehensive test for SSH data consistency"""

    def setUp(self):
        """Set up test fixtures"""
        self.app = app.test_client()
        self.app.testing = True
        
        # Set up logging to capture SSH validation messages
        self.log_handler = logging.StreamHandler()
        self.log_handler.setLevel(logging.WARNING)
        logging.getLogger('app.vastai.vast_manager').addHandler(self.log_handler)
        logging.getLogger('app.vastai.vast_instance').addHandler(self.log_handler)
        logging.getLogger('app.sync.sync_api').addHandler(self.log_handler)

    def tearDown(self):
        """Clean up after tests"""
        logging.getLogger('app.vastai.vast_manager').removeHandler(self.log_handler)
        logging.getLogger('app.vastai.vast_instance').removeHandler(self.log_handler)
        logging.getLogger('app.sync.sync_api').removeHandler(self.log_handler)

    def test_ssh_data_validation_detects_incorrect_format(self):
        """Test that SSH data validation detects suspicious host formats"""
        with patch('app.vastai.vast_manager.VastManager._load_yaml'), \
             patch('app.vastai.vast_manager.VastManager._load_api_key'):
            
            vm = VastManager()
            
            # Test with correct SSH data (should not trigger warnings)
            correct_data = {
                'ssh_host': '104.189.178.116',
                'ssh_port': 2838,
                'id': '26070143'
            }
            
            with self.assertLogs('app.vastai.vast_manager', level='INFO') as log:
                ssh_host, ssh_port = vm._validate_ssh_data(correct_data, '26070143')
                self.assertEqual(ssh_host, '104.189.178.116')
                self.assertEqual(ssh_port, 2838)
                # Should only have INFO log, no WARNING
                warning_logs = [record for record in log.records if record.levelno >= logging.WARNING]
                self.assertEqual(len(warning_logs), 0)
            
            # Test with suspicious SSH data (should trigger warnings)
            suspicious_data = {
                'ssh_host': 'ssh4.vast.ai',
                'ssh_port': 30142,
                'id': '26070143'
            }
            
            with self.assertLogs('app.vastai.vast_manager', level='INFO') as log:
                ssh_host, ssh_port = vm._validate_ssh_data(suspicious_data, '26070143')
                self.assertEqual(ssh_host, 'ssh4.vast.ai')
                self.assertEqual(ssh_port, 30142)
                # Should have WARNING logs about suspicious data
                warning_logs = [record for record in log.records if record.levelno >= logging.WARNING]
                self.assertGreater(len(warning_logs), 0)
                # Check that warning messages contain expected content
                warning_messages = [record.getMessage() for record in warning_logs]
                self.assertTrue(any('Suspicious SSH host detected' in msg for msg in warning_messages))

    @patch('app.sync.sync_api.VastManager')
    def test_web_interface_ssh_data_consistency(self, mock_vast_manager_class):
        """Test that web interface correctly formats and validates SSH data"""
        # Mock VastManager instance
        mock_vm = MagicMock()
        mock_vast_manager_class.return_value = mock_vm
        
        # Test with correct SSH data
        mock_instances = [
            {
                'id': 26070143,
                'cur_state': 'running',
                'gpu_name': 'RTX PRO 6000 WS',
                'num_gpus': 1,
                'gpu_ram': 97996.8,
                'ssh_host': '104.189.178.116',  # Correct format
                'ssh_port': 2838,  # Correct port
                'public_ipaddr': '104.189.178.116',
                'geolocation': 'Kansas, US',
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
        
        # Check that SSH data is correctly formatted and preserved
        instance = data['instances'][0]
        self.assertEqual(instance['ssh_host'], '104.189.178.116')
        self.assertEqual(instance['ssh_port'], 2838)

    @patch('app.vastai.vast_manager.requests.get')
    def test_show_instance_ssh_data_validation(self, mock_get):
        """Test that show_instance method validates SSH data correctly"""
        # Mock API response with correct SSH data
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "instances": {
                "id": "26070143",
                "cur_state": "running",
                "gpu_name": "RTX PRO 6000 WS",
                "ssh_host": "104.189.178.116",
                "ssh_port": 2838,
                "gpu_ram": 97996.8,
                "geolocation": "Kansas, US"
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test the show_instance method
        with patch('app.vastai.vast_manager.VastManager._load_yaml'), \
             patch('app.vastai.vast_manager.VastManager._load_api_key'):
            
            vm = VastManager()
            
            with self.assertLogs('app.vastai.vast_manager', level='INFO') as log:
                result = vm.show_instance("26070143")
                
                # Verify that the SSH data is correct in the returned result
                self.assertEqual(result.get('ssh_host'), '104.189.178.116')
                self.assertEqual(result.get('ssh_port'), 2838)
                
                # Check that INFO log was created but no WARNING (data is correct)
                warning_logs = [record for record in log.records if record.levelno >= logging.WARNING]
                self.assertEqual(len(warning_logs), 0)

    @patch('app.vastai.vast_manager.requests.get')
    def test_list_instances_ssh_data_validation(self, mock_get):
        """Test that list_instances method validates SSH data for all instances"""
        # Mock API response with mixed SSH data (some correct, some suspicious)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "instances": [
                {
                    "id": "26070143",
                    "cur_state": "running",
                    "ssh_host": "104.189.178.116",  # Correct
                    "ssh_port": 2838
                },
                {
                    "id": "26070144",
                    "cur_state": "running", 
                    "ssh_host": "ssh4.vast.ai",  # Suspicious
                    "ssh_port": 30142
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test the list_instances method
        with patch('app.vastai.vast_manager.VastManager._load_yaml'), \
             patch('app.vastai.vast_manager.VastManager._load_api_key'):
            
            vm = VastManager()
            
            with self.assertLogs('app.vastai.vast_manager', level='INFO') as log:
                instances = vm.list_instances()
                
                # Verify we got both instances
                self.assertEqual(len(instances), 2)
                
                # Check that WARNING was logged for suspicious SSH host
                warning_logs = [record for record in log.records if record.levelno >= logging.WARNING]
                self.assertGreater(len(warning_logs), 0)
                
                # Verify the suspicious host warning
                warning_messages = [record.getMessage() for record in warning_logs]
                self.assertTrue(any('ssh4.vast.ai' in msg for msg in warning_messages))

    def test_vast_instance_ssh_data_validation(self):
        """Test that VastInstance class validates SSH data correctly"""
        # Mock client
        mock_client = MagicMock()
        mock_client.show_instance.return_value = {
            "instances": {
                "id": "26070143",
                "cur_state": "running",
                "ssh_host": "104.189.178.116",
                "ssh_port": 2838,
                "gpu_name": "RTX PRO 6000 WS",
                "gpu_ram": 97996.8
            }
        }
        
        # Create VastInstance
        instance = VastInstance("26070143", "test_offer", mock_client)
        
        # Test SSH data validation
        test_data = {
            "ssh_host": "104.189.178.116",
            "ssh_port": 2838
        }
        
        with self.assertLogs('app.vastai.vast_instance', level='INFO') as log:
            ssh_host, ssh_port = instance._validate_ssh_data(test_data)
            
            self.assertEqual(ssh_host, "104.189.178.116")
            self.assertEqual(ssh_port, 2838)
            
            # Should only have INFO log, no WARNING for correct data
            warning_logs = [record for record in log.records if record.levelno >= logging.WARNING]
            self.assertEqual(len(warning_logs), 0)


if __name__ == '__main__':
    unittest.main()