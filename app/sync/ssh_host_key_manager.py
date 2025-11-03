"""
SSH Host Key Manager
Detects and resolves SSH host identification errors
"""

import os
import re
import subprocess
import logging
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HostKeyError:
    """Represents a detected SSH host key error"""
    host: str
    port: int
    known_hosts_file: str
    line_number: int
    new_fingerprint: str
    error_message: str
    detected_at: str


class SSHHostKeyManager:
    """Manages SSH host key detection and resolution"""
    
    # Regex patterns for detecting host key errors
    HOST_KEY_ERROR_PATTERN = re.compile(
        r"WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED"
    )
    
    FINGERPRINT_PATTERN = re.compile(
        r"The fingerprint for the (\w+) key sent by the remote host is\s+(\S+)"
    )
    
    OFFENDING_KEY_PATTERN = re.compile(
        r"Offending \w+ key in ([^:]+):(\d+)"
    )
    
    HOST_PORT_PATTERN = re.compile(
        r"\[([^\]]+)\]:(\d+)"
    )
    
    REMOVE_COMMAND_PATTERN = re.compile(
        r"ssh-keygen -f '([^']+)' -R '\[([^\]]+)\]:(\d+)'"
    )
    
    def __init__(self, known_hosts_path: str = None):
        """
        Initialize SSH Host Key Manager
        
        Args:
            known_hosts_path: Path to known_hosts file (defaults to ~/.ssh/known_hosts)
        """
        if known_hosts_path is None:
            known_hosts_path = os.path.expanduser("~/.ssh/known_hosts")
        self.known_hosts_path = known_hosts_path
    
    def detect_host_key_error(self, ssh_output: str) -> Optional[HostKeyError]:
        """
        Detect SSH host key error from SSH command output
        
        Args:
            ssh_output: Output from SSH command (stderr typically)
            
        Returns:
            HostKeyError if detected, None otherwise
        """
        if not self.HOST_KEY_ERROR_PATTERN.search(ssh_output):
            return None
        
        logger.warning("Detected SSH host key change error")
        
        # Extract fingerprint
        fingerprint_match = self.FINGERPRINT_PATTERN.search(ssh_output)
        fingerprint = fingerprint_match.group(2) if fingerprint_match else "Unknown"
        
        # Extract offending key location
        offending_match = self.OFFENDING_KEY_PATTERN.search(ssh_output)
        if offending_match:
            known_hosts_file = offending_match.group(1)
            line_number = int(offending_match.group(2))
        else:
            known_hosts_file = self.known_hosts_path
            line_number = 0
        
        # Extract host and port from remove command
        remove_match = self.REMOVE_COMMAND_PATTERN.search(ssh_output)
        if remove_match:
            host = remove_match.group(2)
            port = int(remove_match.group(3))
        else:
            # Try to extract from other patterns
            host_port_match = self.HOST_PORT_PATTERN.search(ssh_output)
            if host_port_match:
                host = host_port_match.group(1)
                port = int(host_port_match.group(2))
            else:
                host = "Unknown"
                port = 0
        
        from datetime import datetime
        error = HostKeyError(
            host=host,
            port=port,
            known_hosts_file=known_hosts_file,
            line_number=line_number,
            new_fingerprint=fingerprint,
            error_message=ssh_output,
            detected_at=datetime.now().isoformat()
        )
        
        logger.info(f"Host key error detected for {host}:{port}")
        return error
    
    def remove_old_host_key(self, host: str, port: int, known_hosts_file: str = None) -> Tuple[bool, str]:
        """
        Remove old host key from known_hosts file
        
        Args:
            host: Hostname or IP address
            port: Port number
            known_hosts_file: Path to known_hosts file (optional)
            
        Returns:
            Tuple of (success, message)
        """
        if known_hosts_file is None:
            known_hosts_file = self.known_hosts_path
        
        # Construct the host specification
        host_spec = f"[{host}]:{port}"
        
        try:
            # Use ssh-keygen to remove the old key
            cmd = [
                "ssh-keygen",
                "-f", known_hosts_file,
                "-R", host_spec
            ]
            
            logger.info(f"Removing old host key for {host_spec} from {known_hosts_file}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"Successfully removed old host key for {host_spec}")
                return True, f"Old host key for {host_spec} removed successfully"
            else:
                error_msg = result.stderr or result.stdout
                logger.error(f"Failed to remove host key: {error_msg}")
                return False, f"Failed to remove host key: {error_msg}"
        
        except subprocess.TimeoutExpired:
            error_msg = "Command timed out while removing host key"
            logger.error(error_msg)
            return False, error_msg
        
        except Exception as e:
            error_msg = f"Error removing host key: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def accept_new_host_key(self, host: str, port: int, user: str = "root") -> Tuple[bool, str]:
        """
        Accept new host key by connecting with StrictHostKeyChecking=accept-new
        
        Args:
            host: Hostname or IP address
            port: Port number
            user: SSH user (defaults to 'root')
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Use SSH with accept-new option to accept the new key
            cmd = [
                "ssh",
                "-p", str(port),
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", "ConnectTimeout=10",
                "-o", "BatchMode=yes",
                f"{user}@{host}",
                "echo 'Host key accepted'"
            ]
            
            logger.info(f"Accepting new host key for {user}@{host}:{port}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"Successfully accepted new host key for {host}:{port}")
                return True, f"New host key for {host}:{port} accepted successfully"
            else:
                # Even if the command fails, the key might have been added
                # Check if it was a connection issue vs key issue
                error_msg = result.stderr or result.stdout
                if "Host key verification failed" not in error_msg:
                    # The key was likely accepted, but connection failed for other reasons
                    logger.warning(f"Key accepted but connection failed: {error_msg}")
                    return True, f"Host key accepted (connection warning: {error_msg[:100]})"
                else:
                    logger.error(f"Failed to accept host key: {error_msg}")
                    return False, f"Failed to accept host key: {error_msg}"
        
        except subprocess.TimeoutExpired:
            error_msg = "Command timed out while accepting host key"
            logger.error(error_msg)
            return False, error_msg
        
        except Exception as e:
            error_msg = f"Error accepting host key: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def resolve_host_key_error(self, error: HostKeyError, user: str = "root") -> Tuple[bool, str]:
        """
        Resolve a host key error by removing old key and accepting new one
        
        Args:
            error: HostKeyError instance
            user: SSH user (defaults to 'root')
            
        Returns:
            Tuple of (success, message)
        """
        logger.info(f"Resolving host key error for {error.host}:{error.port}")
        
        # Step 1: Remove old host key
        success, message = self.remove_old_host_key(
            error.host,
            error.port,
            error.known_hosts_file
        )
        
        if not success:
            return False, f"Failed to remove old key: {message}"
        
        # Step 2: Accept new host key
        success, message = self.accept_new_host_key(error.host, error.port, user)
        
        if not success:
            return False, f"Old key removed but failed to accept new key: {message}"
        
        return True, f"Host key resolved successfully for {error.host}:{error.port}"
