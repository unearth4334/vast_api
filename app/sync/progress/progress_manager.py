"""
Progress tracking manager
"""

import logging
from typing import Dict, List, Callable, Optional
from datetime import datetime

from ..models import SyncProgress

logger = logging.getLogger(__name__)


class ProgressManager:
    """Manage progress tracking for sync operations."""
    
    def __init__(self):
        self._progress_store: Dict[str, SyncProgress] = {}
        self._callbacks: List[Callable] = []
    
    def register_callback(self, callback: Callable[[SyncProgress], None]):
        """Register a callback for progress updates."""
        self._callbacks.append(callback)
    
    def create_progress(self, sync_id: str, job_id: str) -> SyncProgress:
        """Create a new progress tracker."""
        progress = SyncProgress(
            sync_id=sync_id,
            job_id=job_id,
            status='initializing',
            progress_percent=0.0,
            current_stage='initializing',
            start_time=datetime.now(),
            last_update=datetime.now()
        )
        
        self._progress_store[sync_id] = progress
        return progress
    
    def get_progress(self, sync_id: str) -> Optional[SyncProgress]:
        """Get progress for a sync operation."""
        return self._progress_store.get(sync_id)
    
    def update_progress(self, sync_id: str, updates: dict):
        """Update progress for a sync operation."""
        if sync_id not in self._progress_store:
            logger.warning(f"Unknown sync_id: {sync_id}")
            return
        
        progress = self._progress_store[sync_id]
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(progress, key):
                setattr(progress, key, value)
        
        progress.last_update = datetime.now()
        
        # Calculate derived metrics
        self._update_derived_metrics(progress)
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Progress callback failed: {e}")
    
    def _update_derived_metrics(self, progress: SyncProgress):
        """Calculate derived progress metrics."""
        # Calculate percentage
        if progress.total_bytes > 0:
            progress.progress_percent = min(
                100.0,
                (progress.transferred_bytes / progress.total_bytes * 100)
            )
        elif progress.total_files > 0:
            progress.progress_percent = min(
                100.0,
                (progress.transferred_files / progress.total_files * 100)
            )
        
        # Calculate transfer rate
        elapsed = (progress.last_update - progress.start_time).total_seconds()
        if elapsed > 0 and progress.transferred_bytes > 0:
            progress.transfer_rate_mbps = (
                progress.transferred_bytes / elapsed / 1_000_000
            )
        
        # Estimate remaining time
        if progress.transfer_rate_mbps > 0 and progress.total_bytes > 0:
            remaining_bytes = progress.total_bytes - progress.transferred_bytes
            if remaining_bytes > 0:
                progress.estimated_time_remaining = int(
                    remaining_bytes / (progress.transfer_rate_mbps * 1_000_000)
                )
            else:
                progress.estimated_time_remaining = 0
    
    def complete_progress(self, sync_id: str, success: bool = True):
        """Mark a sync as complete."""
        if sync_id in self._progress_store:
            progress = self._progress_store[sync_id]
            progress.status = 'complete' if success else 'failed'
            progress.progress_percent = 100.0 if success else progress.progress_percent
            progress.end_time = datetime.now()
            progress.last_update = datetime.now()
            
            # Notify callbacks one last time
            for callback in self._callbacks:
                try:
                    callback(progress)
                except Exception as e:
                    logger.error(f"Progress callback failed: {e}")
    
    def list_active(self) -> List[SyncProgress]:
        """List all active sync operations."""
        return [
            p for p in self._progress_store.values()
            if p.status not in ['complete', 'failed']
        ]
    
    def cleanup_old(self, max_age_seconds: int = 3600):
        """Clean up old completed progress entries."""
        current_time = datetime.now()
        to_remove = []
        
        for sync_id, progress in self._progress_store.items():
            if progress.status in ['complete', 'failed'] and progress.end_time:
                age = (current_time - progress.end_time).total_seconds()
                if age > max_age_seconds:
                    to_remove.append(sync_id)
        
        for sync_id in to_remove:
            del self._progress_store[sync_id]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old progress entries")
