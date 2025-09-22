#!/usr/bin/env python3
"""
Test for status field fix in vastai_utils.py
"""

import unittest
import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.vastai.vastai_utils import format_instance_info


class TestStatusFieldFix(unittest.TestCase):
    """Test that format_instance_info correctly uses cur_state for status"""
    
    def test_format_instance_info_with_cur_state(self):
        """Test that format_instance_info correctly maps cur_state to status"""
        # Sample instance data as returned by VastAI API
        instance_data = {
            'id': '12345',
            'gpu_name': 'RTX 4090',
            'ssh_host': 'example.com',
            'ssh_port': 22,
            'cur_state': 'running',
            'geolocation': 'US, California'
        }
        
        result = format_instance_info(instance_data)
        
        # Verify all fields are mapped correctly
        self.assertEqual(result['id'], '12345')
        self.assertEqual(result['gpu'], 'RTX 4090')
        self.assertEqual(result['host'], 'example.com')
        self.assertEqual(result['port'], 22)
        self.assertEqual(result['status'], 'running')  # This should come from cur_state
        self.assertEqual(result['location'], 'US, California')
    
    def test_format_instance_info_with_different_status_values(self):
        """Test formatting with different possible status values"""
        test_cases = [
            {'cur_state': 'running', 'expected': 'running'},
            {'cur_state': 'stopped', 'expected': 'stopped'},
            {'cur_state': 'starting', 'expected': 'starting'},
            {'cur_state': 'loading', 'expected': 'loading'},
        ]
        
        for test_case in test_cases:
            instance_data = {
                'id': '123',
                'cur_state': test_case['cur_state']
            }
            
            result = format_instance_info(instance_data)
            self.assertEqual(result['status'], test_case['expected'])
    
    def test_format_instance_info_missing_cur_state(self):
        """Test that missing cur_state results in None status"""
        instance_data = {
            'id': '123',
            'gpu_name': 'RTX 4090',
            # cur_state is missing
        }
        
        result = format_instance_info(instance_data)
        self.assertIsNone(result['status'])
    
    def test_format_instance_info_empty_instance(self):
        """Test formatting empty instance data"""
        result = format_instance_info({})
        self.assertEqual(result, {})
        
        result = format_instance_info(None)
        self.assertEqual(result, {})
    
    def test_format_instance_info_does_not_use_actual_status(self):
        """Test that actual_status field is ignored (regression test)"""
        instance_data = {
            'id': '123',
            'cur_state': 'running',
            'actual_status': 'should_be_ignored'  # This should not be used
        }
        
        result = format_instance_info(instance_data)
        # The status should come from cur_state, not actual_status
        self.assertEqual(result['status'], 'running')
        self.assertNotEqual(result['status'], 'should_be_ignored')


if __name__ == '__main__':
    unittest.main()