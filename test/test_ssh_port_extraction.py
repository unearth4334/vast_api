#!/usr/bin/env python3
"""
Test SSH port extraction from VastAI instance data.
"""

import unittest
import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.vastai.vastai_utils import get_ssh_port


class TestSSHPortExtraction(unittest.TestCase):
    """Test the get_ssh_port function"""
    
    def test_ports_mapping_preferred(self):
        """Test that ports mapping is preferred over ssh_port field"""
        instance = {
            "ssh_port": 22,
            "ports": {
                "22/tcp": [
                    {"HostPort": "12345"}
                ]
            }
        }
        
        result = get_ssh_port(instance)
        self.assertEqual(result, "12345")
    
    def test_fallback_to_ssh_port(self):
        """Test fallback to ssh_port when ports mapping is missing"""
        instance = {
            "ssh_port": 2222
        }
        
        result = get_ssh_port(instance)
        self.assertEqual(result, 2222)
    
    def test_only_ports_mapping(self):
        """Test when only ports mapping is present"""
        instance = {
            "ports": {
                "22/tcp": [
                    {"HostPort": "9999"}
                ]
            }
        }
        
        result = get_ssh_port(instance)
        self.assertEqual(result, "9999")
    
    def test_empty_ports_array(self):
        """Test when ports array is empty - should fallback to ssh_port"""
        instance = {
            "ssh_port": 3333,
            "ports": {
                "22/tcp": []
            }
        }
        
        result = get_ssh_port(instance)
        self.assertEqual(result, 3333)
    
    def test_missing_host_port_in_ports(self):
        """Test when HostPort key is missing - should fallback to ssh_port"""
        instance = {
            "ssh_port": 4444,
            "ports": {
                "22/tcp": [
                    {"SomeOtherKey": "value"}
                ]
            }
        }
        
        result = get_ssh_port(instance)
        self.assertEqual(result, 4444)
    
    def test_multiple_port_entries(self):
        """Test when there are multiple port entries - should use first one"""
        instance = {
            "ssh_port": 22,
            "ports": {
                "22/tcp": [
                    {"HostPort": "11111"},
                    {"HostPort": "22222"}
                ]
            }
        }
        
        result = get_ssh_port(instance)
        self.assertEqual(result, "11111")
    
    def test_ports_not_dict(self):
        """Test when ports is not a dict - should fallback to ssh_port"""
        instance = {
            "ssh_port": 5555,
            "ports": "not_a_dict"
        }
        
        result = get_ssh_port(instance)
        self.assertEqual(result, 5555)
    
    def test_ports_tcp_not_list(self):
        """Test when ports["22/tcp"] is not a list - should fallback to ssh_port"""
        instance = {
            "ssh_port": 6666,
            "ports": {
                "22/tcp": "not_a_list"
            }
        }
        
        result = get_ssh_port(instance)
        self.assertEqual(result, 6666)
    
    def test_no_port_data(self):
        """Test when neither ports nor ssh_port is available"""
        instance = {
            "other_field": "value"
        }
        
        result = get_ssh_port(instance)
        self.assertIsNone(result)
    
    def test_empty_instance(self):
        """Test with empty instance dict"""
        instance = {}
        
        result = get_ssh_port(instance)
        self.assertIsNone(result)
    
    def test_none_instance(self):
        """Test with None instance"""
        result = get_ssh_port(None)
        self.assertIsNone(result)
    
    def test_port_value_types(self):
        """Test that both string and int port values are handled"""
        # Test with string port in ports mapping
        instance1 = {
            "ports": {
                "22/tcp": [
                    {"HostPort": "7777"}
                ]
            }
        }
        result1 = get_ssh_port(instance1)
        self.assertEqual(result1, "7777")
        
        # Test with int port in ssh_port
        instance2 = {
            "ssh_port": 8888
        }
        result2 = get_ssh_port(instance2)
        self.assertEqual(result2, 8888)
    
    def test_missing_22_tcp_key(self):
        """Test when ports dict exists but doesn't have 22/tcp key"""
        instance = {
            "ssh_port": 9999,
            "ports": {
                "8080/tcp": [
                    {"HostPort": "8080"}
                ]
            }
        }
        
        result = get_ssh_port(instance)
        self.assertEqual(result, 9999)


if __name__ == '__main__':
    unittest.main()
