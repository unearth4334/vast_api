---
tags: [upscaler, anime, enhancement]
ecosystem: realesrgan
basemodel: other
type: upscaler
version: x4plus_anime_6B
image: RealESRGAN_anime.png
size: 17938009
author: Tencent ARC Lab
published: 2021-10-15
url: https://github.com/xinntao/Real-ESRGAN
license: BSD-3-Clause
---

# RealESRGAN x4plus Anime 6B

Specialized 4x upscaler optimized for anime and cartoon images. Provides better results for anime art compared to the general model.

## Features
- 4x upscaling for anime/cartoon
- Preserves line art quality
- Reduces artifacts
- Fast inference

## Usage
Best for anime-style images, illustrations, and cartoons. Use the standard x4plus model for photorealistic content.

### Download
```bash
wget -P "$UI_HOME/models/upscale_models" \
  https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth
```
