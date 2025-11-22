"""
Workflow State Manager
Manages persistent state for workflow execution to enable state restoration on page refresh.
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from threading import Lock

logger = logging.getLogger(__name__)

# Default state file location
DEFAULT_STATE_FILE = "/tmp/workflow_state.json"


class WorkflowStateManager:
    """Manages persistent workflow state for UI restoration."""
    
    def __init__(self, state_file: str = DEFAULT_STATE_FILE):
        """
        Initialize the workflow state manager.
        
        Args:
            state_file: Path to the JSON file for storing workflow state
        """
        self.state_file = state_file
        self._lock = Lock()
        logger.info(f"WorkflowStateManager initialized with state file: {state_file}")
    
    def save_state(self, state: Dict[str, Any]) -> bool:
        """
        Save workflow state to file.
        
        Args:
            state: Dictionary containing workflow state
                Expected keys:
                - workflow_id: Unique identifier for the workflow
                - status: Current status (running, completed, failed, cancelled)
                - current_step: Index of current step being executed
                - steps: List of step configurations
                - start_time: ISO format timestamp when workflow started
                - last_update: ISO format timestamp of last update
                
        Returns:
            True if save was successful, False otherwise
        """
        with self._lock:
            try:
                # Add metadata
                state['last_update'] = datetime.now().isoformat()
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
                
                # Write state to file atomically
                temp_file = f"{self.state_file}.tmp"
                with open(temp_file, 'w') as f:
                    json.dump(state, f, indent=2)
                
                # Atomic rename
                os.replace(temp_file, self.state_file)
                
                logger.debug(f"Workflow state saved: {state.get('workflow_id')} - {state.get('status')}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to save workflow state: {e}")
                return False
    
    def load_state(self) -> Optional[Dict[str, Any]]:
        """
        Load workflow state from file.
        
        Returns:
            Dictionary containing workflow state, or None if no state exists
        """
        with self._lock:
            try:
                if not os.path.exists(self.state_file):
                    logger.debug("No workflow state file exists")
                    return None
                
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                logger.debug(f"Workflow state loaded: {state.get('workflow_id')} - {state.get('status')}")
                return state
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in workflow state file: {e}")
                # Remove corrupted file
                self._remove_state_file()
                return None
                
            except Exception as e:
                logger.error(f"Failed to load workflow state: {e}")
                return None
    
    def clear_state(self) -> bool:
        """
        Clear workflow state by removing the state file.
        
        Returns:
            True if clear was successful, False otherwise
        """
        with self._lock:
            return self._remove_state_file()
    
    def _remove_state_file(self) -> bool:
        """Remove the state file if it exists."""
        try:
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
                logger.info("Workflow state file removed")
            return True
        except Exception as e:
            logger.error(f"Failed to remove workflow state file: {e}")
            return False
    
    def is_active(self) -> bool:
        """
        Check if there is an active workflow.
        
        Returns:
            True if there is a workflow in 'running' status, False otherwise
        """
        state = self.load_state()
        if not state:
            return False
        
        status = state.get('status', '')
        return status == 'running'
    
    def update_step_progress(self, step_index: int, step_status: str, step_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update the progress of a specific step.
        
        Args:
            step_index: Index of the step to update
            step_status: Status of the step (in_progress, completed, failed)
            step_data: Optional additional data for the step
            
        Returns:
            True if update was successful, False otherwise
        """
        state = self.load_state()
        if not state:
            logger.warning("Cannot update step progress: no active workflow state")
            return False
        
        # Update current step
        state['current_step'] = step_index
        
        # Update steps array if it exists
        if 'steps' in state and isinstance(state['steps'], list):
            if 0 <= step_index < len(state['steps']):
                state['steps'][step_index]['status'] = step_status
                if step_data:
                    state['steps'][step_index]['data'] = step_data
        
        return self.save_state(state)
    
    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current workflow state.
        
        Returns:
            Dictionary with state summary including workflow_id, status, and progress
        """
        state = self.load_state()
        if not state:
            return {
                'active': False,
                'workflow_id': None,
                'status': None
            }
        
        total_steps = len(state.get('steps', []))
        current_step = state.get('current_step', 0)
        
        return {
            'active': state.get('status') == 'running',
            'workflow_id': state.get('workflow_id'),
            'status': state.get('status'),
            'current_step': current_step,
            'total_steps': total_steps,
            'progress_percent': (current_step / total_steps * 100) if total_steps > 0 else 0,
            'start_time': state.get('start_time'),
            'last_update': state.get('last_update')
        }


# Global instance
_workflow_state_manager = None


def get_workflow_state_manager() -> WorkflowStateManager:
    """
    Get or create the global workflow state manager instance.
    
    Returns:
        WorkflowStateManager instance
    """
    global _workflow_state_manager
    if _workflow_state_manager is None:
        _workflow_state_manager = WorkflowStateManager()
    return _workflow_state_manager
