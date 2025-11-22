"""
Test workflow state persistence functionality
"""

import os
import json
import tempfile
import pytest
from datetime import datetime

# Import the module to test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.sync.workflow_state import WorkflowStateManager


class TestWorkflowStateManager:
    """Test cases for WorkflowStateManager"""
    
    def setup_method(self):
        """Setup test fixtures"""
        # Create a temporary state file for testing
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.state_file = self.temp_file.name
        self.manager = WorkflowStateManager(self.state_file)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        # Remove temporary state file
        from pathlib import Path
        Path(self.state_file).unlink(missing_ok=True)
    
    def test_save_and_load_state(self):
        """Test saving and loading workflow state"""
        # Create test state
        test_state = {
            'workflow_id': 'test_workflow_123',
            'status': 'running',
            'current_step': 2,
            'steps': [
                {'action': 'test_ssh', 'status': 'completed', 'index': 0},
                {'action': 'set_ui_home', 'status': 'completed', 'index': 1},
                {'action': 'sync_instance', 'status': 'in_progress', 'index': 2}
            ],
            'start_time': '2024-01-01T00:00:00Z',
            'ssh_connection': 'ssh -p 2222 root@example.com'
        }
        
        # Save state
        result = self.manager.save_state(test_state)
        assert result is True, "save_state should return True"
        
        # Verify file exists
        assert os.path.exists(self.state_file), "State file should exist"
        
        # Load state
        loaded_state = self.manager.load_state()
        assert loaded_state is not None, "load_state should return state"
        assert loaded_state['workflow_id'] == 'test_workflow_123'
        assert loaded_state['status'] == 'running'
        assert loaded_state['current_step'] == 2
        assert len(loaded_state['steps']) == 3
        assert 'last_update' in loaded_state
    
    def test_load_nonexistent_state(self):
        """Test loading state when no state file exists"""
        # Ensure state file doesn't exist
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        
        loaded_state = self.manager.load_state()
        assert loaded_state is None, "load_state should return None when no state exists"
    
    def test_clear_state(self):
        """Test clearing workflow state"""
        # Create and save test state
        test_state = {
            'workflow_id': 'test_clear',
            'status': 'running',
            'current_step': 0,
            'steps': [],
            'start_time': datetime.now().isoformat()
        }
        self.manager.save_state(test_state)
        
        # Verify state exists
        assert os.path.exists(self.state_file)
        
        # Clear state
        result = self.manager.clear_state()
        assert result is True, "clear_state should return True"
        assert not os.path.exists(self.state_file), "State file should be deleted"
        
        # Verify state is None after clearing
        loaded_state = self.manager.load_state()
        assert loaded_state is None, "State should be None after clearing"
    
    def test_is_active(self):
        """Test checking if workflow is active"""
        # Test with no state
        assert self.manager.is_active() is False, "Should not be active with no state"
        
        # Test with running workflow
        running_state = {
            'workflow_id': 'test_active',
            'status': 'running',
            'current_step': 0,
            'steps': [],
            'start_time': datetime.now().isoformat()
        }
        self.manager.save_state(running_state)
        assert self.manager.is_active() is True, "Should be active with running status"
        
        # Test with completed workflow
        completed_state = running_state.copy()
        completed_state['status'] = 'completed'
        self.manager.save_state(completed_state)
        assert self.manager.is_active() is False, "Should not be active with completed status"
        
        # Test with failed workflow
        failed_state = running_state.copy()
        failed_state['status'] = 'failed'
        self.manager.save_state(failed_state)
        assert self.manager.is_active() is False, "Should not be active with failed status"
    
    def test_update_step_progress(self):
        """Test updating step progress"""
        # Create initial state with steps
        initial_state = {
            'workflow_id': 'test_update',
            'status': 'running',
            'current_step': 0,
            'steps': [
                {'action': 'step1', 'status': 'pending', 'index': 0},
                {'action': 'step2', 'status': 'pending', 'index': 1},
                {'action': 'step3', 'status': 'pending', 'index': 2}
            ],
            'start_time': datetime.now().isoformat()
        }
        self.manager.save_state(initial_state)
        
        # Update step 1 to in_progress
        result = self.manager.update_step_progress(1, 'in_progress', {'message': 'Processing'})
        assert result is True, "update_step_progress should return True"
        
        # Verify update
        state = self.manager.load_state()
        assert state['current_step'] == 1
        assert state['steps'][1]['status'] == 'in_progress'
        assert state['steps'][1]['data']['message'] == 'Processing'
        
        # Update step 1 to completed
        result = self.manager.update_step_progress(1, 'completed')
        assert result is True
        
        # Verify update
        state = self.manager.load_state()
        assert state['steps'][1]['status'] == 'completed'
    
    def test_get_state_summary(self):
        """Test getting workflow state summary"""
        # Test with no state
        summary = self.manager.get_state_summary()
        assert summary['active'] is False
        assert summary['workflow_id'] is None
        assert summary['status'] is None
        
        # Create state with progress
        state = {
            'workflow_id': 'test_summary',
            'status': 'running',
            'current_step': 2,
            'steps': [
                {'action': 'step1', 'status': 'completed'},
                {'action': 'step2', 'status': 'completed'},
                {'action': 'step3', 'status': 'in_progress'},
                {'action': 'step4', 'status': 'pending'},
                {'action': 'step5', 'status': 'pending'}
            ],
            'start_time': '2024-01-01T00:00:00Z'
        }
        self.manager.save_state(state)
        
        # Get summary
        summary = self.manager.get_state_summary()
        assert summary['active'] is True
        assert summary['workflow_id'] == 'test_summary'
        assert summary['status'] == 'running'
        assert summary['current_step'] == 2
        assert summary['total_steps'] == 5
        assert summary['progress_percent'] == 60.0  # 3 out of 5 steps (current_step=2 means step 0,1,2 completed)
        assert 'start_time' in summary
        assert 'last_update' in summary
    
    def test_invalid_json_recovery(self):
        """Test recovery from corrupted JSON file"""
        # Write invalid JSON to state file
        with open(self.state_file, 'w') as f:
            f.write('{invalid json content}')
        
        # Should return None and remove corrupted file
        loaded_state = self.manager.load_state()
        assert loaded_state is None, "Should return None for invalid JSON"
        assert not os.path.exists(self.state_file), "Corrupted file should be removed"
    
    def test_concurrent_access(self):
        """Test thread-safe access to state"""
        import threading
        
        results = []
        
        def save_state(workflow_id):
            state = {
                'workflow_id': workflow_id,
                'status': 'running',
                'current_step': 0,
                'steps': [],
                'start_time': datetime.now().isoformat()
            }
            result = self.manager.save_state(state)
            results.append(result)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=save_state, args=(f'workflow_{i}',))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All saves should succeed
        assert all(results), "All concurrent saves should succeed"
        
        # Final state should be from one of the threads
        final_state = self.manager.load_state()
        assert final_state is not None
        assert final_state['workflow_id'].startswith('workflow_')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
