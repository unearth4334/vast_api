---
tags: [lora, flux, anime, style]
title: "FLUX Anime Style LoRA"
version: "v1.2"
published: 2024-10-15
size: 235000000
creator: Community
ecosystem: flux
basemodel: flux-dev
type: lora
AIR: "flux_anime_v1.2"
image: flux_anime.jpg
dependencies:
  - flux_dev_checkpoint
---

# Description

- Transform FLUX generations into anime-style artwork with vibrant colors and characteristic anime aesthetics.
- Strong anime styling with vibrant color palette, works well with character portraits.
- Recommended weight: 0.7-1.0 | Works best with anime-related prompts

# Download
```bash
mkdir -p "$UI_HOME/models/loras" && \
wget -O "$UI_HOME/models/loras/flux_anime_v1.2.safetensors" \
  "https://civitai.com/api/download/models/flux-anime-v12"
```
