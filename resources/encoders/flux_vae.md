---
tags: [vae, encoder, flux]
ecosystem: flux
basemodel: flux
type: vae
version: v1.0
image: flux_vae.jpg
author: Black Forest Labs
published: 2024-08-01
size: 335000000
---

# FLUX VAE Encoder

Official VAE encoder for FLUX models. Required for proper encoding/decoding of latent representations.

## Features
- Optimized for FLUX models
- High-quality encoding/decoding
- Fast processing
- Standard component

## Specifications
- Size: ~335MB
- Format: Safetensors
- Compatible with all FLUX variants

### Download
```bash
mkdir -p "$UI_HOME/models/vae" && \
wget -O "$UI_HOME/models/vae/flux_vae.safetensors" \
  "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/ae.safetensors"
```
