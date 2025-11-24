---
tags: [workflow, img2img, sd15, enhancement]
title: "SD 1.5 Image-to-Image Workflow"
version: "v1.0"
published: 2024-08-15
size: 2048
creator: Community
ecosystem: sd15
basemodel: sd1.5
type: workflow
AIR: "sd15_img2img"
image: encoder.jpg
---

# Description

- Classic image-to-image workflow using Stable Diffusion 1.5. Great for image enhancement and style transfer.
- Flexible denoising strength control with multiple sampler options and ControlNet compatibility.
- Requirements: SD 1.5 checkpoint, Input image, 4GB+ VRAM

# Download
```bash
mkdir -p "$UI_HOME/user/default/workflows/sd15" && \
wget https://raw.githubusercontent.com/vastai-examples/workflows/main/sd15_img2img.json \
  -O "$UI_HOME/user/default/workflows/sd15/sd15_img2img.json"
```
