#!/usr/bin/env python3
"""
Test the BackgroundTaskManager
"""

import unittest
import time
import threading
import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.sync.background_tasks import BackgroundTaskManager, get_task_manager


class TestBackgroundTaskManager(unittest.TestCase):
    """Test the BackgroundTaskManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.task_manager = BackgroundTaskManager()
    
    def test_start_simple_task(self):
        """Test starting a simple task"""
        result = {'completed': False}
        
        def simple_task():
            time.sleep(0.1)
            result['completed'] = True
        
        task_id = 'test-task-1'
        self.task_manager.start_task(task_id, simple_task)
        
        # Check task is running
        self.assertTrue(self.task_manager.is_task_running(task_id))
        
        # Wait for completion
        time.sleep(0.2)
        
        # Check task completed
        self.assertTrue(result['completed'])
        self.assertFalse(self.task_manager.is_task_running(task_id))
        
        # Check status
        status = self.task_manager.get_status(task_id)
        self.assertIsNotNone(status)
        self.assertEqual(status['state'], 'completed')
        self.assertEqual(status['task_id'], task_id)
    
    def test_start_task_with_args(self):
        """Test starting a task with arguments"""
        result = {'value': None}
        
        def task_with_args(x, y, z=0):
            result['value'] = x + y + z
        
        task_id = 'test-task-2'
        self.task_manager.start_task(task_id, task_with_args, 10, 20, z=5)
        
        # Wait for completion
        time.sleep(0.1)
        
        # Check result
        self.assertEqual(result['value'], 35)
        
        # Check status
        status = self.task_manager.get_status(task_id)
        self.assertEqual(status['state'], 'completed')
    
    def test_task_failure(self):
        """Test task that raises an exception"""
        def failing_task():
            raise ValueError("Test error")
        
        task_id = 'test-task-3'
        self.task_manager.start_task(task_id, failing_task)
        
        # Wait for completion
        time.sleep(0.1)
        
        # Check status
        status = self.task_manager.get_status(task_id)
        self.assertEqual(status['state'], 'failed')
        self.assertIn('Test error', status['error'])
    
    def test_duplicate_task(self):
        """Test starting a task with duplicate ID while first is running"""
        def long_task():
            time.sleep(0.5)
        
        task_id = 'test-task-4'
        self.task_manager.start_task(task_id, long_task)
        
        # Try to start same task again
        with self.assertRaises(ValueError) as context:
            self.task_manager.start_task(task_id, long_task)
        
        self.assertIn('already running', str(context.exception))
        
        # Wait for task to complete
        time.sleep(0.6)
    
    def test_get_nonexistent_task(self):
        """Test getting status of non-existent task"""
        status = self.task_manager.get_status('nonexistent-task')
        self.assertIsNone(status)
    
    def test_is_task_running_false(self):
        """Test is_task_running for non-existent task"""
        self.assertFalse(self.task_manager.is_task_running('nonexistent-task'))
    
    def test_cleanup_completed_task(self):
        """Test cleanup of completed task"""
        result = {'completed': False}
        
        def simple_task():
            result['completed'] = True
        
        task_id = 'test-task-5'
        self.task_manager.start_task(task_id, simple_task)
        
        # Wait for completion
        time.sleep(0.1)
        
        # Cleanup task
        success = self.task_manager.cleanup_task(task_id)
        self.assertTrue(success)
        
        # Task should be gone
        status = self.task_manager.get_status(task_id)
        self.assertIsNone(status)
    
    def test_cleanup_running_task(self):
        """Test cleanup of running task should fail"""
        def long_task():
            time.sleep(1.0)
        
        task_id = 'test-task-6'
        self.task_manager.start_task(task_id, long_task)
        
        # Try to cleanup while running
        success = self.task_manager.cleanup_task(task_id)
        self.assertFalse(success)
        
        # Task should still exist
        status = self.task_manager.get_status(task_id)
        self.assertIsNotNone(status)
        
        # Wait for task to complete
        time.sleep(1.1)
    
    def test_get_all_tasks(self):
        """Test getting all tasks"""
        def quick_task():
            time.sleep(0.05)
        
        # Start multiple tasks
        task_ids = ['task-a', 'task-b', 'task-c']
        for task_id in task_ids:
            self.task_manager.start_task(task_id, quick_task)
        
        # Get all tasks
        all_tasks = self.task_manager.get_all_tasks()
        
        # Should have all tasks
        for task_id in task_ids:
            self.assertIn(task_id, all_tasks)
            self.assertIn('thread_alive', all_tasks[task_id])
        
        # Wait for completion
        time.sleep(0.2)
    
    def test_concurrent_tasks(self):
        """Test running multiple tasks concurrently"""
        results = {'a': False, 'b': False, 'c': False}
        
        def task_a():
            time.sleep(0.1)
            results['a'] = True
        
        def task_b():
            time.sleep(0.1)
            results['b'] = True
        
        def task_c():
            time.sleep(0.1)
            results['c'] = True
        
        # Start all tasks
        self.task_manager.start_task('task-a', task_a)
        self.task_manager.start_task('task-b', task_b)
        self.task_manager.start_task('task-c', task_c)
        
        # All should be running
        self.assertTrue(self.task_manager.is_task_running('task-a'))
        self.assertTrue(self.task_manager.is_task_running('task-b'))
        self.assertTrue(self.task_manager.is_task_running('task-c'))
        
        # Wait for completion
        time.sleep(0.2)
        
        # All should be completed
        self.assertTrue(results['a'])
        self.assertTrue(results['b'])
        self.assertTrue(results['c'])
        
        # All should have completed status
        self.assertEqual(self.task_manager.get_status('task-a')['state'], 'completed')
        self.assertEqual(self.task_manager.get_status('task-b')['state'], 'completed')
        self.assertEqual(self.task_manager.get_status('task-c')['state'], 'completed')
    
    def test_get_task_manager_singleton(self):
        """Test that get_task_manager returns a singleton"""
        tm1 = get_task_manager()
        tm2 = get_task_manager()
        
        # Should be the same instance
        self.assertIs(tm1, tm2)


class TestBackgroundTaskManagerEdgeCases(unittest.TestCase):
    """Test edge cases for BackgroundTaskManager"""
    
    def test_task_with_no_args(self):
        """Test task with no arguments"""
        tm = BackgroundTaskManager()
        result = {'value': 42}
        
        def no_arg_task():
            result['value'] = 100
        
        tm.start_task('test-no-args', no_arg_task)
        time.sleep(0.1)
        
        self.assertEqual(result['value'], 100)
    
    def test_task_completion_timestamps(self):
        """Test that completion timestamps are set"""
        tm = BackgroundTaskManager()
        
        def quick_task():
            pass
        
        task_id = 'test-timestamps'
        tm.start_task(task_id, quick_task)
        
        # Get start time
        status = tm.get_status(task_id)
        start_time = status['started_at']
        self.assertIsNotNone(start_time)
        
        # Wait for completion
        time.sleep(0.1)
        
        # Check completion time
        status = tm.get_status(task_id)
        completed_at = status.get('completed_at')
        self.assertIsNotNone(completed_at)
        self.assertGreaterEqual(completed_at, start_time)
    
    def test_thread_alive_status(self):
        """Test that thread_alive status is accurate"""
        tm = BackgroundTaskManager()
        
        def medium_task():
            time.sleep(0.3)
        
        task_id = 'test-thread-alive'
        tm.start_task(task_id, medium_task)
        
        # Should be alive immediately
        status = tm.get_status(task_id)
        self.assertTrue(status['thread_alive'])
        
        # Wait for completion
        time.sleep(0.4)
        
        # Should not be alive anymore
        status = tm.get_status(task_id)
        self.assertFalse(status['thread_alive'])


if __name__ == '__main__':
    unittest.main()
