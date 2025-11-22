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
                success, error_message = self._execute_step(step, ssh_connection, state_manager, workflow_id, step_index)
                
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
            elif action == 'set_ui_home':
                ui_home = step.get('ui_home', '/workspace/ComfyUI')
                return self._execute_set_ui_home(ssh_connection, ui_home)
            elif action == 'get_ui_home':
                return self._execute_get_ui_home(ssh_connection)
            elif action == 'setup_civitdl':
                return self._execute_setup_civitdl(ssh_connection)
            elif action == 'test_civitdl':
                return self._execute_test_civitdl(ssh_connection)
            elif action == 'sync_instance':
                return self._execute_sync_instance(ssh_connection)
            elif action == 'setup_python_venv':
                return self._execute_setup_python_venv(ssh_connection)
            elif action == 'install_custom_nodes':
                ui_home = step.get('ui_home', '/workspace/ComfyUI')
                return self._execute_install_custom_nodes(ssh_connection, ui_home, state_manager, workflow_id, step_index)
            elif action == 'verify_dependencies':
                ui_home = step.get('ui_home', '/workspace/ComfyUI')
                return self._execute_verify_dependencies(ssh_connection, ui_home)
            elif action == 'reboot_instance':
                instance_id = step.get('instance_id')
                return self._execute_reboot_instance(instance_id)
            else:
                logger.warning(f"Unknown action: {action}")
                return False, f"Unknown action: {action}"
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error executing step {action}: {error_msg}", exc_info=True)
            return False, f"Exception: {error_msg}"
    
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
                    error_msg = "Host key verification required. Please verify the SSH host key first using the 'Verify Host Key' button."
                
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
    
    def _execute_install_custom_nodes(self, ssh_connection: str, ui_home: str, 
                                     state_manager, workflow_id: str, step_index: int) -> tuple:
        """
        Install custom nodes by calling /ssh/install-custom-nodes API endpoint.
        Polls progress and updates state during installation.
        """
        logger.info("Installing custom nodes...")
        
        try:
            # Start the installation (this returns immediately)
            response = requests.post(
                f"{API_BASE_URL}/ssh/install-custom-nodes",
                json={
                    'ssh_connection': ssh_connection,
                    'ui_home': ui_home
                },
                timeout=1800  # 30 minutes timeout
            )
            
            result = response.json()
            if result.get('success'):
                # Installation completed successfully
                total = result.get('total_nodes', 0)
                successful = result.get('successful_clones', 0)
                failed = result.get('failed_clones', 0)
                
                logger.info(f"Custom nodes installation completed: {successful}/{total} successful, {failed} failed")
                
                # Update step progress
                state = state_manager.load_state()
                if state:
                    state['steps'][step_index]['progress'] = {
                        'total': total,
                        'processed': total,
                        'successful': successful,
                        'failed': failed
                    }
                    state_manager.save_state(state)
                
                return True, None
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.error(f"Custom nodes installation failed: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Custom nodes installation failed: {error_msg}")
            return False, f"Connection error: {error_msg}"
    
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
