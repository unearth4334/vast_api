---
tags: [workflow, I2V, wan, video]
title: "WAN 2.2 I2V by UmeAiRT"
version: "v1.2 (classic)"
published: 2025-08-03
creator: UmeAiRT
ecosystem: wan
basemodel: wan2.2
type: workflow
AIR: "urn:air:wanvideo14b_i2v_720p:unknown:civitai:1824577@2077046"
image: 1824577@2077046.jpg
url: https://civitai.com/models/1824577
dependencies:
  - wan2.2_checkpoint
  - wan2.1_vae
---

# Description

- Image-to-Video workflow for Wan 2.2 model enabling high-quality video generation from static images.
- 720p video output with customizable frame count and motion control parameters.
- Requirements: WAN 2.2 checkpoint model, WAN 2.1 VAE encoder, 16GB+ VRAM recommended.

# Download

```bash
mkdir -p "$UI_HOME/user/default/workflows/UmeAiRT" && \
wget https://raw.githubusercontent.com/UmeAiRT/ComfyUI-Workflows/refs/heads/main/06_WAN/2.2/Base/IMG%20to%20VIDEO.json -O "$UI_HOME/user/default/workflows/UmeAiRT/WAN2.2_IMG_to_VIDEO_Base.json"
```
