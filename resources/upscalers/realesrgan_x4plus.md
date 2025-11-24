---
tags: [upscaler, realesrgan, enhancement]
title: "RealESRGAN x4plus"
version: "x4plus"
published: 2021-08-01
size: 67040989
creator: Tencent ARC Lab
ecosystem: realesrgan
basemodel: other
type: upscaler
AIR: "realesrgan_x4plus"
image: encoder.jpg
license: BSD-3-Clause
url: https://github.com/xinntao/Real-ESRGAN
---

# Description

- High-quality 4x upscaling model for general image enhancement. Works well with both anime and real-world images.
- 4x upscaling resolution with excellent detail preservation and fast inference time.
- Works with most ComfyUI upscaler nodes. Recommended for final output enhancement.

# Download
```bash
wget -P "$UI_HOME/models/upscale_models" \
  https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth
```
