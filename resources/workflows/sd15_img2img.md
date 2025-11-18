---
tags: [workflow, img2img, sd15, enhancement]
ecosystem: sd15
basemodel: sd1.5
type: workflow
version: v1.0
image: sd15_img2img.jpg
author: Community
published: 2024-08-15
---

# SD 1.5 Image-to-Image

Classic image-to-image workflow using Stable Diffusion 1.5. Great for image enhancement and style transfer.

## Features
- Flexible denoising strength control
- Multiple sampler options
- ControlNet compatible
- Low VRAM requirements (4GB+)

## Requirements
- SD 1.5 checkpoint
- Input image

### Download
```bash
mkdir -p "$UI_HOME/user/default/workflows/sd15" && \
wget https://raw.githubusercontent.com/vastai-examples/workflows/main/sd15_img2img.json \
  -O "$UI_HOME/user/default/workflows/sd15/sd15_img2img.json"
```
