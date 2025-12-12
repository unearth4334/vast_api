#!/usr/bin/env python3
"""
Test script to verify downloads queue creates separate jobs per resource
"""
import requests
import json

BASE_URL = "http://10.0.78.66:5001"

def test_queue_multiple_resources():
    """Test that selecting 3 resources creates 3 separate jobs"""
    
    # Mock data: 3 resources
    resources = [
        {'filepath': 'upscalers/Upscaler-RealESRGAN_4xplus.md'},
        {'filepath': 'loras/wan21_fusionx.md'},
        {'filepath': 'encoders/some_encoder.md'}  # This may not exist, but that's ok for the test
    ]
    
    payload = {
        'ssh_connection': 'ssh -p 44686 root@109.231.106.68 -L 8080:localhost:8080',
        'resources': resources,
        'ui_home': '/workspace/ComfyUI'
    }
    
    print("Sending POST /downloads/queue with 3 resources...")
    response = requests.post(f"{BASE_URL}/downloads/queue", json=payload)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            jobs = data.get('jobs', [])
            print(f"\n✅ Success! Created {len(jobs)} jobs")
            for i, job in enumerate(jobs, 1):
                resource_paths = job.get('resource_paths', [])
                commands = job.get('commands', [])
                print(f"\nJob {i}:")
                print(f"  - ID: {job['id']}")
                print(f"  - Resources: {resource_paths}")
                print(f"  - Commands: {len(commands)} command(s)")
                print(f"  - Status: {job['status']}")
        else:
            print(f"❌ Failed: {data.get('message')}")
    else:
        print(f"❌ HTTP Error: {response.status_code}")

if __name__ == '__main__':
    test_queue_multiple_resources()
