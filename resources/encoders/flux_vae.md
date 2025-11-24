---
tags: [vae, encoder, flux]
title: "FLUX VAE Encoder"
version: "v1.0"
published: 2024-08-01
size: 335000000
creator: Black Forest Labs
ecosystem: flux
basemodel: flux
type: vae
AIR: "flux_vae"
image: flux_vae.jpg
---

# Description

- Official VAE encoder for FLUX models. Required for proper encoding/decoding of latent representations.
- Optimized for FLUX models with high-quality encoding/decoding and fast processing.
- Size: ~335MB | Format: Safetensors | Compatible with all FLUX variants

# Download
```bash
mkdir -p "$UI_HOME/models/vae" && \
wget -O "$UI_HOME/models/vae/flux_vae.safetensors" \
  "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/ae.safetensors"
```
