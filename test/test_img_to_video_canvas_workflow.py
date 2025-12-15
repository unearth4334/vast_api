#!/usr/bin/env python3
"""
Comprehensive Test Fixture for IMG_to_VIDEO_canvas workflow generation
Tests token replacement and node mode toggles for the canvas workflow editor
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.create.workflow_loader import WorkflowLoader
from app.create.workflow_generator import WorkflowGenerator


class WorkflowTestFixture:
    """Comprehensive test fixture for IMG_to_VIDEO_canvas workflow"""
    
    def __init__(self):
        self.workflow_id = "IMG_to_VIDEO_canvas"
        self.config = None
        self.template = None
        self.generator = None
        self.test_results = []
        
    def load_workflow(self) -> bool:
        """Load workflow configuration and template"""
        print("=" * 80)
        print("IMG_to_VIDEO_canvas Workflow Test Fixture")
        print("=" * 80)
        
        # Load config
        print("\n1. Loading workflow configuration...")
        try:
            self.config = WorkflowLoader.load_workflow(self.workflow_id)
            print(f"   ✓ Config loaded: {self.config.name}")
            print(f"   ✓ Inputs: {len(self.config.inputs)}")
            print(f"   ✓ Workflow file: {self.config.workflow_file}")
        except Exception as e:
            print(f"   ✗ Error loading config: {e}")
            return False
        
        # Load template
        print("\n2. Loading workflow template...")
        try:
            self.template = WorkflowLoader.load_workflow_json(self.workflow_id)
            template_str = json.dumps(self.template)
            token_count = template_str.count('{{')
            
            print(f"   ✓ Template loaded")
            if 'nodes' in self.template:
                print(f"   ✓ Format: Canvas ({len(self.template['nodes'])} nodes)")
            else:
                print(f"   ✓ Format: API ({len(self.template)} top-level nodes)")
            print(f"   ✓ Tokens found: {token_count}")
            
        except Exception as e:
            print(f"   ✗ Error loading template: {e}")
            return False
        
        # Create generator
        print("\n3. Creating workflow generator...")
        try:
            self.generator = WorkflowGenerator(self.config, self.template)
            print(f"   ✓ Generator initialized")
        except Exception as e:
            print(f"   ✗ Error creating generator: {e}")
            return False
        
        return True
    
    def get_test_inputs(self) -> Dict[str, Any]:
        """Get comprehensive test inputs covering all fields"""
        return {
            # Basic Settings
            "input_image": "test_image.png",
            "positive_prompt": "A beautiful cinematic scene with smooth camera movement",
            "negative_prompt": "blurry, low quality, artifacts",
            "seed": 42,
            
            # Generation Parameters
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
            "clip_model": {
                "path": "Wan-2.2/umt5_xxl_fp16.safetensors"
            },
            "vae_model": {
                "path": "Wan-2.1/wan_2.1_vae.safetensors"
            },
            "upscale_model": {
                "path": "RealESRGAN_x4plus.pth"
            },
            
            # Advanced Features (node mode toggles)
            "save_last_frame": 2,  # disabled
            "enable_interpolation": 0,  # enabled
            "use_upscaler": 2,  # disabled
            "enable_upscale_interpolation": 2,  # disabled
            "enable_video_enhancer": 0,  # enabled
            "enable_cfg_zero_star": 0,  # enabled
            "enable_speed_regulation": 0,  # enabled
            "enable_normalized_attention": 0,  # enabled
            "enable_magcache": 0,  # enabled
            "enable_torch_compile": 4,  # muted/disabled
            "enable_block_swap": 0,  # enabled
            "vram_reduction": 100,  # percentage
            "enable_auto_prompt": 0,  # enabled
        }
    
    def generate_workflow(self) -> Tuple[bool, Dict]:
        """Generate workflow from test inputs"""
        print("\n4. Generating workflow from test inputs...")
        
        test_inputs = self.get_test_inputs()
        
        try:
            generated = self.generator.generate(test_inputs)
            print(f"   ✓ Workflow generated successfully")
            
            # Basic structure check
            if 'nodes' in generated:
                print(f"   ✓ Canvas format preserved ({len(generated['nodes'])} nodes)")
            else:
                print(f"   ✓ API format ({len(generated)} nodes)")
            
            return True, generated
        except Exception as e:
            print(f"   ✗ Error generating workflow: {e}")
            import traceback
            traceback.print_exc()
            return False, {}
    
    def verify_token_replacements(self, workflow: Dict) -> bool:
        """Verify all tokens were replaced correctly"""
        print("\n5. Verifying token replacements...")
        
        workflow_str = json.dumps(workflow)
        test_inputs = self.get_test_inputs()
        
        # Check for unreplaced tokens
        remaining_tokens = re.findall(r'\{\{[A-Z_]+\}\}', workflow_str)
        if remaining_tokens:
            print(f"   ✗ Found {len(remaining_tokens)} unreplaced tokens:")
            for token in set(remaining_tokens):
                print(f"      - {token}")
            return False
        else:
            print(f"   ✓ All tokens replaced successfully")
        
        # Verify specific token replacements
        token_checks = [
            ("INPUT_IMAGE", test_inputs["input_image"], "input image"),
            ("POSITIVE_PROMPT", test_inputs["positive_prompt"], "positive prompt"),
            ("NEGATIVE_PROMPT", test_inputs["negative_prompt"], "negative prompt"),
            ("SEED", str(test_inputs["seed"]), "seed"),
            ("SIZE_WIDTH", str(test_inputs["size_x"]), "width"),
            ("SIZE_HEIGHT", str(test_inputs["size_y"]), "height"),
            ("DURATION", str(test_inputs["duration"]), "duration"),
            ("STEPS", str(test_inputs["steps"]), "steps"),
            ("CFG", str(test_inputs["cfg"]), "CFG scale"),
            ("FRAME_RATE", str(test_inputs["frame_rate"]), "frame rate"),
            ("SPEED", str(test_inputs["speed"]), "speed"),
            ("UPSCALE_RATIO", str(test_inputs["upscale_ratio"]), "upscale ratio"),
            ("VRAM_REDUCTION", str(test_inputs["vram_reduction"]), "VRAM reduction"),
            ("WAN_HIGH_MODEL", test_inputs["main_model"]["highNoisePath"], "high noise model"),
            ("WAN_LOW_MODEL", test_inputs["main_model"]["lowNoisePath"], "low noise model"),
            ("CLIP_MODEL", test_inputs["clip_model"]["path"], "CLIP model"),
            ("VAE_MODEL", test_inputs["vae_model"]["path"], "VAE model"),
            ("UPSCALE_MODEL", test_inputs["upscale_model"]["path"], "upscale model"),
        ]
        
        all_found = True
        for token, value, description in token_checks:
            # Check if value appears in workflow (allowing for JSON escaping)
            if value in workflow_str or json.dumps(value)[1:-1] in workflow_str:
                print(f"   ✓ {description} replaced correctly")
            else:
                print(f"   ✗ {description} not found in workflow")
                all_found = False
        
        return all_found
    
    def verify_node_modes(self, workflow: Dict) -> bool:
        """Verify node mode toggles were applied correctly"""
        print("\n6. Verifying node mode toggles...")
        
        if 'nodes' not in workflow:
            print("   ⚠ Not a canvas format workflow, skipping node mode checks")
            return True
        
        test_inputs = self.get_test_inputs()
        
        # Map of node IDs to expected modes based on test inputs
        node_mode_checks = [
            # save_last_frame: disabled (mode 2)
            (447, 2, "SaveImage - save_last_frame"),
            (444, 2, "ImageFromBatch - save_last_frame"),
            
            # enable_interpolation: enabled (mode 0)
            (431, 0, "RIFE VFI - enable_interpolation"),
            (433, 0, "VHS_VideoCombine - enable_interpolation"),
            
            # use_upscaler: disabled (mode 2)
            (385, 2, "ImageUpscaleWithModel - use_upscaler"),
            (418, 2, "ImageScaleBy - use_upscaler"),
            
            # enable_upscale_interpolation: disabled (mode 2)
            (442, 2, "RIFE VFI - enable_upscale_interpolation"),
            (443, 2, "VHS_VideoCombine - enable_upscale_interpolation"),
            
            # enable_video_enhancer: enabled (mode 0)
            (481, 0, "WanVideoEnhanceAVideoKJ - enable_video_enhancer (high)"),
            (482, 0, "WanVideoEnhanceAVideoKJ - enable_video_enhancer (low)"),
            
            # enable_cfg_zero_star: enabled (mode 0)
            (483, 0, "CFGZeroStarAndInit - enable_cfg_zero_star (high)"),
            (484, 0, "CFGZeroStarAndInit - enable_cfg_zero_star (low)"),
            
            # enable_speed_regulation: enabled (mode 0)
            (467, 0, "ModelSamplingSD3 - enable_speed_regulation (high)"),
            (468, 0, "ModelSamplingSD3 - enable_speed_regulation (low)"),
            
            # enable_normalized_attention: enabled (mode 0)
            (485, 0, "WanVideoNAG - enable_normalized_attention (high)"),
            (486, 0, "WanVideoNAG - enable_normalized_attention (low)"),
            
            # enable_magcache: enabled (mode 0)
            (506, 0, "MagCache - enable_magcache"),
            
            # enable_torch_compile: muted (mode 4)
            (492, 4, "TorchCompileModelWanVideo - enable_torch_compile (high)"),
            (494, 4, "TorchCompileModelWanVideo - enable_torch_compile (low)"),
            
            # enable_block_swap: enabled (mode 0)
            (500, 0, "wanBlockSwap - enable_block_swap (high)"),
            
            # enable_auto_prompt: enabled (mode 0)
            (473, 0, "DownloadAndLoadFlorence2Model - enable_auto_prompt"),
            (480, 0, "Florence2Run - enable_auto_prompt"),
            (474, 0, "Text Find and Replace (photo) - enable_auto_prompt"),
            (475, 0, "Text Find and Replace (image) - enable_auto_prompt"),
            (476, 0, "Text Find and Replace (painting) - enable_auto_prompt"),
            (472, 0, "Text Find and Replace (illustration) - enable_auto_prompt"),
            (501, 0, "wanBlockSwap - enable_block_swap (low)"),
        ]
        
        nodes_by_id = {node['id']: node for node in workflow['nodes']}
        all_correct = True
        
        for node_id, expected_mode, description in node_mode_checks:
            if node_id not in nodes_by_id:
                print(f"   ✗ Node {node_id} not found: {description}")
                all_correct = False
                continue
            
            actual_mode = nodes_by_id[node_id].get('mode')
            if actual_mode == expected_mode:
                print(f"   ✓ Node {node_id}: mode={actual_mode} - {description}")
            else:
                print(f"   ✗ Node {node_id}: mode={actual_mode} (expected {expected_mode}) - {description}")
                all_correct = False
        
        return all_correct
    
    def verify_model_paths(self, workflow: Dict) -> bool:
        """Verify model paths were inserted correctly in the right nodes"""
        print("\n7. Verifying model paths in specific nodes...")
        
        if 'nodes' not in workflow:
            print("   ⚠ Not a canvas format workflow, skipping model path checks")
            return True
        
        test_inputs = self.get_test_inputs()
        nodes_by_id = {node['id']: node for node in workflow['nodes']}
        
        model_checks = [
            (522, "wan2.2_i2v_high_noise_14B_fp16.safetensors", "High noise model"),
            (523, "wan2.2_i2v_low_noise_14B_fp16.safetensors", "Low noise model"),
            (460, "umt5_xxl_fp16.safetensors", "CLIP model"),
            (461, "wan_2.1_vae.safetensors", "VAE model"),
            (384, "RealESRGAN_x4plus.pth", "Upscale model"),
        ]
        
        all_correct = True
        for node_id, expected_substring, description in model_checks:
            if node_id not in nodes_by_id:
                print(f"   ✗ Node {node_id} not found: {description}")
                all_correct = False
                continue
            
            node = nodes_by_id[node_id]
            widgets_values = node.get('widgets_values', [])
            
            if not widgets_values:
                print(f"   ✗ Node {node_id}: No widgets_values - {description}")
                all_correct = False
                continue
            
            model_path = widgets_values[0]
            if expected_substring in model_path:
                print(f"   ✓ Node {node_id}: {model_path} - {description}")
            else:
                print(f"   ✗ Node {node_id}: {model_path} (expected {expected_substring}) - {description}")
                all_correct = False
        
        return all_correct
    
    def verify_widget_values(self, workflow: Dict) -> bool:
        """Verify widget values were set correctly"""
        print("\n8. Verifying widget values in nodes...")
        
        if 'nodes' not in workflow:
            print("   ⚠ Not a canvas format workflow, skipping widget value checks")
            return True
        
        test_inputs = self.get_test_inputs()
        nodes_by_id = {node['id']: node for node in workflow['nodes']}
        
        # Check specific widget values (simple single-index checks)
        widget_checks = [
            (408, 0, test_inputs["positive_prompt"], "Positive prompt"),
            (409, 0, test_inputs["negative_prompt"], "Negative prompt"),
            (88, 0, test_inputs["input_image"], "Input image"),
            (73, 0, test_inputs["seed"], "Seed"),
            (502, 0, test_inputs["vram_reduction"], "VRAM reduction"),
        ]
        
        print("\n   Text/Special Input Validation:")
        all_correct = True
        for node_id, widget_index, expected_value, description in widget_checks:
            if node_id not in nodes_by_id:
                print(f"   ✗ Node {node_id} not found: {description}")
                all_correct = False
                continue
            
            node = nodes_by_id[node_id]
            widgets_values = node.get('widgets_values', [])
            
            if len(widgets_values) <= widget_index:
                print(f"   ✗ Node {node_id}: Missing widget index {widget_index} - {description}")
                all_correct = False
                continue
            
            actual_value = widgets_values[widget_index]
            if actual_value == expected_value:
                print(f"   ✓ Node {node_id}[{widget_index}]: {actual_value} - {description}")
            else:
                print(f"   ✗ Node {node_id}[{widget_index}]: {actual_value} (expected {expected_value}) - {description}")
                all_correct = False
        
        # Check numeric slider values (mxSlider nodes with [value, value, step] pattern)
        # Based on sample file analysis:
        # - Node 85: CFG slider [cfg, cfg, 1]
        # - Node 82: Steps slider [steps, steps, 0]
        # - Node 426: Duration slider [duration, duration, 1]
        # - Node 157: Speed slider [speed, speed, 1]
        # - Node 490: Frame rate slider [frame_rate, frame_rate, 1]
        # - Node 421: Upscale ratio slider [?, upscale_ratio, 1]
        
        numeric_slider_checks = [
            (85, [0, 1], test_inputs["cfg"], "CFG slider"),
            (82, [0, 1], test_inputs["steps"], "Steps slider"),
            (426, [0, 1], test_inputs["duration"], "Duration slider"),
            (157, [0, 1], test_inputs["speed"], "Speed slider"),
            (490, [0, 1], test_inputs["frame_rate"], "Frame rate slider"),
            (421, [1], test_inputs["upscale_ratio"], "Upscale ratio slider (index 1 only)"),
        ]
        
        print("\n   Numeric Slider Validation:")
        for node_id, widget_indices, expected_value, description in numeric_slider_checks:
            if node_id not in nodes_by_id:
                print(f"   ✗ Node {node_id} not found: {description}")
                all_correct = False
                continue
            
            node = nodes_by_id[node_id]
            widgets_values = node.get('widgets_values', [])
            
            # Check each specified index
            node_ok = True
            for idx in widget_indices:
                if len(widgets_values) <= idx:
                    print(f"   ✗ Node {node_id}: Missing widget index {idx} - {description}")
                    all_correct = False
                    node_ok = False
                    break
                
                actual_value = widgets_values[idx]
                if actual_value != expected_value:
                    print(f"   ✗ Node {node_id}[{idx}]: {actual_value} (expected {expected_value}) - {description}")
                    all_correct = False
                    node_ok = False
            
            if node_ok:
                # Show the full widgets_values for verification
                value_str = f"{widgets_values}"
                print(f"   ✓ Node {node_id}: {value_str} - {description}")
        
        return all_correct
    
    def compare_with_example(self, workflow: Dict) -> bool:
        """Compare generated workflow structure with example output"""
        print("\n9. Comparing with example output structure...")
        
        example_path = Path.home() / "Downloads" / "WAN2.2_IMG_to_VIDEO_Base (example).json"
        
        if not example_path.exists():
            print(f"   ⚠ Example file not found: {example_path}")
            return True
        
        try:
            with open(example_path, 'r', encoding='utf-8') as f:
                example = json.load(f)
            
            # Compare high-level structure
            checks = []
            
            if 'nodes' in workflow and 'nodes' in example:
                checks.append((
                    len(workflow['nodes']) == len(example['nodes']),
                    f"Node count: {len(workflow['nodes'])} (example: {len(example['nodes'])})"
                ))
            
            if 'links' in workflow and 'links' in example:
                checks.append((
                    len(workflow['links']) == len(example['links']),
                    f"Link count: {len(workflow['links'])} (example: {len(example['links'])})"
                ))
            
            if 'groups' in workflow and 'groups' in example:
                checks.append((
                    len(workflow['groups']) == len(example['groups']),
                    f"Group count: {len(workflow['groups'])} (example: {len(example['groups'])})"
                ))
            
            all_correct = True
            for check_passed, message in checks:
                if check_passed:
                    print(f"   ✓ {message}")
                else:
                    print(f"   ✗ {message}")
                    all_correct = False
            
            return all_correct
            
        except Exception as e:
            print(f"   ⚠ Could not compare with example: {e}")
            return True
    
    def save_output(self, workflow: Dict) -> bool:
        """Save generated workflow for manual inspection"""
        print("\n10. Saving generated workflow...")
        
        output_path = project_root / "test" / "output" / f"{self.workflow_id}_generated.json"
        output_path.parent.mkdir(exist_ok=True)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(workflow, f, indent=2)
            print(f"   ✓ Saved to: {output_path}")
            return True
        except Exception as e:
            print(f"   ✗ Error saving: {e}")
            return False
    
    def run_full_test(self) -> bool:
        """Run complete test suite"""
        if not self.load_workflow():
            return False
        
        success, workflow = self.generate_workflow()
        if not success:
            return False
        
        # Run all verification tests
        tests = [
            ("Token Replacements", self.verify_token_replacements(workflow)),
            ("Node Mode Toggles", self.verify_node_modes(workflow)),
            ("Model Paths", self.verify_model_paths(workflow)),
            ("Widget Values", self.verify_widget_values(workflow)),
            ("Structure Comparison", self.compare_with_example(workflow)),
            ("Output Save", self.save_output(workflow)),
        ]
        
        # Print summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for _, result in tests if result)
        total = len(tests)
        
        for name, result in tests:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {name}")
        
        print(f"\nResults: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed - see details above")
            return False


def main():
    """Run the test fixture"""
    fixture = WorkflowTestFixture()
    success = fixture.run_full_test()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
