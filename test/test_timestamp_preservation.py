"""
Tests to verify that sync workflows preserve file timestamps from remote sources.
"""

import asyncio
import os
import tempfile
import time
import unittest
from unittest.mock import Mock, patch, AsyncMock
import sys

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.sync.transport.ssh_rsync import SSHRsyncAdapter


class TestTimestampPreservation(unittest.TestCase):
    """Test that file timestamps are preserved during sync."""

    def test_transfer_folder_includes_times_flag(self):
        """Test that transfer_folder command includes --times flag to preserve timestamps."""
        adapter = SSHRsyncAdapter(host="test.host", port=2222, user="testuser")
        
        # Mock the subprocess execution to capture the command
        captured_cmd = []
        
        async def mock_exec(*args, **kwargs):
            captured_cmd.extend(args)
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"total size is 1000\n", b""))
            mock_proc.returncode = 0
            return mock_proc
        
        with patch('asyncio.create_subprocess_exec', side_effect=mock_exec):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                adapter.transfer_folder("/remote/path", "/local/path")
            )
            
            loop.close()
        
        # Verify that --times is in the command and --no-times is not
        self.assertIn("--times", captured_cmd, 
                     "rsync command should include --times flag to preserve modification times")
        self.assertNotIn("--no-times", captured_cmd,
                        "rsync command should not include --no-times flag")
        self.assertNotIn("--omit-dir-times", captured_cmd,
                        "rsync command should not include --omit-dir-times flag")
    
    def test_transfer_file_preserves_times(self):
        """Test that transfer_file preserves timestamps (uses -avz which includes -t)."""
        adapter = SSHRsyncAdapter(host="test.host", port=2222, user="testuser")
        
        # Mock the subprocess execution to capture the command
        captured_cmd = []
        
        async def mock_exec(*args, **kwargs):
            captured_cmd.extend(args)
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0
            return mock_proc
        
        with patch('asyncio.create_subprocess_exec', side_effect=mock_exec):
            with patch('os.path.exists', return_value=True):
                with patch('os.path.getsize', return_value=1000):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    result = loop.run_until_complete(
                        adapter.transfer_file("/remote/file.txt", "/local/file.txt")
                    )
                    
                    loop.close()
        
        # Verify that -avz is in the command (which includes -t for time preservation)
        self.assertIn("-avz", captured_cmd,
                     "rsync command should include -avz flags which preserve timestamps")
    
    def test_timestamp_preservation_integration(self):
        """Integration test: verify timestamps would be preserved in actual rsync command."""
        adapter = SSHRsyncAdapter(host="example.com", port=22, user="root")
        
        # Create a mock to capture the actual rsync command that would be executed
        captured_commands = []
        
        async def capture_command(*cmd_args, **kwargs):
            # Store the command
            captured_commands.append(cmd_args)
            
            # Return a mock process
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"total size is 5000\n", b""))
            mock_proc.returncode = 0
            return mock_proc
        
        with patch('asyncio.create_subprocess_exec', side_effect=capture_command):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Test transfer_folder
            result = loop.run_until_complete(
                adapter.transfer_folder("/remote/images", "/local/images")
            )
            
            loop.close()
        
        # Analyze the captured command
        self.assertEqual(len(captured_commands), 1, "Should have captured one command")
        cmd = captured_commands[0]
        
        # Convert to string for easier analysis
        cmd_str = " ".join(cmd)
        
        # Verify the command structure
        self.assertIn("rsync", cmd_str)
        self.assertIn("--times", cmd_str, 
                     "Command must include --times to preserve file modification times")
        self.assertNotIn("--no-times", cmd_str,
                        "Command must NOT include --no-times which would prevent time preservation")
        
        # Verify success
        self.assertTrue(result.success, "Transfer should succeed")


class TestRsyncFlagConsistency(unittest.TestCase):
    """Test that rsync flags are correctly configured across different transfer methods."""
    
    def test_folder_transfer_rsync_flags(self):
        """Verify that transfer_folder uses the correct rsync flags."""
        adapter = SSHRsyncAdapter(host="test.host", port=2222, user="root")
        
        # Expected flags for folder transfer
        expected_flags = [
            "-rlD",  # recursive, links, devices
            "--compress",
            "--times",  # preserve modification times
            "--no-perms",
            "--no-owner", 
            "--no-group",
            "--partial",
        ]
        
        captured_cmd = []
        
        async def mock_exec(*args, **kwargs):
            captured_cmd.extend(args)
            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"total size is 1000\n", b""))
            mock_proc.returncode = 0
            return mock_proc
        
        with patch('asyncio.create_subprocess_exec', side_effect=mock_exec):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                adapter.transfer_folder("/remote/path", "/local/path")
            )
            
            loop.close()
        
        # Verify all expected flags are present
        for flag in expected_flags:
            self.assertIn(flag, captured_cmd, 
                         f"Expected flag {flag} should be in rsync command")
        
        # Verify flags that should NOT be present
        forbidden_flags = ["--no-times", "--omit-dir-times"]
        for flag in forbidden_flags:
            self.assertNotIn(flag, captured_cmd,
                           f"Flag {flag} should NOT be in rsync command")


if __name__ == '__main__':
    unittest.main()
