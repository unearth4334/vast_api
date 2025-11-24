---
tags: [checkpoint, flux, fast, text2img]
ecosystem: flux
basemodel: flux-schnell
type: checkpoint
version: v1.0
image: flux_schnell.jpg
author: Black Forest Labs
published: 2024-08-01
size: 23600000000
url: https://huggingface.co/black-forest-labs/FLUX.1-schnell
license: Apache-2.0
---

# FLUX.1 Schnell Checkpoint

Fast distilled version of FLUX.1 for rapid text-to-image generation. Produces high-quality images in 4-8 steps.

## Features
- Ultra-fast generation (4-8 steps)
- Excellent prompt understanding
- High-quality outputs
- Efficient memory usage

## Specifications
- Size: ~23.6GB
- Resolution: Up to 1024x1024
- Format: Safetensors

### Download
```bash
mkdir -p "$UI_HOME/models/checkpoints" && \
wget -O "$UI_HOME/models/checkpoints/flux1-schnell.safetensors" \
  "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/flux1-schnell.safetensors"
```
