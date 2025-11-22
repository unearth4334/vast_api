#!/usr/bin/env python3
"""
Queue ComfyUI Workflow on Remote Instance

This script uploads an input image and queues a ComfyUI workflow on a remote VastAI instance.

Usage:
    python3 queue_comfyui_workflow.py SSH_CONNECTION WORKFLOW_FILE IMAGE_PATH

Example:
    python3 queue_comfyui_workflow.py "ssh -p 40738 root@198.53.64.194" workflow.json input.png
"""

import sys
import json
import subprocess
import argparse
import os
import re
from pathlib import Path


def parse_ssh_connection(ssh_connection):
    """Extract host and port from SSH connection string."""
    # Match patterns like: "ssh -p PORT root@HOST" or "root@HOST -p PORT"
    port_match = re.search(r'-p\s+(\d+)', ssh_connection)
    host_match = re.search(r'root@([\w\.-]+)', ssh_connection)
    
    if not port_match or not host_match:
        raise ValueError(f"Could not parse SSH connection string: {ssh_connection}")
    
    return host_match.group(1), port_match.group(1)


def upload_image(ssh_connection, local_image_path, remote_path="/workspace/ComfyUI/input/"):
    """Upload the input image to the remote ComfyUI instance."""
    host, port = parse_ssh_connection(ssh_connection)
    image_filename = Path(local_image_path).name
    remote_full_path = f"{remote_path}{image_filename}"
    
    print(f"📤 Uploading {image_filename} to {host}:{port}...")
    
    scp_cmd = [
        'scp',
        '-P', port,
        local_image_path,
        f'root@{host}:{remote_path}'
    ]
    
    result = subprocess.run(scp_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to upload image: {result.stderr}")
    
    print(f"✅ Image uploaded successfully")
    return image_filename


def upload_workflow(ssh_connection, workflow_file):
    """Upload the workflow file to the remote instance."""
    host, port = parse_ssh_connection(ssh_connection)
    remote_path = "/tmp/workflow.json"
    
    print(f"📤 Uploading workflow file...")
    
    scp_cmd = [
        'scp',
        '-P', port,
        workflow_file,
        f'root@{host}:{remote_path}'
    ]
    
    result = subprocess.run(scp_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to upload workflow: {result.stderr}")
    
    print(f"✅ Workflow uploaded successfully")
    return remote_path


def queue_workflow(ssh_connection, remote_workflow_path):
    """Queue the workflow on the remote ComfyUI instance."""
    host, port = parse_ssh_connection(ssh_connection)
    
    print(f"🚀 Queuing workflow on ComfyUI...")
    
    python_script = """
import json
import requests

try:
    with open('{}', 'r') as f:
        workflow = json.load(f)
    
    prompt_request = {{
        'prompt': workflow,
        'client_id': 'vast_api_queue_script'
    }}
    
    response = requests.post(
        'http://localhost:18188/prompt',
        json=prompt_request,
        timeout=30
    )
    result = response.json()
    
    if 'prompt_id' in result:
        print('SUCCESS')
        print('PROMPT_ID:', result['prompt_id'])
        print('QUEUE_NUMBER:', result.get('number', 'N/A'))
    else:
        print('ERROR')
        print(json.dumps(result, indent=2))
        
except Exception as e:
    print('EXCEPTION')
    print(str(e))
""".format(remote_workflow_path)
    
    ssh_cmd = [
        'ssh',
        '-p', port,
        f'root@{host}',
        f'python3 -c "{python_script}"'
    ]
    
    result = subprocess.run(ssh_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to queue workflow: {result.stderr}")
    
    output = result.stdout.strip()
    
    if 'SUCCESS' in output:
        lines = output.split('\n')
        prompt_id = None
        queue_number = None
        
        for line in lines:
            if line.startswith('PROMPT_ID:'):
                prompt_id = line.split(':', 1)[1].strip()
            elif line.startswith('QUEUE_NUMBER:'):
                queue_number = line.split(':', 1)[1].strip()
        
        print(f"✅ Workflow queued successfully!")
        print(f"   Prompt ID: {prompt_id}")
        print(f"   Queue Position: {queue_number}")
        
        return prompt_id, queue_number
    elif 'ERROR' in output:
        error_msg = '\n'.join(output.split('\n')[1:])
        raise RuntimeError(f"ComfyUI API error:\n{error_msg}")
    else:
        raise RuntimeError(f"Unexpected response:\n{output}")


def validate_inputs(ssh_connection, workflow_file, image_path):
    """Validate that all inputs exist and are accessible."""
    if not os.path.exists(workflow_file):
        raise FileNotFoundError(f"Workflow file not found: {workflow_file}")
    
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Test SSH connection
    try:
        host, port = parse_ssh_connection(ssh_connection)
        test_cmd = ['ssh', '-p', port, f'root@{host}', 'echo "test"']
        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            raise RuntimeError(f"SSH connection test failed: {result.stderr}")
    except Exception as e:
        raise RuntimeError(f"Cannot connect via SSH: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Queue a ComfyUI workflow on a remote VastAI instance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "ssh -p 40738 root@198.53.64.194" workflow.json input.png
  %(prog)s "ssh -p 12345 root@example.com -L 8080:localhost:8080" my_workflow.json my_image.jpg
        """
    )
    
    parser.add_argument('ssh_connection', 
                       help='SSH connection string (e.g., "ssh -p 40738 root@198.53.64.194")')
    parser.add_argument('workflow_file', 
                       help='Path to the ComfyUI workflow JSON file (API format)')
    parser.add_argument('image_path', 
                       help='Path to the input image file')
    parser.add_argument('--no-upload-image', 
                       action='store_true',
                       help='Skip image upload (if already on remote)')
    
    args = parser.parse_args()
    
    try:
        print("="*60)
        print("ComfyUI Workflow Queue Script")
        print("="*60)
        
        # Validate inputs
        print("\n🔍 Validating inputs...")
        validate_inputs(args.ssh_connection, args.workflow_file, args.image_path)
        print("✅ All inputs validated")
        
        # Upload image
        if not args.no_upload_image:
            image_filename = upload_image(args.ssh_connection, args.image_path)
        else:
            image_filename = Path(args.image_path).name
            print(f"⏭️  Skipping image upload (using existing: {image_filename})")
        
        # Upload workflow
        remote_workflow = upload_workflow(args.ssh_connection, args.workflow_file)
        
        # Queue workflow
        prompt_id, queue_number = queue_workflow(args.ssh_connection, remote_workflow)
        
        print("\n" + "="*60)
        print("✅ SUCCESS!")
        print("="*60)
        print(f"Workflow has been queued on the remote instance.")
        print(f"Monitor progress in ComfyUI web interface or use the prompt ID.")
        
        return 0
        
    except Exception as e:
        print("\n" + "="*60)
        print("❌ ERROR!")
        print("="*60)
        print(f"{e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
