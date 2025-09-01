#!/usr/bin/env python3
"""
Test script to verify mobile-specific fixes for Obsidian integration
"""

import unittest
import json
import os
from unittest.mock import patch, Mock
from sync_api import app


class TestMobileFixes(unittest.TestCase):
    
    def setUp(self):
        """Set up test client"""
        self.app = app.test_client()
        self.app.testing = True
    
    def test_sync_latest_endpoint_no_progress_files(self):
        """Test that /sync/latest returns proper response when no progress files exist"""
        # Clear any existing progress files
        import glob
        for f in glob.glob("/tmp/sync_progress_*.json"):
            try:
                os.remove(f)
            except:
                pass
        
        response = self.app.get('/sync/latest')
        data = json.loads(response.data)
        
        # Should return 404 with success=False instead of throwing error
        self.assertEqual(response.status_code, 404)
        self.assertFalse(data['success'])
        self.assertIn('message', data)
    
    def test_sync_progress_endpoint_missing_id(self):
        """Test that /sync/progress/<id> handles missing progress files gracefully"""
        fake_id = "nonexistent-id-12345"
        response = self.app.get(f'/sync/progress/{fake_id}')
        data = json.loads(response.data)
        
        # Should return 404 with descriptive message
        self.assertEqual(response.status_code, 404)
        self.assertFalse(data['success'])
        self.assertIn('Progress file not found', data['message'])
        self.assertEqual(data['sync_id'], fake_id)
    
    def test_cors_headers_for_mobile(self):
        """Test that proper CORS headers are set for mobile requests"""
        # Test with Obsidian mobile origin
        response = self.app.get('/status', headers={'Origin': 'app://obsidian.md'})
        
        # Check that Private Network Access header is set
        self.assertIn('Access-Control-Allow-Private-Network', response.headers)
        self.assertEqual(response.headers['Access-Control-Allow-Private-Network'], 'true')
    
    def test_options_requests_for_mobile(self):
        """Test that OPTIONS requests are handled properly for mobile CORS"""
        response = self.app.options('/sync/forge')
        self.assertEqual(response.status_code, 204)
        
        response = self.app.options('/sync/comfy')
        self.assertEqual(response.status_code, 204)
        
        response = self.app.options('/sync/vastai')
        self.assertEqual(response.status_code, 204)
    
    def test_sync_endpoints_return_sync_id(self):
        """Test that sync endpoints return sync_id for progress tracking"""
        with patch('sync_api.subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Sync completed"
            mock_run.return_value.stderr = ""
            
            response = self.app.post('/sync/forge')
            data = json.loads(response.data)
            
            self.assertTrue(data['success'])
            self.assertIn('sync_id', data)
            self.assertIsInstance(data['sync_id'], str)


if __name__ == '__main__':
    unittest.main()