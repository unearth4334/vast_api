---
tags: [lora, wan, video, style, enhancement]
title: "General NSFW"
version: "v0.08a"
published: 2025-08-05
size: 524288000
creator: CivitAI Community
ecosystem: wan
basemodel: wan2.2
type: lora
AIR: "urn:air:wanvideo-22-i2v-a14b:lora:civitai:1307155@2083303"
image: encoder.jpg
url: https://civitai.com/models/1307155?modelVersionId=2073605
---

# Description

- Style LoRA for Wan 2.1 that enhances video quality and provides better motion coherence. Particularly effective for Image-to-Video workflows.
- Enhanced motion smoothness with better temporal consistency and improved detail preservation.
- Recommended weight: 0.6-0.8 | Higher weights may produce more stylized output

# Download
```bash
civitdl "https://civitai.com/models/1678575?modelVersionId=1900322" \
  "$UI_HOME/models/loras"
```
#### High Noise
```bash
# High noise
civitdl "https://civitai.com/models/1307155?modelVersionId=2073605" "$UI_HOME"/models/

# Low noise
civitdl "https://civitai.com/models/1307155?modelVersionId=2083303" "$UI_HOME"/models/Lora
```
