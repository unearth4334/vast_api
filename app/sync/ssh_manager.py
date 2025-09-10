#!/usr/bin/env python3
"""
SSH Identity Manager

Handles SSH key validation, identity management, and user prompts for SSH setup.
Provides a clean interface for the web UI to manage SSH connectivity.
"""

import os
import subprocess
import logging
import json
import tempfile
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class SSHIdentityManager:
    """Manages SSH identities and provides user interaction for SSH setup"""
    
    def __init__(self, ssh_key_path: str = "/root/.ssh/id_ed25519"):
        """
        Initialize SSH Identity Manager
        
        Args:
            ssh_key_path: Path to the SSH private key
        """
        self.ssh_key_path = ssh_key_path
        self.ssh_pub_key_path = f"{ssh_key_path}.pub"
        self.ssh_config_path = "/root/.ssh/config"
        self.known_hosts_path = "/root/.ssh/known_hosts"
        self.ssh_dir = os.path.dirname(ssh_key_path)
        
    def validate_ssh_setup(self) -> Dict:
        """
        Validate the current SSH setup and return status
        
        Returns:
            dict: Validation results with status and details
        """
        validation_result = {
            'valid': True,
            'issues': [],
            'warnings': [],
            'ssh_key_exists': False,
            'ssh_key_readable': False,
            'ssh_agent_running': False,
            'identity_loaded': False,
            'permissions_ok': False
        }
        
        try:
            # Check SSH key existence
            if os.path.exists(self.ssh_key_path):
                validation_result['ssh_key_exists'] = True
                
                # Check key readability
                if os.access(self.ssh_key_path, os.R_OK):
                    validation_result['ssh_key_readable'] = True
                else:
                    validation_result['issues'].append(f"SSH key not readable: {self.ssh_key_path}")
                    validation_result['valid'] = False
            else:
                validation_result['issues'].append(f"SSH key not found: {self.ssh_key_path}")
                validation_result['valid'] = False
            
            # Check SSH key permissions
            if validation_result['ssh_key_exists']:
                key_stat = os.stat(self.ssh_key_path)
                key_perms = oct(key_stat.st_mode)[-3:]
                if key_perms != '600':
                    validation_result['warnings'].append(f"SSH key permissions should be 600, found {key_perms}")
                else:
                    validation_result['permissions_ok'] = True
            
            # Check if ssh-agent is running
            ssh_auth_sock = os.environ.get('SSH_AUTH_SOCK')
            if ssh_auth_sock and os.path.exists(ssh_auth_sock):
                validation_result['ssh_agent_running'] = True
                
                # Check if our identity is already loaded
                validation_result['identity_loaded'] = self._is_identity_loaded()
            else:
                validation_result['warnings'].append("SSH agent not running")
            
            # Check SSH directory permissions
            if os.path.exists(self.ssh_dir):
                dir_stat = os.stat(self.ssh_dir)
                dir_perms = oct(dir_stat.st_mode)[-3:]
                if dir_perms not in ['700', '750']:
                    validation_result['warnings'].append(f"SSH directory permissions should be 700/750, found {dir_perms}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating SSH setup: {e}")
            validation_result['valid'] = False
            validation_result['issues'].append(f"Validation error: {str(e)}")
            return validation_result
    
    def _is_identity_loaded(self) -> bool:
        """Check if our SSH identity is already loaded in ssh-agent"""
        try:
            result = subprocess.run(
                ['ssh-add', '-l'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse ssh-add output to see if our key is listed
                for line in result.stdout.split('\n'):
                    if 'media-sync@qnap' in line or self.ssh_key_path in line:
                        return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking loaded identities: {e}")
            return False
    
    def setup_ssh_agent(self) -> Dict:
        """
        Set up SSH agent and add identity
        
        Returns:
            dict: Setup result with status and messages
        """
        setup_result = {
            'success': False,
            'message': '',
            'ssh_agent_pid': None,
            'identity_added': False,
            'requires_user_confirmation': False
        }
        
        try:
            # Validate SSH setup first
            validation = self.validate_ssh_setup()
            if not validation['valid']:
                setup_result['message'] = f"SSH validation failed: {', '.join(validation['issues'])}"
                return setup_result
            
            # Check if ssh-agent is already running
            if not validation['ssh_agent_running']:
                logger.info("Starting SSH agent...")
                agent_result = subprocess.run(
                    ['ssh-agent', '-s'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if agent_result.returncode != 0:
                    setup_result['message'] = f"Failed to start SSH agent: {agent_result.stderr}"
                    return setup_result
                
                # Parse ssh-agent output to set environment variables
                for line in agent_result.stdout.split('\n'):
                    if 'SSH_AUTH_SOCK=' in line:
                        sock_path = line.split('=')[1].split(';')[0]
                        os.environ['SSH_AUTH_SOCK'] = sock_path
                    elif 'SSH_AGENT_PID=' in line:
                        pid = line.split('=')[1].split(';')[0]
                        os.environ['SSH_AGENT_PID'] = pid
                        try:
                            setup_result['ssh_agent_pid'] = int(pid)
                        except ValueError:
                            logger.warning(f"Invalid SSH_AGENT_PID format: {pid}")
            
            # Check if identity is already loaded
            if validation['identity_loaded']:
                setup_result['success'] = True
                setup_result['identity_added'] = True
                setup_result['message'] = "SSH identity already loaded"
                return setup_result
            
            # Add SSH identity
            logger.info(f"Adding SSH identity: {self.ssh_key_path}")
            add_result = subprocess.run(
                ['ssh-add', self.ssh_key_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if add_result.returncode == 0:
                setup_result['success'] = True
                setup_result['identity_added'] = True
                setup_result['message'] = f"SSH identity added successfully: {add_result.stdout.strip()}"
                logger.info(f"SSH identity added: {add_result.stdout.strip()}")
            else:
                # Check if this requires user confirmation (interactive prompt)
                if 'Enter passphrase' in add_result.stderr or 'Bad passphrase' in add_result.stderr:
                    setup_result['requires_user_confirmation'] = True
                    setup_result['message'] = "SSH key requires passphrase - user confirmation needed"
                else:
                    setup_result['message'] = f"Failed to add SSH identity: {add_result.stderr}"
            
            return setup_result
            
        except subprocess.TimeoutExpired:
            setup_result['message'] = "SSH setup timed out"
            return setup_result
        except Exception as e:
            logger.error(f"Error setting up SSH agent: {e}")
            setup_result['message'] = f"SSH setup error: {str(e)}"
            return setup_result
    
    def test_ssh_connection(self, host: str, port: int, user: str = "root", timeout: int = 10) -> Dict:
        """
        Test SSH connection to a specific host
        
        Args:
            host: Target hostname or IP
            port: SSH port
            user: SSH user
            timeout: Connection timeout
            
        Returns:
            dict: Connection test result
        """
        test_result = {
            'success': False,
            'host': host,
            'port': port,
            'user': user,
            'message': '',
            'response_time': None
        }
        
        try:
            start_time = datetime.now()
            
            cmd = [
                'ssh',
                '-i', self.ssh_key_path,
                '-p', str(port),
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'StrictHostKeyChecking=no',
                '-o', f'ConnectTimeout={timeout}',
                '-o', 'BatchMode=yes',
                f'{user}@{host}',
                'echo "ssh-test-success"'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 5
            )
            
            end_time = datetime.now()
            test_result['response_time'] = (end_time - start_time).total_seconds()
            
            if result.returncode == 0 and 'ssh-test-success' in result.stdout:
                test_result['success'] = True
                test_result['message'] = f"Connection successful in {test_result['response_time']:.2f}s"
            else:
                test_result['message'] = f"Connection failed: {result.stderr.strip() or 'Unknown error'}"
            
            return test_result
            
        except subprocess.TimeoutExpired:
            test_result['message'] = f"Connection timed out after {timeout} seconds"
            return test_result
        except Exception as e:
            logger.error(f"Error testing SSH connection: {e}")
            test_result['message'] = f"Test error: {str(e)}"
            return test_result
    
    def cleanup_ssh_agent(self) -> bool:
        """
        Clean up SSH agent
        
        Returns:
            bool: True if cleanup successful
        """
        try:
            ssh_agent_pid = os.environ.get('SSH_AGENT_PID')
            if ssh_agent_pid:
                subprocess.run(['ssh-agent', '-k'], timeout=5)
                # Clean up environment variables
                for var in ['SSH_AUTH_SOCK', 'SSH_AGENT_PID']:
                    if var in os.environ:
                        del os.environ[var]
                return True
            return True
        except Exception as e:
            logger.error(f"Error cleaning up SSH agent: {e}")
            return False
    
    def ensure_ssh_permissions(self) -> Dict:
        """
        Ensure SSH files have correct permissions
        
        Returns:
            dict: Permission fix result
        """
        result = {
            'success': True,
            'changes_made': [],
            'errors': []
        }
        
        try:
            # Ensure SSH directory exists and has correct permissions
            if not os.path.exists(self.ssh_dir):
                os.makedirs(self.ssh_dir, mode=0o700)
                result['changes_made'].append(f"Created SSH directory: {self.ssh_dir}")
            else:
                # Fix directory permissions
                current_perms = oct(os.stat(self.ssh_dir).st_mode)[-3:]
                if current_perms != '700':
                    os.chmod(self.ssh_dir, 0o700)
                    result['changes_made'].append(f"Fixed SSH directory permissions: {current_perms} -> 700")
            
            # Fix SSH key permissions
            if os.path.exists(self.ssh_key_path):
                current_perms = oct(os.stat(self.ssh_key_path).st_mode)[-3:]
                if current_perms != '600':
                    os.chmod(self.ssh_key_path, 0o600)
                    result['changes_made'].append(f"Fixed SSH key permissions: {current_perms} -> 600")
            
            # Fix public key permissions
            if os.path.exists(self.ssh_pub_key_path):
                current_perms = oct(os.stat(self.ssh_pub_key_path).st_mode)[-3:]
                if current_perms != '644':
                    os.chmod(self.ssh_pub_key_path, 0o644)
                    result['changes_made'].append(f"Fixed SSH public key permissions: {current_perms} -> 644")
            
            # Fix config file permissions
            if os.path.exists(self.ssh_config_path):
                current_perms = oct(os.stat(self.ssh_config_path).st_mode)[-3:]
                if current_perms != '644':
                    os.chmod(self.ssh_config_path, 0o644)
                    result['changes_made'].append(f"Fixed SSH config permissions: {current_perms} -> 644")
            
            return result
            
        except Exception as e:
            result['success'] = False
            result['errors'].append(f"Permission fix error: {str(e)}")
            return result
    
    def get_ssh_status(self) -> Dict:
        """
        Get comprehensive SSH status for the web UI
        
        Returns:
            dict: Complete SSH status information
        """
        validation = self.validate_ssh_setup()
        
        status = {
            'timestamp': datetime.now().isoformat(),
            'ssh_key_path': self.ssh_key_path,
            'validation': validation,
            'agent_running': validation['ssh_agent_running'],
            'identity_loaded': validation['identity_loaded'],
            'ready_for_sync': validation['valid'] and validation['ssh_agent_running'] and validation['identity_loaded']
        }
        
        return status