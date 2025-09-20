#!/usr/bin/env python3
"""
Tests for CivitDL setup functionality
"""
import unittest
from unittest.mock import patch, mock_open
import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.sync.sync_api import app, read_api_key_from_file

class TestCivitDLSetup(unittest.TestCase):
    def setUp(self):
        """Set up test client"""
        self.app = app
        self.app.testing = True
        self.client = self.app.test_client()

    @patch('builtins.open', new_callable=mock_open, read_data="vastai: api_key_123456\ncivitdl: api_key_abcdef\n")
    @patch('os.path.exists')
    def test_read_api_key_from_file_success(self, mock_exists, mock_file):
        """Test reading CivitDL API key from file"""
        mock_exists.return_value = True
        
        result = read_api_key_from_file()
        
        self.assertEqual(result, "api_key_abcdef")
        mock_file.assert_called_once()

    @patch('os.path.exists')
    def test_read_api_key_from_file_not_found(self, mock_exists):
        """Test handling when api_key.txt file doesn't exist"""
        mock_exists.return_value = False
        
        result = read_api_key_from_file()
        
        self.assertIsNone(result)

    @patch('builtins.open', new_callable=mock_open, read_data="vastai: api_key_123456\n")
    @patch('os.path.exists')
    def test_read_api_key_from_file_civitdl_not_found(self, mock_exists, mock_file):
        """Test handling when CivitDL key is not in api_key.txt"""
        mock_exists.return_value = True
        
        result = read_api_key_from_file()
        
        self.assertIsNone(result)

    def test_setup_civitdl_endpoint_missing_ssh_connection(self):
        """Test CivitDL setup endpoint with missing SSH connection"""
        response = self.client.post('/vastai/setup-civitdl', 
                                   data=json.dumps({}),
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('SSH connection string is required', data['message'])

    @patch('app.sync.sync_api.read_api_key_from_file')
    def test_setup_civitdl_endpoint_missing_api_key(self, mock_read_key):
        """Test CivitDL setup endpoint with missing API key"""
        mock_read_key.return_value = None
        
        response = self.client.post('/vastai/setup-civitdl',
                                   data=json.dumps({'ssh_connection': 'ssh -p 2838 root@test.com'}),
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('CivitDL API key not found', data['message'])

    @patch('app.sync.sync_api.parse_ssh_connection')
    @patch('app.sync.sync_api.read_api_key_from_file')
    def test_setup_civitdl_endpoint_invalid_ssh_connection(self, mock_read_key, mock_parse_ssh):
        """Test CivitDL setup endpoint with invalid SSH connection string"""
        mock_read_key.return_value = "test_api_key"
        mock_parse_ssh.return_value = None
        
        response = self.client.post('/vastai/setup-civitdl',
                                   data=json.dumps({'ssh_connection': 'invalid_ssh_string'}),
                                   content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('Invalid SSH connection string format', data['message'])

    def test_civitdl_endpoint_options_request(self):
        """Test CivitDL setup endpoint handles OPTIONS request"""
        response = self.client.options('/vastai/setup-civitdl')
        
        self.assertEqual(response.status_code, 204)

if __name__ == '__main__':
    unittest.main()