"""
Server-Side Workflow Executor
Executes workflows in background threads, allowing them to continue even if the page is refreshed.
"""

import logging
import threading
import time
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from .workflow_state import get_workflow_state_manager

logger = logging.getLogger(__name__)

# Global workflow executor instance
_workflow_executor = None

# API base URL (assumes running on same host)
API_BASE_URL = "http://localhost:5000"


class WorkflowExecutor:
    """Executes workflows in background threads."""
    
    def __init__(self):
        """Initialize the workflow executor."""
        self.active_workflows: Dict[str, threading.Thread] = {}
        self.stop_flags: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()
        logger.info("WorkflowExecutor initialized")
    
    def start_workflow(self, workflow_id: str, steps: list, ssh_connection: str, step_delay: int = 5) -> bool:
        """
        Start a workflow execution in the background.
        
        Args:
            workflow_id: Unique identifier for the workflow
            steps: List of step configurations
            ssh_connection: SSH connection string
            step_delay: Delay between steps in seconds
            
        Returns:
            True if workflow started successfully, False otherwise
        """
        with self._lock:
            # Check if workflow is already running
            if workflow_id in self.active_workflows and self.active_workflows[workflow_id].is_alive():
                logger.warning(f"Workflow {workflow_id} is already running")
                return False
            
            # Create stop flag for this workflow
            stop_flag = threading.Event()
            self.stop_flags[workflow_id] = stop_flag
            
            # Create and start thread
            thread = threading.Thread(
                target=self._execute_workflow,
                args=(workflow_id, steps, ssh_connection, step_delay, stop_flag),
                daemon=True,
                name=f"workflow-{workflow_id}"
            )
            
            self.active_workflows[workflow_id] = thread
            thread.start()
            
            logger.info(f"Started workflow {workflow_id} in background thread")
            return True
    
    def stop_workflow(self, workflow_id: str) -> bool:
        """
        Stop a running workflow.
        
        Args:
            workflow_id: Unique identifier for the workflow
            
        Returns:
            True if workflow was stopped, False otherwise
        """
        with self._lock:
            if workflow_id in self.stop_flags:
                self.stop_flags[workflow_id].set()
                logger.info(f"Requested stop for workflow {workflow_id}")
                return True
            else:
                logger.warning(f"Workflow {workflow_id} not found")
                return False
    
    def is_workflow_running(self, workflow_id: str) -> bool:
        """
        Check if a workflow is currently running.
        
        Args:
            workflow_id: Unique identifier for the workflow
            
        Returns:
            True if workflow is running, False otherwise
        """
        with self._lock:
            return (workflow_id in self.active_workflows and 
                    self.active_workflows[workflow_id].is_alive())
    
    def _execute_workflow(self, workflow_id: str, steps: list, ssh_connection: str, 
                         step_delay: int, stop_flag: threading.Event):
        """
        Execute workflow steps in sequence (runs in background thread).
        
        Args:
            workflow_id: Unique identifier for the workflow
            steps: List of step configurations
            ssh_connection: SSH connection string
            step_delay: Delay between steps in seconds
            stop_flag: Event to signal workflow should stop
        """
        state_manager = get_workflow_state_manager()
        
        try:
            logger.info(f"Executing workflow {workflow_id} with {len(steps)} steps")
            
            # Initialize workflow state
            state = {
                'workflow_id': workflow_id,
                'status': 'running',
                'current_step': 0,
                'steps': steps,
                'start_time': datetime.now().isoformat(),
                'ssh_connection': ssh_connection
            }
            state_manager.save_state(state)
            
            # Execute each step
            for step_index, step in enumerate(steps):
                # Check if workflow should stop
                if stop_flag.is_set():
                    logger.info(f"Workflow {workflow_id} stopped by user request")
                    state['status'] = 'cancelled'
                    state['current_step'] = step_index
                    state_manager.save_state(state)
                    return
                
                logger.info(f"Executing step {step_index + 1}/{len(steps)}: {step['action']}")
                
                # Update state - step starting
                state['current_step'] = step_index
                state['steps'][step_index]['status'] = 'in_progress'
                state_manager.save_state(state)
                
                # Execute the step
                result = self._execute_step(step, ssh_connection, state_manager, workflow_id, step_index)
                
                # Check if step returned blocking information (3-element tuple)
                if isinstance(result, tuple) and len(result) == 3:
                    success, error_message, block_info = result
                    if not success and block_info and block_info.get('block_reason'):
                        # Step needs user interaction - enter blocked state
                        logger.info(f"Step {step_index + 1} requires user interaction: {block_info.get('block_reason')}")
                        state['status'] = 'blocked'
                        state['steps'][step_index]['status'] = 'blocked'
                        state['steps'][step_index]['error'] = error_message
                        state['block_info'] = block_info
                        state_manager.save_state(state)
                        
                        # Wait for workflow to be resumed (polling for state change)
                        while not stop_flag.is_set():
                            time.sleep(1)
                            current_state = state_manager.load_state()
                            if current_state and current_state.get('status') != 'blocked':
                                # State changed - reload and continue
                                state = current_state
                                if state.get('status') == 'running':
                                    # Retry the failed step
                                    logger.info(f"Workflow resumed, retrying step {step_index + 1}")
                                    state['steps'][step_index]['status'] = 'in_progress'
                                    state_manager.save_state(state)
                                    success, error_message = self._execute_step(step, ssh_connection, state_manager, workflow_id, step_index)
                                    break
                                elif state.get('status') == 'cancelled':
                                    logger.info(f"Workflow {workflow_id} cancelled during blocked state")
                                    return
                                elif state.get('status') == 'failed':
                                    logger.info(f"Workflow {workflow_id} failed during blocked state")
                                    return
                        
                        if stop_flag.is_set():
                            logger.info(f"Workflow {workflow_id} stopped during blocked state")
                            state['status'] = 'cancelled'
                            state_manager.save_state(state)
                            return
                else:
                    # Normal 2-element tuple
                    success, error_message = result
                
                # Update state - step completed or failed
                if success:
                    state['steps'][step_index]['status'] = 'completed'
                    logger.info(f"Step {step_index + 1} completed: {step['action']}")
                else:
                    state['steps'][step_index]['status'] = 'failed'
                    state['steps'][step_index]['error'] = error_message
                    state['status'] = 'failed'
                    state['error_message'] = f"Step {step_index + 1} ({step['action']}) failed: {error_message}"
                    logger.error(f"Step {step_index + 1} failed: {step['action']} - {error_message}")
                    state_manager.save_state(state)
                    return
                
                state_manager.save_state(state)
                
                # Delay before next step (unless it's the last step)
                if step_index < len(steps) - 1:
                    time.sleep(step_delay)
            
            # All steps completed successfully
            state['status'] = 'completed'
            state_manager.save_state(state)
            logger.info(f"Workflow {workflow_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error executing workflow {workflow_id}: {e}", exc_info=True)
            state['status'] = 'failed'
            state_manager.save_state(state)
        finally:
            # Clean up
            with self._lock:
                if workflow_id in self.active_workflows:
                    del self.active_workflows[workflow_id]
                if workflow_id in self.stop_flags:
                    del self.stop_flags[workflow_id]
    
    def _execute_step(self, step: Dict[str, Any], ssh_connection: str, state_manager, workflow_id: str, step_index: int) -> tuple:
        """
        Execute a single workflow step by calling actual SSH API endpoints.
        
        Args:
            step: Step configuration with 'action' and other parameters
            ssh_connection: SSH connection string
            state_manager: WorkflowStateManager for progress updates
            workflow_id: ID of the workflow
            step_index: Index of current step
            
        Returns:
            Tuple of (success: bool, error_message: str or None)
        """
        action = step.get('action')
        
        try:
            # Map action to execution logic
            if action == 'test_ssh':
                return self._execute_test_ssh(ssh_connection)
            elif action == 'setup_civitdl':
                # Consolidated: Setup and Test CivitDL
                return self._execute_setup_civitdl_consolidated(ssh_connection, state_manager, workflow_id, step_index)
            elif action == 'set_ui_home':
                # Consolidated: Set and Read UI_HOME
                ui_home = step.get('ui_home', '/workspace/ComfyUI')
                return self._execute_set_ui_home_consolidated(ssh_connection, ui_home, state_manager, workflow_id, step_index)
            elif action == 'sync_instance':
                return self._execute_sync_instance(ssh_connection)
            elif action == 'install_custom_nodes':
                ui_home = step.get('ui_home', '/workspace/ComfyUI')
                return self._execute_install_custom_nodes(ssh_connection, ui_home, state_manager, workflow_id, step_index)
            elif action == 'reboot_instance':
                instance_id = step.get('instance_id')
                return self._execute_reboot_instance_with_tasks(instance_id, state_manager, workflow_id, step_index)
            else:
                logger.warning(f"Unknown action: {action}")
                return False, f"Unknown action: {action}"
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error executing step {action}: {error_msg}", exc_info=True)
            return False, f"Exception: {error_msg}"
    
    def _update_task_status(self, state_manager, workflow_id: str, step_index: int, task_name: str, status: str, note: str = None):
        """
        Update the status of a specific task within a workflow step.
        
        Args:
            state_manager: WorkflowStateManager instance
            workflow_id: ID of the workflow
            step_index: Index of the step
            task_name: Name of the task
            status: Status of the task (pending, running, success, failed)
            note: Optional completion note
        """
        state = state_manager.load_state()
        if not state or step_index >= len(state.get('steps', [])):
            return
        
        # Initialize tasks list if not present
        if 'tasks' not in state['steps'][step_index]:
            state['steps'][step_index]['tasks'] = []
        
        # Find or create task entry
        tasks = state['steps'][step_index]['tasks']
        task_entry = None
        for task in tasks:
            if task['name'] == task_name:
                task_entry = task
                break
        
        if not task_entry:
            task_entry = {'name': task_name, 'status': status}
            tasks.append(task_entry)
        else:
            task_entry['status'] = status
        
        if note:
            task_entry['note'] = note
        
        state_manager.save_state(state)
    
    def _set_completion_note(self, state_manager, workflow_id: str, step_index: int, note: str):
        """
        Set a completion note for a workflow step.
        
        Args:
            state_manager: WorkflowStateManager instance
            workflow_id: ID of the workflow
            step_index: Index of the step
            note: Completion note text
        """
        state = state_manager.load_state()
        if not state or step_index >= len(state.get('steps', [])):
            return
        
        state['steps'][step_index]['completion_note'] = note
        state_manager.save_state(state)
    
    def _parse_ssh_connection(self, ssh_connection: str) -> tuple:
        """Parse SSH connection string to extract host and port."""
        try:
            # Format: ssh -p PORT root@HOST -L 8080:localhost:8080
            import re
            port_match = re.search(r'-p\s+(\d+)', ssh_connection)
            host_match = re.search(r'root@([\d\.]+)', ssh_connection)
            
            port = port_match.group(1) if port_match else '22'
            host = host_match.group(1) if host_match else None
            
            return host, port
        except Exception as e:
            logger.error(f"Error parsing SSH connection: {e}")
            return None, None
    
    def _execute_test_ssh(self, ssh_connection: str) -> tuple:
        """Test SSH connection by calling /ssh/test API endpoint."""
        logger.info("Testing SSH connection...")
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/ssh/test",
                json={'ssh_connection': ssh_connection},
                timeout=30
            )
            
            result = response.json()
            if result.get('success'):
                logger.info("SSH connection test successful")
                return True, None
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.error(f"SSH test failed: {error_msg}")
                
                # Check if it's a host key verification issue
                if result.get('host_verification_needed'):
                    # Return a special tuple that signals blocking
                    # Format: (success=False, error_msg, block_reason_dict)
                    return False, "Host key verification required", {
                        'block_reason': 'host_verification_needed',
                        'host': result.get('host'),
                        'port': result.get('port'),
                        'fingerprints': result.get('fingerprints', [])
                    }
                
                return False, error_msg
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"SSH test failed: {error_msg}")
            return False, f"Connection error: {error_msg}"
    
    def _execute_set_ui_home(self, ssh_connection: str, ui_home: str = '/workspace/ComfyUI') -> tuple:
        """Set UI_HOME environment variable by calling /ssh/set-ui-home API endpoint."""
        logger.info(f"Setting UI_HOME to {ui_home}...")
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/ssh/set-ui-home",
                json={
                    'ssh_connection': ssh_connection,
                    'ui_home': ui_home
                },
                timeout=30
            )
            
            result = response.json()
            if result.get('success'):
                logger.info("UI_HOME set successfully")
                return True, None
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.error(f"Set UI_HOME failed: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Set UI_HOME failed: {error_msg}")
            return False, f"Connection error: {error_msg}"
    
    def _execute_set_ui_home_consolidated(self, ssh_connection: str, ui_home: str, state_manager, workflow_id: str, step_index: int) -> tuple:
        """
        Consolidated UI_HOME setup: Set and Read.
        This replaces separate set_ui_home and get_ui_home actions.
        """
        logger.info(f"Starting consolidated UI_HOME setup (set + read): {ui_home}")
        
        # Task 1: Install (Set)
        self._update_task_status(state_manager, workflow_id, step_index, 'install', 'running')
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/ssh/set-ui-home",
                json={
                    'ssh_connection': ssh_connection,
                    'ui_home': ui_home
                },
                timeout=30
            )
            
            result = response.json()
            if not result.get('success'):
                error_msg = result.get('message', 'Unknown error')
                self._update_task_status(state_manager, workflow_id, step_index, 'install', 'failed')
                self._set_completion_note(state_manager, workflow_id, step_index, f"Failed to set UI_HOME: {error_msg}")
                return False, error_msg
            
            self._update_task_status(state_manager, workflow_id, step_index, 'install', 'success')
            logger.info("UI_HOME set successfully")
            
        except Exception as e:
            error_msg = str(e)
            self._update_task_status(state_manager, workflow_id, step_index, 'install', 'failed')
            self._set_completion_note(state_manager, workflow_id, step_index, f"Error setting UI_HOME: {error_msg}")
            return False, error_msg
        
        # Task 2: Test (Read)
        self._update_task_status(state_manager, workflow_id, step_index, 'test', 'running')
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/ssh/get-ui-home",
                json={'ssh_connection': ssh_connection},
                timeout=30
            )
            
            result = response.json()
            if result.get('success'):
                retrieved_ui_home = result.get('ui_home', 'Not set')
                self._update_task_status(state_manager, workflow_id, step_index, 'test', 'success')
                self._set_completion_note(state_manager, workflow_id, step_index, f"UI_HOME verified: {retrieved_ui_home}")
                logger.info(f"UI_HOME verified: {retrieved_ui_home}")
                return True, None
            else:
                error_msg = result.get('message', 'Unknown error')
                self._update_task_status(state_manager, workflow_id, step_index, 'test', 'failed')
                self._set_completion_note(state_manager, workflow_id, step_index, f"Failed to verify UI_HOME: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = str(e)
            self._update_task_status(state_manager, workflow_id, step_index, 'test', 'failed')
            self._set_completion_note(state_manager, workflow_id, step_index, f"Error verifying UI_HOME: {error_msg}")
            return False, error_msg
    
    def _execute_get_ui_home(self, ssh_connection: str) -> tuple:
        """Get UI_HOME environment variable by calling /ssh/get-ui-home API endpoint."""
        logger.info("Getting UI_HOME...")
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/ssh/get-ui-home",
                json={'ssh_connection': ssh_connection},
                timeout=30
            )
            
            result = response.json()
            if result.get('success'):
                ui_home = result.get('ui_home', 'Not set')
                logger.info(f"UI_HOME: {ui_home}")
                return True, None
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.error(f"Get UI_HOME failed: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Get UI_HOME failed: {error_msg}")
            return False, f"Connection error: {error_msg}"
    
    def _execute_setup_civitdl(self, ssh_connection: str) -> tuple:
        """Setup CivitDL by calling /ssh/setup-civitdl API endpoint."""
        logger.info("Setting up CivitDL...")
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/ssh/setup-civitdl",
                json={'ssh_connection': ssh_connection},
                timeout=180  # 3 minutes for installation
            )
            
            result = response.json()
            if result.get('success'):
                logger.info("CivitDL setup successful")
                return True, None
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.error(f"CivitDL setup failed: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"CivitDL setup failed: {error_msg}")
            return False, f"Connection error: {error_msg}"
    
    def _execute_setup_civitdl_consolidated(self, ssh_connection: str, state_manager, workflow_id: str, step_index: int) -> tuple:
        """
        Consolidated CivitDL setup: Install and Test.
        This replaces separate setup_civitdl and test_civitdl actions.
        """
        logger.info("Starting consolidated CivitDL setup (install + test)...")
        
        # Task 1: Install
        self._update_task_status(state_manager, workflow_id, step_index, 'install', 'running')
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/ssh/setup-civitdl",
                json={'ssh_connection': ssh_connection},
                timeout=180
            )
            
            result = response.json()
            if not result.get('success'):
                error_msg = result.get('message', 'Unknown error')
                self._update_task_status(state_manager, workflow_id, step_index, 'install', 'failed')
                self._set_completion_note(state_manager, workflow_id, step_index, f"Installation failed: {error_msg}")
                return False, error_msg
            
            self._update_task_status(state_manager, workflow_id, step_index, 'install', 'success')
            logger.info("CivitDL installation successful")
            
        except Exception as e:
            error_msg = str(e)
            self._update_task_status(state_manager, workflow_id, step_index, 'install', 'failed')
            self._set_completion_note(state_manager, workflow_id, step_index, f"Installation error: {error_msg}")
            return False, error_msg
        
        # Task 2: Test
        self._update_task_status(state_manager, workflow_id, step_index, 'test', 'running')
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/ssh/test-civitdl",
                json={'ssh_connection': ssh_connection},
                timeout=60
            )
            
            result = response.json()
            if result.get('success'):
                self._update_task_status(state_manager, workflow_id, step_index, 'test', 'success')
                self._set_completion_note(state_manager, workflow_id, step_index, "CivitDL installed and tested successfully")
                logger.info("CivitDL test successful")
                return True, None
            else:
                error_msg = result.get('message', 'Unknown error')
                # Test failure might be acceptable with warning
                if result.get('has_warning', False):
                    self._update_task_status(state_manager, workflow_id, step_index, 'test', 'success')
                    self._set_completion_note(state_manager, workflow_id, step_index, f"CivitDL installed successfully (test warning: {error_msg})")
                    return True, None
                else:
                    self._update_task_status(state_manager, workflow_id, step_index, 'test', 'failed')
                    self._set_completion_note(state_manager, workflow_id, step_index, f"Test failed: {error_msg}")
                    return False, error_msg
                    
        except Exception as e:
            error_msg = str(e)
            self._update_task_status(state_manager, workflow_id, step_index, 'test', 'failed')
            self._set_completion_note(state_manager, workflow_id, step_index, f"Test error: {error_msg}")
            return False, error_msg
    
    def _execute_test_civitdl(self, ssh_connection: str) -> tuple:
        """Test CivitDL installation by calling /ssh/test-civitdl API endpoint."""
        logger.info("Testing CivitDL...")
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/ssh/test-civitdl",
                json={'ssh_connection': ssh_connection},
                timeout=60
            )
            
            result = response.json()
            if result.get('success'):
                logger.info("CivitDL test successful")
                return True, None
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.warning(f"CivitDL test failed: {error_msg}")
                # Consider partial success acceptable
                if result.get('has_warning', False):
                    return True, None  # Warning but not failure
                return False, error_msg
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"CivitDL test failed: {error_msg}")
            return False, f"Connection error: {error_msg}"
    
    def _execute_sync_instance(self, ssh_connection: str) -> tuple:
        """Sync instance media by calling /sync/vastai-connection API endpoint."""
        logger.info("Syncing instance...")
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/sync/vastai-connection",
                json={
                    'ssh_connection': ssh_connection,
                    'cleanup': True
                },
                timeout=600  # 10 minutes for sync
            )
            
            result = response.json()
            if result.get('success'):
                logger.info("Instance sync successful")
                return True, None
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.error(f"Instance sync failed: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Instance sync failed: {error_msg}")
            return False, f"Connection error: {error_msg}"
    
    def _execute_setup_python_venv(self, ssh_connection: str) -> tuple:
        """Setup Python virtual environment (placeholder - may not be needed)."""
        logger.info("Setting up Python venv...")
        # Most VastAI templates already have venv configured
        # This is a placeholder for future use
        time.sleep(1)
        logger.info("Python venv already configured")
        return True, None
    
    def _execute_clone_auto_installer(self, ssh_connection: str) -> tuple:
        """Clone Auto Installer repository by calling template execute-step API."""
        logger.info("Cloning Auto Installer repository...")
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/templates/comfyui/execute-step",
                json={
                    'ssh_connection': ssh_connection,
                    'step_name': 'Clone ComfyUI Auto Installer'
                },
                timeout=300  # 5 minutes
            )
            
            result = response.json()
            if result.get('success'):
                logger.info("Auto Installer repository cloned successfully")
                return True, None
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.error(f"Auto Installer clone failed: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Auto Installer clone failed: {error_msg}")
            return False, f"Connection error: {error_msg}"
    
    def _execute_install_custom_nodes(self, ssh_connection: str, ui_home: str, 
                                     state_manager, workflow_id: str, step_index: int) -> tuple:
        """
        Install custom nodes with rolling tasklist display.
        Includes: Clone Auto-installer, custom nodes (with rolling 5-line display), and verify dependencies.
        """
        logger.info("Starting custom nodes installation workflow...")
        
        # Task 1: Clone Auto-installer
        self._update_task_status(state_manager, workflow_id, step_index, 'Clone Auto-installer', 'running')
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/templates/comfyui/execute-step",
                json={
                    'ssh_connection': ssh_connection,
                    'step_name': 'Clone ComfyUI Auto Installer'
                },
                timeout=300
            )
            
            result = response.json()
            if not result.get('success'):
                error_msg = result.get('message', 'Unknown error')
                self._update_task_status(state_manager, workflow_id, step_index, 'Clone Auto-installer', 'failed')
                self._set_completion_note(state_manager, workflow_id, step_index, f"Failed to clone auto-installer: {error_msg}")
                return False, error_msg
            
            self._update_task_status(state_manager, workflow_id, step_index, 'Clone Auto-installer', 'success')
            logger.info("Auto-installer cloned successfully")
            
        except Exception as e:
            error_msg = str(e)
            self._update_task_status(state_manager, workflow_id, step_index, 'Clone Auto-installer', 'failed')
            self._set_completion_note(state_manager, workflow_id, step_index, f"Error cloning auto-installer: {error_msg}")
            return False, error_msg
        
        # Task 2: Install Custom Nodes (with rolling display)
        try:
            # Start the installation
            response = requests.post(
                f"{API_BASE_URL}/ssh/install-custom-nodes",
                json={
                    'ssh_connection': ssh_connection,
                    'ui_home': ui_home
                },
                timeout=1800  # 30 minutes timeout
            )
            
            result = response.json()
            if not result.get('success'):
                error_msg = result.get('message', 'Unknown error')
                logger.error(f"Custom nodes installation failed: {error_msg}")
                self._set_completion_note(state_manager, workflow_id, step_index, f"Custom nodes installation failed: {error_msg}")
                return False, error_msg
            
            # Installation completed - update tasklist with rolling display logic
            total_nodes = result.get('total_nodes', 0)
            successful_nodes = result.get('successful_clones', 0)
            failed_nodes = result.get('failed_clones', 0)
            node_list = result.get('nodes', [])
            
            logger.info(f"Custom nodes installation completed: {successful_nodes}/{total_nodes} successful, {failed_nodes} failed")
            
            # Update state with rolling display for nodes
            state = state_manager.load_state()
            if state:
                tasks = state['steps'][step_index].get('tasks', [])
                
                # Keep Clone Auto-installer task
                # Add node tasks with rolling display
                MAX_VISIBLE = 5
                
                if total_nodes > MAX_VISIBLE - 1:  # -1 for Clone Auto-installer
                    # Show first 3 nodes, then "# others"
                    for i, node in enumerate(node_list[:3]):
                        task_name = node.get('name', f'Node {i+1}')
                        status = 'success' if node.get('success') else 'failed'
                        self._update_task_status(state_manager, workflow_id, step_index, task_name, status)
                    
                    # Add "# others" summary
                    remaining = total_nodes - 3
                    others_status = f"success ({successful_nodes - 3}/{remaining})" if successful_nodes > 3 else "pending"
                    self._update_task_status(state_manager, workflow_id, step_index, f"{remaining} others", others_status)
                else:
                    # Show all nodes
                    for node in node_list:
                        task_name = node.get('name', 'Unknown Node')
                        status = 'success' if node.get('success') else 'failed'
                        self._update_task_status(state_manager, workflow_id, step_index, task_name, status)
                
                state_manager.save_state(state)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Custom nodes installation failed: {error_msg}")
            self._set_completion_note(state_manager, workflow_id, step_index, f"Installation error: {error_msg}")
            return False, error_msg
        
        # Task 3: Verify Dependencies (with rolling display)
        self._update_task_status(state_manager, workflow_id, step_index, 'Verify Dependencies', 'running')
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/ssh/verify-dependencies",
                json={
                    'ssh_connection': ssh_connection,
                    'ui_home': ui_home
                },
                timeout=300
            )
            
            result = response.json()
            if result.get('success'):
                installed_deps = result.get('installed', [])
                if installed_deps:
                    logger.info(f"Installed {len(installed_deps)} missing dependencies")
                    
                    # Add dependencies as sub-tasks with rolling display
                    MAX_DEP_VISIBLE = 5
                    if len(installed_deps) > MAX_DEP_VISIBLE:
                        for dep in installed_deps[:4]:
                            self._update_task_status(state_manager, workflow_id, step_index, f"  {dep}", 'success')
                        remaining_deps = len(installed_deps) - 4
                        self._update_task_status(state_manager, workflow_id, step_index, f"  {remaining_deps} others", f"success ({remaining_deps}/{remaining_deps})")
                    else:
                        for dep in installed_deps:
                            self._update_task_status(state_manager, workflow_id, step_index, f"  {dep}", 'success')
                
                self._update_task_status(state_manager, workflow_id, step_index, 'Verify Dependencies', 'success')
                self._set_completion_note(state_manager, workflow_id, step_index, f"Custom nodes installation completed: {successful_nodes}/{total_nodes} nodes, {len(installed_deps)} dependencies installed")
                return True, None
            else:
                error_msg = result.get('message', 'Unknown error')
                self._update_task_status(state_manager, workflow_id, step_index, 'Verify Dependencies', 'failed')
                self._set_completion_note(state_manager, workflow_id, step_index, f"Dependency verification failed: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = str(e)
            self._update_task_status(state_manager, workflow_id, step_index, 'Verify Dependencies', 'failed')
            self._set_completion_note(state_manager, workflow_id, step_index, f"Dependency verification error: {error_msg}")
            return False, error_msg
    
    def _execute_verify_dependencies(self, ssh_connection: str, ui_home: str) -> tuple:
        """Verify dependencies by calling /ssh/verify-dependencies API endpoint."""
        logger.info("Verifying dependencies...")
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/ssh/verify-dependencies",
                json={
                    'ssh_connection': ssh_connection,
                    'ui_home': ui_home
                },
                timeout=300  # 5 minutes
            )
            
            result = response.json()
            if result.get('success'):
                installed = result.get('installed', [])
                if installed:
                    logger.info(f"Installed {len(installed)} missing dependencies: {', '.join(installed)}")
                else:
                    logger.info("All dependencies verified")
                return True, None
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.error(f"Dependency verification failed: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Dependency verification failed: {error_msg}")
            return False, f"Connection error: {error_msg}"
    
    def _execute_reboot_instance(self, instance_id: Optional[int]) -> tuple:
        """Reboot instance by calling /ssh/reboot-instance API endpoint."""
        logger.info(f"Rebooting instance {instance_id}...")
        
        if not instance_id:
            error_msg = "Instance ID required for reboot"
            logger.error(error_msg)
            return False, error_msg
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/ssh/reboot-instance",
                json={'instance_id': instance_id},
                timeout=30
            )
            
            result = response.json()
            if result.get('success'):
                logger.info("Instance reboot initiated")
                # Wait for instance to come back up
                logger.info("Waiting 30 seconds for instance to restart...")
                time.sleep(30)
                return True, None
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.error(f"Instance reboot failed: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Instance reboot failed: {error_msg}")
            return False, f"Connection error: {error_msg}"
    
    def _execute_reboot_instance_with_tasks(self, instance_id: Optional[int], state_manager, workflow_id: str, step_index: int) -> tuple:
        """
        Reboot instance with detailed task tracking.
        Tasks: Initiating, Waiting (with countdown), Checking (with retry).
        """
        logger.info(f"Starting reboot workflow for instance {instance_id}...")
        
        if not instance_id:
            error_msg = "Instance ID required for reboot"
            logger.error(error_msg)
            self._set_completion_note(state_manager, workflow_id, step_index, error_msg)
            return False, error_msg
        
        # Task 1: Initiating
        self._update_task_status(state_manager, workflow_id, step_index, 'Initiating', 'running')
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/ssh/reboot-instance",
                json={'instance_id': instance_id},
                timeout=30
            )
            
            result = response.json()
            if not result.get('success'):
                error_msg = result.get('message', 'Unknown error')
                self._update_task_status(state_manager, workflow_id, step_index, 'Initiating', 'failed')
                self._set_completion_note(state_manager, workflow_id, step_index, f"Failed to initiate reboot: {error_msg}")
                return False, error_msg
            
            self._update_task_status(state_manager, workflow_id, step_index, 'Initiating', 'success')
            logger.info("Instance reboot initiated")
            
        except Exception as e:
            error_msg = str(e)
            self._update_task_status(state_manager, workflow_id, step_index, 'Initiating', 'failed')
            self._set_completion_note(state_manager, workflow_id, step_index, f"Reboot initiation error: {error_msg}")
            return False, error_msg
        
        # Task 2: Waiting (with countdown)
        WAIT_DURATION = 30  # seconds
        for remaining in range(WAIT_DURATION, 0, -1):
            self._update_task_status(state_manager, workflow_id, step_index, 'Waiting', f'countdown:{remaining}')
            time.sleep(1)
        
        self._update_task_status(state_manager, workflow_id, step_index, 'Waiting', 'success')
        logger.info("Wait period completed")
        
        # Task 3: Checking (with retry)
        MAX_RETRIES = 3
        for attempt in range(1, MAX_RETRIES + 1):
            self._update_task_status(state_manager, workflow_id, step_index, 'Checking', 'running')
            logger.info(f"Checking instance status (attempt {attempt}/{MAX_RETRIES})...")
            
            try:
                # Check if instance is back online
                check_response = requests.get(
                    f"{API_BASE_URL}/vastai/instances",
                    timeout=30
                )
                
                check_result = check_response.json()
                if check_result.get('success'):
                    instances = check_result.get('instances', [])
                    target_instance = next((inst for inst in instances if inst.get('id') == instance_id), None)
                    
                    if target_instance and target_instance.get('actual_status') == 'running':
                        self._update_task_status(state_manager, workflow_id, step_index, 'Checking', 'success')
                        self._set_completion_note(state_manager, workflow_id, step_index, "Instance rebooted and verified successfully")
                        logger.info("Instance is back online")
                        return True, None
                
                # Check failed, retry if attempts remain
                if attempt < MAX_RETRIES:
                    logger.warning(f"Instance not ready, waiting 30 seconds before retry...")
                    for remaining in range(30, 0, -1):
                        self._update_task_status(state_manager, workflow_id, step_index, 'Waiting', f'countdown:{remaining}')
                        time.sleep(1)
                    self._update_task_status(state_manager, workflow_id, step_index, 'Waiting', 'success')
                else:
                    # Max retries reached
                    self._update_task_status(state_manager, workflow_id, step_index, 'Checking', 'failed')
                    error_msg = f"Instance did not come back online after {MAX_RETRIES} attempts"
                    self._set_completion_note(state_manager, workflow_id, step_index, error_msg)
                    return False, error_msg
                    
            except Exception as e:
                error_msg = str(e)
                if attempt < MAX_RETRIES:
                    logger.warning(f"Check failed with error: {error_msg}, retrying...")
                    for remaining in range(30, 0, -1):
                        self._update_task_status(state_manager, workflow_id, step_index, 'Waiting', f'countdown:{remaining}')
                        time.sleep(1)
                    self._update_task_status(state_manager, workflow_id, step_index, 'Waiting', 'success')
                else:
                    self._update_task_status(state_manager, workflow_id, step_index, 'Checking', 'failed')
                    self._set_completion_note(state_manager, workflow_id, step_index, f"Check error: {error_msg}")
                    return False, error_msg
        
        # Should not reach here
        return False, "Unexpected error in reboot workflow"


def get_workflow_executor() -> WorkflowExecutor:
    """
    Get or create the global workflow executor instance.
    
    Returns:
        WorkflowExecutor instance
    """
    global _workflow_executor
    if _workflow_executor is None:
        _workflow_executor = WorkflowExecutor()
    return _workflow_executor
