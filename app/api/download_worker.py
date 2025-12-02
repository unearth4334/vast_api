"""
Download Worker

Background worker that processes the download queue and executes
wget and civitdl download commands on remote instances.
"""

import json
import logging
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Paths to queue and status files
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOWNLOADS_DIR = BASE_DIR / 'downloads'
QUEUE_PATH = DOWNLOADS_DIR / 'download_queue.json'
STATUS_PATH = DOWNLOADS_DIR / 'download_status.json'

# Worker state
_worker_thread: Optional[threading.Thread] = None
_worker_running = False
_worker_lock = threading.Lock()


def _load_queue():
    """Load download queue from disk"""
    if not QUEUE_PATH.exists():
        return []
    try:
        with open(QUEUE_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading queue: {e}")
        return []


def _save_queue(queue):
    """Save download queue to disk"""
    try:
        DOWNLOADS_DIR.mkdir(exist_ok=True)
        with open(QUEUE_PATH, 'w') as f:
            json.dump(queue, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving queue: {e}")


def _load_status():
    """Load download status from disk"""
    if not STATUS_PATH.exists():
        return []
    try:
        with open(STATUS_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading status: {e}")
        return []


def _save_status(status):
    """Save download status to disk"""
    try:
        DOWNLOADS_DIR.mkdir(exist_ok=True)
        with open(STATUS_PATH, 'w') as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving status: {e}")


def _update_job_status(job_id: str, status_updates: Dict):
    """Update status for a specific job"""
    status = _load_status()
    for s in status:
        if s['id'] == job_id:
            s.update(status_updates)
            s['updated_at'] = datetime.utcnow().isoformat() + 'Z'
            break
    _save_status(status)


def _progress_callback(job_id: str, progress_data: Dict):
    """Callback to update job progress"""
    logger.debug(f"Progress update for job {job_id}: {progress_data}")
    
    status_updates = {
        'progress': progress_data
    }
    
    # Update overall status based on progress type
    if progress_data.get('type') == 'stage_start':
        status_updates['status'] = 'RUNNING'
        status_updates['current_stage'] = progress_data.get('name')
    elif progress_data.get('type') == 'stage_complete':
        status_updates['status'] = 'RUNNING'
    
    _update_job_status(job_id, status_updates)


def _process_job(job: Dict) -> bool:
    """
    Process a single download job
    
    Returns:
        True if successful, False otherwise
    """
    job_id = job['id']
    ssh_connection = job['ssh_connection']
    ui_home = job['ui_home']
    commands = job['commands']
    
    logger.info(f"Processing job {job_id}: {len(commands)} command(s)")
    
    # Update status to RUNNING
    _update_job_status(job_id, {
        'status': 'RUNNING',
        'started_at': datetime.utcnow().isoformat() + 'Z'
    })
    
    try:
        # Import ResourceInstaller
        from ..resources import ResourceInstaller
        
        # Parse SSH connection to get host and port
        import re
        match = re.search(r'-p\s+(\d+).*?root@([\d.]+)', ssh_connection)
        if not match:
            raise ValueError(f"Could not parse SSH connection: {ssh_connection}")
        
        ssh_port = int(match.group(1))
        ssh_host = match.group(2)
        
        # Create installer with progress callback
        installer = ResourceInstaller(
            progress_callback=lambda data: _progress_callback(job_id, data)
        )
        
        # Execute the download command
        # For now, we process single command per job
        command = commands[0] if commands else None
        if not command:
            raise ValueError("No command to execute")
        
        display_name = job.get('display_name', 'resource')
        result = installer.install_resource(
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            ui_home=ui_home,
            download_command=command,
            resource_name=display_name
        )
        
        if result['success']:
            logger.info(f"Job {job_id} completed successfully")
            _update_job_status(job_id, {
                'status': 'COMPLETED',
                'completed_at': datetime.utcnow().isoformat() + 'Z',
                'output': result.get('output', [])
            })
            return True
        else:
            # Check for host verification needed
            if result.get('host_verification_needed'):
                logger.warning(f"Job {job_id} requires host verification")
                _update_job_status(job_id, {
                    'status': 'HOST_VERIFICATION_NEEDED',
                    'host_verification_needed': True,
                    'host': result.get('host'),
                    'port': result.get('port'),
                    'error': 'Host key verification required'
                })
            else:
                logger.error(f"Job {job_id} failed")
                _update_job_status(job_id, {
                    'status': 'FAILED',
                    'completed_at': datetime.utcnow().isoformat() + 'Z',
                    'error': '\n'.join(result.get('output', [])),
                    'return_code': result.get('return_code')
                })
            return False
            
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}", exc_info=True)
        _update_job_status(job_id, {
            'status': 'FAILED',
            'completed_at': datetime.utcnow().isoformat() + 'Z',
            'error': str(e)
        })
        return False


def _worker_loop():
    """Main worker loop that processes the download queue"""
    logger.info("Download worker started")
    
    while _worker_running:
        try:
            # Load current queue
            queue = _load_queue()
            
            # Find next PENDING job
            next_job = None
            for job in queue:
                if job.get('status') == 'PENDING':
                    next_job = job
                    break
            
            if next_job:
                # Process the job
                success = _process_job(next_job)
                
                # Update job status in queue
                for job in queue:
                    if job['id'] == next_job['id']:
                        job['status'] = 'COMPLETED' if success else 'FAILED'
                        break
                
                _save_queue(queue)
            else:
                # No pending jobs, sleep for a bit
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"Error in download worker loop: {e}", exc_info=True)
            time.sleep(5)
    
    logger.info("Download worker stopped")


def start_worker():
    """Start the download worker thread"""
    global _worker_thread, _worker_running
    
    with _worker_lock:
        if _worker_running:
            logger.warning("Download worker already running")
            return
        
        _worker_running = True
        _worker_thread = threading.Thread(
            target=_worker_loop,
            daemon=True,
            name="download-worker"
        )
        _worker_thread.start()
        logger.info("Download worker thread started")


def stop_worker():
    """Stop the download worker thread"""
    global _worker_running
    
    with _worker_lock:
        if not _worker_running:
            logger.warning("Download worker not running")
            return
        
        _worker_running = False
        logger.info("Download worker stopping...")


def is_worker_running() -> bool:
    """Check if download worker is running"""
    return _worker_running
