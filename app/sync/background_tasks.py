"""
Background Task Manager

Manages asynchronous background tasks with progress tracking.
Decouples long-running operations from HTTP request threads.
"""

import threading
import time
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """Manages background tasks with thread-safe state tracking."""
    
    def __init__(self):
        """Initialize the task manager."""
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self._cleanup_interval = 3600  # Clean up old tasks after 1 hour
        self._max_task_age = 7200  # Keep task records for 2 hours
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_old_tasks,
            daemon=True,
            name="background-task-cleanup"
        )
        self._cleanup_thread.start()
        logger.info("BackgroundTaskManager initialized")
    
    def start_task(self, task_id: str, target_func: Callable, *args, **kwargs) -> str:
        """
        Start a background task.
        
        Args:
            task_id: Unique identifier for the task
            target_func: Function to run in background
            *args: Positional arguments for target_func
            **kwargs: Keyword arguments for target_func
            
        Returns:
            task_id of the started task
        """
        with self.lock:
            if task_id in self.tasks and self.tasks[task_id]['thread'].is_alive():
                logger.warning(f"Task {task_id} is already running")
                raise ValueError(f"Task {task_id} is already running")
            
            # Create wrapper function to track completion
            def wrapped_target():
                try:
                    logger.info(f"Starting background task {task_id}")
                    target_func(*args, **kwargs)
                    with self.lock:
                        if task_id in self.tasks:
                            self.tasks[task_id]['status']['state'] = 'completed'
                            self.tasks[task_id]['status']['completed_at'] = time.time()
                    logger.info(f"Background task {task_id} completed successfully")
                except Exception as e:
                    logger.error(f"Background task {task_id} failed: {e}", exc_info=True)
                    with self.lock:
                        if task_id in self.tasks:
                            self.tasks[task_id]['status']['state'] = 'failed'
                            self.tasks[task_id]['status']['error'] = str(e)
                            self.tasks[task_id]['status']['completed_at'] = time.time()
            
            # Create and start thread
            thread = threading.Thread(
                target=wrapped_target,
                daemon=True,
                name=f"task-{task_id}"
            )
            
            self.tasks[task_id] = {
                'thread': thread,
                'status': {
                    'state': 'running',
                    'started_at': time.time(),
                    'task_id': task_id
                }
            }
            
            thread.start()
            logger.info(f"Started background task {task_id}")
            return task_id
    
    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a task.
        
        Args:
            task_id: Unique identifier for the task
            
        Returns:
            Status dictionary or None if task not found
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if task:
                # Add thread alive status
                status = task['status'].copy()
                status['thread_alive'] = task['thread'].is_alive()
                return status
            return None
    
    def is_task_running(self, task_id: str) -> bool:
        """
        Check if a task is currently running.
        
        Args:
            task_id: Unique identifier for the task
            
        Returns:
            True if task is running, False otherwise
        """
        with self.lock:
            task = self.tasks.get(task_id)
            return task is not None and task['thread'].is_alive()
    
    def cleanup_task(self, task_id: str) -> bool:
        """
        Remove a task from tracking.
        
        Args:
            task_id: Unique identifier for the task
            
        Returns:
            True if task was removed, False otherwise
        """
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task['thread'].is_alive():
                    logger.warning(f"Cannot cleanup running task {task_id}")
                    return False
                del self.tasks[task_id]
                logger.info(f"Cleaned up task {task_id}")
                return True
            return False
    
    def _cleanup_old_tasks(self):
        """Background thread that periodically cleans up old completed tasks."""
        while True:
            try:
                time.sleep(self._cleanup_interval)
                current_time = time.time()
                
                with self.lock:
                    tasks_to_remove = []
                    for task_id, task in self.tasks.items():
                        # Remove tasks that completed more than max_task_age seconds ago
                        if not task['thread'].is_alive():
                            completed_at = task['status'].get('completed_at', 
                                                            task['status']['started_at'])
                            if current_time - completed_at > self._max_task_age:
                                tasks_to_remove.append(task_id)
                    
                    for task_id in tasks_to_remove:
                        del self.tasks[task_id]
                        logger.info(f"Auto-cleaned up old task {task_id}")
                        
                    if tasks_to_remove:
                        logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
                        
            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}", exc_info=True)
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all tasks.
        
        Returns:
            Dictionary of all tasks with their status
        """
        with self.lock:
            result = {}
            for task_id, task in self.tasks.items():
                status = task['status'].copy()
                status['thread_alive'] = task['thread'].is_alive()
                result[task_id] = status
            return result


# Global task manager instance
_task_manager = None


def get_task_manager() -> BackgroundTaskManager:
    """
    Get or create the global task manager instance.
    
    Returns:
        The global BackgroundTaskManager instance
    """
    global _task_manager
    if _task_manager is None:
        _task_manager = BackgroundTaskManager()
    return _task_manager
