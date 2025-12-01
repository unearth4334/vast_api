---
tags: [checkpoint, img2video]
title: "Wan 2.2 I2V 14B FP16"
version: "v1.0"
published: 2024-08-01
size: 57200000000
creator: Comfy-Org
ecosystem: wan
basemodel: wan2.2
type: checkpoint
AIR: "wan2.2_t2v_14B_fp16"
image: wan2.2_t2v_14B_fp16.jpg
---

# Description

- `wan2.2_i2v_*_14B_fp16_scaled.safetensors` is the 14‑billion‑parameter image‑to‑video diffusion model for the Wan 2.2 ComfyUI pipeline. It takes an input image and extends it into smooth, temporally‑coherent 720p video sequences, leveraging the Wan 2.2 architecture for high‑fidelity motion generation.
- High noise is used for the first steps and the low-noise for the details. 

# Download

```bash
# High noise
wget --progress=bar:force -P "$UI_HOME"/models/diffusion_models/Wan-2.2_ComfyUI_repackaged \
  https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp16.safetensors

# Low noise
wget --progress=bar:force -P "$UI_HOME"/models/diffusion_models/Wan-2.2_ComfyUI_repackaged \
  https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp16.safetensors
```


