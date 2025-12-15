# Workflow Extensibility - Quick Start Guide

**Quick guide for using the enhanced workflow configuration system**

---

## Table of Contents
1. [Basic Usage (No Changes Required)](#basic-usage)
2. [Adding Metadata to Inputs](#adding-metadata)
3. [Enabling Validation](#enabling-validation)
4. [Running Validation](#running-validation)
5. [Common Patterns](#common-patterns)
6. [Troubleshooting](#troubleshooting)

---

## Basic Usage (No Changes Required) {#basic-usage}

**Good news**: Your existing workflows work exactly as before! The enhancements are optional.

```yaml
# This still works perfectly fine
- id: "my_slider"
  section: "generation"
  token: "{{MY_VALUE}}"
  type: "slider"
  min: 0
  max: 100
  default: 50
```

---

## Adding Metadata to Inputs {#adding-metadata}

Metadata makes your configuration self-documenting and enables validation.

### Pattern 1: Simple Slider

```yaml
- id: "cfg"
  section: "generation"
  token: "{{CFG}}"
  type: "slider"
  min: 1.0
  max: 10.0
  default: 3.5
  # Add metadata (optional)
  metadata:
    widget_type: "mxSlider"               # Node type in template
    widget_pattern: "[value, value, step]" # Pattern for documentation
    widget_indices: [0, 1]                # Which indices are modified
    target_nodes:
      - node_id: "85"                     # Node affected by this input
        description: "KSampler CFG parameter"
```

**Benefits**:
- ✅ Documents which node is affected
- ✅ Shows widget value pattern
- ✅ Enables validation
- ✅ Better error messages

### Pattern 2: Coupled Inputs (2D Slider)

When two inputs affect the same node:

```yaml
- id: "size_x"
  section: "generation"
  token: "{{SIZE_WIDTH}}"
  type: "slider"
  min: 512
  max: 1920
  default: 896
  metadata:
    widget_type: "mxSlider2D"
    widget_pattern: "[width, width, height, height, 0, 0]"
    widget_indices: [0, 1]      # Width uses indices 0-1
    coupled_with: "size_y"      # Paired with height
    target_nodes:
      - node_id: "83"
        description: "EmptyLatentImage size"

- id: "size_y"
  section: "generation"
  token: "{{SIZE_HEIGHT}}"
  type: "slider"
  min: 512
  max: 1920
  default: 512
  metadata:
    widget_type: "mxSlider2D"
    widget_pattern: "[width, width, height, height, 0, 0]"
    widget_indices: [2, 3]      # Height uses indices 2-3
    coupled_with: "size_x"      # Paired with width
    target_nodes:
      - node_id: "83"
        description: "EmptyLatentImage size"
```

**Benefits**:
- ✅ Explicit coupling relationship
- ✅ Documents shared node
- ✅ Shows index allocation

### Pattern 3: Multi-Node Input

When one input affects multiple nodes:

```yaml
- id: "enable_feature"
  section: "features"
  type: "node_mode_toggle"
  node_ids: ["123", "456", "789"]
  default: 0
  metadata:
    target_nodes:
      - node_id: "123"
        description: "Feature processor"
      - node_id: "456"
        description: "Feature output"
      - node_id: "789"
        description: "Feature cleanup"
```

### Pattern 4: Complex Structure (LoRA)

For complex widget structures:

```yaml
- id: "loras"
  section: "models"
  type: "high_low_pair_lora_list"
  node_ids: ["416", "471"]
  metadata:
    target_nodes:
      - node_id: "416"
        description: "High noise LoRA loader"
      - node_id: "471"
        description: "Low noise LoRA loader"
    structure:
      data_index: 2  # LoRA data at widgets_values[2]
      format:
        on: boolean
        lora: string
        strength: float
        strengthTwo: null
      empty_state: {}
```

---

## Enabling Validation {#enabling-validation}

Add a validation section to your workflow YAML:

```yaml
# At the top of your workflow YAML, after time_estimate

validation:
  strict_mode: false      # If true, errors prevent workflow generation
  check_tokens: true      # Verify tokens in inputs exist in template
  check_node_ids: true    # Verify node_ids exist in template
  check_widgets: false    # Validate widget structures (strict)
  warn_on_mismatch: true  # Warn instead of error on validation failures
```

**Recommended Settings**:

**Development** (permissive):
```yaml
validation:
  strict_mode: false
  check_tokens: true
  check_node_ids: true
  check_widgets: false
  warn_on_mismatch: true
```

**Production** (strict):
```yaml
validation:
  strict_mode: true
  check_tokens: true
  check_node_ids: true
  check_widgets: true
  warn_on_mismatch: false
```

---

## Running Validation {#running-validation}

### Command Line

```bash
cd /path/to/vast_api
python3 scripts/validate_workflow.py
```

### Programmatic

```python
from app.create.workflow_validator import TemplateValidator

# Validate by workflow ID
result = TemplateValidator.validate_workflow_file("IMG_to_VIDEO_canvas")

if result.is_valid:
    print("✅ Validation passed")
else:
    print("❌ Validation failed")
    for error in result.errors:
        print(f"   • {error}")

if result.has_warnings:
    print("⚠️  Warnings:")
    for warning in result.warnings:
        print(f"   • {warning}")
```

### Output Example

```
================================================================================
WORKFLOW CONFIGURATION VALIDATION
================================================================================

Loading workflow: IMG_to_VIDEO_canvas

✅ Workflow loaded: IMG to VIDEO (Canvas) v3.0.0
   Inputs: 30
   Outputs: 1

📋 Validation Configuration:
   Check Tokens: True
   Check Node IDs: True

Inputs with metadata: 4/30

✅ Template loaded
   Nodes: 85
   Links: 111

🔍 Running validation...

ℹ️  Input 'cfg': Token {{CFG}} found 2 time(s)
ℹ️  Input 'cfg': Node 85 (mxSlider) found
...

Token validation complete: 18 token(s) checked
Node ID validation complete: 30 node(s) checked

✅ Validation PASSED
```

---

## Common Patterns {#common-patterns}

### Widget Patterns Reference

Different node types have different widget_values patterns:

```yaml
# Regular Slider (mxSlider)
widget_pattern: "[value, value, step]"
widget_indices: [0, 1]

# 2D Slider (mxSlider2D)
widget_pattern: "[width, width, height, height, 0, 0]"
widget_indices: [0, 1]  # for width
widget_indices: [2, 3]  # for height

# Text Input (PrimitiveStringMultiline)
widget_pattern: "[text]"
widget_indices: [0]

# Seed (RandomNoise)
widget_pattern: "[seed, 'randomize']"
widget_indices: [0]

# Image Input (LoadImage)
widget_pattern: "[filename, 'image']"
widget_indices: [0]

# Model Selector (UNETLoader)
widget_pattern: "[model_path]"
widget_indices: [0]
```

### Metadata Templates

**Copy-paste ready templates**:

#### Numeric Slider
```yaml
metadata:
  widget_type: "mxSlider"
  widget_pattern: "[value, value, step]"
  widget_indices: [0, 1]
  target_nodes:
    - node_id: "NODE_ID"
      description: "Description"
```

#### Text Input
```yaml
metadata:
  widget_type: "PrimitiveStringMultiline"
  widget_pattern: "[text]"
  widget_indices: [0]
  target_nodes:
    - node_id: "NODE_ID"
      description: "Description"
```

#### Toggle (Node Mode)
```yaml
metadata:
  target_nodes:
    - node_id: "NODE_ID_1"
      description: "Description 1"
    - node_id: "NODE_ID_2"
      description: "Description 2"
```

#### Model Selector
```yaml
metadata:
  widget_type: "UNETLoader"
  widget_pattern: "[model_path]"
  widget_indices: [0]
  target_nodes:
    - node_id: "NODE_ID"
      description: "Description"
```

---

## Troubleshooting {#troubleshooting}

### Issue 1: Token Not Found

**Error**:
```
❌ Input 'my_slider': Token {{MY_VALUE}} not found in template
```

**Solution**:
1. Check token spelling in YAML (case-sensitive!)
2. Search template JSON for the token
3. Ensure token is properly wrapped: `"{{TOKEN}}"`

### Issue 2: Node ID Not Found

**Error**:
```
❌ Input 'my_toggle': Node ID '999' not found in template
```

**Solution**:
1. Open template JSON and verify node ID exists
2. Check if node ID is a string (not number) in YAML
3. Ensure node wasn't removed from template

### Issue 3: Widget Type Mismatch

**Warning**:
```
⚠️  Input 'my_slider': Node 85 type mismatch - expected 'mxSlider', got 'KSampler'
```

**Solution**:
1. Update metadata.widget_type to match actual node type
2. Or update template to use expected node type
3. This is usually just a documentation issue

### Issue 4: Validation Not Running

**Problem**: Validation script shows "No validation configuration"

**Solution**:
Add validation section to YAML:
```yaml
validation:
  check_tokens: true
  check_node_ids: true
```

### Issue 5: Metadata Not Loading

**Problem**: Scripts shows "Inputs with metadata: 0/30"

**Solution**:
Check YAML indentation:
```yaml
# WRONG (metadata at root level)
- id: "cfg"
  token: "{{CFG}}"
metadata:
  widget_type: "mxSlider"

# CORRECT (metadata indented under input)
- id: "cfg"
  token: "{{CFG}}"
  metadata:
    widget_type: "mxSlider"
```

---

## Best Practices

### 1. Start Simple
- Add metadata to critical inputs first
- Enable validation in development
- Test thoroughly before strict mode

### 2. Document Relationships
- Always document coupled inputs
- List all target nodes
- Include helpful descriptions

### 3. Validate Regularly
```bash
# Run before committing changes
python3 scripts/validate_workflow.py
```

### 4. Keep It Optional
- Don't force metadata on every input
- Add metadata where it adds value
- Focus on complex inputs first

### 5. Use Consistent Patterns
- Follow widget pattern conventions
- Use standard descriptions
- Keep node_id format consistent

---

## Migration Guide

### Adding Metadata to Existing Workflow

**Step 1**: Find which nodes an input affects
```bash
# Search template for token
grep "{{MY_TOKEN}}" workflows/my_workflow.json
```

**Step 2**: Add metadata section
```yaml
- id: "my_input"
  token: "{{MY_TOKEN}}"
  # ... existing fields ...
  metadata:
    target_nodes:
      - node_id: "NODE_ID_FROM_GREP"
        description: "What this node does"
```

**Step 3**: Run validation
```bash
python3 scripts/validate_workflow.py
```

**Step 4**: Fix any issues reported

---

## Summary

**Quick Wins**:
1. ✅ Add metadata to complex inputs
2. ✅ Enable validation in development
3. ✅ Run validation script regularly
4. ✅ Document coupled inputs
5. ✅ Use consistent patterns

**Remember**:
- Metadata is optional
- Start simple
- Add incrementally
- Test thoroughly

**Need Help?**
- Check examples in `IMG_to_VIDEO_canvas.webui.yml`
- Read `FEATURE_WORKFLOW_EXTENSIBILITY.md`
- Review `REVIEW_MAPPING_SCHEME_EXTENSIBILITY.md`

---

**Ready to enhance your workflows!** 🚀
