"""
Unit tests for ComfyUIFileTransfer
Tests file upload/download, remote command execution, and cleanup operations.
"""

import unittest
import os
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
from app.sync.comfyui_file_transfer import ComfyUIFileTransfer


class TestComfyUIFileTransfer(unittest.TestCase):
    """Test cases for ComfyUI file transfer operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.ssh_connection = "ssh -p 40738 root@198.53.64.194"
        self.transfer = ComfyUIFileTransfer(self.ssh_connection)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test file transfer initialization."""
        self.assertEqual(self.transfer.host, "198.53.64.194")
        self.assertEqual(self.transfer.port, "40738")
        self.assertEqual(self.transfer.user, "root")
    
    @patch('subprocess.run')
    def test_upload_file_success(self, mock_run):
        """Test successful file upload."""
        # Create test file
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Mock successful upload
        mock_run.return_value = Mock(returncode=0)
        
        success = self.transfer.upload_file(test_file, "/tmp/test.txt")
        
        self.assertTrue(success)
        self.assertEqual(mock_run.call_count, 2)  # mkdir + scp
    
    @patch('subprocess.run')
    def test_upload_file_not_found(self, mock_run):
        """Test upload with non-existent file."""
        success = self.transfer.upload_file("/nonexistent/file.txt", "/tmp/test.txt")
        
        self.assertFalse(success)
        mock_run.assert_not_called()
    
    @patch('subprocess.run')
    def test_upload_file_failure(self, mock_run):
        """Test failed file upload."""
        # Create test file
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Mock failed upload
        mock_run.side_effect = [
            Mock(returncode=0),  # mkdir succeeds
            Mock(returncode=1, stderr=b"Upload failed")  # scp fails
        ]
        
        success = self.transfer.upload_file(test_file, "/tmp/test.txt")
        
        self.assertFalse(success)
    
    @patch('subprocess.run')
    def test_download_file_success(self, mock_run):
        """Test successful file download."""
        # Mock successful download
        mock_run.return_value = Mock(returncode=0)
        
        local_path = os.path.join(self.temp_dir, "downloaded.txt")
        success = self.transfer.download_file("/tmp/remote.txt", local_path)
        
        self.assertTrue(success)
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_download_file_failure(self, mock_run):
        """Test failed file download."""
        # Mock failed download
        mock_run.return_value = Mock(returncode=1, stderr=b"Download failed")
        
        local_path = os.path.join(self.temp_dir, "downloaded.txt")
        success = self.transfer.download_file("/tmp/remote.txt", local_path)
        
        self.assertFalse(success)
    
    @patch('subprocess.run')
    def test_execute_remote_command_success(self, mock_run):
        """Test successful remote command execution."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="command output",
            stderr=""
        )
        
        success, stdout, stderr = self.transfer.execute_remote_command("echo test")
        
        self.assertTrue(success)
        self.assertEqual(stdout, "command output")
        self.assertEqual(stderr, "")
    
    @patch('subprocess.run')
    def test_execute_remote_command_failure(self, mock_run):
        """Test failed remote command execution."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="command error"
        )
        
        success, stdout, stderr = self.transfer.execute_remote_command("invalid_command")
        
        self.assertFalse(success)
        self.assertEqual(stderr, "command error")
    
    @patch('subprocess.run')
    def test_upload_workflow(self, mock_run):
        """Test workflow JSON upload."""
        # Create test workflow file
        workflow_file = os.path.join(self.temp_dir, "workflow.json")
        workflow_data = {"node1": {"class_type": "LoadImage"}}
        with open(workflow_file, 'w') as f:
            json.dump(workflow_data, f)
        
        # Mock successful upload
        mock_run.return_value = Mock(returncode=0)
        
        remote_path = self.transfer.upload_workflow(workflow_file, "/tmp")
        
        self.assertIsNotNone(remote_path)
        self.assertTrue(remote_path.startswith("/tmp/workflow_"))
        self.assertTrue(remote_path.endswith(".json"))
    
    @patch('subprocess.run')
    def test_upload_workflow_invalid_json(self, mock_run):
        """Test workflow upload with invalid JSON."""
        # Create invalid JSON file
        workflow_file = os.path.join(self.temp_dir, "invalid.json")
        with open(workflow_file, 'w') as f:
            f.write("{ invalid json }")
        
        remote_path = self.transfer.upload_workflow(workflow_file, "/tmp")
        
        self.assertIsNone(remote_path)
        mock_run.assert_not_called()
    
    @patch('subprocess.run')
    def test_upload_input_images(self, mock_run):
        """Test input image uploads."""
        # Create test images
        img1 = os.path.join(self.temp_dir, "img1.png")
        img2 = os.path.join(self.temp_dir, "img2.png")
        
        with open(img1, 'w') as f:
            f.write("fake image 1")
        with open(img2, 'w') as f:
            f.write("fake image 2")
        
        # Mock successful uploads
        mock_run.return_value = Mock(returncode=0)
        
        uploaded = self.transfer.upload_input_images([img1, img2], "/workspace/input")
        
        self.assertEqual(len(uploaded), 2)
        self.assertTrue(any("img1.png" in path for path in uploaded))
        self.assertTrue(any("img2.png" in path for path in uploaded))
    
    @patch('subprocess.run')
    def test_download_outputs(self, mock_run):
        """Test output file downloads."""
        # Mock successful downloads
        mock_run.return_value = Mock(returncode=0)
        
        output_filenames = ["output1.png", "output2.png"]
        downloaded = self.transfer.download_outputs(
            output_filenames,
            self.temp_dir,
            "/workspace/output"
        )
        
        self.assertEqual(len(downloaded), 2)
        self.assertTrue(any("output1.png" in path for path in downloaded))
        self.assertTrue(any("output2.png" in path for path in downloaded))
    
    @patch('subprocess.run')
    def test_cleanup_remote_files(self, mock_run):
        """Test remote file cleanup."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        remote_paths = ["/tmp/file1.json", "/tmp/file2.png"]
        success = self.transfer.cleanup_remote_files(remote_paths)
        
        self.assertTrue(success)
        mock_run.assert_called_once()
        
        # Verify rm command was constructed correctly
        call_args = mock_run.call_args[0][0]
        self.assertIn('rm -f', ' '.join(call_args))
    
    @patch('subprocess.run')
    def test_file_exists(self, mock_run):
        """Test remote file existence check."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="exists\n",
            stderr=""
        )
        
        exists = self.transfer.file_exists("/tmp/test.txt")
        
        self.assertTrue(exists)
    
    @patch('subprocess.run')
    def test_file_not_exists(self, mock_run):
        """Test remote file does not exist."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        exists = self.transfer.file_exists("/tmp/nonexistent.txt")
        
        self.assertFalse(exists)
    
    @patch('subprocess.run')
    def test_get_file_size(self, mock_run):
        """Test getting remote file size."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="1024\n",
            stderr=""
        )
        
        size = self.transfer.get_file_size("/tmp/test.txt")
        
        self.assertEqual(size, 1024)
    
    @patch('subprocess.run')
    def test_upload_files_batch(self, mock_run):
        """Test batch file upload."""
        # Create test files
        file1 = os.path.join(self.temp_dir, "file1.txt")
        file2 = os.path.join(self.temp_dir, "file2.txt")
        
        with open(file1, 'w') as f:
            f.write("content 1")
        with open(file2, 'w') as f:
            f.write("content 2")
        
        # Mock successful uploads
        mock_run.return_value = Mock(returncode=0)
        
        files = [
            (file1, "/tmp/file1.txt"),
            (file2, "/tmp/file2.txt")
        ]
        
        success = self.transfer.upload_files(files)
        
        self.assertTrue(success)


if __name__ == '__main__':
    unittest.main()
