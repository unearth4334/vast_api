---
tags: [lora, sdxl, detail, enhancement]
title: "Detail Enhancer LoRA for SDXL"
version: "v2.0"
published: 2024-09-01
size: 144000000
creator: Community
ecosystem: sdxl
basemodel: sdxl-1.0
type: lora
AIR: "detail_enhancer_sdxl_v2"
image: detail_enhancer.jpg
---

# Description

- Enhances fine details and textures in SDXL generations. Great for photorealistic renders and architectural visualization.
- Enhanced texture detail with better material rendering and improved skin textures.
- Recommended weight: 0.5-0.8 | Best for photorealistic styles

# Download
```bash
mkdir -p "$UI_HOME/models/loras" && \
wget -O "$UI_HOME/models/loras/detail_enhancer_v2.safetensors" \
  "https://civitai.com/api/download/models/detail-enhancer-v2"
```
