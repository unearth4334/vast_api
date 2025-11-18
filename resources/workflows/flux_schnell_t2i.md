---
tags: [workflow, text2img, flux, fast]
ecosystem: flux
basemodel: flux-schnell
type: workflow
version: v1.0
image: flux_t2i_simple.jpg
author: Community
published: 2024-10-01
---

# FLUX Schnell Text-to-Image

Simple and fast text-to-image workflow using FLUX Schnell model. Perfect for rapid prototyping and iteration.

## Features
- Fast generation (4-8 steps)
- Good quality output
- Low VRAM usage
- Simple interface

## Requirements
- FLUX Schnell checkpoint
- 8GB+ VRAM

### Download
```bash
mkdir -p "$UI_HOME/user/default/workflows/flux" && \
wget https://raw.githubusercontent.com/vastai-examples/workflows/main/flux_schnell_t2i.json \
  -O "$UI_HOME/user/default/workflows/flux/flux_schnell_t2i.json"
```
