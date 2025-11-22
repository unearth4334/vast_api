---
tags: [workflow, I2V, wan, video]
ecosystem: wan
basemodel: wan2.2
type: workflow
version: v1.2
AIR: urn:air:wanvideo14b_i2v_720p:unknown:civitai:1824577@2077046
image: wan22_i2v.jpg
dependencies:
  - wan2.2_checkpoint
  - wan2.1_vae
author: UmeAiRT
published: 2024-12-15
url: https://civitai.com/models/1824577
license: CreativeML Open RAIL-M
---

# WAN 2.2 I2V by UmeAiRT

Image-to-Video workflow for Wan 2.2 model. This workflow enables high-quality video generation from static images using the WAN 2.2 base model.

## Features
- 720p video output
- Customizable frame count
- Motion control parameters
- Seamless integration with WAN 2.2 checkpoint

## Requirements
- WAN 2.2 checkpoint model
- WAN 2.1 VAE encoder
- Minimum 16GB VRAM recommended

### Download
```bash
mkdir -p "$UI_HOME/user/default/workflows/UmeAiRT" && \
wget https://raw.githubusercontent.com/vastai-examples/workflows/main/WAN2.2_IMG_to_VIDEO_Base.json \
  -O "$UI_HOME/user/default/workflows/UmeAiRT/WAN2.2_IMG_to_VIDEO_Base.json"
```
