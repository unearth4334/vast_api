#!/usr/bin/env python3
"""
Test Fixture for Text and Special Input Validation
Validates that text inputs, model changes, VRAM settings, and LoRA system correctly update workflow JSON
Uses new sample files: ChangedInputImage, ChangedPositivePrompt, ChangedSeed, LoRA samples, etc.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.create.workflow_loader import WorkflowLoader
from app.create.workflow_generator import WorkflowGenerator


class TextAndSpecialInputTests:
    """Test text inputs, model selection, VRAM, and LoRA system"""
    
    def __init__(self):
        self.workflow_id = "IMG_to_VIDEO_canvas"
        self.samples_dir = Path(__file__).parent / "samples"
        self.config = None
        self.template = None
        self.generator = None
        
    def setup(self):
        """Load workflow configuration and template"""
        print("=" * 80)
        print("Text and Special Input Validation Tests")
        print("=" * 80)
        
        self.config = WorkflowLoader.load_workflow(self.workflow_id)
        self.template = WorkflowLoader.load_workflow_json(self.workflow_id)
        self.generator = WorkflowGenerator(self.config, self.template)
        print(f"✓ Workflow loaded: {self.config.name}\n")
    
    def get_baseline_inputs(self) -> Dict[str, Any]:
        """Get baseline test inputs"""
        return {
            "input_image": "test_image.png",
            "positive_prompt": "A beautiful cinematic scene",
            "negative_prompt": "blurry, low quality",
            "seed": 42,
            "size_x": 896,
            "size_y": 1120,
            "duration": 5.0,
            "steps": 20,
            "cfg": 3.5,
            "frame_rate": 16.0,
            "speed": 7.0,
            "upscale_ratio": 2.0,
            "main_model": {
                "highNoisePath": "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_high_noise_14B_fp16.safetensors",
                "lowNoisePath": "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_low_noise_14B_fp16.safetensors"
            },
            "clip_model": {"path": "Wan-2.2/umt5_xxl_fp16.safetensors"},
            "vae_model": {"path": "Wan-2.1/wan_2.1_vae.safetensors"},
            "upscale_model": {"path": "RealESRGAN_x4plus.pth"},
            "save_last_frame": 2,
            "enable_interpolation": 0,
            "use_upscaler": 2,
            "enable_upscale_interpolation": 2,
            "enable_video_enhancer": 0,
            "enable_cfg_zero_star": 0,
            "enable_speed_regulation": 0,
            "enable_normalized_attention": 0,
            "enable_magcache": 0,
            "enable_torch_compile": 4,
            "enable_block_swap": 0,
            "vram_reduction": 100,
            "enable_auto_prompt": 0,
        }
    
    def test_positive_prompt_change(self):
        """Test positive prompt text change"""
        print("Test 1: Positive Prompt Change")
        print("-" * 80)
        
        inputs = self.get_baseline_inputs()
        new_prompt = "The young woman turns towards the camera, she has a cute smile"
        inputs["positive_prompt"] = new_prompt
        
        workflow = self.generator.generate(inputs)
        nodes_by_id = {node['id']: node for node in workflow['nodes']}
        
        node_408 = nodes_by_id[408]
        actual = node_408['widgets_values'][0]
        
        if new_prompt in actual:
            print(f"✓ Node 408 (Positive prompt): Contains expected text")
            print(f"  Value: {actual[:80]}...")
            return True
        else:
            print(f"✗ Node 408: Expected '{new_prompt}' in prompt")
            print(f"  Actual: {actual[:80]}...")
            return False
    
    def test_negative_prompt_change(self):
        """Test negative prompt text change"""
        print("\nTest 2: Negative Prompt Change")
        print("-" * 80)
        
        inputs = self.get_baseline_inputs()
        new_neg_prompt = "static, no motion, frozen frame"
        inputs["negative_prompt"] = new_neg_prompt
        
        workflow = self.generator.generate(inputs)
        nodes_by_id = {node['id']: node for node in workflow['nodes']}
        
        node_409 = nodes_by_id[409]
        actual = node_409['widgets_values'][0]
        
        if new_neg_prompt in actual:
            print(f"✓ Node 409 (Negative prompt): Contains expected text")
            print(f"  Value: {actual[:80]}...")
            return True
        else:
            print(f"✗ Node 409: Expected '{new_neg_prompt}' in prompt")
            return False
    
    def test_input_image_change(self):
        """Test input image file path change"""
        print("\nTest 3: Input Image Change")
        print("-" * 80)
        
        inputs = self.get_baseline_inputs()
        new_image = "upload_12345.jpeg"
        inputs["input_image"] = new_image
        
        workflow = self.generator.generate(inputs)
        nodes_by_id = {node['id']: node for node in workflow['nodes']}
        
        node_88 = nodes_by_id[88]
        actual = node_88['widgets_values'][0]
        
        if actual == new_image:
            print(f"✓ Node 88 (Input image): {actual}")
            return True
        else:
            print(f"✗ Node 88: {actual} (expected {new_image})")
            return False
    
    def test_seed_change(self):
        """Test seed value change"""
        print("\nTest 4: Seed Change")
        print("-" * 80)
        
        inputs = self.get_baseline_inputs()
        new_seed = 701601234567340
        inputs["seed"] = new_seed
        
        workflow = self.generator.generate(inputs)
        nodes_by_id = {node['id']: node for node in workflow['nodes']}
        
        node_73 = nodes_by_id[73]
        actual = node_73['widgets_values'][0]
        
        if actual == new_seed:
            print(f"✓ Node 73 (Seed): {actual}")
            return True
        else:
            print(f"✗ Node 73: {actual} (expected {new_seed})")
            return False
    
    def test_vram_reduction_change(self):
        """Test VRAM reduction percentage change"""
        print("\nTest 5: VRAM Reduction Change (100 → 71)")
        print("-" * 80)
        
        inputs = self.get_baseline_inputs()
        inputs["vram_reduction"] = 71
        
        workflow = self.generator.generate(inputs)
        nodes_by_id = {node['id']: node for node in workflow['nodes']}
        
        node_502 = nodes_by_id[502]
        expected = [71.0, 71.0, 0]
        actual = node_502['widgets_values']
        
        if actual == expected:
            print(f"✓ Node 502 (VRAM reduction): {actual}")
            return True
        else:
            print(f"✗ Node 502: {actual} (expected {expected})")
            return False
    
    def test_model_change(self):
        """Test main model path change"""
        print("\nTest 6: Main Model Change")
        print("-" * 80)
        
        inputs = self.get_baseline_inputs()
        inputs["main_model"] = {
            "highNoisePath": "Smooth Mix Wan 2.2 (I2V&T2V 14B)/smoothMixWan22I2VT2V_i2vHigh.safetensors",
            "lowNoisePath": "Smooth Mix Wan 2.2 (I2V&T2V 14B)/smoothMixWan22I2VT2V_i2vLow.safetensors"
        }
        
        workflow = self.generator.generate(inputs)
        nodes_by_id = {node['id']: node for node in workflow['nodes']}
        
        # Check high noise model (node 522)
        node_522 = nodes_by_id[522]
        high_path = node_522['widgets_values'][0]
        
        # Check low noise model (node 523)
        node_523 = nodes_by_id[523]
        low_path = node_523['widgets_values'][0]
        
        high_ok = "smoothMixWan22I2VT2V_i2vHigh" in high_path
        low_ok = "smoothMixWan22I2VT2V_i2vLow" in low_path
        
        if high_ok and low_ok:
            print(f"✓ Node 522 (High model): ...{high_path[-60:]}")
            print(f"✓ Node 523 (Low model): ...{low_path[-60:]}")
            return True
        else:
            if not high_ok:
                print(f"✗ Node 522: Model path not updated")
            if not low_ok:
                print(f"✗ Node 523: Model path not updated")
            return False
    
    def test_lora_system(self):
        """Test LoRA system with Power Lora Loader nodes"""
        print("\nTest 7: LoRA System Validation")
        print("-" * 80)
        
        # This test just validates that LoRA nodes exist and have correct structure
        # Real LoRA testing would require understanding the complex loras input format
        
        inputs = self.get_baseline_inputs()
        workflow = self.generator.generate(inputs)
        nodes_by_id = {node['id']: node for node in workflow['nodes']}
        
        # Check LoRA loader nodes exist
        lora_nodes = [416, 471]
        all_ok = True
        
        for node_id in lora_nodes:
            if node_id not in nodes_by_id:
                print(f"✗ LoRA Node {node_id} not found")
                all_ok = False
                continue
            
            node = nodes_by_id[node_id]
            if node['type'] != "Power Lora Loader (rgthree)":
                print(f"✗ Node {node_id}: Wrong type {node['type']}")
                all_ok = False
                continue
            
            widgets_values = node.get('widgets_values', [])
            if len(widgets_values) < 3:
                print(f"✗ Node {node_id}: Missing widget values")
                all_ok = False
                continue
            
            # widgets_values[2] should be a dict with LoRA data
            lora_data = widgets_values[2]
            if isinstance(lora_data, dict):
                print(f"✓ Node {node_id}: LoRA loader structure valid")
                # Can be empty {} or have {on, lora, strength, strengthTwo}
            else:
                print(f"✗ Node {node_id}: Invalid LoRA data structure")
                all_ok = False
        
        return all_ok
    
    def run_all_tests(self):
        """Run all text and special input tests"""
        self.setup()
        
        tests = [
            self.test_positive_prompt_change,
            self.test_negative_prompt_change,
            self.test_input_image_change,
            self.test_seed_change,
            self.test_vram_reduction_change,
            self.test_model_change,
            self.test_lora_system,
        ]
        
        results = []
        for test in tests:
            try:
                passed = test()
                results.append(passed)
            except Exception as e:
                print(f"✗ Test failed with error: {e}")
                import traceback
                traceback.print_exc()
                results.append(False)
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        passed = sum(results)
        total = len(results)
        
        test_names = [
            "Positive Prompt Change",
            "Negative Prompt Change",
            "Input Image Change",
            "Seed Change",
            "VRAM Reduction Change",
            "Model Change",
            "LoRA System Validation",
        ]
        
        for i, (name, result) in enumerate(zip(test_names, results), 1):
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: Test {i} - {name}")
        
        print(f"\nResults: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All text and special input tests passed!")
        else:
            print(f"⚠️  {total - passed} test(s) failed")
        
        return all(results)


if __name__ == "__main__":
    tester = TextAndSpecialInputTests()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
