#!/usr/bin/env python3
"""
Create a comprehensive test input for IMG_to_VIDEO editor

This script:
1. Retrieves available models from the instance
2. Creates a test input JSON with the specified configuration
3. Uses the sample_input_image.jpeg as the input image

Usage:
    python3 scripts/create_test_input.py <ssh_connection_string>
    
Example:
    python3 scripts/create_test_input.py "root@123.45.67.89 -p 12345"
"""

import sys
import os
import json
import requests
import shutil
from pathlib import Path

# Base URL for the API
BASE_URL = "http://localhost:5050"

def get_ssh_connection():
    """Get SSH connection from command line or config"""
    if len(sys.argv) > 1:
        return sys.argv[1]
    
    # Try to read from config.yaml
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f)
            ssh_config = config.get('ssh', {})
            host = ssh_config.get('host')
            port = ssh_config.get('port', 22)
            username = ssh_config.get('username', 'root')
            if host:
                return f"{username}@{host} -p {port}"
    
    return None


def scan_models(ssh_connection, model_type, search_pattern='single'):
    """Scan for available models on the instance"""
    print(f"  Scanning for {model_type}...")
    
    url = f"{BASE_URL}/api/models/scan"
    
    payload = {
        'ssh_connection': ssh_connection,
        'model_type': model_type,
        'search_pattern': search_pattern,
        'force_refresh': True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        if data.get('success'):
            models = data.get('models', [])
            print(f"    ✅ Found {len(models)} models")
            return models
        else:
            print(f"    ❌ Error: {data.get('message')}")
            return []
            
    except requests.exceptions.ConnectionError:
        print(f"    ⚠️  Cannot connect to API server (is it running?)")
        return []
    except Exception as e:
        print(f"    ⚠️  Error: {e}")
        return []


def find_model_by_name(models, name_pattern):
    """Find a model matching the name pattern"""
    for model in models:
        if name_pattern in model.get('path', '') or name_pattern in model.get('name', ''):
            return model
    return None


def create_test_input(ssh_connection):
    """Create comprehensive test input with model scanning"""
    
    print("\n" + "=" * 70)
    print("Creating IMG_to_VIDEO Test Input")
    print("=" * 70)
    
    print(f"\nSSH Connection: {ssh_connection}")
    
    # Step 1: Retrieve available models
    print("\n📦 Step 1: Retrieving available models from instance...")
    
    # Scan for diffusion models (high/low pairs)
    diffusion_models = scan_models(ssh_connection, 'diffusion_models', 'high_low_pair')
    
    # Scan for LoRAs
    loras = scan_models(ssh_connection, 'loras', 'high_low_pair')
    
    # Scan for text encoders (CLIP)
    clip_models = scan_models(ssh_connection, 'text_encoders', 'single')
    
    # Scan for VAE models
    vae_models = scan_models(ssh_connection, 'vae', 'single')
    
    # Scan for upscale models
    upscale_models = scan_models(ssh_connection, 'upscale_models', 'single')
    
    # Step 2: Select models based on user requirements
    print("\n🎯 Step 2: Selecting models...")
    
    # Main model: Wan2.2 I2V
    main_model = find_model_by_name(diffusion_models, 'wan2.2_i2v')
    if not main_model:
        main_model = find_model_by_name(diffusion_models, 'wan-2.2')
    if not main_model and diffusion_models:
        main_model = diffusion_models[0]  # Fallback to first available
    
    if main_model:
        print(f"  ✅ Main Model: {main_model.get('name', 'Unknown')}")
    else:
        print(f"  ⚠️  Main Model: Using default path")
    
    # LoRA: Nsfw-22 Strength: 1.0
    lora_model = find_model_by_name(loras, 'Nsfw-22')
    if not lora_model:
        lora_model = find_model_by_name(loras, 'nsfw')
    
    if lora_model:
        print(f"  ✅ LoRA: {lora_model.get('name', 'Unknown')}")
    else:
        print(f"  ⚠️  LoRA: Not found, will use default if available")
    
    # CLIP: umt5_xxl_fp16.safetensors
    clip_model = find_model_by_name(clip_models, 'umt5_xxl_fp16')
    if not clip_model and clip_models:
        clip_model = clip_models[0]  # Fallback to first available
    
    if clip_model:
        print(f"  ✅ CLIP Model: {clip_model.get('name', 'Unknown')}")
    else:
        print(f"  ⚠️  CLIP Model: Using default path")
    
    # VAE: wan_2.1_vae.safetensors
    vae_model = find_model_by_name(vae_models, 'wan_2.1_vae')
    if not vae_model and vae_models:
        vae_model = vae_models[0]  # Fallback to first available
    
    if vae_model:
        print(f"  ✅ VAE Model: {vae_model.get('name', 'Unknown')}")
    else:
        print(f"  ⚠️  VAE Model: Using default path")
    
    # Upscale: RealESRGAN_x4plus.pth
    upscale_model = find_model_by_name(upscale_models, 'RealESRGAN_x4plus')
    if not upscale_model and upscale_models:
        upscale_model = upscale_models[0]  # Fallback to first available
    
    if upscale_model:
        print(f"  ✅ Upscale Model: {upscale_model.get('name', 'Unknown')}")
    else:
        print(f"  ⚠️  Upscale Model: Using default path")
    
    # Step 3: Prepare image path
    print("\n🖼️  Step 3: Preparing input image...")
    
    sample_image = Path(__file__).parent.parent / "test" / "samples" / "sample_input_image.jpeg"
    if not sample_image.exists():
        print(f"  ❌ ERROR: sample_input_image.jpeg not found at {sample_image}")
        sys.exit(1)
    
    print(f"  ✅ Input Image: {sample_image.name} ({sample_image.stat().st_size / 1024:.1f} KB)")
    
    # Step 4: Build test input configuration
    print("\n⚙️  Step 4: Building test input configuration...")
    
    test_input = {
        "workflow_id": "IMG_to_VIDEO_canvas",
        "name": "Comprehensive Test Input",
        "description": "Test input with all parameters configured and models retrieved from instance",
        "inputs": {
            # Image input (relative path for test)
            "input_image": str(sample_image.relative_to(Path(__file__).parent.parent)),
            
            # Text inputs
            "positive_prompt": "The subject moves naturally with smooth cinematic motion, high quality, detailed",
            "negative_prompt": "fast movements, blurry, mouth moving, talking, teeth visible, strong blush",
            "seed": -1,  # Random seed
            
            # Size parameters
            "size_x": 576,
            "size_y": 832,
            
            # Generation parameters
            "duration": 5,
            "steps": 20,
            "cfg": 3.5,
            "frame_rate": 16,
            "speed": 7,
            "upscale_ratio": 2,
            
            # Model selections
            "main_model": {
                "high": main_model.get('high_path') if main_model else "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_high_noise_14B_fp16.safetensors",
                "low": main_model.get('low_path') if main_model else "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_low_noise_14B_fp16.safetensors"
            },
            
            "clip_model": clip_model.get('path') if clip_model else "Wan-2.2/umt5_xxl_fp16.safetensors",
            "vae_model": vae_model.get('path') if vae_model else "Wan-2.1/wan_2.1_vae.safetensors",
            "upscale_model": upscale_model.get('path') if upscale_model else "RealESRGAN_x4plus.pth",
            
            # Toggles (using mode values: 0 = enabled, 2 = disabled/bypassed)
            "save_last_frame": 2,  # false = mode 2 (bypassed)
            "enable_interpolation": 0,  # true = mode 0 (enabled)
            "enable_upscaler": 2,  # false = mode 2 (bypassed)
            "enable_upscale_interpolation": 2,  # false = mode 2 (bypassed)
            "video_enhancer": 0,  # true = mode 0 (enabled)
            "cfg_zero_star": 0,  # true = mode 0 (enabled)
            "speed_regulation": 0,  # true = mode 0 (enabled)
            "normalized_attention": 0,  # true = mode 0 (enabled)
            "magcache": 0,  # true = mode 0 (enabled)
            "torchcompile": 0,  # true = mode 0 (enabled)
            "blockswap": 0,  # true = mode 0 (enabled)
            "vram_reduction": 100,
            "automatic_prompting": 0  # true = mode 0 (enabled)
        }
    }
    
    # Add LoRA if found
    if lora_model:
        test_input["inputs"]["loras"] = [
            {
                "high_path": lora_model.get('high_path'),
                "low_path": lora_model.get('low_path'),
                "strength": 1.0
            }
        ]
        print(f"  ✅ Added LoRA with strength 1.0")
    
    print(f"  ✅ Configuration complete")
    
    # Step 5: Save test input
    print("\n💾 Step 5: Saving test input...")
    
    output_path = Path(__file__).parent.parent / "test" / "samples" / "IMG_to_VIDEO_comprehensive_test.json"
    
    with open(output_path, 'w') as f:
        json.dump(test_input, f, indent=2)
    
    print(f"  ✅ Saved to: {output_path}")
    
    # Step 6: Display summary
    print("\n" + "=" * 70)
    print("📋 Test Input Summary")
    print("=" * 70)
    print(f"\nWorkflow: {test_input['workflow_id']}")
    print(f"\nImage: {test_input['inputs']['input_image']}")
    print(f"\nDimensions: {test_input['inputs']['size_x']}x{test_input['inputs']['size_y']}")
    print(f"Duration: {test_input['inputs']['duration']}s @ {test_input['inputs']['frame_rate']} FPS")
    print(f"Steps: {test_input['inputs']['steps']}, CFG: {test_input['inputs']['cfg']}")
    print(f"Speed: {test_input['inputs']['speed']}, Upscale: {test_input['inputs']['upscale_ratio']}x")
    
    print(f"\nModels:")
    print(f"  Main: {test_input['inputs']['main_model']['high'].split('/')[-1]}")
    if lora_model:
        print(f"  LoRA: {test_input['inputs']['loras'][0]['high_path'].split('/')[-1]} (strength: 1.0)")
    print(f"  CLIP: {test_input['inputs']['clip_model'].split('/')[-1]}")
    print(f"  VAE: {test_input['inputs']['vae_model'].split('/')[-1]}")
    print(f"  Upscale: {test_input['inputs']['upscale_model'].split('/')[-1]}")
    
    print(f"\nFeatures Enabled:")
    enabled_features = []
    disabled_features = []
    
    feature_map = {
        "save_last_frame": "Save Last Frame",
        "enable_interpolation": "Interpolation (RIFE)",
        "enable_upscaler": "Upscaler",
        "enable_upscale_interpolation": "Upscale + Interpolation",
        "video_enhancer": "Video Enhancer",
        "cfg_zero_star": "CFGZeroStar",
        "speed_regulation": "Speed Regulation",
        "normalized_attention": "Normalized Attention",
        "magcache": "MagCache",
        "torchcompile": "TorchCompile",
        "blockswap": "BlockSwap",
        "automatic_prompting": "Automatic Prompting"
    }
    
    for key, label in feature_map.items():
        if test_input['inputs'][key] == 0:
            enabled_features.append(label)
        else:
            disabled_features.append(label)
    
    for feature in enabled_features:
        print(f"  ✅ {feature}")
    
    if disabled_features:
        print(f"\nFeatures Disabled:")
        for feature in disabled_features:
            print(f"  ❌ {feature}")
    
    print(f"\nPrompts:")
    print(f"  Positive: {test_input['inputs']['positive_prompt'][:60]}...")
    print(f"  Negative: {test_input['inputs']['negative_prompt'][:60]}...")
    
    print("\n" + "=" * 70)
    print("✅ Test input created successfully!")
    print("=" * 70)
    
    print(f"\n📍 Location: {output_path}")
    print(f"\n🚀 Next steps:")
    print(f"  1. Review the generated JSON file")
    print(f"  2. Use it in the WebUI for testing")
    print(f"  3. Or use it with the workflow generator API")
    
    return output_path


def main():
    """Main entry point"""
    
    ssh_connection = get_ssh_connection()
    
    if not ssh_connection:
        print("❌ ERROR: SSH connection string required")
        print("\nUsage:")
        print('  python3 scripts/create_test_input.py "root@123.45.67.89 -p 12345"')
        print("\nOr configure SSH in config.yaml")
        sys.exit(1)
    
    try:
        output_path = create_test_input(ssh_connection)
        print(f"\n✨ Success! Test input created at:\n   {output_path}")
        
    except KeyboardInterrupt:
        print("\n\n⏸️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
