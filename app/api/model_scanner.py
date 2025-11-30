"""
Model Scanner for discovering models on remote SSH instances.
Supports high-low noise pair models (WAN 2.2 style) and single models.
"""

import os
import re
import subprocess
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class HighLowPairModel:
    """Represents a high-low noise pair model (e.g., WAN 2.2 14B)"""
    display_name: str
    high_noise_path: str
    low_noise_path: str
    base_path: str
    size: int = 0


@dataclass
class SingleModel:
    """Represents a single model file"""
    display_name: str
    path: str
    size: int = 0
    model_type: str = ""


class ModelScanner:
    """
    Scans remote SSH instances for available models.
    Supports both high-low noise pair models and single models.
    """
    
    def __init__(self, ssh_connection: str, config: dict):
        """
        Initialize the model scanner.
        
        Args:
            ssh_connection: SSH connection string (e.g., 'ssh -p 2838 root@104.189.178.116')
            config: Model discovery configuration from config.yaml
        """
        self.ssh_connection = ssh_connection
        self.config = config
        self.ssh_host, self.ssh_port = self._parse_ssh_connection(ssh_connection)
        
    def _parse_ssh_connection(self, connection: str) -> Tuple[str, int]:
        """
        Extract host and port from SSH connection string.
        
        Args:
            connection: SSH connection string
            
        Returns:
            Tuple of (host, port)
        """
        # Parse: ssh -p 2838 root@104.189.178.116
        port_match = re.search(r'-p\s+(\d+)', connection)
        port = int(port_match.group(1)) if port_match else 22
        
        host_match = re.search(r'root@([\d\.]+)', connection)
        host = host_match.group(1) if host_match else None
        
        if not host:
            raise ValueError(f"Invalid SSH connection string: {connection}")
        
        return host, port
    
    def _run_ssh_command(self, command: str, timeout: int = 30) -> str:
        """
        Execute a command on the remote host via SSH.
        
        Args:
            command: Shell command to execute
            timeout: Command timeout in seconds
            
        Returns:
            Command stdout
        """
        # Build SSH command
        ssh_cmd = [
            'ssh',
            '-p', str(self.ssh_port),
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=accept-new',
            '-o', 'BatchMode=yes',
            f'root@{self.ssh_host}',
            command
        ]
        
        logger.debug(f"Running SSH command: {' '.join(ssh_cmd)}")
        
        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                logger.warning(f"SSH command failed with code {result.returncode}: {result.stderr}")
                return ""
            
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.error(f"SSH command timed out after {timeout}s")
            return ""
        except Exception as e:
            logger.error(f"SSH command error: {e}")
            return ""
    
    def scan_high_low_pairs(
        self,
        base_path: str,
        pattern_config: Optional[dict] = None
    ) -> List[Dict]:
        """
        Scan for high/low noise model pairs on the remote instance.
        
        Args:
            base_path: Base path to scan (e.g., 'models/diffusion_models')
            pattern_config: Pattern configuration for matching pairs
            
        Returns:
            List of model pair dictionaries
        """
        if not pattern_config:
            return []
        
        high_suffix = pattern_config.get('high_suffix', '')
        low_suffix = pattern_config.get('low_suffix', '')
        extract_regex = pattern_config.get('extract_name_regex', '')
        
        max_depth = self.config.get('max_depth', 3)
        extensions = self.config.get('extensions', ['.safetensors', '.ckpt', '.pth'])
        
        # Build find command to get all matching files
        ext_conditions = ' -o '.join([f'-name "*{ext}"' for ext in extensions])
        find_cmd = f'''
            find "$UI_HOME/{base_path}" -maxdepth {max_depth} -type f \
            \\( {ext_conditions} \\) \
            -printf "%P|%s\\n" 2>/dev/null || true
        '''
        
        output = self._run_ssh_command(find_cmd)
        if not output:
            logger.warning(f"No files found in {base_path}")
            return []
        
        # Parse file list
        files = []
        for line in output.strip().split('\n'):
            if '|' in line:
                parts = line.split('|')
                if len(parts) == 2:
                    files.append((parts[0], int(parts[1]) if parts[1].isdigit() else 0))
        
        # Match pairs
        pairs = self._match_high_low_pairs(files, extract_regex, high_suffix, low_suffix)
        
        # Format for frontend
        models = []
        for base_name, high_file, low_file in pairs:
            models.append({
                'displayName': self._format_display_name(base_name),
                'highNoisePath': high_file[0],
                'lowNoisePath': low_file[0],
                'basePath': base_path,
                'size': high_file[1] + low_file[1]
            })
        
        logger.info(f"Found {len(models)} high-low pair model(s) in {base_path}")
        return models
    
    def _match_high_low_pairs(
        self,
        files: List[Tuple[str, int]],
        extract_regex: str,
        high_suffix: str,
        low_suffix: str
    ) -> List[Tuple[str, Tuple[str, int], Tuple[str, int]]]:
        """
        Match high and low noise files into pairs.
        
        Args:
            files: List of (filepath, size) tuples
            extract_regex: Regex to extract base name
            high_suffix: Suffix for high noise files
            low_suffix: Suffix for low noise files
            
        Returns:
            List of (base_name, high_file, low_file) tuples
        """
        high_files = {}
        low_files = {}
        
        for filepath, size in files:
            # Get just the filename for matching
            filename = os.path.basename(filepath)
            
            if extract_regex:
                match = re.search(extract_regex, filename)
                if match:
                    base_name = match.group(1)
                else:
                    continue
            else:
                base_name = filename
            
            if high_suffix and filename.endswith(high_suffix):
                high_files[base_name] = (filepath, size)
            elif low_suffix and filename.endswith(low_suffix):
                low_files[base_name] = (filepath, size)
        
        # Create pairs
        pairs = []
        for base_name in high_files:
            if base_name in low_files:
                pairs.append((
                    base_name,
                    high_files[base_name],
                    low_files[base_name]
                ))
        
        return pairs
    
    def scan_single_models(self, base_path: str, model_type: str = "") -> List[Dict]:
        """
        Scan for individual model files on the remote instance.
        
        Args:
            base_path: Base path to scan (e.g., 'models/vae')
            model_type: Type of model (for categorization)
            
        Returns:
            List of model dictionaries
        """
        max_depth = self.config.get('max_depth', 3)
        extensions = self.config.get('extensions', ['.safetensors', '.ckpt', '.pth'])
        
        # Build find command
        ext_conditions = ' -o '.join([f'-name "*{ext}"' for ext in extensions])
        find_cmd = f'''
            find "$UI_HOME/{base_path}" -maxdepth {max_depth} -type f \
            \\( {ext_conditions} \\) \
            -printf "%P|%s\\n" 2>/dev/null || true
        '''
        
        output = self._run_ssh_command(find_cmd)
        if not output:
            logger.warning(f"No files found in {base_path}")
            return []
        
        # Parse and format results
        models = []
        for line in output.strip().split('\n'):
            if '|' in line:
                parts = line.split('|')
                if len(parts) == 2:
                    filepath = parts[0]
                    size = int(parts[1]) if parts[1].isdigit() else 0
                    
                    models.append({
                        'displayName': os.path.basename(filepath),
                        'path': filepath,
                        'size': size,
                        'type': model_type or os.path.splitext(filepath)[1]
                    })
        
        # Sort by display name
        models.sort(key=lambda x: x['displayName'])
        
        logger.info(f"Found {len(models)} single model(s) in {base_path}")
        return models
    
    def _format_display_name(self, base_name: str) -> str:
        """
        Convert a base filename to a friendly display name.
        
        Args:
            base_name: Raw filename base (e.g., 'wan2.2_i2v')
            
        Returns:
            Formatted display name (e.g., 'Wan 2.2 I2V')
        """
        # Replace underscores with spaces and title case
        name = base_name.replace('_', ' ').title()
        # Fix version numbers (e.g., "2.2" not "2. 2")
        name = re.sub(r'(\d+)\.\s*(\d+)', r'\1.\2', name)
        # Fix common abbreviations
        name = re.sub(r'\bI2v\b', 'I2V', name)
        name = re.sub(r'\bT2v\b', 'T2V', name)
        name = re.sub(r'\bT2i\b', 'T2I', name)
        name = re.sub(r'\bFp16\b', 'FP16', name)
        name = re.sub(r'\bFp32\b', 'FP32', name)
        return name


def get_model_discovery_config() -> dict:
    """
    Load model discovery configuration from config.yaml.
    
    Returns:
        Model discovery configuration dictionary
    """
    try:
        import yaml
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'config.yaml'
        )
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return config.get('model_discovery', {
            'base_paths': {
                'diffusion_models': 'models/diffusion_models',
                'loras': 'models/loras',
                'text_encoders': 'models/text_encoders',
                'vae': 'models/vae',
                'upscale_models': 'models/upscale_models'
            },
            'extensions': ['.safetensors', '.ckpt', '.pth'],
            'max_depth': 3,
            'cache_ttl': 300
        })
    except Exception as e:
        logger.error(f"Error loading model discovery config: {e}")
        return {}
