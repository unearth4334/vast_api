---
tags: [upscaler, realesrgan, enhancement]
ecosystem: realesrgan
basemodel: other
type: upscaler
version: x4plus
image: RealESRGAN_x4plus.png
size: 67040989
author: Tencent ARC Lab
published: 2021-08-01
url: https://github.com/xinntao/Real-ESRGAN
license: BSD-3-Clause
---

# RealESRGAN x4plus

High-quality 4x upscaling model for general image enhancement. Works well with both anime and real-world images.

## Features
- 4x upscaling resolution
- Excellent detail preservation
- Works with various image types
- Fast inference time

## Usage
Works with most ComfyUI upscaler nodes. Recommended for final output enhancement.

### Download
```bash
wget -P "$UI_HOME/models/upscale_models" \
  https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth
```
