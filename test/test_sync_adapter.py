"""
Tests for sync_adapter module to verify non-blocking progress polling
"""

import asyncio
import time
import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.sync.sync_adapter import _poll_job_status, get_orchestrator
from app.sync.models import SyncJob, SyncResult


class TestPollJobStatus(unittest.TestCase):
    """Test the _poll_job_status function for non-blocking behavior."""

    def test_poll_job_status_completes_immediately(self):
        """Test polling when job completes immediately."""
        # Create a mock orchestrator
        mock_orchestrator = Mock()
        mock_job = Mock()
        mock_job.status = 'complete'
        
        # get_job_status returns completed job
        mock_orchestrator.get_job_status = Mock(return_value=mock_job)
        
        # Run the async polling function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        start_time = time.time()
        result = loop.run_until_complete(_poll_job_status(mock_orchestrator, 'job_123', max_wait=10))
        elapsed = time.time() - start_time
        
        loop.close()
        
        # Should complete quickly
        self.assertLess(elapsed, 1.0)
        self.assertEqual(result, mock_job)
        self.assertEqual(result.status, 'complete')

    def test_poll_job_status_waits_then_completes(self):
        """Test polling when job takes some time to complete."""
        # Create a mock orchestrator
        mock_orchestrator = Mock()
        
        # Simulate job that completes after 3 calls
        call_count = [0]
        
        def get_job_status_side_effect(job_id):
            call_count[0] += 1
            mock_job = Mock()
            if call_count[0] >= 3:
                mock_job.status = 'complete'
            else:
                mock_job.status = 'running'
            return mock_job
        
        mock_orchestrator.get_job_status = Mock(side_effect=get_job_status_side_effect)
        
        # Run the async polling function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        start_time = time.time()
        result = loop.run_until_complete(_poll_job_status(mock_orchestrator, 'job_123', max_wait=10))
        elapsed = time.time() - start_time
        
        loop.close()
        
        # Should take at least 4 seconds (2 waits of 2 seconds each)
        self.assertGreaterEqual(elapsed, 4.0)
        self.assertLess(elapsed, 6.0)  # But not much more
        self.assertEqual(result.status, 'complete')
        # Should have been called 3 times
        self.assertEqual(call_count[0], 3)

    def test_poll_job_status_timeout(self):
        """Test polling when job never completes and times out."""
        # Create a mock orchestrator
        mock_orchestrator = Mock()
        mock_job = Mock()
        mock_job.status = 'running'
        
        # get_job_status always returns running job
        mock_orchestrator.get_job_status = Mock(return_value=mock_job)
        
        # Run the async polling function with short timeout
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        start_time = time.time()
        result = loop.run_until_complete(_poll_job_status(mock_orchestrator, 'job_123', max_wait=5))
        elapsed = time.time() - start_time
        
        loop.close()
        
        # Should time out after ~5 seconds
        self.assertGreaterEqual(elapsed, 4.0)
        self.assertLess(elapsed, 7.0)
        # Should return the last status
        self.assertEqual(result, mock_job)

    def test_poll_job_status_uses_to_thread(self):
        """Test that polling uses asyncio.to_thread to avoid blocking."""
        # This test verifies that get_job_status is called via to_thread
        mock_orchestrator = Mock()
        mock_job = Mock()
        mock_job.status = 'complete'
        
        mock_orchestrator.get_job_status = Mock(return_value=mock_job)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Patch asyncio.to_thread to verify it's being used
        with patch('asyncio.to_thread', wraps=asyncio.to_thread) as mock_to_thread:
            result = loop.run_until_complete(_poll_job_status(mock_orchestrator, 'job_123', max_wait=10))
            
            # Verify to_thread was called
            self.assertTrue(mock_to_thread.called)
            # Verify it was called with orchestrator.get_job_status
            call_args = mock_to_thread.call_args_list[0]
            self.assertEqual(call_args[0][0], mock_orchestrator.get_job_status)
        
        loop.close()


class TestSyncAdapterIntegration(unittest.TestCase):
    """Integration tests for sync_adapter."""

    def test_event_loop_not_blocked(self):
        """Test that the event loop can handle other tasks during polling."""
        # Create a mock orchestrator
        mock_orchestrator = Mock()
        
        # Track when the job completes
        completion_time = [None]
        
        def get_job_status_side_effect(job_id):
            mock_job = Mock()
            # Complete after some time
            if completion_time[0] and (time.time() - completion_time[0]) > 4:
                mock_job.status = 'complete'
            else:
                if not completion_time[0]:
                    completion_time[0] = time.time()
                mock_job.status = 'running'
            return mock_job
        
        mock_orchestrator.get_job_status = Mock(side_effect=get_job_status_side_effect)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Track if other tasks can run
        other_task_ran = [False]
        
        async def other_task():
            """A task that should run while polling."""
            await asyncio.sleep(1)
            other_task_ran[0] = True
        
        async def run_both():
            """Run polling and another task concurrently."""
            poll_task = asyncio.create_task(_poll_job_status(mock_orchestrator, 'job_123', max_wait=10))
            other = asyncio.create_task(other_task())
            
            # Wait for both
            results = await asyncio.gather(poll_task, other)
            return results[0]
        
        start_time = time.time()
        result = loop.run_until_complete(run_both())
        elapsed = time.time() - start_time
        
        loop.close()
        
        # The other task should have run
        self.assertTrue(other_task_ran[0], "Event loop was blocked, other task didn't run")
        # Polling should have completed
        self.assertEqual(result.status, 'complete')


if __name__ == '__main__':
    unittest.main()
