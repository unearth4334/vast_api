"""
VastAI utility functions for API interfacing and connection management
"""

import os
import re
import logging

logger = logging.getLogger(__name__)

# ------------------------------- SSH parsing -------------------------------

def parse_ssh_connection(ssh_connection):
    """
    Parse SSH connection string to extract host, port, and user.

    Supports typical forms like:
      - "ssh -p 2838 root@104.189.178.116 -L 8080:localhost:8080"
      - "ssh root@myhost" (defaults port=22)

    Returns:
        dict | None: {'user': str, 'host': str, 'port': int} or None if invalid
    """
    try:
        if not ssh_connection:
            return None

        # Extract -p <port>
        port_match = re.search(r'(?:^|\s)-p\s+(\d+)\b', ssh_connection)
        port = int(port_match.group(1)) if port_match else 22

        # Extract user@host (IPv4 or hostname)
        # Accept usernames with common chars; host can be IP or hostname
        user_host_match = re.search(r'([A-Za-z0-9._-]+)@([0-9.]+|[A-Za-z0-9._-]+)', ssh_connection)
        if not user_host_match:
            return None

        user = user_host_match.group(1)
        host = user_host_match.group(2)

        return {"user": user, "host": host, "port": port}

    except Exception as e:
        logger.error(f"Error parsing SSH connection string: {e}")
        return None


def parse_host_port(ssh_connection):
    """
    Parse SSH connection string into (host, port) for sync operations.

    Accepts:
      - Full SSH command (e.g., "ssh -p 2838 root@104.189.178.116 -L ...")
      - "host:port"
    Returns:
      tuple[str, str]
    Raises:
      ValueError on invalid formats
    """
    if not ssh_connection:
        raise ValueError("SSH connection string cannot be empty")

    if ssh_connection.strip().startswith('ssh '):
        result = parse_ssh_connection(ssh_connection)
        if not result:
            raise ValueError("Invalid SSH command format")
        return result['host'], str(result['port'])

    # Simple "host:port"
    if ':' not in ssh_connection:
        raise ValueError("Invalid SSH connection format. Expected 'host:port' or full SSH command")

    parts = ssh_connection.split(':')
    if len(parts) != 2:
        raise ValueError("Invalid SSH connection format. Expected 'host:port'")

    host, port = parts
    host = host.strip()
    
    # Strip username if present (e.g., "root@79.116.177.128" -> "79.116.177.128")
    if '@' in host:
        host = host.split('@', 1)[1]
    
    if not host:
        raise ValueError("Host cannot be empty")

    try:
        port_int = int(port)
        if port_int < 1 or port_int > 65535:
            raise ValueError("Port must be between 1 and 65535")
    except ValueError:
        raise ValueError("Port must be a valid integer")

    return host, str(port_int)


# ---------------------------- API key extraction ----------------------------

# Heuristic: VastAI API keys are long hex tokens (40+ chars). Adjust if needed.
_API_KEY_HEX = re.compile(r"\b[a-f0-9]{40,}\b", re.I)

def _extract_api_key(text: str, vendor: str = "vastai") -> str | None:
    """
    Extract a single API key from the given text.

    Supports:
      - Plain token on a line
      - YAML:  vastai: <key>  /  api_key: <key>
      - .env:  VASTAI_API_KEY=<key> / API_KEY=<key>
      - First long hex token found anywhere
    Ignores commented lines (starting with '#').
    """
    if not text:
        return None

    # Try YAML parse if PyYAML is available
    try:
        import yaml  # type: ignore
    except Exception:
        yaml = None

    if yaml is not None:
        try:
            data = yaml.safe_load(text)
            if isinstance(data, dict):
                for k in (vendor, "vastai", "VASTAI", "api_key", "API_KEY", "key", "Key"):
                    v = data.get(k)
                    if isinstance(v, str) and v.strip():
                        return v.strip()
        except Exception:
            pass  # fall through

    # Normalize lines: strip whitespace and skip comments/empties
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)

    # k=v or k: v formats (.env / yamlish)
    KEY_NAMES = {
        "vastai", "vastai_api_key", "vast_api_key",
        "api_key", "apikey", "key"
    }
    for line in lines:
        if "=" in line:
            k, v = line.split("=", 1)
            if k.strip().lower() in KEY_NAMES:
                val = v.strip().strip('"').strip("'")
                if val:
                    return val
        if ":" in line:
            k, v = line.split(":", 1)
            if k.strip().lower() in KEY_NAMES or k.strip().lower() == vendor:
                val = v.strip().strip('"').strip("'")
                if val:
                    return val

    # First long hex token anywhere
    m = _API_KEY_HEX.search(text)
    if m:
        return m.group(0).strip()

    # Fallback: first non-assignment, non-comment line
    for line in lines:
        if ("=" not in line) and (":" not in line):
            return line.strip()

    return None


def read_api_key_from_file(api_key_path: str = "api_key.txt", vendor: str = "vastai") -> str | None:
    """
    Read VastAI API key from file and return ONLY the key string.

    Search order:
      - api_key_path (exact)
      - ./api_key.txt
      - ./config/api_key.txt

    Returns:
      str | None  -> the key if found/parsed, otherwise None.
    """
    candidates = []
    if api_key_path:
        candidates.append(api_key_path)
    # If caller used default, also try common locations
    if api_key_path == "api_key.txt":
        cwd = os.getcwd()
        candidates.extend([
            os.path.join(cwd, "api_key.txt"),
            os.path.join(cwd, "config", "api_key.txt"),
        ])

    seen = set()
    for p in candidates:
        if not p or p in seen:
            continue
        seen.add(p)
        try:
            if not os.path.exists(p):
                continue
            with open(p, "r", encoding="utf-8") as f:
                text = f.read()
            key = _extract_api_key(text, vendor=vendor)
            if key:
                # Final sanitation: reject multi-line, obvious labels, etc.
                compact = key.strip()
                if any(ch in compact for ch in ("\n", " ", "\t", ":", "=")):
                    m = _API_KEY_HEX.search(compact)
                    compact = m.group(0) if m else ""
                if compact:
                    return compact
        except Exception as e:
            logger.error(f"Error reading API key file '{p}': {e}")

    return None


# ------------------------------- Misc helpers -------------------------------

def validate_ssh_host_format(host):
    """
    Validate SSH host format (basic validation).

    Returns:
        bool: True if valid format, False otherwise
    """
    if not host or not host.strip():
        return False

    host = host.strip()

    # Basic IPv4 pattern
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ip_pattern, host):
        # Check octets 0-255
        try:
            return all(0 <= int(o) <= 255 for o in host.split('.'))
        except ValueError:
            return False

    # Basic hostname pattern
    hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$'
    return bool(re.match(hostname_pattern, host))


def get_ssh_port(instance):
    """
    Extract SSH port from VastAI instance data.
    
    Prefers the host-side port from the ports mapping (instance["ports"]["22/tcp"][0]["HostPort"])
    as this represents the externally mapped port. Falls back to instance["ssh_port"] if the
    ports mapping is not available or malformed.
    
    Args:
        instance (dict): Instance data from VastAI API
        
    Returns:
        int or str: SSH port number, or None if not found
    """
    if not instance:
        return None
    
    # Try to get port from ports mapping (preferred method)
    try:
        ports = instance.get('ports', {})
        if isinstance(ports, dict) and '22/tcp' in ports:
            tcp_ports = ports['22/tcp']
            if isinstance(tcp_ports, list) and len(tcp_ports) > 0:
                host_port = tcp_ports[0].get('HostPort')
                if host_port:
                    return host_port
    except (TypeError, KeyError, IndexError, AttributeError):
        # Ignore errors and fall back to ssh_port
        pass
    
    # Fallback to ssh_port field
    ssh_port = instance.get('ssh_port')
    if ssh_port:
        return ssh_port
    
    return None


def format_instance_info(instance):
    """
    Format VastAI instance information for display.
    """
    if not instance:
        return {}

    return {
        'id': instance.get('id'),
        'gpu': instance.get('gpu_name'),
        'host': instance.get('ssh_host'),
        'port': get_ssh_port(instance),
        'status': instance.get('actual_status'),
        'location': instance.get('geolocation')
    }