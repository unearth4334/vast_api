---
tags: [lora, sdxl, detail, enhancement]
ecosystem: sdxl
basemodel: sdxl-1.0
type: lora
version: v2.0
image: detail_enhancer.jpg
author: Community
published: 2024-09-01
size: 144000000
---

# Detail Enhancer LoRA for SDXL

Enhances fine details and textures in SDXL generations. Great for photorealistic renders and architectural visualization.

## Features
- Enhanced texture detail
- Better material rendering
- Improved skin textures
- Works with most SDXL models

## Usage
- Recommended weight: 0.5-0.8
- Best for photorealistic styles
- Can be combined with other LoRAs

### Download
```bash
mkdir -p "$UI_HOME/models/loras" && \
wget -O "$UI_HOME/models/loras/detail_enhancer_v2.safetensors" \
  "https://civitai.com/api/download/models/detail-enhancer-v2"
```
