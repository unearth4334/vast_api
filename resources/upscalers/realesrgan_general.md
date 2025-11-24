---
tags: [upscaler, realesrgan, general, 4x]
title: "RealESRGAN General 4x"
version: "v3"
published: 2024-03-01
size: 67000000
creator: Tencent ARC
ecosystem: other
basemodel: universal
type: upscaler
AIR: "realesrgan_x4plus"
image: realesrgan.jpg
license: BSD-3-Clause
url: https://github.com/xinntao/Real-ESRGAN
---

# Description

- General-purpose upscaling model that works well with various image types. 4x upscaling with excellent detail preservation.
- Works with photos and artwork with good balance of sharpness and smoothness.
- Scale: 4x | Input: Any resolution | Format: .pth model file

# Download
```bash
mkdir -p "$UI_HOME/models/upscale_models" && \
wget -O "$UI_HOME/models/upscale_models/RealESRGAN_x4plus.pth" \
  "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
```
