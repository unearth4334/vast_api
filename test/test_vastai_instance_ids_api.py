import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.sync.sync_api import app

class TestVastAIInstanceIDsAPI(unittest.TestCase):
    def setUp(self):
        """Set up test client"""
        self.app = app.test_client()
        self.app.testing = True

    def test_get_instance_ids_options_request(self):
        """Test OPTIONS request to instance IDs endpoint"""
        response = self.app.options('/vastai/instance-ids')
        self.assertEqual(response.status_code, 204)

    @patch('app.sync.sync_api.VastManager')
    def test_get_instance_ids_success(self, mock_vast_manager):
        """Test successful retrieval of instance IDs"""
        # Mock VastManager
        mock_instance = MagicMock()
        mock_instance.list_instances.return_value = [
            {'id': 123, 'cur_state': 'running'},
            {'id': 456, 'cur_state': 'stopped'},
            {'id': 789, 'cur_state': 'running'}
        ]
        mock_vast_manager.return_value = mock_instance

        response = self.app.get('/vastai/instance-ids')
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['instance_ids'], [123, 456, 789])
        self.assertEqual(data['count'], 3)

    @patch('app.sync.sync_api.VastManager')
    def test_get_instance_ids_empty(self, mock_vast_manager):
        """Test when no instances are found"""
        # Mock VastManager
        mock_instance = MagicMock()
        mock_instance.list_instances.return_value = []
        mock_vast_manager.return_value = mock_instance

        response = self.app.get('/vastai/instance-ids')
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['instance_ids'], [])
        self.assertEqual(data['count'], 0)

    @patch('app.sync.sync_api.VastManager')
    def test_get_instance_ids_with_none_ids(self, mock_vast_manager):
        """Test when some instances have None IDs"""
        # Mock VastManager
        mock_instance = MagicMock()
        mock_instance.list_instances.return_value = [
            {'id': 123, 'cur_state': 'running'},
            {'id': None, 'cur_state': 'stopped'},  # Instance with None ID
            {'id': 789, 'cur_state': 'running'}
        ]
        mock_vast_manager.return_value = mock_instance

        response = self.app.get('/vastai/instance-ids')
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['instance_ids'], [123, 789])  # None ID should be filtered out
        self.assertEqual(data['count'], 2)

    @patch('app.sync.sync_api.VastManager')
    def test_get_instance_ids_file_not_found(self, mock_vast_manager):
        """Test when configuration files are not found"""
        mock_vast_manager.side_effect = FileNotFoundError("Config file not found")

        response = self.app.get('/vastai/instance-ids')
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'VastAI configuration files not found (config.yaml or api_key.txt)')

    @patch('app.sync.sync_api.VastManager')
    def test_get_instance_ids_api_error(self, mock_vast_manager):
        """Test when VastAI API returns an error"""
        mock_instance = MagicMock()
        mock_instance.list_instances.side_effect = Exception("API Error")
        mock_vast_manager.return_value = mock_instance

        response = self.app.get('/vastai/instance-ids')
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertFalse(data['success'])
        self.assertIn('Error getting VastAI instance IDs: API Error', data['message'])


if __name__ == '__main__':
    unittest.main()