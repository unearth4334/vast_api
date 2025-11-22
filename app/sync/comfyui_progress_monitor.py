"""
ComfyUI Progress Monitor
Monitors ComfyUI workflow execution via WebSocket and HTTP polling.
"""

import json
import logging
import time
import requests
import websocket
import threading
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
from .comfyui_workflow_state import (
    ComfyUIWorkflowState, ComfyUINodeStatus, 
    ComfyUIWorkflowStatus, ComfyUIOutputFile
)

logger = logging.getLogger(__name__)


class ComfyUIProgressMonitor:
    """Monitor ComfyUI workflow execution progress via WebSocket and HTTP."""
    
    def __init__(self, comfyui_host: str = "localhost", comfyui_port: int = 18188):
        """
        Initialize the progress monitor.
        
        Args:
            comfyui_host: ComfyUI API host (usually localhost when via SSH tunnel)
            comfyui_port: ComfyUI API port
        """
        self.comfyui_host = comfyui_host
        self.comfyui_port = comfyui_port
        self.api_url = f"http://{comfyui_host}:{comfyui_port}"
        self.ws_url = f"ws://{comfyui_host}:{comfyui_port}/ws"
        self.client_id = f"vast_api_{int(time.time())}"
        
        self._ws = None
        self._ws_thread = None
        self._stop_event = threading.Event()
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        logger.info(f"ComfyUIProgressMonitor initialized - API: {self.api_url}, WS: {self.ws_url}")
    
    def register_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback for progress updates."""
        self._callbacks.append(callback)
    
    def _notify_callbacks(self, event_data: Dict[str, Any]):
        """Notify all registered callbacks of an event."""
        for callback in self._callbacks:
            try:
                callback(event_data)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def get_queue_status(self) -> Optional[Dict[str, Any]]:
        """
        Get current queue status from ComfyUI.
        
        Returns:
            Queue status dictionary or None on error
        """
        try:
            response = requests.get(f"{self.api_url}/queue", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return None
    
    def get_queue_position(self, prompt_id: str) -> Optional[int]:
        """
        Get queue position for a specific prompt.
        
        Args:
            prompt_id: ComfyUI prompt ID
            
        Returns:
            Queue position (0-based) or None if not in queue
        """
        queue_status = self.get_queue_status()
        if not queue_status:
            return None
        
        # Check pending queue
        pending = queue_status.get('queue_pending', [])
        for idx, item in enumerate(pending):
            if len(item) >= 2 and item[1] == prompt_id:
                return idx
        
        # Check running queue (position 0)
        running = queue_status.get('queue_running', [])
        for item in running:
            if len(item) >= 2 and item[1] == prompt_id:
                return 0
        
        return None
    
    def get_history(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """
        Get execution history for a prompt.
        
        Args:
            prompt_id: ComfyUI prompt ID
            
        Returns:
            History dictionary or None if not found
        """
        try:
            response = requests.get(f"{self.api_url}/history/{prompt_id}", timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get(prompt_id)
        except Exception as e:
            logger.error(f"Failed to get history for {prompt_id}: {e}")
            return None
    
    def is_execution_complete(self, prompt_id: str) -> tuple[bool, bool]:
        """
        Check if execution is complete for a prompt.
        
        Args:
            prompt_id: ComfyUI prompt ID
            
        Returns:
            Tuple of (is_complete, is_success)
        """
        history = self.get_history(prompt_id)
        if not history:
            return False, False
        
        # Check if there are any outputs (indicates completion)
        outputs = history.get('outputs', {})
        has_outputs = len(outputs) > 0
        
        # Check status
        status = history.get('status', {})
        completed = status.get('completed', False)
        
        # Check for errors
        messages = status.get('messages', [])
        has_errors = any(msg[0] == 'execution_error' for msg in messages if isinstance(msg, list))
        
        is_complete = completed or has_outputs
        is_success = is_complete and not has_errors
        
        return is_complete, is_success
    
    def get_execution_outputs(self, prompt_id: str) -> List[ComfyUIOutputFile]:
        """
        Get list of output files from execution history.
        
        Args:
            prompt_id: ComfyUI prompt ID
            
        Returns:
            List of ComfyUIOutputFile objects
        """
        history = self.get_history(prompt_id)
        if not history:
            return []
        
        outputs = []
        output_data = history.get('outputs', {})
        
        for node_id, node_outputs in output_data.items():
            if not isinstance(node_outputs, dict):
                continue
            
            # Check for images
            images = node_outputs.get('images', [])
            for img in images:
                if isinstance(img, dict) and 'filename' in img:
                    output = ComfyUIOutputFile(
                        filename=img['filename'],
                        file_type=img.get('type', 'output'),
                        remote_path=f"/workspace/ComfyUI/output/{img['filename']}",
                        downloaded=False
                    )
                    outputs.append(output)
            
            # Check for videos, audio, etc.
            for file_type in ['videos', 'audio', 'gifs']:
                files = node_outputs.get(file_type, [])
                for file_info in files:
                    if isinstance(file_info, dict) and 'filename' in file_info:
                        output = ComfyUIOutputFile(
                            filename=file_info['filename'],
                            file_type=file_type.rstrip('s'),  # videos -> video
                            remote_path=f"/workspace/ComfyUI/output/{file_info['filename']}",
                            downloaded=False
                        )
                        outputs.append(output)
        
        return outputs
    
    def monitor_execution_polling(
        self, 
        prompt_id: str, 
        state: ComfyUIWorkflowState,
        update_callback: Callable[[ComfyUIWorkflowState], None],
        poll_interval: float = 2.0,
        timeout: float = 3600.0
    ) -> bool:
        """
        Monitor workflow execution using HTTP polling (fallback method).
        
        Args:
            prompt_id: ComfyUI prompt ID
            state: ComfyUIWorkflowState to update
            update_callback: Function to call with state updates
            poll_interval: Seconds between polls
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if execution completed successfully, False otherwise
        """
        logger.info(f"Starting polling monitor for prompt {prompt_id}")
        start_time = time.time()
        
        state.status = ComfyUIWorkflowStatus.EXECUTING
        state.start_time = datetime.now().isoformat()
        update_callback(state)
        
        while time.time() - start_time < timeout:
            # Check queue position
            queue_pos = self.get_queue_position(prompt_id)
            if queue_pos is not None:
                state.queue_position = queue_pos
                if queue_pos > 0:
                    state.status = ComfyUIWorkflowStatus.QUEUED
                else:
                    state.status = ComfyUIWorkflowStatus.EXECUTING
                update_callback(state)
            
            # Check completion
            is_complete, is_success = self.is_execution_complete(prompt_id)
            
            if is_complete:
                if is_success:
                    # Get outputs
                    outputs = self.get_execution_outputs(prompt_id)
                    state.outputs = outputs
                    state.set_completed()
                    logger.info(f"Workflow {prompt_id} completed successfully with {len(outputs)} outputs")
                else:
                    # Check for error details
                    history = self.get_history(prompt_id)
                    error_msg = "Execution failed"
                    if history:
                        messages = history.get('status', {}).get('messages', [])
                        for msg in messages:
                            if isinstance(msg, list) and len(msg) > 1 and msg[0] == 'execution_error':
                                error_msg = str(msg[1])
                                break
                    state.set_error(error_msg)
                    logger.error(f"Workflow {prompt_id} failed: {error_msg}")
                
                update_callback(state)
                return is_success
            
            # Update progress estimate based on queue position
            if state.queue_position == 0 and state.total_nodes > 0:
                # Rough estimate: assume 50% progress if executing
                state.progress_percent = 50.0
                update_callback(state)
            
            time.sleep(poll_interval)
        
        # Timeout
        state.set_error(f"Execution monitoring timed out after {timeout} seconds")
        update_callback(state)
        logger.error(f"Monitoring timed out for prompt {prompt_id}")
        return False
    
    def _on_ws_message(self, ws, message: str, state: ComfyUIWorkflowState, 
                      update_callback: Callable[[ComfyUIWorkflowState], None]):
        """Handle WebSocket message."""
        try:
            data = json.loads(message)
            event_type = data.get('type')
            
            if event_type == 'status':
                # Queue status update
                status_data = data.get('data', {})
                queue_remaining = status_data.get('status', {}).get('exec_info', {}).get('queue_remaining', 0)
                state.queue_position = queue_remaining
                update_callback(state)
                
            elif event_type == 'executing':
                # Node execution event
                node_id = data.get('data', {}).get('node')
                prompt_id = data.get('data', {}).get('prompt_id')
                
                if node_id is None:
                    # Execution complete
                    logger.info(f"Execution complete signal received for {prompt_id}")
                else:
                    # Node started executing
                    state.current_node = node_id
                    state.update_node_status(node_id, ComfyUINodeStatus.EXECUTING)
                    
                    # Update completed count (assume previous nodes are done)
                    completed = sum(1 for n in state.nodes 
                                  if n.status in [ComfyUINodeStatus.EXECUTED, ComfyUINodeStatus.CACHED])
                    state.update_progress(completed, node_id)
                    
                    logger.debug(f"Node {node_id} executing ({state.completed_nodes}/{state.total_nodes})")
                
                update_callback(state)
                
            elif event_type == 'progress':
                # Progress update for current node
                value = data.get('data', {}).get('value', 0)
                max_value = data.get('data', {}).get('max', 1)
                
                if max_value > 0 and state.current_node:
                    node_progress = (value / max_value) * 100
                    state.update_node_status(state.current_node, ComfyUINodeStatus.EXECUTING, progress=node_progress)
                    update_callback(state)
                
            elif event_type == 'executed':
                # Node execution completed
                node_id = data.get('data', {}).get('node')
                if node_id:
                    state.update_node_status(node_id, ComfyUINodeStatus.EXECUTED, progress=100.0)
                    state.update_progress(state.completed_nodes + 1)
                    update_callback(state)
                    logger.debug(f"Node {node_id} completed")
            
            elif event_type == 'execution_error':
                # Execution error
                error_data = data.get('data', {})
                node_id = error_data.get('node_id')
                error_msg = error_data.get('exception_message', 'Unknown error')
                
                state.set_error(error_msg, node_id)
                update_callback(state)
                logger.error(f"Execution error at node {node_id}: {error_msg}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse WebSocket message: {e}")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
    
    def _on_ws_error(self, ws, error):
        """Handle WebSocket error."""
        logger.error(f"WebSocket error: {error}")
    
    def _on_ws_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")
    
    def _on_ws_open(self, ws):
        """Handle WebSocket open."""
        logger.info("WebSocket connection opened")
    
    def monitor_execution_websocket(
        self,
        prompt_id: str,
        state: ComfyUIWorkflowState,
        update_callback: Callable[[ComfyUIWorkflowState], None],
        timeout: float = 3600.0
    ) -> bool:
        """
        Monitor workflow execution using WebSocket (preferred method).
        
        Args:
            prompt_id: ComfyUI prompt ID
            state: ComfyUIWorkflowState to update
            update_callback: Function to call with state updates
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if execution completed successfully, False otherwise
        """
        logger.info(f"Starting WebSocket monitor for prompt {prompt_id}")
        
        try:
            # Update state
            state.status = ComfyUIWorkflowStatus.EXECUTING
            state.start_time = datetime.now().isoformat()
            update_callback(state)
            
            # Create WebSocket connection
            ws_url_with_client = f"{self.ws_url}?clientId={self.client_id}"
            
            self._ws = websocket.WebSocketApp(
                ws_url_with_client,
                on_message=lambda ws, msg: self._on_ws_message(ws, msg, state, update_callback),
                on_error=self._on_ws_error,
                on_close=self._on_ws_close,
                on_open=self._on_ws_open
            )
            
            # Run WebSocket in separate thread with timeout
            ws_thread = threading.Thread(target=self._ws.run_forever, daemon=True)
            ws_thread.start()
            
            # Wait for completion or timeout
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Check if execution is complete via HTTP
                is_complete, is_success = self.is_execution_complete(prompt_id)
                
                if is_complete:
                    # Get outputs
                    if is_success:
                        outputs = self.get_execution_outputs(prompt_id)
                        state.outputs = outputs
                        state.set_completed()
                        logger.info(f"Workflow {prompt_id} completed via WebSocket with {len(outputs)} outputs")
                    
                    # Close WebSocket
                    self._ws.close()
                    return is_success
                
                time.sleep(1.0)
            
            # Timeout
            self._ws.close()
            state.set_error(f"WebSocket monitoring timed out after {timeout} seconds")
            update_callback(state)
            logger.error(f"WebSocket monitoring timed out for prompt {prompt_id}")
            return False
            
        except Exception as e:
            logger.error(f"WebSocket monitoring failed: {e}")
            # Fall back to polling
            logger.info("Falling back to HTTP polling")
            return self.monitor_execution_polling(prompt_id, state, update_callback, timeout=timeout)
    
    def cancel_execution(self, prompt_id: str) -> bool:
        """
        Cancel a running execution.
        
        Args:
            prompt_id: ComfyUI prompt ID to cancel
            
        Returns:
            True if cancellation was successful
        """
        try:
            response = requests.post(
                f"{self.api_url}/interrupt",
                timeout=5
            )
            response.raise_for_status()
            logger.info(f"Cancelled execution for prompt {prompt_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel execution: {e}")
            return False
