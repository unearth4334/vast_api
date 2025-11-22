"""
ComfyUI Workflow State Extension
Extends workflow state management for ComfyUI-specific workflow execution tracking.
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class ComfyUIWorkflowStatus(str, Enum):
    """ComfyUI workflow execution status."""
    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ComfyUINodeStatus(str, Enum):
    """ComfyUI node execution status."""
    PENDING = "pending"
    EXECUTING = "executing"
    EXECUTED = "executed"
    CACHED = "cached"
    FAILED = "failed"


@dataclass
class ComfyUINodeState:
    """State of a single ComfyUI node."""
    node_id: str
    node_type: str
    status: ComfyUINodeStatus
    progress: float = 0.0  # 0-100
    message: Optional[str] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'node_id': self.node_id,
            'node_type': self.node_type,
            'status': self.status.value if isinstance(self.status, ComfyUINodeStatus) else self.status,
            'progress': self.progress,
            'message': self.message,
            'error': self.error,
            'execution_time': self.execution_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComfyUINodeState':
        """Create from dictionary."""
        return cls(
            node_id=data['node_id'],
            node_type=data['node_type'],
            status=ComfyUINodeStatus(data['status']) if isinstance(data['status'], str) else data['status'],
            progress=data.get('progress', 0.0),
            message=data.get('message'),
            error=data.get('error'),
            execution_time=data.get('execution_time')
        )


@dataclass
class ComfyUIOutputFile:
    """Information about a generated output file."""
    filename: str
    file_type: str  # image, video, audio, etc.
    remote_path: str
    local_path: Optional[str] = None
    downloaded: bool = False
    size_bytes: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'filename': self.filename,
            'type': self.file_type,
            'remote_path': self.remote_path,
            'local_path': self.local_path,
            'downloaded': self.downloaded,
            'size_bytes': self.size_bytes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComfyUIOutputFile':
        """Create from dictionary."""
        return cls(
            filename=data['filename'],
            file_type=data.get('type', 'unknown'),
            remote_path=data.get('remote_path', data.get('path', '')),
            local_path=data.get('local_path'),
            downloaded=data.get('downloaded', False),
            size_bytes=data.get('size_bytes')
        )


@dataclass
class ComfyUIWorkflowState:
    """Complete state for ComfyUI workflow execution."""
    workflow_id: str
    workflow_type: str = "comfyui_workflow"
    workflow_name: Optional[str] = None
    prompt_id: Optional[str] = None  # ComfyUI prompt ID
    ssh_connection: str = ""
    workflow_file: str = ""
    status: ComfyUIWorkflowStatus = ComfyUIWorkflowStatus.QUEUED
    
    # Progress tracking
    queue_position: Optional[int] = None
    current_node: Optional[str] = None
    total_nodes: int = 0
    completed_nodes: int = 0
    progress_percent: float = 0.0
    
    # Node execution details
    nodes: List[ComfyUINodeState] = field(default_factory=list)
    
    # Timing information
    queue_time: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    last_update: Optional[str] = None
    estimated_completion: Optional[str] = None
    
    # Output tracking
    outputs: List[ComfyUIOutputFile] = field(default_factory=list)
    
    # Error tracking
    error_message: Optional[str] = None
    failed_node: Optional[str] = None
    
    # Additional metadata
    input_images: List[str] = field(default_factory=list)
    output_dir: str = "/tmp/comfyui_outputs"
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Ensure status is enum
        if isinstance(self.status, str):
            self.status = ComfyUIWorkflowStatus(self.status)
        
        # Convert node dictionaries to NodeState objects
        if self.nodes and isinstance(self.nodes[0], dict):
            self.nodes = [ComfyUINodeState.from_dict(n) for n in self.nodes]
        
        # Convert output dictionaries to OutputFile objects
        if self.outputs and isinstance(self.outputs[0], dict):
            self.outputs = [ComfyUIOutputFile.from_dict(o) for o in self.outputs]
        
        # Set timestamps if not present
        if not self.queue_time:
            self.queue_time = datetime.now().isoformat()
        if not self.last_update:
            self.last_update = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'workflow_id': self.workflow_id,
            'type': self.workflow_type,
            'workflow_name': self.workflow_name,
            'prompt_id': self.prompt_id,
            'ssh_connection': self.ssh_connection,
            'workflow_file': self.workflow_file,
            'status': self.status.value if isinstance(self.status, ComfyUIWorkflowStatus) else self.status,
            'progress': {
                'queue_position': self.queue_position,
                'current_node': self.current_node,
                'total_nodes': self.total_nodes,
                'completed_nodes': self.completed_nodes,
                'progress_percent': self.progress_percent
            },
            'nodes': [n.to_dict() if hasattr(n, 'to_dict') else n for n in self.nodes],
            'timing': {
                'queue_time': self.queue_time,
                'start_time': self.start_time,
                'end_time': self.end_time,
                'last_update': self.last_update,
                'estimated_completion': self.estimated_completion
            },
            'outputs': [o.to_dict() if hasattr(o, 'to_dict') else o for o in self.outputs],
            'error': {
                'message': self.error_message,
                'failed_node': self.failed_node
            } if self.error_message else None,
            'input_images': self.input_images,
            'output_dir': self.output_dir
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComfyUIWorkflowState':
        """Create from dictionary."""
        # Extract nested progress data
        progress = data.get('progress', {})
        timing = data.get('timing', {})
        error = data.get('error', {})
        
        return cls(
            workflow_id=data['workflow_id'],
            workflow_type=data.get('type', 'comfyui_workflow'),
            workflow_name=data.get('workflow_name'),
            prompt_id=data.get('prompt_id'),
            ssh_connection=data.get('ssh_connection', ''),
            workflow_file=data.get('workflow_file', ''),
            status=ComfyUIWorkflowStatus(data['status']) if isinstance(data['status'], str) else data['status'],
            queue_position=progress.get('queue_position'),
            current_node=progress.get('current_node'),
            total_nodes=progress.get('total_nodes', 0),
            completed_nodes=progress.get('completed_nodes', 0),
            progress_percent=progress.get('progress_percent', 0.0),
            nodes=[ComfyUINodeState.from_dict(n) if isinstance(n, dict) else n 
                   for n in data.get('nodes', [])],
            queue_time=timing.get('queue_time'),
            start_time=timing.get('start_time'),
            end_time=timing.get('end_time'),
            last_update=timing.get('last_update'),
            estimated_completion=timing.get('estimated_completion'),
            outputs=[ComfyUIOutputFile.from_dict(o) if isinstance(o, dict) else o 
                     for o in data.get('outputs', [])],
            error_message=error.get('message') if error else None,
            failed_node=error.get('failed_node') if error else None,
            input_images=data.get('input_images', []),
            output_dir=data.get('output_dir', '/tmp/comfyui_outputs')
        )
    
    def update_progress(self, completed_nodes: int, current_node: Optional[str] = None):
        """Update progress information."""
        self.completed_nodes = completed_nodes
        if current_node:
            self.current_node = current_node
        
        if self.total_nodes > 0:
            self.progress_percent = (self.completed_nodes / self.total_nodes) * 100
        
        self.last_update = datetime.now().isoformat()
    
    def update_node_status(self, node_id: str, status: ComfyUINodeStatus, 
                          progress: Optional[float] = None,
                          message: Optional[str] = None,
                          error: Optional[str] = None):
        """Update status of a specific node."""
        for node in self.nodes:
            if node.node_id == node_id:
                node.status = status
                if progress is not None:
                    node.progress = progress
                if message is not None:
                    node.message = message
                if error is not None:
                    node.error = error
                break
        
        self.last_update = datetime.now().isoformat()
    
    def add_output(self, filename: str, file_type: str, remote_path: str):
        """Add an output file to the state."""
        output = ComfyUIOutputFile(
            filename=filename,
            file_type=file_type,
            remote_path=remote_path
        )
        self.outputs.append(output)
        self.last_update = datetime.now().isoformat()
    
    def mark_output_downloaded(self, filename: str, local_path: str):
        """Mark an output file as downloaded."""
        for output in self.outputs:
            if output.filename == filename:
                output.downloaded = True
                output.local_path = local_path
                break
        
        self.last_update = datetime.now().isoformat()
    
    def set_error(self, error_message: str, failed_node: Optional[str] = None):
        """Set error state."""
        self.status = ComfyUIWorkflowStatus.FAILED
        self.error_message = error_message
        self.failed_node = failed_node
        self.end_time = datetime.now().isoformat()
        self.last_update = self.end_time
    
    def set_completed(self):
        """Mark workflow as completed."""
        self.status = ComfyUIWorkflowStatus.COMPLETED
        self.progress_percent = 100.0
        self.end_time = datetime.now().isoformat()
        self.last_update = self.end_time
    
    def set_cancelled(self):
        """Mark workflow as cancelled."""
        self.status = ComfyUIWorkflowStatus.CANCELLED
        self.end_time = datetime.now().isoformat()
        self.last_update = self.end_time


def create_comfyui_workflow_state(
    workflow_id: str,
    ssh_connection: str,
    workflow_file: str,
    workflow_name: Optional[str] = None,
    input_images: Optional[List[str]] = None,
    output_dir: str = "/tmp/comfyui_outputs"
) -> ComfyUIWorkflowState:
    """
    Create a new ComfyUI workflow state.
    
    Args:
        workflow_id: Unique identifier for the workflow
        ssh_connection: SSH connection string
        workflow_file: Path to workflow JSON file
        workflow_name: Optional human-readable workflow name
        input_images: Optional list of input image paths
        output_dir: Directory for output files
        
    Returns:
        ComfyUIWorkflowState instance
    """
    return ComfyUIWorkflowState(
        workflow_id=workflow_id,
        workflow_name=workflow_name,
        ssh_connection=ssh_connection,
        workflow_file=workflow_file,
        input_images=input_images or [],
        output_dir=output_dir
    )


def parse_workflow_nodes(workflow_data: Dict[str, Any]) -> List[ComfyUINodeState]:
    """
    Parse workflow JSON to extract node information.
    
    Args:
        workflow_data: Workflow JSON data
        
    Returns:
        List of ComfyUINodeState objects
    """
    nodes = []
    
    # ComfyUI workflows are dictionaries where keys are node IDs
    for node_id, node_data in workflow_data.items():
        if isinstance(node_data, dict) and 'class_type' in node_data:
            node = ComfyUINodeState(
                node_id=str(node_id),
                node_type=node_data['class_type'],
                status=ComfyUINodeStatus.PENDING
            )
            nodes.append(node)
    
    return nodes
