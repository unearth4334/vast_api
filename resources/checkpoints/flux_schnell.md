---
tags: [checkpoint, flux, fast, text2img]
title: "FLUX.1 Schnell Checkpoint"
version: "v1.0"
published: 2024-08-01
size: 23600000000
creator: Black Forest Labs
ecosystem: flux
basemodel: flux-schnell
type: checkpoint
AIR: "flux1_schnell"
image: flux_schnell.jpg
license: Apache-2.0
url: https://huggingface.co/black-forest-labs/FLUX.1-schnell
---

# Description

- Fast distilled version of FLUX.1 for rapid text-to-image generation. Produces high-quality images in 4-8 steps.
- Ultra-fast generation with excellent prompt understanding and efficient memory usage.
- Size: ~23.6GB | Resolution: Up to 1024x1024 | Format: Safetensors

# Download
```bash
mkdir -p "$UI_HOME/models/checkpoints" && \
wget -O "$UI_HOME/models/checkpoints/flux1-schnell.safetensors" \
  "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/flux1-schnell.safetensors"
```
