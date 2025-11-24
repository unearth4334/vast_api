---
tags: [checkpoint, sd15, base, classic]
title: "Stable Diffusion 1.5 Base"
version: "v1.5"
published: 2022-10-21
size: 4270000000
creator: Stability AI
ecosystem: sd15
basemodel: sd-1.5
type: checkpoint
AIR: "sd15_base"
image: encoder.jpg
license: CreativeML Open RAIL-M
url: https://huggingface.co/runwayml/stable-diffusion-v1-5
---

# Description

- The classic Stable Diffusion 1.5 checkpoint. Widely compatible with countless LoRAs, embeddings, and tools.
- Huge ecosystem of add-ons, well-documented and tested with fast inference.
- Size: ~4.27GB | Resolution: 512x512 (native) | Format: Safetensors

# Download
```bash
mkdir -p "$UI_HOME/models/checkpoints" && \
wget -O "$UI_HOME/models/checkpoints/v1-5-pruned-emaonly.safetensors" \
  "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors"
```
