---
tags: [lora, flux, anime, style]
ecosystem: flux
basemodel: flux-dev
type: lora
version: v1.2
image: flux_anime.jpg
author: Community
published: 2024-10-15
size: 235000000
dependencies:
  - flux_dev_checkpoint
---

# FLUX Anime Style LoRA

Transform FLUX generations into anime-style artwork with vibrant colors and characteristic anime aesthetics.

## Features
- Strong anime styling
- Vibrant color palette
- Works well with character portraits
- Compatible with FLUX Dev

## Usage
- Recommended weight: 0.7-1.0
- Works best with anime-related prompts
- Mix with other LoRAs for unique styles

### Download
```bash
mkdir -p "$UI_HOME/models/loras" && \
wget -O "$UI_HOME/models/loras/flux_anime_v1.2.safetensors" \
  "https://civitai.com/api/download/models/flux-anime-v12"
```
