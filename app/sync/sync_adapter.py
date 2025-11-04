"""
Adapter to make the new sync system compatible with legacy sync_utils.run_sync interface
"""

import asyncio
import logging
import os
from typing import Optional

from .orchestrator import SyncOrchestrator
from .models import SyncConfig

logger = logging.getLogger(__name__)

# Default folders to sync
DEFAULT_FOLDERS = [
    'txt2img-images',
    'img2img-images',
    'txt2img-grids',
    'img2img-grids',
    'WAN',
    'extras-images'
]

# Global orchestrator instance
_orchestrator = None


def get_orchestrator() -> SyncOrchestrator:
    """Get or create the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SyncOrchestrator()
    return _orchestrator


async def _poll_job_status(orchestrator: SyncOrchestrator, job_id: str, max_wait: int = 600) -> Optional[dict]:
    """
    Poll job status asynchronously to avoid blocking.
    
    Uses asyncio.to_thread() to run synchronous get_job_status in a thread,
    preventing blocking of the event loop during progress polling.
    
    Args:
        orchestrator: The orchestrator instance
        job_id: Job ID to poll
        max_wait: Maximum time to wait in seconds
    
    Returns:
        The final job status or None if timeout
    """
    elapsed = 0
    while elapsed < max_wait:
        # Run synchronous get_job_status in a thread to avoid blocking
        job_status = await asyncio.to_thread(orchestrator.get_job_status, job_id)
        if job_status and job_status.status in ['complete', 'failed']:
            return job_status
        await asyncio.sleep(2)
        elapsed += 2
    
    # Timeout - get final status
    return await asyncio.to_thread(orchestrator.get_job_status, job_id)


def run_sync_v2(host: str, port: str, sync_type: str, cleanup: bool = True, 
                folders: list = None, source_path: str = None) -> dict:
    """
    Run sync using the new orchestrator system.
    
    This function provides backward compatibility with the old run_sync interface
    while using the new redesigned system under the hood.
    
    Args:
        host: SSH host to sync from
        port: SSH port
        sync_type: Type of sync ('forge', 'comfyui', 'vastai')
        cleanup: Whether to cleanup old media
        folders: List of folders to sync (default: DEFAULT_FOLDERS)
        source_path: Source path on remote (default: detect from UI_HOME)
    
    Returns:
        dict: Result with success, message, and output
    """
    try:
        # Detect source path if not provided
        if not source_path:
            if sync_type.lower() == 'forge':
                source_path = '/workspace/stable-diffusion-webui/outputs'
            elif sync_type.lower() == 'comfyui':
                source_path = '/workspace/ComfyUI/output'
            else:
                source_path = '/workspace/stable-diffusion-webui/outputs'
        
        # Use default folders if not provided
        if not folders:
            folders = DEFAULT_FOLDERS
        
        # Get destination path from environment or default
        dest_path = os.environ.get('MEDIA_BASE', '/mnt/qnap-sd/SecretFolder')
        
        # Create config
        config = SyncConfig(
            source_type=sync_type.lower(),
            source_host=host,
            source_port=int(port),
            source_path=source_path,
            dest_path=dest_path,
            folders=folders,
            parallel_transfers=3,
            enable_cleanup=cleanup,
            cleanup_age_hours=24,
            cleanup_dry_run=False,
            generate_xmp=True,
            calculate_hashes=False,
            extract_metadata=True
        )
        
        # Start sync
        orchestrator = get_orchestrator()
        
        # Run async operation in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        job = loop.run_until_complete(orchestrator.start_sync(config))
        
        # Poll for completion using asyncio.to_thread() to avoid blocking
        final_job = loop.run_until_complete(_poll_job_status(orchestrator, job.id, max_wait=600))
        
        loop.close()
        
        # Get final status if polling returned None
        if not final_job:
            final_job = orchestrator.get_job_status(job.id)
        
        if not final_job:
            return {
                'success': False,
                'message': 'Sync job not found',
                'output': ''
            }
        
        if final_job.status == 'complete' and final_job.result and final_job.result.success:
            result = final_job.result
            output = (f"Sync completed successfully\n"
                     f"Files transferred: {result.files_transferred}\n"
                     f"Bytes transferred: {result.bytes_transferred:,}\n"
                     f"Duration: {result.duration:.2f}s\n"
                     f"Transfer rate: {result.bytes_transferred / result.duration / 1024 / 1024:.2f} MB/s")
            
            return {
                'success': True,
                'message': f'{sync_type} sync completed successfully',
                'output': output,
                'job_id': job.id,
                'files_transferred': result.files_transferred,
                'bytes_transferred': result.bytes_transferred,
                'duration': result.duration
            }
        else:
            errors = final_job.result.errors if final_job.result else ['Unknown error']
            return {
                'success': False,
                'message': f'{sync_type} sync failed',
                'output': '\n'.join(errors),
                'job_id': job.id,
                'errors': errors
            }
    
    except Exception as e:
        logger.error(f"Sync error: {e}")
        return {
            'success': False,
            'message': f'Sync error: {str(e)}',
            'output': str(e)
        }
