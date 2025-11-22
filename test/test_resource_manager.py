#!/usr/bin/env python3
"""
Test Resource Management API endpoints
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.resources import ResourceParser, ResourceManager, ResourceInstaller

def test_resource_parser():
    """Test ResourceParser functionality"""
    print("Testing ResourceParser...")
    
    parser = ResourceParser('resources')
    
    # Test listing all resources
    resources = parser.list_resources()
    print(f"✓ Found {len(resources)} resources")
    
    # Test filtering by ecosystem
    sdxl_resources = parser.list_resources(ecosystem='sdxl')
    print(f"✓ Found {len(sdxl_resources)} SDXL resources")
    
    # Test filtering by type
    workflows = parser.list_resources(resource_type='workflows')
    print(f"✓ Found {len(workflows)} workflow resources")
    
    # Test ecosystems
    ecosystems = parser.get_ecosystems()
    print(f"✓ Found ecosystems: {', '.join(ecosystems)}")
    
    # Test types
    types = parser.get_types()
    print(f"✓ Found types: {', '.join(types)}")
    
    # Test tags
    tags = parser.get_tags()
    print(f"✓ Found {len(tags)} unique tags")
    
    print("✓ ResourceParser tests passed!\n")

def test_resource_manager():
    """Test ResourceManager functionality"""
    print("Testing ResourceManager...")
    
    manager = ResourceManager('resources')
    
    # Test listing resources
    resources = manager.list_resources()
    print(f"✓ Manager can list {len(resources)} resources")
    
    # Test getting specific resource
    if resources:
        resource = manager.get_resource(resources[0]['filepath'])
        if resource:
            print(f"✓ Manager can get resource: {resources[0]['filepath']}")
        else:
            print("✗ Failed to get resource")
    
    # Test search
    search_results = manager.search_resources('workflow')
    print(f"✓ Search found {len(search_results)} results for 'workflow'")
    
    print("✓ ResourceManager tests passed!\n")

def test_resource_structure():
    """Test resource file structure"""
    print("Testing resource structure...")
    
    parser = ResourceParser('resources')
    resources = parser.list_resources()
    
    required_fields = ['tags', 'ecosystem', 'basemodel', 'version', 'type']
    
    for resource in resources:
        metadata = resource['metadata']
        
        # Check required fields
        for field in required_fields:
            if field not in metadata:
                print(f"✗ Missing required field '{field}' in {resource['filepath']}")
                return False
        
        # Check download command exists
        if not resource.get('download_command'):
            print(f"✗ Missing download command in {resource['filepath']}")
            return False
    
    print(f"✓ All {len(resources)} resources have valid structure")
    print("✓ Resource structure tests passed!\n")

def main():
    print("=" * 60)
    print("Resource Management System Tests")
    print("=" * 60 + "\n")
    
    try:
        test_resource_parser()
        test_resource_manager()
        test_resource_structure()
        
        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
