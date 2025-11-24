---
tags: [workflow, video, ltxv, text2video]
ecosystem: ltxv
basemodel: ltxv-0.9
type: workflow
version: v1.0
image: ltxv_video.jpg
author: Lightricks
published: 2024-11-01
size: 4096
dependencies:
  - ltxv_checkpoint
---

# LTX Video Generation Workflow

Generate videos from text prompts using the LTX Video model. Produces 5-second clips at 24fps.

## Features
- Text-to-video generation
- 5-second clips (121 frames)
- 768x512 resolution
- Fast inference (~45s on H100)

## Requirements
- LTX Video 0.9 checkpoint
- 24GB+ VRAM recommended
- ComfyUI LTXVideo node support

### Download
```bash
mkdir -p "$UI_HOME/user/default/workflows/ltxv" && \
wget https://raw.githubusercontent.com/vastai-examples/workflows/main/ltxv_video_gen.json \
  -O "$UI_HOME/user/default/workflows/ltxv/ltxv_video_gen.json"
```
