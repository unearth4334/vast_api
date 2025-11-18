# Resource Library

This directory contains markdown-based resource definitions for workflows, models, and other assets that can be downloaded to VastAI instances.

## Directory Structure

```
/resources/
├── workflows/          # ComfyUI workflow JSON files
├── encoders/          # VAE and other encoders
├── upscalers/         # Upscaling models (RealESRGAN, etc.)
├── checkpoints/       # Base models and checkpoints
├── loras/             # LoRA files
├── images/            # Preview images and thumbnails
└── _metadata/         # System metadata (installed resources, etc.)
```

## Resource Format

Each resource is defined in a markdown file with YAML frontmatter:

```markdown
---
tags: [workflow, I2V, wan]
ecosystem: wan
basemodel: wan2.2
type: workflow
version: v1.0
image: preview.jpg
dependencies:
  - wan2.2_checkpoint
author: Author Name
published: 2024-01-01
url: https://example.com
license: MIT
size: 1048576
---

# Resource Title

Description of the resource...

## Features
- Feature 1
- Feature 2

### Download
\`\`\`bash
wget -P "$UI_HOME/models" \
  https://example.com/file.safetensors
\`\`\`
```

## Required Fields

- `tags`: Array of categorization tags
- `ecosystem`: Primary ecosystem (wan, flux, ltxv, sd15, sdxl, etc.)
- `basemodel`: Base model compatibility
- `version`: Version identifier
- `type`: Resource type (workflow, lora, checkpoint, vae, upscaler, etc.)

## Optional Fields

- `aliases`: Alternative names
- `published`: Publication date (YYYY-MM-DD)
- `AIR`: Asset Identifier Record (URN format)
- `image`: Preview image filename (stored in /resources/images/)
- `size`: File size in bytes
- `dependencies`: Array of required resources
- `author`: Creator name
- `url`: Official source URL
- `license`: License type

## Download Section

The markdown body must contain a `### Download` section with a bash code block containing the download command(s). The `$UI_HOME` variable will be automatically substituted with the actual ComfyUI home directory.

## Adding New Resources

1. Create a new markdown file in the appropriate subdirectory
2. Follow the format shown above
3. Include all required fields
4. Add a clear description and feature list
5. Provide a working download command
6. (Optional) Add a preview image to `/resources/images/`

## Resource Types

- **workflow**: ComfyUI workflow JSON files
- **checkpoint**: Base models and checkpoints
- **lora**: LoRA (Low-Rank Adaptation) models
- **vae**: VAE encoders
- **upscaler**: Upscaling models
- **embeddings**: Textual inversions and embeddings
- **controlnet**: ControlNet models

## Ecosystems

- **wan**: Wan Video models
- **flux**: FLUX models
- **ltxv**: LTX Video models
- **sd15**: Stable Diffusion 1.5
- **sdxl**: Stable Diffusion XL
- **other**: Other/general purpose

## Current Resources

This library currently contains:
- 3 workflows (WAN, FLUX, SD 1.5)
- 3 LoRAs (WAN, FLUX, SDXL)
- 2 upscalers (RealESRGAN)
- 1 checkpoint (SDXL base)
- 1 VAE (SDXL)

Total: 10 resources across 5 ecosystems
