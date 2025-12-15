# IMG_to_VIDEO_canvas Test Suite - Quick Reference

## Running Tests

### Run All Tests
```bash
cd /home/sdamk/dev/vast_api

# Core validation (6 tests)
python3 test/test_img_to_video_canvas_workflow.py

# Widget variations (7 tests)
python3 test/test_widget_value_variations.py

# Both suites
python3 test/test_img_to_video_canvas_workflow.py && \
python3 test/test_widget_value_variations.py
```

## Test Coverage

### Core Test Fixture
**File**: `test/test_img_to_video_canvas_workflow.py`

**Validates**:
- ✅ 27 token replacements
- ✅ 27 node mode toggles
- ✅ 5 model paths
- ✅ 11 widget values (5 simple + 6 numeric sliders)
- ✅ Structure (85 nodes, 111 links, 16 groups)
- ✅ Output file generation

### Widget Variation Tests
**File**: `test/test_widget_value_variations.py`

**Validates**:
- ✅ CFG changes (node 85)
- ✅ Steps changes (node 82)
- ✅ Duration changes (node 426)
- ✅ Frame Rate changes (node 490)
- ✅ Speed changes (node 157)
- ✅ Upscale Ratio changes (node 421)
- ✅ Multiple simultaneous changes

## Quick Node Reference

### Numeric Sliders (widgets_values pattern: `[value, value, step]`)
```
Input          Node  Title          Pattern
cfg            85    CFG            [cfg, cfg, 1]
steps          82    Steps          [steps, steps, 0]
duration       426   Duration       [duration, duration, 1]
frame_rate     490   Frame rate     [frame_rate, frame_rate, 1]
speed          157   Speed          [speed, speed, 1]
upscale_ratio  421   Upscale ratio  [ratio, ratio, 1]
```

### Single-Value Widgets (widgets_values[0])
```
Input            Node  Description
seed             73    Random seed
positive_prompt  408   Positive prompt text
negative_prompt  409   Negative prompt text
input_image      88    Input image path
vram_reduction   502   VRAM reduction %
```

### Model Loaders (widgets_values[0])
```
Input                      Node  Model Type
main_model.highNoisePath   522   WAN High Noise
main_model.lowNoisePath    523   WAN Low Noise
clip_model.path            460   CLIP
vae_model.path             461   VAE
upscale_model.path         384   Upscale
```

### Toggle Nodes (mode: 0=enabled, 2=disabled, 4=muted)
```
Input                        Nodes        Mode
save_last_frame              447, 444     2
enable_interpolation         431, 433     0
use_upscaler                 385, 418     2
enable_upscale_interpolation 442, 443     2
enable_video_enhancer        481, 482     0
enable_cfg_zero_star         483, 484     0
enable_speed_regulation      467, 468     0
enable_normalized_attention  485, 486     0
enable_magcache              506          0
enable_torch_compile         492, 494     4
enable_block_swap            500, 501     0
enable_auto_prompt           473, 480,    0
                             474, 475,
                             476, 472
```

## Documentation Files

### Main Documentation
- **[TEST_WIDGET_VALUE_MAPPING.md](TEST_WIDGET_VALUE_MAPPING.md)** - Complete input→node mapping
- **[SUMMARY_TEST_FIXTURE_ENHANCEMENT.md](SUMMARY_TEST_FIXTURE_ENHANCEMENT.md)** - Enhancement summary
- **[TEST_QUICK_REFERENCE.md](TEST_QUICK_REFERENCE.md)** - This file

### Related Docs
- [GUIDE_TOKEN_WORKFLOW_CREATION.md](GUIDE_TOKEN_WORKFLOW_CREATION.md) - Token system guide
- [TESTING.md](TESTING.md) - General testing documentation

## Sample Files Location

Sample workflow files used for validation:
```
test/samples/WAN2.2_Img2Video (Original).json
test/samples/WAN2.2_Img2Video(CFGChangedTo5).json
test/samples/WAN2.2_Img2Video(StepsChangedTo30).json
test/samples/WAN2.2_Img2Video(DurationChangedTo8Sec).json
... (19 files total)
```

## Expected Test Output

### ✅ Success
```
Results: 6/6 tests passed
🎉 All tests passed!

Results: 7/7 tests passed
🎉 All widget variation tests passed!
```

### ❌ Failure Examples
```
✗ Node 85: [5.0, 5.0, 1] (expected [3.5, 3.5, 1]) - CFG slider
✗ Node 447: mode=0 (expected 2) - SaveImage - save_last_frame
```

## Troubleshooting

### Test Failures
1. Check workflow template: `workflows/IMG_to_VIDEO_canvas.json`
2. Check configuration: `workflows/IMG_to_VIDEO_canvas.webui.yml`
3. Verify generator: `app/create/workflow_generator.py`

### Missing Node IDs
If node IDs don't match:
- Canvas format may have changed
- Nodes may have been added/removed
- Check against latest sample files

### Token Not Replaced
- Verify token exists in template: `grep "{{TOKEN}}" workflows/IMG_to_VIDEO_canvas.json`
- Check webui.yml has matching token definition
- Ensure generator processes the token type

## Adding New Tests

### For New Numeric Input
1. Add to `workflows/IMG_to_VIDEO_canvas.webui.yml`
2. Add token to template JSON
3. Generate sample with changed value
4. Identify node ID with `jq` comparison
5. Add to `numeric_slider_checks` in test fixture
6. Add variation test case

### For New Toggle
1. Add to webui.yml
2. Identify affected nodes
3. Add to `node_mode_checks` in test fixture
4. Generate sample with toggle disabled/enabled

## CI/CD Integration

### Pre-commit Hook
```bash
#!/bin/bash
python3 test/test_img_to_video_canvas_workflow.py || exit 1
python3 test/test_widget_value_variations.py || exit 1
```

### GitHub Actions
```yaml
- name: Run Workflow Tests
  run: |
    python3 test/test_img_to_video_canvas_workflow.py
    python3 test/test_widget_value_variations.py
```

---

**Status**: ✅ All Tests Passing (13/13)  
**Coverage**: 30/30 Inputs (100%)  
**Last Validated**: 2025-01-XX
