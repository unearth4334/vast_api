#!/usr/bin/env python3
"""
Test script to validate SSH connection fix implementation
"""

import unittest
import os
import sys
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock

# Add the app directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from app.sync.ssh_manager import SSHManager, validate_ssh_prerequisites
    from app.sync.sync_utils import run_sync
except ImportError as e:
    print(f"Warning: Could not import modules: {e}")
    print("This test requires the SSH manager and sync utils to be available")
    sys.exit(1)


class TestSSHConnectionFix(unittest.TestCase):
    """Test the SSH connection fix implementation"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_host = "10.0.78.108"
        self.test_port = "2222"
        self.test_user = "root"
    
    def test_ssh_manager_initialization(self):
        """Test SSH manager can be initialized"""
        try:
            ssh_mgr = SSHManager()
            self.assertIsInstance(ssh_mgr, SSHManager)
            self.assertEqual(ssh_mgr.ssh_key_path, "/root/.ssh/id_ed25519")
        except Exception as e:
            self.fail(f"SSH manager initialization failed: {e}")
    
    @patch('os.path.exists')
    @patch('os.stat')
    def test_ssh_key_validation_missing_key(self, mock_stat, mock_exists):
        """Test SSH key validation when key is missing"""
        mock_exists.return_value = False
        
        ssh_mgr = SSHManager()
        result = ssh_mgr.validate_ssh_key()
        
        self.assertFalse(result['valid'])
        self.assertFalse(result['exists'])
        self.assertIn('not found', result['message'])
    
    @patch('os.path.exists')
    @patch('os.stat')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="test key")
    def test_ssh_key_validation_wrong_permissions(self, mock_open, mock_stat, mock_exists):
        """Test SSH key validation with wrong permissions"""
        mock_exists.return_value = True
        
        # Mock file stat to return wrong permissions (644 instead of 600)
        mock_stat_result = Mock()
        mock_stat_result.st_mode = 0o100644  # Regular file with 644 permissions
        mock_stat.return_value = mock_stat_result
        
        ssh_mgr = SSHManager()
        result = ssh_mgr.validate_ssh_key()
        
        self.assertFalse(result['valid'])
        self.assertTrue(result['exists'])
        self.assertTrue(result['readable'])
        self.assertEqual(result['permissions'], '644')
        self.assertIn('incorrect permissions', result['message'])
    
    @patch('os.path.exists')
    @patch('os.stat')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="test key")
    def test_ssh_key_validation_success(self, mock_open, mock_stat, mock_exists):
        """Test successful SSH key validation"""
        mock_exists.return_value = True
        
        # Mock file stat to return correct permissions (600)
        mock_stat_result = Mock()
        mock_stat_result.st_mode = 0o100600  # Regular file with 600 permissions
        mock_stat.return_value = mock_stat_result
        
        ssh_mgr = SSHManager()
        result = ssh_mgr.validate_ssh_key()
        
        self.assertTrue(result['valid'])
        self.assertTrue(result['exists'])
        self.assertTrue(result['readable'])
        self.assertEqual(result['permissions'], '600')
        self.assertEqual(result['message'], 'SSH key validation successful')
    
    @patch('subprocess.run')
    def test_ssh_agent_start_success(self, mock_run):
        """Test successful SSH agent startup"""
        # Mock ssh-agent output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "SSH_AUTH_SOCK=/tmp/ssh-agent.123; export SSH_AUTH_SOCK;\nSSH_AGENT_PID=12345; export SSH_AGENT_PID;\n"
        mock_run.return_value = mock_result
        
        ssh_mgr = SSHManager()
        result = ssh_mgr.start_ssh_agent()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['pid'], 12345)
        self.assertEqual(result['auth_sock'], '/tmp/ssh-agent.123')
        self.assertIn('started successfully', result['message'])
    
    @patch('subprocess.run')
    def test_ssh_agent_start_failure(self, mock_run):
        """Test SSH agent startup failure"""
        # Mock ssh-agent failure
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Failed to start ssh-agent"
        mock_run.return_value = mock_result
        
        ssh_mgr = SSHManager()
        result = ssh_mgr.start_ssh_agent()
        
        self.assertFalse(result['success'])
        self.assertIn('Failed to start ssh-agent', result['message'])
    
    def test_validate_ssh_prerequisites(self):
        """Test SSH prerequisites validation"""
        try:
            result = validate_ssh_prerequisites()
            self.assertIsInstance(result, dict)
            self.assertIn('valid', result)
            self.assertIn('issues', result)
            self.assertIn('ssh_key_path', result)
            self.assertIn('known_hosts_path', result)
        except Exception as e:
            self.fail(f"SSH prerequisites validation failed: {e}")
    
    @patch('app.sync.sync_utils.validate_ssh_prerequisites')
    @patch('app.sync.sync_utils.SSHManager')
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_run_sync_with_ssh_validation(self, mock_exists, mock_subprocess, mock_ssh_manager, mock_prereqs):
        """Test run_sync with SSH validation"""
        # Mock prerequisites validation
        mock_prereqs.return_value = {'valid': True, 'issues': []}
        
        # Mock SSH manager
        mock_ssh_instance = Mock()
        mock_ssh_instance.setup_ssh_for_sync.return_value = {'success': True, 'message': 'SSH setup successful'}
        mock_ssh_manager.return_value.__enter__.return_value = mock_ssh_instance
        
        # Mock sync script exists
        mock_exists.return_value = True
        
        # Mock successful sync execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Sync completed successfully"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        # Run sync
        result = run_sync(self.test_host, self.test_port, "Test")
        
        self.assertTrue(result['success'])
        self.assertIn('sync_id', result)
        mock_prereqs.assert_called_once()
    
    @patch('app.sync.sync_utils.validate_ssh_prerequisites')
    @patch('os.path.exists')
    def test_run_sync_ssh_prerequisites_fail(self, mock_exists, mock_prereqs):
        """Test run_sync when SSH prerequisites fail"""
        # Mock prerequisites validation failure
        mock_prereqs.return_value = {
            'valid': False, 
            'issues': ['SSH key not found', 'Wrong permissions']
        }
        
        # Mock sync script exists
        mock_exists.return_value = True
        
        # Run sync
        result = run_sync(self.test_host, self.test_port, "Test")
        
        self.assertFalse(result['success'])
        self.assertIn('SSH prerequisites not met', result['message'])
        self.assertIn('SSH key not found', result['message'])


def run_tests():
    """Run all tests"""
    print("Running SSH Connection Fix Tests...")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSSHConnectionFix)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ All tests passed!")
        print(f"Ran {result.testsRun} tests successfully")
    else:
        print("❌ Some tests failed!")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        
        for test, traceback in result.failures + result.errors:
            print(f"\nFailed: {test}")
            print(traceback)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)