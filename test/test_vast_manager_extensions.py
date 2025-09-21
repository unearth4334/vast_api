#!/usr/bin/env python3
"""
Test the new VastManager functionality
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.vastai.vast_manager import VastManager


class TestVastManagerExtensions(unittest.TestCase):
    """Test the new list_instances and get_running_instance methods"""

    def setUp(self):
        """Set up test fixtures"""
        with patch('app.vastai.vast_manager.VastManager._load_yaml'), \
             patch('app.vastai.vast_manager.VastManager._load_api_key'):
            self.manager = VastManager()
            self.manager.config = {'test': 'config'}
            self.manager.api_key = 'test_key'
            self.manager.headers = {'Authorization': 'Bearer test_key'}

    @patch('requests.get')
    def test_list_instances_success(self, mock_get):
        """Test successful instance listing"""
        # Mock responses for list call and detail calls
        list_response = MagicMock()
        list_response.json.return_value = {
            'instances': [
                {'id': 1, 'cur_state': 'running'},
                {'id': 2, 'cur_state': 'stopped'}
            ]
        }
        list_response.raise_for_status.return_value = None
        
        detail_response_1 = MagicMock()
        detail_response_1.json.return_value = {
            'instances': {'id': 1, 'cur_state': 'running', 'ssh_host': 'host1.example.com', 'ssh_port': 22001}
        }
        detail_response_1.raise_for_status.return_value = None
        
        detail_response_2 = MagicMock()
        detail_response_2.json.return_value = {
            'instances': {'id': 2, 'cur_state': 'stopped', 'ssh_host': 'host2.example.com', 'ssh_port': 22002}
        }
        detail_response_2.raise_for_status.return_value = None
        
        # Return list response first, then detail responses
        mock_get.side_effect = [list_response, detail_response_1, detail_response_2]

        instances = self.manager.list_instances()

        self.assertEqual(len(instances), 2)
        self.assertEqual(instances[0]['id'], 1)
        self.assertEqual(instances[0]['ssh_host'], 'host1.example.com')
        self.assertEqual(instances[0]['ssh_port'], 22001)
        self.assertEqual(instances[1]['id'], 2)
        self.assertEqual(instances[1]['ssh_host'], 'host2.example.com')
        self.assertEqual(instances[1]['ssh_port'], 22002)
        self.assertEqual(mock_get.call_count, 3)  # 1 list call + 2 detail calls

    @patch('requests.get')
    def test_list_instances_empty(self, mock_get):
        """Test empty instance list"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'instances': []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        instances = self.manager.list_instances()

        self.assertEqual(len(instances), 0)

    @patch('app.vastai.vast_manager.VastManager.list_instances')
    def test_get_running_instance_found(self, mock_list):
        """Test finding a running instance"""
        mock_list.return_value = [
            {'id': 1, 'cur_state': 'stopped'},
            {'id': 2, 'cur_state': 'running', 'ssh_host': 'test.host'},
            {'id': 3, 'cur_state': 'starting'}
        ]

        running = self.manager.get_running_instance()

        self.assertIsNotNone(running)
        self.assertEqual(running['id'], 2)
        self.assertEqual(running['cur_state'], 'running')

    @patch('app.vastai.vast_manager.VastManager.list_instances')
    def test_get_running_instance_not_found(self, mock_list):
        """Test when no running instance exists"""
        mock_list.return_value = [
            {'id': 1, 'cur_state': 'stopped'},
            {'id': 2, 'cur_state': 'starting'}
        ]

        running = self.manager.get_running_instance()

        self.assertIsNone(running)

    @patch('app.vastai.vast_manager.VastManager.list_instances')
    def test_get_running_instance_empty_list(self, mock_list):
        """Test when no instances exist"""
        mock_list.return_value = []

        running = self.manager.get_running_instance()

        self.assertIsNone(running)


if __name__ == '__main__':
    unittest.main()