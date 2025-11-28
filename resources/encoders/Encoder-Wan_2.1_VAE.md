---
tags: [vae, wan, video]
title: "Wan 2.1 VAE"
version: "wan_2.1_vae"
ecosystem: wan
basemodel: wan2.1
type: vae
AIR: "wan_21_vae"
image: encoder.jpg
url: https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/blob/main/split_files/vae/wan_2.1_vae.safetensors
---

# Description

- Variational autoencoder for the Wan 2.1 family of text-to-video and image-to-video models in ComfyUI.
- Handles efficient latent encoding and decoding while preserving temporal information for video generation.
- Supports 1080p video resolution and is optimized for high-quality video output.

# Download

```bash
wget --progress=bar:force -P "$UI_HOME/models/vae/Wan-2.1" \
  https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors
```
