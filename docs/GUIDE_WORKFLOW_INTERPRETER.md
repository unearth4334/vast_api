# Quick Start: Using the Workflow Interpreter

## Overview

The workflow generation system now uses an **action-based interpreter** that reads `node_mapping` from webui.yml files to modify workflows.

## Basic Workflow

1. **User fills out form** → UI collects flat inputs
2. **InterpreterAdapter converts** → Nested format (basic_settings, generation_parameters, etc.)
3. **Interpreter generates actions** → Based on node_mapping in webui.yml
4. **Actions applied to workflow** → Modified workflow JSON returned

## Action Types

### 1. modify_widget
Modifies a single widget value (sliders, text fields, etc.)

```yaml
duration:
  node_id: 426
  action_type: modify_widget
  target_index: 0  # Which value in widgets_values array
```

### 2. toggle_node_mode
Enables/disables a node (mode 0 = active, mode 2+ = disabled)

```yaml
enable_interpolation:
  node_id: 433
  action_type: toggle_node_mode
```

### 3. modify_vector_widget
Modifies multiple values in a widget (e.g., 2D sliders)

```yaml
size:
  node_id: 428
  action_type: modify_vector_widget
  coupled_params:
    - param: size_x
      index: 0
    - param: size_y
      index: 1
```

### 4. add_lora_pair
Adds LoRA model pairs to the workflow

```yaml
loras:
  action_type: add_lora_pair
  high_noise_node_id: 515
  low_noise_node_id: 516
  strength_node_id: 517  # Optional
```

## Input Sections

UI inputs are organized into 4 sections:

- **basic_settings**: Core inputs (prompts, seed, input_image)
- **generation_parameters**: Generation controls (steps, CFG, duration, size)
- **model_selection**: Models and LoRAs
- **advanced_features**: Optional enhancements
  - output_enhancement
  - quality_enhancements
  - performance_memory
  - automatic_prompting

## Creating a New Workflow

1. **Export workflow** from ComfyUI (save as `workflows/MY_WORKFLOW.json`)

2. **Create webui.yml** (`workflows/MY_WORKFLOW.webui.yml`):

```yaml
name: "My Workflow"
description: "Description here"
version: "1.0.0"
category: "generation"
workflow_file: "workflows/MY_WORKFLOW.json"

# Define inputs
inputs:
  - id: my_slider
    type: slider
    label: "My Slider"
    section: "basic"
    min: 0
    max: 100
    default: 50

# Map inputs to nodes
node_mapping:
  my_slider:
    node_id: 123
    action_type: modify_widget
    target_index: 0
```

3. **Test with interpreter**:

```python
from app.create.interpreter_adapter import InterpreterAdapter
from pathlib import Path

adapter = InterpreterAdapter('MY_WORKFLOW', Path('workflows/MY_WORKFLOW.webui.yml'))
workflow = adapter.generate({'my_slider': 75})
```

## Node Mode Values

When using `toggle_node_mode`:
- UI checkbox checked → `node.mode = 0` (active)
- UI checkbox unchecked → `node.mode = 2` or `4` (disabled)
  - Mode 2 = bypassed (node skipped)
  - Mode 4 = muted (node disabled)

In webui.yml, use `node_mode_toggle` type:

```yaml
inputs:
  - id: enable_feature
    type: node_mode_toggle
    label: "Enable Feature"
    default: 0  # 0 = enabled, 2 = bypassed, 4 = muted
```

## Finding Node IDs

1. Open workflow in ComfyUI
2. Right-click node → "Copy Node ID"
3. Or inspect the JSON:

```json
{
  "nodes": [
    {
      "id": 426,  // ← This is the node_id
      "title": "Duration",
      "type": "mxSlider",
      "widgets_values": [120, 120, 1]
    }
  ]
}
```

## Testing Your Workflow

Use the test script:

```bash
python test_interpreter.py
```

Or write a custom test:

```python
ui_inputs = {
    'my_param': 50,
    'enable_feature': 0,
}

adapter = InterpreterAdapter('MY_WORKFLOW', Path('workflows/MY_WORKFLOW.webui.yml'))
workflow = adapter.generate(ui_inputs)

# Check results
print(f"Generated {len(workflow['nodes'])} nodes")
```

## API Endpoints

The interpreter is automatically used by these endpoints:

- `POST /create/generate-workflow` - Generate workflow JSON
- `POST /create/execute` - Execute on remote instance

No API changes needed - the adapter handles everything internally.

## Common Patterns

### Coupled Parameters (2D sliders)
```yaml
size:
  node_id: 428
  action_type: modify_vector_widget
  coupled_params:
    - param: size_x
      index: 0
    - param: size_y
      index: 1
```

### Model Pairs (high/low noise)
```yaml
inputs:
  - id: main_model
    type: high_low_pair_model_selector
    model_type: checkpoints

node_mapping:
  main_model:
    high_noise_node_id: 123
    low_noise_node_id: 124
    action_type: modify_widget
```

### LoRA Lists
```yaml
inputs:
  - id: loras
    type: high_low_pair_lora_selector

node_mapping:
  loras:
    action_type: add_lora_pair
    high_noise_node_id: 515
    low_noise_node_id: 516
```

## Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

The interpreter logs:
- Action generation: "Generated X actions"
- Action application: "Applying ModifyWidgetAction to node X"
- Workflow loading: "Loading workflow: path/to/workflow.json"

## Migration from Token System

Old system (deprecated):
```yaml
inputs:
  - id: duration
    token: "{{DURATION}}"
```

New system:
```yaml
inputs:
  - id: duration
    # No token needed

node_mapping:
  duration:
    node_id: 426
    action_type: modify_widget
    target_index: 0
```

The `WorkflowGenerator` class is deprecated but still exists for reference.

## Example: Full Workflow Config

See [IMG_to_VIDEO_canvas.webui.yml](../workflows/IMG_to_VIDEO_canvas.webui.yml) for a complete working example with:
- 27 inputs across 4 sections
- All 4 action types
- Model pairs and LoRA lists
- Toggle nodes for optional features
