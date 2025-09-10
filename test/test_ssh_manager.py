#!/usr/bin/env python3
"""
Tests for SSH Identity Manager functionality
"""

import unittest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock, mock_open
import sys

# Add the app directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

try:
    from sync.ssh_manager import SSHIdentityManager
except ImportError:
    # Fallback import
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from app.sync.ssh_manager import SSHIdentityManager


class TestSSHIdentityManager(unittest.TestCase):
    """Test SSH Identity Manager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary SSH key path for testing
        self.temp_dir = tempfile.mkdtemp()
        self.ssh_key_path = os.path.join(self.temp_dir, 'id_ed25519')
        self.ssh_manager = SSHIdentityManager(self.ssh_key_path)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_ssh_manager_initialization(self):
        """Test SSH manager initializes with correct paths"""
        self.assertEqual(self.ssh_manager.ssh_key_path, self.ssh_key_path)
        self.assertEqual(self.ssh_manager.ssh_pub_key_path, f"{self.ssh_key_path}.pub")
        self.assertEqual(self.ssh_manager.ssh_config_path, "/root/.ssh/config")
    
    @patch('os.path.exists')
    @patch('os.access')
    @patch('os.stat')
    def test_validate_ssh_setup_missing_key(self, mock_stat, mock_access, mock_exists):
        """Test validation when SSH key is missing"""
        mock_exists.return_value = False
        
        result = self.ssh_manager.validate_ssh_setup()
        
        self.assertFalse(result['valid'])
        self.assertFalse(result['ssh_key_exists'])
        self.assertIn('SSH key not found', str(result['issues']))
    
    @patch('os.path.exists')
    @patch('os.access')
    @patch('os.stat')
    @patch('os.environ.get')
    def test_validate_ssh_setup_success(self, mock_env_get, mock_stat, mock_access, mock_exists):
        """Test successful SSH validation"""
        # Mock file existence and permissions
        mock_exists.side_effect = lambda path: True
        mock_access.return_value = True
        
        # Mock proper permissions (600 for key)
        mock_stat_result = MagicMock()
        mock_stat_result.st_mode = 0o100600  # Regular file with 600 permissions
        mock_stat.return_value = mock_stat_result
        
        # Mock SSH agent running
        mock_env_get.side_effect = lambda key, default=None: '/tmp/ssh-agent-socket' if key == 'SSH_AUTH_SOCK' else default
        
        with patch.object(self.ssh_manager, '_is_identity_loaded', return_value=True):
            result = self.ssh_manager.validate_ssh_setup()
        
        self.assertTrue(result['valid'])
        self.assertTrue(result['ssh_key_exists'])
        self.assertTrue(result['ssh_key_readable'])
        self.assertTrue(result['ssh_agent_running'])
        self.assertTrue(result['identity_loaded'])
        self.assertTrue(result['permissions_ok'])
    
    @patch('subprocess.run')
    def test_is_identity_loaded_success(self, mock_subprocess):
        """Test checking if SSH identity is loaded"""
        # Mock ssh-add -l success with our key
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = f"2048 SHA256:abc123 {self.ssh_key_path} (ED25519)\n2048 SHA256:def456 media-sync@qnap (ED25519)"
        mock_subprocess.return_value = mock_result
        
        result = self.ssh_manager._is_identity_loaded()
        self.assertTrue(result)
    
    @patch('subprocess.run')
    def test_is_identity_loaded_not_found(self, mock_subprocess):
        """Test when SSH identity is not loaded"""
        # Mock ssh-add -l success but our key not in list
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "2048 SHA256:xyz789 /other/key (RSA)"
        mock_subprocess.return_value = mock_result
        
        result = self.ssh_manager._is_identity_loaded()
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_is_identity_loaded_agent_error(self, mock_subprocess):
        """Test when ssh-add fails"""
        # Mock ssh-add -l failure
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_subprocess.return_value = mock_result
        
        result = self.ssh_manager._is_identity_loaded()
        self.assertFalse(result)
    
    @patch('subprocess.run')
    @patch.object(SSHIdentityManager, 'validate_ssh_setup')
    def test_setup_ssh_agent_success(self, mock_validate, mock_subprocess):
        """Test successful SSH agent setup"""
        # Mock validation success
        mock_validate.return_value = {
            'valid': True,
            'ssh_agent_running': False,
            'identity_loaded': False
        }
        
        # Mock ssh-agent and ssh-add success
        agent_result = MagicMock()
        agent_result.returncode = 0
        agent_result.stdout = "SSH_AUTH_SOCK=/tmp/ssh-agent-123; export SSH_AUTH_SOCK;\nSSH_AGENT_PID=12345; export SSH_AGENT_PID;"
        
        add_result = MagicMock()
        add_result.returncode = 0
        add_result.stdout = f"Identity added: {self.ssh_key_path} (media-sync@qnap)"
        
        mock_subprocess.side_effect = [agent_result, add_result]
        
        result = self.ssh_manager.setup_ssh_agent()
        
        self.assertTrue(result['success'])
        self.assertTrue(result['identity_added'])
        self.assertIn('SSH identity added successfully', result['message'])
    
    @patch('subprocess.run')
    @patch.object(SSHIdentityManager, 'validate_ssh_setup')
    def test_setup_ssh_agent_validation_failed(self, mock_validate, mock_subprocess):
        """Test SSH agent setup when validation fails"""
        # Mock validation failure
        mock_validate.return_value = {
            'valid': False,
            'issues': ['SSH key not found']
        }
        
        result = self.ssh_manager.setup_ssh_agent()
        
        self.assertFalse(result['success'])
        self.assertIn('SSH validation failed', result['message'])
    
    @patch('subprocess.run')
    @patch.object(SSHIdentityManager, 'validate_ssh_setup')
    def test_setup_ssh_agent_requires_confirmation(self, mock_validate, mock_subprocess):
        """Test SSH agent setup when passphrase is required"""
        # Mock validation success
        mock_validate.return_value = {
            'valid': True,
            'ssh_agent_running': True,
            'identity_loaded': False
        }
        
        # Mock ssh-add failure due to passphrase
        add_result = MagicMock()
        add_result.returncode = 1
        add_result.stderr = "Enter passphrase for /root/.ssh/id_ed25519:"
        
        mock_subprocess.return_value = add_result
        
        result = self.ssh_manager.setup_ssh_agent()
        
        self.assertFalse(result['success'])
        self.assertTrue(result['requires_user_confirmation'])
        self.assertIn('user confirmation needed', result['message'])
    
    @patch('subprocess.run')
    def test_test_ssh_connection_success(self, mock_subprocess):
        """Test successful SSH connection test"""
        # Mock successful SSH connection
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ssh-test-success"
        mock_subprocess.return_value = mock_result
        
        result = self.ssh_manager.test_ssh_connection('localhost', 22, 'root', 10)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['host'], 'localhost')
        self.assertEqual(result['port'], 22)
        self.assertEqual(result['user'], 'root')
        self.assertIn('Connection successful', result['message'])
        self.assertIsNotNone(result['response_time'])
    
    @patch('subprocess.run')
    def test_test_ssh_connection_failure(self, mock_subprocess):
        """Test failed SSH connection test"""
        # Mock failed SSH connection
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Connection refused"
        mock_subprocess.return_value = mock_result
        
        result = self.ssh_manager.test_ssh_connection('localhost', 22, 'root', 10)
        
        self.assertFalse(result['success'])
        self.assertIn('Connection failed', result['message'])
    
    @patch('subprocess.run')
    def test_test_ssh_connection_timeout(self, mock_subprocess):
        """Test SSH connection timeout"""
        import subprocess
        # Mock timeout
        mock_subprocess.side_effect = subprocess.TimeoutExpired('ssh', 15)
        
        result = self.ssh_manager.test_ssh_connection('localhost', 22, 'root', 10)
        
        self.assertFalse(result['success'])
        self.assertIn('timed out', result['message'])
    
    @patch('subprocess.run')
    @patch('os.environ')
    def test_cleanup_ssh_agent_success(self, mock_environ, mock_subprocess):
        """Test successful SSH agent cleanup"""
        # Mock environment with SSH_AGENT_PID
        mock_environ.get.return_value = '12345'
        mock_environ.__contains__ = lambda self, key: key in ['SSH_AUTH_SOCK', 'SSH_AGENT_PID']
        mock_environ.__delitem__ = MagicMock()
        
        # Mock successful ssh-agent -k
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        result = self.ssh_manager.cleanup_ssh_agent()
        self.assertTrue(result)
    
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('os.chmod')
    @patch('os.stat')
    def test_ensure_ssh_permissions_creates_directory(self, mock_stat, mock_chmod, mock_makedirs, mock_exists):
        """Test creating SSH directory with correct permissions"""
        # Mock directory doesn't exist initially
        mock_exists.return_value = False
        
        result = self.ssh_manager.ensure_ssh_permissions()
        
        self.assertTrue(result['success'])
        mock_makedirs.assert_called_with(self.ssh_manager.ssh_dir, mode=0o700)
        self.assertIn('Created SSH directory', str(result['changes_made']))
    
    @patch('os.path.exists')
    @patch('os.chmod')
    @patch('os.stat')
    def test_ensure_ssh_permissions_fixes_permissions(self, mock_stat, mock_chmod, mock_exists):
        """Test fixing SSH file permissions"""
        # Mock files exist with wrong permissions
        mock_exists.return_value = True
        
        # Mock wrong permissions
        mock_stat_result = MagicMock()
        mock_stat_result.st_mode = 0o100644  # Wrong permissions (644 instead of 600 for key)
        mock_stat.return_value = mock_stat_result
        
        result = self.ssh_manager.ensure_ssh_permissions()
        
        self.assertTrue(result['success'])
        # Should fix permissions for SSH directory and key
        self.assertTrue(any('Fixed SSH' in change for change in result['changes_made']))
    
    def test_get_ssh_status(self):
        """Test getting comprehensive SSH status"""
        with patch.object(self.ssh_manager, 'validate_ssh_setup') as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'ssh_agent_running': True,
                'identity_loaded': True
            }
            
            status = self.ssh_manager.get_ssh_status()
            
            self.assertIn('timestamp', status)
            self.assertIn('validation', status)
            self.assertTrue(status['ready_for_sync'])
            self.assertEqual(status['ssh_key_path'], self.ssh_key_path)


if __name__ == '__main__':
    unittest.main()