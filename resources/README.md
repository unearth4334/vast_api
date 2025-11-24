# Resource Library

This directory contains markdown-based resource definitions for workflows, models, and other assets that can be downloaded to VastAI instances through the Resource Manager.

## Directory Structure

```
resources/
├── README.md              # This file - instructions and documentation
├── checkpoints/          # Base models and diffusion checkpoints
├── loras/                # LoRA (Low-Rank Adaptation) models
├── workflows/            # ComfyUI workflow JSON files
├── encoders/             # VAE and other encoders
├── upscalers/            # Upscaling models (RealESRGAN, etc.)
└── images/               # Preview images and thumbnails
```

## Resource File Format

Each resource is defined in a markdown file with YAML frontmatter followed by a Description section and Download section.

### Template

```markdown
---
tags: [tag1, tag2, tag3]
title: "Resource Display Name"
version: "v1.0"
published: 2024-01-01
size: 1048576
creator: Creator Name
ecosystem: ecosystem_name
basemodel: base_model_name
type: resource_type
AIR: "unique_identifier"
image: preview_image.jpg
license: License Type
url: https://source-url.com
dependencies:
  - dependency1
  - dependency2
---

# Description

- First bullet point: Brief description of what this resource is and what it does.
- Second bullet point: Key features, specifications, or capabilities.
- Third bullet point: Requirements, usage notes, or recommendations.

# Download

\`\`\`bash
wget -P "$UI_HOME/models/target_directory" \
  https://example.com/resource_file.safetensors
\`\`\`
```

## Frontmatter Fields

### Required Fields

- **`tags`**: Array of categorization tags (e.g., `[checkpoint, flux, text2img]`)
- **`title`**: Display name shown in the Resource Manager UI
- **`version`**: Version identifier (e.g., `"v1.0"`, `"x4plus"`)
- **`ecosystem`**: Primary ecosystem - `wan`, `flux`, `ltxv`, `sd15`, `sdxl`, `realesrgan`, `other`
- **`basemodel`**: Base model compatibility (e.g., `flux-schnell`, `sdxl1.0`, `wan2.2`)
- **`type`**: Resource type - `checkpoint`, `lora`, `workflow`, `vae`, `upscaler`, `embeddings`, `controlnet`
- **`AIR`**: Asset Identifier Record - unique identifier for this resource

### Optional Fields

- **`published`**: Publication date in YYYY-MM-DD format
- **`size`**: File size in bytes (integer)
- **`creator`**: Creator or author name
- **`image`**: Preview image filename (stored in `resources/images/`)
- **`license`**: License type (e.g., `Apache-2.0`, `CreativeML Open RAIL-M`, `BSD-3-Clause`)
- **`url`**: Official source URL or documentation
- **`dependencies`**: Array of required resources (AIR identifiers)

## Body Sections

### Description Section

The Description section should contain 2-4 bullet points:

1. **What it is**: Brief description of the resource and its primary purpose
2. **Key features**: Notable capabilities, specifications, or characteristics
3. **Usage notes**: Requirements, recommendations, or important details

Use pipe separators (`|`) to include inline specifications for readability.

### Download Section

The Download section must contain a bash code block with download commands. Use `$UI_HOME` as the ComfyUI home directory variable - it will be automatically substituted during installation.

Common download patterns:
- **Direct wget**: `wget -P "$UI_HOME/models/checkpoints" https://example.com/model.safetensors`
- **Multiple files**: Use multiple wget commands for resources with several files
- **CivitDL**: `civitdl "https://civitai.com/models/..." "$UI_HOME/models/loras"`
- **Create directories**: Use `mkdir -p "$UI_HOME/..."` before downloading if needed

## Resource Types

### Checkpoints (`type: checkpoint`)
Large diffusion models that form the base of image/video generation:
- Location: `resources/checkpoints/`
- Target: `$UI_HOME/models/checkpoints/`
- Examples: FLUX Schnell, SDXL Base, Stable Diffusion 1.5

### LoRAs (`type: lora`)
Lightweight adaptation models that modify style or content:
- Location: `resources/loras/`
- Target: `$UI_HOME/models/loras/`
- Examples: Anime styles, realism enhancers, detail LoRAs

### Workflows (`type: workflow`)
ComfyUI workflow JSON files for specific use cases:
- Location: `resources/workflows/`
- Target: `$UI_HOME/user/default/workflows/`
- Examples: Text-to-image, image-to-video, upscaling workflows

### VAEs (`type: vae`)
Variational autoencoders for encoding/decoding latents:
- Location: `resources/encoders/`
- Target: `$UI_HOME/models/vae/`
- Examples: FLUX VAE, SDXL VAE

### Upscalers (`type: upscaler`)
Models for increasing image resolution:
- Location: `resources/upscalers/`
- Target: `$UI_HOME/models/upscale_models/`
- Examples: RealESRGAN variants

## Ecosystems

Resources are organized by ecosystem to help users find compatible components:

- **`wan`**: Wan Video models (2.1, 2.2) - text-to-video and image-to-video
- **`flux`**: FLUX models (Schnell, Dev) - fast text-to-image generation
- **`ltxv`**: LTX Video models - video generation
- **`sd15`**: Stable Diffusion 1.5 - classic text-to-image
- **`sdxl`**: Stable Diffusion XL - high-resolution text-to-image
- **`realesrgan`**: RealESRGAN upscaling models
- **`other`**: Universal or general-purpose resources

## Adding New Resources

1. **Choose the correct subdirectory** based on resource type
2. **Create a markdown file** with a descriptive filename (e.g., `flux_realism_lora.md`)
3. **Fill in all required frontmatter fields**
4. **Write clear description bullets** (2-4 points)
5. **Provide working download commands** using `$UI_HOME` variable
6. **Add preview image** (optional) to `resources/images/` and reference in frontmatter
7. **Test the resource** by selecting it in the Resource Manager

## Naming Conventions

### Filenames
- Use lowercase with underscores: `flux_schnell.md`, `sdxl_anime_style.md`
- Include version if relevant: `wan22_i2v.md`, `realesrgan_x4plus.md`
- Be descriptive but concise

### AIR (Asset Identifier Record)
- Format: `lowercase_with_underscores`
- Examples: `flux_schnell`, `sdxl_base_1.0`, `realesrgan_x4plus`
- For URNs: `urn:air:ecosystem:type:source:id@version`

### Images
- Same basename as markdown file: `flux_schnell.jpg` for `flux_schnell.md`
- Supported formats: `.jpg`, `.png`, `.webp`
- Recommended size: 512x512 or 1024x1024

## Best Practices

1. **Be accurate**: Verify file sizes, URLs, and technical specifications
2. **Be concise**: Keep descriptions clear and to the point (2-4 bullets)
3. **Be helpful**: Include requirements, recommended settings, and usage notes
4. **Test downloads**: Ensure download URLs are valid and accessible
5. **Use variables**: Always use `$UI_HOME` instead of hardcoded paths
6. **Organize logically**: Group related resources (e.g., base model + VAE + workflows)
7. **Version explicitly**: Include version numbers in titles and AIR identifiers
8. **Document dependencies**: List required resources in the `dependencies` array

## Current Resource Count

This library currently contains:
- **4 Checkpoints**: FLUX Schnell, SD 1.5, SDXL Base, WAN 2.2
- **5 LoRAs**: FLUX (Anime, Realism), SDXL (Anime, Detail), WAN (FusionX)
- **5 Workflows**: FLUX T2I, SDXL T2I, SD15 I2I, LTXV Video, WAN I2V
- **2 VAEs**: FLUX VAE, SDXL VAE
- **3 Upscalers**: RealESRGAN (General, Anime, x4plus)

**Total**: 19 resources across 6 ecosystems

## Troubleshooting

### Resource not appearing in UI
- Check YAML frontmatter syntax (use a YAML validator)
- Ensure all required fields are present
- Verify the file is in the correct subdirectory
- Check for duplicate AIR identifiers

### Download fails
- Test the download URL manually with `wget` or `curl`
- Verify the target directory path is correct
- Check if the file requires authentication (use alternative download method)
- Ensure sufficient disk space on the target instance

### Resource displays incorrectly
- Verify the `type` field matches the resource category
- Check that the `ecosystem` value is one of the supported ecosystems
- Ensure the `title` field is in quotes if it contains special characters
- Validate that `size` is an integer (no quotes, no commas)

## API Integration

Resources defined here are automatically parsed and made available through:
- **REST API**: `/resources/list` endpoint with filtering
- **Web UI**: Resource Manager tab with search and selection
- **Installer**: Background task that downloads selected resources to instances

The resource parser (`app/resources/resource_parser.py`) reads these markdown files and extracts metadata for display and installation.

---

For questions or issues, refer to the main project documentation or open an issue on GitHub.
