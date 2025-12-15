# Widget Value Mapping - IMG_to_VIDEO_canvas Workflow

## Overview

This document provides a comprehensive mapping of WebUI inputs to workflow node widget values. Based on systematic analysis of sample workflow files and validation through automated tests.

**Test Results**: ✅ All validations passing (13 tests total)
- 6 core validation tests
- 7 widget variation tests

---

## Numeric Input Mappings

All numeric slider inputs in the WebUI update specific nodes in the generated workflow JSON. These nodes are `mxSlider` type with `widgets_values` arrays in the format `[value, value, step]`.

### Input: `cfg` (CFG Scale)
- **Default**: 3.5
- **Range**: 1.0 - 10.0 (step: 0.5)
- **Target Node**: 85 (mxSlider "CFG")
- **Widget Pattern**: `[cfg, cfg, 1]`
- **Example**: Input `cfg=5.0` → Node 85: `[5.0, 5.0, 1]`

### Input: `steps` (Denoising Steps)
- **Default**: 20
- **Range**: 10 - 40 (step: 1)
- **Target Node**: 82 (mxSlider "Steps")
- **Widget Pattern**: `[steps, steps, 0]`
- **Example**: Input `steps=30` → Node 82: `[30.0, 30.0, 0]`

### Input: `duration` (Video Duration)
- **Default**: 5.0
- **Range**: 1.0 - 10.0 (step: 0.5)
- **Unit**: seconds
- **Target Node**: 426 (mxSlider "Duration")
- **Widget Pattern**: `[duration, duration, 1]`
- **Example**: Input `duration=8.0` → Node 426: `[8.0, 8.0, 1]`

### Input: `frame_rate` (Frame Rate)
- **Default**: 16.0
- **Range**: 8 - 60 (step: 1)
- **Unit**: fps
- **Target Node**: 490 (mxSlider "Frame rate")
- **Widget Pattern**: `[frame_rate, frame_rate, 1]`
- **Example**: Input `frame_rate=20.0` → Node 490: `[20.0, 20.0, 1]`

### Input: `speed` (Generation Speed)
- **Default**: 7.0
- **Range**: 1 - 13 (step: 1)
- **Target Node**: 157 (mxSlider "Speed")
- **Widget Pattern**: `[speed, speed, 1]`
- **Example**: Input `speed=10.0` → Node 157: `[10.0, 10.0, 1]`

### Input: `upscale_ratio` (Upscale Ratio)
- **Default**: 2.0
- **Range**: 1.0 - 4.0 (step: 0.1)
- **Target Node**: 421 (mxSlider "Upscale ratio")
- **Widget Pattern**: `[upscale_ratio, upscale_ratio, 1]`
- **Example**: Input `upscale_ratio=1.5` → Node 421: `[1.5, 1.5, 1]`

---

## Single-Value Input Mappings

### Input: `seed` (Random Seed)
- **Default**: -1 (randomize)
- **Target Node**: 73
- **Widget Index**: 0
- **Example**: Input `seed=42` → Node 73: `[42, "randomize"]`

### Input: `positive_prompt`
- **Target Node**: 408
- **Widget Index**: 0
- **Type**: String (textarea)

### Input: `negative_prompt`
- **Target Node**: 409
- **Widget Index**: 0
- **Type**: String (textarea)

### Input: `input_image`
- **Target Node**: 88
- **Widget Index**: 0
- **Type**: String (file path)

### Input: `vram_reduction`
- **Default**: 100
- **Range**: 0 - 100 (percentage)
- **Target Node**: 502
- **Widget Index**: 0

---

## Node Mode Toggle Mappings

Feature toggles in the WebUI control the `mode` property of specific nodes:
- **mode 0**: Enabled (node executes)
- **mode 2**: Disabled (node skipped)
- **mode 4**: Muted (node bypassed)

### Input: `save_last_frame` (default: disabled/2)
- Node 447: SaveImage
- Node 444: ImageFromBatch

### Input: `enable_interpolation` (default: enabled/0)
- Node 431: RIFE VFI
- Node 433: VHS_VideoCombine (interpolated output)

### Input: `use_upscaler` (default: disabled/2)
- Node 385: ImageUpscaleWithModel
- Node 418: ImageScaleBy

### Input: `enable_upscale_interpolation` (default: disabled/2)
- Node 442: RIFE VFI (upscaled)
- Node 443: VHS_VideoCombine (upscaled+interpolated)

### Input: `enable_video_enhancer` (default: enabled/0)
- Node 481: WanVideoEnhanceAVideoKJ (high noise)
- Node 482: WanVideoEnhanceAVideoKJ (low noise)

### Input: `enable_cfg_zero_star` (default: enabled/0)
- Node 483: CFGZeroStarAndInit (high noise)
- Node 484: CFGZeroStarAndInit (low noise)

### Input: `enable_speed_regulation` (default: enabled/0)
- Node 467: ModelSamplingSD3 (high noise)
- Node 468: ModelSamplingSD3 (low noise)

### Input: `enable_normalized_attention` (default: enabled/0)
- Node 485: WanVideoNAG (high noise)
- Node 486: WanVideoNAG (low noise)

### Input: `enable_magcache` (default: enabled/0)
- Node 506: MagCache

### Input: `enable_torch_compile` (default: muted/4)
- Node 492: TorchCompileModelWanVideo (high noise)
- Node 494: TorchCompileModelWanVideo (low noise)

### Input: `enable_block_swap` (default: enabled/0)
- Node 500: wanBlockSwap (high noise)
- Node 501: wanBlockSwap (low noise)

### Input: `enable_auto_prompt` (default: enabled/0)
- Node 473: DownloadAndLoadFlorence2Model
- Node 480: Florence2Run
- Node 474: Text Find and Replace (photo)
- Node 475: Text Find and Replace (image)
- Node 476: Text Find and Replace (painting)
- Node 472: Text Find and Replace (illustration)

---

## Model Path Mappings

Model selection inputs populate `widgets_values[0]` in loader nodes:

### Input: `main_model.highNoisePath`
- **Target Node**: 522 (WAN High Noise Model Loader)
- **Widget Index**: 0

### Input: `main_model.lowNoisePath`
- **Target Node**: 523 (WAN Low Noise Model Loader)
- **Widget Index**: 0

### Input: `clip_model.path`
- **Target Node**: 460 (CLIP Model Loader)
- **Widget Index**: 0

### Input: `vae_model.path`
- **Target Node**: 461 (VAE Loader)
- **Widget Index**: 0

### Input: `upscale_model.path`
- **Target Node**: 384 (Upscale Model Loader)
- **Widget Index**: 0

---

## Validation Test Coverage

### Core Tests (`test_img_to_video_canvas_workflow.py`)
1. ✅ Token Replacements (27 tokens)
2. ✅ Node Mode Toggles (27 nodes)
3. ✅ Model Paths (5 loaders)
4. ✅ Widget Values (11 nodes)
5. ✅ Structure Comparison (85 nodes, 111 links, 16 groups)
6. ✅ Output Save

### Widget Variation Tests (`test_widget_value_variations.py`)
1. ✅ CFG variation (3.5 → 5.0)
2. ✅ Steps variation (20 → 30)
3. ✅ Duration variation (5 → 8)
4. ✅ Frame Rate variation (16 → 20)
5. ✅ Speed variation (7 → 10)
6. ✅ Upscale Ratio variation (2.0 → 1.5)
7. ✅ Multiple simultaneous changes

---

## Sample Files Used for Analysis

The following workflow files were analyzed to determine the mapping:

- `WAN2.2_Img2Video (Original).json` - Baseline with default values
- `WAN2.2_Img2Video(CFGChangedTo5).json` - Node 85 analysis
- `WAN2.2_Img2Video(StepsChangedTo30).json` - Node 82 analysis
- `WAN2.2_Img2Video(DurationChangedTo8Sec).json` - Node 426 analysis
- `WAN2.2_Img2Video(FrameRateChangedTo20).json` - Node 490 analysis
- `WAN2.2_Img2Video(SpeedChangedTo10).json` - Node 157 analysis
- `WAN2.2_Img2Video(UpscaleRatioChangedTo1.5).json` - Node 421 analysis
- Various toggle samples (AutoPrompt, BlockSwap, Interpolation, etc.)

---

## Implementation Details

### Token Replacement System
- Template file: `workflows/IMG_to_VIDEO_canvas.json`
- Configuration: `workflows/IMG_to_VIDEO_canvas.webui.yml`
- Generator: `app/create/workflow_generator.py`

### Widget Value Update Flow
1. User changes input in WebUI
2. WorkflowGenerator receives updated input dictionary
3. Token replacement updates string tokens ({{TOKEN}} → value)
4. Node mode updates set node.mode based on toggle inputs
5. Widget values are set directly in nodes' widgets_values arrays

### mxSlider Widget Pattern
Most numeric sliders use the pattern: `[value, value, step]`
- Index 0: Current value
- Index 1: Current value (duplicate for consistency)
- Index 2: Step size for the slider

**Exception**: Node 82 (Steps) uses `[value, value, 0]` with step=0

---

## Testing Commands

```bash
# Run core validation tests
python3 test/test_img_to_video_canvas_workflow.py

# Run widget variation tests
python3 test/test_widget_value_variations.py

# Run both test suites
python3 test/test_img_to_video_canvas_workflow.py && python3 test/test_widget_value_variations.py
```

---

## Notes for Developers

1. **All numeric inputs validated**: Every slider input in the WebUI has been verified to correctly update its target node's widget values.

2. **Node mode toggles validated**: All 11 feature toggles (controlling 27 nodes total) have been verified.

3. **Model paths validated**: All 5 model loader nodes correctly receive their paths.

4. **Multiple simultaneous changes**: The system correctly handles multiple input changes in a single workflow generation.

5. **Sample file correlation**: All findings have been cross-referenced with actual workflow sample files from the ComfyUI editor.

---

**Last Updated**: 2025-01-XX  
**Test Status**: ✅ All Tests Passing (13/13)  
**Coverage**: 30 inputs, 85 nodes, 27 tokens
