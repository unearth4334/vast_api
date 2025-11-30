# IMG to VIDEO WebUI Redesign Plan

## Overview
This document outlines the complete redesign of the IMG_to_VIDEO.webui.yml wrapper and its implementation in the Create tab UI. The redesign focuses on providing a comprehensive, user-friendly interface for the WAN 2.2 Image-to-Video workflow with advanced model selection, LoRA management, and feature toggles.

---

## 1. Requirements Analysis

### 1.1 Input Categories

#### Basic Inputs
- **Positive Prompt**: Textarea for describing desired motion/style
- **Negative Prompt**: Textarea for unwanted elements
- **Input Image**: Image upload field
- **Seed**: Random number with randomize control

#### Generation Parameters
- **Custom Size**: Boolean toggle
- **Size X/Y**: Sliders (896 × 1120 default)
- **Duration**: Slider (seconds)
- **Steps**: Slider (denoising steps)
- **CFG**: Slider (classifier-free guidance)
- **Frame Rate**: Slider (FPS)
- **Speed**: Slider (sampling shift)
- **Upscale Ratio**: Slider (1.5 default)

#### Model Selection (High-Low Noise Pairs)
- **Main Model**: Dropdown with high/low noise pairs
- **LoRAs**: Multi-select with add/remove functionality

#### Single Model Selection
- **CLIP Model**: Dropdown
- **VAE Model**: Dropdown
- **Upscale Model**: Dropdown

#### Feature Toggles
- Enable saving last frame
- Enable interpolation
- Enable upscaler
- Enable upscale and interpolation
- Enable Video enhancer
- Enable CFGZeroStar
- Enable speed regulation
- Enable Normalized Attention
- Enable MagCache
- Enable TorchCompile
- Enable BlockSwap
- Reduce VRAM usage (BlockSwap slider: 0-100)

---

## 2. New UI Components Design

### 2.1 High-Low Pair Model Selector

**Component**: `HighLowPairModelSelector`

**Purpose**: Select models that come in high-noise/low-noise pairs (e.g., WAN 2.2 14B models)

**UI Elements**:
```
┌─────────────────────────────────────────────────┐
│ Main Model                              🔄      │
├─────────────────────────────────────────────────┤
│ ▼ Wan 2.2 I2V 14B FP16                         │
│   Wan 2.2 T2V 14B FP16                         │
│   Custom Model Set                              │
└─────────────────────────────────────────────────┘
```

**Features**:
- Dropdown showing friendly names for model pairs
- Refresh button (🔄) to scan SSH instance for available models
- Matches files like:
  - `{name}_high_noise_14B_fp16.safetensors`
  - `{name}_low_noise_14B_fp16.safetensors`
- Stores both paths internally
- Shows loading state during refresh

**Data Structure**:
```javascript
{
  displayName: "Wan 2.2 I2V 14B FP16",
  highNoisePath: "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_high_noise_14B_fp16.safetensors",
  lowNoisePath: "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_low_noise_14B_fp16.safetensors",
  basePath: "diffusion_models/Wan-2.2_ComfyUI_repackaged",
  size: 57200000000
}
```

### 2.2 High-Low Pair LoRA Selector

**Component**: `HighLowPairLoRASelector`

**Purpose**: Multi-select LoRAs that come in high-noise/low-noise pairs

**UI Elements**:
```
┌─────────────────────────────────────────────────┐
│ LoRAs                                   🔄      │
├─────────────────────────────────────────────────┤
│ ▼ Select LoRA to add...                        │
│   Motion Enhancement v2                         │
│   Style Transfer Pro                            │
│   Detail Boost HD                               │
├─────────────────────────────────────────────────┤
│ Added LoRAs:                                    │
│ • Motion Enhancement v2               ❌        │
│   Strength: [━━━━━○━━━━] 0.8                   │
│ • Style Transfer Pro                  ❌        │
│   Strength: [━━━━━━○━━━] 1.0                   │
└─────────────────────────────────────────────────┘
```

**Features**:
- Dropdown to select from available LoRA pairs
- Refresh button to scan instance
- Added LoRAs shown as list items
- Each item has:
  - Display name
  - Strength slider (0.0 - 2.0)
  - Remove button (❌)
- Drag to reorder (optional enhancement)
- Matches files like:
  - `{name}_high_noise.safetensors`
  - `{name}_low_noise.safetensors`

**Data Structure**:
```javascript
{
  id: "lora_1",
  displayName: "Motion Enhancement v2",
  highNoisePath: "loras/motion_enhance_v2_high_noise.safetensors",
  lowNoisePath: "loras/motion_enhance_v2_low_noise.safetensors",
  strength: 0.8
}
```

### 2.3 Single Model Selector

**Component**: `SingleModelSelector`

**Purpose**: Select individual model files (CLIP, VAE, Upscale)

**UI Elements**:
```
┌─────────────────────────────────────────────────┐
│ CLIP Model                              🔄      │
├─────────────────────────────────────────────────┤
│ ▼ umt5_xxl_fp16.safetensors                    │
│   clip_l.safetensors                            │
│   t5xxl_fp16.safetensors                        │
└─────────────────────────────────────────────────┘
```

**Features**:
- Simple dropdown with file names
- Refresh button for each type
- Shows full path on hover
- File size indicator (optional)

**Data Structure**:
```javascript
{
  displayName: "umt5_xxl_fp16.safetensors",
  path: "text_encoders/Wan-2.2/umt5_xxl_fp16.safetensors",
  size: 11400000000,
  type: "clip"
}
```

### 2.4 Feature Toggle Group

**Component**: `FeatureToggleGroup`

**Purpose**: Group related enable/disable toggles

**UI Elements**:
```
┌─────────────────────────────────────────────────┐
│ Advanced Features                               │
├─────────────────────────────────────────────────┤
│ Video Output Options                            │
│ ☐ Save last frame                               │
│ ☐ Enable interpolation                          │
│ ☐ Enable upscaler                               │
│ ☑ Enable upscale and interpolation              │
│                                                  │
│ Quality Enhancements                            │
│ ☑ Video enhancer                                │
│ ☑ CFGZeroStar                                   │
│ ☑ Speed regulation                              │
│ ☑ Normalized Attention                          │
│                                                  │
│ Performance Optimization                        │
│ ☑ MagCache                                      │
│ ☐ TorchCompile                                  │
│ ☑ BlockSwap                                     │
│   VRAM Reduction: [━━━━━━━━━━○] 100%          │
└─────────────────────────────────────────────────┘
```

**Features**:
- Grouped checkboxes by category
- Conditional fields (VRAM slider only shown if BlockSwap enabled)
- Tooltips explaining each feature
- Collapsible sections

---

## 3. Model Discovery Architecture

### 3.1 Backend API Endpoints

#### 3.1.1 Scan Models Endpoint
```
POST /api/models/scan
Request:
{
  "ssh_connection": "ssh -p 2838 root@104.189.178.116",
  "model_type": "diffusion_models" | "loras" | "text_encoders" | "vae" | "upscale_models",
  "search_pattern": "high_low_pair" | "single"
}

Response:
{
  "success": true,
  "models": [
    {
      "displayName": "Wan 2.2 I2V 14B FP16",
      "highNoisePath": "...",
      "lowNoisePath": "...",
      "size": 57200000000
    }
  ],
  "cached": false,
  "cache_timestamp": "2025-11-29T..."
}
```

#### 3.1.2 Model Cache Management
- Cache scan results for 5 minutes per instance
- Invalidate cache on manual refresh
- Store in Redis or in-memory dict

### 3.2 Model Path Configuration (config.yaml)

```yaml
# Model discovery configuration
model_discovery:
  base_paths:
    diffusion_models: "models/diffusion_models"
    loras: "models/loras"
    text_encoders: "models/text_encoders"
    vae: "models/vae"
    upscale_models: "models/upscale_models"
    
  # High-Low pair patterns
  high_low_patterns:
    diffusion_models:
      high_suffix: "_high_noise_14B_fp16.safetensors"
      low_suffix: "_low_noise_14B_fp16.safetensors"
      extract_name_regex: "^(.+?)(?:_high_noise|_low_noise)"
      
    loras:
      high_suffix: "_high_noise.safetensors"
      low_suffix: "_low_noise.safetensors"
      extract_name_regex: "^(.+?)(?:_high_noise|_low_noise)"
  
  # File extensions to scan
  extensions:
    - ".safetensors"
    - ".ckpt"
    - ".pth"
    
  # Maximum depth for recursive search
  max_depth: 3
  
  # Cache TTL in seconds
  cache_ttl: 300
```

### 3.3 SSH Model Scanner Implementation

**File**: `app/api/model_scanner.py`

**Key Functions**:
```python
class ModelScanner:
    def __init__(self, ssh_connection: str, config: dict):
        """Initialize with SSH connection and config"""
        
    def scan_high_low_pairs(self, base_path: str, pattern_config: dict) -> List[HighLowPairModel]:
        """Scan for high/low noise model pairs"""
        
    def scan_single_models(self, base_path: str) -> List[SingleModel]:
        """Scan for individual model files"""
        
    def get_file_size(self, remote_path: str) -> int:
        """Get file size via SSH"""
        
    def match_pairs(self, files: List[str], pattern_config: dict) -> List[tuple]:
        """Match high/low noise pairs from file list"""
```

**SSH Commands**:
```bash
# List files recursively with size
find "$UI_HOME/models/diffusion_models" -maxdepth 3 -type f \( -name "*.safetensors" -o -name "*.ckpt" -o -name "*.pth" \) -exec ls -lh {} \;

# Get relative paths
find "$UI_HOME/models/diffusion_models" -maxdepth 3 -type f -name "*high_noise*.safetensors" -printf "%P\n"
```

---

## 4. WebUI YAML Structure

### 4.1 Redesigned IMG_to_VIDEO.webui.yml

```yaml
name: "IMG to VIDEO"
description: "Generate video from image using WAN 2.2 with comprehensive controls"
version: "2.0.0"
category: "video"
workflow_file: "IMG to VIDEO.json"
vram_estimate: "24GB"

# UI Layout Configuration
layout:
  sections:
    - id: "basic"
      title: "Basic Settings"
      collapsed: false
      
    - id: "generation"
      title: "Generation Parameters"
      collapsed: false
      
    - id: "models"
      title: "Model Selection"
      collapsed: false
      
    - id: "features"
      title: "Advanced Features"
      collapsed: true

# Input definitions
inputs:
  # BASIC SETTINGS
  - id: "input_image"
    section: "basic"
    node_id: "88"
    field: "image"
    type: "image"
    label: "Input Image"
    description: "Source image to animate"
    required: true
    accept: "image/png,image/jpeg,image/webp"
    max_size_mb: 10

  - id: "positive_prompt"
    section: "basic"
    node_id: "408"
    field: "value"
    type: "textarea"
    label: "Positive Prompt"
    description: "Describe the motion and style"
    required: true
    default: "The young woman turns towards the camera"
    placeholder: "Describe the motion..."
    max_length: 2000
    rows: 4

  - id: "negative_prompt"
    section: "basic"
    node_id: "409"
    field: "value"
    type: "textarea"
    label: "Negative Prompt"
    description: "What to avoid"
    required: false
    default: "色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走, fast movements, blurry, mouth moving, talking, teeth visible, strong blush"
    rows: 3

  # GENERATION PARAMETERS
  - id: "custom_size"
    section: "generation"
    node_id: "518"
    field: "value"
    type: "checkbox"
    label: "Use Custom Size"
    description: "Override auto-sizing from image"
    default: false

  - id: "size_x"
    section: "generation"
    node_id: "83"
    fields: ["Xi", "Xf"]
    type: "slider"
    label: "Width"
    description: "Output width"
    min: 512
    max: 1920
    step: 64
    default: 896
    unit: "px"
    depends_on:
      field: "custom_size"
      value: true

  - id: "size_y"
    section: "generation"
    node_id: "83"
    fields: ["Yi", "Yf"]
    type: "slider"
    label: "Height"
    description: "Output height"
    min: 512
    max: 1920
    step: 64
    default: 1120
    unit: "px"
    depends_on:
      field: "custom_size"
      value: true

  - id: "duration"
    section: "generation"
    node_id: "426"
    field: "Xi"
    type: "slider"
    label: "Duration"
    description: "Video length"
    min: 1.0
    max: 10.0
    step: 0.5
    default: 5.0
    unit: "seconds"

  - id: "steps"
    section: "generation"
    node_id: "82"
    fields: ["Xi", "Xf"]
    type: "slider"
    label: "Steps"
    description: "Denoising steps"
    min: 10
    max: 40
    step: 1
    default: 20

  - id: "cfg"
    section: "generation"
    node_id: "85"
    fields: ["Xi", "Xf"]
    type: "slider"
    label: "CFG Scale"
    description: "Prompt adherence strength"
    min: 1.0
    max: 10.0
    step: 0.5
    default: 3.5

  - id: "frame_rate"
    section: "generation"
    node_id: "490"
    field: "Xi"
    type: "slider"
    label: "Frame Rate"
    description: "Output FPS"
    min: 8.0
    max: 24.0
    step: 1.0
    default: 16.0
    unit: "FPS"

  - id: "speed"
    section: "generation"
    node_id: "157"
    fields: ["Xi", "Xf"]
    type: "slider"
    label: "Sampling Speed"
    description: "Speed parameter"
    min: 1.0
    max: 15.0
    step: 0.5
    default: 7.0

  - id: "seed"
    section: "generation"
    node_id: "73"
    field: "noise_seed"
    type: "seed"
    label: "Seed"
    description: "Random seed"
    default: -1
    randomize_button: true
    control_after_generate: "randomize"

  - id: "upscale_ratio"
    section: "generation"
    node_id: "421"
    fields: ["Xi", "Xf"]
    type: "slider"
    label: "Upscale Ratio"
    description: "Scale factor for upscaling"
    min: 1.0
    max: 4.0
    step: 0.5
    default: 1.5

  # MODEL SELECTION
  - id: "main_model"
    section: "models"
    node_ids: ["522", "523"]  # high and low noise loaders
    type: "high_low_pair_model"
    label: "Main Model (High/Low Noise Pair)"
    description: "Diffusion model pair for generation"
    required: true
    model_type: "diffusion_models"
    default_high: "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_high_noise_14B_fp16.safetensors"
    default_low: "Wan-2.2_ComfyUI_repackaged/wan2.2_i2v_low_noise_14B_fp16.safetensors"

  - id: "loras"
    section: "models"
    node_ids: ["416", "471"]  # high and low noise LoRA loaders
    type: "high_low_pair_lora_list"
    label: "LoRAs (High/Low Noise Pairs)"
    description: "Add LoRAs for style/motion control"
    required: false
    model_type: "loras"
    max_items: 5

  - id: "clip_model"
    section: "models"
    node_id: "460"
    field: "clip_name"
    type: "single_model"
    label: "CLIP Model"
    description: "Text encoder"
    required: true
    model_type: "text_encoders"
    default: "Wan-2.2/umt5_xxl_fp16.safetensors"

  - id: "vae_model"
    section: "models"
    node_id: "461"
    field: "vae_name"
    type: "single_model"
    label: "VAE Model"
    description: "Variational autoencoder"
    required: true
    model_type: "vae"
    default: "Wan-2.1/wan_2.1_vae.safetensors"

  - id: "upscale_model"
    section: "models"
    node_id: "384"
    field: "model_name"
    type: "single_model"
    label: "Upscale Model"
    description: "Super-resolution model"
    required: true
    model_type: "upscale_models"
    default: "RealESRGAN_x4plus.pth"

  # ADVANCED FEATURES
  - id: "save_last_frame"
    section: "features"
    category: "Video Output"
    type: "checkbox"
    label: "Save Last Frame"
    description: "Save final frame as image"
    default: false
    # Maps to workflow logic

  - id: "enable_interpolation"
    section: "features"
    category: "Video Output"
    node_id: "431"
    type: "checkbox"
    label: "Enable Interpolation"
    description: "Use RIFE for frame interpolation"
    default: false

  - id: "enable_upscaler"
    section: "features"
    category: "Video Output"
    type: "checkbox"
    label: "Enable Upscaler"
    description: "Apply upscaling without interpolation"
    default: false

  - id: "enable_upscale_interpolation"
    section: "features"
    category: "Video Output"
    type: "checkbox"
    label: "Enable Upscale + Interpolation"
    description: "Apply both upscaling and interpolation"
    default: true

  - id: "enable_video_enhancer"
    section: "features"
    category: "Quality"
    node_ids: ["481", "482"]
    type: "checkbox"
    label: "Video Enhancer"
    description: "WanVideoEnhanceAVideoKJ"
    default: true

  - id: "enable_cfgzerostar"
    section: "features"
    category: "Quality"
    node_ids: ["483", "484"]
    type: "checkbox"
    label: "CFGZeroStar"
    description: "CFG guidance enhancement"
    default: true

  - id: "enable_speed_regulation"
    section: "features"
    category: "Quality"
    node_ids: ["467", "468"]
    type: "checkbox"
    label: "Speed Regulation"
    description: "ModelSamplingSD3"
    default: true

  - id: "enable_normalized_attention"
    section: "features"
    category: "Quality"
    node_ids: ["485", "486"]
    type: "checkbox"
    label: "Normalized Attention"
    description: "WanVideoNAG"
    default: true

  - id: "enable_magcache"
    section: "features"
    category: "Performance"
    node_ids: ["505", "506"]
    type: "checkbox"
    label: "MagCache"
    description: "Memory optimization"
    default: true

  - id: "enable_torchcompile"
    section: "features"
    category: "Performance"
    type: "checkbox"
    label: "TorchCompile"
    description: "JIT compilation (experimental)"
    default: false

  - id: "enable_blockswap"
    section: "features"
    category: "Performance"
    node_ids: ["500", "501"]
    type: "checkbox"
    label: "BlockSwap"
    description: "VRAM reduction via offloading"
    default: true

  - id: "vram_reduction"
    section: "features"
    category: "Performance"
    node_id: "502"
    fields: ["Xi", "Xf"]
    type: "slider"
    label: "VRAM Reduction"
    description: "Percentage of model offloading (0% = fastest, 100% = lowest VRAM)"
    min: 0
    max: 100
    step: 10
    default: 100
    unit: "%"
    depends_on:
      field: "enable_blockswap"
      value: true

# Output configuration
outputs:
  - id: "original_video"
    node_id: "398"
    type: "video"
    format: "mp4"
    label: "Original Video"

  - id: "interpolated_video"
    node_id: "433"
    type: "video"
    format: "mp4"
    label: "Interpolated Video"
    depends_on:
      field: "enable_interpolation"
      value: true
```

---

## 5. Frontend Implementation

### 5.1 File Structure

```
app/webui/js/create/
├── workflow-form-builder.js       (existing, enhanced)
├── components/
│   ├── HighLowPairModelSelector.js
│   ├── HighLowPairLoRASelector.js
│   ├── SingleModelSelector.js
│   ├── FeatureToggleGroup.js
│   └── SectionContainer.js
└── services/
    ├── modelScannerService.js
    └── workflowValueMapper.js
```

### 5.2 Component APIs

#### HighLowPairModelSelector
```javascript
class HighLowPairModelSelector {
  constructor(config) {
    this.sshConnection = null;
    this.modelType = config.model_type; // 'diffusion_models'
    this.nodeIds = config.node_ids; // [high_node, low_node]
    this.cache = null;
  }
  
  async refreshModels() {
    const models = await modelScannerService.scanHighLowPairs(
      this.sshConnection,
      this.modelType
    );
    this.renderDropdown(models);
  }
  
  getValue() {
    return {
      highNoisePath: this.selectedModel.highNoisePath,
      lowNoisePath: this.selectedModel.lowNoisePath
    };
  }
  
  mapToWorkflowNodes(workflow) {
    workflow[this.nodeIds[0]].inputs.unet_name = this.getValue().highNoisePath;
    workflow[this.nodeIds[1]].inputs.unet_name = this.getValue().lowNoisePath;
  }
}
```

#### HighLowPairLoRASelector
```javascript
class HighLowPairLoRASelector {
  constructor(config) {
    this.addedLoras = [];
    this.maxItems = config.max_items || 5;
  }
  
  async refreshAvailableLoras() {
    // Scan instance for LoRA pairs
  }
  
  addLora(lora) {
    if (this.addedLoras.length >= this.maxItems) {
      alert(`Maximum ${this.maxItems} LoRAs allowed`);
      return;
    }
    this.addedLoras.push({
      id: generateId(),
      ...lora,
      strength: 1.0
    });
    this.renderLoraList();
  }
  
  removeLora(id) {
    this.addedLoras = this.addedLoras.filter(l => l.id !== id);
    this.renderLoraList();
  }
  
  getValue() {
    return this.addedLoras;
  }
  
  mapToWorkflowNodes(workflow) {
    const highNode = workflow[this.nodeIds[0]];
    const lowNode = workflow[this.nodeIds[1]];
    
    // Build Power Lora Loader format
    const loraConfig = {};
    this.addedLoras.forEach((lora, index) => {
      loraConfig[`Lora ${index + 1}`] = {
        on: true,
        lora: lora.highNoisePath,
        strength: lora.strength,
        strength_clip: lora.strength
      };
    });
    
    highNode.inputs["➕ Add Lora"] = loraConfig;
    // Similar for low node
  }
}
```

### 5.3 Model Scanner Service

**File**: `app/webui/js/create/services/modelScannerService.js`

```javascript
class ModelScannerService {
  constructor() {
    this.cache = new Map();
    this.cacheTTL = 300000; // 5 minutes
  }
  
  async scanHighLowPairs(sshConnection, modelType) {
    const cacheKey = `${sshConnection}:${modelType}:high_low`;
    
    // Check cache
    if (this.cache.has(cacheKey)) {
      const cached = this.cache.get(cacheKey);
      if (Date.now() - cached.timestamp < this.cacheTTL) {
        return cached.data;
      }
    }
    
    // Fetch from backend
    const response = await fetch('/api/models/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ssh_connection: sshConnection,
        model_type: modelType,
        search_pattern: 'high_low_pair'
      })
    });
    
    const data = await response.json();
    
    // Cache result
    this.cache.set(cacheKey, {
      data: data.models,
      timestamp: Date.now()
    });
    
    return data.models;
  }
  
  async scanSingleModels(sshConnection, modelType) {
    // Similar implementation for single models
  }
  
  invalidateCache(sshConnection, modelType) {
    const keys = Array.from(this.cache.keys())
      .filter(k => k.startsWith(`${sshConnection}:${modelType}`));
    keys.forEach(k => this.cache.delete(k));
  }
}

export const modelScannerService = new ModelScannerService();
```

---

## 6. Backend Implementation

### 6.1 API Route

**File**: `app/api/models.py`

```python
from flask import Blueprint, request, jsonify
from app.api.model_scanner import ModelScanner
from app.utils.config import get_model_discovery_config

bp = Blueprint('models', __name__, url_prefix='/api/models')

@bp.route('/scan', methods=['POST'])
def scan_models():
    """Scan SSH instance for models"""
    data = request.get_json()
    
    ssh_connection = data.get('ssh_connection')
    model_type = data.get('model_type')
    search_pattern = data.get('search_pattern', 'single')
    
    if not ssh_connection or not model_type:
        return jsonify({
            'success': False,
            'message': 'ssh_connection and model_type required'
        }), 400
    
    try:
        config = get_model_discovery_config()
        scanner = ModelScanner(ssh_connection, config)
        
        if search_pattern == 'high_low_pair':
            models = scanner.scan_high_low_pairs(
                config['base_paths'][model_type],
                config['high_low_patterns'].get(model_type)
            )
        else:
            models = scanner.scan_single_models(
                config['base_paths'][model_type]
            )
        
        return jsonify({
            'success': True,
            'models': models,
            'cached': False
        })
        
    except Exception as e:
        logger.error(f"Model scan error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
```

### 6.2 Model Scanner Class

**File**: `app/api/model_scanner.py`

```python
import re
import subprocess
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

@dataclass
class HighLowPairModel:
    display_name: str
    high_noise_path: str
    low_noise_path: str
    base_path: str
    size: int

@dataclass
class SingleModel:
    display_name: str
    path: str
    size: int
    type: str

class ModelScanner:
    def __init__(self, ssh_connection: str, config: dict):
        self.ssh_connection = ssh_connection
        self.config = config
        self.ssh_host, self.ssh_port = self._parse_ssh_connection(ssh_connection)
    
    def _parse_ssh_connection(self, connection: str) -> Tuple[str, int]:
        """Extract host and port from SSH connection string"""
        # Parse: ssh -p 2838 root@104.189.178.116
        port_match = re.search(r'-p\s+(\d+)', connection)
        port = int(port_match.group(1)) if port_match else 22
        
        host_match = re.search(r'root@([\d\.]+)', connection)
        host = host_match.group(1) if host_match else None
        
        if not host:
            raise ValueError("Invalid SSH connection string")
        
        return host, port
    
    def _run_ssh_command(self, command: str) -> str:
        """Execute command on remote host"""
        ssh_cmd = [
            'ssh',
            '-p', str(self.ssh_port),
            '-i', '/root/.ssh/id_ed25519',
            '-o', 'ConnectTimeout=10',
            '-o', 'StrictHostKeyChecking=yes',
            f'root@{self.ssh_host}',
            command
        ]
        
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise Exception(f"SSH command failed: {result.stderr}")
        
        return result.stdout
    
    def scan_high_low_pairs(
        self,
        base_path: str,
        pattern_config: Optional[dict]
    ) -> List[Dict]:
        """Scan for high/low noise model pairs"""
        if not pattern_config:
            return []
        
        high_suffix = pattern_config['high_suffix']
        low_suffix = pattern_config['low_suffix']
        extract_regex = pattern_config['extract_name_regex']
        
        # Find all matching files
        extensions = '|'.join(self.config['extensions'])
        find_cmd = f'''
            find "$UI_HOME/{base_path}" -maxdepth {self.config['max_depth']} -type f \
            \( -name "*{high_suffix}" -o -name "*{low_suffix}" \) \
            -printf "%P|%s\\n"
        '''
        
        output = self._run_ssh_command(find_cmd)
        files = [line.split('|') for line in output.strip().split('\n') if line]
        
        # Match pairs
        pairs = self._match_high_low_pairs(files, extract_regex, high_suffix, low_suffix)
        
        # Format for frontend
        models = []
        for base_name, high_file, low_file in pairs:
            models.append({
                'displayName': self._format_display_name(base_name),
                'highNoisePath': f"{base_path}/{high_file[0]}",
                'lowNoisePath': f"{base_path}/{low_file[0]}",
                'basePath': base_path,
                'size': int(high_file[1]) + int(low_file[1])
            })
        
        return models
    
    def _match_high_low_pairs(
        self,
        files: List[Tuple[str, str]],
        extract_regex: str,
        high_suffix: str,
        low_suffix: str
    ) -> List[Tuple[str, Tuple, Tuple]]:
        """Match high and low noise files into pairs"""
        high_files = {}
        low_files = {}
        
        for filepath, size in files:
            match = re.search(extract_regex, filepath)
            if match:
                base_name = match.group(1)
                
                if filepath.endswith(high_suffix):
                    high_files[base_name] = (filepath, size)
                elif filepath.endswith(low_suffix):
                    low_files[base_name] = (filepath, size)
        
        # Create pairs
        pairs = []
        for base_name in high_files:
            if base_name in low_files:
                pairs.append((
                    base_name,
                    high_files[base_name],
                    low_files[base_name]
                ))
        
        return pairs
    
    def scan_single_models(self, base_path: str) -> List[Dict]:
        """Scan for individual model files"""
        extensions = ' -o '.join([f'-name "*{ext}"' for ext in self.config['extensions']])
        find_cmd = f'''
            find "$UI_HOME/{base_path}" -maxdepth {self.config['max_depth']} -type f \
            \( {extensions} \) \
            -printf "%P|%s\\n"
        '''
        
        output = self._run_ssh_command(find_cmd)
        files = [line.split('|') for line in output.strip().split('\n') if line]
        
        models = []
        for filepath, size in files:
            models.append({
                'displayName': os.path.basename(filepath),
                'path': f"{base_path}/{filepath}",
                'size': int(size),
                'type': os.path.splitext(filepath)[1]
            })
        
        return sorted(models, key=lambda x: x['displayName'])
    
    def _format_display_name(self, base_name: str) -> str:
        """Convert base_name to friendly display name"""
        # wan2.2_i2v -> Wan 2.2 I2V
        name = base_name.replace('_', ' ').title()
        name = re.sub(r'(\d+)\.(\d+)', r'\1.\2', name)  # Fix version numbers
        return name
```

---

## 7. Workflow Value Mapping

### 7.1 Workflow Value Mapper

**File**: `app/webui/js/create/services/workflowValueMapper.js`

```javascript
class WorkflowValueMapper {
  /**
   * Map UI form values to ComfyUI workflow JSON
   */
  mapFormToWorkflow(formValues, workflowTemplate, config) {
    const workflow = JSON.parse(JSON.stringify(workflowTemplate));
    
    config.inputs.forEach(input => {
      const value = formValues[input.id];
      if (value === undefined) return;
      
      switch (input.type) {
        case 'high_low_pair_model':
          this.mapHighLowPairModel(workflow, input, value);
          break;
          
        case 'high_low_pair_lora_list':
          this.mapLoraList(workflow, input, value);
          break;
          
        case 'single_model':
          this.mapSingleModel(workflow, input, value);
          break;
          
        case 'checkbox':
          this.mapCheckbox(workflow, input, value);
          break;
          
        case 'slider':
          this.mapSlider(workflow, input, value);
          break;
          
        case 'seed':
          this.mapSeed(workflow, input, value);
          break;
          
        case 'textarea':
        case 'text':
          this.mapText(workflow, input, value);
          break;
          
        case 'image':
          this.mapImage(workflow, input, value);
          break;
      }
    });
    
    return workflow;
  }
  
  mapHighLowPairModel(workflow, input, value) {
    const [highNodeId, lowNodeId] = input.node_ids;
    workflow[highNodeId].inputs.unet_name = value.highNoisePath;
    workflow[lowNodeId].inputs.unet_name = value.lowNoisePath;
  }
  
  mapLoraList(workflow, input, loras) {
    const [highNodeId, lowNodeId] = input.node_ids;
    
    // Build Power Lora Loader config
    const loraConfig = {};
    loras.forEach((lora, index) => {
      const key = `Lora ${index + 1}`;
      loraConfig[key] = {
        on: true,
        lora: lora.highNoisePath,
        strength: lora.strength,
        strength_clip: lora.strength
      };
    });
    
    workflow[highNodeId].inputs["➕ Add Lora"] = loraConfig;
    
    // Repeat for low noise node with low paths
    const loraConfigLow = {};
    loras.forEach((lora, index) => {
      const key = `Lora ${index + 1}`;
      loraConfigLow[key] = {
        on: true,
        lora: lora.lowNoisePath,
        strength: lora.strength,
        strength_clip: lora.strength
      };
    });
    
    workflow[lowNodeId].inputs["➕ Add Lora"] = loraConfigLow;
  }
  
  mapSingleModel(workflow, input, value) {
    const node = workflow[input.node_id];
    node.inputs[input.field] = value.path;
  }
  
  mapCheckbox(workflow, input, value) {
    if (input.node_ids) {
      // Enable/disable multiple nodes
      input.node_ids.forEach(nodeId => {
        // Implementation depends on how nodes are enabled/disabled
        // May need to add/remove nodes or set bypass flags
      });
    }
  }
  
  mapSlider(workflow, input, value) {
    const node = workflow[input.node_id];
    if (input.fields) {
      // Map to multiple fields (e.g., Xi and Xf)
      input.fields.forEach(field => {
        node.inputs[field] = value;
      });
    } else {
      node.inputs[input.field] = value;
    }
  }
  
  mapSeed(workflow, input, value) {
    const node = workflow[input.node_id];
    if (value === -1 || value === 'random') {
      // Generate random seed
      value = Math.floor(Math.random() * 1000000000000);
    }
    node.inputs[input.field] = value;
  }
  
  mapText(workflow, input, value) {
    const node = workflow[input.node_id];
    node.inputs[input.field] = value;
  }
  
  mapImage(workflow, input, value) {
    const node = workflow[input.node_id];
    // value is the uploaded filename
    node.inputs[input.field] = value;
  }
}

export const workflowValueMapper = new WorkflowValueMapper();
```

---

## 8. Implementation Phases

### Phase 1: Configuration & Backend (Week 1)
- [ ] Update `config.yaml` with model discovery settings
- [ ] Implement `ModelScanner` class
- [ ] Create `/api/models/scan` endpoint
- [ ] Test SSH model scanning with WAN 2.2 models

### Phase 2: UI Components (Week 2)
- [ ] Build `HighLowPairModelSelector` component
- [ ] Build `HighLowPairLoRASelector` component
- [ ] Build `SingleModelSelector` component
- [ ] Build `FeatureToggleGroup` component
- [ ] Build `SectionContainer` for collapsible sections

### Phase 3: Integration (Week 3)
- [ ] Update `workflow-form-builder.js` to handle new component types
- [ ] Implement `modelScannerService`
- [ ] Implement `workflowValueMapper`
- [ ] Redesign `IMG_to_VIDEO.webui.yml`
- [ ] Wire up all components in Create tab

### Phase 4: Testing & Polish (Week 4)
- [ ] Test model scanning with real SSH instance
- [ ] Test LoRA add/remove/reorder functionality
- [ ] Test workflow generation with various configurations
- [ ] Test feature toggles and conditional fields
- [ ] Performance optimization (caching, debouncing)
- [ ] UI polish and responsive design

### Phase 5: Documentation (Week 5)
- [ ] Document new component APIs
- [ ] Create workflow YAML authoring guide
- [ ] Add tooltips and help text
- [ ] Create example workflows
- [ ] User testing and feedback

---

## 9. Technical Considerations

### 9.1 Performance Optimization
- **Debounce** model scans to avoid rapid SSH requests
- **Cache** scan results for 5 minutes per instance
- **Lazy load** LoRA strength sliders until user adds a LoRA
- **Virtualize** long LoRA lists if >20 items
- **Batch** workflow node updates to reduce re-renders

### 9.2 Error Handling
- SSH timeout handling (show retry button)
- Model not found errors (show warning, allow manual entry)
- Invalid workflow JSON (validate before submission)
- Missing required fields (show validation messages)
- Network errors during scan (graceful degradation)

### 9.3 Accessibility
- Keyboard navigation for all controls
- ARIA labels for screen readers
- Focus management in modals
- Color contrast compliance
- Responsive design for mobile/tablet

### 9.4 Security
- Sanitize SSH connection strings
- Validate file paths (prevent directory traversal)
- Rate limit model scan API
- Timeout long-running SSH commands
- XSS prevention in model names

---

## 10. Future Enhancements

### 10.1 Advanced Features
- **Preset management**: Save/load complete configurations
- **Workflow comparison**: Compare two workflow configs side-by-side
- **Model recommendations**: Suggest models based on prompt
- **Batch generation**: Queue multiple variations
- **A/B testing**: Generate with different settings simultaneously

### 10.2 UI Improvements
- **Drag-and-drop** LoRA reordering
- **Visual preview** of model files (thumbnails)
- **Size indicators** next to model names
- **Download progress** for missing models
- **Favorites system** for frequently used models
- **Search/filter** in model dropdowns

### 10.3 Workflow Features
- **Custom node support**: Handle arbitrary ComfyUI nodes
- **Workflow validation**: Check for missing models/nodes
- **Node graph visualization**: Show workflow structure
- **Hot reload**: Update UI when workflow YAML changes
- **Template system**: Create reusable workflow templates

---

## 11. Success Criteria

### 11.1 Functional Requirements
- ✅ All 20+ inputs correctly mapped to workflow nodes
- ✅ High-low pair model selection works with refresh
- ✅ LoRA management (add/remove/adjust strength) functional
- ✅ All feature toggles control correct nodes
- ✅ Conditional fields show/hide based on dependencies
- ✅ Workflow JSON generated correctly for execution

### 11.2 Performance Requirements
- Model scan completes in <10 seconds
- UI remains responsive during scans
- Form submission generates workflow in <1 second
- No memory leaks with repeated use
- Smooth animations and transitions

### 11.3 Usability Requirements
- Intuitive model selection process
- Clear visual feedback for all actions
- Helpful error messages
- Tooltips explain all advanced options
- Mobile-friendly responsive design

---

## 12. File Checklist

### Configuration Files
- [ ] `config.yaml` - Model discovery settings
- [ ] `IMG_to_VIDEO.webui.yml` - Redesigned workflow config

### Backend Files
- [ ] `app/api/models.py` - Model scan API blueprint
- [ ] `app/api/model_scanner.py` - SSH scanning logic
- [ ] `app/utils/config.py` - Config loading helpers

### Frontend Files
- [ ] `app/webui/js/create/components/HighLowPairModelSelector.js`
- [ ] `app/webui/js/create/components/HighLowPairLoRASelector.js`
- [ ] `app/webui/js/create/components/SingleModelSelector.js`
- [ ] `app/webui/js/create/components/FeatureToggleGroup.js`
- [ ] `app/webui/js/create/components/SectionContainer.js`
- [ ] `app/webui/js/create/services/modelScannerService.js`
- [ ] `app/webui/js/create/services/workflowValueMapper.js`
- [ ] `app/webui/js/create/workflow-form-builder.js` (enhanced)

### CSS Files
- [ ] `app/webui/css/create.css` - New component styles

### Test Files
- [ ] `test/test_model_scanner.py` - Backend tests
- [ ] `test/test_workflow_mapper.js` - Frontend tests

---

## 13. Migration Path

### For Existing Workflows
1. Old `.webui.yml` files continue to work
2. New component types are opt-in
3. Gradual migration of other workflows
4. Backward compatibility for 2 versions

### For Users
1. Existing saved configurations remain valid
2. UI gracefully handles missing models
3. Clear migration guide in docs
4. Video tutorial for new features

---

## Conclusion

This redesign provides a comprehensive, scalable solution for the IMG_to_VIDEO workflow UI that:
- Supports complex high-low noise model pairs
- Enables flexible LoRA management
- Provides intuitive model selection with SSH discovery
- Organizes 20+ inputs into logical sections
- Supports advanced features with clear toggles
- Maintains performance with caching and optimization
- Sets foundation for future workflow enhancements

The modular component design allows reuse across other workflows, and the configuration-driven approach makes it easy to create new workflow UIs without writing custom code.
