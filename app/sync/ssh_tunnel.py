"""
SSH Tunneling Utilities
Provides SSH tunnel management for accessing ComfyUI API on remote instances.
"""

import logging
import subprocess
import time
import socket
import threading
from typing import Optional, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class SSHTunnel:
    """Manages an SSH tunnel for port forwarding."""
    
    def __init__(self, ssh_connection: str, remote_port: int, local_port: Optional[int] = None):
        """
        Initialize SSH tunnel.
        
        Args:
            ssh_connection: SSH connection string (e.g., "ssh -p 40738 root@198.53.64.194")
            remote_port: Remote port to forward (e.g., 18188 for ComfyUI)
            local_port: Local port to bind to (auto-assigned if None)
        """
        self.ssh_connection = ssh_connection
        self.remote_port = remote_port
        self.local_port = local_port or self._find_free_port()
        self._process: Optional[subprocess.Popen] = None
        self._is_running = False
        
        logger.info(f"SSHTunnel initialized: localhost:{self.local_port} -> remote:{self.remote_port}")
    
    @staticmethod
    def _find_free_port() -> int:
        """Find an available local port."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    @staticmethod
    def parse_ssh_connection(ssh_connection: str) -> Tuple[str, str, str]:
        """
        Parse SSH connection string.
        
        Args:
            ssh_connection: SSH connection string
            
        Returns:
            Tuple of (host, port, user)
        """
        import re
        
        # Extract port
        port_match = re.search(r'-p\s+(\d+)', ssh_connection)
        port = port_match.group(1) if port_match else '22'
        
        # Extract user@host
        host_match = re.search(r'(\w+)@([\w\.-]+)', ssh_connection)
        if not host_match:
            raise ValueError(f"Invalid SSH connection string: {ssh_connection}")
        
        user = host_match.group(1)
        host = host_match.group(2)
        
        return host, port, user
    
    def start(self, timeout: float = 10.0) -> bool:
        """
        Start the SSH tunnel.
        
        Args:
            timeout: Seconds to wait for tunnel to establish
            
        Returns:
            True if tunnel started successfully
        """
        if self._is_running:
            logger.warning("SSH tunnel already running")
            return True
        
        try:
            # Parse SSH connection
            host, port, user = self.parse_ssh_connection(self.ssh_connection)
            
            # Build SSH command for port forwarding
            # -L local_port:localhost:remote_port
            # -N: no remote command
            # -f: go to background (we'll manage the process ourselves)
            # -o ExitOnForwardFailure=yes: exit if port forwarding fails
            # -o StrictHostKeyChecking=no: don't prompt for host key (use with caution)
            cmd = [
                'ssh',
                '-p', port,
                '-L', f'{self.local_port}:localhost:{self.remote_port}',
                '-N',
                '-o', 'ExitOnForwardFailure=yes',
                '-o', 'ServerAliveInterval=60',
                '-o', 'ServerAliveCountMax=3',
                f'{user}@{host}'
            ]
            
            logger.info(f"Starting SSH tunnel: {' '.join(cmd)}")
            
            # Start SSH process
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE
            )
            
            # Wait for tunnel to establish
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Check if process is still running
                if self._process.poll() is not None:
                    stderr = self._process.stderr.read().decode('utf-8') if self._process.stderr else ''
                    logger.error(f"SSH tunnel process exited: {stderr}")
                    return False
                
                # Check if port is listening
                if self._is_port_open('localhost', self.local_port):
                    logger.info(f"SSH tunnel established on localhost:{self.local_port}")
                    self._is_running = True
                    return True
                
                time.sleep(0.5)
            
            # Timeout
            logger.error(f"SSH tunnel failed to establish within {timeout} seconds")
            self.stop()
            return False
            
        except Exception as e:
            logger.error(f"Failed to start SSH tunnel: {e}")
            self.stop()
            return False
    
    def stop(self):
        """Stop the SSH tunnel."""
        if self._process:
            try:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait()
                logger.info("SSH tunnel stopped")
            except Exception as e:
                logger.error(f"Error stopping SSH tunnel: {e}")
            finally:
                self._process = None
                self._is_running = False
    
    def is_alive(self) -> bool:
        """Check if tunnel is alive."""
        if not self._is_running or not self._process:
            return False
        
        # Check process
        if self._process.poll() is not None:
            logger.warning("SSH tunnel process has exited")
            self._is_running = False
            return False
        
        # Check port
        if not self._is_port_open('localhost', self.local_port):
            logger.warning("SSH tunnel port is not open")
            self._is_running = False
            return False
        
        return True
    
    @staticmethod
    def _is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
        """Check if a port is open."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect((host, port))
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


@contextmanager
def ssh_tunnel_context(ssh_connection: str, remote_port: int, local_port: Optional[int] = None):
    """
    Context manager for SSH tunnel.
    
    Args:
        ssh_connection: SSH connection string
        remote_port: Remote port to forward
        local_port: Local port to bind to (auto-assigned if None)
        
    Yields:
        SSHTunnel instance
        
    Example:
        with ssh_tunnel_context("ssh -p 40738 root@198.53.64.194", 18188) as tunnel:
            # Use tunnel.local_port to access ComfyUI API
            api_url = f"http://localhost:{tunnel.local_port}"
    """
    tunnel = SSHTunnel(ssh_connection, remote_port, local_port)
    try:
        if not tunnel.start():
            raise RuntimeError("Failed to establish SSH tunnel")
        yield tunnel
    finally:
        tunnel.stop()


class SSHTunnelPool:
    """Manages a pool of SSH tunnels for reuse."""
    
    def __init__(self):
        """Initialize tunnel pool."""
        self._tunnels: dict[str, SSHTunnel] = {}
        self._lock = threading.Lock()
    
    def get_tunnel(self, ssh_connection: str, remote_port: int) -> SSHTunnel:
        """
        Get or create an SSH tunnel.
        
        Args:
            ssh_connection: SSH connection string
            remote_port: Remote port to forward
            
        Returns:
            SSHTunnel instance
        """
        key = f"{ssh_connection}:{remote_port}"
        
        with self._lock:
            # Check if tunnel exists and is alive
            if key in self._tunnels:
                tunnel = self._tunnels[key]
                if tunnel.is_alive():
                    logger.debug(f"Reusing existing tunnel: {key}")
                    return tunnel
                else:
                    logger.info(f"Removing dead tunnel: {key}")
                    tunnel.stop()
                    del self._tunnels[key]
            
            # Create new tunnel
            logger.info(f"Creating new tunnel: {key}")
            tunnel = SSHTunnel(ssh_connection, remote_port)
            if tunnel.start():
                self._tunnels[key] = tunnel
                return tunnel
            else:
                raise RuntimeError(f"Failed to create SSH tunnel for {key}")
    
    def release_tunnel(self, ssh_connection: str, remote_port: int):
        """
        Release a tunnel (but keep it alive for reuse).
        
        Args:
            ssh_connection: SSH connection string
            remote_port: Remote port
        """
        # For now, we keep tunnels alive for reuse
        # Could implement reference counting if needed
        pass
    
    def close_tunnel(self, ssh_connection: str, remote_port: int):
        """
        Close and remove a tunnel from the pool.
        
        Args:
            ssh_connection: SSH connection string
            remote_port: Remote port
        """
        key = f"{ssh_connection}:{remote_port}"
        
        with self._lock:
            if key in self._tunnels:
                logger.info(f"Closing tunnel: {key}")
                self._tunnels[key].stop()
                del self._tunnels[key]
    
    def close_all(self):
        """Close all tunnels in the pool."""
        with self._lock:
            logger.info(f"Closing {len(self._tunnels)} tunnels")
            for tunnel in self._tunnels.values():
                tunnel.stop()
            self._tunnels.clear()
    
    def cleanup_dead_tunnels(self):
        """Remove dead tunnels from the pool."""
        with self._lock:
            dead_keys = [k for k, t in self._tunnels.items() if not t.is_alive()]
            for key in dead_keys:
                logger.info(f"Removing dead tunnel: {key}")
                self._tunnels[key].stop()
                del self._tunnels[key]


# Global tunnel pool instance
_tunnel_pool = SSHTunnelPool()


def get_tunnel_pool() -> SSHTunnelPool:
    """Get the global tunnel pool instance."""
    return _tunnel_pool
