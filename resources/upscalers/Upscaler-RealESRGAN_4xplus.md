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

- 4× super-resolution model from the RealESRGAN project designed for high-quality image upscaling.
- Restores fine details and textures while minimizing artifacts and enhancing clarity.
- Suitable for both photographic and artistic AI-generated images.

# Download

```bash
wget --progress=bar:force -P "$UI_HOME/models/ESRGAN" \
  https://huggingface.co/lllyasviel/Annotators/resolve/main/RealESRGAN_x4plus.pth
```
