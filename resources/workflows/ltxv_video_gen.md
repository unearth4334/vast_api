---
tags: [workflow, video, ltxv, text2video]
title: "LTX Video Generation Workflow"
version: "v1.0"
published: 2024-11-01
size: 4096
creator: Lightricks
ecosystem: ltxv
basemodel: ltxv-0.9
type: workflow
AIR: "ltxv_video_gen"
image: ltxv_video.jpg
dependencies:
  - ltxv_checkpoint
---

# Description

- Generate videos from text prompts using the LTX Video model. Produces 5-second clips at 24fps.
- Text-to-video generation with 5-second clips (121 frames) at 768x512 resolution.
- Requirements: LTX Video 0.9 checkpoint, 24GB+ VRAM recommended, ComfyUI LTXVideo node support

# Download
```bash
mkdir -p "$UI_HOME/user/default/workflows/ltxv" && \
wget https://raw.githubusercontent.com/vastai-examples/workflows/main/ltxv_video_gen.json \
  -O "$UI_HOME/user/default/workflows/ltxv/ltxv_video_gen.json"
```
