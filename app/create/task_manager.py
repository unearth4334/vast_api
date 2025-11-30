#!/usr/bin/env python3
"""
Task Manager - Manage workflow execution tasks and their lifecycle.
Provides in-memory task storage with thread-safe operations.
"""

import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Execution task status values"""
    QUEUED = 'queued'
    UPLOADING = 'uploading'
    RUNNING = 'running'
    COMPLETE = 'complete'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


@dataclass
class TaskProgress:
    """Progress information for a running task"""
    current_step: int = 0
    total_steps: int = 0
    percent: float = 0.0
    message: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'percent': self.percent,
            'message': self.message,
        }


@dataclass
class ExecutionTask:
    """Represents a workflow execution task"""
    task_id: str
    workflow_id: str
    ssh_connection: str
    options: Dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.QUEUED
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: TaskProgress = field(default_factory=TaskProgress)
    outputs: List[Dict] = field(default_factory=list)
    error: Optional[str] = None
    comfyui_prompt_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    _cancel_requested: bool = field(default=False, repr=False)
    
    def __post_init__(self):
        """Initialize task"""
        if self.started_at is None:
            self.started_at = datetime.now(timezone.utc)
    
    def get_elapsed_seconds(self) -> int:
        """Get elapsed time in seconds"""
        if not self.started_at:
            return 0
        
        end_time = self.completed_at or datetime.now(timezone.utc)
        return int((end_time - self.started_at).total_seconds())
    
    def get_estimated_remaining(self) -> Optional[int]:
        """Estimate remaining time based on progress"""
        if self.progress.percent == 0:
            return None
        
        elapsed = self.get_elapsed_seconds()
        if elapsed == 0:
            return None
        
        total_estimated = elapsed / (self.progress.percent / 100)
        return max(0, int(total_estimated - elapsed))
    
    def get_progress(self) -> Dict:
        """Get progress information"""
        return self.progress.to_dict()
    
    def get_outputs(self) -> List[Dict]:
        """Get output files"""
        return self.outputs
    
    def update_progress(self, current: int, total: int, message: str = ""):
        """Update progress"""
        self.progress.current_step = current
        self.progress.total_steps = total
        self.progress.percent = (current / total * 100) if total > 0 else 0
        self.progress.message = message
    
    def add_output(self, output: Dict):
        """Add an output file"""
        self.outputs.append(output)
    
    def set_status(self, status: TaskStatus):
        """Update task status"""
        self.status = status
        if status in (TaskStatus.COMPLETE, TaskStatus.FAILED, TaskStatus.CANCELLED):
            self.completed_at = datetime.now(timezone.utc)
    
    def request_cancel(self):
        """Request task cancellation"""
        self._cancel_requested = True
    
    def is_cancel_requested(self) -> bool:
        """Check if cancellation was requested"""
        return self._cancel_requested
    
    def cancel(self):
        """Cancel the task"""
        self._cancel_requested = True
        self.set_status(TaskStatus.CANCELLED)
        logger.info(f"Task {self.task_id} cancelled")
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response"""
        return {
            'task_id': self.task_id,
            'workflow_id': self.workflow_id,
            'status': self.status.value,
            'progress': self.get_progress(),
            'started_at': self.started_at.isoformat() + 'Z' if self.started_at else None,
            'completed_at': self.completed_at.isoformat() + 'Z' if self.completed_at else None,
            'elapsed_seconds': self.get_elapsed_seconds(),
            'estimated_remaining_seconds': self.get_estimated_remaining(),
            'outputs': self.get_outputs(),
            'error': self.error if self.status == TaskStatus.FAILED else None,
            'metadata': self.metadata,
        }


class TaskManager:
    """Manage execution tasks with thread-safe operations"""
    
    _tasks: Dict[str, ExecutionTask] = {}
    _lock = threading.Lock()
    _instance = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def create_task(cls, workflow_id: str, ssh_connection: str, 
                   options: Optional[Dict] = None, metadata: Optional[Dict] = None) -> ExecutionTask:
        """Create and register a new task"""
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        task = ExecutionTask(
            task_id=task_id,
            workflow_id=workflow_id,
            ssh_connection=ssh_connection,
            options=options or {},
            metadata=metadata or {}
        )
        cls.register_task(task_id, task)
        return task
    
    @classmethod
    def register_task(cls, task_id: str, task: ExecutionTask):
        """Register a task"""
        with cls._lock:
            cls._tasks[task_id] = task
            logger.info(f"Registered task {task_id} for workflow {task.workflow_id}")
    
    @classmethod
    def get_task(cls, task_id: str) -> Optional[ExecutionTask]:
        """Get task by ID"""
        with cls._lock:
            return cls._tasks.get(task_id)
    
    @classmethod
    def list_tasks(cls, workflow_id: Optional[str] = None, 
                  status: Optional[TaskStatus] = None) -> List[ExecutionTask]:
        """List tasks with optional filtering"""
        with cls._lock:
            tasks = list(cls._tasks.values())
        
        if workflow_id:
            tasks = [t for t in tasks if t.workflow_id == workflow_id]
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        return tasks
    
    @classmethod
    def update_task_status(cls, task_id: str, status: TaskStatus, 
                          error: Optional[str] = None) -> bool:
        """Update task status"""
        with cls._lock:
            task = cls._tasks.get(task_id)
            if not task:
                return False
            task.set_status(status)
            if error:
                task.error = error
            return True
    
    @classmethod
    def update_task_progress(cls, task_id: str, current: int, total: int, 
                            message: str = "") -> bool:
        """Update task progress"""
        with cls._lock:
            task = cls._tasks.get(task_id)
            if not task:
                return False
            task.update_progress(current, total, message)
            return True
    
    @classmethod
    def cancel_task(cls, task_id: str) -> bool:
        """Cancel a task"""
        with cls._lock:
            task = cls._tasks.get(task_id)
            if not task:
                return False
            
            if task.status in (TaskStatus.COMPLETE, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return False
            
            task.cancel()
            return True
    
    @classmethod
    def cleanup_old_tasks(cls, max_age_hours: int = 24):
        """Remove tasks older than max_age_hours"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        with cls._lock:
            to_remove = [
                task_id for task_id, task in cls._tasks.items()
                if task.started_at and task.started_at < cutoff
            ]
            for task_id in to_remove:
                del cls._tasks[task_id]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old tasks")
    
    @classmethod
    def get_active_tasks_count(cls) -> int:
        """Get count of active (non-terminal) tasks"""
        with cls._lock:
            return sum(
                1 for task in cls._tasks.values()
                if task.status in (TaskStatus.QUEUED, TaskStatus.UPLOADING, TaskStatus.RUNNING)
            )
    
    @classmethod
    def clear_all_tasks(cls):
        """Clear all tasks (for testing)"""
        with cls._lock:
            cls._tasks.clear()
