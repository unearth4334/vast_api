#!/usr/bin/env python3
"""
Test BrowserAgent Workflow Queueing in Isolation

This script tests the BrowserAgent workflow queueing step independently,
allowing you to debug issues without running the full workflow generation pipeline.

Usage:
    # Test with a specific workflow file already on the remote instance
    python3 test_browseragent_queue.py \
        --ssh "ssh -p 40738 root@198.53.64.194" \
        --workflow-path /workspace/ComfyUI/user/default/workflows/workflow_a1b2c3d4.json

    # Test with a local workflow file (will upload it first)
    python3 test_browseragent_queue.py \
        --ssh "ssh -p 40738 root@198.53.64.194" \
        --local-workflow /path/to/local/workflow.json

    # Test direct API queueing (fallback method)
    python3 test_browseragent_queue.py \
        --ssh "ssh -p 40738 root@198.53.64.194" \
        --workflow-path /workspace/ComfyUI/user/default/workflows/workflow_a1b2c3d4.json \
        --method api
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path


def parse_ssh_connection(ssh_connection):
    """Extract host and port from SSH connection string."""
    port_match = re.search(r'-p\s+(\d+)', ssh_connection)
    host_match = re.search(r'root@([\w\.-]+)', ssh_connection)
    
    if not port_match or not host_match:
        raise ValueError(f"Could not parse SSH connection: {ssh_connection}")
    
    return host_match.group(1), port_match.group(1)


def check_remote_file_exists(ssh_connection, remote_path):
    """Check if a file exists on the remote instance."""
    host, port = parse_ssh_connection(ssh_connection)
    
    cmd = [
        'ssh',
        '-p', port,
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        f'root@{host}',
        f'test -f {remote_path} && echo "EXISTS" || echo "NOT_FOUND"'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return 'EXISTS' in result.stdout


def upload_workflow_to_remote(ssh_connection, local_workflow_path):
    """Upload a local workflow file to the remote instance."""
    host, port = parse_ssh_connection(ssh_connection)
    
    # Generate remote filename
    filename = f"test_workflow_{uuid.uuid4().hex[:8]}.json"
    remote_path = f"/workspace/ComfyUI/user/default/workflows/{filename}"
    
    print(f"📤 Uploading {local_workflow_path} to remote...")
    
    # Ensure remote directory exists
    mkdir_cmd = [
        'ssh',
        '-p', port,
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        f'root@{host}',
        'mkdir -p /workspace/ComfyUI/user/default/workflows'
    ]
    
    subprocess.run(mkdir_cmd, capture_output=True, text=True)
    
    # Upload file
    scp_cmd = [
        'scp',
        '-P', port,
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        local_workflow_path,
        f'root@{host}:{remote_path}'
    ]
    
    result = subprocess.run(scp_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to upload workflow: {result.stderr}")
    
    print(f"✅ Uploaded to: {remote_path}")
    return remote_path


def check_browseragent_installed(ssh_connection):
    """Check if BrowserAgent is installed on the remote instance."""
    host, port = parse_ssh_connection(ssh_connection)
    
    print("🔍 Checking BrowserAgent installation...")
    
    cmd = [
        'ssh',
        '-p', port,
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        f'root@{host}',
        'test -d ~/BrowserAgent && test -f ~/BrowserAgent/.venv/bin/python && test -f ~/BrowserAgent/examples/comfyui/queue_workflow_ui_click.py && echo "INSTALLED" || echo "NOT_FOUND"'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if 'INSTALLED' in result.stdout:
        print("✅ BrowserAgent is installed")
        return True
    else:
        print("❌ BrowserAgent not found or incomplete installation")
        return False


def check_comfyui_running(ssh_connection):
    """Check if ComfyUI is running on the remote instance."""
    host, port = parse_ssh_connection(ssh_connection)
    
    print("🔍 Checking ComfyUI status...")
    
    # Try to get HTML response - vast.ai welcome message goes to stderr, HTML to stdout
    cmd = [
        'ssh',
        '-p', port,
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        f'root@{host}',
        'curl -s http://localhost:18188/ | head -c 100'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    
    # Combine stdout and stderr to check
    combined_output = result.stdout + result.stderr
    
    # Look for ComfyUI HTML in response (doctype html is good enough)
    if '<!doctype html>' in combined_output.lower() or 'ComfyUI' in combined_output or 'comfyui' in combined_output.lower():
        print("✅ ComfyUI is running")
        return True
    else:
        print(f"❌ ComfyUI not accessible")
        if result.stdout:
            print(f"   stdout: {result.stdout[:100]}")
        if result.stderr:
            print(f"   stderr: {result.stderr[:100]}")
        return False


def queue_with_browseragent(ssh_connection, workflow_path, comfyui_url="http://localhost:18188", verbose=False):
    """Queue workflow using BrowserAgent script."""
    host, port = parse_ssh_connection(ssh_connection)
    
    print(f"\n🚀 Queueing workflow via BrowserAgent...")
    print(f"   Workflow: {workflow_path}")
    print(f"   ComfyUI: {comfyui_url}")
    
    # Note: BrowserAgent script doesn't support verbose flag, ignoring it
    
    cmd = [
        'ssh',
        '-p', port,
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        f'root@{host}',
        f'cd ~/BrowserAgent && ./.venv/bin/python examples/comfyui/queue_workflow_ui_click.py --workflow-path {workflow_path} --comfyui-url {comfyui_url}'
    ]
    
    print(f"\n📝 Executing command:")
    print(f"   {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    print("=" * 80)
    print("STDOUT:")
    print("=" * 80)
    print(result.stdout)
    print()
    
    if result.stderr:
        print("=" * 80)
        print("STDERR:")
        print("=" * 80)
        print(result.stderr)
        print()
    
    if result.returncode != 0:
        print(f"❌ Command failed with exit code {result.returncode}")
        return None
    
    # Try to extract prompt_id
    match = re.search(r'Prompt ID:\s*([a-f0-9\-]+)', result.stdout, re.IGNORECASE)
    
    if match:
        prompt_id = match.group(1)
        print(f"✅ Successfully queued! Prompt ID: {prompt_id}")
        return prompt_id
    else:
        if 'Success' in result.stdout or 'queued' in result.stdout.lower():
            print("⚠️  Workflow queued but prompt_id not found in output")
            return f"queued_unknown"
        else:
            print("❌ Could not extract prompt_id from output")
            return None


def queue_with_api(ssh_connection, workflow_path):
    """Queue workflow using direct ComfyUI API (fallback method)."""
    host, port = parse_ssh_connection(ssh_connection)
    
    print(f"\n🚀 Queueing workflow via ComfyUI API...")
    print(f"   Workflow: {workflow_path}")
    
    python_script = f"""
import json
import requests

try:
    # Load workflow
    with open('{workflow_path}', 'r') as f:
        workflow = json.load(f)
    
    # Queue via API
    response = requests.post(
        'http://localhost:18188/prompt',
        json={{'prompt': workflow, 'client_id': 'test_script'}},
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
"""
    
    cmd = [
        'ssh',
        '-p', port,
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        f'root@{host}',
        f'python3 -c "{python_script}"'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    
    print("=" * 80)
    print("STDOUT:")
    print("=" * 80)
    print(result.stdout)
    print()
    
    if result.stderr:
        print("=" * 80)
        print("STDERR:")
        print("=" * 80)
        print(result.stderr)
        print()
    
    if result.returncode != 0:
        print(f"❌ Command failed with exit code {result.returncode}")
        return None
    
    # Parse output
    output = result.stdout.strip()
    
    if 'SUCCESS' in output:
        lines = output.split('\n')
        for line in lines:
            if line.startswith('PROMPT_ID:'):
                prompt_id = line.split(':', 1)[1].strip()
                print(f"✅ Successfully queued! Prompt ID: {prompt_id}")
                return prompt_id
    
    print("❌ Failed to queue workflow")
    return None


def main():
    parser = argparse.ArgumentParser(
        description='Test BrowserAgent workflow queueing in isolation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--ssh',
        required=True,
        help='SSH connection string (e.g., "ssh -p 40738 root@198.53.64.194")'
    )
    
    parser.add_argument(
        '--workflow-path',
        help='Remote path to workflow file (e.g., /workspace/ComfyUI/user/default/workflows/workflow.json)'
    )
    
    parser.add_argument(
        '--local-workflow',
        help='Local workflow file to upload first'
    )
    
    parser.add_argument(
        '--method',
        choices=['browseragent', 'api'],
        default='browseragent',
        help='Queueing method to use (default: browseragent)'
    )
    
    parser.add_argument(
        '--comfyui-url',
        default='http://localhost:18188',
        help='ComfyUI URL (default: http://localhost:18188)'
    )
    
    parser.add_argument(
        '--skip-checks',
        action='store_true',
        help='Skip prerequisite checks'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output from BrowserAgent'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.workflow_path and not args.local_workflow:
        parser.error('Either --workflow-path or --local-workflow is required')
    
    print("=" * 80)
    print("BrowserAgent Workflow Queueing Test")
    print("=" * 80)
    print()
    
    try:
        # Run prerequisite checks
        if not args.skip_checks:
            print("Running prerequisite checks...\n")
            
            if not check_comfyui_running(args.ssh):
                print("\n⚠️  ComfyUI is not running. The queueing will likely fail.")
                response = input("Continue anyway? (y/N): ")
                if response.lower() != 'y':
                    return 1
            
            if args.method == 'browseragent':
                if not check_browseragent_installed(args.ssh):
                    print("\n⚠️  BrowserAgent is not installed.")
                    print("You can either:")
                    print("  1. Install BrowserAgent on the remote instance")
                    print("  2. Use --method api for direct API queueing")
                    response = input("\nSwitch to API method? (y/N): ")
                    if response.lower() == 'y':
                        args.method = 'api'
                    else:
                        return 1
            
            print()
        
        # Handle workflow path
        workflow_path = args.workflow_path
        
        if args.local_workflow:
            if not Path(args.local_workflow).exists():
                print(f"❌ Local workflow file not found: {args.local_workflow}")
                return 1
            
            workflow_path = upload_workflow_to_remote(args.ssh, args.local_workflow)
            print()
        else:
            # Check if remote workflow exists
            if not check_remote_file_exists(args.ssh, workflow_path):
                print(f"❌ Workflow file not found on remote: {workflow_path}")
                return 1
            print(f"✅ Remote workflow file exists: {workflow_path}\n")
        
        # Queue workflow
        if args.method == 'browseragent':
            prompt_id = queue_with_browseragent(
                args.ssh,
                workflow_path,
                args.comfyui_url,
                args.verbose
            )
        else:
            prompt_id = queue_with_api(args.ssh, workflow_path)
        
        if prompt_id:
            print("\n" + "=" * 80)
            print(f"✅ Test completed successfully!")
            print(f"   Prompt ID: {prompt_id}")
            print("=" * 80)
            return 0
        else:
            print("\n" + "=" * 80)
            print("❌ Test failed - could not queue workflow")
            print("=" * 80)
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        return 130
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
