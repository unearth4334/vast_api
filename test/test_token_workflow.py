#!/usr/bin/env python3
"""
Test script for token-based workflow generation
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.create.workflow_loader import WorkflowLoader
from app.create.workflow_generator import WorkflowGenerator

def test_token_workflow():
    """Test the token-based workflow system"""
    
    print("=" * 60)
    print("Testing Token-Based Workflow System")
    print("=" * 60)
    
    # Load the workflow configuration
    print("\n1. Loading workflow configuration...")
    workflow_id = "IMG_to_VIDEO_canvas"
    
    try:
        config = WorkflowLoader.load_workflow(workflow_id)
        print(f"   ✓ Loaded: {config.name} v{config.version}")
        print(f"   ✓ Workflow file: {config.workflow_file}")
        print(f"   ✓ Number of inputs: {len(config.inputs)}")
        
        # Check for token-based inputs
        token_inputs = [inp for inp in config.inputs if inp.token or inp.tokens]
        node_inputs = [inp for inp in config.inputs if inp.node_id or inp.node_ids]
        print(f"   ✓ Token-based inputs: {len(token_inputs)}")
        print(f"   ✓ Node-based inputs (legacy): {len(node_inputs)}")
        
    except Exception as e:
        print(f"   ✗ Error loading config: {e}")
        return False
    
    # Load the workflow template
    print("\n2. Loading workflow template...")
    try:
        template = WorkflowLoader.load_workflow_json(workflow_id)
        print(f"   ✓ Template loaded successfully")
        
        # Check if it's canvas format
        if 'nodes' in template:
            print(f"   ✓ Canvas format detected ({len(template['nodes'])} nodes)")
        else:
            print(f"   ✓ API format detected ({len(template)} nodes)")
        
        # Check for tokens in template
        template_str = json.dumps(template)
        token_count = template_str.count('{{')
        print(f"   ✓ Found {token_count} tokens in template")
        
    except Exception as e:
        print(f"   ✗ Error loading template: {e}")
        return False
    
    # Create generator
    print("\n3. Creating workflow generator...")
    try:
        generator = WorkflowGenerator(config, template)
        print(f"   ✓ Generator created")
    except Exception as e:
        print(f"   ✗ Error creating generator: {e}")
        return False
    
    # Test generation with sample inputs
    print("\n4. Testing workflow generation with sample inputs...")
    test_inputs = {
        "input_image": "test_image.png",
        "positive_prompt": "A beautiful cinematic scene with smooth motion",
        "negative_prompt": "static, blurry, low quality",
        "seed": 12345,
        "duration": 5.0,
        "steps": 20,
        "cfg": 3.5,
        "frame_rate": 16.0,
        "speed": 7.0,
        "upscale_ratio": 2.0,
        "size_x": 896,
        "size_y": 1120,
        "main_model": {
            "highNoisePath": "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_high_noise_14B_fp16.safetensors",
            "lowNoisePath": "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_low_noise_14B_fp16.safetensors"
        },
        "clip_model": {
            "path": "Wan-2.2/umt5_xxl_fp16.safetensors"
        },
        "vae_model": {
            "path": "Wan-2.1/wan_2.1_vae.safetensors"
        },
        "upscale_model": {
            "path": "RealESRGAN_x4plus.pth"
        }
    }
    
    try:
        generated_workflow = generator.generate(test_inputs)
        print(f"   ✓ Workflow generated successfully")
        
        # Verify replacements
        generated_str = json.dumps(generated_workflow)
        remaining_tokens = generated_str.count('{{')
        
        if remaining_tokens > 0:
            print(f"   ⚠ Warning: {remaining_tokens} tokens were not replaced")
            # Find which tokens weren't replaced
            import re
            unreplaced = re.findall(r'\{\{[A-Z_]+\}\}', generated_str)
            if unreplaced:
                print(f"   Unreplaced tokens: {set(unreplaced)}")
        else:
            print(f"   ✓ All tokens replaced successfully")
        
        # Check specific values
        if 'nodes' in generated_workflow:
            # Canvas format - find specific nodes
            for node in generated_workflow['nodes']:
                if node.get('id') == 408:  # Positive prompt
                    value = node.get('widgets_values', [None])[0]
                    if value == test_inputs['positive_prompt']:
                        print(f"   ✓ Positive prompt replaced correctly")
                    else:
                        print(f"   ✗ Positive prompt mismatch: {value}")
                
                if node.get('id') == 73:  # Seed
                    value = node.get('widgets_values', [None])[0]
                    if value == test_inputs['seed']:
                        print(f"   ✓ Seed replaced correctly")
                    else:
                        print(f"   ✗ Seed mismatch: {value}")
                
                if node.get('id') == 522:  # High model
                    value = node.get('widgets_values', [None])[0]
                    if value == test_inputs['main_model']['highNoisePath']:
                        print(f"   ✓ High model path replaced correctly")
                    else:
                        print(f"   ✗ High model mismatch: {value}")
        
        # Save generated workflow for inspection
        output_path = Path(__file__).parent / "test_generated_workflow.json"
        with open(output_path, 'w') as f:
            json.dump(generated_workflow, f, indent=2)
        print(f"\n   📄 Generated workflow saved to: {output_path}")
        
    except Exception as e:
        print(f"   ✗ Error generating workflow: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_token_workflow()
    sys.exit(0 if success else 1)
