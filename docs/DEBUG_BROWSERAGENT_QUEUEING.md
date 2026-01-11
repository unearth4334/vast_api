# BrowserAgent Workflow Queueing - Debug Guide

## Overview

When the "▶️ Run Workflow" button is clicked in the Create tab, the system processes inputs and queues the workflow via BrowserAgent. This document traces the exact inputs available at each step for isolation testing.

## Complete Flow with Data Points

### 1. Frontend Form Submission

**Location:** `app/webui/js/create/create-tab.js` - `executeWorkflow()`

**Inputs Available:**
```javascript
{
  ssh_connection: "ssh -p 40738 root@198.53.64.194 -L 8080:localhost:8080",
  workflow_id: "IMG_to_VIDEO_canvas",
  inputs: {
    input_image: "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
    canvas_width: 1024,
    canvas_height: 576,
    video_frames: 120,
    video_fps: 20,
    positive_prompt: "beautiful landscape with mountains",
    negative_prompt: "ugly, distorted",
    checkpoint_model: "dreamshaper_8.safetensors",
    motion_module: "mm_sd15_v3.safetensors"
  }
}
```

### 2. Backend Endpoint Receives Request

**Location:** `app/api/create.py` - `queue_workflow_with_browseragent()`

**Processing Steps:**

#### Step 2a: Parse SSH Connection
```python
ssh_connection = "ssh -p 40738 root@198.53.64.194 -L 8080:localhost:8080"
host = "198.53.64.194"
port = "40738"
```

#### Step 2b: Load Workflow Configuration
```python
workflow_config = WorkflowLoader.load_workflow("IMG_to_VIDEO_canvas")
# Returns WorkflowConfig object from IMG_to_VIDEO_canvas.webui.yml
```

### 3. Generate Workflow from Inputs

**Location:** `app/api/create.py` - `_generate_workflow_from_inputs()`

**Input Parameters:**
```python
workflow_id = "IMG_to_VIDEO_canvas"
workflow_config = WorkflowConfig(...)  # From .webui.yml file
flat_inputs = {
    "input_image": "data:image/jpeg;base64,...",
    "canvas_width": 1024,
    "canvas_height": 576,
    ...
}
process_images = True
ssh_connection = "ssh -p 40738 root@198.53.64.194 -L 8080:localhost:8080"
host = "198.53.64.194"
port = "40738"
```

#### Step 3a: Upload Images FIRST

**Function:** `_upload_image_to_remote(base64_data, ssh_connection, host, port)`

**Process:**
1. Extract image data from base64
2. Generate filename: `image_d41d8cd98f00b204e9800998ecf8427e.jpeg`
3. Create temporary local file
4. **Execute SCP upload:**
   ```bash
   scp -P 40738 \
     -o StrictHostKeyChecking=yes \
     -o UserKnownHostsFile=/root/.ssh/known_hosts \
     /tmp/tmpXXXXXX.jpeg \
     root@198.53.64.194:/workspace/ComfyUI/input/image_d41d8cd98f00b204e9800998ecf8427e.jpeg
   ```
5. Return: `"image_d41d8cd98f00b204e9800998ecf8427e.jpeg"`

**Updated Inputs After Upload:**
```python
processed_flat_inputs = {
    "input_image": "image_d41d8cd98f00b204e9800998ecf8427e.jpeg",  # ← Changed!
    "canvas_width": 1024,
    "canvas_height": 576,
    ...
}
```

#### Step 3b: Convert to Nested Format

**Function:** `InterpreterAdapter.convert_ui_inputs_to_interpreter_format()`

**Input:** Flat dict with filenames (no base64)
```python
{
    "input_image": "image_d41d8cd98f00b204e9800998ecf8427e.jpeg",
    "canvas_width": 1024,
    "canvas_height": 576,
    ...
}
```

**Output:** Nested structure
```json
{
  "inputs": {
    "canvas": {
      "width": 1024,
      "height": 576
    },
    "video": {
      "frames": 120,
      "fps": 20
    },
    "prompts": {
      "positive": "beautiful landscape with mountains",
      "negative": "ugly, distorted"
    },
    "models": {
      "checkpoint": "dreamshaper_8.safetensors",
      "motion_module": "mm_sd15_v3.safetensors"
    },
    "input_image": {
      "image": "image_d41d8cd98f00b204e9800998ecf8427e.jpeg"
    }
  }
}
```

#### Step 3c: Create Full Input JSON

**Structure:**
```json
{
  "description": "Input values for IMG to Video Canvas workflow",
  "test_id": "IMG_to_VIDEO_canvas_20260110_143022",
  "notes": "Generated from WebUI. Workflow version: 1.0",
  "inputs": {
    "canvas": { "width": 1024, "height": 576 },
    "video": { "frames": 120, "fps": 20 },
    "prompts": { ... },
    "models": { ... },
    "input_image": { "image": "image_d41d8cd98f00b204e9800998ecf8427e.jpeg" }
  }
}
```

**Saved to:** `/tmp/tmpXXXXXX_inputs.json`

#### Step 3d: Run WorkflowInterpreter

**Function:** `WorkflowInterpreter.generate_actions(inputs_data)`

**Inputs:**
- Wrapper path: `workflows/IMG_to_VIDEO_canvas.webui.yml`
- Input JSON: (from above)
- Base workflow: `workflows/IMG_to_VIDEO_canvas.json`

**Process:**
1. Load node mappings from wrapper
2. Generate actions (ModifyWidget, ToggleNode, AddLoRA)
3. Apply actions to base workflow
4. Return modified workflow JSON

**Output:** Complete executable workflow JSON
```json
{
  "last_node_id": 45,
  "last_link_id": 89,
  "nodes": [
    {
      "id": 1,
      "type": "LoadImage",
      "widgets_values": [
        "image_d41d8cd98f00b204e9800998ecf8427e.jpeg",
        "image"
      ]
    },
    {
      "id": 2,
      "type": "EmptyLatentImage",
      "widgets_values": [1024, 576, 1]
    },
    // ... 40+ more nodes with modified values
  ],
  "links": [...],
  "groups": [...],
  "config": {...}
}
```

### 4. Upload Workflow to Remote

**Location:** `app/api/create.py` - `_upload_workflow_to_browseragent()`

**Input:** Complete workflow JSON (from Step 3d)

**Process:**
1. Generate unique filename: `workflow_a1b2c3d4.json`
2. Write to local temp file: `/tmp/tmpXXXXXX.json`
3. **Create remote directory:**
   ```bash
   ssh -p 40738 \
     -o StrictHostKeyChecking=yes \
     -o UserKnownHostsFile=/root/.ssh/known_hosts \
     root@198.53.64.194 \
     'mkdir -p /workspace/ComfyUI/user/default/workflows'
   ```
4. **Upload workflow file:**
   ```bash
   scp -P 40738 \
     -o StrictHostKeyChecking=yes \
     -o UserKnownHostsFile=/root/.ssh/known_hosts \
     /tmp/tmpXXXXXX.json \
     root@198.53.64.194:/workspace/ComfyUI/user/default/workflows/workflow_a1b2c3d4.json
   ```

**Returns:** `/workspace/ComfyUI/user/default/workflows/workflow_a1b2c3d4.json`

### 5. Queue via BrowserAgent

**Location:** `app/api/create.py` - `_queue_workflow_with_browseragent()`

**Inputs Available:**
```python
workflow_path = "/workspace/ComfyUI/user/default/workflows/workflow_a1b2c3d4.json"
ssh_connection = "ssh -p 40738 root@198.53.64.194 -L 8080:localhost:8080"
host = "198.53.64.194"
port = "40738"
```

**Executed Command:**
```bash
ssh -p 40738 \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=/root/.ssh/known_hosts \
  root@198.53.64.194 \
  'cd ~/BrowserAgent && ./.venv/bin/python examples/comfyui/queue_workflow_ui_click.py --workflow-path /workspace/ComfyUI/user/default/workflows/workflow_a1b2c3d4.json --comfyui-url http://localhost:18188'
```

**BrowserAgent Script Receives:**
- `--workflow-path`: Absolute path to workflow JSON on remote filesystem
- `--comfyui-url`: URL to ComfyUI web interface

**Expected Output Format:**
```
✅ Queued! Prompt ID: 12345678-abcd-1234-5678-123456789abc
```

or

```
SUCCESS
Prompt ID: 12345678-abcd-1234-5678-123456789abc
```

## Testing in Isolation

### Prerequisites on Remote Instance

1. **Files exist:**
   ```bash
   # Check image was uploaded
   ls -lh /workspace/ComfyUI/input/image_d41d8cd98f00b204e9800998ecf8427e.jpeg
   
   # Check workflow was uploaded
   ls -lh /workspace/ComfyUI/user/default/workflows/workflow_a1b2c3d4.json
   
   # Verify workflow content
   cat /workspace/ComfyUI/user/default/workflows/workflow_a1b2c3d4.json | jq '.nodes[0]'
   ```

2. **BrowserAgent installed:**
   ```bash
   # Check BrowserAgent exists
   ls -la ~/BrowserAgent/
   
   # Check script exists
   ls -lh ~/BrowserAgent/examples/comfyui/queue_workflow_ui_click.py
   
   # Check venv
   ls -la ~/BrowserAgent/.venv/bin/python
   ```

3. **ComfyUI running:**
   ```bash
   # Check ComfyUI is accessible
   curl -s http://localhost:18188/ | head -n 5
   
   # Check queue endpoint
   curl -s http://localhost:18188/queue | jq '.'
   ```

### Manual Test Command

**On remote instance via SSH:**
```bash
cd ~/BrowserAgent && \
  ./.venv/bin/python examples/comfyui/queue_workflow_ui_click.py \
  --workflow-path /workspace/ComfyUI/user/default/workflows/workflow_a1b2c3d4.json \
  --comfyui-url http://localhost:18188
```

**Expected behavior:**
1. Script launches Playwright browser (headless)
2. Opens ComfyUI at http://localhost:18188
3. Loads workflow from file path
4. Clicks "Queue Prompt" button
5. Retrieves prompt_id from response
6. Outputs: `✅ Queued! Prompt ID: <uuid>`

### Debug: Check Script Output

**From local machine:**
```bash
ssh -p 40738 root@198.53.64.194 'cd ~/BrowserAgent && ./.venv/bin/python examples/comfyui/queue_workflow_ui_click.py --workflow-path /workspace/ComfyUI/user/default/workflows/workflow_a1b2c3d4.json --comfyui-url http://localhost:18188'
```

**If script fails, check:**

1. **Python environment:**
   ```bash
   ssh -p 40738 root@198.53.64.194 '~/BrowserAgent/.venv/bin/python --version'
   ```

2. **Required packages:**
   ```bash
   ssh -p 40738 root@198.53.64.194 '~/BrowserAgent/.venv/bin/pip list | grep -E "playwright|requests"'
   ```

3. **Playwright browsers installed:**
   ```bash
   ssh -p 40738 root@198.53.64.194 '~/BrowserAgent/.venv/bin/playwright install --help'
   ```

4. **Script exists and is readable:**
   ```bash
   ssh -p 40738 root@198.53.64.194 'cat ~/BrowserAgent/examples/comfyui/queue_workflow_ui_click.py | head -n 20'
   ```

5. **ComfyUI accessibility:**
   ```bash
   ssh -p 40738 root@198.53.64.194 'curl -s http://localhost:18188/queue'
   ```

### Alternative: Test with Simple API Call

If BrowserAgent is not working, you can test direct API queueing:

```bash
ssh -p 40738 root@198.53.64.194 'python3 -c "
import json
import requests

# Load workflow
with open(\"/workspace/ComfyUI/user/default/workflows/workflow_a1b2c3d4.json\") as f:
    workflow = json.load(f)

# Queue via API
response = requests.post(
    \"http://localhost:18188/prompt\",
    json={\"prompt\": workflow, \"client_id\": \"test\"}
)

print(json.dumps(response.json(), indent=2))
"'
```

## Common Issues

### 1. Workflow Path Not Found
**Error:** `FileNotFoundError: /workspace/ComfyUI/user/default/workflows/workflow_a1b2c3d4.json`

**Fix:** Verify upload step completed successfully

### 2. Image Not Found in Workflow
**Error:** ComfyUI error about missing image file

**Fix:** Check that image was uploaded to `/workspace/ComfyUI/input/` before workflow was queued

### 3. BrowserAgent Script Not Found
**Error:** `No such file or directory: ~/BrowserAgent/examples/comfyui/queue_workflow_ui_click.py`

**Fix:** Install BrowserAgent on remote instance or use alternative direct API method

### 4. Playwright Browser Not Installed
**Error:** `Executable doesn't exist at /root/.cache/ms-playwright/chromium-*/chrome-linux/chrome`

**Fix:** 
```bash
ssh -p 40738 root@198.53.64.194 'cd ~/BrowserAgent && ./.venv/bin/playwright install chromium'
```

### 5. Timeout Waiting for ComfyUI
**Error:** `Timeout 60s exceeded`

**Fix:** 
- Check ComfyUI is running: `curl http://localhost:18188`
- Increase timeout in `_queue_workflow_with_browseragent()`
- Check if ComfyUI UI is responsive

## Data Flow Summary

```
User Form Input
    │
    ├─ Base64 Image → Upload to /workspace/ComfyUI/input/ → Filename
    │
    ├─ Flat Inputs → InterpreterAdapter → Nested Inputs
    │
    └─ Nested Inputs + Base Workflow → WorkflowInterpreter → Final Workflow JSON
                                             │
                                             ├─ Upload to /workspace/ComfyUI/user/default/workflows/
                                             │
                                             └─ BrowserAgent Script
                                                    │
                                                    ├─ Load workflow file
                                                    ├─ Click Queue button
                                                    └─ Return prompt_id
```

## Key File Locations

### Local (API Server)
- Workflow configs: `workflows/*.webui.yml`
- Base workflows: `workflows/*.json`
- Temporary files: `/tmp/tmpXXXXXX.*`

### Remote (VastAI Instance)
- Input images: `/workspace/ComfyUI/input/*.jpeg`
- Uploaded workflows: `/workspace/ComfyUI/user/default/workflows/*.json`
- BrowserAgent: `~/BrowserAgent/`
- Queue script: `~/BrowserAgent/examples/comfyui/queue_workflow_ui_click.py`
- ComfyUI: `/workspace/ComfyUI/`

## Next Steps for Debugging

1. **Verify all files exist** on remote before BrowserAgent call
2. **Test BrowserAgent script manually** with known-good workflow
3. **Check script output** for actual error messages
4. **Add verbose logging** to BrowserAgent script
5. **Consider fallback** to direct API queueing if BrowserAgent fails
