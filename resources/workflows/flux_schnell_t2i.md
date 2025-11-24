---
tags: [workflow, text2img, flux, fast]
title: "FLUX Schnell Text-to-Image Workflow"
version: "v1.0"
published: 2024-10-01
size: 4096
creator: Community
ecosystem: flux
basemodel: flux-schnell
type: workflow
AIR: "flux_schnell_t2i"
image: encoder.jpg
---

# Description

- Simple and fast text-to-image workflow using FLUX Schnell model. Perfect for rapid prototyping and iteration.
- Fast generation (4-8 steps) with low VRAM usage and simple interface.
- Requirements: FLUX Schnell checkpoint, 8GB+ VRAM

# Download
```bash
mkdir -p "$UI_HOME/user/default/workflows/flux" && \
wget https://raw.githubusercontent.com/vastai-examples/workflows/main/flux_schnell_t2i.json \
  -O "$UI_HOME/user/default/workflows/flux/flux_schnell_t2i.json"
```
