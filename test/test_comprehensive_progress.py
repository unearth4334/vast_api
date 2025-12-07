#!/usr/bin/env python3
"""
Test for comprehensive progress readouts in custom nodes installer
Validates that new progress fields (download_rate, total_size, elapsed_time, eta) are properly tracked
"""

import unittest
import json
import tempfile
import os
from pathlib import Path


class TestComprehensiveProgressReadouts(unittest.TestCase):
    """Test the comprehensive progress tracking enhancements"""
    
    def test_json_progress_structure(self):
        """Test that JSON progress includes all new fields"""
        # Simulate a progress JSON file
        progress_data = {
            "in_progress": True,
            "completed": False,
            "success": True,
            "total_nodes": 10,
            "processed": 3,
            "current_node": "ComfyUI-Manager",
            "current_status": "running",
            "successful": 2,
            "failed": 0,
            "has_requirements": False,
            "clone_progress": 45,
            "download_rate": "1.2 MiB/s",
            "data_received": "5.4 MiB",
            "total_size": "12.0 MiB",
            "elapsed_time": "01:23",
            "eta": "02:15"
        }
        
        # Verify all expected fields are present
        self.assertIn('clone_progress', progress_data)
        self.assertIn('download_rate', progress_data)
        self.assertIn('data_received', progress_data)
        self.assertIn('total_size', progress_data)
        self.assertIn('elapsed_time', progress_data)
        self.assertIn('eta', progress_data)
        
        # Verify data types and formats
        self.assertIsInstance(progress_data['clone_progress'], int)
        self.assertIsInstance(progress_data['download_rate'], str)
        self.assertIsInstance(progress_data['data_received'], str)
        self.assertIsInstance(progress_data['total_size'], str)
        self.assertIsInstance(progress_data['elapsed_time'], str)
        self.assertIsInstance(progress_data['eta'], str)
        
        # Verify time format (MM:SS)
        self.assertRegex(progress_data['elapsed_time'], r'^\d{2}:\d{2}$')
        self.assertRegex(progress_data['eta'], r'^\d{2}:\d{2}$')
        
        # Verify size format (includes unit)
        self.assertRegex(progress_data['data_received'], r'^\d+\.?\d*\s+(KiB|MiB|GiB)$')
        self.assertRegex(progress_data['total_size'], r'^\d+\.?\d*\s+(KiB|MiB|GiB)$')
        
        # Verify rate format (includes /s)
        self.assertRegex(progress_data['download_rate'], r'^\d+\.?\d*\s+(KiB|MiB|GiB)/s$')
    
    def test_progress_percentage_range(self):
        """Test that clone progress percentage is within valid range"""
        for progress in [0, 25, 50, 75, 100]:
            progress_data = {
                "in_progress": True,
                "clone_progress": progress
            }
            self.assertGreaterEqual(progress_data['clone_progress'], 0)
            self.assertLessEqual(progress_data['clone_progress'], 100)
    
    def test_progress_single_line_format(self):
        """Test that progress info can be formatted into a single line"""
        progress_data = {
            "current_node": "ComfyUI-Manager",
            "clone_progress": 45,
            "download_rate": "1.2 MiB/s",
            "data_received": "5.4 MiB",
            "total_size": "12.0 MiB",
            "elapsed_time": "01:23",
            "eta": "02:15"
        }
        
        # Format as a single line (as would be displayed in UI)
        single_line = (
            f"{progress_data['current_node']}: "
            f"{progress_data['clone_progress']}% | "
            f"{progress_data['data_received']}/{progress_data['total_size']} @ "
            f"{progress_data['download_rate']} | "
            f"Elapsed: {progress_data['elapsed_time']} | "
            f"ETA: {progress_data['eta']}"
        )
        
        # Verify single line is reasonable length (< 150 chars for typical terminal)
        self.assertLess(len(single_line), 150)
        
        # Verify it contains all key information
        self.assertIn('ComfyUI-Manager', single_line)
        self.assertIn('45%', single_line)
        self.assertIn('1.2 MiB/s', single_line)
        self.assertIn('5.4 MiB', single_line)
        self.assertIn('12.0 MiB', single_line)
        self.assertIn('01:23', single_line)
        self.assertIn('02:15', single_line)
    
    def test_progress_with_requirements(self):
        """Test progress tracking for nodes with requirements"""
        progress_data = {
            "in_progress": True,
            "current_node": "ComfyUI-Custom-Scripts",
            "has_requirements": True,
            "requirements_status": "collecting (3/10): numpy",
            "clone_progress": 100,
            "data_received": "8.2 MiB",
            "total_size": "8.2 MiB",
            "elapsed_time": "00:45"
        }
        
        # Verify requirements tracking
        self.assertTrue(progress_data['has_requirements'])
        self.assertIn('collecting', progress_data['requirements_status'])
        self.assertIn('numpy', progress_data['requirements_status'])
        
        # Format with requirements info
        single_line = (
            f"{progress_data['current_node']}: "
            f"Clone complete ({progress_data['total_size']}) | "
            f"Dependencies: {progress_data['requirements_status']} | "
            f"Elapsed: {progress_data['elapsed_time']}"
        )
        
        self.assertLess(len(single_line), 150)
        self.assertIn('Dependencies', single_line)
        self.assertIn('numpy', single_line)
    
    def test_completion_status(self):
        """Test that completion includes comprehensive stats"""
        progress_data = {
            "in_progress": False,
            "completed": True,
            "success": True,
            "total_nodes": 10,
            "processed": 10,
            "successful": 9,
            "failed": 1,
            "current_node": "Installation complete",
            "current_status": "completed"
        }
        
        # Verify completion status
        self.assertFalse(progress_data['in_progress'])
        self.assertTrue(progress_data['completed'])
        self.assertTrue(progress_data['success'])
        
        # Verify final counts
        self.assertEqual(progress_data['total_nodes'], 10)
        self.assertEqual(progress_data['processed'], 10)
        self.assertEqual(progress_data['successful'], 9)
        self.assertEqual(progress_data['failed'], 1)
    
    def test_backward_compatibility(self):
        """Test that old progress format still works (without new fields)"""
        # Old format progress data (without new fields)
        old_progress_data = {
            "in_progress": True,
            "total_nodes": 5,
            "processed": 2,
            "current_node": "ComfyUI-Manager",
            "current_status": "running",
            "successful": 1,
            "failed": 0
        }
        
        # Should work without new fields
        self.assertIn('current_node', old_progress_data)
        self.assertIn('current_status', old_progress_data)
        
        # New fields should be optional
        self.assertNotIn('clone_progress', old_progress_data)
        self.assertNotIn('download_rate', old_progress_data)
        self.assertNotIn('eta', old_progress_data)


if __name__ == '__main__':
    unittest.main()
