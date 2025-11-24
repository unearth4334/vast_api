---
tags: [checkpoint, sdxl, base, realistic]
title: "Stable Diffusion XL Base 1.0"
version: "v1.0"
published: 2023-07-26
size: 6938078731
creator: Stability AI
ecosystem: sdxl
basemodel: sdxl1.0
type: checkpoint
AIR: "sdxl_base_1.0"
image: encoder.jpg
license: CreativeML Open RAIL++-M
url: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
---

# Description

- Official SDXL base model from Stability AI. High-quality text-to-image generation with improved composition and face generation.
- 1024x1024 native resolution with improved prompt following, better composition, and enhanced face generation.
- Requirements: 10GB+ VRAM for full precision, 6GB+ VRAM with optimizations | Use with SDXL VAE for best results

# Download
```bash
wget -P "$UI_HOME/models/checkpoints" \
  https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
```
