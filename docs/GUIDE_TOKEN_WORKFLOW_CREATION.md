# Quick Start: Creating Token-Based Workflows

This guide shows you how to create new token-based workflows for the WebUI.

## Step-by-Step Process

### 1. Export Workflow from ComfyUI

1. Open your workflow in ComfyUI
2. Click **Save** (canvas format) or **Save (API Format)**
3. Prefer **canvas format** for better compatibility
4. Save as `workflows/YOUR_WORKFLOW_NAME.json`

### 2. Add Tokens to Workflow

**Option A: Use the Tokenization Script**

```bash
cd workflows
python3 tokenize_workflow.py
# Edit the script first to add your specific nodes
```

**Option B: Manual Token Addition**

Find the nodes you want to control and replace their values with tokens:

```json
{
  "nodes": [
    {
      "id": 123,
      "type": "LoadImage",
      "widgets_values": [
        "{{INPUT_IMAGE}}",  // ← Replace filename with token
        "image"
      ]
    },
    {
      "id": 456,
      "type": "mxSlider",
      "widgets_values": [
        "{{STEPS}}",  // ← Replace numeric values
        "{{STEPS}}",  // (often need to replace multiple copies)
        1
      ]
    }
  ]
}
```

### 3. Create .webui.yml Configuration

Create `workflows/YOUR_WORKFLOW_NAME.webui.yml`:

```yaml
name: "Your Workflow Name"
description: "What this workflow does"
version: "1.0.0"
category: "video"  # or "image", "text", etc.
workflow_file: "YOUR_WORKFLOW_NAME.json"

layout:
  sections:
    - id: "basic"
      title: "📝 Basic Settings"
      collapsed: false
    - id: "advanced"
      title: "⚙️ Advanced"
      collapsed: true

inputs:
  # Simple text/image input
  - id: "input_image"
    section: "basic"
    token: "{{INPUT_IMAGE}}"
    type: "image"
    label: "Input Image"
    required: true
    accept: "image/png,image/jpeg"
  
  # Numeric slider
  - id: "steps"
    section: "basic"
    token: "{{STEPS}}"
    type: "slider"
    label: "Steps"
    min: 10
    max: 50
    step: 1
    default: 20
  
  # Text prompt
  - id: "prompt"
    section: "basic"
    token: "{{PROMPT}}"
    type: "textarea"
    label: "Prompt"
    default: "Your default prompt here"
    rows: 4
  
  # Random seed
  - id: "seed"
    section: "basic"
    token: "{{SEED}}"
    type: "seed"
    label: "Seed"
    default: -1
  
  # Single model selector
  - id: "checkpoint"
    section: "basic"
    token: "{{CHECKPOINT}}"
    type: "single_model"
    label: "Checkpoint"
    model_type: "checkpoints"
    default: "path/to/default.safetensors"
  
  # High/Low model pair (for WAN workflows)
  - id: "diffusion_model"
    section: "basic"
    type: "high_low_pair_model"
    tokens:
      high: "{{MODEL_HIGH}}"
      low: "{{MODEL_LOW}}"
    label: "Diffusion Model"
    model_type: "diffusion_models"
    default_high: "path/to/high.safetensors"
    default_low: "path/to/low.safetensors"

outputs:
  - id: "result"
    node_id: "123"  # Still need node_id for output identification
    type: "image"
    format: "png"
    label: "Result"
```

### 4. Test Your Workflow

```bash
cd test
python3 test_token_workflow.py
```

Expected output:
```
✓ Loaded: Your Workflow Name v1.0.0
✓ Found N tokens in template
✓ All tokens replaced successfully
```

### 5. Common Token Patterns

**Input/Output**
- `{{INPUT_IMAGE}}` - Image files
- `{{OUTPUT_PATH}}` - Save paths
- `{{FILENAME_PREFIX}}` - Filename prefixes

**Generation Parameters**
- `{{SEED}}` - Random seed
- `{{STEPS}}` - Denoising steps
- `{{CFG}}` - CFG scale
- `{{DENOISE}}` - Denoise strength

**Text**
- `{{POSITIVE_PROMPT}}` - Main prompt
- `{{NEGATIVE_PROMPT}}` - Negative prompt
- `{{STYLE}}` - Style preset

**Dimensions**
- `{{WIDTH}}` - Image width
- `{{HEIGHT}}` - Image height
- `{{SIZE_WIDTH}}`, `{{SIZE_HEIGHT}}` - Alternative naming

**Models**
- `{{CHECKPOINT}}` - Main checkpoint
- `{{VAE_MODEL}}` - VAE
- `{{LORA_1}}` - LoRA models
- `{{UPSCALE_MODEL}}` - Upscaler
- `{{MODEL_HIGH}}`, `{{MODEL_LOW}}` - Paired models

**Advanced**
- `{{SAMPLER}}` - Sampler type
- `{{SCHEDULER}}` - Scheduler
- `{{CLIP_SKIP}}` - CLIP skip
- `{{BATCH_SIZE}}` - Batch size

### 6. Input Types Reference

**type: "image"**
```yaml
- id: "input"
  token: "{{INPUT_IMAGE}}"
  type: "image"
  accept: "image/png,image/jpeg,image/webp"
  max_size_mb: 10
```

**type: "slider"**
```yaml
- id: "parameter"
  token: "{{PARAMETER}}"
  type: "slider"
  min: 0.0
  max: 100.0
  step: 0.1
  default: 50.0
  unit: "%"  # optional
```

**type: "text" / "textarea"**
```yaml
- id: "prompt"
  token: "{{PROMPT}}"
  type: "textarea"
  rows: 4
  max_length: 2000
  placeholder: "Enter your prompt..."
```

**type: "seed"**
```yaml
- id: "seed"
  token: "{{SEED}}"
  type: "seed"
  randomize_button: true
  default: -1
```

**type: "checkbox"**
```yaml
- id: "enable_feature"
  token: "{{ENABLE_FEATURE}}"
  type: "checkbox"
  default: false
```

**type: "dropdown"**
```yaml
- id: "sampler"
  token: "{{SAMPLER}}"
  type: "dropdown"
  options:
    - "euler"
    - "euler_a"
    - "dpm++"
  default: "euler"
```

**type: "single_model"**
```yaml
- id: "checkpoint"
  token: "{{CHECKPOINT}}"
  type: "single_model"
  model_type: "checkpoints"  # or "vae", "loras", "upscale_models"
  default: "path/to/model.safetensors"
```

**type: "high_low_pair_model"**
```yaml
- id: "model_pair"
  type: "high_low_pair_model"
  tokens:
    high: "{{MODEL_HIGH}}"
    low: "{{MODEL_LOW}}"
  model_type: "diffusion_models"
  default_high: "path/to/high.safetensors"
  default_low: "path/to/low.safetensors"
```

### 7. Advanced: Conditional Inputs

Show inputs only when conditions are met:

```yaml
- id: "advanced_mode"
  token: "{{ADVANCED_MODE}}"
  type: "checkbox"
  label: "Enable Advanced Settings"
  default: false

- id: "advanced_param"
  token: "{{ADVANCED_PARAM}}"
  type: "slider"
  label: "Advanced Parameter"
  depends_on:
    field: "advanced_mode"
    value: true
  # ^ Only shows when advanced_mode is checked
```

### 8. Adding Presets

```yaml
presets:
  - name: "Fast"
    description: "Quick generation"
    values:
      steps: 15
      cfg: 7.0
  
  - name: "Quality"
    description: "High quality"
    values:
      steps: 30
      cfg: 10.0
```

## Troubleshooting

### "Token not replaced" error
- Check spelling matches exactly (case-sensitive)
- Verify token exists in workflow JSON
- Token must be in quotes: `"{{TOKEN}}"`

### "Node not found" in output
- Output nodes still use `node_id` not tokens
- Check node ID matches the output node in workflow

### Workflow fails to load
- Validate JSON: `python -m json.tool workflow.json`
- Check `.webui.yml` syntax with YAML validator
- Verify `workflow_file` name matches

## Examples

See `IMG_to_VIDEO_canvas.webui.yml` for a complete, working example.

## Questions?

Check the full documentation: `docs/FEATURE_TOKEN_BASED_WORKFLOW_SYSTEM.md`
