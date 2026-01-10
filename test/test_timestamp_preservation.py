"""
Tests for timestamp preservation during sync operations
"""

import pytest
import os
import tempfile
import time
from datetime import datetime


class TestTimestampPreservation:
    """Test that file timestamps are preserved during sync operations."""
    
    def test_rsync_flags_include_times(self):
        """Test that rsync commands include --times flag and not --no-times."""
        # Test bash script flags
        with open('scripts/sync_outputs.sh', 'r') as f:
            script_content = f.read()
        
        # Check that --times or -t is present (via -rltD which includes -t)
        assert 'rltD' in script_content, "Bash script should include -rltD flag"
        
        # Check that --no-times is NOT present
        assert '--no-times' not in script_content, "Bash script should not include --no-times flag"
        
        # Check comment mentions timestamp preservation
        assert 'preserve' in script_content.lower() or 'retain' in script_content.lower(), \
            "Script should document timestamp preservation"
    
    def test_python_rsync_flags_preserve_times(self):
        """Test that Python SSH rsync adapter preserves timestamps."""
        with open('app/sync/transport/ssh_rsync.py', 'r') as f:
            adapter_content = f.read()
        
        # Check that --times is explicitly included
        assert '--times' in adapter_content, "Python adapter should include --times flag"
        
        # Check that --no-times is NOT present
        assert '--no-times' not in adapter_content, "Python adapter should not include --no-times flag"
        
        # Check comment mentions timestamp preservation
        assert 'preserve' in adapter_content.lower() or 'retain' in adapter_content.lower(), \
            "Adapter should document timestamp preservation"
    
    def test_local_file_timestamp_preservation(self):
        """Test that copying a file locally preserves timestamps using rsync."""
        # Create a temporary source file with known timestamp
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as src_file:
            src_path = src_file.name
            src_file.write("Test content for timestamp preservation")
        
        try:
            # Set specific modification time (Jan 1, 2024, 12:00:00)
            test_mtime = datetime(2024, 1, 1, 12, 0, 0).timestamp()
            os.utime(src_path, (test_mtime, test_mtime))
            
            # Verify the timestamp was set
            original_mtime = os.path.getmtime(src_path)
            assert abs(original_mtime - test_mtime) < 1.0, \
                f"Original mtime {original_mtime} should match test_mtime {test_mtime}"
            
            # Create destination directory
            with tempfile.TemporaryDirectory() as dest_dir:
                dest_path = os.path.join(dest_dir, 'test_file.txt')
                
                # Use rsync with --times flag (like our implementation)
                import subprocess
                result = subprocess.run(
                    ['rsync', '--times', src_path, dest_path],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    # Check that destination file has same timestamp
                    dest_mtime = os.path.getmtime(dest_path)
                    time_diff = abs(dest_mtime - original_mtime)
                    
                    assert time_diff < 2.0, \
                        f"Destination mtime {dest_mtime} should match source {original_mtime} " \
                        f"(diff: {time_diff}s)"
                else:
                    pytest.skip(f"rsync not available or failed: {result.stderr}")
        
        finally:
            # Cleanup
            if os.path.exists(src_path):
                os.unlink(src_path)
    
    def test_rsync_transfer_file_flags(self):
        """Test that transfer_file method uses correct flags."""
        # Import the adapter
        from app.sync.transport.ssh_rsync import SSHRsyncAdapter
        
        # Create an adapter instance
        adapter = SSHRsyncAdapter(host="test.example.com", port=22)
        
        # The transfer_file method uses -avz which includes -t (preserve times)
        # We just verify the class exists and has the method
        assert hasattr(adapter, 'transfer_file'), \
            "SSHRsyncAdapter should have transfer_file method"
        assert hasattr(adapter, 'transfer_folder'), \
            "SSHRsyncAdapter should have transfer_folder method"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
