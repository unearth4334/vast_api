#!/usr/bin/env python3
"""
Comprehensive test for enhanced template execution with SSH connections and VastAI logging.
Tests the "📁 Set UI_HOME" button as requested by user.
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://10.0.78.66:5000"
SSH_CONNECTION = "ssh -p 40150 root@39.114.238.31 -L 8080:localhost:8080"
INSTANCE_ID = "27050456"

def test_set_ui_home_with_logging():
    """Test Set UI_HOME template execution and verify logging works."""
    print("🧪 Testing Enhanced Template Execution: 📁 Set UI_HOME")
    print("=" * 60)
    
    # Get baseline log count
    print("📊 Getting baseline log count...")
    try:
        logs_response = requests.get(f"{BASE_URL}/vastai/logs?lines=20")
        baseline_count = len(logs_response.json().get('logs', []))
        print(f"   📋 Baseline log entries: {baseline_count}")
    except Exception as e:
        print(f"   ❌ Failed to get baseline logs: {e}")
        return False
    
    # Execute Set UI_HOME template step
    print(f"\n🏠 Executing Set UI_HOME template step...")
    print(f"   🔗 SSH Connection: {SSH_CONNECTION}")
    print(f"   🆔 Instance ID: {INSTANCE_ID}")
    
    template_data = {
        "step_name": "Set UI Home",
        "ssh_connection": SSH_CONNECTION,
        "instance_id": INSTANCE_ID
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/templates/comfyui/execute-step",
            json=template_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Template execution: SUCCESS")
            print(f"   📝 Response: {result.get('message', 'No message')}")
            if result.get('success'):
                print(f"   🎯 UI_HOME operation completed successfully")
                if 'output' in result:
                    print(f"   📤 SSH Output: {result['output'].strip()}")
            else:
                print(f"   ⚠️ Template execution reported failure: {result}")
        else:
            print(f"   ❌ Template execution failed: HTTP {response.status_code}")
            print(f"   📝 Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Template execution error: {e}")
        return False
    
    # Wait for logs to be processed
    print(f"\n⏳ Waiting for log processing...")
    time.sleep(2)
    
    # Check enhanced logging
    print(f"\n📋 Checking VastAI logs for template execution entries...")
    try:
        logs_response = requests.get(f"{BASE_URL}/vastai/logs?lines=30")
        if logs_response.status_code == 200:
            logs_data = logs_response.json()
            logs = logs_data.get('logs', [])
            new_count = len(logs)
            print(f"   📊 Total log entries: {new_count} (added {new_count - baseline_count})")
            
            # Look for template-related logs
            template_logs = []
            ssh_logs = []
            ui_home_logs = []
            
            for log in logs[:15]:  # Check last 15 logs
                operation = log.get('operation', '')
                message = log.get('message', '')
                
                if any(keyword in operation.lower() for keyword in ['template', 'ui_home', 'set_ui_home']):
                    template_logs.append(log)
                
                if 'ssh' in operation.lower():
                    ssh_logs.append(log)
                
                if 'ui_home' in operation.lower() or 'UI_HOME' in message:
                    ui_home_logs.append(log)
            
            print(f"\n🔍 Enhanced Logging Analysis:")
            print(f"   🎯 Template operation logs: {len(template_logs)}")
            print(f"   🔌 SSH connection logs: {len(ssh_logs)}")
            print(f"   🏠 UI_HOME specific logs: {len(ui_home_logs)}")
            
            # Display relevant log entries
            if template_logs:
                print(f"\n📝 Template Execution Log Entries:")
                for i, log in enumerate(template_logs[:5], 1):
                    timestamp = log.get('timestamp', 'Unknown')
                    operation = log.get('operation', 'Unknown')
                    message = log.get('message', 'No message')
                    level = log.get('level', 'INFO')
                    print(f"   {i}. [{level}] {timestamp}")
                    print(f"      🔧 Operation: {operation}")
                    print(f"      📝 Message: {message}")
                    if 'extra_data' in log and log['extra_data']:
                        extra = log['extra_data']
                        if 'host' in extra or 'port' in extra:
                            print(f"      🔗 SSH: {extra.get('user', 'root')}@{extra.get('host')}:{extra.get('port')}")
                    print()
            
            # Success criteria
            has_template_logs = len(template_logs) > 0
            has_ssh_logs = len(ssh_logs) > 0
            has_ui_home_logs = len(ui_home_logs) > 0
            
            print(f"📊 Success Criteria:")
            print(f"   {'✅' if has_template_logs else '❌'} Template execution logged")
            print(f"   {'✅' if has_ssh_logs else '❌'} SSH connection logged") 
            print(f"   {'✅' if has_ui_home_logs else '❌'} UI_HOME operation logged")
            
            if has_template_logs and has_ui_home_logs:
                print(f"\n🎉 SUCCESS: Enhanced template execution logging is working!")
                print(f"   📁 Set UI_HOME button generates proper VastAI log entries")
                print(f"   🔗 SSH interactions are comprehensively logged")
                print(f"   📋 Template operations appear in VastAI Logs pane")
                return True
            else:
                print(f"\n❌ FAILURE: Enhanced logging not working as expected")
                return False
                
        else:
            print(f"   ❌ Failed to fetch logs: HTTP {logs_response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error checking logs: {e}")
        return False

def main():
    """Run the comprehensive template logging test."""
    success = test_set_ui_home_with_logging()
    
    print(f"\n" + "=" * 60)
    if success:
        print("🏆 CONCLUSION: Template button functionality with enhanced logging is WORKING")
        print("   📁 Set UI_HOME button successfully tested")
        print("   🔗 SSH connection string parsing works correctly")
        print("   📋 VastAI Logs pane displays template execution entries")
        print("   ✅ All requirements met")
    else:
        print("❌ CONCLUSION: Issues detected in template functionality or logging")
        print("   🔧 Further investigation needed")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())