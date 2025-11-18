"""
Resource Installer

Handles installation of resources to remote VastAI instances via SSH.
Executes download commands and tracks installation progress.
"""

import subprocess
import logging
from typing import Dict, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class ResourceInstaller:
    """Installer for deploying resources to remote instances"""
    
    def __init__(self, ssh_key: str = '/root/.ssh/id_ed25519'):
        """
        Initialize resource installer
        
        Args:
            ssh_key: Path to SSH private key
        """
        self.ssh_key = ssh_key
        logger.info(f"Initialized ResourceInstaller with SSH key: {self.ssh_key}")
    
    def install_resource(
        self,
        ssh_host: str,
        ssh_port: int,
        ui_home: str,
        download_command: str,
        resource_name: str = "resource"
    ) -> Dict:
        """
        Install a single resource on remote instance
        
        Args:
            ssh_host: SSH hostname or IP
            ssh_port: SSH port
            ui_home: ComfyUI home directory on remote instance
            download_command: Bash command to download the resource
            resource_name: Name for logging purposes
            
        Returns:
            Dictionary with installation result
        """
        logger.info(f"Installing resource '{resource_name}' to {ssh_host}:{ssh_port}")
        
        # Substitute environment variables
        command = download_command.replace('$UI_HOME', ui_home)
        
        # Wrap in SSH command
        ssh_cmd = [
            'ssh',
            '-p', str(ssh_port),
            '-i', self.ssh_key,
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
            '-o', 'IdentitiesOnly=yes',
            f'root@{ssh_host}',
            f'cd /tmp && {command}'
        ]
        
        logger.debug(f"Executing SSH command: {' '.join(ssh_cmd)}")
        
        try:
            # Execute with streaming output
            process = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            output_lines = []
            for line in process.stdout:
                line_stripped = line.rstrip()
                output_lines.append(line_stripped)
                logger.debug(f"  {line_stripped}")
            
            return_code = process.wait(timeout=3600)  # 1 hour timeout
            
            success = return_code == 0
            
            if success:
                logger.info(f"Successfully installed resource '{resource_name}'")
            else:
                logger.error(f"Failed to install resource '{resource_name}' (exit code {return_code})")
            
            return {
                'success': success,
                'output': output_lines,
                'return_code': return_code,
                'resource': resource_name
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout while installing resource '{resource_name}'")
            process.kill()
            return {
                'success': False,
                'output': ['Installation timed out after 1 hour'],
                'return_code': -1,
                'resource': resource_name
            }
        except Exception as e:
            logger.error(f"Error installing resource '{resource_name}': {e}")
            return {
                'success': False,
                'output': [str(e)],
                'return_code': -1,
                'resource': resource_name
            }
    
    def install_multiple(
        self,
        ssh_host: str,
        ssh_port: int,
        ui_home: str,
        resources: List[Dict]
    ) -> Dict:
        """
        Install multiple resources with dependency resolution
        
        Args:
            ssh_host: SSH hostname or IP
            ssh_port: SSH port
            ui_home: ComfyUI home directory
            resources: List of resource dictionaries
            
        Returns:
            Dictionary with overall installation results
        """
        logger.info(f"Installing {len(resources)} resources to {ssh_host}:{ssh_port}")
        
        # Resolve dependencies (simple ordering for now)
        ordered_resources = self._resolve_dependencies(resources)
        
        results = []
        for resource in ordered_resources:
            resource_name = resource.get('filename', 'unknown')
            result = self.install_resource(
                ssh_host,
                ssh_port,
                ui_home,
                resource['download_command'],
                resource_name=resource_name
            )
            result['filepath'] = resource['filepath']
            results.append(result)
            
            if not result['success']:
                logger.warning(f"Stopping installation due to failure at '{resource_name}'")
                break  # Stop on first failure
        
        success_count = len([r for r in results if r['success']])
        overall_success = success_count == len(resources)
        
        logger.info(f"Installation complete: {success_count}/{len(resources)} successful")
        
        return {
            'success': overall_success,
            'installed': success_count,
            'total': len(resources),
            'results': results
        }
    
    def _resolve_dependencies(self, resources: List[Dict]) -> List[Dict]:
        """
        Order resources by dependencies
        
        For now, this is a simple pass-through. A full implementation
        would perform topological sort based on the 'dependencies' field.
        
        Args:
            resources: List of resource dictionaries
            
        Returns:
            Ordered list of resources
        """
        # TODO: Implement proper dependency resolution with topological sort
        # For now, just return resources as-is
        logger.debug("Dependency resolution not yet implemented, using original order")
        return resources
    
    def verify_installation(
        self,
        ssh_host: str,
        ssh_port: int,
        ui_home: str,
        resource_path: str
    ) -> Dict:
        """
        Verify if a resource is installed on remote instance
        
        Args:
            ssh_host: SSH hostname or IP
            ssh_port: SSH port
            ui_home: ComfyUI home directory
            resource_path: Path to check (with $UI_HOME variable)
            
        Returns:
            Dictionary with verification result
        """
        # Substitute environment variables
        path = resource_path.replace('$UI_HOME', ui_home)
        
        # Check if path exists
        check_cmd = f'test -e {path} && echo "exists" || echo "not_found"'
        
        ssh_cmd = [
            'ssh',
            '-p', str(ssh_port),
            '-i', self.ssh_key,
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
            '-o', 'IdentitiesOnly=yes',
            f'root@{ssh_host}',
            check_cmd
        ]
        
        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            exists = 'exists' in result.stdout
            
            return {
                'success': True,
                'exists': exists,
                'path': path
            }
        except Exception as e:
            logger.error(f"Error verifying installation: {e}")
            return {
                'success': False,
                'exists': False,
                'error': str(e)
            }
