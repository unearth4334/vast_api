---
tags: [text-encoder, wan, video]
title: "Wan 2.2 UMT5-XXL FP16 Text Encoder"
version: "umt5_xxl_fp16"
ecosystem: wan
basemodel: wan2.2
size: 11400000000
type: text_encoder
AIR: "wan_22_umt5_xxl_fp16"
image: encoder.jpg
url: https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/blob/main/split_files/text_encoders/umt5_xxl_fp16.safetensors
---

# Description

- Large multilingual T5-XXL text encoder for the Wan 2.2 family of text-to-video and image-to-video models in ComfyUI.
- Provides high-capacity natural language understanding for prompt conditioning with FP16 precision.
- Enables more expressive and detailed control over generated video content through advanced text embeddings.

# Download

```bash
wget --progress=bar:force -P "$UI_HOME"/models/text_encoders/Wan-2.2 \
  https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp16.safetensors
```
