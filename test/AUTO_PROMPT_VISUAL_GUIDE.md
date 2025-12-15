# Automatic Prompting Toggle - Visual Comparison

## Node Mode Changes

### When ENABLED (enable_auto_prompt: 0)

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTO PROMPT: ENABLED                      │
└─────────────────────────────────────────────────────────────┘

Input Image → Node 473 (Florence2 Model) [mode: 0] ✅ ACTIVE
                      ↓
              Node 480 (Florence2 Run) [mode: 0] ✅ ACTIVE
                      ↓
         Generated Caption: "A photo of a woman..."
                      ↓
              Node 474 [mode: 0] ✅ ACTIVE
         Replace: "photo" → "video"
                      ↓
              Node 475 [mode: 0] ✅ ACTIVE
         Replace: "image" → "video"
                      ↓
              Node 476 [mode: 0] ✅ ACTIVE
         Replace: "painting" → "video"
                      ↓
              Node 472 [mode: 0] ✅ ACTIVE
         Replace: "illustration" → "video"
                      ↓
         Processed Caption: "A video of a woman..."
                      ↓
              Node 451 (String Concatenate)
         Combines: Auto Caption + User Prompt
                      ↓
         Final Prompt: "A video of a woman... The young woman turns..."
                      ↓
              Encode & Generate Video
```

### When DISABLED (enable_auto_prompt: 4)

```
┌─────────────────────────────────────────────────────────────┐
│                   AUTO PROMPT: DISABLED                      │
└─────────────────────────────────────────────────────────────┘

Input Image → Node 473 (Florence2 Model) [mode: 4] ❌ MUTED
                      
              Node 480 (Florence2 Run) [mode: 4] ❌ MUTED
                      
              Node 474 [mode: 4] ❌ MUTED
              
              Node 475 [mode: 4] ❌ MUTED
              
              Node 476 [mode: 4] ❌ MUTED
              
              Node 472 [mode: 4] ❌ MUTED
                      ↓
              Node 451 (String Concatenate)
         Uses: Empty String + User Prompt
                      ↓
         Final Prompt: "The young woman turns..."
                      ↓
              Encode & Generate Video
```

## Example Output Comparison

### Example: Portrait Image

**Input Image:** A photo of a young woman with black hair wearing a gold bodysuit

**User Prompt:** "The young woman turns towards the camera"

#### With Auto-Prompting ENABLED ✅

**Generated Caption (Florence2):**
```
A photo of a slender, pale-skinned woman with short, black hair 
and a bob cut, wearing a transparent, gold-colored bodysuit that 
reveals her spine. The background is a simple, white gradient.
```

**After Text Replacement:**
```
A video of a slender, pale-skinned woman with short, black hair 
and a bob cut, wearing a transparent, gold-colored bodysuit that 
reveals her spine. The background is a simple, white gradient.
```

**Final Prompt Sent to Model:**
```
A video of a slender, pale-skinned woman with short, black hair 
and a bob cut, wearing a transparent, gold-colored bodysuit that 
reveals her spine. The background is a simple, white gradient. 
The young woman turns towards the camera
```

**Benefits:**
- ✅ Rich description of the image content
- ✅ Details about appearance, clothing, background
- ✅ Combined with user's motion instruction
- ✅ Better video quality and consistency

#### With Auto-Prompting DISABLED ❌

**Generated Caption:** _(none - nodes muted)_

**Final Prompt Sent to Model:**
```
The young woman turns towards the camera
```

**Characteristics:**
- ⚠️ Only user-provided prompt used
- ⚠️ No automatic description of image content
- ⚠️ Model has less context about the scene
- ✅ Faster processing (no Florence2 inference)
- ✅ User has full control over prompt

## Performance Impact

### With Auto-Prompting ENABLED
- **Additional Time:** +5-10 seconds (Florence2 inference)
- **VRAM Usage:** +1-2GB (Florence2 model)
- **Quality:** Higher (better prompt context)
- **Use Case:** Best for complex images needing description

### With Auto-Prompting DISABLED
- **Additional Time:** 0 seconds
- **VRAM Usage:** 0GB extra
- **Quality:** Depends on user prompt quality
- **Use Case:** Best when you know exactly what to describe

## UI Appearance

```yaml
┌─────────────────────────────────────────────────────────────┐
│ 🔧 Advanced Features                                    [▼] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ... (other toggles) ...                                     │
│                                                              │
│ ☑ Automatic Prompting (Florence2)                          │
│   Enable Florence2 AI to automatically generate            │
│   descriptive prompts from the input image. When           │
│   enabled, generates and enhances prompts automatically.   │
│                                                              │
│ ... (other toggles) ...                                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Decision Guide

### ✅ Enable Auto-Prompting When:
- You have a complex image with many details
- You want rich, descriptive prompts automatically
- You're okay with +5-10 seconds generation time
- You want to combine AI description with your motion prompt
- You have sufficient VRAM (24GB+)

### ❌ Disable Auto-Prompting When:
- You have a very simple image
- You've written a detailed prompt yourself
- You want faster generation
- You're working with limited VRAM
- You prefer full manual control over prompts

## Implementation Details

| Aspect | Details |
|--------|---------|
| **Input ID** | `enable_auto_prompt` |
| **Type** | `node_mode_toggle` |
| **Default** | Enabled (mode: 0) |
| **Nodes Affected** | 6 nodes (473, 480, 474, 475, 476, 472) |
| **Section** | Advanced Features |
| **Required** | No |

## Test Validation

```
Test: enable_auto_prompt = 0 (enabled)
✓ Node 473: mode=0
✓ Node 480: mode=0  
✓ Node 474: mode=0
✓ Node 475: mode=0
✓ Node 476: mode=0
✓ Node 472: mode=0

Test: enable_auto_prompt = 4 (disabled)
✓ Node 473: mode=4
✓ Node 480: mode=4
✓ Node 474: mode=4
✓ Node 475: mode=4
✓ Node 476: mode=4
✓ Node 472: mode=4
```

## Related Features

This toggle works alongside:
- ✅ **Positive Prompt** - User's manual prompt (always used)
- ✅ **Negative Prompt** - What to avoid (always used)
- ✅ **Video Enhancer** - Improves video quality
- ✅ **CFG Zero Star** - Better prompt adherence

## Summary

The automatic prompting toggle gives you **flexible control** over whether to use AI-generated image descriptions in your video prompts. Enable it for rich, detailed descriptions automatically, or disable it for faster generation with manual prompts only.

**Current Status:** ✅ Fully implemented and tested
