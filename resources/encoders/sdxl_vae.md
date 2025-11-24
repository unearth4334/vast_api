---
tags: [vae, encoder, sdxl]
title: "SDXL VAE"
version: "v1.0"
published: 2023-07-26
size: 334645796
creator: Stability AI
ecosystem: sdxl
basemodel: sdxl1.0
type: vae
AIR: "sdxl_vae"
image: sdxl_vae.jpg
license: CreativeML Open RAIL-M
url: https://huggingface.co/stabilityai/sdxl-vae
---

# Description

- Official VAE (Variational Autoencoder) for Stable Diffusion XL. Essential for high-quality image generation with SDXL models.
- Improved color accuracy and better fine details. Required for SDXL workflows and compatible with all SDXL checkpoints.
- This VAE is automatically used by most SDXL models but can be explicitly specified in workflows for best results.

# Download
```bash
wget -P "$UI_HOME/models/vae" \
  https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors
```
