"""
ComfyUI File Transfer Utilities
Handles uploading workflow files, input images, and downloading outputs via SSH/SCP.
"""

import os
import logging
import subprocess
import json
from pathlib import Path
from typing import List, Optional, Tuple
from .ssh_tunnel import SSHTunnel

logger = logging.getLogger(__name__)


class ComfyUIFileTransfer:
    """Manages file transfers for ComfyUI workflows via SSH/SCP."""
    
    def __init__(self, ssh_connection: str):
        """
        Initialize file transfer manager.
        
        Args:
            ssh_connection: SSH connection string (e.g., "ssh -p 40738 root@198.53.64.194")
        """
        self.ssh_connection = ssh_connection
        self.host, self.port, self.user = SSHTunnel.parse_ssh_connection(ssh_connection)
        logger.info(f"FileTransfer initialized for {self.user}@{self.host}:{self.port}")
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """
        Upload a single file to remote instance.
        
        Args:
            local_path: Local file path
            remote_path: Remote destination path
            
        Returns:
            True if upload succeeded
        """
        if not os.path.exists(local_path):
            logger.error(f"Local file not found: {local_path}")
            return False
        
        try:
            # Ensure remote directory exists
            remote_dir = os.path.dirname(remote_path)
            if remote_dir:
                mkdir_cmd = [
                    'ssh',
                    '-p', self.port,
                    f'{self.user}@{self.host}',
                    f'mkdir -p {remote_dir}'
                ]
                subprocess.run(mkdir_cmd, check=True, capture_output=True, timeout=10)
            
            # Upload file
            scp_cmd = [
                'scp',
                '-P', self.port,
                local_path,
                f'{self.user}@{self.host}:{remote_path}'
            ]
            
            logger.info(f"Uploading {local_path} -> {remote_path}")
            result = subprocess.run(scp_cmd, capture_output=True, timeout=60)
            
            if result.returncode != 0:
                logger.error(f"Upload failed: {result.stderr.decode('utf-8')}")
                return False
            
            logger.info(f"Upload completed: {os.path.basename(local_path)}")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"Upload timed out: {local_path}")
            return False
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return False
    
    def upload_files(self, files: List[Tuple[str, str]]) -> bool:
        """
        Upload multiple files.
        
        Args:
            files: List of (local_path, remote_path) tuples
            
        Returns:
            True if all uploads succeeded
        """
        success = True
        for local_path, remote_path in files:
            if not self.upload_file(local_path, remote_path):
                success = False
        return success
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Download a single file from remote instance.
        
        Args:
            remote_path: Remote file path
            local_path: Local destination path
            
        Returns:
            True if download succeeded
        """
        try:
            # Ensure local directory exists
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)
            
            # Download file
            scp_cmd = [
                'scp',
                '-P', self.port,
                f'{self.user}@{self.host}:{remote_path}',
                local_path
            ]
            
            logger.info(f"Downloading {remote_path} -> {local_path}")
            result = subprocess.run(scp_cmd, capture_output=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"Download failed: {result.stderr.decode('utf-8')}")
                return False
            
            logger.info(f"Download completed: {os.path.basename(local_path)}")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"Download timed out: {remote_path}")
            return False
        except Exception as e:
            logger.error(f"Download error: {e}")
            return False
    
    def download_files(self, files: List[Tuple[str, str]]) -> bool:
        """
        Download multiple files.
        
        Args:
            files: List of (remote_path, local_path) tuples
            
        Returns:
            True if all downloads succeeded
        """
        success = True
        for remote_path, local_path in files:
            if not self.download_file(remote_path, local_path):
                success = False
        return success
    
    def execute_remote_command(self, command: str, timeout: int = 30) -> Tuple[bool, str, str]:
        """
        Execute a command on the remote instance.
        
        Args:
            command: Command to execute
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            ssh_cmd = [
                'ssh',
                '-p', self.port,
                f'{self.user}@{self.host}',
                command
            ]
            
            logger.debug(f"Executing remote command: {command}")
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            logger.error(f"Remote command timed out: {command}")
            return False, "", "Command timed out"
        except Exception as e:
            logger.error(f"Remote command error: {e}")
            return False, "", str(e)
    
    def upload_workflow(self, workflow_file: str, remote_dir: str = "/tmp") -> Optional[str]:
        """
        Upload workflow JSON file.
        
        Args:
            workflow_file: Local path to workflow JSON
            remote_dir: Remote directory for upload
            
        Returns:
            Remote file path or None on failure
        """
        if not os.path.exists(workflow_file):
            logger.error(f"Workflow file not found: {workflow_file}")
            return None
        
        # Read and validate workflow JSON
        try:
            with open(workflow_file, 'r') as f:
                workflow_data = json.load(f)
            logger.info(f"Workflow validated: {len(workflow_data)} nodes")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid workflow JSON: {e}")
            return None
        
        # Generate remote filename
        remote_filename = f"workflow_{os.getpid()}_{int(os.path.basename(workflow_file).replace('.json', ''))}.json"
        remote_path = f"{remote_dir}/{remote_filename}"
        
        # Upload
        if self.upload_file(workflow_file, remote_path):
            return remote_path
        return None
    
    def upload_input_images(
        self, 
        image_paths: List[str], 
        remote_dir: str = "/workspace/ComfyUI/input"
    ) -> List[str]:
        """
        Upload input images to ComfyUI input directory.
        
        Args:
            image_paths: List of local image paths
            remote_dir: Remote ComfyUI input directory
            
        Returns:
            List of successfully uploaded remote paths
        """
        uploaded_paths = []
        
        for local_path in image_paths:
            if not os.path.exists(local_path):
                logger.warning(f"Input image not found: {local_path}")
                continue
            
            # Use original filename
            filename = os.path.basename(local_path)
            remote_path = f"{remote_dir}/{filename}"
            
            if self.upload_file(local_path, remote_path):
                uploaded_paths.append(remote_path)
        
        logger.info(f"Uploaded {len(uploaded_paths)}/{len(image_paths)} input images")
        return uploaded_paths
    
    def download_outputs(
        self,
        output_filenames: List[str],
        local_dir: str,
        remote_dir: str = "/workspace/ComfyUI/output"
    ) -> List[str]:
        """
        Download output files from ComfyUI.
        
        Args:
            output_filenames: List of output filenames
            local_dir: Local directory to save outputs
            remote_dir: Remote ComfyUI output directory
            
        Returns:
            List of successfully downloaded local paths
        """
        downloaded_paths = []
        
        # Ensure local directory exists
        os.makedirs(local_dir, exist_ok=True)
        
        for filename in output_filenames:
            remote_path = f"{remote_dir}/{filename}"
            local_path = os.path.join(local_dir, filename)
            
            if self.download_file(remote_path, local_path):
                downloaded_paths.append(local_path)
        
        logger.info(f"Downloaded {len(downloaded_paths)}/{len(output_filenames)} outputs")
        return downloaded_paths
    
    def cleanup_remote_files(self, remote_paths: List[str]) -> bool:
        """
        Clean up temporary files on remote instance.
        
        Args:
            remote_paths: List of remote file paths to delete
            
        Returns:
            True if cleanup succeeded
        """
        if not remote_paths:
            return True
        
        # Build rm command
        paths_str = ' '.join(f'"{p}"' for p in remote_paths)
        command = f'rm -f {paths_str}'
        
        success, stdout, stderr = self.execute_remote_command(command)
        
        if success:
            logger.info(f"Cleaned up {len(remote_paths)} remote files")
        else:
            logger.warning(f"Cleanup failed: {stderr}")
        
        return success
    
    def get_file_size(self, remote_path: str) -> Optional[int]:
        """
        Get size of a remote file in bytes.
        
        Args:
            remote_path: Remote file path
            
        Returns:
            File size in bytes or None on error
        """
        command = f'stat -f %z "{remote_path}" 2>/dev/null || stat -c %s "{remote_path}"'
        success, stdout, stderr = self.execute_remote_command(command)
        
        if success and stdout.strip():
            try:
                return int(stdout.strip())
            except ValueError:
                pass
        
        return None
    
    def file_exists(self, remote_path: str) -> bool:
        """
        Check if a file exists on the remote instance.
        
        Args:
            remote_path: Remote file path
            
        Returns:
            True if file exists
        """
        command = f'test -f "{remote_path}" && echo "exists"'
        success, stdout, stderr = self.execute_remote_command(command, timeout=5)
        
        return success and "exists" in stdout


def create_file_transfer(ssh_connection: str) -> ComfyUIFileTransfer:
    """
    Create a file transfer manager.
    
    Args:
        ssh_connection: SSH connection string
        
    Returns:
        ComfyUIFileTransfer instance
    """
    return ComfyUIFileTransfer(ssh_connection)
