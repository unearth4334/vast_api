"""
Sync orchestrator - central coordinator for media sync operations
"""

import asyncio
import uuid
import logging
from typing import Optional, Dict
from datetime import datetime

from .models import SyncConfig, SyncJob, SyncResult
from .engine import SyncEngine
from .transport.ssh_rsync import SSHRsyncAdapter
from .progress import ProgressManager
from .cleanup import CleanupEngine
from .ingest import MediaEventManager

logger = logging.getLogger(__name__)


class SyncOrchestrator:
    """Central coordinator for media sync operations."""
    
    def __init__(self, manifest_dir: str = "/app/logs/manifests"):
        self.manifest_dir = manifest_dir
        self.progress_manager = ProgressManager()
        self.event_manager = MediaEventManager()
        self._active_jobs: Dict[str, SyncJob] = {}
    
    async def start_sync(self, config: SyncConfig) -> SyncJob:
        """
        Initiate a new sync operation.
        
        Args:
            config: Sync configuration including source, destination,
                   filters, and options
        
        Returns:
            SyncJob: Job handle for tracking progress
        """
        job_id = str(uuid.uuid4())
        sync_id = f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{job_id[:8]}"
        
        job = SyncJob(
            id=job_id,
            config=config,
            status='initializing',
            start_time=datetime.now()
        )
        
        self._active_jobs[job_id] = job
        
        # Create progress tracker
        progress = self.progress_manager.create_progress(sync_id, job_id)
        
        # Start sync in background
        asyncio.create_task(self._execute_sync(job, sync_id, progress))
        
        return job
    
    async def _execute_sync(self, job: SyncJob, sync_id: str, progress):
        """Execute the sync operation."""
        config = job.config
        
        try:
            logger.info(f"Starting sync job {job.id}")
            
            # Update progress
            self.progress_manager.update_progress(sync_id, {
                'status': 'initializing',
                'current_stage': 'Setting up transport'
            })
            
            # Create transport adapter
            transport = SSHRsyncAdapter(
                host=config.source_host,
                port=config.source_port
            )
            
            # Create sync engine with manifest
            manifest_path = f"{self.manifest_dir}/{config.source_type}_{config.source_host}.json"
            engine = SyncEngine(transport, manifest_path)
            
            # Prepare folder pairs
            folder_pairs = []
            base_dest = config.dest_path
            
            if config.folders:
                for folder in config.folders:
                    source_path = f"{config.source_path}/{folder}" if config.source_path else folder
                    dest_path = f"{base_dest}/{folder}"
                    folder_pairs.append((source_path, dest_path))
            else:
                # Sync entire source path
                folder_pairs.append((config.source_path or "", base_dest))
            
            self.progress_manager.update_progress(sync_id, {
                'status': 'transferring',
                'total_folders': len(folder_pairs),
                'current_stage': 'Transferring folders'
            })
            
            # Progress callback
            def progress_callback(update):
                self.progress_manager.update_progress(sync_id, update)
            
            # Execute sync
            if config.parallel_transfers > 1 and len(folder_pairs) > 1:
                logger.info(f"Syncing {len(folder_pairs)} folders in parallel")
                results = await engine.sync_folders_parallel(
                    folder_pairs,
                    config,
                    progress_callback
                )
            else:
                logger.info(f"Syncing {len(folder_pairs)} folders sequentially")
                results = []
                for i, (src, dest) in enumerate(folder_pairs):
                    self.progress_manager.update_progress(sync_id, {
                        'completed_folders': i,
                        'current_folder': src
                    })
                    result = await engine.sync_folder(src, dest, config, progress_callback)
                    results.append(result)
            
            # Aggregate results
            total_files = sum(r.files_transferred for r in results if r.success)
            total_bytes = sum(r.bytes_transferred for r in results if r.success)
            all_errors = []
            for r in results:
                all_errors.extend(r.errors)
            
            success = all(r.success for r in results)
            
            job.result = SyncResult(
                success=success,
                files_transferred=total_files,
                bytes_transferred=total_bytes,
                duration=(datetime.now() - job.start_time).total_seconds(),
                errors=all_errors
            )
            
            # Cleanup if enabled
            if config.enable_cleanup and success:
                self.progress_manager.update_progress(sync_id, {
                    'status': 'cleaning',
                    'current_stage': 'Cleaning up old media'
                })
                
                await self._run_cleanup(config, transport, progress_callback)
            
            # Mark complete
            job.status = 'complete' if success else 'failed'
            job.end_time = datetime.now()
            
            self.progress_manager.complete_progress(sync_id, success)
            
            logger.info(f"Sync job {job.id} completed: success={success}, files={total_files}, bytes={total_bytes}")
        
        except Exception as e:
            logger.error(f"Sync job {job.id} failed: {e}")
            job.status = 'failed'
            job.end_time = datetime.now()
            job.result = SyncResult(
                success=False,
                files_transferred=0,
                bytes_transferred=0,
                duration=(datetime.now() - job.start_time).total_seconds(),
                errors=[str(e)]
            )
            
            self.progress_manager.complete_progress(sync_id, False)
    
    async def _run_cleanup(self, config: SyncConfig, transport, progress_callback):
        """Run cleanup operation."""
        try:
            cleanup_engine = CleanupEngine()
            
            # Cleanup source (remote)
            if config.source_path:
                result = await cleanup_engine.cleanup_old_media(
                    target_path=config.source_path,
                    age_hours=config.cleanup_age_hours,
                    dry_run=config.cleanup_dry_run,
                    transport=transport,
                    progress_callback=progress_callback
                )
                
                logger.info(f"Cleanup: deleted {result.files_deleted} files, freed {result.space_freed_bytes} bytes")
        
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def get_job_status(self, job_id: str) -> Optional[SyncJob]:
        """Get current status of a sync job."""
        return self._active_jobs.get(job_id)
    
    def list_active_jobs(self) -> list:
        """List all active sync jobs."""
        return [job for job in self._active_jobs.values() if job.status not in ['complete', 'failed']]
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running sync job."""
        # Note: This is a simplified implementation
        # Full cancellation would require task tracking
        job = self._active_jobs.get(job_id)
        if job and job.status not in ['complete', 'failed']:
            job.status = 'cancelled'
            job.end_time = datetime.now()
            return True
        return False
