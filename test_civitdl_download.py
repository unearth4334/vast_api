#!/usr/bin/env python3
"""
Test script to queue Wan_2.2_I2V Smooth Mix download via civitdl
"""
import requests
import json
import time

BASE_URL = "http://10.0.78.66:5000"
SSH_CONNECTION = "ssh -p 40538 root@198.53.64.194 -L 8080:localhost:8080"

def queue_download():
    """Queue the Wan_2.2_I2V Smooth Mix checkpoint for download"""
    
    # Resource to download
    resources = [
        {'filepath': 'checkpoints/CHKPT-Wan_2.2_I2V Smooth Mix (14B FP8).md'}
    ]
    
    payload = {
        'ssh_connection': SSH_CONNECTION,
        'resources': resources,
        'ui_home': '/workspace/ComfyUI'
    }
    
    print("Queueing Wan_2.2_I2V Smooth Mix for download...")
    print(f"SSH: {SSH_CONNECTION}")
    print()
    
    response = requests.post(f"{BASE_URL}/downloads/queue", json=payload)
    
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 200 and data.get('success'):
        jobs = data.get('jobs', [])
        print(f"\n✅ Successfully queued {len(jobs)} job(s)")
        
        for i, job in enumerate(jobs, 1):
            print(f"\nJob {i}:")
            print(f"  ID: {job['id']}")
            print(f"  Display Name: {job.get('display_name', 'N/A')}")
            print(f"  Variant: {job.get('variant_tag', 'N/A')}")
            print(f"  Status: {job['status']}")
            print(f"  Commands: {job.get('commands', [])}")
        
        return jobs
    else:
        print(f"❌ Failed: {data.get('message', 'Unknown error')}")
        return None


def monitor_progress(instance_id):
    """Monitor download progress"""
    print(f"\n{'='*80}")
    print("Monitoring download progress...")
    print(f"{'='*80}\n")
    
    last_status = {}
    
    for _ in range(60):  # Monitor for up to 5 minutes
        try:
            response = requests.get(f"{BASE_URL}/downloads/status?instance_id={instance_id}")
            if response.status_code == 200:
                jobs = response.json()
                
                for job in jobs:
                    job_id = job['id'][:8]
                    status = job.get('status', 'UNKNOWN')
                    progress = job.get('progress', {})
                    display_name = job.get('display_name', 'Unknown')
                    
                    # Only print if status changed or has progress
                    if job_id not in last_status or last_status[job_id] != (status, progress):
                        last_status[job_id] = (status, progress)
                        
                        print(f"[{job_id}] {display_name}: {status}")
                        
                        if progress:
                            prog_type = progress.get('type')
                            if prog_type == 'progress':
                                stage = progress.get('stage', 'unknown')
                                percent = progress.get('percent', 0)
                                speed = progress.get('speed', 'N/A')
                                print(f"  └─ {stage}: {percent}% @ {speed}")
                            elif prog_type == 'stage_start':
                                print(f"  └─ Starting: {progress.get('name')}")
                            elif prog_type == 'stage_complete':
                                print(f"  └─ Completed: {progress.get('name')}")
                
                # Check if all jobs are complete or failed
                all_done = all(j.get('status') in ['COMPLETED', 'FAILED'] for j in jobs)
                if all_done:
                    print("\n✅ All downloads complete!")
                    break
            
            time.sleep(5)
        except Exception as e:
            print(f"Error monitoring: {e}")
            time.sleep(5)
    
    print(f"\n{'='*80}")
    print("Monitoring complete")
    print(f"{'='*80}")


if __name__ == '__main__':
    jobs = queue_download()
    
    if jobs:
        # Extract instance ID from SSH connection
        instance_id = SSH_CONNECTION.split('@')[1].split()[0].replace('.', '_')
        
        print(f"\nWaiting 5 seconds before monitoring...")
        time.sleep(5)
        
        monitor_progress(instance_id)
