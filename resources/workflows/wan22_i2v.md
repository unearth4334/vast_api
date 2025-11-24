---
tags: [workflow, I2V, wan, video]
title: "WAN 2.2 I2V by UmeAiRT"
version: "v1.2"
published: 2024-12-15
size: 4096
creator: UmeAiRT
ecosystem: wan
basemodel: wan2.2
type: workflow
AIR: "urn:air:wanvideo14b_i2v_720p:unknown:civitai:1824577@2077046"
image: encoder.jpg
license: CreativeML Open RAIL-M
url: https://civitai.com/models/1824577
dependencies:
  - wan2.2_checkpoint
  - wan2.1_vae
---

# Description

- Image-to-Video workflow for Wan 2.2 model. This workflow enables high-quality video generation from static images using the WAN 2.2 base model.
- 720p video output with customizable frame count, motion control parameters, and seamless integration.
- Requirements: WAN 2.2 checkpoint model, WAN 2.1 VAE encoder, 16GB+ VRAM recommended

# Download
```bash
mkdir -p "$UI_HOME/user/default/workflows/UmeAiRT" && \
wget https://raw.githubusercontent.com/vastai-examples/workflows/main/WAN2.2_IMG_to_VIDEO_Base.json \
  -O "$UI_HOME/user/default/workflows/UmeAiRT/WAN2.2_IMG_to_VIDEO_Base.json"
```
