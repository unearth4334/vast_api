#!/usr/bin/env python3
"""
Test script for node_mode_toggle input type
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.create.workflow_loader import WorkflowLoader
from app.create.workflow_generator import WorkflowGenerator

def test_node_mode_toggle():
    """Test the node_mode_toggle input type"""
    
    print("=" * 60)
    print("Testing node_mode_toggle Input Type")
    print("=" * 60)
    
    # Load the workflow configuration
    print("\n1. Loading workflow configuration...")
    workflow_id = "IMG_to_VIDEO_canvas"
    
    try:
        config = WorkflowLoader.load_workflow(workflow_id)
        print(f"   ✓ Loaded: {config.name} v{config.version}")
        
        # Find node_mode_toggle inputs
        toggle_inputs = [inp for inp in config.inputs if inp.type == 'node_mode_toggle']
        print(f"   ✓ Found {len(toggle_inputs)} node_mode_toggle inputs")
        
        for toggle in toggle_inputs:
            print(f"     - {toggle.id}: {toggle.label} (default: {toggle.default})")
            if toggle.node_ids:
                print(f"       node_ids: {toggle.node_ids}")
        
    except Exception as e:
        print(f"   ✗ Error loading config: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Load the workflow template
    print("\n2. Loading workflow template...")
    try:
        template = WorkflowLoader.load_workflow_json(workflow_id)
        print(f"   ✓ Template loaded successfully")
        print(f"   ✓ Format: {'Canvas' if 'nodes' in template else 'Legacy'}")
        
        if 'nodes' in template:
            print(f"   ✓ Number of nodes: {len(template['nodes'])}")
    except Exception as e:
        print(f"   ✗ Error loading template: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test workflow generation with node_mode_toggle values
    print("\n3. Testing workflow generation...")
    try:
        generator = WorkflowGenerator(config, template)
        
        # Get the first toggle input and its node IDs for testing
        first_toggle = toggle_inputs[0]
        test_field_id = first_toggle.id
        test_node_ids = [int(nid) for nid in first_toggle.node_ids]
        test_default = first_toggle.default
        
        print(f"\n   Testing with field: {test_field_id}")
        print(f"   Node IDs: {test_node_ids}")
        print(f"   Default mode: {test_default}")
        
        # Test case 1: Enable a toggle (mode = 0)
        print(f"\n   Test 1: Enable '{test_field_id}' (mode = 0)")
        test_inputs_1 = {
            test_field_id: 0,  # enabled
            'input_image': 'test.png',
            'positive_prompt': 'test prompt',
            'seed': 12345
        }
        
        workflow_1 = generator.generate(test_inputs_1)
        
        # Check if the mode was applied correctly
        if 'nodes' in workflow_1:
            test_nodes = [next((n for n in workflow_1['nodes'] if n.get('id') == nid), None) 
                          for nid in test_node_ids]
            
            if all(test_nodes):
                modes = [n.get('mode') for n in test_nodes]
                for i, (node_id, mode) in enumerate(zip(test_node_ids, modes)):
                    print(f"     Node {node_id} mode: {mode} (expected: 0)")
                
                if all(m == 0 for m in modes):
                    print("     ✓ Mode correctly set to 0 (enabled)")
                else:
                    print(f"     ✗ Mode not correct! Expected all 0, got {modes}")
                    return False
            else:
                print(f"     ✗ Some nodes not found in workflow: {test_node_ids}")
                return False
        
        # Test case 2: Disable a toggle (mode = 2)
        print(f"\n   Test 2: Disable '{test_field_id}' (mode = 2)")
        test_inputs_2 = {
            test_field_id: 2,  # disabled/bypass
            'input_image': 'test.png',
            'positive_prompt': 'test prompt',
            'seed': 12345
        }
        
        workflow_2 = generator.generate(test_inputs_2)
        
        # Check if the mode was applied correctly
        if 'nodes' in workflow_2:
            test_nodes = [next((n for n in workflow_2['nodes'] if n.get('id') == nid), None) 
                          for nid in test_node_ids]
            
            if all(test_nodes):
                modes = [n.get('mode') for n in test_nodes]
                for i, (node_id, mode) in enumerate(zip(test_node_ids, modes)):
                    print(f"     Node {node_id} mode: {mode} (expected: 2)")
                
                if all(m == 2 for m in modes):
                    print("     ✓ Mode correctly set to 2 (disabled)")
                else:
                    print(f"     ✗ Mode not correct! Expected all 2, got {modes}")
                    return False
            else:
                print(f"     ✗ Some nodes not found in workflow: {test_node_ids}")
                return False
        
        # Test case 3: Use default value
        print(f"\n   Test 3: Use default value from config")
        test_inputs_3 = {
            # Field not provided, should use default
            'input_image': 'test.png',
            'positive_prompt': 'test prompt',
            'seed': 12345
        }
        
        workflow_3 = generator.generate(test_inputs_3)
        
        # Check if the mode was applied correctly
        if 'nodes' in workflow_3:
            test_nodes = [next((n for n in workflow_3['nodes'] if n.get('id') == nid), None) 
                          for nid in test_node_ids]
            
            if all(test_nodes):
                modes = [n.get('mode') for n in test_nodes]
                for i, (node_id, mode) in enumerate(zip(test_node_ids, modes)):
                    print(f"     Node {node_id} mode: {mode} (expected: {test_default} from default)")
                
                if all(m == test_default for m in modes):
                    print("     ✓ Default mode correctly applied")
                else:
                    print(f"     ✗ Default mode not correct! Expected all {test_default}, got {modes}")
                    return False
            else:
                print(f"     ✗ Some nodes not found in workflow: {test_node_ids}")
                return False
        
        print("\n   ✓ All tests passed!")
        
    except Exception as e:
        print(f"   ✗ Error generating workflow: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✓ All tests completed successfully!")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_node_mode_toggle()
    sys.exit(0 if success else 1)
