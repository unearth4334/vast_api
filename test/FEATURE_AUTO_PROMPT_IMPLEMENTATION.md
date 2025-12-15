# Automatic Prompting Feature - Implementation Summary

## Overview

Added a toggle control for **Automatic Prompting** using Florence2 AI to the IMG_to_VIDEO_canvas workflow. This feature automatically generates descriptive prompts from the input image to enhance video generation.

## What Was Added

### WebUI Configuration

**File:** `workflows/IMG_to_VIDEO_canvas.webui.yml`

New input in the "Advanced Features" section:

```yaml
- id: "enable_auto_prompt"
  section: "features"
  node_ids:
    - "473"  # DownloadAndLoadFlorence2Model
    - "480"  # Florence2Run
    - "474"  # Text Find and Replace (photo -> video)
    - "475"  # Text Find and Replace (image -> video)
    - "476"  # Text Find and Replace (painting -> video)
    - "472"  # Text Find and Replace (illustration -> video)
  type: "node_mode_toggle"
  label: "Automatic Prompting (Florence2)"
  description: "Enable Florence2 AI to automatically generate descriptive prompts from the input image. When enabled, generates and enhances prompts automatically."
  required: false
  default: 0  # mode: 0 = enabled
```

## How It Works

### When Enabled (mode: 0)
1. **Node 473** loads the Florence2 model
2. **Node 480** analyzes the input image and generates a detailed caption
3. **Nodes 474-476, 472** process the generated text, replacing static image terms with video terms:
   - "photo" → "video"
   - "image" → "video"
   - "painting" → "video"
   - "illustration" → "video"
4. The processed caption is concatenated with the user's prompt

### When Disabled (mode: 4)
All Florence2 and text processing nodes are muted, using only the user-provided prompt.

## Nodes Controlled

| Node ID | Type | Purpose |
|---------|------|---------|
| 473 | DownloadAndLoadFlorence2Model | Loads Florence2 AI model |
| 480 | Florence2Run | Generates caption from image |
| 474 | Text Find and Replace | Replaces "photo" with "video" |
| 475 | Text Find and Replace | Replaces "image" with "video" |
| 476 | Text Find and Replace | Replaces "painting" with "video" |
| 472 | Text Find and Replace | Replaces "illustration" with "video" |

## Test Coverage

Updated test fixture validates:
- ✅ Toggle appears in configuration (30 inputs total)
- ✅ All 6 nodes have correct mode when enabled (mode: 0)
- ✅ All 6 nodes have correct mode when disabled (mode: 4)
- ✅ No interference with other toggles or tokens

### Test Results

```bash
cd /home/sdamk/dev/vast_api
python3 test/test_img_to_video_canvas_workflow.py
```

**Status:** ✅ All tests passing (6/6)

New test validations:
- Node 473: mode=0 ✓
- Node 480: mode=0 ✓
- Node 474: mode=0 ✓
- Node 475: mode=0 ✓
- Node 476: mode=0 ✓
- Node 472: mode=0 ✓

## Usage Example

### Via WebUI
```javascript
{
  "input_image": "woman.jpg",
  "positive_prompt": "The young woman turns towards the camera",
  "enable_auto_prompt": true,  // Enable automatic prompting
  // ... other inputs
}
```

**Result:** Florence2 generates a description of the image, which is combined with your prompt.

### Via API
```python
inputs = {
    "input_image": "data:image/jpeg;base64,...",
    "positive_prompt": "The young woman turns towards the camera",
    "enable_auto_prompt": 0,  # 0 = enabled, 4 = disabled
    # ... other inputs
}
```

## Benefits

1. **Enhanced Prompts**: Automatically generates detailed descriptions from images
2. **Better Context**: AI understands the image content and adds relevant details
3. **Flexible Control**: Can be easily enabled/disabled per generation
4. **No Manual Effort**: No need to manually describe the image

## Technical Details

### Florence2 Model
- **Type:** Vision-language model
- **Task:** Detailed image captioning
- **Model:** `MiaoshouAI/Florence-2-base-PromptGen-v2.0`
- **Precision:** FP16
- **Attention:** SDPA

### Text Processing Pipeline
The generated caption goes through a series of replacements to adapt it for video generation:
1. Florence2 generates: "A photo of a woman..."
2. Replace "photo" → "video"
3. Replace "image" → "video"
4. Replace "painting" → "video"
5. Replace "illustration" → "video"
6. Result: "A video of a woman..."
7. Concatenate with user prompt

## Files Modified

1. ✅ `workflows/IMG_to_VIDEO_canvas.webui.yml` - Added toggle input
2. ✅ `test/test_img_to_video_canvas_workflow.py` - Added test validation
3. ✅ `test/README_WORKFLOW_TESTS.md` - Updated documentation

## Comparison with Sample Files

The implementation matches the behavior observed in:
- ✅ `test/samples/WAN2.2_Img2Video (AutoPromptEnabled).json` - All nodes mode: 0
- ✅ `test/samples/WAN2.2_Img2Video(AutoPromptDisabled).json` - All nodes mode: 4

## Future Enhancements

Potential improvements:
- [ ] Add Florence2 model selection dropdown
- [ ] Add custom text replacement rules
- [ ] Add preview of generated caption before generation
- [ ] Add option to control caption length
- [ ] Add support for different captioning models

## Related Documentation

- [Token-Based Workflow System](../docs/FEATURE_TOKEN_BASED_WORKFLOW_SYSTEM.md)
- [Workflow Test Fixtures](README_WORKFLOW_TESTS.md)
- [Debugging Checklist](DEBUGGING_CHECKLIST.md)

## Status

**✅ COMPLETE AND TESTED**

The automatic prompting toggle is now fully integrated and tested in the IMG_to_VIDEO_canvas workflow.
