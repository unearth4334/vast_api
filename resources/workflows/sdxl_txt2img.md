---
tags: [workflow, text2img, sdxl, high-quality]
title: "SDXL Text-to-Image Workflow"
version: "v1.0"
published: 2024-09-15
size: 2048
creator: Community
ecosystem: sdxl
basemodel: sdxl-1.0
type: workflow
AIR: "sdxl_txt2img"
image: encoder.jpg
---

# Description

- High-quality text-to-image generation using Stable Diffusion XL. Produces detailed 1024x1024 images with excellent prompt adherence.
- High resolution (1024x1024) with built-in refiner support and multiple aspect ratios.
- Requirements: SDXL Base checkpoint, SDXL Refiner checkpoint (optional), 12GB+ VRAM

# Download
```bash
mkdir -p "$UI_HOME/user/default/workflows/sdxl" && \
wget https://raw.githubusercontent.com/vastai-examples/workflows/main/sdxl_txt2img.json \
  -O "$UI_HOME/user/default/workflows/sdxl/sdxl_txt2img.json"
```
