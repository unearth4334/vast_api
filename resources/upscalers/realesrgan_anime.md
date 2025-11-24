---
tags: [upscaler, anime, enhancement]
title: "RealESRGAN x4plus Anime 6B"
version: "x4plus_anime_6B"
published: 2021-10-15
size: 17938009
creator: Tencent ARC Lab
ecosystem: realesrgan
basemodel: other
type: upscaler
AIR: "realesrgan_x4plus_anime_6B"
image: encoder.jpg
license: BSD-3-Clause
url: https://github.com/xinntao/Real-ESRGAN
---

# Description

- Specialized 4x upscaler optimized for anime and cartoon images. Provides better results for anime art compared to the general model.
- 4x upscaling for anime/cartoon with preserved line art quality, reduced artifacts, and fast inference.
- Best for anime-style images, illustrations, and cartoons. Use the standard x4plus model for photorealistic content.

# Download
```bash
wget -P "$UI_HOME/models/upscale_models" \
  https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth
```
