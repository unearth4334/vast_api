# Proposal: "Create" Tab - ComfyUI Workflow Execution UI

## Executive Summary

This proposal outlines the implementation of a new "Create" tab in the Media Sync Tool web UI. This tab will allow users to:
1. Select and connect to VastAI cloud instances
2. Choose from available ComfyUI workflows
3. Fill in workflow-specific input forms
4. Execute workflows on cloud instances by generating filled JSON files and queueing them

---

## Architecture Overview

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Create Tab UI                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ 🖥️ Active VastAI Instances                                             │ │
│  │ [Instance Cards with Connect buttons]                                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ 🔌 Step 1: SSH Connection                                              │ │
│  │ [SSH Connection String Input]                                          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ 🎨 Step 2: Select Workflow                                              │ │
│  │ [Workflow Dropdown/Grid]                                                │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ 📝 Step 3: Configure Inputs                                             │ │
│  │ [Dynamic Form Based on Workflow]                                        │ │
│  │   - Image Upload                                                        │ │
│  │   - Text Prompts                                                        │ │
│  │   - Numeric Sliders                                                     │ │
│  │   - Model Selectors                                                     │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ ▶️ Step 4: Execute                                                       │ │
│  │ [Run Workflow Button]                                                   │ │
│  │ [Progress Indicator]                                                    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ POST /create/execute
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Backend Server                                     │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ create_api.py                                                          │ │
│  │  • /create/workflows/list - List available workflows                   │ │
│  │  • /create/workflows/<name> - Get workflow details                     │ │
│  │  • /create/execute - Execute workflow on instance                      │ │
│  │  • /create/status/<task_id> - Get execution status                    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    │ SSH/SCP                                 │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Workflow Execution                                                     │ │
│  │  1. Generate filled workflow JSON from template + user inputs          │ │
│  │  2. SCP workflow JSON to instance                                      │ │
│  │  3. Queue workflow via ComfyUI API                                     │ │
│  │  4. Monitor execution progress                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Cloud Instance (VastAI)                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ ComfyUI Server                                                         │ │
│  │  • /prompt - Queue workflow                                            │ │
│  │  • /history - Get execution history                                    │ │
│  │  • /queue - Get queue status                                           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## File Structure

### New Files to Create

```
app/
├── sync/
│   └── create_api.py              # New API endpoints for Create tab
├── webui/
│   ├── js/
│   │   └── create/
│   │       ├── create-tab.js      # Main Create tab controller
│   │       ├── workflow-selector.js # Workflow selection component
│   │       ├── form-generator.js   # Dynamic form generator
│   │       └── workflow-runner.js  # Execution and progress tracking
│   └── css/
│       └── create.css              # Create tab styles
docs/
└── workflows/
    ├── IMG_to_VIDEO.json          # Workflow JSON (existing pattern)
    └── IMG_to_VIDEO.webui.yml     # WebUI wrapper specification
```

---

## WebUI Wrapper File Specification

Each workflow JSON file can have a companion `.webui.yml` file that specifies which fields should be exposed in the UI form.

### Format: `<workflow_name>.webui.yml`

```yaml
# docs/workflows/IMG_to_VIDEO.webui.yml

name: "IMG to VIDEO"
description: "Generate video from a single image using WAN Image-to-Video model"
version: "1.0.0"
category: "video"
tags:
  - image-to-video
  - wan
  - video-generation

# Workflow JSON file reference
workflow_file: "IMG to VIDEO.json"

# Thumbnail/preview image (optional)
thumbnail: "IMG_to_VIDEO_preview.png"

# Input fields to expose in UI
inputs:
  # Image input
  - id: "image_input"
    node_id: "88"           # Node ID in workflow JSON
    field: "image"          # Field within node inputs
    type: "image"           # UI component type
    label: "Input Image"
    description: "Source image to animate"
    required: true
    accept: "image/png,image/jpeg,image/webp"
    
  # Text prompt
  - id: "positive_prompt"
    node_id: "408"
    field: "value"
    type: "textarea"
    label: "Positive Prompt"
    description: "Describe what you want the video to show"
    required: true
    default: ""
    placeholder: "cinematic video of..."
    max_length: 2000
    
  # Negative prompt
  - id: "negative_prompt"
    node_id: "409"
    field: "value"
    type: "textarea"
    label: "Negative Prompt"
    description: "Describe what to avoid"
    required: false
    default: "blurry, low quality, static"
    
  # Numeric slider
  - id: "steps"
    node_id: "82"
    field: "Xi"               # And also "Xf" for mxSlider
    type: "slider"
    label: "Steps"
    description: "Number of denoising steps"
    min: 10
    max: 50
    step: 1
    default: 20
    
  # Width/Height 2D slider
  - id: "size"
    node_id: "83"
    type: "size_2d"
    fields:
      width: "Xi"
      height: "Yi"
    label: "Output Size"
    description: "Video dimensions"
    presets:
      - name: "Portrait (896x1120)"
        width: 896
        height: 1120
      - name: "Landscape (1120x896)"
        width: 1120
        height: 896
      - name: "Square (1024x1024)"
        width: 1024
        height: 1024
    default:
      width: 896
      height: 1120
      
  # Float slider
  - id: "cfg"
    node_id: "85"
    field: "Xi"
    type: "slider"
    label: "CFG Scale"
    description: "Classifier-free guidance strength"
    min: 1.0
    max: 10.0
    step: 0.5
    default: 3.5
    
  # Duration
  - id: "duration"
    node_id: "426"
    field: "Xi"
    type: "slider"
    label: "Duration (seconds)"
    description: "Video duration"
    min: 1
    max: 10
    step: 0.5
    default: 5
    
  # Frame rate
  - id: "frame_rate"
    node_id: "490"
    field: "Xi"
    type: "slider"
    label: "Frame Rate"
    description: "Output FPS"
    min: 8
    max: 30
    step: 1
    default: 16
    
  # Seed (special handling)
  - id: "seed"
    node_id: "73"
    field: "noise_seed"
    type: "seed"
    label: "Seed"
    description: "Random seed for reproducibility"
    randomize_button: true
    default: -1    # -1 means random

# Output configuration
outputs:
  - id: "video_output"
    node_id: "398"
    type: "video"
    format: "mp4"
    filename_prefix: "WAN"

# Advanced settings (collapsed by default)
advanced:
  - id: "upscale_ratio"
    node_id: "421"
    field: "Xi"
    type: "slider"
    label: "Upscale Ratio"
    min: 1.0
    max: 4.0
    step: 0.5
    default: 2.0
    
  - id: "speed"
    node_id: "157"
    field: "Xi"
    type: "slider"
    label: "Sampling Speed"
    min: 1.0
    max: 15.0
    step: 0.5
    default: 7.0

# Model requirements (for validation)
requirements:
  models:
    - type: "unet"
      path: "Wan-2.2_ComfyUI_repackaged/wan2.2_t2v_high_noise_14B_fp16.safetensors"
    - type: "clip"
      path: "Wan-2.2/umt5_xxl_fp16.safetensors"
    - type: "vae"
      path: "Wan-2.1/wan_2.1_vae.safetensors"
  custom_nodes:
    - "ComfyUI-VideoHelperSuite"
    - "ComfyUI-KJNodes"
  vram: "24GB recommended"
```

### Input Type Reference

| Type | Description | UI Component |
|------|-------------|--------------|
| `image` | Image upload | File input with preview |
| `text` | Short text | Single-line input |
| `textarea` | Multi-line text | Textarea |
| `slider` | Numeric value | Range slider with input |
| `size_2d` | Width/Height pair | Two sliders or presets |
| `seed` | Random seed | Number input with randomize button |
| `select` | Dropdown selection | Select dropdown |
| `checkbox` | Boolean toggle | Checkbox |
| `model_select` | Model file selection | Dropdown of available models |
| `color` | Color picker | Color input |

---

## Backend API Endpoints

### `/create/workflows/list` (GET)

Lists all available workflows with their metadata.

**Response:**
```json
{
  "success": true,
  "workflows": [
    {
      "id": "img_to_video",
      "name": "IMG to VIDEO",
      "description": "Generate video from a single image",
      "category": "video",
      "tags": ["image-to-video", "wan"],
      "thumbnail": "/workflows/IMG_to_VIDEO_preview.png",
      "has_webui": true
    }
  ]
}
```

### `/create/workflows/<workflow_id>` (GET)

Gets full workflow details including UI configuration.

**Response:**
```json
{
  "success": true,
  "workflow": {
    "id": "img_to_video",
    "name": "IMG to VIDEO",
    "description": "Generate video from a single image",
    "inputs": [...],
    "advanced": [...],
    "requirements": {...},
    "workflow_json": {...}  // The actual ComfyUI workflow
  }
}
```

### `/create/execute` (POST)

Executes a workflow on a cloud instance.

**Request:**
```json
{
  "ssh_connection": "ssh -p 2838 root@104.189.178.116",
  "workflow_id": "img_to_video",
  "inputs": {
    "image_input": "base64_encoded_image_data",
    "positive_prompt": "cinematic video of...",
    "steps": 20,
    "size": { "width": 896, "height": 1120 },
    "seed": 123456789
  }
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Workflow queued successfully"
}
```

### `/create/status/<task_id>` (GET)

Gets execution status.

**Response:**
```json
{
  "success": true,
  "status": "running",
  "progress": {
    "current_node": "KSamplerAdvanced",
    "percent": 45,
    "eta_seconds": 120
  },
  "outputs": null
}
```

---

## Frontend Components

### 1. Create Tab (`create-tab.js`)

Main controller that orchestrates the tab components:

```javascript
class CreateTab {
  constructor() {
    this.workflowSelector = new WorkflowSelector();
    this.formGenerator = new FormGenerator();
    this.workflowRunner = new WorkflowRunner();
  }
  
  async initialize() {
    await this.loadInstances();
    await this.workflowSelector.loadWorkflows();
  }
  
  async onWorkflowSelected(workflowId) {
    const workflow = await this.workflowSelector.getWorkflowDetails(workflowId);
    this.formGenerator.renderForm(workflow.inputs, workflow.advanced);
  }
  
  async onRunClicked() {
    const sshConnection = this.getSshConnection();
    const workflowId = this.workflowSelector.getSelectedWorkflow();
    const inputs = this.formGenerator.getFormValues();
    
    await this.workflowRunner.execute(sshConnection, workflowId, inputs);
  }
}
```

### 2. Workflow Selector (`workflow-selector.js`)

Displays available workflows in a grid/list:

```javascript
class WorkflowSelector {
  async loadWorkflows() {
    const response = await fetch('/create/workflows/list');
    const data = await response.json();
    this.renderWorkflowGrid(data.workflows);
  }
  
  renderWorkflowGrid(workflows) {
    // Render workflow cards with thumbnails
    // Each card shows: name, description, category tags
    // Click to select and load form
  }
}
```

### 3. Form Generator (`form-generator.js`)

Dynamically generates form fields from workflow specification:

```javascript
class FormGenerator {
  renderForm(inputs, advanced) {
    const container = document.getElementById('workflow-inputs');
    container.innerHTML = '';
    
    // Render main inputs
    inputs.forEach(input => {
      const field = this.createField(input);
      container.appendChild(field);
    });
    
    // Render advanced section (collapsed)
    if (advanced && advanced.length > 0) {
      const advancedSection = this.createCollapsibleSection('Advanced', advanced);
      container.appendChild(advancedSection);
    }
  }
  
  createField(input) {
    switch (input.type) {
      case 'image': return this.createImageUpload(input);
      case 'textarea': return this.createTextarea(input);
      case 'slider': return this.createSlider(input);
      case 'size_2d': return this.createSize2D(input);
      case 'seed': return this.createSeedInput(input);
      // ... etc
    }
  }
  
  getFormValues() {
    // Collect all form values into object matching input IDs
  }
}
```

### 4. Workflow Runner (`workflow-runner.js`)

Handles execution and progress tracking:

```javascript
class WorkflowRunner {
  async execute(sshConnection, workflowId, inputs) {
    // Show progress UI
    this.showProgress();
    
    // Start execution
    const response = await fetch('/create/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ssh_connection: sshConnection, workflow_id: workflowId, inputs })
    });
    
    const { task_id } = await response.json();
    
    // Poll for progress
    this.pollProgress(task_id);
  }
  
  async pollProgress(taskId) {
    const interval = setInterval(async () => {
      const response = await fetch(`/create/status/${taskId}`);
      const status = await response.json();
      
      this.updateProgressUI(status);
      
      if (status.status === 'completed' || status.status === 'failed') {
        clearInterval(interval);
        this.handleCompletion(status);
      }
    }, 2000);
  }
}
```

---

## Implementation Phases

### Phase 1: Foundation (2-3 days)
- [ ] Create basic Create tab HTML structure
- [ ] Add tab navigation button
- [ ] Implement SSH connection section (reuse from Resource Manager)
- [ ] Create basic workflow list API endpoint

### Phase 2: Workflow Management (2-3 days)
- [ ] Define webui wrapper YAML format
- [ ] Create example wrapper for "IMG to VIDEO.json"
- [ ] Implement workflow listing endpoint
- [ ] Create workflow selector UI component

### Phase 3: Dynamic Form Generation (3-4 days)
- [ ] Implement form generator for all input types
- [ ] Add image upload with preview
- [ ] Add slider components
- [ ] Add seed input with randomize
- [ ] Implement advanced section toggle

### Phase 4: Execution Engine (3-4 days)
- [ ] Create workflow JSON filler from template + inputs
- [ ] Implement SCP transfer of workflow file
- [ ] Implement ComfyUI API queueing via SSH tunnel
- [ ] Add progress tracking via ComfyUI websocket

### Phase 5: Polish (2 days)
- [ ] Add error handling and validation
- [ ] Implement output preview
- [ ] Add workflow history
- [ ] Testing and bug fixes

**Total Estimated Time: 12-16 days**

---

## Security Considerations

1. **Input Validation**
   - Sanitize all user inputs before including in workflow JSON
   - Validate file uploads (type, size limits)
   - Escape special characters in prompts

2. **SSH Security**
   - Use existing SSH key authentication (no passwords)
   - Validate host keys as per existing implementation
   - Sanitize SSH connection strings

3. **File Handling**
   - Validate uploaded images
   - Limit file sizes
   - Use secure temp file handling

---

## Dependencies

### Existing (Reusable)
- VastAI instance management (from VastAI Setup tab)
- SSH connection handling (`sync_api.py`)
- Background task management (`background_tasks.py`)
- WebSocket progress updates

### New
- ComfyUI API client (for queue/progress)
- YAML parser for webui wrapper files
- Image upload handling

---

## Example Workflow: IMG to VIDEO

Based on the existing `docs/IMG to VIDEO.json`:

**User Flow:**
1. User opens Create tab
2. Selects running VastAI instance
3. Clicks "IMG to VIDEO" workflow card
4. Form appears with:
   - Image upload field
   - Positive/Negative prompt textareas
   - Steps slider (10-50, default 20)
   - Size presets (Portrait/Landscape/Square)
   - CFG slider (1-10, default 3.5)
   - Duration slider (1-10 seconds)
   - Frame rate slider (8-30 FPS)
   - Seed input with "🎲 Randomize" button
5. User fills form and clicks "▶️ Run Workflow"
6. Progress bar shows node execution
7. On completion, video preview appears

---

## Success Criteria

- [ ] User can select a cloud instance
- [ ] User can browse available workflows
- [ ] Dynamic form renders correctly for any workflow
- [ ] Workflow executes successfully on instance
- [ ] Progress is tracked in real-time
- [ ] Errors are handled gracefully
- [ ] Output can be previewed/downloaded

---

## Future Enhancements

1. **Workflow Chaining**: Queue multiple workflows in sequence
2. **Batch Processing**: Run same workflow with different inputs
3. **Template Saving**: Save filled forms as presets
4. **Output Gallery**: View history of generated outputs
5. **Workflow Editor**: Create custom workflows in UI
6. **A/B Testing**: Compare outputs with different parameters

---

## Conclusion

The "Create" tab will provide a user-friendly interface for executing ComfyUI workflows on cloud instances. By using a webui wrapper specification format, any workflow JSON can be made accessible to users through dynamic forms. The implementation leverages existing infrastructure for SSH handling and background tasks while adding new capabilities for workflow management and execution.
