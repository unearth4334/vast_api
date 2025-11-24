---
tags: [upscaler, realesrgan, general, 4x]
ecosystem: other
basemodel: universal
type: upscaler
version: v3
image: realesrgan.jpg
author: Tencent ARC
published: 2024-03-01
size: 67000000
url: https://github.com/xinntao/Real-ESRGAN
license: BSD-3-Clause
---

# RealESRGAN General 4x

General-purpose upscaling model that works well with various image types. 4x upscaling with excellent detail preservation.

## Features
- 4x upscaling
- Works with photos and artwork
- Good balance of sharpness and smoothness
- Fast processing

## Specifications
- Scale: 4x
- Input: Any resolution
- Format: .pth model file

### Download
```bash
mkdir -p "$UI_HOME/models/upscale_models" && \
wget -O "$UI_HOME/models/upscale_models/RealESRGAN_x4plus.pth" \
  "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
```
