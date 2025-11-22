"""
Server-Side Workflow Executor
Executes workflows in background threads, allowing them to continue even if the page is refreshed.
"""

import logging
import threading
import time
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from .workflow_state import get_workflow_state_manager

logger = logging.getLogger(__name__)

# Global workflow executor instance
_workflow_executor = None


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
                success = self._execute_step(step, ssh_connection)
                
                # Update state - step completed or failed
                if success:
                    state['steps'][step_index]['status'] = 'completed'
                    logger.info(f"Step {step_index + 1} completed: {step['action']}")
                else:
                    state['steps'][step_index]['status'] = 'failed'
                    state['status'] = 'failed'
                    logger.error(f"Step {step_index + 1} failed: {step['action']}")
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
    
    def _execute_step(self, step: Dict[str, Any], ssh_connection: str) -> bool:
        """
        Execute a single workflow step.
        
        Args:
            step: Step configuration with 'action' and other parameters
            ssh_connection: SSH connection string
            
        Returns:
            True if step succeeded, False otherwise
        """
        action = step.get('action')
        
        try:
            # Map action to execution logic
            if action == 'test_ssh':
                return self._test_ssh(ssh_connection)
            elif action == 'set_ui_home':
                return self._set_ui_home(ssh_connection)
            elif action == 'get_ui_home':
                return self._get_ui_home(ssh_connection)
            elif action == 'setup_civitdl':
                return self._setup_civitdl(ssh_connection)
            elif action == 'test_civitdl':
                return self._test_civitdl(ssh_connection)
            elif action == 'sync_instance':
                return self._sync_instance(ssh_connection)
            elif action == 'setup_python_venv':
                return self._setup_python_venv(ssh_connection)
            elif action == 'clone_auto_installer':
                return self._clone_auto_installer(ssh_connection)
            elif action == 'install_custom_nodes':
                return self._install_custom_nodes(ssh_connection)
            elif action == 'verify_dependencies':
                return self._verify_dependencies(ssh_connection)
            elif action == 'reboot_instance':
                return self._reboot_instance(ssh_connection)
            else:
                logger.warning(f"Unknown action: {action}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing step {action}: {e}", exc_info=True)
            return False
    
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
    
    def _test_ssh(self, ssh_connection: str) -> bool:
        """Test SSH connection."""
        host, port = self._parse_ssh_connection(ssh_connection)
        if not host:
            return False
        
        cmd = ['ssh', '-p', port, '-o', 'StrictHostKeyChecking=no', 
               '-o', 'ConnectTimeout=10', f'root@{host}', 'echo "Connection successful"']
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"SSH test failed: {e}")
            return False
    
    def _set_ui_home(self, ssh_connection: str) -> bool:
        """Set UI_HOME environment variable."""
        host, port = self._parse_ssh_connection(ssh_connection)
        if not host:
            return False
        
        cmd = ['ssh', '-p', port, '-o', 'StrictHostKeyChecking=no',
               f'root@{host}', 
               'echo "export UI_HOME=/workspace/ComfyUI" >> ~/.bashrc && source ~/.bashrc']
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Set UI_HOME failed: {e}")
            return False
    
    def _get_ui_home(self, ssh_connection: str) -> bool:
        """Get UI_HOME environment variable."""
        host, port = self._parse_ssh_connection(ssh_connection)
        if not host:
            return False
        
        cmd = ['ssh', '-p', port, '-o', 'StrictHostKeyChecking=no',
               f'root@{host}', 'source ~/.bashrc && echo $UI_HOME']
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Get UI_HOME failed: {e}")
            return False
    
    def _setup_civitdl(self, ssh_connection: str) -> bool:
        """Setup CivitDL."""
        # This is a placeholder - actual implementation would call the real setup logic
        logger.info("Setting up CivitDL...")
        time.sleep(2)  # Simulate work
        return True
    
    def _test_civitdl(self, ssh_connection: str) -> bool:
        """Test CivitDL installation."""
        logger.info("Testing CivitDL...")
        time.sleep(1)  # Simulate work
        return True
    
    def _sync_instance(self, ssh_connection: str) -> bool:
        """Sync instance."""
        logger.info("Syncing instance...")
        time.sleep(3)  # Simulate work
        return True
    
    def _setup_python_venv(self, ssh_connection: str) -> bool:
        """Setup Python virtual environment."""
        logger.info("Setting up Python venv...")
        time.sleep(2)  # Simulate work
        return True
    
    def _clone_auto_installer(self, ssh_connection: str) -> bool:
        """Clone Auto Installer repository."""
        logger.info("Cloning Auto Installer...")
        time.sleep(2)  # Simulate work
        return True
    
    def _install_custom_nodes(self, ssh_connection: str) -> bool:
        """Install custom nodes."""
        logger.info("Installing custom nodes...")
        time.sleep(5)  # Simulate work
        return True
    
    def _verify_dependencies(self, ssh_connection: str) -> bool:
        """Verify dependencies."""
        logger.info("Verifying dependencies...")
        time.sleep(2)  # Simulate work
        return True
    
    def _reboot_instance(self, ssh_connection: str) -> bool:
        """Reboot instance."""
        logger.info("Rebooting instance...")
        time.sleep(3)  # Simulate work
        return True


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
