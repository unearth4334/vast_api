#!/usr/bin/env python3
"""
Download Handler: Processes download_queue.json and updates download_status.json
"""
import os
import sys
import json
import time
import uuid
import subprocess
from datetime import datetime
from threading import Lock
from app.utils.progress_parsers import CivitdlProgressParser, WgetProgressParser

QUEUE_PATH = os.path.join(os.path.dirname(__file__), '../downloads/download_queue.json')
STATUS_PATH = os.path.join(os.path.dirname(__file__), '../downloads/download_status.json')
LOCK = Lock()

POLL_INTERVAL = 2  # seconds

# Helper to read/write JSON with locking
def read_json(path):
    with LOCK:
        if not os.path.exists(path):
            return []
        with open(path, 'r') as f:
            return json.load(f)

def write_json(path, data):
    with LOCK:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

def update_status(job_id, update):
    status = read_json(STATUS_PATH)
    for job in status:
        if job['id'] == job_id:
            job.update(update)
            break
    else:
        status.append(update)
    write_json(STATUS_PATH, status)

def run_command_ssh(ssh_connection, command, progress_callback):
    # Compose full SSH command
    ssh_cmd = ssh_connection.split() + [command]
    process = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in process.stdout:
        progress_callback(line.rstrip())
    return process.wait()

def process_job(job):
    job_id = job['id']
    update_status(job_id, {
        'id': job_id,
        'instance_id': job['instance_id'],
        'added_at': job['added_at'],
        'status': 'RUNNING',
        'progress': {},
    })
    all_success = True
    for cmd in job['commands']:
        def progress_cb(line):
            parsed = None
            if 'civitdl' in cmd:
                parsed = CivitdlProgressParser.parse_line(line)
            elif 'wget' in cmd:
                parsed = WgetProgressParser.parse_line(line)
            if parsed:
                update_status(job_id, {'progress': parsed, 'status': 'RUNNING'})
        ret = run_command_ssh(job['ssh_connection'], cmd, progress_cb)
        if ret != 0:
            update_status(job_id, {'status': 'FAILED', 'error': f'Command failed: {cmd}'})
            all_success = False
            break
    if all_success:
        update_status(job_id, {'status': 'COMPLETE', 'progress': {'percent': 100}})

def main():
    while True:
        queue = read_json(QUEUE_PATH)
        for job in queue:
            if job['status'] == 'PENDING':
                job['status'] = 'RUNNING'
                write_json(QUEUE_PATH, queue)
                process_job(job)
                job['status'] = 'COMPLETE' if job['id'] in [j['id'] for j in read_json(STATUS_PATH) if j['status'] == 'COMPLETE'] else 'FAILED'
                write_json(QUEUE_PATH, queue)
        time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    main()
