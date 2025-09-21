"""
VastAI utility functions for API interfacing and connection management
"""

import os
import re
import logging

logger = logging.getLogger(__name__)


def parse_ssh_connection(ssh_connection):
    """
    Parse SSH connection string to extract host, port, and user.
    
    Args:
        ssh_connection (str): SSH connection string in full SSH command format
        
    Returns:
        dict or None: Dictionary with user, host, port for valid SSH commands, 
                     None for invalid input
    """
    try:
        if not ssh_connection:
            return None
        
        # Handle full SSH command format like "ssh -p 2838 root@104.189.178.116 -L 8080:localhost:8080"
        import re
        
        # Extract port from -p flag
        port_match = re.search(r'-p\s+(\d+)', ssh_connection)
        port = int(port_match.group(1)) if port_match else 22
        
        # Extract user@host
        user_host_match = re.search(r'(\w+)@([0-9.]+|[\w.-]+)', ssh_connection)
        if not user_host_match:
            return None
            
        user = user_host_match.group(1)
        host = user_host_match.group(2)
        
        return {
            'user': user,
            'host': host,
            'port': port
        }
        
    except Exception as e:
        logger.error(f"Error parsing SSH connection string: {str(e)}")
        return None


def parse_host_port(ssh_connection):
    """
    Parse SSH connection string into host and port components for sync operations.
    
    Args:
        ssh_connection (str): SSH connection string in format "host:port" or full SSH command
        
    Returns:
        tuple: (host, port) where port is a string
        
    Raises:
        ValueError: If the connection string format is invalid
    """
    if not ssh_connection:
        raise ValueError("SSH connection string cannot be empty")
    
    # Handle full SSH command format like "ssh -p 2838 root@104.189.178.116 -L 8080:localhost:8080"
    if ssh_connection.startswith('ssh '):
        result = parse_ssh_connection(ssh_connection)
        if not result:
            raise ValueError("Invalid SSH command format")
        return result['host'], str(result['port'])
    else:
        # Handle simple host:port format
        if ':' not in ssh_connection:
            raise ValueError("Invalid SSH connection format. Expected 'host:port' or full SSH command")
        
        parts = ssh_connection.split(':')
        if len(parts) != 2:
            raise ValueError("Invalid SSH connection format. Expected 'host:port'")
        
        host, port = parts
        
        # Validate host (basic validation)
        if not host.strip():
            raise ValueError("Host cannot be empty")
        
        # Validate port
        try:
            port_int = int(port)
            if port_int < 1 or port_int > 65535:
                raise ValueError("Port must be between 1 and 65535")
        except ValueError:
            raise ValueError("Port must be a valid integer")
        
        return host.strip(), port.strip()


def read_api_key_from_file(api_key_path='api_key.txt'):
    """
    Read VastAI API key from file.
    
    Args:
        api_key_path (str): Path to the API key file
        
    Returns:
        str: API key content stripped of whitespace
        
    Raises:
        FileNotFoundError: If the API key file doesn't exist
        Exception: If there's an error reading the file
    """
    if not os.path.exists(api_key_path):
        raise FileNotFoundError(f"VastAI API key file not found: {api_key_path}")
    
    try:
        with open(api_key_path, 'r') as f:
            api_key = f.read().strip()
        
        if not api_key:
            raise ValueError("API key file is empty")
            
        return api_key
        
    except Exception as e:
        logger.error(f"Error reading API key file: {e}")
        raise


def validate_ssh_host_format(host):
    """
    Validate SSH host format (basic validation).
    
    Args:
        host (str): Host address (IP or hostname)
        
    Returns:
        bool: True if valid format, False otherwise
    """
    if not host or not host.strip():
        return False
    
    host = host.strip()
    
    # Basic IP address pattern (not comprehensive but catches obvious errors)
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ip_pattern, host):
        # Check if octets are valid (0-255)
        octets = host.split('.')
        try:
            for octet in octets:
                if int(octet) > 255:
                    return False
            return True
        except ValueError:
            return False
    
    # Basic hostname pattern
    hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$'
    return bool(re.match(hostname_pattern, host))


def format_instance_info(instance):
    """
    Format VastAI instance information for display.
    
    Args:
        instance (dict): Instance data from VastAI API
        
    Returns:
        dict: Formatted instance information
    """
    if not instance:
        return {}
    
    return {
        'id': instance.get('id'),
        'gpu': instance.get('gpu_name'),
        'host': instance.get('ssh_host'),
        'port': instance.get('ssh_port'),
        'status': instance.get('cur_state'),
        'location': instance.get('geolocation')
    }