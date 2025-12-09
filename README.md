# Media Sync Tool

An easy-to-use tool for syncing media from local Docker containers and VastAI cloud VMs. Provides a web API interface designed for deployment on QNAP NAS.

> **🎉 NEW: Redesigned Sync System Available!**  
> See [SYNC_REDESIGN_README.md](SYNC_REDESIGN_README.md) for the new v2 API with real-time progress, WebSocket support, and enhanced performance.

## Features

- 🔥 **Sync Forge**: Sync from Stable Diffusion WebUI Forge (10.0.78.108:2222)
- 🖼️ **Sync ComfyUI**: Sync from ComfyUI (10.0.78.108:2223)  
- ☁️ **Sync VastAI**: Auto-discover running VastAI instance and sync
- 🏠 **Local ComfyUI Support**: Execute workflows on ComfyUI installed on your host machine (NEW!)
- 📦 **Resource Manager**: Browse and install workflows, models, and assets to VastAI instances
- 🐳 **Docker Ready**: Containerized for easy deployment on QNAP NAS
- 🌐 **Web API**: REST endpoints for web interface
- ⚡ **Fast Sync**: Manifest-based change detection (v2)
- 📊 **Live Progress**: Real-time WebSocket updates (v2)
- 🧹 **Auto Cleanup**: Configurable old media purge (v2)

## Quick Start

### Prerequisites

1. SSH key setup (`~/.ssh/id_ed25519`) for passwordless access to sync targets
2. VastAI API key (optional, for VastAI sync)
3. Docker and Docker Compose

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd vast_api
   ```

2. **Add VastAI API key** (optional):
   ```bash
   echo "your_vast_api_key_here" > api_key.txt
   ```

3. **Configure sync paths** in `config.yaml` if needed

4. **Deploy with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

### Manual Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the API server**:
   ```bash
   python sync_api.py
   ```

## API Endpoints

### Sync Operations

- `POST /sync/forge` - Sync from Forge (10.0.78.108:2222)
- `POST /sync/comfy` - Sync from ComfyUI (10.0.78.108:2223)
- `POST /sync/vastai` - Auto-discover VastAI instance and sync

### Resource Management

- `GET /resources/list` - List available resources with optional filtering
  - Query params: `type`, `ecosystem`, `tags`, `search`
- `GET /resources/get/<path>` - Get details of a specific resource
- `POST /resources/install` - Install resources to remote instance
  - Body: `{ "ssh_connection": "root@host:port", "resources": [...], "ui_home": "/workspace/ComfyUI" }`
- `GET /resources/ecosystems` - Get list of available ecosystems
- `GET /resources/types` - Get list of available resource types
- `GET /resources/tags` - Get list of available tags
- `GET /resources/search?q=<query>` - Search resources by query string

### Status

- `GET /status` - Get status of all sync targets
- `GET /` - Web interface for testing

### Example Response

```json
{
  "success": true,
  "message": "Forge sync completed successfully",
  "output": "sync operation details..."
}
```

## Configuration

### SSH Setup

Ensure passwordless SSH access to your sync targets:

```bash
# Generate SSH key if not exists
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519

# Copy public key to targets
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@10.0.78.108 -p 2222
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@10.0.78.108 -p 2223
```

### Local Paths

The sync script uses these default paths (configurable in `sync_outputs.sh`):

- **Local base**: `/mnt/qnap-sd/SecretFolder`
- **Remote base**: Auto-detected from `UI_HOME` environment variable
- **Synced folders**: `txt2img-grids`, `txt2img-images`, `img2img-grids`, `img2img-images`, `WAN`, `extras-images`

### VastAI Configuration

Edit `config.yaml` to configure VastAI templates and preferences:

```yaml
template_hash_id: b3a852d995cac99809607b2f52a2fe36  # ComfyUI template
ui_home_env: /workspace/ComfyUI
disk_size_gb: 100
```

## Docker Deployment on QNAP

1. **Enable SSH and Container Station** on your QNAP
2. **Copy project files** to your QNAP
3. **Setup SSH keys**:
   ```bash
   # Run the setup script to create SSH keys and configuration
   ./setup_ssh.sh
   ```
4. **Create API key file**:
   ```bash
   echo "your_vast_api_key_here" > api_key.txt
   ```
5. **Adjust volume mounts** in `docker-compose.yml` for your QNAP paths
6. **Deploy**:
   ```bash
   docker compose up -d
   ```

### QNAP Volume Mapping

The `docker-compose.yml` is pre-configured for QNAP with the following volume mappings:

```yaml
volumes:
  # SSH files (project-local)
  - ./.ssh/id_ed25519:/root/.ssh/id_ed25519:ro
  - ./.ssh/id_ed25519.pub:/root/.ssh/id_ed25519.pub:ro
  - ./.ssh/known_hosts:/root/.ssh/known_hosts:ro
  - ./.ssh/config:/root/.ssh/config:ro
  - ./.ssh/vast_known_hosts:/root/.ssh/vast_known_hosts

  # QNAP media share (adjust path as needed)
  - /share/sd/SecretFolder:/media

  # VastAI API key
  - ./api_key.txt:/app/api_key.txt:ro
```

**Important**: 
- SSH files are stored locally in the project's `.ssh/` directory (run `./setup_ssh.sh` to create them)
- Adjust `/share/sd/SecretFolder` to match your QNAP media share path
- Container runs as `PUID=0` and `PGID=0` for media folder access

## Resource Manager

The Resource Manager provides a centralized system for browsing, filtering, and installing workflows, models, and other assets to VastAI instances.

### Features

- 📦 **Resource Library**: Curated collection of workflows, models, LoRAs, upscalers, and more
- 🔍 **Smart Filtering**: Filter by ecosystem (FLUX, SDXL, WAN, etc.), type, and tags
- 🔎 **Search**: Full-text search across resource descriptions
- ⚡ **Quick Install**: One-click installation to remote instances via SSH
- 📊 **Dependency Tracking**: Automatic dependency resolution (coming soon)
- 🖼️ **Preview Images**: Visual preview of resources

### Using the Resource Manager

1. **Access the Web UI**: Navigate to `http://<your-nas-ip>:5000` in your browser
2. **Go to Resource Manager Tab**: Click the "📦 Resource Manager" tab
3. **Browse Resources**: View available resources in the grid layout
4. **Filter Resources**: Use dropdowns to filter by ecosystem or type
5. **Search**: Use the search box to find specific resources
6. **Select Resources**: Click "Select" on resources you want to install
7. **Install**: Enter your SSH connection string and click "Install Selected"

### Resource Types

- **workflow**: ComfyUI workflow JSON files
- **checkpoint**: Base models and checkpoints (SDXL, FLUX, etc.)
- **lora**: LoRA (Low-Rank Adaptation) models for style transfer
- **vae**: VAE encoders for better image quality
- **upscaler**: Upscaling models (RealESRGAN, etc.)
- **controlnet**: ControlNet models for guided generation

### Supported Ecosystems

- **wan**: WAN Video models for video generation
- **flux**: FLUX models for high-quality image generation
- **sdxl**: Stable Diffusion XL models
- **sd15**: Stable Diffusion 1.5 models
- **realesrgan**: Real-ESRGAN upscaling models
- **other**: General-purpose models

### Adding Custom Resources

Resources are defined in markdown files in the `resources/` directory. See [resources/README.md](resources/README.md) for detailed documentation on the format.

Example resource definition:

```markdown
---
tags: [workflow, text2img]
ecosystem: flux
basemodel: flux-schnell
type: workflow
version: v1.0
---

# My Custom Workflow

Description of the workflow...

### Download
\`\`\`bash
wget -P "$UI_HOME/user/default/workflows" \
  https://example.com/workflow.json
\`\`\`
```

### Current Resource Library

The library includes:
- 3 workflows (WAN, FLUX, SD 1.5)
- 3 LoRAs (WAN, FLUX, SDXL)
- 2 upscalers (RealESRGAN)
- 1 checkpoint (SDXL base)
- 1 VAE (SDXL)

## Local ComfyUI Support (NEW!)

Execute workflows on a ComfyUI installation that's local to your Docker host machine - no cloud GPUs needed!

### Why Use Local Support?

- 💰 **Free**: No cloud GPU rental costs
- 🚀 **Fast**: No network latency to remote servers
- 🔒 **Private**: Your data never leaves your machine
- 🎯 **Convenient**: Use your existing ComfyUI setup

### Quick Setup

**Linux:**
```bash
sudo ./scripts/setup-local-host-linux.sh --comfyui-path /home/user/ComfyUI
```

**Windows:**
```powershell
.\scripts\setup-local-host-windows.bat -ComfyUIPath "C:\Users\username\ComfyUI"
```

The script will:
1. ✅ Install and configure SSH server
2. ✅ Create dedicated user with secure access
3. ✅ Generate SSH keys
4. ✅ Configure firewall rules
5. ✅ Generate configuration files

Then just mount the config in your `docker-compose.yml`:
```yaml
volumes:
  - ./local-support-config.yml:/app/local-support-config.yml:ro
  - ./local_host_key:/root/.ssh/local_host_key:ro
```

Restart the container and your local instance appears in the connection toolbar! 🎉

### Documentation

- 📖 **Quick Start Guide**: [docs/LOCAL_COMFYUI_QUICK_START.md](docs/LOCAL_COMFYUI_QUICK_START.md)
- 📋 **Full Proposal**: [docs/LOCAL_COMFYUI_SUPPORT_PROPOSAL.md](docs/LOCAL_COMFYUI_SUPPORT_PROPOSAL.md)
- ⚙️ **Config Example**: [local-support-config.yml.example](local-support-config.yml.example)

### Features

- ✅ Workflow execution on local GPU
- ✅ Resource installation (models, custom nodes, etc.)
- ✅ Output syncing back to container
- ✅ Appears alongside VastAI instances in UI
- ✅ Secure SSH-based communication
- ✅ Automated setup scripts for Linux and Windows

## Troubleshooting

### Common Issues

1. **SSH Connection Failed**: Verify SSH keys and network connectivity
2. **VastAI Instance Not Found**: Check API key and ensure instance is running
3. **Sync Script Not Found**: Ensure `sync_outputs.sh` is executable
4. **Permission Denied**: Check file/directory permissions and SSH key access

### Logs

View container logs:
```bash
docker-compose logs -f media-sync-api
```

## Security Notes

- Keep SSH private keys secure and read-only
- Store VastAI API key securely
- Use firewall rules to restrict API access
- Consider using HTTPS in production

## License

[Add your license here]