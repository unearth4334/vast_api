---
tags: [vae, encoder, sdxl]
ecosystem: sdxl
basemodel: sdxl1.0
type: vae
version: v1.0
size: 334645796
author: Stability AI
published: 2023-07-26
url: https://huggingface.co/stabilityai/sdxl-vae
license: CreativeML Open RAIL-M
---

# SDXL VAE

Official VAE (Variational Autoencoder) for Stable Diffusion XL. Essential for high-quality image generation with SDXL models.

## Features
- Improved color accuracy
- Better fine details
- Required for SDXL workflows
- Compatible with all SDXL checkpoints

## Usage
This VAE is automatically used by most SDXL models, but can be explicitly specified in workflows for best results.

### Download
```bash
wget -P "$UI_HOME/models/vae" \
  https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors
```
