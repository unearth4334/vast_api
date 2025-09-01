#!/usr/bin/env python3
"""
Test the mobile-optimized progress tracking implementation
"""

import unittest
import json
import os
import tempfile
import time
from unittest.mock import patch, Mock
from sync_api import app


class TestMobileProgressTracking(unittest.TestCase):
    
    def setUp(self):
        """Set up test client"""
        self.app = app.test_client()
        self.app.testing = True
        
        # Clean up any existing progress files
        import glob
        for f in glob.glob("/tmp/sync_progress_*.json"):
            try:
                os.remove(f)
            except:
                pass
    
    def create_test_progress_file(self, sync_id, data):
        """Helper to create test progress files"""
        progress_file = f"/tmp/sync_progress_{sync_id}.json"
        with open(progress_file, 'w') as f:
            json.dump(data, f)
        return progress_file
    
    def test_mobile_detection(self):
        """Test mobile user agent detection"""
        # Test with mobile user agent
        headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)'}
        response = self.app.get('/sync/latest', headers=headers)
        # Should work regardless of user agent
        self.assertIn(response.status_code, [200, 404])
    
    def test_mobile_latest_endpoint(self):
        """Test mobile-optimized latest endpoint"""
        # Create a test progress file
        test_data = {
            "sync_id": "test-123",
            "status": "running",
            "progress_percent": 50,
            "current_stage": "syncing",
            "messages": [
                {"message": "Starting sync", "timestamp": "2024-01-01T10:00:00"},
                {"message": "Processing files", "timestamp": "2024-01-01T10:01:00"}
            ],
            "current_folder": "test-folder",
            "total_folders": 10,
            "completed_folders": 5
        }
        
        self.create_test_progress_file("test-123", test_data)
        
        response = self.app.get('/sync/mobile/latest')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['sync_id'], 'test-123')
        
        # Check that mobile response contains simplified data
        progress = data['progress']
        self.assertIn('status', progress)
        self.assertIn('progress_percent', progress)
        self.assertIn('current_stage', progress)
        self.assertIn('latest_message', progress)  # Should contain only latest message
        
        # Check that mobile response doesn't contain full message array
        self.assertNotIn('messages', progress)
        
        # Check cache headers
        self.assertEqual(response.headers.get('Cache-Control'), 'no-cache, no-store, must-revalidate')
    
    def test_mobile_progress_endpoint(self):
        """Test mobile-optimized progress endpoint"""
        test_data = {
            "sync_id": "mobile-test-456",
            "status": "running",
            "progress_percent": 75,
            "current_stage": "finalizing",
            "messages": [
                {"message": "Almost done", "timestamp": "2024-01-01T10:05:00"}
            ],
            "current_folder": "final-folder"
        }
        
        self.create_test_progress_file("mobile-test-456", test_data)
        
        response = self.app.get('/sync/mobile/progress/mobile-test-456')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertTrue(data['success'])
        
        progress = data['progress']
        self.assertEqual(progress['status'], 'running')
        self.assertEqual(progress['progress_percent'], 75)
        self.assertEqual(progress['current_stage'], 'finalizing')
        self.assertEqual(progress['latest_message'], 'Almost done')
        self.assertIn('timestamp', data)
    
    def test_mobile_progress_missing_file(self):
        """Test mobile progress endpoint with missing file"""
        response = self.app.get('/sync/mobile/progress/nonexistent-id')
        self.assertEqual(response.status_code, 404)
        
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'Sync not found')
        self.assertEqual(data['sync_id'], 'nonexistent-id')
    
    def test_mobile_vs_desktop_latest_endpoint(self):
        """Test that mobile and desktop endpoints return appropriate data"""
        test_data = {
            "sync_id": "comparison-test",
            "status": "running",
            "progress_percent": 25,
            "current_stage": "copying",
            "messages": [
                {"message": "Starting", "timestamp": "2024-01-01T10:00:00"},
                {"message": "In progress", "timestamp": "2024-01-01T10:01:00"},
                {"message": "Still working", "timestamp": "2024-01-01T10:02:00"}
            ],
            "current_folder": "test-folder",
            "extra_field": "should not appear in mobile",
            "detailed_stats": {"files": 100, "bytes": 1024000}
        }
        
        self.create_test_progress_file("comparison-test", test_data)
        
        # Test desktop endpoint (should return full data)
        desktop_response = self.app.get('/sync/latest')
        desktop_data = desktop_response.get_json()
        self.assertTrue(desktop_data['success'])
        desktop_progress = desktop_data['progress']
        self.assertIn('messages', desktop_progress)  # Full messages array
        self.assertIn('extra_field', desktop_progress)  # All fields included
        
        # Test mobile endpoint (should return simplified data)
        mobile_response = self.app.get('/sync/mobile/latest')
        mobile_data = mobile_response.get_json()
        self.assertTrue(mobile_data['success'])
        mobile_progress = mobile_data['progress']
        self.assertNotIn('messages', mobile_progress)  # No full messages array
        self.assertIn('latest_message', mobile_progress)  # Only latest message
        self.assertNotIn('extra_field', mobile_progress)  # Non-essential fields filtered
        self.assertEqual(mobile_progress['latest_message'], 'Still working')  # Latest message
    
    def test_completed_sync_detection(self):
        """Test detection of completed syncs"""
        completed_data = {
            "sync_id": "completed-test",
            "status": "completed",
            "progress_percent": 100,
            "current_stage": "complete",
            "messages": [{"message": "All done!", "timestamp": "2024-01-01T10:10:00"}]
        }
        
        self.create_test_progress_file("completed-test", completed_data)
        
        response = self.app.get('/sync/mobile/latest')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        progress = data['progress']
        self.assertEqual(progress['status'], 'completed')
        self.assertEqual(progress['progress_percent'], 100)
    
    def test_cors_headers_for_mobile_endpoints(self):
        """Test that CORS headers are properly set for mobile endpoints"""
        # Create test data
        test_data = {"sync_id": "cors-test", "status": "running", "progress_percent": 30}
        self.create_test_progress_file("cors-test", test_data)
        
        # Test with Obsidian origin
        headers = {'Origin': 'app://obsidian.md'}
        
        response = self.app.get('/sync/mobile/latest', headers=headers)
        self.assertEqual(response.status_code, 200)
        
        # Should have Private Network Access header
        self.assertIn('Access-Control-Allow-Private-Network', response.headers)
        self.assertEqual(response.headers['Access-Control-Allow-Private-Network'], 'true')
    
    def test_invalid_progress_data(self):
        """Test handling of corrupted progress files"""
        # Create invalid JSON file
        progress_file = f"/tmp/sync_progress_invalid-test.json"
        with open(progress_file, 'w') as f:
            f.write("invalid json {")
        
        response = self.app.get('/sync/mobile/progress/invalid-test')
        self.assertEqual(response.status_code, 500)
        
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('Invalid progress data', data['message'])


if __name__ == '__main__':
    unittest.main()