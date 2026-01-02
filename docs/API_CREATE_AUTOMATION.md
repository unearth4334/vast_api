# Create Workflow Automation API

**Version:** 1.0.0  
**Date:** December 30, 2025  
**Base URL:** `http://<host>:5000/create`

## Overview

This API provides programmatic access to workflow selection, configuration, and execution in the Create tab. It enables automated workflow generation without requiring manual interaction with the web UI.

## Use Cases

- **Automated Video Generation**: Schedule or trigger video generation jobs programmatically
- **Batch Processing**: Process multiple images with the same or different configurations
- **Integration**: Integrate workflow execution into other systems or pipelines
- **Testing**: Automated testing of workflow configurations
- **CI/CD**: Include workflow generation in deployment pipelines

---

## API Endpoints

### 1. List Available Workflows

Get a list of all available workflows with their metadata.

**Endpoint:** `GET /create/workflows/list`

**Response:**
```json
{
  "success": true,
  "workflows": [
    {
      "id": "IMG_to_VIDEO_canvas",
      "name": "IMG to VIDEO",
      "description": "Generate video from a single image using WAN 2.2 Image-to-Video model",
      "category": "video",
      "version": "3.0.0",
      "tags": ["image-to-video", "wan-2.2", "video-generation"],
      "vram_estimate": null,
      "time_estimate": {
        "min": 120,
        "max": 300
      }
    }
  ]
}
```

**Example:**
```bash
curl http://localhost:5000/create/workflows/list
```

---

### 2. Get Workflow Schema

Get detailed information about a workflow including its input fields, types, defaults, and validation rules.

**Endpoint:** `GET /create/workflows/<workflow_id>`

**Parameters:**
- `workflow_id` (path): The workflow identifier (e.g., `IMG_to_VIDEO_canvas`)

**Response:**
```json
{
  "success": true,
  "workflow": {
    "id": "IMG_to_VIDEO_canvas",
    "name": "IMG to VIDEO",
    "description": "Generate video from a single image...",
    "version": "3.0.0",
    "inputs": [
      {
        "id": "input_image",
        "type": "image",
        "label": "Input Image",
        "description": "Source image to animate",
        "required": true,
        "accept": "image/png,image/jpeg,image/webp",
        "max_size_mb": 10
      },
      {
        "id": "positive_prompt",
        "type": "textarea",
        "label": "Positive Prompt",
        "description": "Describe the motion and style",
        "required": true,
        "default": "The subject moves naturally with smooth cinematic motion",
        "max_length": 2000
      },
      {
        "id": "duration",
        "type": "slider",
        "label": "Duration",
        "description": "Video length in seconds",
        "min": 1.0,
        "max": 10.0,
        "step": 0.5,
        "default": 5.0,
        "unit": "seconds"
      }
      // ... more inputs
    ]
  }
}
```

**Example:**
```bash
curl http://localhost:5000/create/workflows/IMG_to_VIDEO_canvas
```

---

### 3. Queue Workflow Execution

Execute a workflow with specified inputs. This is the main endpoint for automated workflow execution.

**Endpoint:** `POST /create/queue-workflow`

**Request Body:**
```json
{
  "ssh_connection": "ssh -p 40526 root@198.53.64.194",
  "workflow_id": "IMG_to_VIDEO_canvas",
  "inputs": {
    "input_image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
    "positive_prompt": "The subject moves naturally with smooth cinematic motion, high quality, detailed",
    "negative_prompt": "blurry, static, low quality",
    "seed": -1,
    "size_x": 832,
    "size_y": 1216,
    "duration": 5.0,
    "steps": 20,
    "cfg": 3.5,
    "frame_rate": 16.0,
    "speed": 7.0,
    "upscale_ratio": 2.0,
    "main_model": {
      "highNoisePath": "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_high_noise_14B_fp16.safetensors",
      "lowNoisePath": "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_low_noise_14B_fp16.safetensors",
      "basePath": "models/diffusion_models"
    },
    "loras": [
      {
        "highNoisePath": "WAN DR34ML4Y/DR34ML4Y_I2V_14B_HIGH.safetensors",
        "lowNoisePath": "WAN DR34ML4Y/DR34ML4Y_I2V_14B_LOW.safetensors",
        "strength": 1.0
      }
    ],
    "clip_model": {
      "path": "Wan-2.2/umt5_xxl_fp16.safetensors"
    },
    "vae_model": {
      "path": "Wan-2.1/wan_2.1_vae.safetensors"
    },
    "upscale_model": {
      "path": "RealESRGAN_x4plus.pth"
    },
    "enable_interpolation": 0,
    "enable_upscale_interpolation": 0,
    "use_upscaler": 2,
    "save_last_frame": 2,
    "enable_video_enhancer": 0,
    "enable_cfg_zero_star": 0,
    "enable_speed_regulation": 0,
    "enable_normalized_attention": 0,
    "enable_magcache": 0,
    "enable_torch_compile": 4,
    "enable_block_swap": 0,
    "vram_reduction": 100,
    "enable_auto_prompt": 0
  }
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "prompt_id": "queued_a1b2c3d4",
  "message": "Workflow queued successfully via BrowserAgent",
  "input_json_info": {
    "version": null,
    "workflow_file": null,
    "input_sections": [
      "basic_settings",
      "generation_parameters",
      "model_selection",
      "advanced_features"
    ]
  },
  "transformed_inputs": {
    "inputs": {
      "basic_settings": {
        "input_image": "upload_abc123.jpeg",
        "positive_prompt": "The subject moves naturally...",
        "negative_prompt": "blurry, static...",
        "seed": 1234567890
      },
      "generation_parameters": {
        "size_x": 832,
        "size_y": 1216,
        "duration": 5.0,
        "steps": 20,
        "cfg": 3.5,
        "frame_rate": 16.0,
        "speed": 7.0,
        "upscale_ratio": 2.0
      },
      "model_selection": {
        "main_model": {
          "high_noise": "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_high_noise_14B_fp16.safetensors",
          "low_noise": "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_low_noise_14B_fp16.safetensors"
        },
        "loras": [
          {
            "high_noise": "WAN DR34ML4Y/DR34ML4Y_I2V_14B_HIGH.safetensors",
            "low_noise": "WAN DR34ML4Y/DR34ML4Y_I2V_14B_LOW.safetensors",
            "strength": 1.0
          }
        ],
        "clip_model": "Wan-2.2/umt5_xxl_fp16.safetensors",
        "vae_model": "Wan-2.1/wan_2.1_vae.safetensors",
        "upscale_model": "RealESRGAN_x4plus.pth"
      },
      "advanced_features": {
        "output_enhancement": {
          "save_last_frame": false,
          "save_original_output": true,
          "save_interpoled_output": false,
          "save_upscaled_output": false,
          "save_upint_output": true
        },
        "quality_enhancements": {
          "enable_video_enhancer": true,
          "enable_cfg_zero_star": true,
          "enable_speed_regulation": true,
          "enable_normalized_attention": true
        },
        "performance_memory": {
          "enable_magcache": true,
          "enable_torch_compile": false,
          "enable_block_swap": true,
          "vram_reduction": 100
        },
        "automatic_prompting": {
          "enable_auto_prompt": true
        }
      }
    }
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/create/queue-workflow \
  -H "Content-Type: application/json" \
  -d '{
    "ssh_connection": "ssh -p 40526 root@198.53.64.194",
    "workflow_id": "IMG_to_VIDEO_canvas",
    "inputs": {
      "input_image": "data:image/jpeg;base64,...",
      "positive_prompt": "cinematic motion",
      "negative_prompt": "blurry",
      "seed": -1,
      "duration": 5.0,
      "steps": 20
    }
  }'
```

---

### 4. Export Workflow (Preview)

Generate and download a workflow JSON file without executing it. Useful for debugging or saving workflow configurations.

**Endpoint:** `POST /create/export-workflow`

**Request Body:**
```json
{
  "workflow_id": "IMG_to_VIDEO_canvas",
  "inputs": {
    "input_image": "data:image/jpeg;base64,...",
    "positive_prompt": "cinematic motion",
    // ... other inputs
  }
}
```

**Response:**
- Content-Type: `application/json`
- Content-Disposition: `attachment; filename="IMG_to_VIDEO_canvas_<timestamp>.json"`
- Body: Complete ComfyUI workflow JSON

**Headers:**
- `X-Input-JSON-Keys`: Comma-separated list of input sections
- `X-Workflow-Version`: Workflow version
- `X-Transformed-Inputs`: JSON string of transformed inputs

**Example:**
```bash
curl -X POST http://localhost:5000/create/export-workflow \
  -H "Content-Type: application/json" \
  -d '{"workflow_id": "IMG_to_VIDEO_canvas", "inputs": {...}}' \
  -o workflow.json
```

---

## Input Field Reference

### Basic Settings

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `input_image` | string (base64) | Yes | - | Base64-encoded image data with MIME type prefix |
| `positive_prompt` | string | Yes | "The subject moves naturally..." | Desired motion and style description |
| `negative_prompt` | string | No | "blurry, static..." | What to avoid |
| `seed` | integer | No | -1 | Random seed (-1 for random) |

### Generation Parameters

| Field | Type | Required | Range | Default | Unit |
|-------|------|----------|-------|---------|------|
| `size_x` | integer | No | 512-1920 | 896 | pixels |
| `size_y` | integer | No | 512-1920 | 1120 | pixels |
| `duration` | float | No | 1.0-10.0 | 5.0 | seconds |
| `steps` | integer | No | 10-40 | 20 | - |
| `cfg` | float | No | 1.0-10.0 | 3.5 | - |
| `frame_rate` | float | No | 8.0-24.0 | 16.0 | FPS |
| `speed` | float | No | 1.0-15.0 | 7.0 | - |
| `upscale_ratio` | float | No | 1.0-4.0 | 2.0 | - |

### Model Selection

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `main_model` | object | Yes | High/low noise model pair |
| `main_model.highNoisePath` | string | Yes | Path to high noise model |
| `main_model.lowNoisePath` | string | Yes | Path to low noise model |
| `loras` | array | No | List of LoRA models (max 5) |
| `loras[].highNoisePath` | string | Yes | Path to high noise LoRA |
| `loras[].lowNoisePath` | string | Yes | Path to low noise LoRA |
| `loras[].strength` | float | Yes | LoRA strength (0.0-1.0) |
| `clip_model` | object | Yes | Text encoder model |
| `vae_model` | object | Yes | VAE model |
| `upscale_model` | object | No | Upscaler model |

### Advanced Features - Output Enhancement

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `save_last_frame` | integer (mode) | 2 | Save final frame (0=enabled, 2=disabled) |
| `enable_interpolation` | integer (mode) | 0 | Enable frame interpolation (0=enabled, 2=disabled) |
| `use_upscaler` | integer (mode) | 2 | Enable upscaling (0=enabled, 2=disabled) |
| `enable_upscale_interpolation` | integer (mode) | 2 | Combined upscale+interpolation (0=enabled, 2=disabled) |

**Note:** Node modes: `0` = enabled, `2` = bypassed, `4` = muted

### Advanced Features - Quality Enhancement

| Field | Type | Default | Mode Values |
|-------|------|---------|-------------|
| `enable_video_enhancer` | integer | 0 | 0=enabled, 4=disabled |
| `enable_cfg_zero_star` | integer | 0 | 0=enabled, 4=disabled |
| `enable_speed_regulation` | integer | 0 | 0=enabled, 4=disabled |
| `enable_normalized_attention` | integer | 0 | 0=enabled, 4=disabled |

### Advanced Features - Performance

| Field | Type | Default | Mode Values |
|-------|------|---------|-------------|
| `enable_magcache` | integer | 0 | 0=enabled, 4=disabled |
| `enable_torch_compile` | integer | 4 | 0=enabled, 4=disabled |
| `enable_block_swap` | integer | 0 | 0=enabled, 4=disabled |
| `vram_reduction` | integer | 100 | 0-100 (percentage) |
| `enable_auto_prompt` | integer | 0 | 0=enabled, 4=disabled |

---

## Complete Example: Python Script

```python
#!/usr/bin/env python3
"""
Automated workflow execution example
"""
import requests
import base64
import json
import time

# Configuration
API_BASE_URL = "http://localhost:5000/create"
SSH_CONNECTION = "ssh -p 40526 root@198.53.64.194"
IMAGE_PATH = "input_image.jpg"

def encode_image(image_path: str) -> str:
    """Encode image to base64 with MIME type prefix"""
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    # Determine MIME type
    if image_path.lower().endswith('.png'):
        mime_type = 'image/png'
    elif image_path.lower().endswith(('.jpg', '.jpeg')):
        mime_type = 'image/jpeg'
    else:
        mime_type = 'image/jpeg'
    
    encoded = base64.b64encode(image_data).decode('utf-8')
    return f"data:{mime_type};base64,{encoded}"

def list_workflows():
    """Get list of available workflows"""
    response = requests.get(f"{API_BASE_URL}/workflows/list")
    return response.json()

def get_workflow_schema(workflow_id: str):
    """Get workflow input schema"""
    response = requests.get(f"{API_BASE_URL}/workflows/{workflow_id}")
    return response.json()

def queue_workflow(workflow_id: str, inputs: dict):
    """Execute workflow with inputs"""
    payload = {
        "ssh_connection": SSH_CONNECTION,
        "workflow_id": workflow_id,
        "inputs": inputs
    }
    
    response = requests.post(
        f"{API_BASE_URL}/queue-workflow",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    return response.json()

def main():
    # Step 1: List available workflows
    print("📋 Fetching available workflows...")
    workflows = list_workflows()
    print(f"✅ Found {len(workflows['workflows'])} workflow(s)")
    for wf in workflows['workflows']:
        print(f"  • {wf['id']}: {wf['name']} (v{wf['version']})")
    
    # Step 2: Get workflow schema
    workflow_id = "IMG_to_VIDEO_canvas"
    print(f"\n📖 Fetching schema for {workflow_id}...")
    schema = get_workflow_schema(workflow_id)
    print(f"✅ Schema has {len(schema['workflow']['inputs'])} input fields")
    
    # Step 3: Prepare inputs
    print(f"\n🖼️  Encoding image from {IMAGE_PATH}...")
    image_base64 = encode_image(IMAGE_PATH)
    print(f"✅ Image encoded ({len(image_base64)} bytes)")
    
    inputs = {
        "input_image": image_base64,
        "positive_prompt": "The subject moves naturally with smooth cinematic motion, high quality, detailed",
        "negative_prompt": "blurry, static, low quality",
        "seed": -1,  # Random seed
        "size_x": 832,
        "size_y": 1216,
        "duration": 5.0,
        "steps": 20,
        "cfg": 3.5,
        "frame_rate": 16.0,
        "speed": 7.0,
        "upscale_ratio": 2.0,
        "main_model": {
            "highNoisePath": "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_high_noise_14B_fp16.safetensors",
            "lowNoisePath": "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_low_noise_14B_fp16.safetensors",
            "basePath": "models/diffusion_models"
        },
        "loras": [],
        "clip_model": {"path": "Wan-2.2/umt5_xxl_fp16.safetensors"},
        "vae_model": {"path": "Wan-2.1/wan_2.1_vae.safetensors"},
        "upscale_model": {"path": "RealESRGAN_x4plus.pth"},
        "enable_interpolation": 2,  # Disabled
        "enable_upscale_interpolation": 0,  # Enabled
        "use_upscaler": 2,  # Disabled
        "save_last_frame": 2,  # Disabled
        "enable_video_enhancer": 0,
        "enable_cfg_zero_star": 0,
        "enable_speed_regulation": 0,
        "enable_normalized_attention": 0,
        "enable_magcache": 0,
        "enable_torch_compile": 4,
        "enable_block_swap": 0,
        "vram_reduction": 100,
        "enable_auto_prompt": 0
    }
    
    # Step 4: Queue workflow
    print(f"\n🚀 Queueing workflow...")
    result = queue_workflow(workflow_id, inputs)
    
    if result['success']:
        print(f"✅ Workflow queued successfully!")
        print(f"   Task ID: {result['task_id']}")
        print(f"   Prompt ID: {result['prompt_id']}")
        print(f"\n📊 Transformed Inputs:")
        print(json.dumps(result['transformed_inputs'], indent=2))
    else:
        print(f"❌ Failed to queue workflow: {result.get('message')}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
```

---

## Error Handling

### Common Error Responses

**400 Bad Request - Missing Required Field:**
```json
{
  "success": false,
  "message": "workflow_id is required"
}
```

**400 Bad Request - Validation Error:**
```json
{
  "success": false,
  "message": "Input validation failed",
  "errors": [
    {
      "field": "duration",
      "message": "Value 15.0 exceeds maximum of 10.0"
    }
  ]
}
```

**404 Not Found - Workflow Not Found:**
```json
{
  "success": false,
  "message": "Workflow not found: invalid_workflow_id"
}
```

**500 Internal Server Error:**
```json
{
  "success": false,
  "message": "Failed to queue workflow: <error details>"
}
```

---

## Rate Limiting

Currently, there are no rate limits on the API. However, keep in mind:

- Image processing and workflow generation can take several seconds
- ComfyUI instance capacity limits concurrent workflow executions
- Large base64-encoded images increase request size and processing time

**Recommendations:**
- Monitor workflow completion before queuing additional workflows
- Implement exponential backoff for retries
- Consider image size optimization (resize before base64 encoding)

---

## Authentication

Currently, the API does not require authentication. In production environments, consider implementing:

- API key authentication
- OAuth2 for user-specific access
- IP whitelisting for trusted sources
- Rate limiting per API key/user

---

## Best Practices

### 1. Image Handling

**Do:**
- Resize images to target dimensions before encoding
- Use JPEG for photographs (smaller file size)
- Use PNG for images with transparency
- Validate image size before encoding (max 10MB recommended)

**Don't:**
- Send extremely large images (>4K resolution)
- Use uncompressed formats unnecessarily

### 2. Input Validation

**Do:**
- Fetch workflow schema first to understand valid inputs
- Validate inputs client-side before submission
- Use default values from schema when available
- Test with minimal inputs first

**Don't:**
- Assume default values without checking schema
- Skip validation of ranges and types

### 3. Error Handling

**Do:**
- Implement retry logic with exponential backoff
- Log full error responses for debugging
- Handle network timeouts gracefully
- Validate SSH connection before queuing

**Don't:**
- Retry immediately without delay
- Ignore validation errors

### 4. Performance

**Do:**
- Reuse SSH connections when possible
- Batch multiple workflows if supported
- Monitor workflow queue status
- Clean up completed workflows

**Don't:**
- Queue unlimited workflows simultaneously
- Poll status too frequently

---

## Future Enhancements

Planned features for future API versions:

- **Workflow Status Polling**: `GET /create/status/<task_id>`
- **Cancel Workflow**: `DELETE /create/cancel/<task_id>`
- **Batch Execution**: Submit multiple workflows in one request
- **Workflow Templates**: Save and reuse input configurations
- **Result Retrieval**: Download generated videos via API
- **WebSocket Support**: Real-time progress updates
- **History API**: Query past workflow executions

---

## Support

For issues, questions, or feature requests:

- Check logs at `/app/logs/` in the container
- Review workflow interpreter logs for detailed execution traces
- Verify SSH connection to ComfyUI instance
- Ensure all required models are present on the instance

---

## Changelog

### Version 1.0.0 (2025-12-30)
- Initial API documentation
- Support for IMG_to_VIDEO_canvas workflow
- Basic workflow queuing and export endpoints
- Input transformation and validation
- Detailed logging support
