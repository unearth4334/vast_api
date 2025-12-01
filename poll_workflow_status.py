#!/usr/bin/env python3
"""
Poll ComfyUI workflow execution status via SSH
"""
import subprocess
import json
import time
import sys

SSH_CONNECTION = "ssh -p 40538 root@198.53.64.194"
PROMPT_ID = "2c8cc6e4-f9f2-43df-aa36-5056f73063b8"
COMFYUI_PORT = 18188
POLL_INTERVAL = 5  # seconds

def run_ssh_command(command):
    """Execute command via SSH and return cleaned output"""
    full_command = f"{SSH_CONNECTION} '{command}'"
    try:
        result = subprocess.run(
            full_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Filter out the welcome message (lines starting with specific patterns)
        lines = result.stdout.split('\n')
        filtered_lines = []
        skip_welcome = False
        
        for line in lines:
            # Skip welcome banner lines
            if any(marker in line for marker in ['***', '===', 'Welcome', 'Instance ID', 'Public IP']):
                skip_welcome = True
                continue
            if skip_welcome and line.strip() == '':
                skip_welcome = False
                continue
            if not skip_welcome:
                filtered_lines.append(line)
        
        output = '\n'.join(filtered_lines).strip()
        return output, result.returncode
        
    except subprocess.TimeoutExpired:
        return "", -1
    except Exception as e:
        print(f"Error executing SSH command: {e}")
        return "", -1

def get_queue_status():
    """Get current queue status"""
    command = f"curl -s http://localhost:{COMFYUI_PORT}/queue"
    output, returncode = run_ssh_command(command)
    
    if returncode != 0 or not output:
        return None
    
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None

def get_history(prompt_id):
    """Get execution history for a specific prompt"""
    command = f"curl -s http://localhost:{COMFYUI_PORT}/history/{prompt_id}"
    output, returncode = run_ssh_command(command)
    
    if returncode != 0 or not output:
        return None
    
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None

def check_prompt_status(prompt_id):
    """Check if prompt is in queue or completed"""
    # Check queue first
    queue_status = get_queue_status()
    if queue_status:
        # Check running queue
        for item in queue_status.get('queue_running', []):
            if item[1] == prompt_id:
                return 'running', item
        
        # Check pending queue
        for item in queue_status.get('queue_pending', []):
            if item[1] == prompt_id:
                return 'pending', item
    
    # Check history
    history = get_history(prompt_id)
    if history and prompt_id in history:
        prompt_data = history[prompt_id]
        status = prompt_data.get('status', {})
        
        if status.get('completed', False):
            return 'completed', prompt_data
        elif 'error' in status:
            return 'error', prompt_data
    
    return 'unknown', None

def format_node_progress(outputs):
    """Format node execution progress"""
    if not outputs:
        return "No outputs yet"
    
    progress = []
    for node_id, node_data in outputs.items():
        node_info = node_data.get('_meta', {}).get('title', f"Node {node_id}")
        progress.append(f"  ✓ {node_info}")
    
    return "\n".join(progress) if progress else "Processing..."

def main():
    print("=" * 60)
    print("ComfyUI Workflow Execution Monitor")
    print("=" * 60)
    print(f"Prompt ID: {PROMPT_ID}")
    print(f"Poll Interval: {POLL_INTERVAL}s")
    print("=" * 60)
    print()
    
    last_status = None
    completed_nodes = set()
    
    try:
        while True:
            status, data = check_prompt_status(PROMPT_ID)
            
            if status != last_status:
                timestamp = time.strftime("%H:%M:%S")
                
                if status == 'pending':
                    print(f"[{timestamp}] ⏳ Workflow is PENDING in queue")
                    queue_position = None
                    if data:
                        queue_position = data[0]  # Position in queue
                    if queue_position is not None:
                        print(f"           Queue position: {queue_position}")
                
                elif status == 'running':
                    print(f"[{timestamp}] ▶️  Workflow is RUNNING")
                
                elif status == 'completed':
                    print(f"[{timestamp}] ✅ Workflow COMPLETED!")
                    
                    # Show outputs
                    if data and 'outputs' in data:
                        outputs = data['outputs']
                        print(f"\n📦 Generated Outputs:")
                        print(format_node_progress(outputs))
                    
                    # Show any final messages
                    if data and 'status' in data:
                        status_info = data['status']
                        if 'messages' in status_info:
                            print(f"\n📝 Messages:")
                            for msg in status_info['messages']:
                                print(f"  {msg}")
                    
                    print("\n✓ Execution finished successfully!")
                    break
                
                elif status == 'error':
                    print(f"[{timestamp}] ❌ Workflow FAILED")
                    
                    if data and 'status' in data:
                        status_info = data['status']
                        if 'error' in status_info:
                            error = status_info['error']
                            print(f"\n⚠️  Error Details:")
                            print(f"  Type: {error.get('exception_type', 'Unknown')}")
                            print(f"  Message: {error.get('exception_message', 'No message')}")
                            if 'node_id' in error:
                                print(f"  Failed Node: {error['node_id']}")
                            if 'traceback' in error:
                                print(f"\n  Traceback:")
                                for line in error['traceback']:
                                    print(f"    {line}")
                    
                    break
                
                elif status == 'unknown':
                    print(f"[{timestamp}] ❓ Status UNKNOWN - workflow may have been cancelled or cleared from history")
                    break
                
                last_status = status
            
            # Show progress for running workflows
            if status == 'running' and data:
                history = get_history(PROMPT_ID)
                if history and PROMPT_ID in history:
                    outputs = history[PROMPT_ID].get('outputs', {})
                    new_nodes = set(outputs.keys()) - completed_nodes
                    
                    if new_nodes:
                        timestamp = time.strftime("%H:%M:%S")
                        for node_id in new_nodes:
                            node_data = outputs[node_id]
                            node_title = node_data.get('_meta', {}).get('title', f"Node {node_id}")
                            print(f"[{timestamp}] ✓ Completed: {node_title}")
                        
                        completed_nodes.update(new_nodes)
            
            time.sleep(POLL_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Monitoring stopped by user")
        print("   (Workflow will continue running on the server)")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
