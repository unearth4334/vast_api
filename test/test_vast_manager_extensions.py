#!/usr/bin/env python3
"""
Test the new VastManager functionality
"""

import unittest
from unittest.mock import patch, MagicMock
from vast_manager import VastManager


class TestVastManagerExtensions(unittest.TestCase):
    """Test the new list_instances and get_running_instance methods"""

    def setUp(self):
        """Set up test fixtures"""
        with patch('vast_manager.VastManager._load_yaml'), \
             patch('vast_manager.VastManager._load_api_key'):
            self.manager = VastManager()
            self.manager.config = {'test': 'config'}
            self.manager.api_key = 'test_key'
            self.manager.headers = {'Authorization': 'Bearer test_key'}

    @patch('requests.get')
    def test_list_instances_success(self, mock_get):
        """Test successful instance listing"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'instances': [
                {'id': 1, 'cur_state': 'running'},
                {'id': 2, 'cur_state': 'stopped'}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        instances = self.manager.list_instances()

        self.assertEqual(len(instances), 2)
        self.assertEqual(instances[0]['id'], 1)
        self.assertEqual(instances[1]['id'], 2)
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_list_instances_empty(self, mock_get):
        """Test empty instance list"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'instances': []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        instances = self.manager.list_instances()

        self.assertEqual(len(instances), 0)

    @patch('vast_manager.VastManager.list_instances')
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

    @patch('vast_manager.VastManager.list_instances')
    def test_get_running_instance_not_found(self, mock_list):
        """Test when no running instance exists"""
        mock_list.return_value = [
            {'id': 1, 'cur_state': 'stopped'},
            {'id': 2, 'cur_state': 'starting'}
        ]

        running = self.manager.get_running_instance()

        self.assertIsNone(running)

    @patch('vast_manager.VastManager.list_instances')
    def test_get_running_instance_empty_list(self, mock_list):
        """Test when no instances exist"""
        mock_list.return_value = []

        running = self.manager.get_running_instance()

        self.assertIsNone(running)


if __name__ == '__main__':
    unittest.main()