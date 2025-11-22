"""
Unit tests for SSH Tunnel utilities
"""

import unittest
from unittest.mock import patch, MagicMock
from app.sync.ssh_tunnel import SSHTunnel, SSHTunnelPool


class TestSSHTunnel(unittest.TestCase):
    """Test SSH tunnel functionality."""
    
    def test_parse_ssh_connection(self):
        """Test parsing SSH connection string."""
        # Standard format
        host, port, user = SSHTunnel.parse_ssh_connection("ssh -p 12345 root@example.com")
        self.assertEqual(host, "example.com")
        self.assertEqual(port, "12345")
        self.assertEqual(user, "root")
        
        # Default port
        host, port, user = SSHTunnel.parse_ssh_connection("user@host.com")
        self.assertEqual(host, "host.com")
        self.assertEqual(port, "22")
        self.assertEqual(user, "user")
    
    def test_find_free_port(self):
        """Test finding a free port."""
        port = SSHTunnel._find_free_port()
        self.assertIsInstance(port, int)
        self.assertGreater(port, 0)
        self.assertLess(port, 65536)
    
    def test_create_tunnel(self):
        """Test creating a tunnel instance."""
        tunnel = SSHTunnel("ssh -p 12345 root@example.com", 18188)
        
        self.assertEqual(tunnel.remote_port, 18188)
        self.assertIsInstance(tunnel.local_port, int)
        self.assertFalse(tunnel._is_running)
    
    @patch('socket.socket')
    def test_is_port_open(self, mock_socket):
        """Test port open check."""
        # Port is open
        mock_socket_instance = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        
        result = SSHTunnel._is_port_open("localhost", 8080)
        mock_socket_instance.connect.assert_called_once_with(("localhost", 8080))


class TestSSHTunnelPool(unittest.TestCase):
    """Test SSH tunnel pool functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.pool = SSHTunnelPool()
    
    def tearDown(self):
        """Clean up after tests."""
        self.pool.close_all()
    
    def test_pool_creation(self):
        """Test creating a tunnel pool."""
        self.assertIsInstance(self.pool._tunnels, dict)
        self.assertEqual(len(self.pool._tunnels), 0)
    
    @patch.object(SSHTunnel, 'start', return_value=True)
    @patch.object(SSHTunnel, 'is_alive', return_value=True)
    def test_get_tunnel(self, mock_is_alive, mock_start):
        """Test getting a tunnel from pool."""
        tunnel = self.pool.get_tunnel("ssh test", 18188)
        
        self.assertIsNotNone(tunnel)
        self.assertEqual(len(self.pool._tunnels), 1)
        mock_start.assert_called_once()
    
    @patch.object(SSHTunnel, 'start', return_value=True)
    @patch.object(SSHTunnel, 'is_alive', return_value=True)
    def test_reuse_tunnel(self, mock_is_alive, mock_start):
        """Test reusing an existing tunnel."""
        # Get tunnel first time
        tunnel1 = self.pool.get_tunnel("ssh test", 18188)
        
        # Get same tunnel again
        tunnel2 = self.pool.get_tunnel("ssh test", 18188)
        
        self.assertIs(tunnel1, tunnel2)
        self.assertEqual(len(self.pool._tunnels), 1)
        # Start should only be called once
        self.assertEqual(mock_start.call_count, 1)
    
    @patch.object(SSHTunnel, 'start', return_value=True)
    @patch.object(SSHTunnel, 'is_alive', return_value=True)
    @patch.object(SSHTunnel, 'stop')
    def test_close_tunnel(self, mock_stop, mock_is_alive, mock_start):
        """Test closing a specific tunnel."""
        self.pool.get_tunnel("ssh test", 18188)
        self.pool.close_tunnel("ssh test", 18188)
        
        self.assertEqual(len(self.pool._tunnels), 0)
        mock_stop.assert_called_once()
    
    @patch.object(SSHTunnel, 'start', return_value=True)
    @patch.object(SSHTunnel, 'is_alive', return_value=True)
    @patch.object(SSHTunnel, 'stop')
    def test_close_all_tunnels(self, mock_stop, mock_is_alive, mock_start):
        """Test closing all tunnels."""
        self.pool.get_tunnel("ssh test1", 18188)
        self.pool.get_tunnel("ssh test2", 18188)
        
        self.assertEqual(len(self.pool._tunnels), 2)
        
        self.pool.close_all()
        
        self.assertEqual(len(self.pool._tunnels), 0)
        self.assertEqual(mock_stop.call_count, 2)


if __name__ == '__main__':
    unittest.main()
