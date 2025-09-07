#!/usr/bin/env python3
"""
Test the progress API functionality
"""

import unittest
import json
import os
import tempfile
from unittest.mock import patch
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.sync.sync_api import app


class TestProgressAPI(unittest.TestCase):
    """Test progress tracking functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.app = app.test_client()
        self.app.testing = True

    def test_progress_endpoint_not_found(self):
        """Test progress endpoint with non-existent sync ID"""
        response = self.app.get('/sync/progress/nonexistent-id')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('Progress file not found', data['message'])

    def test_progress_endpoint_with_valid_data(self):
        """Test progress endpoint with valid progress file"""
        # Create a temporary progress file
        sync_id = "test-progress-123"
        progress_file = f"/tmp/sync_progress_{sync_id}.json"
        
        # Create mock progress data
        progress_data = {
            "sync_id": sync_id,
            "status": "running",
            "current_stage": "sync_folders",
            "progress_percent": 50,
            "total_folders": 6,
            "completed_folders": 3,
            "current_folder": "txt2img-images",
            "messages": [
                {
                    "timestamp": "2025-09-07T05:30:00.000000",
                    "message": "Syncing folder: txt2img-images"
                }
            ],
            "start_time": "2025-09-07T05:30:00+00:00",
            "last_update": "2025-09-07T05:30:30.000000"
        }
        
        try:
            # Write the progress file
            with open(progress_file, 'w') as f:
                json.dump(progress_data, f)
            
            # Test the endpoint
            response = self.app.get(f'/sync/progress/{sync_id}')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            self.assertIn('progress', data)
            
            # Verify progress data
            progress = data['progress']
            self.assertEqual(progress['sync_id'], sync_id)
            self.assertEqual(progress['status'], 'running')
            self.assertEqual(progress['progress_percent'], 50)
            self.assertEqual(progress['current_stage'], 'sync_folders')
            self.assertEqual(progress['total_folders'], 6)
            self.assertEqual(progress['completed_folders'], 3)
            
        finally:
            # Clean up
            if os.path.exists(progress_file):
                os.remove(progress_file)

    def test_progress_endpoint_completed_sync(self):
        """Test progress endpoint with completed sync"""
        sync_id = "test-completed-456"
        progress_file = f"/tmp/sync_progress_{sync_id}.json"
        
        # Create completed sync data
        progress_data = {
            "sync_id": sync_id,
            "status": "completed",
            "current_stage": "complete",
            "progress_percent": 100,
            "total_folders": 6,
            "completed_folders": 6,
            "messages": [
                {
                    "timestamp": "2025-09-07T05:30:00.000000",
                    "message": "Sync completed successfully"
                }
            ],
            "start_time": "2025-09-07T05:30:00+00:00",
            "last_update": "2025-09-07T05:35:00.000000"
        }
        
        try:
            with open(progress_file, 'w') as f:
                json.dump(progress_data, f)
            
            response = self.app.get(f'/sync/progress/{sync_id}')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            
            progress = data['progress']
            self.assertEqual(progress['status'], 'completed')
            self.assertEqual(progress['progress_percent'], 100)
            self.assertEqual(progress['current_stage'], 'complete')
            
        finally:
            if os.path.exists(progress_file):
                os.remove(progress_file)

    def test_progress_endpoint_invalid_json(self):
        """Test progress endpoint with corrupted JSON file"""
        sync_id = "test-invalid-789"
        progress_file = f"/tmp/sync_progress_{sync_id}.json"
        
        try:
            # Write invalid JSON
            with open(progress_file, 'w') as f:
                f.write("{ invalid json")
            
            response = self.app.get(f'/sync/progress/{sync_id}')
            self.assertEqual(response.status_code, 500)
            
            data = json.loads(response.data)
            self.assertFalse(data['success'])
            self.assertIn('Invalid progress data', data['message'])
            
        finally:
            if os.path.exists(progress_file):
                os.remove(progress_file)

    def test_sync_endpoint_returns_sync_id(self):
        """Test that sync endpoints return sync_id for progress tracking"""
        # Mock the run_sync function to avoid actual sync
        with patch('app.sync.sync_api.run_sync') as mock_run_sync:
            mock_run_sync.return_value = {
                'success': False,  # Even failed syncs should have sync_id
                'sync_id': 'test-sync-999',
                'message': 'Sync failed for testing',
                'error': 'Mock error'
            }
            
            response = self.app.post('/sync/forge', 
                                   json={'cleanup': True},
                                   content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            
            # Even failed syncs should return sync_id for progress tracking
            self.assertIn('sync_id', data)
            self.assertEqual(data['sync_id'], 'test-sync-999')


if __name__ == '__main__':
    unittest.main()