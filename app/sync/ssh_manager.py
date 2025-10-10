#!/usr/bin/env python3
"""
SSH Connection Manager
Handles SSH agent management, key loading, and connection validation
"""

import os
import subprocess
import logging
import time
import tempfile
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class SSHManager:
    """Manages SSH connections, keys, and agent for sync operations"""
    
    def __init__(self, ssh_key_path: str = "/root/.ssh/id_ed25519"):
        self.ssh_key_path = ssh_key_path
        self.ssh_agent_pid = None
        self.ssh_auth_sock = None
        
    def validate_ssh_key(self) -> Dict[str, any]:
        """Validate SSH key exists and has correct permissions"""
        result = {
            'valid': False,
            'path': self.ssh_key_path,
            'exists': False,
            'readable': False,
            'permissions': None,
            'message': ''
        }
        
        if not os.path.exists(self.ssh_key_path):
            result['message'] = f"SSH key not found at {self.ssh_key_path}"
            return result
            
        result['exists'] = True
        
        try:
            # Check if file is readable
            with open(self.ssh_key_path, 'r') as f:
                f.read(1)
            result['readable'] = True
        except (IOError, PermissionError) as e:
            result['message'] = f"SSH key not readable: {e}"
            return result
        
        # Check permissions
        stat_info = os.stat(self.ssh_key_path)
        permissions = oct(stat_info.st_mode)[-3:]
        result['permissions'] = permissions
        
        if permissions != '600':
            result['message'] = f"SSH key has incorrect permissions {permissions}, should be 600"
            return result
            
        result['valid'] = True
        result['message'] = "SSH key validation successful"
        return result
    
    def start_ssh_agent(self) -> Dict[str, any]:
        """Start SSH agent and return environment variables"""
        result = {
            'success': False,
            'pid': None,
            'auth_sock': None,
            'message': ''
        }
        
        try:
            # Start ssh-agent
            proc = subprocess.run(['ssh-agent', '-s'], 
                                 capture_output=True, text=True, timeout=10)
            
            if proc.returncode != 0:
                result['message'] = f"Failed to start ssh-agent: {proc.stderr}"
                return result
            
            # Parse the output to extract environment variables
            for line in proc.stdout.strip().split('\n'):
                if line.startswith('SSH_AUTH_SOCK='):
                    auth_sock = line.split('=', 1)[1].rstrip(';')
                    self.ssh_auth_sock = auth_sock
                    os.environ['SSH_AUTH_SOCK'] = auth_sock
                    result['auth_sock'] = auth_sock
                elif line.startswith('SSH_AGENT_PID='):
                    pid = line.split('=', 1)[1].rstrip(';')
                    self.ssh_agent_pid = int(pid)
                    os.environ['SSH_AGENT_PID'] = pid
                    result['pid'] = int(pid)
            
            if self.ssh_agent_pid and self.ssh_auth_sock:
                result['success'] = True
                result['message'] = f"SSH agent started successfully (PID: {self.ssh_agent_pid})"
                logger.info(result['message'])
            else:
                result['message'] = "Failed to parse ssh-agent output"
                
        except subprocess.TimeoutExpired:
            result['message'] = "SSH agent startup timed out"
        except Exception as e:
            result['message'] = f"Error starting ssh-agent: {e}"
            
        return result
    
    def add_ssh_key(self) -> Dict[str, any]:
        """Add SSH key to the agent"""
        result = {
            'success': False,
            'message': ''
        }
        
        # First validate the key
        key_validation = self.validate_ssh_key()
        if not key_validation['valid']:
            result['message'] = f"Key validation failed: {key_validation['message']}"
            return result
        
        try:
            # Add key to agent
            proc = subprocess.run(['ssh-add', self.ssh_key_path], 
                                 capture_output=True, text=True, timeout=10)
            
            if proc.returncode == 0:
                result['success'] = True
                result['message'] = "SSH key added successfully"
                logger.info(f"SSH key {self.ssh_key_path} added to agent")
            else:
                result['message'] = f"Failed to add SSH key: {proc.stderr or proc.stdout}"
                logger.error(result['message'])
                
        except subprocess.TimeoutExpired:
            result['message'] = "SSH key addition timed out"
        except Exception as e:
            result['message'] = f"Error adding SSH key: {e}"
            
        return result
    
    def test_ssh_connection(self, host: str, port: str, user: str = "root", timeout: int = 10) -> Dict[str, any]:
        """Test SSH connection to specified host"""
        result = {
            'success': False,
            'host': host,
            'port': port,
            'user': user,
            'message': '',
            'output': ''
        }
        
        try:
            cmd = [
                'ssh',
                '-p', str(port),
                '-i', self.ssh_key_path,
                '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
                '-o', 'IdentitiesOnly=yes',
                '-o', 'StrictHostKeyChecking=yes',
                '-o', 'ConnectTimeout=10',
                '-o', 'BatchMode=yes',  # Prevent interactive prompts
                f"{user}@{host}",
                'echo "SSH connection test successful"'
            ]
            
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            
            result['output'] = proc.stdout.strip()
            
            if proc.returncode == 0:
                result['success'] = True
                result['message'] = "SSH connection successful"
            else:
                result['message'] = f"SSH connection failed: {proc.stderr.strip()}"
                
        except subprocess.TimeoutExpired:
            result['message'] = f"SSH connection timed out after {timeout} seconds"
        except Exception as e:
            result['message'] = f"SSH connection error: {e}"
            
        return result
    
    def setup_ssh_for_sync(self, host: str, port: str, user: str = "root") -> Dict[str, any]:
        """Complete SSH setup process for sync operations"""
        result = {
            'success': False,
            'steps': {},
            'message': ''
        }
        
        logger.info(f"Setting up SSH connection for {user}@{host}:{port}")
        
        # Step 1: Validate SSH key
        key_result = self.validate_ssh_key()
        result['steps']['key_validation'] = key_result
        if not key_result['valid']:
            result['message'] = f"SSH key validation failed: {key_result['message']}"
            return result
        
        # Step 2: Start SSH agent (or use existing)
        if not self.ssh_agent_pid or not self.ssh_auth_sock:
            agent_result = self.start_ssh_agent()
            result['steps']['ssh_agent'] = agent_result
            if not agent_result['success']:
                result['message'] = f"SSH agent setup failed: {agent_result['message']}"
                return result
        else:
            result['steps']['ssh_agent'] = {'success': True, 'message': 'Using existing SSH agent'}
        
        # Step 3: Add SSH key to agent
        key_add_result = self.add_ssh_key()
        result['steps']['key_addition'] = key_add_result
        if not key_add_result['success']:
            result['message'] = f"Failed to add SSH key: {key_add_result['message']}"
            return result
        
        # Step 4: Test SSH connection
        conn_result = self.test_ssh_connection(host, port, user)
        result['steps']['connection_test'] = conn_result
        if not conn_result['success']:
            result['message'] = f"SSH connection test failed: {conn_result['message']}"
            return result
        
        result['success'] = True
        result['message'] = "SSH setup completed successfully"
        logger.info(f"SSH setup successful for {user}@{host}:{port}")
        
        return result
    
    def cleanup_ssh_agent(self):
        """Clean up SSH agent if we started it"""
        if self.ssh_agent_pid:
            try:
                subprocess.run(['ssh-agent', '-k'], timeout=5)
                logger.info(f"SSH agent {self.ssh_agent_pid} terminated")
            except Exception as e:
                logger.warning(f"Failed to terminate SSH agent: {e}")
            finally:
                self.ssh_agent_pid = None
                self.ssh_auth_sock = None
    
    def get_ssh_environment(self) -> Dict[str, str]:
        """Get SSH environment variables for subprocess execution"""
        env = os.environ.copy()
        
        if self.ssh_auth_sock:
            env['SSH_AUTH_SOCK'] = self.ssh_auth_sock
        if self.ssh_agent_pid:
            env['SSH_AGENT_PID'] = str(self.ssh_agent_pid)
            
        return env
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup_ssh_agent()


def validate_ssh_prerequisites() -> Dict[str, any]:
    """Validate SSH prerequisites for the sync system"""
    result = {
        'valid': True,
        'issues': [],
        'ssh_key_path': '/root/.ssh/id_ed25519',
        'known_hosts_path': '/root/.ssh/known_hosts'
    }
    
    # Check SSH key
    ssh_key_path = '/root/.ssh/id_ed25519'
    if not os.path.exists(ssh_key_path):
        result['valid'] = False
        result['issues'].append(f"SSH private key not found at {ssh_key_path}")
    else:
        try:
            stat_info = os.stat(ssh_key_path)
            permissions = oct(stat_info.st_mode)[-3:]
            if permissions != '600':
                result['valid'] = False
                result['issues'].append(f"SSH key has incorrect permissions {permissions}, should be 600")
        except Exception as e:
            result['valid'] = False
            result['issues'].append(f"Cannot check SSH key permissions: {e}")
    
    # Check known hosts
    known_hosts_path = '/root/.ssh/known_hosts'
    if not os.path.exists(known_hosts_path):
        result['issues'].append(f"Known hosts file not found at {known_hosts_path} (this may cause connection issues)")
    
    # Check SSH directory
    ssh_dir = '/root/.ssh'
    if not os.path.exists(ssh_dir):
        result['valid'] = False
        result['issues'].append(f"SSH directory not found at {ssh_dir}")
    else:
        try:
            stat_info = os.stat(ssh_dir)
            permissions = oct(stat_info.st_mode)[-3:]
            if permissions not in ['700', '750']:
                result['issues'].append(f"SSH directory has permissions {permissions}, recommend 700 or 750")
        except Exception as e:
            result['issues'].append(f"Cannot check SSH directory permissions: {e}")
    
    return result


if __name__ == "__main__":
    # Simple CLI for testing
    import argparse
    
    parser = argparse.ArgumentParser(description='SSH Manager for Vast API')
    parser.add_argument('--host', default='10.0.78.108', help='Host to test')
    parser.add_argument('--port', default='2222', help='Port to test')
    parser.add_argument('--user', default='root', help='User to test')
    parser.add_argument('--check-prereqs', action='store_true', help='Check prerequisites only')
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    if args.check_prereqs:
        result = validate_ssh_prerequisites()
        print(f"Prerequisites valid: {result['valid']}")
        if result['issues']:
            print("Issues found:")
            for issue in result['issues']:
                print(f"  - {issue}")
    else:
        with SSHManager() as ssh_mgr:
            result = ssh_mgr.setup_ssh_for_sync(args.host, args.port, args.user)
            print(f"SSH setup success: {result['success']}")
            print(f"Message: {result['message']}")