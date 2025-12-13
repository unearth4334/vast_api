#!/usr/bin/env python3
"""
Quick test to verify BrowserAgent API endpoint is working

Usage:
  python3 test_browser_agent_api.py <ssh_connection_string>
  
Example:
  python3 test_browser_agent_api.py "root@123.45.67.89 -p 12345"
"""

import sys
import requests

def test_browser_agent_endpoint(ssh_connection):
    """Test the BrowserAgent installation endpoint"""
    
    url = "http://localhost:5050/vastai/install-browser-agent"
    
    print("=" * 70)
    print("Testing BrowserAgent Installation API")
    print("=" * 70)
    print(f"\nEndpoint: {url}")
    print(f"SSH Connection: {ssh_connection}")
    print("\nSending request...")
    
    try:
        response = requests.post(
            url,
            json={'ssh_connection': ssh_connection},
            timeout=600  # 10 minutes
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print("\nResponse:")
        print(response.json())
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("\n✅ SUCCESS! BrowserAgent installation completed")
                if data.get('output'):
                    print("\nOutput:")
                    print(data['output'])
            else:
                print(f"\n❌ FAILED: {data.get('message')}")
                if data.get('error'):
                    print("\nError:")
                    print(data['error'])
        else:
            print(f"\n❌ HTTP Error: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("\n⏱️  Request timed out (exceeded 10 minutes)")
    except requests.exceptions.ConnectionError as e:
        print(f"\n🔌 Connection error: {e}")
        print("\nIs the Flask server running? Try:")
        print("  python3 app/sync/sync_api.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 test_browser_agent_api.py <ssh_connection_string>")
        print('Example: python3 test_browser_agent_api.py "root@123.45.67.89 -p 12345"')
        sys.exit(1)
    
    ssh_connection = sys.argv[1]
    test_browser_agent_endpoint(ssh_connection)
