"""
Resource Installer

Handles installation of resources to remote VastAI instances via SSH.
Executes download commands and tracks installation progress.
"""

import subprocess
import logging
import re
from typing import Dict, List, Tuple, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


def _is_host_key_error(stderr: str, return_code: int) -> bool:
    """
    Check if SSH error is due to host key verification
    
    Args:
        stderr: Standard error output from SSH command
        return_code: Process return code
        
    Returns:
        True if error is related to host key verification
    """
    if return_code != 255:
        return False
    
    stderr_lower = stderr.lower()
    
    # Check for common host key error patterns
    host_key_patterns = [
        'host key verification failed',
        'no matching host key type found',
        'host key for',
        'remote host identification has changed',
        'add correct host key'
    ]
    
    return any(pattern in stderr_lower for pattern in host_key_patterns)


class ProgressParser:
    """Parse civitdl progress output"""
    
    # Regex patterns for civitdl output
    PROGRESS_PATTERN = re.compile(
        r'(Images|Model|Cache):\s*(\d+)%\|[█▓▒░\s]*\|\s*([\d.]+[KMGT]?i?B?)/([\d.]+[KMGT]?i?B?)\s*\[([^\]]+)\<([^\]]+),\s*([\d.]+[KMGT]?i?B?/s)\]'
    )
    STAGE_START = re.compile(r'Now downloading "([^"]+)"')
    STAGE_COMPLETE = re.compile(r'Download completed for "([^"]+)"')
    
    @classmethod
    def parse_line(cls, line: str) -> Optional[Dict]:
        """
        Parse a single line of civitdl output
        
        Args:
            line: Output line from civitdl
            
        Returns:
            Dictionary with progress info or None if not a progress line
        """
        # Check for download start
        match = cls.STAGE_START.search(line)
        if match:
            return {
                'type': 'stage_start',
                'name': match.group(1)
            }
        
        # Check for download complete
        match = cls.STAGE_COMPLETE.search(line)
        if match:
            return {
                'type': 'stage_complete',
                'name': match.group(1)
            }
        
        # Check for progress bar
        match = cls.PROGRESS_PATTERN.search(line)
        if match:
            stage = match.group(1)  # Images, Model, or Cache
            percent = int(match.group(2))
            downloaded = match.group(3)
            total = match.group(4)
            elapsed = match.group(5)
            remaining = match.group(6)
            speed = match.group(7)
            
            return {
                'type': 'progress',
                'stage': stage.lower(),
                'percent': percent,
                'downloaded': downloaded,
                'total': total,
                'elapsed': elapsed,
                'remaining': remaining,
                'speed': speed
            }
        
        return None


class ResourceInstaller:
    """Installer for deploying resources to remote instances"""
    
    def __init__(self, ssh_key: str = '/root/.ssh/id_ed25519', progress_callback: Optional[Callable] = None):
        """
        Initialize resource installer
        
        Args:
            ssh_key: Path to SSH private key
            progress_callback: Optional callback for progress updates
        """
        self.ssh_key = ssh_key
        self.progress_callback = progress_callback
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
                
                # Parse and report progress
                if self.progress_callback:
                    progress_data = ProgressParser.parse_line(line_stripped)
                    if progress_data:
                        progress_data['resource'] = resource_name
                        self.progress_callback(progress_data)
            
            return_code = process.wait(timeout=3600)  # 1 hour timeout
            
            success = return_code == 0
            
            if success:
                logger.info(f"Successfully installed resource '{resource_name}'")
            else:
                logger.error(f"Failed to install resource '{resource_name}' (exit code {return_code})")
                
                # Check for host key verification error
                stderr_text = '\n'.join(output_lines)
                if _is_host_key_error(stderr_text, return_code):
                    logger.warning(f"Host key verification needed for {ssh_host}:{ssh_port}")
                    return {
                        'success': False,
                        'output': output_lines,
                        'return_code': return_code,
                        'resource': resource_name,
                        'host_verification_needed': True,
                        'host': ssh_host,
                        'port': ssh_port
                    }
            
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
