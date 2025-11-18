---
tags: [checkpoint, sdxl, base, realistic]
ecosystem: sdxl
basemodel: sdxl1.0
type: checkpoint
version: v1.0
size: 6938078731
author: Stability AI
published: 2023-07-26
url: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
license: CreativeML Open RAIL++-M
---

# Stable Diffusion XL Base 1.0

Official SDXL base model from Stability AI. High-quality text-to-image generation with improved composition and face generation.

## Features
- 1024x1024 native resolution
- Improved prompt following
- Better composition
- Enhanced face generation
- Two-stage pipeline support

## Requirements
- 10GB+ VRAM for full precision
- 6GB+ VRAM with optimizations

## Usage
Use with SDXL VAE for best results. Can be combined with SDXL refiner for higher quality.

### Download
```bash
wget -P "$UI_HOME/models/checkpoints" \
  https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
```
