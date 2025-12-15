# IMG_to_VIDEO Comprehensive Test Input

**Created**: 2025-12-15  
**Purpose**: Complete test configuration for IMG_to_VIDEO workflow editor  
**Status**: ✅ Ready for use

---

## Overview

This test input provides a comprehensive configuration for the IMG_to_VIDEO workflow with all parameters explicitly set. It can be used for:

- **Manual Testing**: Load in WebUI to test the workflow editor
- **API Testing**: Use with workflow generation API endpoints
- **Model Validation**: Verify model scanning and selection
- **Feature Testing**: Test all toggles and parameters

---

## File Location

```
test/samples/IMG_to_VIDEO_comprehensive_test.json
test/samples/sample_input_image.jpeg
```

---

## Configuration Summary

### Basic Settings

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Input Image** | `sample_input_image.jpeg` | JPEG sample image in test/samples/ |
| **Positive Prompt** | "The subject moves naturally..." | Natural cinematic motion |
| **Negative Prompt** | "fast movements, blurry..." | Avoid unwanted motion |
| **Seed** | -1 | Random seed (will generate new each time) |

### Size & Duration

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Width** | 576 px | Non-standard width (tests custom sizing) |
| **Height** | 832 px | Non-standard height (portrait aspect) |
| **Duration** | 5 seconds | Medium length video |
| **Frame Rate** | 16 FPS | Standard for Wan 2.2 |

### Generation Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Steps** | 20 | Balanced quality/speed |
| **CFG Scale** | 3.5 | Standard prompt adherence |
| **Sampling Speed** | 7 | ModelSamplingSD3 shift |
| **Upscale Ratio** | 2x | Double resolution |

### Model Selection

#### Main Model (High/Low Noise Pair)
- **High Noise**: `Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_high_noise_14B_fp16.safetensors`
- **Low Noise**: `Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_low_noise_14B_fp16.safetensors`
- **Model**: Wan 2.2 Image-to-Video (14B parameters)

#### LoRAs
- **Name**: Nsfw-22
- **High Path**: `Nsfw-22_ComfyUI_repackaged/Nsfw-22_high_noise.safetensors`
- **Low Path**: `Nsfw-22_ComfyUI_repackaged/Nsfw-22_low_noise.safetensors`
- **Strength**: 1.0 (full strength)

#### Supporting Models
- **CLIP**: `Wan-2.2/umt5_xxl_fp16.safetensors` (UMT5-XXL text encoder)
- **VAE**: `Wan-2.1/wan_2.1_vae.safetensors` (Wan 2.1 VAE)
- **Upscale**: `RealESRGAN_x4plus.pth` (4x upscaler)

### Feature Toggles

#### ✅ Enabled Features (mode: 0)

| Feature | Description | Impact |
|---------|-------------|--------|
| **Interpolation** | RIFE frame interpolation | Smoother motion |
| **Video Enhancer** | Post-processing enhancement | Better quality |
| **CFGZeroStar** | CFG optimization | Improved sampling |
| **Speed Regulation** | Motion speed control | Consistent motion |
| **Normalized Attention** | Attention normalization | Better quality |
| **MagCache** | Magnitude caching | Faster generation |
| **TorchCompile** | JIT compilation | Performance boost |
| **BlockSwap** | Memory optimization | Lower VRAM usage |
| **Automatic Prompting** | Auto prompt enhancement | Better results |

#### ❌ Disabled Features (mode: 2)

| Feature | Description | Reason |
|---------|-------------|--------|
| **Save Last Frame** | Save final frame as image | Not needed for test |
| **Upscaler** | Apply upscaling | Testing without upscale |
| **Upscale + Interpolation** | Both upscale + interp | Testing separately |

#### Special Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| **VRAM Reduction** | 100 | Maximum VRAM optimization |

---

## Usage

### 1. Manual Testing (WebUI)

1. Start the application:
   ```bash
   python3 app.py
   ```

2. Open browser to `http://localhost:5050`

3. Navigate to "Create" tab

4. Load test input:
   - Option A: Import from file: `test/samples/IMG_to_VIDEO_comprehensive_test.json`
   - Option B: Manually configure parameters as specified above

5. Verify all fields are populated correctly

6. Test model scanning:
   - Click "Refresh" on model selectors
   - Verify models are found and match the configuration

7. Execute workflow (if connected to instance)

### 2. API Testing

```bash
# Test workflow generation
curl -X POST http://localhost:5050/create/generate-workflow \
  -H "Content-Type: application/json" \
  -d @test/samples/IMG_to_VIDEO_comprehensive_test.json
```

### 3. Model Scanning Script

Use the automated script to scan for models and update the test input:

```bash
# Scan models from connected instance
python3 scripts/create_test_input.py "root@123.45.67.89 -p 12345"
```

This will:
- Connect to the instance via SSH
- Scan for all available models
- Match requested models (Wan 2.2, Nsfw-22, etc.)
- Update the test input with actual paths
- Display a summary of findings

---

## Validation Checklist

Use this checklist to verify the test input works correctly:

### Image Input
- [ ] Image file exists at `test/samples/sample_input_image.jpeg`
- [ ] Image loads in WebUI uploader
- [ ] Image preview displays correctly
- [ ] Auto-sizing calculates dimensions correctly

### Text Inputs
- [ ] Positive prompt displays correctly
- [ ] Negative prompt displays correctly
- [ ] Prompt character counts show correctly
- [ ] Seed field accepts -1 (random)

### Numeric Sliders
- [ ] Width slider set to 576
- [ ] Height slider set to 832
- [ ] Duration slider set to 5
- [ ] Steps slider set to 20
- [ ] CFG slider set to 3.5
- [ ] Frame Rate slider set to 16
- [ ] Speed slider set to 7
- [ ] Upscale Ratio slider set to 2

### Model Selectors
- [ ] Main model high/low pair populated
- [ ] LoRA list shows Nsfw-22 with strength 1.0
- [ ] CLIP model populated
- [ ] VAE model populated
- [ ] Upscale model populated
- [ ] All "Refresh" buttons work
- [ ] Model scanning completes without errors

### Toggle Features
- [ ] Save Last Frame = OFF (grey icon)
- [ ] Interpolation = ON (colored icon)
- [ ] Upscaler = OFF
- [ ] Upscale + Interpolation = OFF
- [ ] Video Enhancer = ON
- [ ] CFGZeroStar = ON
- [ ] Speed Regulation = ON
- [ ] Normalized Attention = ON
- [ ] MagCache = ON
- [ ] TorchCompile = ON
- [ ] BlockSwap = ON
- [ ] Automatic Prompting = ON
- [ ] VRAM Reduction = 100

### Workflow Generation
- [ ] Click "Generate Workflow" (if available)
- [ ] Workflow JSON generates without errors
- [ ] All tokens replaced correctly
- [ ] Node modes set correctly
- [ ] Model paths inserted correctly

### Execution (with connected instance)
- [ ] SSH connection established
- [ ] Click "▶️ Run Workflow"
- [ ] Workflow uploads successfully
- [ ] Execution starts on remote instance
- [ ] Progress updates received (if available)
- [ ] Video generation completes
- [ ] Output video can be retrieved

---

## Expected Workflow Behavior

When this test input is executed, the system should:

1. **Load Image**: Read `sample_input_image.jpeg`
2. **Resize**: Scale to 576x832 (portrait orientation)
3. **Generate Latent**: Create latent space representation
4. **Apply LoRA**: Load Nsfw-22 at full strength (1.0)
5. **Encode Prompts**: Use UMT5-XXL CLIP model
6. **Sample**: Run 20 steps with CFG 3.5, using both high/low noise models
7. **Decode**: Use Wan 2.1 VAE
8. **Interpolate**: Apply RIFE to increase frame rate
9. **Enhance**: Apply video enhancement post-processing
10. **Output**: Generate 5-second video at 16 FPS (80 frames base + interpolation)

**Estimated Generation Time**: 3-8 minutes (depends on GPU)  
**Estimated VRAM Usage**: ~22-24 GB (with VRAM reduction enabled)

---

## Troubleshooting

### Issue: Models Not Found

**Symptoms**:
- Model selectors show "No models found"
- Refresh button doesn't populate models

**Solutions**:
1. Verify SSH connection is active
2. Check instance has models downloaded
3. Run model scanning script manually
4. Check model paths in instance

### Issue: Image Upload Fails

**Symptoms**:
- Image won't upload
- Error message about file size or format

**Solutions**:
1. Verify `sample_input_image.jpeg` exists
2. Check file is valid JPEG format
3. Ensure file size < 10MB
4. Try re-saving image

### Issue: Workflow Generation Fails

**Symptoms**:
- Error when generating workflow
- Missing fields or validation errors

**Solutions**:
1. Verify all required fields populated
2. Check SSH connection string format
3. Review workflow template exists
4. Check logs for specific errors

### Issue: Execution Fails

**Symptoms**:
- Workflow won't run on instance
- Errors during generation

**Solutions**:
1. Verify instance has ComfyUI running
2. Check all models are available on instance
3. Verify VRAM is sufficient (need 24GB+)
4. Check instance logs for specific errors

---

## Files Structure

```
test/samples/
├── sample_input_image.jpeg              # Input image
├── IMG_to_VIDEO_comprehensive_test.json # Test configuration
└── [Other sample workflow files...]

scripts/
└── create_test_input.py                 # Model scanning script

workflows/
├── IMG_to_VIDEO_canvas.json            # Workflow template
└── IMG_to_VIDEO_canvas.webui.yml       # WebUI configuration
```

---

## Related Documentation

- [TEST_RUN_WORKFLOW_BUTTON.md](TEST_RUN_WORKFLOW_BUTTON.md) - Testing the Run Workflow button
- [FEATURE_IMG_TO_VIDEO_REDESIGN.md](FEATURE_IMG_TO_VIDEO_REDESIGN.md) - Complete feature documentation
- [GUIDE_TOKEN_WORKFLOW_CREATION.md](GUIDE_TOKEN_WORKFLOW_CREATION.md) - Token-based workflow system

---

## Notes

### Model Path Format

The test input uses standard ComfyUI model path format:
```
Category/ModelName.safetensors
```

Models are expected to be in ComfyUI's models directory structure:
```
models/
├── diffusion_models/
│   └── Wan-2.2_ComfyUI_repackaged/
│       ├── wan2.2_i2v_high_noise_14B_fp16.safetensors
│       └── wan2.2_i2v_low_noise_14B_fp16.safetensors
├── loras/
│   └── Nsfw-22_ComfyUI_repackaged/
│       ├── Nsfw-22_high_noise.safetensors
│       └── Nsfw-22_low_noise.safetensors
├── text_encoders/
│   └── Wan-2.2/
│       └── umt5_xxl_fp16.safetensors
├── vae/
│   └── Wan-2.1/
│       └── wan_2.1_vae.safetensors
└── upscale_models/
    └── RealESRGAN_x4plus.pth
```

### Toggle Mode Values

The WebUI YAML uses "node_mode_toggle" for features:
- **0** = Enabled (node active)
- **2** = Disabled/Bypassed (node bypassed)

Never use mode 1 (it's an invalid intermediate state).

### High/Low Noise Pairs

Wan 2.2 uses a dual-sampling approach:
- **High Noise Model**: Used for early denoising steps
- **Low Noise Model**: Used for final refinement steps

Both must be from the same model family. LoRAs also follow this pattern.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-15 | Initial comprehensive test input created |

---

## Maintenance

**When to Update**:
- New model versions released
- Feature toggles added/changed
- Parameter ranges modified
- New validation rules added

**How to Update**:
1. Modify JSON values directly
2. Or regenerate using `scripts/create_test_input.py`
3. Update this documentation
4. Test changes manually
5. Update validation checklist if needed

---

**Status**: ✅ Ready for production testing  
**Coverage**: All 30 inputs configured  
**Validation**: Passed format checks
