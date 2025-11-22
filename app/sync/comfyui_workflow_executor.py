"""
ComfyUI Workflow Executor
Main execution engine for running ComfyUI workflows on remote instances.
"""

import os
import json
import time
import uuid
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict

from .comfyui_workflow_state import (
    ComfyUIWorkflowState,
    ComfyUINodeState,
    ComfyUIOutputFile,
    WorkflowStatus,
    NodeStatus
)
from .comfyui_progress_monitor import ComfyUIProgressMonitor, create_progress_monitor
from .comfyui_file_transfer import ComfyUIFileTransfer, create_file_transfer
from .ssh_tunnel import SSHTunnel, SSHTunnelPool

logger = logging.getLogger(__name__)


class ComfyUIWorkflowExecutor:
    """Execute ComfyUI workflows on remote instances with full lifecycle management."""
    
    def __init__(self, state_file_path: str = "/tmp/comfyui_workflow_state.json"):
        """
        Initialize the workflow executor.
        
        Args:
            state_file_path: Path to persistent state file
        """
        self.state_file_path = state_file_path
        self.active_workflows: Dict[str, threading.Thread] = {}
        self.stop_flags: Dict[str, threading.Event] = {}
        self.workflow_states: Dict[str, ComfyUIWorkflowState] = {}
        self.tunnel_pool = SSHTunnelPool()
        self._lock = threading.Lock()
        
        logger.info(f"WorkflowExecutor initialized with state file: {state_file_path}")
    
    def execute_workflow(
        self,
        ssh_connection: str,
        workflow_file: str,
        workflow_name: Optional[str] = None,
        input_images: Optional[List[str]] = None,
        output_dir: str = "/tmp/comfyui_outputs",
        comfyui_port: int = 18188,
        comfyui_input_dir: str = "/workspace/ComfyUI/input",
        comfyui_output_dir: str = "/workspace/ComfyUI/output"
    ) -> Tuple[bool, str, str]:
        """
        Execute a ComfyUI workflow on remote instance.
        
        Args:
            ssh_connection: SSH connection string
            workflow_file: Path to local workflow JSON file
            workflow_name: Optional workflow name
            input_images: Optional list of input image paths
            output_dir: Local directory for downloaded outputs
            comfyui_port: Port for ComfyUI API (default 18188)
            comfyui_input_dir: Remote ComfyUI input directory
            comfyui_output_dir: Remote ComfyUI output directory
            
        Returns:
            Tuple of (success, workflow_id, message)
        """
        # Generate workflow ID
        workflow_id = f"comfyui_workflow_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Validate inputs
        if not os.path.exists(workflow_file):
            return False, "", f"Workflow file not found: {workflow_file}"
        
        if input_images:
            for img_path in input_images:
                if not os.path.exists(img_path):
                    return False, "", f"Input image not found: {img_path}"
        
        # Parse workflow to get node count
        try:
            with open(workflow_file, 'r') as f:
                workflow_data = json.load(f)
            total_nodes = len(workflow_data)
        except Exception as e:
            return False, "", f"Failed to parse workflow: {e}"
        
        # Initialize state
        initial_state = ComfyUIWorkflowState(
            workflow_id=workflow_id,
            workflow_name=workflow_name or os.path.basename(workflow_file),
            prompt_id="",  # Will be set after queuing
            ssh_connection=ssh_connection,
            workflow_file=workflow_file,
            status=WorkflowStatus.QUEUED,
            queue_position=None,
            current_node=None,
            total_nodes=total_nodes,
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
        
        # Store state
        with self._lock:
            self.workflow_states[workflow_id] = initial_state
            self._save_state(workflow_id)
        
        # Create stop flag
        stop_flag = threading.Event()
        self.stop_flags[workflow_id] = stop_flag
        
        # Start execution thread
        execution_thread = threading.Thread(
            target=self._execute_workflow_thread,
            args=(
                workflow_id,
                ssh_connection,
                workflow_file,
                input_images or [],
                output_dir,
                comfyui_port,
                comfyui_input_dir,
                comfyui_output_dir,
                stop_flag
            ),
            daemon=True,
            name=f"ComfyUIExecutor-{workflow_id}"
        )
        
        with self._lock:
            self.active_workflows[workflow_id] = execution_thread
        
        execution_thread.start()
        logger.info(f"Started workflow execution: {workflow_id}")
        
        return True, workflow_id, "Workflow execution started"
    
    def _execute_workflow_thread(
        self,
        workflow_id: str,
        ssh_connection: str,
        workflow_file: str,
        input_images: List[str],
        output_dir: str,
        comfyui_port: int,
        comfyui_input_dir: str,
        comfyui_output_dir: str,
        stop_flag: threading.Event
    ):
        """
        Execute workflow in background thread.
        
        This method handles the complete workflow lifecycle:
        1. Upload workflow and input files
        2. Queue workflow via ComfyUI API
        3. Monitor execution progress
        4. Download outputs
        5. Clean up remote files
        """
        try:
            # Create file transfer manager
            file_transfer = create_file_transfer(ssh_connection)
            
            # Step 1: Upload workflow file
            logger.info(f"[{workflow_id}] Uploading workflow file...")
            remote_workflow_path = file_transfer.upload_workflow(workflow_file, "/tmp")
            
            if not remote_workflow_path:
                self._set_error(workflow_id, "Failed to upload workflow file", None)
                return
            
            if stop_flag.is_set():
                self._set_cancelled(workflow_id)
                return
            
            # Step 2: Upload input images
            remote_input_paths = []
            if input_images:
                logger.info(f"[{workflow_id}] Uploading {len(input_images)} input images...")
                remote_input_paths = file_transfer.upload_input_images(
                    input_images, 
                    comfyui_input_dir
                )
                
                if len(remote_input_paths) != len(input_images):
                    logger.warning(f"[{workflow_id}] Only uploaded {len(remote_input_paths)}/{len(input_images)} images")
            
            if stop_flag.is_set():
                self._set_cancelled(workflow_id)
                return
            
            # Step 3: Get or create SSH tunnel
            tunnel = self.tunnel_pool.get_tunnel(ssh_connection, comfyui_port)
            
            if not tunnel:
                self._set_error(workflow_id, "Failed to create SSH tunnel", None)
                return
            
            local_port = tunnel.local_port
            logger.info(f"[{workflow_id}] Using tunnel localhost:{local_port} -> remote:{comfyui_port}")
            
            # Step 4: Queue workflow
            logger.info(f"[{workflow_id}] Queueing workflow...")
            prompt_id, queue_number = self._queue_workflow(
                remote_workflow_path,
                file_transfer,
                local_port
            )
            
            if not prompt_id:
                self._set_error(workflow_id, "Failed to queue workflow", None)
                return
            
            # Update state with prompt ID
            with self._lock:
                state = self.workflow_states.get(workflow_id)
                if state:
                    state.prompt_id = prompt_id
                    state.queue_position = queue_number
                    state.status = WorkflowStatus.QUEUED
                    state.last_update = datetime.now()
                    self._save_state(workflow_id)
            
            logger.info(f"[{workflow_id}] Workflow queued: prompt_id={prompt_id}, position={queue_number}")
            
            if stop_flag.is_set():
                self._cancel_workflow_api(prompt_id, local_port)
                self._set_cancelled(workflow_id)
                return
            
            # Step 5: Monitor execution
            logger.info(f"[{workflow_id}] Monitoring execution...")
            monitor = create_progress_monitor(ssh_connection, comfyui_port)
            
            success = monitor.monitor_execution_polling(
                prompt_id=prompt_id,
                callback=lambda progress: self._update_progress(workflow_id, progress),
                stop_flag=stop_flag,
                poll_interval=2.0
            )
            
            if stop_flag.is_set():
                self._cancel_workflow_api(prompt_id, local_port)
                self._set_cancelled(workflow_id)
                return
            
            if not success:
                # Check if we got error info from monitoring
                state = self.workflow_states.get(workflow_id)
                if state and state.error_message:
                    return  # Error already set by monitor
                else:
                    self._set_error(workflow_id, "Workflow execution failed", None)
                    return
            
            # Step 6: Get outputs
            logger.info(f"[{workflow_id}] Retrieving outputs...")
            outputs = monitor.get_execution_outputs(prompt_id)
            
            if outputs:
                # Download outputs
                output_filenames = [output['filename'] for output in outputs]
                downloaded_paths = file_transfer.download_outputs(
                    output_filenames,
                    output_dir,
                    comfyui_output_dir
                )
                
                # Update state with outputs
                output_files = []
                for output in outputs:
                    filename = output['filename']
                    local_path = os.path.join(output_dir, filename)
                    downloaded = local_path in downloaded_paths
                    
                    output_files.append(ComfyUIOutputFile(
                        filename=filename,
                        file_type=output.get('type', 'unknown'),
                        remote_path=output.get('path', ''),
                        local_path=local_path if downloaded else None,
                        downloaded=downloaded
                    ))
                
                with self._lock:
                    state = self.workflow_states.get(workflow_id)
                    if state:
                        state.outputs = output_files
                        self._save_state(workflow_id)
                
                logger.info(f"[{workflow_id}] Downloaded {len(downloaded_paths)} outputs")
            
            # Step 7: Clean up remote files
            cleanup_paths = [remote_workflow_path] + remote_input_paths
            file_transfer.cleanup_remote_files(cleanup_paths)
            
            # Mark as completed
            self._set_completed(workflow_id)
            logger.info(f"[{workflow_id}] Workflow completed successfully")
            
        except Exception as e:
            logger.exception(f"[{workflow_id}] Workflow execution error")
            self._set_error(workflow_id, f"Execution error: {str(e)}", None)
        
        finally:
            # Cleanup
            with self._lock:
                if workflow_id in self.active_workflows:
                    del self.active_workflows[workflow_id]
                if workflow_id in self.stop_flags:
                    del self.stop_flags[workflow_id]
    
    def _queue_workflow(
        self,
        workflow_path: str,
        file_transfer: ComfyUIFileTransfer,
        local_port: int
    ) -> Tuple[str, Optional[int]]:
        """
        Queue workflow via ComfyUI API.
        
        Args:
            workflow_path: Remote path to workflow JSON
            file_transfer: File transfer manager
            local_port: Local tunnel port
            
        Returns:
            Tuple of (prompt_id, queue_number)
        """
        try:
            # Read workflow from remote
            success, stdout, stderr = file_transfer.execute_remote_command(
                f'cat "{workflow_path}"'
            )
            
            if not success:
                logger.error(f"Failed to read remote workflow: {stderr}")
                return "", None
            
            workflow_json = stdout
            
            # Queue via API using curl
            curl_cmd = f"""curl -s -X POST http://localhost:{local_port}/prompt \
                -H 'Content-Type: application/json' \
                -d '{{"prompt": {workflow_json}}}'"""
            
            success, stdout, stderr = file_transfer.execute_remote_command(curl_cmd)
            
            if not success:
                logger.error(f"Failed to queue workflow: {stderr}")
                return "", None
            
            # Parse response
            try:
                response = json.loads(stdout)
                prompt_id = response.get('prompt_id', '')
                
                # Get queue position
                queue_cmd = f"curl -s http://localhost:{local_port}/queue"
                success, queue_stdout, _ = file_transfer.execute_remote_command(queue_cmd)
                
                queue_number = None
                if success:
                    try:
                        queue_data = json.loads(queue_stdout)
                        queue_pending = queue_data.get('queue_pending', [])
                        for idx, item in enumerate(queue_pending):
                            if item[1] == prompt_id:
                                queue_number = idx
                                break
                    except:
                        pass
                
                return prompt_id, queue_number
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse queue response: {e}")
                return "", None
        
        except Exception as e:
            logger.error(f"Queue workflow error: {e}")
            return "", None
    
    def _cancel_workflow_api(self, prompt_id: str, local_port: int):
        """Cancel workflow via ComfyUI API."""
        # Note: ComfyUI API doesn't have a direct cancel endpoint
        # We can try to interrupt the current execution
        logger.info(f"Attempting to cancel workflow: {prompt_id}")
    
    def _update_progress(self, workflow_id: str, progress: Dict[str, Any]):
        """
        Update workflow progress from monitor callback.
        
        Args:
            workflow_id: Workflow ID
            progress: Progress data from monitor
        """
        with self._lock:
            state = self.workflow_states.get(workflow_id)
            if not state:
                return
            
            # Update status
            if progress.get('status'):
                state.status = WorkflowStatus(progress['status'])
            
            # Update progress
            if 'queue_position' in progress:
                state.queue_position = progress['queue_position']
            
            if 'current_node' in progress:
                state.current_node = progress['current_node']
            
            if 'completed_nodes' in progress:
                state.completed_nodes = progress['completed_nodes']
            
            if 'progress_percent' in progress:
                state.progress_percent = progress['progress_percent']
            
            # Update nodes
            if 'nodes' in progress:
                node_states = []
                for node_data in progress['nodes']:
                    node_states.append(ComfyUINodeState(
                        node_id=node_data['node_id'],
                        node_type=node_data.get('node_type', 'Unknown'),
                        status=NodeStatus(node_data.get('status', 'pending')),
                        progress=node_data.get('progress', 0.0),
                        message=node_data.get('message')
                    ))
                state.nodes = node_states
            
            # Update timing
            if progress.get('start_time') and not state.start_time:
                state.start_time = datetime.now()
            
            # Update error
            if progress.get('error_message'):
                state.error_message = progress['error_message']
                state.failed_node = progress.get('failed_node')
            
            state.last_update = datetime.now()
            self._save_state(workflow_id)
    
    def _set_completed(self, workflow_id: str):
        """Mark workflow as completed."""
        with self._lock:
            state = self.workflow_states.get(workflow_id)
            if state:
                state.status = WorkflowStatus.COMPLETED
                state.end_time = datetime.now()
                state.progress_percent = 100.0
                state.last_update = datetime.now()
                self._save_state(workflow_id)
    
    def _set_error(self, workflow_id: str, error_message: str, failed_node: Optional[str]):
        """Mark workflow as failed."""
        with self._lock:
            state = self.workflow_states.get(workflow_id)
            if state:
                state.status = WorkflowStatus.FAILED
                state.error_message = error_message
                state.failed_node = failed_node
                state.end_time = datetime.now()
                state.last_update = datetime.now()
                self._save_state(workflow_id)
    
    def _set_cancelled(self, workflow_id: str):
        """Mark workflow as cancelled."""
        with self._lock:
            state = self.workflow_states.get(workflow_id)
            if state:
                state.status = WorkflowStatus.CANCELLED
                state.end_time = datetime.now()
                state.last_update = datetime.now()
                self._save_state(workflow_id)
    
    def _save_state(self, workflow_id: str):
        """Save workflow state to persistent file."""
        state = self.workflow_states.get(workflow_id)
        if not state:
            return
        
        try:
            state_dict = asdict(state)
            
            # Convert datetime objects to ISO format
            for key in ['queue_time', 'start_time', 'end_time', 'last_update']:
                if state_dict.get(key):
                    state_dict[key] = state_dict[key].isoformat()
            
            # Write to file
            with open(self.state_file_path, 'w') as f:
                json.dump(state_dict, f, indent=2)
            
            logger.debug(f"Saved state for workflow: {workflow_id}")
            
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def load_state(self) -> Optional[ComfyUIWorkflowState]:
        """
        Load workflow state from persistent file.
        
        Returns:
            ComfyUIWorkflowState or None
        """
        if not os.path.exists(self.state_file_path):
            return None
        
        try:
            with open(self.state_file_path, 'r') as f:
                state_dict = json.load(f)
            
            # Convert ISO format strings to datetime
            for key in ['queue_time', 'start_time', 'end_time', 'last_update']:
                if state_dict.get(key):
                    state_dict[key] = datetime.fromisoformat(state_dict[key])
            
            # Convert status enums
            state_dict['status'] = WorkflowStatus(state_dict['status'])
            
            # Convert node states
            if 'nodes' in state_dict:
                nodes = []
                for node_data in state_dict['nodes']:
                    node_data['status'] = NodeStatus(node_data['status'])
                    nodes.append(ComfyUINodeState(**node_data))
                state_dict['nodes'] = nodes
            
            # Convert output files
            if 'outputs' in state_dict:
                outputs = []
                for output_data in state_dict['outputs']:
                    outputs.append(ComfyUIOutputFile(**output_data))
                state_dict['outputs'] = outputs
            
            state = ComfyUIWorkflowState(**state_dict)
            
            # Store in memory
            with self._lock:
                self.workflow_states[state.workflow_id] = state
            
            logger.info(f"Loaded state for workflow: {state.workflow_id}")
            return state
            
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return None
    
    def get_workflow_state(self, workflow_id: str) -> Optional[ComfyUIWorkflowState]:
        """
        Get current workflow state.
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            ComfyUIWorkflowState or None
        """
        with self._lock:
            return self.workflow_states.get(workflow_id)
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """
        Cancel a running workflow.
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            True if cancellation was initiated
        """
        with self._lock:
            stop_flag = self.stop_flags.get(workflow_id)
            if stop_flag:
                stop_flag.set()
                logger.info(f"Cancellation requested for workflow: {workflow_id}")
                return True
            
            # If not running, mark as cancelled
            state = self.workflow_states.get(workflow_id)
            if state and state.status in [WorkflowStatus.QUEUED, WorkflowStatus.EXECUTING]:
                self._set_cancelled(workflow_id)
                return True
        
        return False
    
    def is_workflow_active(self, workflow_id: str) -> bool:
        """
        Check if a workflow is currently executing.
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            True if workflow is active
        """
        with self._lock:
            return workflow_id in self.active_workflows
    
    def cleanup_completed_workflows(self, max_age_seconds: int = 3600):
        """
        Remove old completed workflow states from memory.
        
        Args:
            max_age_seconds: Maximum age for completed workflows
        """
        current_time = datetime.now()
        workflows_to_remove = []
        
        with self._lock:
            for workflow_id, state in self.workflow_states.items():
                if state.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
                    if state.end_time:
                        age = (current_time - state.end_time).total_seconds()
                        if age > max_age_seconds:
                            workflows_to_remove.append(workflow_id)
            
            for workflow_id in workflows_to_remove:
                del self.workflow_states[workflow_id]
                logger.info(f"Cleaned up old workflow: {workflow_id}")


# Global executor instance
_executor_instance: Optional[ComfyUIWorkflowExecutor] = None


def get_executor() -> ComfyUIWorkflowExecutor:
    """Get or create global executor instance."""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = ComfyUIWorkflowExecutor()
    return _executor_instance
