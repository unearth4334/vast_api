"""
Tests for SSH Host Key Manager
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import subprocess
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.sync.ssh_host_key_manager import SSHHostKeyManager, HostKeyError


class TestSSHHostKeyManager(unittest.TestCase):
    """Test SSH Host Key Manager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = SSHHostKeyManager(known_hosts_path="/tmp/test_known_hosts")
        
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
    
    def test_detect_host_key_error_success(self):
        """Test successful detection of host key error"""
        error = self.manager.detect_host_key_error(self.sample_error_output)
        
        self.assertIsNotNone(error)
        self.assertIsInstance(error, HostKeyError)
        self.assertEqual(error.host, "10.0.78.108")
        self.assertEqual(error.port, 2222)
        self.assertEqual(error.known_hosts_file, "/root/.ssh/known_hosts")
        self.assertEqual(error.line_number, 6)
        self.assertIn("SHA256:", error.new_fingerprint)
    
    def test_detect_host_key_error_no_error(self):
        """Test detection with normal SSH output (no error)"""
        normal_output = "Connection successful\nWelcome to the server"
        error = self.manager.detect_host_key_error(normal_output)
        
        self.assertIsNone(error)
    
    def test_detect_host_key_error_partial_match(self):
        """Test detection with partial error message"""
        partial_output = """
WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!
The fingerprint for the ED25519 key sent by the remote host is
SHA256:TestFingerprint123.
"""
        error = self.manager.detect_host_key_error(partial_output)
        
        self.assertIsNotNone(error)
        # The period is part of the sentence, so it's captured in the fingerprint
        self.assertEqual(error.new_fingerprint, "SHA256:TestFingerprint123.")
    
    @patch('subprocess.run')
    def test_remove_old_host_key_success(self, mock_run):
        """Test successful removal of old host key"""
        # Mock successful subprocess execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Host [10.0.78.108]:2222 found: line 6\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        success, message = self.manager.remove_old_host_key("10.0.78.108", 2222)
        
        self.assertTrue(success)
        self.assertIn("removed successfully", message)
        
        # Verify ssh-keygen was called with correct arguments
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], "ssh-keygen")
        self.assertIn("-f", call_args)
        self.assertIn("-R", call_args)
        self.assertIn("[10.0.78.108]:2222", call_args)
    
    @patch('subprocess.run')
    def test_remove_old_host_key_failure(self, mock_run):
        """Test failed removal of old host key"""
        # Mock failed subprocess execution
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Host not found"
        mock_run.return_value = mock_result
        
        success, message = self.manager.remove_old_host_key("10.0.78.108", 2222)
        
        self.assertFalse(success)
        self.assertIn("Failed to remove host key", message)
    
    @patch('subprocess.run')
    def test_remove_old_host_key_timeout(self, mock_run):
        """Test timeout during host key removal"""
        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired("ssh-keygen", 30)
        
        success, message = self.manager.remove_old_host_key("10.0.78.108", 2222)
        
        self.assertFalse(success)
        self.assertIn("timed out", message)
    
    @patch('subprocess.run')
    def test_accept_new_host_key_success(self, mock_run):
        """Test successful acceptance of new host key"""
        # Mock successful SSH connection
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Host key accepted\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        success, message = self.manager.accept_new_host_key("10.0.78.108", 2222)
        
        self.assertTrue(success)
        self.assertIn("accepted successfully", message)
        
        # Verify SSH was called with correct arguments
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], "ssh")
        self.assertIn("-p", call_args)
        self.assertIn("2222", call_args)
        self.assertIn("StrictHostKeyChecking=accept-new", " ".join(call_args))
    
    @patch('subprocess.run')
    def test_accept_new_host_key_connection_failed(self, mock_run):
        """Test acceptance of key when connection fails but key is accepted"""
        # Mock failed connection (but key was accepted)
        mock_result = MagicMock()
        mock_result.returncode = 255
        mock_result.stdout = ""
        mock_result.stderr = "Connection refused"
        mock_run.return_value = mock_result
        
        success, message = self.manager.accept_new_host_key("10.0.78.108", 2222)
        
        # Should still succeed since key was likely accepted
        self.assertTrue(success)
        self.assertIn("connection warning", message)
    
    @patch('subprocess.run')
    def test_accept_new_host_key_verification_failed(self, mock_run):
        """Test failed host key acceptance"""
        # Mock verification failure
        mock_result = MagicMock()
        mock_result.returncode = 255
        mock_result.stdout = ""
        mock_result.stderr = "Host key verification failed"
        mock_run.return_value = mock_result
        
        success, message = self.manager.accept_new_host_key("10.0.78.108", 2222)
        
        self.assertFalse(success)
        self.assertIn("Failed to accept host key", message)
    
    @patch.object(SSHHostKeyManager, 'remove_old_host_key')
    @patch.object(SSHHostKeyManager, 'accept_new_host_key')
    def test_resolve_host_key_error_success(self, mock_accept, mock_remove):
        """Test successful resolution of host key error"""
        # Mock successful removal and acceptance
        mock_remove.return_value = (True, "Key removed")
        mock_accept.return_value = (True, "Key accepted")
        
        # Create a test error
        from datetime import datetime
        error = HostKeyError(
            host="10.0.78.108",
            port=2222,
            known_hosts_file="/tmp/known_hosts",
            line_number=6,
            new_fingerprint="SHA256:test",
            error_message="Test error",
            detected_at=datetime.now().isoformat()
        )
        
        success, message = self.manager.resolve_host_key_error(error)
        
        self.assertTrue(success)
        self.assertIn("resolved successfully", message)
        
        # Verify both operations were called
        mock_remove.assert_called_once()
        mock_accept.assert_called_once()
    
    @patch.object(SSHHostKeyManager, 'remove_old_host_key')
    def test_resolve_host_key_error_remove_failed(self, mock_remove):
        """Test resolution when removal fails"""
        # Mock failed removal
        mock_remove.return_value = (False, "Removal failed")
        
        from datetime import datetime
        error = HostKeyError(
            host="10.0.78.108",
            port=2222,
            known_hosts_file="/tmp/known_hosts",
            line_number=6,
            new_fingerprint="SHA256:test",
            error_message="Test error",
            detected_at=datetime.now().isoformat()
        )
        
        success, message = self.manager.resolve_host_key_error(error)
        
        self.assertFalse(success)
        self.assertIn("Failed to remove old key", message)
    
    @patch.object(SSHHostKeyManager, 'remove_old_host_key')
    @patch.object(SSHHostKeyManager, 'accept_new_host_key')
    def test_resolve_host_key_error_accept_failed(self, mock_accept, mock_remove):
        """Test resolution when acceptance fails"""
        # Mock successful removal but failed acceptance
        mock_remove.return_value = (True, "Key removed")
        mock_accept.return_value = (False, "Acceptance failed")
        
        from datetime import datetime
        error = HostKeyError(
            host="10.0.78.108",
            port=2222,
            known_hosts_file="/tmp/known_hosts",
            line_number=6,
            new_fingerprint="SHA256:test",
            error_message="Test error",
            detected_at=datetime.now().isoformat()
        )
        
        success, message = self.manager.resolve_host_key_error(error)
        
        self.assertFalse(success)
        self.assertIn("failed to accept new key", message)
    
    def test_is_host_key_verified_no_file(self):
        """Test verification check when known_hosts doesn't exist"""
        # Manager points to a non-existent file
        manager = SSHHostKeyManager(known_hosts_path="/tmp/nonexistent_known_hosts_12345")
        
        result = manager.is_host_key_verified("10.0.78.108", 2222)
        
        self.assertFalse(result)
    
    def test_is_host_key_verified_found(self):
        """Test verification check when host key is in known_hosts"""
        import tempfile
        import os
        
        # Create a temporary known_hosts file with a test entry
        with tempfile.NamedTemporaryFile(mode='w', suffix='_known_hosts', delete=False) as f:
            f.write("[10.0.78.108]:2222 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI...\n")
            temp_path = f.name
        
        try:
            manager = SSHHostKeyManager(known_hosts_path=temp_path)
            result = manager.is_host_key_verified("10.0.78.108", 2222)
            
            self.assertTrue(result)
        finally:
            os.unlink(temp_path)
    
    def test_is_host_key_verified_not_found(self):
        """Test verification check when host key is NOT in known_hosts"""
        import tempfile
        import os
        
        # Create a temporary known_hosts file with a different host
        with tempfile.NamedTemporaryFile(mode='w', suffix='_known_hosts', delete=False) as f:
            f.write("[192.168.1.1]:22 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI...\n")
            temp_path = f.name
        
        try:
            manager = SSHHostKeyManager(known_hosts_path=temp_path)
            result = manager.is_host_key_verified("10.0.78.108", 2222)
            
            self.assertFalse(result)
        finally:
            os.unlink(temp_path)
    
    def test_is_host_key_verified_empty_file(self):
        """Test verification check with empty known_hosts file"""
        import tempfile
        import os
        
        # Create an empty temporary known_hosts file
        with tempfile.NamedTemporaryFile(mode='w', suffix='_known_hosts', delete=False) as f:
            temp_path = f.name
        
        try:
            manager = SSHHostKeyManager(known_hosts_path=temp_path)
            result = manager.is_host_key_verified("10.0.78.108", 2222)
            
            self.assertFalse(result)
        finally:
            os.unlink(temp_path)
    
    def test_is_host_key_verified_with_comments(self):
        """Test verification check skips comment lines"""
        import tempfile
        import os
        
        # Create a temporary known_hosts file with comments and a matching entry
        with tempfile.NamedTemporaryFile(mode='w', suffix='_known_hosts', delete=False) as f:
            f.write("# This is a comment\n")
            f.write("\n")  # Empty line
            f.write("[10.0.78.108]:2222 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI...\n")
            temp_path = f.name
        
        try:
            manager = SSHHostKeyManager(known_hosts_path=temp_path)
            result = manager.is_host_key_verified("10.0.78.108", 2222)
            
            self.assertTrue(result)
        finally:
            os.unlink(temp_path)
    
    def test_get_key_fingerprint_valid(self):
        """Test fingerprint calculation for a valid SSH key"""
        # This is a sample ED25519 public key (base64 encoded)
        # Using a known key to test the fingerprint calculation
        sample_key = "AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl"
        
        fingerprint = self.manager._get_key_fingerprint(sample_key)
        
        # Should start with SHA256:
        self.assertTrue(fingerprint.startswith("SHA256:"))
        # Should have content after SHA256:
        self.assertGreater(len(fingerprint), 7)
    
    def test_get_key_fingerprint_invalid(self):
        """Test fingerprint calculation for an invalid key"""
        invalid_key = "not_valid_base64!!!"
        
        fingerprint = self.manager._get_key_fingerprint(invalid_key)
        
        # Should return "Unknown" for invalid keys
        self.assertEqual(fingerprint, "Unknown")


if __name__ == '__main__':
    unittest.main()
