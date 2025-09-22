"""
Tests for VastAI API logging functionality
"""

import unittest
import os
import tempfile
import shutil
import json
from datetime import datetime
from unittest.mock import patch

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.utils.vastai_logging import (
    log_api_interaction, get_vastai_logs, get_vastai_log_manifest,
    get_log_filename, get_log_filepath, ensure_vastai_log_dir
)


class TestVastAILogging(unittest.TestCase):
    
    def setUp(self):
        """Create a temporary directory for test logs"""
        self.test_media_dir = tempfile.mkdtemp()
        self.test_log_dir = os.path.join(self.test_media_dir, '.vastai_log')
        
        # Patch the VASTAI_LOG_DIR to use our test directory
        self.patcher = patch('app.utils.vastai_logging.VASTAI_LOG_DIR', self.test_log_dir)
        self.patcher.start()
    
    def tearDown(self):
        """Clean up test directories"""
        self.patcher.stop()
        shutil.rmtree(self.test_media_dir, ignore_errors=True)
    
    def test_ensure_vastai_log_dir(self):
        """Test that log directory is created"""
        self.assertTrue(ensure_vastai_log_dir())
        self.assertTrue(os.path.exists(self.test_log_dir))
    
    def test_get_log_filename(self):
        """Test log filename generation"""
        test_date = datetime(2025, 9, 22, 15, 30, 45)
        filename = get_log_filename(test_date)
        self.assertEqual(filename, "api_log_20250922.json")
    
    def test_get_log_filepath(self):
        """Test log filepath generation"""
        test_date = datetime(2025, 9, 22, 15, 30, 45)
        filepath = get_log_filepath(test_date)
        expected = os.path.join(self.test_log_dir, "api_log_20250922.json")
        self.assertEqual(filepath, expected)
    
    def test_log_api_interaction_success(self):
        """Test logging a successful API interaction"""
        log_api_interaction(
            method="GET",
            endpoint="/instances/",
            request_data=None,
            response_data={"instance_count": 2},
            status_code=200,
            duration_ms=123.45
        )
        
        # Check that log file was created
        today = datetime.now()
        log_file = get_log_filepath(today)
        self.assertTrue(os.path.exists(log_file))
        
        # Check log content
        with open(log_file, 'r') as f:
            logs = json.load(f)
        
        self.assertEqual(len(logs), 1)
        log_entry = logs[0]
        self.assertEqual(log_entry['method'], 'GET')
        self.assertEqual(log_entry['endpoint'], '/instances/')
        self.assertEqual(log_entry['status_code'], 200)
        self.assertEqual(log_entry['duration_ms'], 123.45)
        self.assertEqual(log_entry['response']['instance_count'], 2)
        self.assertIsNone(log_entry.get('error'))
    
    def test_log_api_interaction_failure(self):
        """Test logging a failed API interaction"""
        log_api_interaction(
            method="POST",
            endpoint="/asks/123/",
            request_data={"disk": 50},
            response_data={"error": "Insufficient credit"},
            status_code=400,
            error="Failed to create instance",
            duration_ms=67.89
        )
        
        # Check log content
        today = datetime.now()
        log_file = get_log_filepath(today)
        with open(log_file, 'r') as f:
            logs = json.load(f)
        
        log_entry = logs[0]
        self.assertEqual(log_entry['method'], 'POST')
        self.assertEqual(log_entry['status_code'], 400)
        self.assertEqual(log_entry['error'], 'Failed to create instance')
        self.assertEqual(log_entry['request']['disk'], 50)
        self.assertEqual(log_entry['response']['error'], 'Insufficient credit')
    
    def test_api_key_sanitization(self):
        """Test that API keys are properly sanitized in logs"""
        log_api_interaction(
            method="GET",
            endpoint="/bundles",
            request_data={"api_key": "secret123", "gpu_ram": 10},
            response_data={"offers_count": 5},
            status_code=200
        )
        
        # Check that API key was sanitized
        today = datetime.now()
        log_file = get_log_filepath(today)
        with open(log_file, 'r') as f:
            logs = json.load(f)
        
        log_entry = logs[0]
        self.assertEqual(log_entry['request']['api_key'], '***REDACTED***')
        self.assertEqual(log_entry['request']['gpu_ram'], 10)
    
    def test_get_vastai_logs(self):
        """Test retrieving VastAI logs"""
        # Create some test log entries
        log_api_interaction("GET", "/instances/", status_code=200)
        log_api_interaction("POST", "/asks/123/", status_code=400, error="Test error")
        log_api_interaction("DELETE", "/instances/456/", status_code=200)
        
        # Test retrieving logs
        logs = get_vastai_logs(max_lines=2)
        self.assertEqual(len(logs), 2)
        
        # Logs should be in reverse chronological order (newest first)
        self.assertEqual(logs[0]['method'], 'DELETE')
        self.assertEqual(logs[1]['method'], 'POST')
        
        # Test retrieving all logs
        all_logs = get_vastai_logs(max_lines=100)
        self.assertEqual(len(all_logs), 3)
    
    def test_get_vastai_log_manifest(self):
        """Test getting log file manifest"""
        # Create some test log entries
        log_api_interaction("GET", "/instances/", status_code=200)
        
        manifest = get_vastai_log_manifest()
        self.assertEqual(len(manifest), 1)
        
        file_info = manifest[0]
        self.assertTrue(file_info['filename'].startswith('api_log_'))
        self.assertTrue(file_info['filename'].endswith('.json'))
        self.assertEqual(file_info['entry_count'], 1)
        self.assertGreater(file_info['size'], 0)


if __name__ == '__main__':
    unittest.main()