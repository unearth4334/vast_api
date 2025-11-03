"""
Integration tests for SSH Host Key API endpoints
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.sync.sync_api import app
from app.sync.ssh_host_key_manager import HostKeyError


class TestSSHHostKeyAPIEndpoints(unittest.TestCase):
    """Test SSH Host Key API endpoints"""
    
    def setUp(self):
        """Set up test client"""
        self.app = app.test_client()
        self.app.testing = True
        
        # Sample SSH error output
        self.sample_error_output = """
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
IT IS POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!
Someone could be eavesdropping on you right now (man-in-the-middle attack)!
It is also possible that a host key has just been changed.
The fingerprint for the ED25519 key sent by the remote host is
SHA256:6Dhif6lu1QviP6aTLpbkbv/U3CBxf89FsGSLTm1GhJw.
Please contact your system administrator.
Add correct host key in /root/.ssh/known_hosts to get rid of this message.
Offending ED25519 key in /root/.ssh/known_hosts:6
  remove with:
  ssh-keygen -f '/root/.ssh/known_hosts' -R '[10.0.78.108]:2222'
Host key for [10.0.78.108]:2222 has changed and you have requested strict checking.
Host key verification failed.
"""
    
    def test_check_host_key_error_with_error(self):
        """Test check endpoint with SSH host key error"""
        response = self.app.post('/ssh/host-keys/check',
                                data=json.dumps({'ssh_output': self.sample_error_output}),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertTrue(data['has_error'])
        self.assertIn('error', data)
        self.assertEqual(data['error']['host'], '10.0.78.108')
        self.assertEqual(data['error']['port'], 2222)
    
    def test_check_host_key_error_without_error(self):
        """Test check endpoint with normal SSH output"""
        normal_output = "Connection successful\nWelcome to the server"
        
        response = self.app.post('/ssh/host-keys/check',
                                data=json.dumps({'ssh_output': normal_output}),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertFalse(data['has_error'])
    
    def test_check_host_key_error_missing_output(self):
        """Test check endpoint with missing ssh_output"""
        response = self.app.post('/ssh/host-keys/check',
                                data=json.dumps({}),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('SSH output is required', data['message'])
    
    @patch('app.sync.ssh_host_key_manager.SSHHostKeyManager.resolve_host_key_error')
    def test_resolve_host_key_error_success(self, mock_resolve):
        """Test resolve endpoint with successful resolution"""
        mock_resolve.return_value = (True, "Host key resolved successfully")
        
        response = self.app.post('/ssh/host-keys/resolve',
                                data=json.dumps({
                                    'host': '10.0.78.108',
                                    'port': 2222,
                                    'known_hosts_file': '/root/.ssh/known_hosts'
                                }),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('resolved successfully', data['message'])
    
    @patch('app.sync.ssh_host_key_manager.SSHHostKeyManager.resolve_host_key_error')
    def test_resolve_host_key_error_failure(self, mock_resolve):
        """Test resolve endpoint with failed resolution"""
        mock_resolve.return_value = (False, "Failed to remove old key")
        
        response = self.app.post('/ssh/host-keys/resolve',
                                data=json.dumps({
                                    'host': '10.0.78.108',
                                    'port': 2222
                                }),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 500)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
    
    def test_resolve_host_key_error_missing_params(self):
        """Test resolve endpoint with missing parameters"""
        response = self.app.post('/ssh/host-keys/resolve',
                                data=json.dumps({'host': '10.0.78.108'}),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('Host and port are required', data['message'])
    
    @patch('app.sync.ssh_host_key_manager.SSHHostKeyManager.remove_old_host_key')
    def test_remove_host_key_success(self, mock_remove):
        """Test remove endpoint with successful removal"""
        mock_remove.return_value = (True, "Old host key removed successfully")
        
        response = self.app.post('/ssh/host-keys/remove',
                                data=json.dumps({
                                    'host': '10.0.78.108',
                                    'port': 2222
                                }),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
    
    @patch('app.sync.ssh_host_key_manager.SSHHostKeyManager.remove_old_host_key')
    def test_remove_host_key_failure(self, mock_remove):
        """Test remove endpoint with failed removal"""
        mock_remove.return_value = (False, "Host not found")
        
        response = self.app.post('/ssh/host-keys/remove',
                                data=json.dumps({
                                    'host': '10.0.78.108',
                                    'port': 2222
                                }),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 500)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
    
    def test_remove_host_key_missing_params(self):
        """Test remove endpoint with missing parameters"""
        response = self.app.post('/ssh/host-keys/remove',
                                data=json.dumps({'host': '10.0.78.108'}),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])


if __name__ == '__main__':
    unittest.main()
