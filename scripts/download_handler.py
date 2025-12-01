#!/usr/bin/env python3
"""
Download Handler: Processes download_queue.json and updates download_status.json

This handler:
- Polls the queue every 2 seconds for new jobs
- Writes status updates to the status file every 2 seconds during downloads
- Provides detailed progress info (percent, speed, stage, name)
"""
import os
import sys
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
from threading import Lock, Thread
from typing import Dict, Optional

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.progress_parsers import CivitdlProgressParser, WgetProgressParser

DOWNLOADS_DIR = PROJECT_ROOT / 'downloads'
QUEUE_PATH = DOWNLOADS_DIR / 'download_queue.json'
STATUS_PATH = DOWNLOADS_DIR / 'download_status.json'
LOCK = Lock()

POLL_INTERVAL = 2  # seconds - how often to check for new jobs
STATUS_UPDATE_INTERVAL = 2  # seconds - how often to write status updates


def read_json(path: Path) -> list:
    """Read JSON file with locking"""
    with LOCK:
        if not path.exists():
            return []
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []


def write_json(path: Path, data: list) -> None:
    """Write JSON file with locking"""
    with LOCK:
        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)


def update_status(job_id: str, update: Dict) -> None:
    """Update status for a specific job"""
    status = read_json(STATUS_PATH)
    updated = False
    for job in status:
        if job['id'] == job_id:
            job.update(update)
            updated = True
            break
    if not updated:
        # Job not found, add it
        status.append(update)
    write_json(STATUS_PATH, status)


class ProgressTracker:
    """
    Tracks download progress and periodically writes to status file.
    Ensures status is written every 2 seconds even if progress updates
    are more or less frequent.
    """
    
    def __init__(self, job_id: str, instance_id: str, added_at: str):
        self.job_id = job_id
        self.instance_id = instance_id
        self.added_at = added_at
        self.current_progress: Dict = {}
        self.last_status_write = 0
        self.current_command_index = 0
        self.total_commands = 0
        self.current_model_name: Optional[str] = None
        
    def update_progress(self, parsed: Dict) -> None:
        """Update current progress from parsed output"""
        if not parsed:
            return
            
        self.current_progress.update(parsed)
        
        # Extract model name if stage_start
        if parsed.get('type') == 'stage_start':
            self.current_model_name = parsed.get('name')
            self.current_progress['name'] = self.current_model_name
        elif parsed.get('type') == 'stage_complete':
            self.current_progress['name'] = parsed.get('name')
        
        # Check if it's time to write status (every 2 seconds)
        now = time.time()
        if now - self.last_status_write >= STATUS_UPDATE_INTERVAL:
            self.write_status()
    
    def write_status(self, status: str = 'RUNNING', error: Optional[str] = None) -> None:
        """Write current status to file"""
        self.last_status_write = time.time()
        
        update_data = {
            'id': self.job_id,
            'instance_id': self.instance_id,
            'added_at': self.added_at,
            'status': status,
            'progress': self.current_progress.copy(),
            'updated_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        if error:
            update_data['error'] = error
        
        # Add command progress info
        if self.total_commands > 0:
            update_data['command_index'] = self.current_command_index
            update_data['total_commands'] = self.total_commands
        
        update_status(self.job_id, update_data)
    
    def set_command_info(self, index: int, total: int) -> None:
        """Set current command index and total"""
        self.current_command_index = index
        self.total_commands = total


def is_host_key_error(stderr: str, return_code: int) -> bool:
    """
    Check if SSH error is due to host key verification
    
    Args:
        stderr: Standard error output from SSH command
        return_code: Process return code
        
    Returns:
        True if error is related to host key verification
    """
    if return_code != 255:
        return False
    
    stderr_lower = stderr.lower()
    
    # Check for common host key error patterns
    host_key_patterns = [
        'host key verification failed',
        'no matching host key type found',
        'host key for',
        'remote host identification has changed',
        'add correct host key'
    ]
    
    return any(pattern in stderr_lower for pattern in host_key_patterns)


def extract_host_port(ssh_connection: str) -> tuple:
    """
    Extract host and port from SSH connection string
    
    Args:
        ssh_connection: SSH connection string like "ssh -p 12345 root@host"
        
    Returns:
        Tuple of (host, port)
    """
    import re
    
    # Extract port
    port_match = re.search(r'-p\s+(\d+)', ssh_connection)
    port = int(port_match.group(1)) if port_match else 22
    
    # Extract host
    host_match = re.search(r'root@([\d.]+)', ssh_connection)
    host = host_match.group(1) if host_match else None
    
    return host, port


def run_command_ssh(ssh_connection: str, command: str, progress_callback) -> tuple:
    """
    Run a command via SSH and capture output.
    Calls progress_callback for each line of output.
    
    Returns:
        Tuple of (return_code, stderr_output)
    """
    # Build SSH command with strict host key checking
    # Parse the ssh_connection to extract components and add our options
    import re
    
    # Extract port
    port_match = re.search(r'-p\s+(\d+)', ssh_connection)
    port = port_match.group(1) if port_match else '22'
    
    # Extract host
    host_match = re.search(r'root@([\d.]+)', ssh_connection)
    host = host_match.group(1) if host_match else None
    
    if not host:
        print(f"Could not parse host from SSH connection: {ssh_connection}")
        return -1, "Invalid SSH connection string"
    
    # Build SSH command with our security options
    ssh_cmd = [
        'ssh',
        '-p', port,
        '-i', '/root/.ssh/id_ed25519',
        '-o', 'ConnectTimeout=10',
        '-o', 'StrictHostKeyChecking=yes',
        '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
        '-o', 'IdentitiesOnly=yes',
        f'root@{host}',
        command
    ]
    
    try:
        process = subprocess.Popen(
            ssh_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Redirect stderr to stdout so we get all output
            text=True,
            bufsize=1
        )
        
        # Read all output (stdout + stderr merged)
        for line in process.stdout:
            progress_callback(line.rstrip())
        
        return_code = process.wait()
        
        # Return empty stderr since we merged it with stdout
        return return_code, ""
    except Exception as e:
        print(f"Error running SSH command: {e}")
        return -1, str(e)


def process_job(job: Dict) -> None:
    """Process a single download job"""
    job_id = job['id']
    instance_id = job.get('instance_id', 'unknown')
    added_at = job.get('added_at', datetime.utcnow().isoformat() + 'Z')
    commands = job.get('commands', [])
    ssh_connection = job.get('ssh_connection', '')
    
    if not commands or not ssh_connection:
        update_status(job_id, {
            'id': job_id,
            'instance_id': instance_id,
            'added_at': added_at,
            'status': 'FAILED',
            'error': 'Missing commands or SSH connection',
            'progress': {}
        })
        return
    
    # Initialize progress tracker
    tracker = ProgressTracker(job_id, instance_id, added_at)
    tracker.set_command_info(0, len(commands))
    
    # Write initial running status
    tracker.write_status('RUNNING')
    
    all_success = True
    
    for idx, cmd in enumerate(commands):
        tracker.set_command_info(idx + 1, len(commands))
        tracker.current_progress = {}  # Reset progress for new command
        
        def progress_cb(line: str):
            """Callback for each line of output"""
            parsed = None
            
            # Debug: print the line
            print(f"[PROGRESS] {line}")
            
            # Parse based on command type
            if 'civitdl' in cmd.lower():
                parsed = CivitdlProgressParser.parse_line(line)
            elif 'wget' in cmd.lower():
                parsed = WgetProgressParser.parse_line(line)
            
            if parsed:
                print(f"[PARSED] {parsed}")
                tracker.update_progress(parsed)
            else:
                # Even without parsed progress, write status periodically
                now = time.time()
                if now - tracker.last_status_write >= STATUS_UPDATE_INTERVAL:
                    tracker.write_status()
        
        # Run the command
        ret, stderr = run_command_ssh(ssh_connection, cmd, progress_cb)
        
        if ret != 0:
            # Check if this is a host key verification error
            if is_host_key_error(stderr, ret):
                host, port = extract_host_port(ssh_connection)
                error_msg = f'Host key verification required for {host}:{port}'
                status_data = {
                    'id': job_id,
                    'instance_id': instance_id,
                    'added_at': added_at,
                    'status': 'HOST_VERIFICATION_NEEDED',
                    'error': error_msg,
                    'host_verification_needed': True,
                    'host': host,
                    'port': port,
                    'ssh_connection': ssh_connection,
                    'progress': tracker.current_progress,
                    'updated_at': datetime.utcnow().isoformat() + 'Z'
                }
                update_status(job_id, status_data)
                all_success = False
                break
            else:
                tracker.write_status('FAILED', f'Command failed with exit code {ret}: {cmd[:50]}...')
                all_success = False
                break
    
    # Write final status
    if all_success:
        tracker.current_progress = {'percent': 100}
        tracker.write_status('COMPLETE')


def main():
    """Main loop: poll queue and process pending jobs"""
    print(f"Download handler started. Polling every {POLL_INTERVAL}s, status updates every {STATUS_UPDATE_INTERVAL}s")
    
    # Ensure directories exist
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    
    while True:
        try:
            queue = read_json(QUEUE_PATH)
            
            # Find pending jobs
            pending_jobs = [job for job in queue if job.get('status') == 'PENDING']
            
            if pending_jobs:
                print(f"Found {len(pending_jobs)} pending job(s)")
            
            for job in pending_jobs:
                job_id = job['id']
                
                # Mark as running in queue
                for q_job in queue:
                    if q_job['id'] == job_id:
                        q_job['status'] = 'RUNNING'
                        break
                write_json(QUEUE_PATH, queue)
                
                # Process the job
                print(f"Processing job {job_id[:8]}...")
                process_job(job)
                
                # Update queue status based on final status
                status = read_json(STATUS_PATH)
                final_status = next(
                    (s['status'] for s in status if s['id'] == job_id),
                    'FAILED'
                )
                
                queue = read_json(QUEUE_PATH)  # Re-read in case of changes
                for q_job in queue:
                    if q_job['id'] == job_id:
                        q_job['status'] = final_status
                        break
                write_json(QUEUE_PATH, queue)
                
                print(f"Job {job_id[:8]} completed with status: {final_status}")
        
        except Exception as e:
            print(f"Error in main loop: {e}")
        
        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()
