#!/usr/bin/env python3
"""
Test the VastAI API module
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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


class TestVastAIAPI(unittest.TestCase):
    """Test the VastAI API module functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_api_key = "test_api_key_123"
        self.test_instance_id = "12345"
        self.test_offer_id = "67890"
        
    def test_create_headers(self):
        """Test header creation"""
        headers = create_headers(self.test_api_key)
        
        self.assertIsInstance(headers, dict)
        self.assertEqual(headers['Accept'], 'application/json')
        self.assertEqual(headers['Content-Type'], 'application/json')
        self.assertEqual(headers['Authorization'], f'Bearer {self.test_api_key}')
    
    @patch('app.utils.vastai_api.requests.put')
    def test_query_offers_success(self, mock_put):
        """Test successful offers query"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"offers": [{"id": 1, "gpu_name": "RTX 4090"}]}
        mock_put.return_value = mock_response
        
        result = query_offers(self.test_api_key, gpu_ram=8, sort="dph_total")
        
        # Verify request was made correctly
        expected_body = {
            "select_cols": ["*"],
            "q": {
                "verified": {"eq": True},
                "rentable": {"eq": True},
                "external": {"eq": False},
                "rented": {"eq": False},
                "order": [["dph_total", "asc"]],
                "type": "on-demand",
                "limit": 100,
                "gpu_ram": {"gte": 8192}  # 8 GB * 1024 MB/GB
            }
        }
        
        mock_put.assert_called_once_with(
            f"{VAST_API_BASE_URL}/search/asks/",
            headers={'Accept': 'application/json', 'Content-Type': 'application/json', 'Authorization': f'Bearer {self.test_api_key}'},
            json=expected_body
        )
        
        # Verify response
        self.assertEqual(result, {"offers": [{"id": 1, "gpu_name": "RTX 4090"}]})
    
    @patch('app.utils.vastai_api.requests.put')
    def test_query_offers_failure(self, mock_put):
        """Test offers query failure"""
        # Mock failed response
        import requests
        mock_put.side_effect = requests.RequestException("Network error")
        
        with self.assertRaises(VastAIAPIError):
            query_offers(self.test_api_key)
    
    @patch('app.utils.vastai_api.requests.put')
    def test_query_offers_custom_parameters(self, mock_put):
        """Test offers query with custom parameters"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"offers": []}
        mock_put.return_value = mock_response
        
        # Test with custom parameters
        query_offers(
            self.test_api_key, 
            gpu_ram=16, 
            sort="score", 
            limit=50,
            verified=False,
            external=True
        )
        
        # Verify request was made with custom parameters
        expected_body = {
            "select_cols": ["*"],
            "q": {
                "verified": {"eq": False},
                "rentable": {"eq": True},
                "external": {"eq": True},
                "rented": {"eq": False},
                "order": [["score", "asc"]],
                "type": "on-demand",
                "limit": 50,
                "gpu_ram": {"gte": 16384}  # 16 GB * 1024 MB/GB
            }
        }
        
        mock_put.assert_called_once_with(
            f"{VAST_API_BASE_URL}/search/asks/",
            headers={'Accept': 'application/json', 'Content-Type': 'application/json', 'Authorization': f'Bearer {self.test_api_key}'},
            json=expected_body
        )
    
    @patch('app.utils.vastai_api.requests.put')
    def test_create_instance_success(self, mock_put):
        """Test successful instance creation"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "new_contract": self.test_instance_id}
        mock_put.return_value = mock_response
        
        result = create_instance(
            self.test_api_key,
            self.test_offer_id,
            "template_hash_123",
            "/workspace",
            disk_size_gb=50
        )
        
        # Verify request was made correctly
        mock_put.assert_called_once()
        call_args = mock_put.call_args
        
        # Check URL
        self.assertEqual(call_args[1]['headers']['Authorization'], f'Bearer {self.test_api_key}')
        
        # Check payload
        payload_data = json.loads(call_args[1]['data'])
        self.assertEqual(payload_data['template_hash_id'], "template_hash_123")
        self.assertEqual(payload_data['disk'], 50)
        self.assertEqual(payload_data['target_state'], "running")
        
        # Verify response
        self.assertEqual(result, {"success": True, "new_contract": self.test_instance_id})
    
    @patch('app.utils.vastai_api.requests.put')
    def test_create_instance_failure(self, mock_put):
        """Test instance creation failure"""
        # Mock failed response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Invalid offer"}
        mock_response.text = '{"error": "Invalid offer"}'
        mock_put.return_value = mock_response
        
        with self.assertRaises(VastAIAPIError) as context:
            create_instance(self.test_api_key, self.test_offer_id, "template_hash_123", "/workspace")
        
        self.assertIn("Invalid offer", str(context.exception))
    
    @patch('app.utils.vastai_api.requests.get')
    def test_show_instance_success(self, mock_get):
        """Test successful instance details retrieval"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "instances": {
                "id": self.test_instance_id,
                "cur_state": "running",
                "gpu_name": "RTX 4090"
            }
        }
        mock_get.return_value = mock_response
        
        result = show_instance(self.test_api_key, self.test_instance_id)
        
        # Verify request
        mock_get.assert_called_once_with(
            f"{VAST_API_BASE_URL}/instances/{self.test_instance_id}/",
            headers=create_headers(self.test_api_key)
        )
        
        # Verify response
        self.assertIn("instances", result)
        self.assertEqual(result["instances"]["id"], self.test_instance_id)
    
    @patch('app.utils.vastai_api.requests.delete')
    def test_destroy_instance_success(self, mock_delete):
        """Test successful instance destruction"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"success": True}
        mock_delete.return_value = mock_response
        
        result = destroy_instance(self.test_api_key, self.test_instance_id)
        
        # Verify request
        mock_delete.assert_called_once_with(
            f"{VAST_API_BASE_URL}/instances/{self.test_instance_id}/",
            headers=create_headers(self.test_api_key)
        )
        
        # Verify response
        self.assertEqual(result, {"success": True})
    
    @patch('app.utils.vastai_api.requests.get')
    def test_list_instances_success(self, mock_get):
        """Test successful instances listing"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "instances": [
                {"id": "123", "cur_state": "running"},
                {"id": "456", "cur_state": "stopped"}
            ]
        }
        mock_get.return_value = mock_response
        
        result = list_instances(self.test_api_key)
        
        # Verify request
        mock_get.assert_called_once_with(
            f"{VAST_API_BASE_URL}/instances/",
            headers=create_headers(self.test_api_key)
        )
        
        # Verify response
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "123")
        self.assertEqual(result[1]["id"], "456")
    
    @patch('app.utils.vastai_api.list_instances')
    def test_get_running_instance_found(self, mock_list_instances):
        """Test finding a running instance"""
        # Mock instances list with one running
        mock_list_instances.return_value = [
            {"id": "123", "cur_state": "stopped"},
            {"id": "456", "cur_state": "running"},
            {"id": "789", "cur_state": "loading"}
        ]
        
        result = get_running_instance(self.test_api_key)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "456")
        self.assertEqual(result["cur_state"], "running")
    
    @patch('app.utils.vastai_api.list_instances')
    def test_get_running_instance_not_found(self, mock_list_instances):
        """Test when no running instance exists"""
        # Mock instances list with no running instances
        mock_list_instances.return_value = [
            {"id": "123", "cur_state": "stopped"},
            {"id": "456", "cur_state": "loading"}
        ]
        
        result = get_running_instance(self.test_api_key)
        
        self.assertIsNone(result)
    
    def test_parse_instance_details_direct(self):
        """Test parsing instance details from direct instance data"""
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
    
    def test_parse_instance_details_wrapped(self):
        """Test parsing instance details from wrapped API response"""
        wrapped_data = {
            "instances": {
                "id": "12345",
                "cur_state": "running",
                "gpu_name": "RTX 4090",
                "gpu_ram": 12288,  # 12GB in MB
            }
        }
        
        result = parse_instance_details(wrapped_data)
        
        self.assertEqual(result["Instance ID"], "12345")
        self.assertEqual(result["Status"], "running")
        self.assertEqual(result["GPU"], "RTX 4090")
        self.assertEqual(result["GPU RAM (GB)"], 12.0)
    
    def test_parse_instance_details_empty(self):
        """Test parsing empty instance details"""
        result = parse_instance_details({})
        self.assertEqual(result, {})
        
        result = parse_instance_details(None)
        self.assertEqual(result, {})


if __name__ == '__main__':
    unittest.main()