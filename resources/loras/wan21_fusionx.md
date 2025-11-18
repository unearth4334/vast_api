---
tags: [lora, wan, video, style, enhancement]
ecosystem: wan
basemodel: wan2.1
type: lora
version: Image2Video
AIR: urn:air:wanvideo14b_i2v_720p:lora:civitai:1678575@1900322
image: fusionx_lora.jpg
size: 524288000
license: CreativeML Open RAIL-M
author: CivitAI Community
published: 2024-11-20
url: https://civitai.com/models/1678575
---

# Wan 2.1 FusionX LoRA

Style LoRA for Wan 2.1 that enhances video quality and provides better motion coherence. This LoRA is particularly effective for Image-to-Video workflows.

## Features
- Enhanced motion smoothness
- Better temporal consistency
- Improved detail preservation
- Compatible with various WAN 2.1 workflows

## Usage
Apply with weight between 0.6-0.8 for best results. Higher weights may produce more stylized output.

### Download
```bash
civitdl "https://civitai.com/models/1678575?modelVersionId=1900322" \
  "$UI_HOME/models/loras"
```
