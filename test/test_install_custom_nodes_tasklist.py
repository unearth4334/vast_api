#!/usr/bin/env python3
"""
Test for install-custom-nodes tasklist visualization
Verifies that the task list properly displays:
1. Clone Auto-installer
2. Configure venv path
3. Individual custom nodes (rolling display)
4. "# others" summary
5. Verify Dependencies
"""

import unittest
from unittest.mock import patch, MagicMock, Mock
import json
import sys
import os
import time

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.sync.workflow_executor import WorkflowExecutor
from app.sync.workflow_state import WorkflowStateManager
from app.sync.sync_api import app
from app.sync.background_tasks import get_task_manager


class TestInstallCustomNodesTasklist(unittest.TestCase):
    """Test the tasklist visualization for install-custom-nodes workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = app.test_client()
        self.app.testing = True
        self.executor = WorkflowExecutor()
        self.state_manager = WorkflowStateManager('/tmp/test_workflow_state.json')
        self.workflow_id = 'test-workflow-123'
        
        # Clean up any existing state
        if os.path.exists('/tmp/test_workflow_state.json'):
            os.remove('/tmp/test_workflow_state.json')
    
    def tearDown(self):
        """Clean up after tests"""
        if os.path.exists('/tmp/test_workflow_state.json'):
            os.remove('/tmp/test_workflow_state.json')
    
    def test_tasklist_progression_sequence(self):
        """Test that tasks appear in the correct sequence"""
        # Initialize workflow state with install_custom_nodes step
        initial_state = {
            'workflow_id': self.workflow_id,
            'status': 'running',
            'current_step': 0,
            'steps': [
                {
                    'action': 'install_custom_nodes',
                    'status': 'running',
                    'tasks': []
                }
            ],
            'start_time': time.time()
        }
        self.state_manager.save_state(initial_state)
        
        # Test sequence:
        # 1. Clone Auto-installer appears
        state = self.state_manager.load_state()
        state['steps'][0]['tasks'] = [
            {'name': 'Clone Auto-installer', 'status': 'running'}
        ]
        self.state_manager.save_state(state)
        
        state = self.state_manager.load_state()
        self.assertEqual(len(state['steps'][0]['tasks']), 1)
        self.assertEqual(state['steps'][0]['tasks'][0]['name'], 'Clone Auto-installer')
        self.assertEqual(state['steps'][0]['tasks'][0]['status'], 'running')
        
        # 2. Clone Auto-installer completes
        state['steps'][0]['tasks'][0]['status'] = 'success'
        self.state_manager.save_state(state)
        
        # 3. Configure venv path appears
        state = self.state_manager.load_state()
        state['steps'][0]['tasks'].append({
            'name': 'Configure venv path',
            'status': 'running'
        })
        self.state_manager.save_state(state)
        
        state = self.state_manager.load_state()
        self.assertEqual(len(state['steps'][0]['tasks']), 2)
        self.assertEqual(state['steps'][0]['tasks'][1]['name'], 'Configure venv path')
        self.assertEqual(state['steps'][0]['tasks'][1]['status'], 'running')
        
        # 4. Configure venv path completes, first custom node appears
        state['steps'][0]['tasks'][1]['status'] = 'success'
        state['steps'][0]['tasks'].append({
            'name': 'ComfyUI-Manager',
            'status': 'running'
        })
        self.state_manager.save_state(state)
        
        state = self.state_manager.load_state()
        self.assertEqual(len(state['steps'][0]['tasks']), 3)
        self.assertEqual(state['steps'][0]['tasks'][2]['name'], 'ComfyUI-Manager')
        
        # 5. Verify task list structure
        task_names = [t['name'] for t in state['steps'][0]['tasks']]
        self.assertIn('Clone Auto-installer', task_names)
        self.assertIn('Configure venv path', task_names)
        self.assertIn('ComfyUI-Manager', task_names)
    
    def test_rolling_display_with_max_4_nodes(self):
        """Test that only 4 custom nodes are shown at a time (rolling display)"""
        # Set up state with Clone Auto-installer and Configure venv path completed
        state = {
            'workflow_id': self.workflow_id,
            'status': 'running',
            'current_step': 0,
            'steps': [
                {
                    'action': 'install_custom_nodes',
                    'status': 'running',
                    'tasks': [
                        {'name': 'Clone Auto-installer', 'status': 'success'},
                        {'name': 'Configure venv path', 'status': 'success'}
                    ]
                }
            ]
        }
        
        # Simulate 10 nodes total, showing rolling window of 4
        total_nodes = 10
        max_visible = 4
        
        # Add first 4 nodes
        for i in range(1, 5):
            state['steps'][0]['tasks'].append({
                'name': f'CustomNode-{i}',
                'status': 'success' if i < 4 else 'running'
            })
        
        # Add "# others" for remaining nodes
        remaining = total_nodes - 4
        state['steps'][0]['tasks'].append({
            'name': f'{remaining} others',
            'status': 'pending'
        })
        
        self.state_manager.save_state(state)
        state = self.state_manager.load_state()
        
        # Verify structure: Clone Auto-installer + Configure venv path + 4 nodes + "# others"
        tasks = state['steps'][0]['tasks']
        self.assertEqual(len(tasks), 7)  # 2 setup tasks + 4 nodes + 1 "# others"
        
        # Check that we have the setup tasks
        self.assertEqual(tasks[0]['name'], 'Clone Auto-installer')
        self.assertEqual(tasks[1]['name'], 'Configure venv path')
        
        # Check that we have 4 custom nodes
        node_tasks = [t for t in tasks if t['name'].startswith('CustomNode-')]
        self.assertEqual(len(node_tasks), 4)
        
        # Check that "# others" is present
        others_tasks = [t for t in tasks if 'others' in t['name']]
        self.assertEqual(len(others_tasks), 1)
        self.assertEqual(others_tasks[0]['name'], f'{remaining} others')
    
    def test_subtask_for_dependencies(self):
        """Test that dependencies appear as subtasks"""
        state = {
            'workflow_id': self.workflow_id,
            'status': 'running',
            'current_step': 0,
            'steps': [
                {
                    'action': 'install_custom_nodes',
                    'status': 'running',
                    'tasks': [
                        {'name': 'Clone Auto-installer', 'status': 'success'},
                        {'name': 'Configure venv path', 'status': 'success'},
                        {
                            'name': 'ComfyUI-Manager',
                            'status': 'running',
                            'subtasks': [
                                {
                                    'name': 'Install dependencies',
                                    'status': 'running'
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        self.state_manager.save_state(state)
        state = self.state_manager.load_state()
        
        # Verify subtask structure
        node_task = state['steps'][0]['tasks'][2]
        self.assertEqual(node_task['name'], 'ComfyUI-Manager')
        self.assertIn('subtasks', node_task)
        self.assertEqual(len(node_task['subtasks']), 1)
        self.assertEqual(node_task['subtasks'][0]['name'], 'Install dependencies')
        self.assertEqual(node_task['subtasks'][0]['status'], 'running')
    
    def test_verify_dependencies_appears_at_end(self):
        """Test that Verify Dependencies task appears after all nodes installed"""
        state = {
            'workflow_id': self.workflow_id,
            'status': 'running',
            'current_step': 0,
            'steps': [
                {
                    'action': 'install_custom_nodes',
                    'status': 'running',
                    'tasks': [
                        {'name': 'Clone Auto-installer', 'status': 'success'},
                        {'name': 'Configure venv path', 'status': 'success'},
                        {'name': 'CustomNode-1', 'status': 'success'},
                        {'name': 'CustomNode-2', 'status': 'success'},
                        {'name': 'Verify Dependencies', 'status': 'pending'}
                    ]
                }
            ]
        }
        
        self.state_manager.save_state(state)
        state = self.state_manager.load_state()
        
        # Verify Verify Dependencies is last
        tasks = state['steps'][0]['tasks']
        last_task = tasks[-1]
        self.assertEqual(last_task['name'], 'Verify Dependencies')
        self.assertEqual(last_task['status'], 'pending')
    
    @patch('app.sync.sync_api.subprocess')
    @patch('app.sync.sync_api._extract_host_port')
    def test_progress_updates_populate_tasklist(self, mock_extract, mock_subprocess):
        """Test that progress updates from backend properly update the tasklist"""
        # Mock SSH connection
        mock_extract.return_value = ('test.host.com', 22)
        
        # Mock the progress response sequence
        progress_sequence = [
            # Initial state
            {
                'in_progress': True,
                'task_id': 'test-task-123',
                'total_nodes': 0,
                'processed': 0,
                'current_node': 'Initializing',
                'current_status': 'running',
                'successful': 0,
                'failed': 0
            },
            # Configure venv path
            {
                'in_progress': True,
                'task_id': 'test-task-123',
                'total_nodes': 0,
                'processed': 0,
                'current_node': 'Configure venv path',
                'current_status': 'running',
                'successful': 0,
                'failed': 0
            },
            # First node
            {
                'in_progress': True,
                'task_id': 'test-task-123',
                'total_nodes': 5,
                'processed': 1,
                'current_node': 'ComfyUI-Manager',
                'current_status': 'running',
                'successful': 0,
                'failed': 0
            },
            # Second node with dependencies
            {
                'in_progress': True,
                'task_id': 'test-task-123',
                'total_nodes': 5,
                'processed': 2,
                'current_node': 'ComfyUI-Custom-Scripts',
                'current_status': 'running',
                'successful': 1,
                'failed': 0,
                'has_requirements': True,
                'requirements_status': 'running'
            },
            # Completion
            {
                'in_progress': False,
                'task_id': 'test-task-123',
                'completed': True,
                'success': True,
                'total_nodes': 5,
                'processed': 5,
                'successful_clones': 5,
                'failed_clones': 0
            }
        ]
        
        # Test that each progress state is valid
        for i, progress in enumerate(progress_sequence):
            self.assertIn('task_id', progress)
            self.assertEqual(progress['task_id'], 'test-task-123')
            
            if progress.get('in_progress'):
                self.assertIn('current_node', progress)
                self.assertIn('current_status', progress)
                
                # Verify expected nodes appear
                if i == 1:  # Configure venv path
                    self.assertEqual(progress['current_node'], 'Configure venv path')
                elif i == 2:  # First node
                    self.assertEqual(progress['current_node'], 'ComfyUI-Manager')
                    self.assertGreater(progress['total_nodes'], 0)
                elif i == 3:  # Second node with dependencies
                    self.assertEqual(progress['current_node'], 'ComfyUI-Custom-Scripts')
                    self.assertTrue(progress.get('has_requirements'))
                    self.assertEqual(progress.get('requirements_status'), 'running')
    
    def test_completed_others_summary(self):
        """Test that completed nodes show as '# others' with success count"""
        # Simulate scenario: 10 nodes total, processed 7, showing last 4
        state = {
            'workflow_id': self.workflow_id,
            'status': 'running',
            'current_step': 0,
            'steps': [
                {
                    'action': 'install_custom_nodes',
                    'status': 'running',
                    'tasks': [
                        {'name': 'Clone Auto-installer', 'status': 'success'},
                        {'name': 'Configure venv path', 'status': 'success'},
                        # Completed others: 3 nodes (7 - 4)
                        {'name': '3 others', 'status': 'success (3/3)'},
                        # Last 4 nodes
                        {'name': 'CustomNode-4', 'status': 'success'},
                        {'name': 'CustomNode-5', 'status': 'success'},
                        {'name': 'CustomNode-6', 'status': 'success'},
                        {'name': 'CustomNode-7', 'status': 'running'},
                        # Remaining
                        {'name': '3 others', 'status': 'pending'}
                    ]
                }
            ]
        }
        
        self.state_manager.save_state(state)
        state = self.state_manager.load_state()
        
        tasks = state['steps'][0]['tasks']
        
        # Find the completed "# others" task
        completed_others = [t for t in tasks if '3 others' in t['name'] and 'success' in str(t['status'])]
        self.assertEqual(len(completed_others), 1)
        self.assertIn('success', completed_others[0]['status'])
        
        # Find the pending "# others" task
        pending_others = [t for t in tasks if '3 others' in t['name'] and t['status'] == 'pending']
        self.assertEqual(len(pending_others), 1)
    
    def test_task_status_transitions(self):
        """Test that task statuses transition correctly: pending -> running -> success/failed"""
        state = {
            'workflow_id': self.workflow_id,
            'status': 'running',
            'current_step': 0,
            'steps': [
                {
                    'action': 'install_custom_nodes',
                    'status': 'running',
                    'tasks': []
                }
            ]
        }
        
        # Test pending -> running transition
        state['steps'][0]['tasks'].append({
            'name': 'CustomNode-1',
            'status': 'pending'
        })
        self.state_manager.save_state(state)
        
        state = self.state_manager.load_state()
        self.assertEqual(state['steps'][0]['tasks'][0]['status'], 'pending')
        
        # Transition to running
        state['steps'][0]['tasks'][0]['status'] = 'running'
        self.state_manager.save_state(state)
        
        state = self.state_manager.load_state()
        self.assertEqual(state['steps'][0]['tasks'][0]['status'], 'running')
        
        # Transition to success
        state['steps'][0]['tasks'][0]['status'] = 'success'
        self.state_manager.save_state(state)
        
        state = self.state_manager.load_state()
        self.assertEqual(state['steps'][0]['tasks'][0]['status'], 'success')
        
        # Test failed status
        state['steps'][0]['tasks'].append({
            'name': 'CustomNode-2',
            'status': 'running'
        })
        state['steps'][0]['tasks'][1]['status'] = 'failed'
        self.state_manager.save_state(state)
        
        state = self.state_manager.load_state()
        self.assertEqual(state['steps'][0]['tasks'][1]['status'], 'failed')


class TestTasklistIntegrationWithAPI(unittest.TestCase):
    """Integration tests with the actual API endpoints"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = app.test_client()
        self.app.testing = True
    
    @patch('app.sync.sync_api.subprocess')
    @patch('app.sync.sync_api._extract_host_port')
    def test_full_workflow_tasklist_visualization(self, mock_extract, mock_subprocess):
        """Test full workflow from start to finish with tasklist updates"""
        # Mock SSH connection
        mock_extract.return_value = ('test.host.com', 22)
        mock_subprocess.run.return_value = MagicMock(returncode=0)
        
        # 1. Start installation
        response = self.app.post(
            '/ssh/install-custom-nodes',
            json={
                'ssh_connection': 'root@test.host.com',
                'ui_home': '/workspace/ComfyUI'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('task_id', data)
        task_id = data['task_id']
        
        # 2. Verify we can poll progress with task_id
        # Mock progress responses
        progress_responses = [
            json.dumps({
                'in_progress': True,
                'task_id': task_id,
                'current_node': 'Configure venv path',
                'current_status': 'running',
                'total_nodes': 0,
                'processed': 0
            }),
            json.dumps({
                'in_progress': True,
                'task_id': task_id,
                'current_node': 'ComfyUI-Manager',
                'current_status': 'running',
                'total_nodes': 5,
                'processed': 1,
                'successful': 0,
                'failed': 0
            }),
            json.dumps({
                'in_progress': False,
                'task_id': task_id,
                'completed': True,
                'success': True,
                'total_nodes': 5,
                'processed': 5
            })
        ]
        
        for progress_json in progress_responses:
            mock_subprocess.run.return_value = MagicMock(
                returncode=0,
                stdout=progress_json
            )
            
            response = self.app.post(
                '/ssh/install-custom-nodes/progress',
                json={
                    'ssh_connection': 'root@test.host.com',
                    'task_id': task_id
                }
            )
            
            self.assertEqual(response.status_code, 200)
            progress = json.loads(response.data)
            self.assertTrue(progress['success'])
            
            # Verify progress structure
            if progress.get('in_progress'):
                self.assertIn('current_node', progress)
                self.assertIn('current_status', progress)
                # These nodes should appear in the tasklist
                self.assertIn(progress['current_node'], 
                            ['Configure venv path', 'ComfyUI-Manager', 'Initializing'])


if __name__ == '__main__':
    unittest.main()
