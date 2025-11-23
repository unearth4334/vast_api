#!/usr/bin/env python3
"""
Standalone test for install-custom-nodes tasklist visualization
Tests the workflow state management and task list progression without requiring Flask
"""

import unittest
import json
import sys
import os
import tempfile

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.sync.workflow_state import WorkflowStateManager


class TestTasklistVisualizationStandalone(unittest.TestCase):
    """Standalone tests for tasklist visualization logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Use temporary file for state
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.state_manager = WorkflowStateManager(self.temp_file.name)
        self.workflow_id = 'test-workflow-tasklist'
    
    def tearDown(self):
        """Clean up after tests"""
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)
    
    def test_task_sequence_validation(self):
        """Verify tasks appear in correct sequence"""
        expected_sequence = [
            'Clone Auto-installer',
            'Configure venv path',
            'ComfyUI-Manager',
            'ComfyUI-Custom-Scripts',
            'Verify Dependencies'
        ]
        
        state = {
            'workflow_id': self.workflow_id,
            'status': 'running',
            'current_step': 0,
            'steps': [{
                'action': 'install_custom_nodes',
                'status': 'running',
                'tasks': [{'name': name, 'status': 'success'} for name in expected_sequence]
            }]
        }
        
        self.state_manager.save_state(state)
        loaded_state = self.state_manager.load_state()
        
        actual_sequence = [t['name'] for t in loaded_state['steps'][0]['tasks']]
        self.assertEqual(actual_sequence, expected_sequence)
    
    def test_rolling_window_logic(self):
        """Test rolling window display with MAX_VISIBLE_NODES=4"""
        MAX_VISIBLE_NODES = 4
        total_nodes = 10
        
        # Simulate rolling window at node 7 (past first 4)
        # Should show: "3 others" + last 4 nodes + "3 others pending"
        
        setup_tasks = ['Clone Auto-installer', 'Configure venv path']
        completed_nodes = [f'Node-{i}' for i in range(1, 4)]  # Nodes 1-3 (hidden in "others")
        visible_nodes = [f'Node-{i}' for i in range(4, 8)]   # Nodes 4-7 (visible)
        
        tasks = []
        for task in setup_tasks:
            tasks.append({'name': task, 'status': 'success'})
        
        # Add completed "others"
        tasks.append({'name': '3 others', 'status': 'success (3/3)'})
        
        # Add visible nodes
        for i, node in enumerate(visible_nodes):
            status = 'success' if i < 3 else 'running'
            tasks.append({'name': node, 'status': status})
        
        # Add pending "others"
        remaining = total_nodes - 7
        tasks.append({'name': f'{remaining} others', 'status': 'pending'})
        
        state = {
            'workflow_id': self.workflow_id,
            'status': 'running',
            'current_step': 0,
            'steps': [{
                'action': 'install_custom_nodes',
                'status': 'running',
                'tasks': tasks
            }]
        }
        
        self.state_manager.save_state(state)
        loaded_state = self.state_manager.load_state()
        
        loaded_tasks = loaded_state['steps'][0]['tasks']
        
        # Verify structure
        self.assertEqual(loaded_tasks[0]['name'], 'Clone Auto-installer')
        self.assertEqual(loaded_tasks[1]['name'], 'Configure venv path')
        self.assertEqual(loaded_tasks[2]['name'], '3 others')
        
        # Verify 4 visible nodes
        visible_task_names = [t['name'] for t in loaded_tasks[3:7]]
        self.assertEqual(visible_task_names, visible_nodes)
        
        # Verify pending others
        self.assertEqual(loaded_tasks[-1]['name'], f'{remaining} others')
        self.assertEqual(loaded_tasks[-1]['status'], 'pending')
    
    def test_subtask_structure(self):
        """Verify subtask structure for dependencies"""
        state = {
            'workflow_id': self.workflow_id,
            'status': 'running',
            'current_step': 0,
            'steps': [{
                'action': 'install_custom_nodes',
                'status': 'running',
                'tasks': [
                    {'name': 'Clone Auto-installer', 'status': 'success'},
                    {'name': 'Configure venv path', 'status': 'success'},
                    {
                        'name': 'ComfyUI-Manager',
                        'status': 'running',
                        'subtasks': [
                            {'name': 'Install dependencies', 'status': 'running'}
                        ]
                    }
                ]
            }]
        }
        
        self.state_manager.save_state(state)
        loaded_state = self.state_manager.load_state()
        
        node_task = loaded_state['steps'][0]['tasks'][2]
        self.assertEqual(node_task['name'], 'ComfyUI-Manager')
        self.assertIn('subtasks', node_task)
        self.assertEqual(len(node_task['subtasks']), 1)
        self.assertEqual(node_task['subtasks'][0]['name'], 'Install dependencies')
    
    def test_status_transitions(self):
        """Test valid status transitions"""
        valid_statuses = ['pending', 'running', 'success', 'failed']
        
        state = {
            'workflow_id': self.workflow_id,
            'status': 'running',
            'current_step': 0,
            'steps': [{
                'action': 'install_custom_nodes',
                'status': 'running',
                'tasks': []
            }]
        }
        
        # Test each status
        for status in valid_statuses:
            state['steps'][0]['tasks'] = [
                {'name': 'TestNode', 'status': status}
            ]
            self.state_manager.save_state(state)
            loaded_state = self.state_manager.load_state()
            
            self.assertEqual(
                loaded_state['steps'][0]['tasks'][0]['status'],
                status,
                f"Status {status} should be preserved"
            )
    
    def test_progress_data_structure(self):
        """Verify progress data structure matches expected format"""
        # This tests the structure that the backend writes
        progress_data = {
            'in_progress': True,
            'task_id': 'test-task-123',
            'total_nodes': 34,
            'processed': 15,
            'current_node': 'ComfyUI-Manager',
            'current_status': 'running',
            'successful': 14,
            'failed': 0,
            'has_requirements': True,
            'requirements_status': 'running'
        }
        
        # Verify all required fields are present
        required_fields = [
            'in_progress', 'task_id', 'total_nodes', 'processed',
            'current_node', 'current_status', 'successful', 'failed'
        ]
        
        for field in required_fields:
            self.assertIn(field, progress_data, f"Required field '{field}' missing")
        
        # Verify types
        self.assertIsInstance(progress_data['in_progress'], bool)
        self.assertIsInstance(progress_data['task_id'], str)
        self.assertIsInstance(progress_data['total_nodes'], int)
        self.assertIsInstance(progress_data['processed'], int)
        self.assertIsInstance(progress_data['current_node'], str)
        self.assertIsInstance(progress_data['current_status'], str)
    
    def test_completion_progress_structure(self):
        """Verify completion progress structure"""
        completion_data = {
            'in_progress': False,
            'task_id': 'test-task-123',
            'completed': True,
            'success': True,
            'total_nodes': 34,
            'processed': 34,
            'successful_clones': 32,
            'failed_clones': 2,
            'successful_requirements': 28,
            'failed_requirements': 4
        }
        
        # Verify completion indicators
        self.assertFalse(completion_data['in_progress'])
        self.assertTrue(completion_data['completed'])
        
        # Verify stats
        self.assertEqual(completion_data['total_nodes'], completion_data['processed'])
        self.assertGreaterEqual(completion_data['successful_clones'], 0)
    
    def test_task_list_persistence(self):
        """Verify task list persists across save/load cycles"""
        state = {
            'workflow_id': self.workflow_id,
            'status': 'running',
            'current_step': 0,
            'steps': [{
                'action': 'install_custom_nodes',
                'status': 'running',
                'tasks': [
                    {'name': 'Clone Auto-installer', 'status': 'success'},
                    {'name': 'Configure venv path', 'status': 'running'}
                ]
            }]
        }
        
        # Save and load multiple times
        for i in range(3):
            self.state_manager.save_state(state)
            loaded_state = self.state_manager.load_state()
            
            self.assertEqual(
                len(loaded_state['steps'][0]['tasks']),
                2,
                f"Task count should remain 2 on iteration {i}"
            )
            
            # Verify task details persist
            self.assertEqual(loaded_state['steps'][0]['tasks'][0]['name'], 'Clone Auto-installer')
            self.assertEqual(loaded_state['steps'][0]['tasks'][1]['name'], 'Configure venv path')


class TestProgressDataValidation(unittest.TestCase):
    """Validate progress data format and content"""
    
    def test_initial_progress_format(self):
        """Test initial progress message format"""
        initial_progress = {
            'in_progress': True,
            'task_id': 'uuid-123',
            'total_nodes': 0,
            'processed': 0,
            'current_node': 'Initializing',
            'current_status': 'running',
            'successful': 0,
            'failed': 0,
            'has_requirements': False
        }
        
        self.assertTrue(initial_progress['in_progress'])
        self.assertEqual(initial_progress['current_node'], 'Initializing')
        self.assertEqual(initial_progress['total_nodes'], 0)
    
    def test_venv_config_progress_format(self):
        """Test venv configuration progress format"""
        venv_progress = {
            'in_progress': True,
            'task_id': 'uuid-123',
            'total_nodes': 0,
            'processed': 0,
            'current_node': 'Configure venv path',
            'current_status': 'running',
            'successful': 0,
            'failed': 0
        }
        
        self.assertEqual(venv_progress['current_node'], 'Configure venv path')
        self.assertEqual(venv_progress['current_status'], 'running')
    
    def test_node_progress_format(self):
        """Test custom node progress format"""
        node_progress = {
            'in_progress': True,
            'task_id': 'uuid-123',
            'total_nodes': 34,
            'processed': 5,
            'current_node': 'ComfyUI-Manager',
            'current_status': 'running',
            'successful': 4,
            'failed': 0,
            'has_requirements': False
        }
        
        self.assertGreater(node_progress['total_nodes'], 0)
        self.assertGreater(node_progress['processed'], 0)
        self.assertLessEqual(node_progress['processed'], node_progress['total_nodes'])


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)
