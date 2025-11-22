"""
Test workflow state API endpoints
"""

import os
import json
import tempfile
import pytest

# Import the Flask app
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.sync.sync_api import app
from app.sync.workflow_state import get_workflow_state_manager


class TestWorkflowStateAPI:
    """Test cases for workflow state API endpoints"""
    
    def setup_method(self):
        """Setup test fixtures"""
        # Setup Flask test client
        app.config['TESTING'] = True
        self.client = app.test_client()
        
        # Use a temporary state file for testing
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.state_file = self.temp_file.name
        
        # Replace the global manager with test manager
        from app.sync import workflow_state
        workflow_state._workflow_state_manager = workflow_state.WorkflowStateManager(self.state_file)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        # Remove temporary state file
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
    
    def test_get_workflow_state_no_state(self):
        """Test GET /workflow/state when no state exists"""
        response = self.client.get('/workflow/state')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['active'] is False
        assert data['state'] is None
    
    def test_post_workflow_state(self):
        """Test POST /workflow/state to save state"""
        test_state = {
            'workflow_id': 'test_api_123',
            'status': 'running',
            'current_step': 1,
            'steps': [
                {'action': 'test_ssh', 'status': 'completed'},
                {'action': 'sync_instance', 'status': 'in_progress'}
            ],
            'start_time': '2024-01-01T00:00:00Z'
        }
        
        response = self.client.post(
            '/workflow/state',
            data=json.dumps(test_state),
            content_type='application/json'
        )
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['message'] == 'Workflow state saved'
    
    def test_get_workflow_state_with_state(self):
        """Test GET /workflow/state when state exists"""
        # First save a state
        test_state = {
            'workflow_id': 'test_get_123',
            'status': 'running',
            'current_step': 0,
            'steps': [
                {'action': 'test_ssh', 'status': 'in_progress'}
            ],
            'start_time': '2024-01-01T00:00:00Z'
        }
        
        self.client.post(
            '/workflow/state',
            data=json.dumps(test_state),
            content_type='application/json'
        )
        
        # Now retrieve it
        response = self.client.get('/workflow/state')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['active'] is True
        assert data['state'] is not None
        assert data['state']['workflow_id'] == 'test_get_123'
        assert data['state']['status'] == 'running'
    
    def test_delete_workflow_state(self):
        """Test DELETE /workflow/state to clear state"""
        # First save a state
        test_state = {
            'workflow_id': 'test_delete_123',
            'status': 'running',
            'current_step': 0,
            'steps': [],
            'start_time': '2024-01-01T00:00:00Z'
        }
        
        self.client.post(
            '/workflow/state',
            data=json.dumps(test_state),
            content_type='application/json'
        )
        
        # Delete the state
        response = self.client.delete('/workflow/state')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['message'] == 'Workflow state cleared'
        
        # Verify state is cleared
        response = self.client.get('/workflow/state')
        data = json.loads(response.data)
        assert data['active'] is False
        assert data['state'] is None
    
    def test_get_workflow_state_summary(self):
        """Test GET /workflow/state/summary"""
        # Test with no state
        response = self.client.get('/workflow/state/summary')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['summary']['active'] is False
        
        # Save a state
        test_state = {
            'workflow_id': 'test_summary_123',
            'status': 'running',
            'current_step': 2,
            'steps': [
                {'action': 'step1', 'status': 'completed'},
                {'action': 'step2', 'status': 'completed'},
                {'action': 'step3', 'status': 'in_progress'},
                {'action': 'step4', 'status': 'pending'}
            ],
            'start_time': '2024-01-01T00:00:00Z'
        }
        
        self.client.post(
            '/workflow/state',
            data=json.dumps(test_state),
            content_type='application/json'
        )
        
        # Get summary with state
        response = self.client.get('/workflow/state/summary')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['summary']['active'] is True
        assert data['summary']['workflow_id'] == 'test_summary_123'
        assert data['summary']['current_step'] == 2
        assert data['summary']['total_steps'] == 4
        assert data['summary']['progress_percent'] == 75.0  # 3 out of 4 steps (current_step=2 means 0,1,2 completed)
    
    def test_post_workflow_state_no_data(self):
        """Test POST /workflow/state with no data returns error"""
        response = self.client.post(
            '/workflow/state',
            data='',
            content_type='application/json'
        )
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'required' in data['message'].lower()
    
    def test_options_requests(self):
        """Test OPTIONS requests for CORS preflight"""
        # Test GET endpoint
        response = self.client.options('/workflow/state')
        assert response.status_code == 204
        
        # Test summary endpoint
        response = self.client.options('/workflow/state/summary')
        assert response.status_code == 204
    
    def test_workflow_state_lifecycle(self):
        """Test complete workflow state lifecycle"""
        # 1. Start workflow
        initial_state = {
            'workflow_id': 'lifecycle_123',
            'status': 'running',
            'current_step': 0,
            'steps': [
                {'action': 'test_ssh', 'status': 'in_progress'},
                {'action': 'sync_instance', 'status': 'pending'}
            ],
            'start_time': '2024-01-01T00:00:00Z'
        }
        
        response = self.client.post(
            '/workflow/state',
            data=json.dumps(initial_state),
            content_type='application/json'
        )
        assert response.status_code == 200
        
        # 2. Progress through steps
        progress_state = initial_state.copy()
        progress_state['current_step'] = 1
        progress_state['steps'][0]['status'] = 'completed'
        progress_state['steps'][1]['status'] = 'in_progress'
        
        response = self.client.post(
            '/workflow/state',
            data=json.dumps(progress_state),
            content_type='application/json'
        )
        assert response.status_code == 200
        
        # 3. Complete workflow
        complete_state = progress_state.copy()
        complete_state['status'] = 'completed'
        complete_state['steps'][1]['status'] = 'completed'
        
        response = self.client.post(
            '/workflow/state',
            data=json.dumps(complete_state),
            content_type='application/json'
        )
        assert response.status_code == 200
        
        # 4. Verify final state
        response = self.client.get('/workflow/state')
        data = json.loads(response.data)
        assert data['state']['status'] == 'completed'
        assert data['active'] is False  # Not active when completed
        
        # 5. Clear state
        response = self.client.delete('/workflow/state')
        assert response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
