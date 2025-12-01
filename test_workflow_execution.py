#!/usr/bin/env python3
"""
Test workflow execution via the webui API
"""
import requests
import json
import time
import base64
from pathlib import Path

# Configuration
API_BASE_URL = "http://10.0.78.66:5000"
SSH_CONNECTION = "ssh -p 40538 root@198.53.64.194 -L 8080:localhost:8080"
IMAGE_PATH = "/home/sdamk/dev/vast_api/test/upload_827e9bba.jpeg"
WORKFLOW_ID = "IMG_to_VIDEO"

def encode_image_to_base64(image_path):
    """Encode image file to base64 string"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def generate_workflow(image_base64):
    """Generate workflow JSON via API"""
    url = f"{API_BASE_URL}/create/generate-workflow"
    
    # Prepare form data matching the webui structure
    inputs = {
        "input_image": f"data:image/jpeg;base64,{image_base64}",
        "positive_prompt": "The subject moves naturally with smooth cinematic motion, high quality, detailed",
        "negative_prompt": "色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走, fast movements, blurry, mouth moving, talking, teeth visible, strong blush",
        "noise_seed": 495100899429947,
        "steps": 20,
        "width": 896,
        "height": 1120,
        "cfg_scale": 3.5,
        "speed": 7,
        "duration": 5,
        "frame_rate": 16,
        "enable_interpolation": True,
        "enable_upscale": False,
        "enable_upscale_interpolation": False,
        "enable_florence_caption": False,
        "enable_custom_size": False,
        "main_model": {
            "highNoisePath": "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_high_noise_14B_fp16.safetensors",
            "lowNoisePath": "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_low_noise_14B_fp16.safetensors"
        },
        "clip_model": "Wan-2.2/umt5_xxl_fp16.safetensors",
        "vae_model": "Wan-2.1/wan_2.1_vae.safetensors",
        "upscale_model": "RealESRGAN_x4plus.pth",
        "upscale_ratio": 2
    }
    
    payload = {
        "workflow_id": WORKFLOW_ID,
        "inputs": inputs
    }
    
    print("Generating workflow...")
    print(f"POST {url}")
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    result = response.json()
    print(f"✓ Workflow generated successfully")
    return result, inputs  # Return both result and inputs

def execute_workflow(inputs, ssh_connection):
    """Execute workflow on cloud instance"""
    url = f"{API_BASE_URL}/create/execute"
    
    payload = {
        "workflow_id": WORKFLOW_ID,
        "inputs": inputs,
        "ssh_connection": ssh_connection
    }
    
    print(f"\nExecuting workflow on cloud instance...")
    print(f"POST {url}")
    print(f"SSH: {ssh_connection}")
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    result = response.json()
    print(f"✓ Workflow execution started")
    print(f"Prompt ID: {result.get('prompt_id', 'N/A')}")
    return result

def main():
    print("=" * 60)
    print("Workflow Execution Test")
    print("=" * 60)
    
    try:
        # Step 1: Encode image
        print(f"\n1. Encoding image: {IMAGE_PATH}")
        image_base64 = encode_image_to_base64(IMAGE_PATH)
        image_size_kb = len(image_base64) / 1024
        print(f"✓ Image encoded: {image_size_kb:.1f} KB (base64)")
        
        # Step 2: Generate workflow
        print(f"\n2. Generating workflow: {WORKFLOW_ID}")
        workflow_result, inputs = generate_workflow(image_base64)
        
        if 'workflow' not in workflow_result:
            print("✗ Error: No workflow in response")
            print(json.dumps(workflow_result, indent=2))
            return
        
        workflow_json = workflow_result['workflow']
        print(f"✓ Workflow has {len(workflow_json)} nodes")
        
        # Step 3: Execute workflow
        print(f"\n3. Executing workflow")
        exec_result = execute_workflow(inputs, SSH_CONNECTION)
        
        if 'error' in exec_result:
            print(f"✗ Execution error: {exec_result['error']}")
            return
        
        prompt_id = exec_result.get('prompt_id')
        if prompt_id:
            print(f"\n✓ SUCCESS!")
            print(f"   Prompt ID: {prompt_id}")
            print(f"   Monitor progress in ComfyUI at the cloud instance")
        else:
            print(f"\n⚠ Execution started but no prompt_id returned")
            print(json.dumps(exec_result, indent=2))
        
    except requests.exceptions.RequestException as e:
        print(f"\n✗ HTTP Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(json.dumps(error_detail, indent=2))
            except:
                print(e.response.text)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
