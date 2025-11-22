"""
Unit tests for ComfyUIWorkflowExecutor
Tests workflow execution, state management, and lifecycle operations.
"""

import unittest
import os
import json
import tempfile
import threading
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from app.sync.comfyui_workflow_executor import ComfyUIWorkflowExecutor, get_executor
from app.sync.comfyui_workflow_state import WorkflowStatus, NodeStatus


class TestComfyUIWorkflowExecutor(unittest.TestCase):
    """Test cases for ComfyUI workflow executor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, "test_state.json")
        self.executor = ComfyUIWorkflowExecutor(state_file_path=self.state_file)
        
        # Create test workflow file
        self.workflow_file = os.path.join(self.temp_dir, "test_workflow.json")
        workflow_data = {
            "1": {"class_type": "LoadImage", "inputs": {}},
            "2": {"class_type": "KSampler", "inputs": {}},
            "3": {"class_type": "SaveImage", "inputs": {}}
        }
        with open(self.workflow_file, 'w') as f:
            json.dump(workflow_data, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test executor initialization."""
        self.assertEqual(self.executor.state_file_path, self.state_file)
        self.assertEqual(len(self.executor.active_workflows), 0)
        self.assertEqual(len(self.executor.workflow_states), 0)
    
    @patch('app.sync.comfyui_workflow_executor.create_file_transfer')
    @patch('app.sync.comfyui_workflow_executor.create_progress_monitor')
    def test_execute_workflow_initialization(self, mock_monitor, mock_transfer):
        """Test workflow execution initialization."""
        ssh_connection = "ssh -p 40738 root@198.53.64.194"
        
        success, workflow_id, message = self.executor.execute_workflow(
            ssh_connection=ssh_connection,
            workflow_file=self.workflow_file,
            workflow_name="Test Workflow"
        )
        
        self.assertTrue(success)
        self.assertTrue(workflow_id.startswith("comfyui_workflow_"))
        self.assertEqual(message, "Workflow execution started")
        
        # Verify state was created
        state = self.executor.get_workflow_state(workflow_id)
        self.assertIsNotNone(state)
        self.assertEqual(state.workflow_name, "Test Workflow")
        self.assertEqual(state.status, WorkflowStatus.QUEUED)
        self.assertEqual(state.total_nodes, 3)
    
    def test_execute_workflow_invalid_file(self):
        """Test workflow execution with invalid file."""
        success, workflow_id, message = self.executor.execute_workflow(
            ssh_connection="ssh -p 40738 root@198.53.64.194",
            workflow_file="/nonexistent/workflow.json"
        )
        
        self.assertFalse(success)
        self.assertEqual(workflow_id, "")
        self.assertIn("not found", message)
    
    def test_execute_workflow_invalid_json(self):
        """Test workflow execution with invalid JSON."""
        invalid_file = os.path.join(self.temp_dir, "invalid.json")
        with open(invalid_file, 'w') as f:
            f.write("{ invalid json }")
        
        success, workflow_id, message = self.executor.execute_workflow(
            ssh_connection="ssh -p 40738 root@198.53.64.194",
            workflow_file=invalid_file
        )
        
        self.assertFalse(success)
        self.assertIn("Failed to parse", message)
    
    def test_get_workflow_state(self):
        """Test getting workflow state."""
        # Create a mock state
        from app.sync.comfyui_workflow_state import ComfyUIWorkflowState
        
        workflow_id = "test_workflow_123"
        state = ComfyUIWorkflowState(
            workflow_id=workflow_id,
            workflow_name="Test",
            prompt_id="",
            ssh_connection="ssh -p 40738 root@198.53.64.194",
            workflow_file=self.workflow_file,
            status=WorkflowStatus.QUEUED,
            queue_position=None,
            current_node=None,
            total_nodes=3,
            completed_nodes=0,
            progress_percent=0.0,
            nodes=[],
            queue_time=datetime.now(),
            start_time=None,
            end_time=None,
            last_update=datetime.now(),
            outputs=[],
            error_message=None,
            failed_node=None
        )
        
        self.executor.workflow_states[workflow_id] = state
        
        retrieved_state = self.executor.get_workflow_state(workflow_id)
        self.assertIsNotNone(retrieved_state)
        self.assertEqual(retrieved_state.workflow_id, workflow_id)
    
    def test_cancel_workflow(self):
        """Test workflow cancellation."""
        workflow_id = "test_workflow_123"
        
        # Create stop flag
        stop_flag = threading.Event()
        self.executor.stop_flags[workflow_id] = stop_flag
        
        # Cancel workflow
        success = self.executor.cancel_workflow(workflow_id)
        
        self.assertTrue(success)
        self.assertTrue(stop_flag.is_set())
    
    def test_cancel_nonexistent_workflow(self):
        """Test cancelling non-existent workflow."""
        success = self.executor.cancel_workflow("nonexistent_workflow")
        self.assertFalse(success)
    
    def test_is_workflow_active(self):
        """Test checking if workflow is active."""
        workflow_id = "test_workflow_123"
        
        # Not active initially
        self.assertFalse(self.executor.is_workflow_active(workflow_id))
        
        # Add to active workflows
        mock_thread = Mock()
        self.executor.active_workflows[workflow_id] = mock_thread
        
        # Should be active now
        self.assertTrue(self.executor.is_workflow_active(workflow_id))
    
    def test_save_and_load_state(self):
        """Test state persistence."""
        from app.sync.comfyui_workflow_state import (
            ComfyUIWorkflowState, 
            ComfyUINodeState,
            ComfyUIOutputFile
        )
        
        workflow_id = "test_workflow_123"
        
        # Create state with full data
        state = ComfyUIWorkflowState(
            workflow_id=workflow_id,
            workflow_name="Test Workflow",
            prompt_id="prompt_abc_123",
            ssh_connection="ssh -p 40738 root@198.53.64.194",
            workflow_file=self.workflow_file,
            status=WorkflowStatus.EXECUTING,
            queue_position=None,
            current_node="2",
            total_nodes=3,
            completed_nodes=1,
            progress_percent=33.3,
            nodes=[
                ComfyUINodeState(
                    node_id="1",
                    node_type="LoadImage",
                    status=NodeStatus.EXECUTED,
                    progress=100.0,
                    message="Loaded"
                ),
                ComfyUINodeState(
                    node_id="2",
                    node_type="KSampler",
                    status=NodeStatus.EXECUTING,
                    progress=50.0,
                    message="Sampling"
                )
            ],
            queue_time=datetime.now(),
            start_time=datetime.now(),
            end_time=None,
            last_update=datetime.now(),
            outputs=[
                ComfyUIOutputFile(
                    filename="output.png",
                    file_type="image",
                    remote_path="/workspace/output/output.png",
                    local_path=None,
                    downloaded=False
                )
            ],
            error_message=None,
            failed_node=None
        )
        
        self.executor.workflow_states[workflow_id] = state
        self.executor._save_state(workflow_id)
        
        # Verify file was created
        self.assertTrue(os.path.exists(self.state_file))
        
        # Create new executor and load state
        new_executor = ComfyUIWorkflowExecutor(state_file_path=self.state_file)
        loaded_state = new_executor.load_state()
        
        self.assertIsNotNone(loaded_state)
        self.assertEqual(loaded_state.workflow_id, workflow_id)
        self.assertEqual(loaded_state.workflow_name, "Test Workflow")
        self.assertEqual(loaded_state.status, WorkflowStatus.EXECUTING)
        self.assertEqual(loaded_state.progress_percent, 33.3)
        self.assertEqual(len(loaded_state.nodes), 2)
        self.assertEqual(len(loaded_state.outputs), 1)
    
    def test_update_progress(self):
        """Test progress updates."""
        from app.sync.comfyui_workflow_state import ComfyUIWorkflowState
        
        workflow_id = "test_workflow_123"
        
        # Create initial state
        state = ComfyUIWorkflowState(
            workflow_id=workflow_id,
            workflow_name="Test",
            prompt_id="prompt_123",
            ssh_connection="ssh -p 40738 root@198.53.64.194",
            workflow_file=self.workflow_file,
            status=WorkflowStatus.QUEUED,
            queue_position=5,
            current_node=None,
            total_nodes=3,
            completed_nodes=0,
            progress_percent=0.0,
            nodes=[],
            queue_time=datetime.now(),
            start_time=None,
            end_time=None,
            last_update=datetime.now(),
            outputs=[],
            error_message=None,
            failed_node=None
        )
        
        self.executor.workflow_states[workflow_id] = state
        
        # Update progress
        progress_update = {
            'status': 'executing',
            'queue_position': None,
            'current_node': '2',
            'completed_nodes': 1,
            'progress_percent': 33.3,
            'nodes': [
                {
                    'node_id': '1',
                    'node_type': 'LoadImage',
                    'status': 'executed',
                    'progress': 100.0
                }
            ]
        }
        
        self.executor._update_progress(workflow_id, progress_update)
        
        # Verify updates
        updated_state = self.executor.get_workflow_state(workflow_id)
        self.assertEqual(updated_state.status, WorkflowStatus.EXECUTING)
        self.assertIsNone(updated_state.queue_position)
        self.assertEqual(updated_state.current_node, '2')
        self.assertEqual(updated_state.completed_nodes, 1)
        self.assertEqual(updated_state.progress_percent, 33.3)
        self.assertEqual(len(updated_state.nodes), 1)
    
    def test_set_completed(self):
        """Test marking workflow as completed."""
        from app.sync.comfyui_workflow_state import ComfyUIWorkflowState
        
        workflow_id = "test_workflow_123"
        
        state = ComfyUIWorkflowState(
            workflow_id=workflow_id,
            workflow_name="Test",
            prompt_id="",
            ssh_connection="ssh -p 40738 root@198.53.64.194",
            workflow_file=self.workflow_file,
            status=WorkflowStatus.EXECUTING,
            queue_position=None,
            current_node=None,
            total_nodes=3,
            completed_nodes=2,
            progress_percent=66.6,
            nodes=[],
            queue_time=datetime.now(),
            start_time=datetime.now(),
            end_time=None,
            last_update=datetime.now(),
            outputs=[],
            error_message=None,
            failed_node=None
        )
        
        self.executor.workflow_states[workflow_id] = state
        self.executor._set_completed(workflow_id)
        
        completed_state = self.executor.get_workflow_state(workflow_id)
        self.assertEqual(completed_state.status, WorkflowStatus.COMPLETED)
        self.assertEqual(completed_state.progress_percent, 100.0)
        self.assertIsNotNone(completed_state.end_time)
    
    def test_set_error(self):
        """Test marking workflow as failed."""
        from app.sync.comfyui_workflow_state import ComfyUIWorkflowState
        
        workflow_id = "test_workflow_123"
        
        state = ComfyUIWorkflowState(
            workflow_id=workflow_id,
            workflow_name="Test",
            prompt_id="",
            ssh_connection="ssh -p 40738 root@198.53.64.194",
            workflow_file=self.workflow_file,
            status=WorkflowStatus.EXECUTING,
            queue_position=None,
            current_node="2",
            total_nodes=3,
            completed_nodes=1,
            progress_percent=33.3,
            nodes=[],
            queue_time=datetime.now(),
            start_time=datetime.now(),
            end_time=None,
            last_update=datetime.now(),
            outputs=[],
            error_message=None,
            failed_node=None
        )
        
        self.executor.workflow_states[workflow_id] = state
        self.executor._set_error(workflow_id, "Node execution failed", "2")
        
        failed_state = self.executor.get_workflow_state(workflow_id)
        self.assertEqual(failed_state.status, WorkflowStatus.FAILED)
        self.assertEqual(failed_state.error_message, "Node execution failed")
        self.assertEqual(failed_state.failed_node, "2")
        self.assertIsNotNone(failed_state.end_time)
    
    def test_cleanup_completed_workflows(self):
        """Test cleanup of old completed workflows."""
        from app.sync.comfyui_workflow_state import ComfyUIWorkflowState
        from datetime import timedelta
        
        # Create old completed workflow
        old_workflow_id = "old_workflow_123"
        old_time = datetime.now() - timedelta(hours=2)
        
        old_state = ComfyUIWorkflowState(
            workflow_id=old_workflow_id,
            workflow_name="Old",
            prompt_id="",
            ssh_connection="ssh -p 40738 root@198.53.64.194",
            workflow_file=self.workflow_file,
            status=WorkflowStatus.COMPLETED,
            queue_position=None,
            current_node=None,
            total_nodes=3,
            completed_nodes=3,
            progress_percent=100.0,
            nodes=[],
            queue_time=old_time,
            start_time=old_time,
            end_time=old_time,
            last_update=old_time,
            outputs=[],
            error_message=None,
            failed_node=None
        )
        
        self.executor.workflow_states[old_workflow_id] = old_state
        
        # Create recent workflow
        recent_workflow_id = "recent_workflow_456"
        recent_state = ComfyUIWorkflowState(
            workflow_id=recent_workflow_id,
            workflow_name="Recent",
            prompt_id="",
            ssh_connection="ssh -p 40738 root@198.53.64.194",
            workflow_file=self.workflow_file,
            status=WorkflowStatus.EXECUTING,
            queue_position=None,
            current_node=None,
            total_nodes=3,
            completed_nodes=1,
            progress_percent=33.3,
            nodes=[],
            queue_time=datetime.now(),
            start_time=datetime.now(),
            end_time=None,
            last_update=datetime.now(),
            outputs=[],
            error_message=None,
            failed_node=None
        )
        
        self.executor.workflow_states[recent_workflow_id] = recent_state
        
        # Cleanup with 1 hour max age
        self.executor.cleanup_completed_workflows(max_age_seconds=3600)
        
        # Old workflow should be removed
        self.assertIsNone(self.executor.get_workflow_state(old_workflow_id))
        
        # Recent workflow should remain
        self.assertIsNotNone(self.executor.get_workflow_state(recent_workflow_id))
    
    def test_get_executor_singleton(self):
        """Test global executor singleton."""
        executor1 = get_executor()
        executor2 = get_executor()
        
        self.assertIs(executor1, executor2)


if __name__ == '__main__':
    unittest.main()
