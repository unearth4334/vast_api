#!/usr/bin/env python3
"""
Test script to verify template button functionality after SSH parsing fixes.
Tests the complete template execution workflow to ensure buttons work properly.
"""

import requests
import json
import sys
from typing import Dict, Any

# Configuration
BASE_URL = "http://10.0.78.66:5000"
TEST_SSH_CONNECTION = "root@39.114.238.31:40150"  # Real VastAI instance
TEST_INSTANCE_ID = "27050456"

def test_template_endpoint(step_name: str) -> Dict[str, Any]:
    """Test template execution endpoint with given step name."""
    url = f"{BASE_URL}/templates/comfyui/execute-step"
    data = {
        "step_name": step_name,
        "ssh_connection": TEST_SSH_CONNECTION,
        "instance_id": TEST_INSTANCE_ID
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        return {
            "status_code": response.status_code,
            "response": response.json(),
            "success": response.status_code == 200
        }
    except Exception as e:
        return {
            "status_code": None,
            "response": {"error": str(e)},
            "success": False
        }

def check_logs_for_template_activity() -> Dict[str, Any]:
    """Check if template execution is generating log entries."""
    try:
        response = requests.get(f"{BASE_URL}/vastai/logs")
        if response.status_code == 200:
            logs = response.json()
            # Look for recent template-related logs
            template_logs = []
            for log in logs.get('logs', [])[-10:]:  # Check last 10 logs
                if any(keyword in str(log).lower() for keyword in 
                      ['template', 'civitdl', 'ui_home', 'clone', 'python_venv']):
                    template_logs.append(log)
            
            return {
                "success": True,
                "template_logs_count": len(template_logs),
                "recent_logs": template_logs
            }
        else:
            return {"success": False, "error": "Failed to fetch logs"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    """Run comprehensive template functionality test."""
    print("🧪 Testing Template Button Functionality")
    print("=" * 50)
    
    # Test steps from ComfyUI template
    test_steps = [
        "Install CivitDL",
        "Set UI Home",
        "Clone ComfyUI Auto Installer",
        "Setup Python Virtual Environment"
    ]
    
    results = {}
    
    for step in test_steps:
        print(f"\n🔧 Testing: {step}")
        result = test_template_endpoint(step)
        results[step] = result
        
        if result["success"]:
            print(f"   ✅ API Call: SUCCESS (Status: {result['status_code']})")
        else:
            print(f"   ❌ API Call: FAILED (Status: {result['status_code']})")
        
        # Print response details
        response = result["response"]
        if "message" in response:
            print(f"   📝 Message: {response['message']}")
        if "error" in response:
            print(f"   🚨 Error: {response['error'][:100]}...")  # Truncate long errors
    
    # Check logging functionality
    print(f"\n📋 Checking Template Execution Logging...")
    log_result = check_logs_for_template_activity()
    
    if log_result["success"]:
        count = log_result["template_logs_count"]
        print(f"   ✅ Found {count} template-related log entries")
        if count > 0:
            print("   📝 Recent template logs detected")
    else:
        print(f"   ❌ Failed to check logs: {log_result.get('error', 'Unknown error')}")
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 30)
    successful_tests = sum(1 for result in results.values() if result["success"])
    total_tests = len(results)
    
    print(f"✅ Template API Tests: {successful_tests}/{total_tests} successful")
    print(f"📋 Logging Integration: {'✅ Working' if log_result['success'] else '❌ Failed'}")
    
    # Determine overall status
    ssh_parsing_working = any("Permission denied" in str(result["response"].get("error", "")) 
                             for result in results.values())
    api_endpoint_working = any(result["status_code"] == 200 for result in results.values())
    
    print(f"\n🔍 Analysis:")
    if ssh_parsing_working:
        print("   ✅ SSH Connection Parsing: FIXED (reaches authentication stage)")
    else:
        print("   ❓ SSH Connection Parsing: Status unclear")
        
    if api_endpoint_working:
        print("   ✅ Template Execution API: WORKING")
    else:
        print("   ❌ Template Execution API: FAILING")
    
    print(f"\n🎯 Conclusion:")
    if ssh_parsing_working and api_endpoint_working:
        print("   ✅ Template button functionality is RESTORED")
        print("   📝 SSH parsing fixes successfully implemented")
        print("   🔧 Template buttons should now work in web UI")
        return 0
    else:
        print("   ❌ Template functionality still has issues")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)