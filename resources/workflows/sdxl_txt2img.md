---
tags: [workflow, text2img, sdxl, high-quality]
ecosystem: sdxl
basemodel: sdxl-1.0
type: workflow
version: v1.0
image: sdxl_t2i.jpg
author: Community
published: 2024-09-15
size: 2048
---

# SDXL Text-to-Image Workflow

High-quality text-to-image generation using Stable Diffusion XL. Produces detailed 1024x1024 images with excellent prompt adherence.

## Features
- High resolution (1024x1024)
- Excellent prompt following
- Built-in refiner support
- Multiple aspect ratios

## Requirements
- SDXL Base checkpoint
- SDXL Refiner checkpoint (optional)
- 12GB+ VRAM

### Download
```bash
mkdir -p "$UI_HOME/user/default/workflows/sdxl" && \
wget https://raw.githubusercontent.com/vastai-examples/workflows/main/sdxl_txt2img.json \
  -O "$UI_HOME/user/default/workflows/sdxl/sdxl_txt2img.json"
```
