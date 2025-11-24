---
tags: [checkpoint, sd15, base, classic]
ecosystem: sd15
basemodel: sd-1.5
type: checkpoint
version: v1.5
image: sd15.jpg
author: Stability AI
published: 2022-10-21
size: 4270000000
url: https://huggingface.co/runwayml/stable-diffusion-v1-5
license: CreativeML Open RAIL-M
---

# Stable Diffusion 1.5 Base

The classic Stable Diffusion 1.5 checkpoint. Widely compatible with countless LoRAs, embeddings, and tools.

## Features
- Huge ecosystem of add-ons
- Well-documented and tested
- Fast inference
- 512x512 native resolution

## Specifications
- Size: ~4.27GB
- Format: Safetensors
- Resolution: 512x512 (native)
- Compatible with thousands of LoRAs

### Download
```bash
mkdir -p "$UI_HOME/models/checkpoints" && \
wget -O "$UI_HOME/models/checkpoints/v1-5-pruned-emaonly.safetensors" \
  "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors"
```
