# Asset Catalog Download Detection Syntax Rules

## Overview

This document defines the syntax requirements for asset catalog pages to support automated download detection. Download detection allows the system to check if assets have been downloaded to a specific instance.

## Test Fixture

**Location**: `test_catalog_fixture.csv`

**Statistics** (as of 2026-01-15):
- Total catalog pages: 207
- Valid for download detection: 57 (27.5%)
- Pages with AIR identifiers: 167 (80.7%)
- Pages with download commands: 85 (41.1%)

## Syntax Types

### 1. CIVITDL_WITH_AIR ✅ (Preferred)
**Count**: 53 pages (25.6%)  
**Status**: Valid for download detection

**Requirements**:
- Has AIR identifier in YAML frontmatter
- Has civitdl download command in bash code block
- AIR civitai ID matches URL in civitdl command

**Example**:
```markdown
---
AIR: urn:air:sdxl:lora:civitai:1327644@1498986
---

### 📥 Download

\```bash
civitdl "https://civitai.com/models/1327644?modelVersionId=1498986" "$UI_HOME"/models/Lora
\```
```

**Detection Logic**:
- Extract version ID from AIR: `1498986`
- Search for files matching pattern: `*1498986*.safetensors`
- Look in path: `$UI_HOME/models/Lora`

---

### 2. WGET_WITH_AIR ✅ (Supported)
**Count**: 4 pages (1.9%)  
**Status**: Valid for download detection (with manual validation)

**Requirements**:
- Has AIR identifier in YAML frontmatter
- Has wget download command with `-P` or `-O` flag

**Example**:
```markdown
---
AIR: urn:air:sdxl:encoder:huggingface:stabilityai/stable-diffusion-xl-base-1.0@main/sd_xl_base_1.0.safetensors
---

### Download

\```bash
wget -P "$UI_HOME"/models/VAE \
  https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
\```
```

**Detection Logic**:
- Extract filename from AIR or URL
- Search for exact filename in target directory

---

### 3. CIVITDL_NO_AIR ⚠️ (Incomplete)
**Count**: 5 pages (2.4%)  
**Status**: Invalid - Missing AIR identifier

**Issue**: Cannot generate filename pattern without AIR identifier

**Example of Invalid Page**:
```markdown
---
# Missing AIR field!
---

### Download

\```bash
civitdl "https://civitai.com/models/1327644?modelVersionId=1498986" "$UI_HOME"/models/Lora
\```
```

**Fix**: Add AIR identifier to frontmatter matching the civitai URL

---

### 4. WGET_NO_AIR ⚠️ (Incomplete)
**Count**: 23 pages (11.1%)  
**Status**: Invalid - Missing AIR identifier

**Issue**: Cannot validate filename without AIR identifier

**Example of Invalid Page**:
```markdown
---
# Missing AIR field!
---

### Download

\```bash
wget -P "$UI_HOME"/models/VAE \
  https://example.com/model.safetensors
\```
```

**Fix**: Add AIR identifier to frontmatter

---

### 5. NO_DOWNLOAD ❌ (Not Applicable)
**Count**: 121 pages (58.5%)  
**Status**: Not applicable for download detection

**Reason**: No download command present (category pages, informational pages, etc.)

**Examples**:
- Category landing pages (e.g., `LoRAs.md`)
- Embeddings without direct downloads
- Reference documentation

---

### 6. INVALID ❌ (Error)
**Count**: 1 page (0.5%)  
**Status**: Failed to parse

**Reason**: File unreadable or malformed

---

## Required Elements for Download Detection

### 1. AIR Identifier (Asset Identifier Reference)

**Format**: `urn:air:<ecosystem>:<type>:<source>:<id>@<version>`

**Examples**:
- CivitAI: `urn:air:sdxl:lora:civitai:1327644@1498986`
- HuggingFace: `urn:air:flux:encoder:huggingface:black-forest-labs/FLUX.1-dev@main/ae.safetensors`

**Purpose**:
- Uniquely identifies the asset
- Used to generate filename search patterns
- Validates download command matches intended asset

**Location**: YAML frontmatter
```yaml
---
AIR: urn:air:sdxl:lora:civitai:1327644@1498986
---
```

### 2. Download Command

**Supported Commands**:

#### A. civitdl (Preferred)
```bash
civitdl "https://civitai.com/models/{model_id}?modelVersionId={version_id}" "$UI_HOME"/{target_path}
```

**Pattern**: Files named with format: `{name}_{model_id}-vid_{version_id}.{ext}`

#### B. wget with -P flag
```bash
wget -P "$UI_HOME"/{target_path} \
  {url}
```

**Pattern**: Filename extracted from URL

#### C. wget with -O flag
```bash
wget -O "$UI_HOME"/{full_path} \
  {url}
```

**Pattern**: Exact path specified

### 3. Code Block Formatting

**Required**: Bash code block with proper markdown fencing

```markdown
### 📥 Download

\```bash
civitdl "https://civitai.com/models/1327644?modelVersionId=1498986" "$UI_HOME"/models/Lora
\```
```

**Common Headers**:
- `### 📥 Download`
- `### Download`
- `#### Download`

---

## Validation Algorithm

```python
def validate_catalog_page(content: str) -> bool:
    """
    Returns True if page is valid for download detection
    """
    # 1. Check for AIR identifier
    air_match = re.search(r'AIR:\s*urn:air:\w+:\w+:\w+:\d+@\d+', content)
    if not air_match:
        return False
    
    # 2. Check for download command
    code_blocks = re.findall(r'```(?:bash)?\n(.*?)\n```', content, re.DOTALL)
    has_download = False
    
    for block in code_blocks:
        if re.search(r'civitdl|wget', block):
            has_download = True
            break
    
    if not has_download:
        return False
    
    # 3. For civitdl, validate AIR matches URL
    air_id = re.search(r'civitai:(\d+)@', air_match.group(0))
    if air_id:
        for block in code_blocks:
            civitdl_url = re.search(r'civitai\.com/models/(\d+)', block)
            if civitdl_url and civitdl_url.group(1) == air_id.group(1):
                return True
    
    # For wget, just having AIR and command is sufficient
    return True
```

---

## Detection Process

### Step 1: Parse Catalog Page
1. Extract AIR identifier from frontmatter
2. Parse AIR to get version ID (for CivitAI) or filename (for HuggingFace)
3. Extract download command and target path

### Step 2: Generate Search Pattern
For CivitAI:
```python
civitai_id, version_id = parse_air("urn:air:sdxl:lora:civitai:1327644@1498986")
patterns = [f"*{version_id}*.safetensors", f"*{version_id}*.ckpt"]
```

For HuggingFace:
```python
filename = extract_filename_from_air("urn:air:flux:encoder:huggingface:org/repo@branch/file.safetensors")
patterns = [filename]
```

### Step 3: Check Instance
```bash
ssh -p {port} root@{host} 'find "$UI_HOME/{target_path}" -maxdepth 2 -name "{pattern}"'
```

### Step 4: Return Status
- **Found**: Return file path
- **Not Found**: Return None

---

## Test Coverage

### Validated Pages (57 total)
- **CIVITDL_WITH_AIR**: 53 pages ready for testing
- **WGET_WITH_AIR**: 4 pages ready for testing

### Test Strategy
1. Select representative samples from each category
2. Test against multiple instances (Forge, ComfyUI)
3. Verify both positive (downloaded) and negative (not downloaded) cases
4. Document edge cases and failures

### Test Fixture Fields

| Field | Description |
|-------|-------------|
| `file_path` | Full path to catalog markdown file |
| `syntax_type` | Syntax classification (see above) |
| `tested` | "Yes" if tested, "No" if not |
| `is_valid` | True if passes validation for download detection |
| `air` | AIR identifier (if present) |
| `download_count` | Number of download commands found |
| `notes` | Validation notes or issues |

---

## Next Steps

1. **Run Tests**: Execute download detection on all 57 valid pages
2. **Update CSV**: Mark tested pages and record results
3. **Fix Invalid Pages**: Add missing AIR identifiers where possible
4. **Implement API**: Create `/api/catalog/check-downloads` endpoint
5. **Add UI Indicators**: Show download status badges on catalog tiles
