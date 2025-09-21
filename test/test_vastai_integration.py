#!/usr/bin/env python3
"""
Integration test to verify VastAI API module can be imported and used
"""

import unittest
import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class TestVastAIIntegration(unittest.TestCase):
    """Test VastAI API module integration"""
    
    def test_api_module_import(self):
        """Test that the VastAI API module can be imported"""
        try:
            from app.utils.vastai_api import (
                VastAIAPIError,
                create_headers,
                query_offers,
                create_instance,
                show_instance,
                destroy_instance,
                list_instances,
                get_running_instance,
                parse_instance_details,
                VAST_API_BASE_URL
            )
            self.assertTrue(True)  # If we got here, import worked
        except ImportError as e:
            self.fail(f"Failed to import VastAI API module: {e}")
    
    def test_vast_manager_import(self):
        """Test that VastManager can still be imported after refactoring"""
        try:
            from app.vastai.vast_manager import VastManager
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import VastManager: {e}")
    
    def test_vast_client_import(self):
        """Test that VastClient can still be imported after refactoring"""
        try:
            from app.vastai.vast_client import VastClient
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import VastClient: {e}")
    
    def test_headers_creation(self):
        """Test header creation functionality"""
        from app.utils.vastai_api import create_headers
        
        api_key = "test_key_123"
        headers = create_headers(api_key)
        
        self.assertIsInstance(headers, dict)
        self.assertIn('Authorization', headers)
        self.assertEqual(headers['Authorization'], f'Bearer {api_key}')
        self.assertEqual(headers['Accept'], 'application/json')
        self.assertEqual(headers['Content-Type'], 'application/json')
    
    def test_parse_instance_details(self):
        """Test instance details parsing"""
        from app.utils.vastai_api import parse_instance_details
        
        # Test with sample instance data
        instance_data = {
            "id": "12345",
            "cur_state": "running",
            "gpu_name": "RTX 4090",
            "gpu_ram": 24576,  # 24GB in MB
            "ssh_host": "example.com",
            "ssh_port": 22
        }
        
        result = parse_instance_details(instance_data)
        
        self.assertEqual(result["Instance ID"], "12345")
        self.assertEqual(result["Status"], "running")
        self.assertEqual(result["GPU"], "RTX 4090")
        self.assertEqual(result["GPU RAM (GB)"], 24.0)
        self.assertEqual(result["SSH Host"], "example.com")
        self.assertEqual(result["SSH Port"], 22)
    
    def test_vast_manager_can_be_instantiated(self):
        """Test that VastManager can be instantiated (without calling init)"""
        from app.vastai.vast_manager import VastManager
        
        # Create instance without calling __init__ to avoid file dependencies
        vm = VastManager.__new__(VastManager)
        self.assertIsInstance(vm, VastManager)
        
        # Verify it has the expected methods
        self.assertTrue(hasattr(vm, 'query_offers'))
        self.assertTrue(hasattr(vm, 'create_instance'))
        self.assertTrue(hasattr(vm, 'show_instance'))
        self.assertTrue(hasattr(vm, 'destroy_instance'))
        self.assertTrue(hasattr(vm, 'list_instances'))
        self.assertTrue(hasattr(vm, 'get_running_instance'))
    
    def test_vast_client_can_be_instantiated(self):
        """Test that VastClient can be instantiated"""
        from app.vastai.vast_client import VastClient
        
        # Create VastClient with dummy API key
        client = VastClient("dummy_key")
        self.assertIsInstance(client, VastClient)
        
        # Verify it has the expected methods
        self.assertTrue(hasattr(client, 'query_offers'))
        self.assertTrue(hasattr(client, 'create_instance'))
        self.assertTrue(hasattr(client, 'show_instance'))
        self.assertTrue(hasattr(client, 'destroy_instance'))
        self.assertTrue(hasattr(client, 'list_instances'))
        
        # Verify it has the API key
        self.assertEqual(client.api_key, "dummy_key")
        self.assertIn('Authorization', client.headers)


if __name__ == '__main__':
    unittest.main()