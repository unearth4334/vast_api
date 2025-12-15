# Workflow Test Fixtures

This directory contains comprehensive test fixtures for validating ComfyUI workflow generation.

## Overview

The workflow generation system uses a **token-based replacement** approach where:
1. Template workflow JSON files contain tokens like `{{POSITIVE_PROMPT}}`
2. The WebUI YAML configuration maps UI inputs to these tokens
3. The WorkflowGenerator replaces tokens with user-provided values
4. Node mode toggles are applied to enable/disable workflow features

## Test Files

### `test_img_to_video_canvas_workflow.py`

Comprehensive test fixture for the IMG_to_VIDEO_canvas workflow that validates:

#### 1. Token Replacements
Verifies all tokens in the template are correctly replaced with test values:
- Text fields (prompts, filenames)
- Numeric values (dimensions, steps, CFG, etc.)
- Model paths (high/low noise pairs, CLIP, VAE, upscale)
- Seed values (with random generation support)

#### 2. Node Mode Toggles
Validates that node `mode` fields are set correctly based on UI toggles:
- `mode: 0` = enabled/active
- `mode: 2` = disabled/bypassed  
- `mode: 4` = muted/inactive

Tests coverage of all toggle features:
- Save Last Frame (nodes 447, 444)
- Frame Interpolation (nodes 431, 433)
- Upscaler (nodes 385, 418)
- Upscale + Interpolation (nodes 442, 443)
- Video Enhancer (nodes 481, 482)
- CFG Zero Star (nodes 483, 484)
- Speed Regulation (nodes 467, 468)
- Normalized Attention (nodes 485, 486)
- MagCache (node 506)
- TorchCompile (nodes 492, 494)
- Block Swap (nodes 500, 501)
- Automatic Prompting (nodes 473, 480, 474, 475, 476, 472)

#### 3. Model Path Verification
Confirms model paths are inserted in the correct nodes:
- Node 522: High noise model
- Node 523: Low noise model
- Node 460: CLIP model
- Node 461: VAE model
- Node 384: Upscale model

#### 4. Widget Value Verification
Checks that widget values in nodes match expected test inputs:
- Node 408: Positive prompt
- Node 409: Negative prompt
- Node 88: Input image
- Node 157: Speed slider
- Node 73: Seed value
- Node 502: VRAM reduction percentage

#### 5. Structure Comparison
Compares generated workflow structure with example output:
- Node count
- Link count
- Group count

#### 6. Output Generation
Saves the generated workflow to `test/output/` for manual inspection.

## Running Tests

### Run all tests:
```bash
cd /home/sdamk/dev/vast_api
python3 test/test_img_to_video_canvas_workflow.py
```

### Expected Output:
```
================================================================================
IMG_to_VIDEO_canvas Workflow Test Fixture
================================================================================

1. Loading workflow configuration...
   ✓ Config loaded: IMG to VIDEO (Canvas)
   ✓ Inputs: 29

2. Loading workflow template...
   ✓ Template loaded
   ✓ Format: Canvas (85 nodes)
   ✓ Tokens found: 27

3. Creating workflow generator...
   ✓ Generator initialized

4. Generating workflow from test inputs...
   ✓ Workflow generated successfully

5. Verifying token replacements...
   ✓ All tokens replaced successfully
   ✓ positive prompt replaced correctly
   ...

6. Verifying node mode toggles...
   ✓ Node 447: mode=2 - SaveImage - save_last_frame
   ...

================================================================================
TEST SUMMARY
================================================================================
✓ PASS: Token Replacements
✓ PASS: Node Mode Toggles
✓ PASS: Model Paths
✓ PASS: Widget Values
✓ PASS: Structure Comparison
✓ PASS: Output Save

Results: 6/6 tests passed
🎉 All tests passed!
```

## Test Coverage

The test fixture validates the complete workflow generation pipeline:

### Input Processing
- ✅ Basic text inputs (prompts)
- ✅ Image uploads
- ✅ Numeric sliders (dimensions, steps, CFG, etc.)
- ✅ Seed generation and randomization
- ✅ Model selection (high/low pairs + single models)
- ✅ Node mode toggles (enable/disable features)

### Token Replacement
- ✅ String tokens with JSON escaping
- ✅ Numeric tokens (int and float)
- ✅ Model path tokens
- ✅ Seed tokens with -1 random handling
- ✅ Duplicate token replacement (same value in multiple places)

### Node Modifications
- ✅ Node mode changes (enable/disable/mute)
- ✅ Widget value updates
- ✅ Model path insertion
- ✅ Preservation of node structure and links

### Output Validation
- ✅ No unreplaced tokens remain
- ✅ All expected values present
- ✅ Node modes match configuration
- ✅ Structure matches template
- ✅ Valid JSON output

## Using This as a Template

To create tests for other workflows:

1. **Copy the test file:**
   ```bash
   cp test/test_img_to_video_canvas_workflow.py test/test_my_workflow.py
   ```

2. **Update the workflow ID:**
   ```python
   self.workflow_id = "my_workflow_name"
   ```

3. **Update test inputs:**
   Modify `get_test_inputs()` to match your workflow's inputs from the `.webui.yml` file.

4. **Update verification checks:**
   - Update `node_mode_checks` with your workflow's toggle node IDs
   - Update `model_checks` with your workflow's model loader node IDs
   - Update `widget_checks` with nodes you want to verify

5. **Run the tests:**
   ```bash
   python3 test/test_my_workflow.py
   ```

## Debugging Failed Tests

### Token Not Replaced
If you see unreplaced tokens like `{{MY_TOKEN}}`:

1. Check the `.webui.yml` file has the correct token defined:
   ```yaml
   - id: "my_input"
     token: "{{MY_TOKEN}}"
   ```

2. Verify the token exists in the workflow JSON:
   ```bash
   grep "MY_TOKEN" workflows/my_workflow.json
   ```

3. Ensure test inputs include a value for the input:
   ```python
   "my_input": "test_value"
   ```

### Node Mode Incorrect
If node modes don't match expectations:

1. Check the `.webui.yml` configuration for the toggle:
   ```yaml
   - id: "my_toggle"
     type: "node_mode_toggle"
     node_ids:
       - "123"  # Node to control
     default: 0  # Default mode
   ```

2. Verify test input provides the correct mode value:
   ```python
   "my_toggle": 0  # or 2 for disabled, 4 for muted
   ```

3. Check node exists in the workflow template:
   ```bash
   grep '"id": 123' workflows/my_workflow.json
   ```

### Widget Value Mismatch
If widget values aren't correct:

1. Verify the node ID and widget index:
   ```bash
   # Find the node and check widgets_values array
   grep -A 20 '"id": 408' workflows/my_workflow.json
   ```

2. Check token is in the correct position:
   ```json
   "widgets_values": [
     "{{MY_TOKEN}}",  // Index 0
     "other_value"    // Index 1
   ]
   ```

3. Ensure input type matches token replacement logic:
   - Text: `_replace_text_token()`
   - Numbers: `_replace_numeric_token()`
   - Models: `_replace_single_model_token()` or `_replace_high_low_model_tokens()`

## Related Documentation

- **Token System Overview:** `docs/FEATURE_TOKEN_BASED_WORKFLOW_SYSTEM.md`
- **Creating Token Workflows:** `docs/GUIDE_TOKEN_WORKFLOW_CREATION.md`
- **Workflow Generator Code:** `app/create/workflow_generator.py`
- **Workflow Loader Code:** `app/create/workflow_loader.py`

## Continuous Integration

These tests should be run:
- Before committing workflow template changes
- After modifying workflow generation logic
- When adding new workflow features
- As part of CI/CD pipeline

Exit code:
- `0` = All tests passed
- `1` = Some tests failed

## Test Output

Generated workflows are saved to:
```
test/output/{workflow_id}_generated.json
```

You can:
1. Load this file in ComfyUI to verify it works
2. Compare it with the example output
3. Use it for debugging specific issues

## Future Enhancements

Potential improvements to the test suite:

- [ ] Test random seed generation (-1 handling)
- [ ] Test conditional inputs (depends_on logic)
- [ ] Test LoRA list handling
- [ ] Test validation errors and edge cases
- [ ] Test with actual ComfyUI execution
- [ ] Performance benchmarks
- [ ] Test multiple input variations automatically
- [ ] Integration with pytest framework
