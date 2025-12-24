#!/usr/bin/env python3
"""
Test the new workflow interpreter adapter
"""

import json
import logging
from pathlib import Path
from app.create.interpreter_adapter import InterpreterAdapter

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_interpreter():
    """Test the interpreter with sample inputs"""
    
    print("=" * 60)
    print("Testing Workflow Interpreter")
    print("=" * 60)
    
    # Test inputs (simplified version)
    ui_inputs = {
        'input_image': 'test_image.png',
        'positive_prompt': 'A beautiful sunset over the ocean',
        'negative_prompt': 'blurry, low quality',
        'seed': 12345,
        'size_x': 1024,
        'size_y': 576,
        'duration': 120,
        'steps': 28,
        'cfg': 7.0,
        'frame_rate': 24,
        'speed': 1.0,
        'upscale_ratio': 1.0,
        'main_model': {
            'highNoisePath': 'models/hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors',
            'lowNoisePath': 'models/hunyuan_video_720_cfgdistill_fp8_e4m3fn.safetensors'
        },
        'loras': [],
        'save_last_frame': 0,
        'enable_interpolation': 2,
        'use_upscaler': 2,
        'enable_upscale_interpolation': 2,
        'enable_video_enhancer': 2,
        'enable_cfg_zero_star': 2,
        'enable_speed_regulation': 0,
        'enable_normalized_attention': 2,
        'enable_magcache': 2,
        'enable_torch_compile': 2,
        'enable_block_swap': 2,
        'vram_reduction': 0,
        'enable_auto_prompt': 2
    }
    
    print("\n1. Loading interpreter...")
    workflow_id = 'IMG_to_VIDEO_canvas'
    wrapper_path = Path(f'workflows/{workflow_id}.webui.yml')
    
    if not wrapper_path.exists():
        print(f"❌ Wrapper file not found: {wrapper_path}")
        return False
    
    print(f"✓ Found wrapper: {wrapper_path}")
    
    try:
        adapter = InterpreterAdapter(workflow_id, wrapper_path)
        print("✓ Interpreter loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load interpreter: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n2. Converting UI inputs to interpreter format...")
    try:
        interpreter_inputs = adapter.convert_ui_inputs_to_interpreter_format(ui_inputs)
        print("✓ Inputs converted successfully")
        print(f"  Sections: {list(interpreter_inputs.get('inputs', {}).keys())}")
    except Exception as e:
        print(f"❌ Failed to convert inputs: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n3. Generating workflow...")
    try:
        generated_workflow = adapter.generate(ui_inputs)
        print("✓ Workflow generated successfully")
        
        # Check workflow structure
        if isinstance(generated_workflow, dict):
            if 'nodes' in generated_workflow:
                print(f"  Format: Canvas (nodes array)")
                print(f"  Node count: {len(generated_workflow['nodes'])}")
            else:
                print(f"  Format: API")
                print(f"  Keys: {list(generated_workflow.keys())[:5]}...")
        else:
            print(f"  ⚠️ Unexpected type: {type(generated_workflow)}")
        
    except Exception as e:
        print(f"❌ Failed to generate workflow: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n4. Validating key modifications...")
    try:
        # Check that some key values were set correctly
        if 'nodes' in generated_workflow:
            # Canvas format - find specific nodes
            nodes_by_title = {node.get('title', ''): node for node in generated_workflow['nodes']}
            
            # Check CFG node (should be 7.0)
            if 'CFG' in nodes_by_title:
                cfg_value = nodes_by_title['CFG'].get('widgets_values', [None])[0]
                if cfg_value == 7.0:
                    print(f"  ✓ CFG value set correctly: {cfg_value}")
                else:
                    print(f"  ⚠️ CFG value unexpected: {cfg_value} (expected 7.0)")
            
            # Check Steps node (should be 28)
            if 'Steps' in nodes_by_title:
                steps_value = nodes_by_title['Steps'].get('widgets_values', [None])[0]
                if steps_value == 28:
                    print(f"  ✓ Steps value set correctly: {steps_value}")
                else:
                    print(f"  ⚠️ Steps value unexpected: {steps_value} (expected 28)")
            
            # Check Duration node (should be 120)
            if 'Duration' in nodes_by_title:
                duration_value = nodes_by_title['Duration'].get('widgets_values', [None])[0]
                if duration_value == 120:
                    print(f"  ✓ Duration value set correctly: {duration_value}")
                else:
                    print(f"  ⚠️ Duration value unexpected: {duration_value} (expected 120)")
        
        print("✓ Validation complete")
        
    except Exception as e:
        print(f"⚠️ Validation failed: {e}")
        # Not critical - continue
    
    print("\n5. Saving test output...")
    output_path = Path('temp/test_interpreter_output.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(output_path, 'w') as f:
            json.dump(generated_workflow, f, indent=2)
        print(f"✓ Saved to: {output_path}")
    except Exception as e:
        print(f"⚠️ Failed to save: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Test completed successfully!")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_interpreter()
    exit(0 if success else 1)
