#!/usr/bin/env python3
"""
Demo script to show mobile-optimized progress tracking in action
This simulates what happens when using the mobile Obsidian integration
"""

import json
import time
import uuid
import os
import requests
from datetime import datetime


def create_mock_progress_file():
    """Create a mock progress file to simulate a running sync"""
    sync_id = str(uuid.uuid4())
    progress_file = f"/tmp/sync_progress_{sync_id}.json"
    
    # Simulate progress stages
    stages = [
        {"stage": "initialization", "percent": 5, "message": "Setting up SSH connection"},
        {"stage": "remote_discovery", "percent": 15, "message": "Discovering remote paths"},
        {"stage": "folder_discovery", "percent": 25, "message": "Finding folders to sync"},
        {"stage": "sync_folders", "percent": 45, "message": "Syncing folder 1 of 4"},
        {"stage": "sync_folders", "percent": 65, "message": "Syncing folder 2 of 4"},
        {"stage": "sync_folders", "percent": 85, "message": "Syncing folder 3 of 4"},
        {"stage": "complete", "percent": 100, "message": "Sync completed successfully"},
    ]
    
    print(f"🔄 Creating mock sync with ID: {sync_id[:8]}...")
    
    for i, stage_info in enumerate(stages):
        # Create/update progress file
        progress_data = {
            "sync_id": sync_id,
            "status": "completed" if stage_info["percent"] >= 100 else "running",
            "current_stage": stage_info["stage"],
            "progress_percent": stage_info["percent"],
            "total_folders": 4,
            "completed_folders": max(0, i - 2),
            "current_folder": f"folder-{i+1}" if i < 6 else "",
            "messages": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "message": stage_info["message"]
                }
            ],
            "start_time": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat()
        }
        
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
        
        print(f"  📊 Progress: {stage_info['percent']}% - {stage_info['message']}")
        
        # Simulate time delay between stages
        if i < len(stages) - 1:
            time.sleep(2)
    
    return sync_id, progress_file


def test_mobile_endpoints():
    """Test the mobile-optimized endpoints"""
    # Start the Flask test server in the background
    from sync_api import app
    client = app.test_client()
    
    print("\n🧪 Testing mobile endpoints...")
    
    # Test mobile latest without any progress files
    print("\n1. Testing mobile/latest with no active syncs:")
    response = client.get('/sync/mobile/latest')
    print(f"   Status: {response.status_code}")
    if response.status_code == 404:
        data = response.get_json()
        print(f"   Message: {data['message']}")
    
    # Create a mock progress file
    sync_id, progress_file = create_mock_progress_file()
    
    # Test mobile latest with active sync
    print(f"\n2. Testing mobile/latest with active sync ({sync_id[:8]}):")
    response = client.get('/sync/mobile/latest')
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.get_json()
        print(f"   Sync ID: {data['sync_id'][:8]}...")
        progress = data['progress']
        print(f"   Progress: {progress['progress_percent']}%")
        print(f"   Stage: {progress['current_stage']}")
        print(f"   Message: {progress.get('latest_message', 'N/A')}")
        print(f"   Mobile optimized: {'latest_message' in progress and 'messages' not in progress}")
    
    # Test mobile progress endpoint
    print(f"\n3. Testing mobile/progress/{sync_id[:8]}:")
    response = client.get(f'/sync/mobile/progress/{sync_id}')
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.get_json()
        progress = data['progress']
        print(f"   Progress: {progress['progress_percent']}%")
        print(f"   Current folder: {progress.get('current_folder', 'N/A')}")
        print(f"   Timestamp: {data.get('timestamp', 'N/A')}")
        print(f"   Cache headers: {response.headers.get('Cache-Control', 'N/A')}")
    
    # Compare desktop vs mobile response sizes
    print(f"\n4. Comparing desktop vs mobile response sizes:")
    desktop_response = client.get('/sync/latest')
    mobile_response = client.get('/sync/mobile/latest')
    
    if desktop_response.status_code == 200 and mobile_response.status_code == 200:
        desktop_size = len(desktop_response.data)
        mobile_size = len(mobile_response.data)
        print(f"   Desktop response: {desktop_size} bytes")
        print(f"   Mobile response: {mobile_size} bytes")
        print(f"   Mobile reduction: {(1 - mobile_size/desktop_size)*100:.1f}%")
    
    # Cleanup
    try:
        os.remove(progress_file)
        print(f"\n🧹 Cleaned up progress file: {progress_file}")
    except:
        pass


def simulate_mobile_polling():
    """Simulate how mobile client would poll for progress"""
    print("\n📱 Simulating mobile client polling behavior...")
    
    # Create a progress file that updates over time
    sync_id = str(uuid.uuid4())
    progress_file = f"/tmp/sync_progress_{sync_id}.json"
    
    from sync_api import app
    client = app.test_client()
    
    # Simulate mobile user agent
    headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)'}
    
    print(f"   Starting mock sync: {sync_id[:8]}...")
    
    # Simulate polling with mobile-like intervals
    poll_intervals = [3, 3, 5, 5, 3, 5]  # Variable intervals like a real mobile client
    
    for i, interval in enumerate(poll_intervals):
        # Update progress file
        progress_percent = min(100, 10 + i * 15)
        progress_data = {
            "sync_id": sync_id,
            "status": "completed" if progress_percent >= 100 else "running",
            "current_stage": "syncing" if progress_percent < 100 else "complete",
            "progress_percent": progress_percent,
            "current_folder": f"processing-folder-{i+1}",
            "messages": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Processing step {i+1}"
                }
            ],
            "last_update": datetime.now().isoformat()
        }
        
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
        
        # Poll mobile endpoint
        response = client.get(f'/sync/mobile/progress/{sync_id}', headers=headers)
        
        if response.status_code == 200:
            data = response.get_json()
            progress = data['progress']
            print(f"   Poll {i+1}: {progress['progress_percent']}% - {progress.get('latest_message', '')}")
        else:
            print(f"   Poll {i+1}: Error {response.status_code}")
        
        if progress_percent >= 100:
            print("   🎉 Sync completed!")
            break
        
        # Wait for next poll (simulating mobile polling interval)
        time.sleep(interval)
    
    # Cleanup
    try:
        os.remove(progress_file)
    except:
        pass


if __name__ == '__main__':
    print("🔄 Mobile Progress Tracking Demo")
    print("=" * 50)
    
    test_mobile_endpoints()
    simulate_mobile_polling()
    
    print("\n✅ Demo completed successfully!")
    print("\nKey improvements for mobile:")
    print("• Reduced payload sizes for slow networks")
    print("• Better error handling and timeouts")
    print("• Mobile-specific cache headers")
    print("• Simplified progress data structure")
    print("• User-agent detection for adaptive responses")