#!/usr/bin/env python3
"""
Troubleshooting guide for "📁 Set UI_HOME" button not responding.
This script provides step-by-step verification of the complete workflow.
"""

import requests
import json

BASE_URL = "http://10.0.78.66:5000"

def check_step(step_name, check_func, fix_suggestion=""):
    """Helper function to check each step and provide feedback."""
    print(f"\n📋 {step_name}")
    print("-" * 50)
    
    try:
        success, message = check_func()
        if success:
            print(f"✅ {message}")
            return True
        else:
            print(f"❌ {message}")
            if fix_suggestion:
                print(f"💡 Fix: {fix_suggestion}")
            return False
    except Exception as e:
        print(f"🚨 Error during check: {e}")
        return False

def check_api_connection():
    """Check if the API server is running and responsive."""
    try:
        response = requests.get(f"{BASE_URL}/vastai/instances", timeout=5)
        if response.status_code == 200:
            data = response.json()
            instance_count = len(data.get('instances', []))
            return True, f"API server is running. Found {instance_count} VastAI instances."
        else:
            return False, f"API server responded with status {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to API server"
    except Exception as e:
        return False, f"API connection error: {e}"

def check_templates():
    """Check if templates are loading correctly."""
    try:
        response = requests.get(f"{BASE_URL}/templates")
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('templates'):
                template_count = len(data['templates'])
                comfyui_found = any(t['id'] == 'comfyui' for t in data['templates'])
                if comfyui_found:
                    return True, f"Templates loading correctly. Found {template_count} templates including ComfyUI."
                else:
                    return False, "ComfyUI template not found in template list"
            else:
                return False, "Templates endpoint returned unsuccessful response"
        else:
            return False, f"Templates endpoint returned status {response.status_code}"
    except Exception as e:
        return False, f"Template loading error: {e}"

def check_comfyui_template():
    """Check if ComfyUI template has the correct UI configuration."""
    try:
        response = requests.get(f"{BASE_URL}/templates/comfyui")
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('template'):
                template = data['template']
                ui_config = template.get('ui_config', {})
                setup_buttons = ui_config.get('setup_buttons', [])
                
                set_ui_home_button = next((b for b in setup_buttons if b['action'] == 'set_ui_home'), None)
                if set_ui_home_button:
                    return True, f"ComfyUI template has '📁 Set UI_HOME' button: {set_ui_home_button['label']}"
                else:
                    return False, "ComfyUI template missing 'set_ui_home' button configuration"
            else:
                return False, "ComfyUI template endpoint returned unsuccessful response"
        else:
            return False, f"ComfyUI template endpoint returned status {response.status_code}"
    except Exception as e:
        return False, f"ComfyUI template check error: {e}"

def check_template_execution():
    """Check if template execution endpoint works."""
    try:
        test_data = {
            "step_name": "Set UI Home",
            "ssh_connection": "ssh -p 40150 root@39.114.238.31 -L 8080:localhost:8080",
            "instance_id": "test"
        }
        
        response = requests.post(
            f"{BASE_URL}/templates/comfyui/execute-step",
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return True, f"Template execution working. Result: {data.get('message', 'Success')}"
            else:
                return True, f"Template execution API working (expected SSH failure): {data.get('message', 'No message')}"
        else:
            return False, f"Template execution endpoint returned status {response.status_code}"
    except Exception as e:
        return False, f"Template execution error: {e}"

def check_instance_with_ssh():
    """Check if there's a running VastAI instance that can provide SSH connection."""
    try:
        response = requests.get(f"{BASE_URL}/vastai/instances")
        if response.status_code == 200:
            data = response.json()
            instances = data.get('instances', [])
            
            running_instances = [i for i in instances if str(i.get('actual_status', '')).lower() == 'running']
            if running_instances:
                instance = running_instances[0]
                host = instance.get('public_ipaddr', 'N/A')
                ports = instance.get('ports', {})
                ssh_port = None
                
                if ports and '22/tcp' in ports:
                    tcp_ports = ports['22/tcp']
                    if tcp_ports and len(tcp_ports) > 0:
                        ssh_port = tcp_ports[0].get('HostPort')
                
                if host != 'N/A' and ssh_port:
                    ssh_connection = f"ssh -p {ssh_port} root@{host}"
                    return True, f"Found running instance with SSH: {ssh_connection}"
                else:
                    return False, f"Running instance found but missing SSH details (host: {host}, port: {ssh_port})"
            else:
                return False, "No running VastAI instances found"
        else:
            return False, f"Instance check returned status {response.status_code}"
    except Exception as e:
        return False, f"Instance check error: {e}"

def main():
    """Run complete troubleshooting workflow."""
    print("🔧 VastAI Template Button Troubleshooting")
    print("=" * 60)
    print("This script will check each component of the template button system.")
    print("")
    
    # Step 1: API Connection
    api_ok = check_step(
        "Step 1: API Server Connection",
        check_api_connection,
        "Ensure the container is running: docker ps | grep media-sync-api"
    )
    
    # Step 2: Template Loading
    templates_ok = check_step(
        "Step 2: Template System",
        check_templates,
        "Check if template files exist and are properly formatted"
    )
    
    # Step 3: ComfyUI Template
    comfyui_ok = check_step(
        "Step 3: ComfyUI Template Configuration",
        check_comfyui_template,
        "Verify templates_comfyui.yml has correct ui_config.setup_buttons"
    )
    
    # Step 4: Template Execution
    execution_ok = check_step(
        "Step 4: Template Execution API",
        check_template_execution,
        "Check container logs for any backend errors"
    )
    
    # Step 5: VastAI Instance
    instance_ok = check_step(
        "Step 5: Running VastAI Instance",
        check_instance_with_ssh,
        "Ensure you have a running VastAI instance with SSH access"
    )
    
    # Summary
    print(f"\n📊 TROUBLESHOOTING SUMMARY")
    print("=" * 60)
    
    issues_found = []
    if not api_ok:
        issues_found.append("API server connection")
    if not templates_ok:
        issues_found.append("Template loading")
    if not comfyui_ok:
        issues_found.append("ComfyUI template configuration")
    if not execution_ok:
        issues_found.append("Template execution API")
    if not instance_ok:
        issues_found.append("VastAI instance availability")
    
    if not issues_found:
        print("✅ ALL SYSTEMS OPERATIONAL")
        print("")
        print("🎯 If the '📁 Set UI_HOME' button still doesn't respond:")
        print("   1. Open browser developer tools (F12)")
        print("   2. Check Console tab for JavaScript errors")
        print("   3. Verify template is selected in dropdown")
        print("   4. Verify SSH connection string is populated")
        print("   5. Check Network tab when clicking button")
        print("")
        print("📋 Required User Actions:")
        print("   1. Select running VastAI instance (to populate SSH connection)")
        print("   2. Select 'ComfyUI' from template dropdown")  
        print("   3. Click '📁 Set UI_HOME' button")
        print("   4. Check setup result area for response")
        return 0
    else:
        print("❌ ISSUES FOUND:")
        for issue in issues_found:
            print(f"   - {issue}")
        print("")
        print("🔧 Fix the issues above before testing template buttons.")
        return 1

if __name__ == "__main__":
    exit(main())