#!/usr/bin/env python3
"""
API Integration Tests for Resource Manager

Tests the Flask API endpoints with actual HTTP requests.
"""

import sys
import os
import json
import time
import subprocess
import requests
from threading import Thread

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class APITestServer:
    """Helper class to manage test server"""
    
    def __init__(self, port=5555):
        self.port = port
        self.base_url = f"http://localhost:{port}"
        self.process = None
    
    def start(self):
        """Start the Flask server in a subprocess"""
        print(f"Starting test server on port {self.port}...")
        
        # Start server
        env = os.environ.copy()
        env['FLASK_APP'] = 'app.sync.sync_api'
        env['FLASK_ENV'] = 'development'
        
        self.process = subprocess.Popen(
            ['python3', '-m', 'flask', 'run', '--port', str(self.port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        
        # Wait for server to start
        max_attempts = 30
        for i in range(max_attempts):
            try:
                response = requests.get(f"{self.base_url}/status", timeout=1)
                if response.status_code == 200:
                    print(f"✓ Server started successfully on port {self.port}")
                    return True
            except requests.exceptions.RequestException:
                time.sleep(0.5)
        
        print(f"✗ Failed to start server after {max_attempts} attempts")
        return False
    
    def stop(self):
        """Stop the Flask server"""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            print("✓ Server stopped")


def test_api_resource_list():
    """Test GET /resources/list endpoint"""
    print("\n" + "=" * 70)
    print("Testing: GET /resources/list")
    print("=" * 70)
    
    server = APITestServer()
    
    try:
        if not server.start():
            print("✗ Could not start server")
            return False
        
        # Test 1: List all resources
        response = requests.get(f"{server.base_url}/resources/list")
        print(f"\nTest 1: List all resources")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success: {data.get('count', 0)} resources found")
            print(f"  Response keys: {list(data.keys())}")
        else:
            print(f"✗ Failed with status {response.status_code}")
            return False
        
        # Test 2: Filter by ecosystem
        response = requests.get(f"{server.base_url}/resources/list?ecosystem=sdxl")
        print(f"\nTest 2: Filter by ecosystem (sdxl)")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success: {data.get('count', 0)} SDXL resources found")
        
        # Test 3: Filter by type
        response = requests.get(f"{server.base_url}/resources/list?type=workflows")
        print(f"\nTest 3: Filter by type (workflows)")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success: {data.get('count', 0)} workflow resources found")
        
        # Test 4: Search
        response = requests.get(f"{server.base_url}/resources/list?search=upscaler")
        print(f"\nTest 4: Search (upscaler)")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success: {data.get('count', 0)} results found")
        
        return True
        
    finally:
        server.stop()


def test_api_metadata_endpoints():
    """Test metadata endpoints (ecosystems, types, tags)"""
    print("\n" + "=" * 70)
    print("Testing: Metadata Endpoints")
    print("=" * 70)
    
    server = APITestServer()
    
    try:
        if not server.start():
            print("✗ Could not start server")
            return False
        
        # Test ecosystems
        response = requests.get(f"{server.base_url}/resources/ecosystems")
        print(f"\nTest: GET /resources/ecosystems")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            ecosystems = data.get('ecosystems', [])
            print(f"✓ Success: Found {len(ecosystems)} ecosystems")
            print(f"  Ecosystems: {', '.join(ecosystems)}")
        
        # Test types
        response = requests.get(f"{server.base_url}/resources/types")
        print(f"\nTest: GET /resources/types")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            types = data.get('types', [])
            print(f"✓ Success: Found {len(types)} types")
            print(f"  Types: {', '.join(types)}")
        
        # Test tags
        response = requests.get(f"{server.base_url}/resources/tags")
        print(f"\nTest: GET /resources/tags")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            tags = data.get('tags', [])
            print(f"✓ Success: Found {len(tags)} tags")
            print(f"  Sample tags: {', '.join(tags[:10])}")
        
        return True
        
    finally:
        server.stop()


def test_api_get_resource():
    """Test GET /resources/get/<path> endpoint"""
    print("\n" + "=" * 70)
    print("Testing: GET /resources/get/<path>")
    print("=" * 70)
    
    server = APITestServer()
    
    try:
        if not server.start():
            print("✗ Could not start server")
            return False
        
        # Test getting a specific resource
        resource_path = "workflows/wan22_i2v.md"
        response = requests.get(f"{server.base_url}/resources/get/{resource_path}")
        print(f"\nTest: Get resource '{resource_path}'")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                resource = data.get('resource', {})
                print(f"✓ Success: Retrieved resource")
                print(f"  Type: {resource.get('metadata', {}).get('type')}")
                print(f"  Ecosystem: {resource.get('metadata', {}).get('ecosystem')}")
                print(f"  Has download command: {bool(resource.get('download_command'))}")
        else:
            print(f"✗ Failed with status {response.status_code}")
        
        # Test getting nonexistent resource
        response = requests.get(f"{server.base_url}/resources/get/nonexistent/resource.md")
        print(f"\nTest: Get nonexistent resource")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 404:
            print(f"✓ Success: Correctly returned 404 for nonexistent resource")
        
        return True
        
    finally:
        server.stop()


def test_api_search():
    """Test GET /resources/search endpoint"""
    print("\n" + "=" * 70)
    print("Testing: GET /resources/search")
    print("=" * 70)
    
    server = APITestServer()
    
    try:
        if not server.start():
            print("✗ Could not start server")
            return False
        
        search_queries = ['workflow', 'SDXL', 'upscaler', 'anime']
        
        for query in search_queries:
            response = requests.get(f"{server.base_url}/resources/search?q={query}")
            print(f"\nTest: Search for '{query}'")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Success: Found {data.get('count', 0)} results")
        
        # Test empty query
        response = requests.get(f"{server.base_url}/resources/search")
        print(f"\nTest: Search with empty query")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 400:
            print(f"✓ Success: Correctly returned 400 for empty query")
        
        return True
        
    finally:
        server.stop()


def run_api_tests():
    """Run all API integration tests"""
    print("=" * 70)
    print("RESOURCE MANAGER API INTEGRATION TESTS")
    print("=" * 70)
    print("\nNote: These tests require the Flask server to start.")
    print("If tests fail, ensure no other service is using port 5555.\n")
    
    tests = [
        test_api_resource_list,
        test_api_metadata_endpoints,
        test_api_get_resource,
        test_api_search,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
            time.sleep(1)  # Small delay between tests
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 70)
    print("API TEST SUMMARY")
    print("=" * 70)
    print(f"Total tests: {len(results)}")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")
    print("=" * 70)
    
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(run_api_tests())
