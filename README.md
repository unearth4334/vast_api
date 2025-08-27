# Media Sync Tool

An easy-to-use tool for syncing media from local Docker containers and VastAI cloud VMs. Provides a web API interface designed for deployment on QNAP NAS and integration with Obsidian notes via dataviewjs.

## Features

- 🔥 **Sync Forge**: Sync from Stable Diffusion WebUI Forge (10.0.78.108:2222)
- 🖼️ **Sync ComfyUI**: Sync from ComfyUI (10.0.78.108:2223)  
- ☁️ **Sync VastAI**: Auto-discover running VastAI instance and sync
- 🐳 **Docker Ready**: Containerized for easy deployment on QNAP NAS
- 🌐 **Web API**: REST endpoints for integration with Obsidian dataviewjs

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

## Obsidian Integration

Use dataviewjs code in your Obsidian notes:

```javascript
const API_BASE = "http://your-nas-ip:5000";

// Create sync buttons
const buttons = [
    { name: "🔥 Sync Forge", endpoint: "/sync/forge" },
    { name: "🖼️ Sync Comfy", endpoint: "/sync/comfy" },
    { name: "☁️ Sync VastAI", endpoint: "/sync/vastai" }
];

buttons.forEach(button => {
    const btn = dv.el("button", button.name);
    btn.addEventListener("click", async () => {
        btn.textContent = "Syncing...";
        try {
            const response = await fetch(API_BASE + button.endpoint, { method: "POST" });
            const data = await response.json();
            btn.textContent = data.success ? "✅ Done" : "❌ Failed";
            setTimeout(() => btn.textContent = button.name, 3000);
        } catch (error) {
            btn.textContent = "❌ Error";
            setTimeout(() => btn.textContent = button.name, 3000);
        }
    });
});
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