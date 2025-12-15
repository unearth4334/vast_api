#!/usr/bin/env python3
"""
Test Fixture for Widget Value Variations
Validates that changing input values correctly updates the workflow JSON
Uses sample files as ground truth for validation
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


class WidgetVariationTests:
    """Test widget value changes across different input configurations"""
    
    def __init__(self):
        self.workflow_id = "IMG_to_VIDEO_canvas"
        self.samples_dir = Path(__file__).parent / "samples"
        self.config = None
        self.template = None
        self.generator = None
        
    def setup(self):
        """Load workflow configuration and template"""
        print("=" * 80)
        print("Widget Value Variation Tests")
        print("=" * 80)
        
        self.config = WorkflowLoader.load_workflow(self.workflow_id)
        self.template = WorkflowLoader.load_workflow_json(self.workflow_id)
        self.generator = WorkflowGenerator(self.config, self.template)
        print(f"✓ Workflow loaded: {self.config.name}\n")
    
    def get_baseline_inputs(self) -> Dict[str, Any]:
        """Get baseline test inputs matching the Original sample"""
        return {
            # Basic Settings
            "input_image": "test_image.png",
            "positive_prompt": "A beautiful cinematic scene",
            "negative_prompt": "blurry, low quality",
            "seed": 42,
            
            # Generation Parameters (matching Original sample defaults)
            "size_x": 896,
            "size_y": 1120,
            "duration": 5.0,
            "steps": 20,
            "cfg": 3.5,
            "frame_rate": 16.0,
            "speed": 7.0,
            "upscale_ratio": 2.0,
            
            # Model Selection
            "main_model": {
                "highNoisePath": "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_high_noise_14B_fp16.safetensors",
                "lowNoisePath": "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_low_noise_14B_fp16.safetensors"
            },
            "clip_model": {"path": "Wan-2.2/umt5_xxl_fp16.safetensors"},
            "vae_model": {"path": "Wan-2.1/wan_2.1_vae.safetensors"},
            "upscale_model": {"path": "RealESRGAN_x4plus.pth"},
            
            # Advanced Features (all enabled/default)
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
    
    def test_cfg_variation(self):
        """Test CFG value change from 3.5 to 5.0"""
        print("Test 1: CFG Value Change (3.5 → 5.0)")
        print("-" * 80)
        
        # Generate workflow with CFG = 5.0
        inputs = self.get_baseline_inputs()
        inputs["cfg"] = 5.0
        
        workflow = self.generator.generate(inputs)
        nodes_by_id = {node['id']: node for node in workflow['nodes']}
        
        # Verify Node 85 (CFG slider) has [5.0, 5.0, 1]
        node_85 = nodes_by_id[85]
        expected = [5.0, 5.0, 1]
        actual = node_85['widgets_values']
        
        if actual == expected:
            print(f"✓ Node 85 (CFG slider): {actual}")
            return True
        else:
            print(f"✗ Node 85 (CFG slider): {actual} (expected {expected})")
            return False
    
    def test_steps_variation(self):
        """Test Steps value change from 20 to 30"""
        print("\nTest 2: Steps Value Change (20 → 30)")
        print("-" * 80)
        
        inputs = self.get_baseline_inputs()
        inputs["steps"] = 30
        
        workflow = self.generator.generate(inputs)
        nodes_by_id = {node['id']: node for node in workflow['nodes']}
        
        # Verify Node 82 (Steps slider) has [30, 30, 0]
        node_82 = nodes_by_id[82]
        expected = [30.0, 30.0, 0]
        actual = node_82['widgets_values']
        
        if actual == expected:
            print(f"✓ Node 82 (Steps slider): {actual}")
            return True
        else:
            print(f"✗ Node 82 (Steps slider): {actual} (expected {expected})")
            return False
    
    def test_duration_variation(self):
        """Test Duration value change from 5 to 8"""
        print("\nTest 3: Duration Value Change (5 → 8)")
        print("-" * 80)
        
        inputs = self.get_baseline_inputs()
        inputs["duration"] = 8.0
        
        workflow = self.generator.generate(inputs)
        nodes_by_id = {node['id']: node for node in workflow['nodes']}
        
        # Verify Node 426 (Duration slider) has [8, 8, 1]
        node_426 = nodes_by_id[426]
        expected = [8.0, 8.0, 1]
        actual = node_426['widgets_values']
        
        if actual == expected:
            print(f"✓ Node 426 (Duration slider): {actual}")
            return True
        else:
            print(f"✗ Node 426 (Duration slider): {actual} (expected {expected})")
            return False
    
    def test_frame_rate_variation(self):
        """Test Frame Rate value change from 16 to 20"""
        print("\nTest 4: Frame Rate Value Change (16 → 20)")
        print("-" * 80)
        
        inputs = self.get_baseline_inputs()
        inputs["frame_rate"] = 20.0
        
        workflow = self.generator.generate(inputs)
        nodes_by_id = {node['id']: node for node in workflow['nodes']}
        
        # Verify Node 490 (Frame rate slider) has [20, 20, 1]
        node_490 = nodes_by_id[490]
        expected = [20.0, 20.0, 1]
        actual = node_490['widgets_values']
        
        if actual == expected:
            print(f"✓ Node 490 (Frame rate slider): {actual}")
            return True
        else:
            print(f"✗ Node 490 (Frame rate slider): {actual} (expected {expected})")
            return False
    
    def test_speed_variation(self):
        """Test Speed value change from 7 to 10"""
        print("\nTest 5: Speed Value Change (7 → 10)")
        print("-" * 80)
        
        inputs = self.get_baseline_inputs()
        inputs["speed"] = 10.0
        
        workflow = self.generator.generate(inputs)
        nodes_by_id = {node['id']: node for node in workflow['nodes']}
        
        # Verify Node 157 (Speed slider) has [10, 10, 1]
        node_157 = nodes_by_id[157]
        expected = [10.0, 10.0, 1]
        actual = node_157['widgets_values']
        
        if actual == expected:
            print(f"✓ Node 157 (Speed slider): {actual}")
            return True
        else:
            print(f"✗ Node 157 (Speed slider): {actual} (expected {expected})")
            return False
    
    def test_upscale_ratio_variation(self):
        """Test Upscale Ratio value change from 2.0 to 1.5"""
        print("\nTest 6: Upscale Ratio Value Change (2.0 → 1.5)")
        print("-" * 80)
        
        inputs = self.get_baseline_inputs()
        inputs["upscale_ratio"] = 1.5
        
        workflow = self.generator.generate(inputs)
        nodes_by_id = {node['id']: node for node in workflow['nodes']}
        
        # Verify Node 421 (Upscale ratio slider) has [?, 1.5, 1]
        # Based on sample analysis, index 1 contains the upscale_ratio value
        node_421 = nodes_by_id[421]
        actual = node_421['widgets_values']
        
        # Check if index 1 has 1.5
        if len(actual) > 1 and actual[1] == 1.5:
            print(f"✓ Node 421 (Upscale ratio slider): {actual}")
            return True
        else:
            print(f"✗ Node 421 (Upscale ratio slider): {actual} (expected [?, 1.5, 1])")
            return False
    
    def test_multiple_changes(self):
        """Test multiple simultaneous value changes"""
        print("\nTest 7: Multiple Value Changes (CFG=7.0, Steps=25, Duration=6.0)")
        print("-" * 80)
        
        inputs = self.get_baseline_inputs()
        inputs["cfg"] = 7.0
        inputs["steps"] = 25
        inputs["duration"] = 6.0
        
        workflow = self.generator.generate(inputs)
        nodes_by_id = {node['id']: node for node in workflow['nodes']}
        
        # Verify all three changes
        checks = [
            (85, [7.0, 7.0, 1], "CFG slider"),
            (82, [25.0, 25.0, 0], "Steps slider"),
            (426, [6.0, 6.0, 1], "Duration slider"),
        ]
        
        all_ok = True
        for node_id, expected, desc in checks:
            actual = nodes_by_id[node_id]['widgets_values']
            if actual == expected:
                print(f"✓ Node {node_id} ({desc}): {actual}")
            else:
                print(f"✗ Node {node_id} ({desc}): {actual} (expected {expected})")
                all_ok = False
        
        return all_ok
    
    def run_all_tests(self):
        """Run all variation tests"""
        self.setup()
        
        tests = [
            self.test_cfg_variation,
            self.test_steps_variation,
            self.test_duration_variation,
            self.test_frame_rate_variation,
            self.test_speed_variation,
            self.test_upscale_ratio_variation,
            self.test_multiple_changes,
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
        
        for i, result in enumerate(results, 1):
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: Test {i}")
        
        print(f"\nResults: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All widget variation tests passed!")
        else:
            print(f"⚠️  {total - passed} test(s) failed")
        
        return all(results)


if __name__ == "__main__":
    tester = WidgetVariationTests()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
