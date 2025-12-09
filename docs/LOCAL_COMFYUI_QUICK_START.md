# Local ComfyUI Support - Quick Start Guide

This guide will help you set up local ComfyUI support in under 15 minutes.

## Overview

Local ComfyUI support allows the Media Sync Tool Docker container to execute workflows on a ComfyUI installation that's already running on your host machine. This means:

- ✅ No need to rent expensive cloud GPUs
- ✅ Use your existing local ComfyUI setup
- ✅ Free workflow execution on your own hardware
- ✅ Access all the same features as cloud instances

## Prerequisites

Before you begin, ensure you have:

1. **ComfyUI installed on your host machine**
   - Linux: Typically in `/home/user/ComfyUI`
   - Windows: Typically in `C:\Users\username\ComfyUI`

2. **Docker Desktop or Docker Engine running**
   - With the Media Sync Tool container deployed

3. **Administrator/sudo access on your host**
   - Required to configure SSH server

4. **15 minutes of time** ⏱️
   - Setup is automated but requires some configuration

## Setup Steps

### For Linux Users 🐧

1. **Download the setup script** (if not already cloned)
   ```bash
   cd /path/to/vast_api
   ```

2. **Run the setup script**
   ```bash
   sudo ./scripts/setup-local-host-linux.sh --comfyui-path /home/user/ComfyUI
   ```
   
   Replace `/home/user/ComfyUI` with your actual ComfyUI path.

3. **Follow the prompts**
   - The script will:
     - Install OpenSSH server (if needed)
     - Create a dedicated SSH user
     - Generate SSH keys
     - Configure firewall rules
     - Generate configuration files

4. **Copy the generated files**
   ```bash
   # The script creates these files in the current directory:
   # - local-support-config.yml
   # - local_host_key
   # - local_host_key.pub
   
   # Copy them to your Docker project directory
   cp local-support-config.yml /path/to/vast_api/
   cp local_host_key /path/to/vast_api/
   ```

5. **Update docker-compose.yml**
   
   Add these volume mounts to your `docker-compose.yml`:
   ```yaml
   services:
     media-sync-api:
       volumes:
         # ... existing volumes ...
         - ./local-support-config.yml:/app/local-support-config.yml:ro
         - ./local_host_key:/root/.ssh/local_host_key:ro
       extra_hosts:
         - "host.docker.internal:host-gateway"
   ```

6. **Restart the container**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

7. **Done!** 🎉
   - Open the web UI
   - You should see your local instance in the connection toolbar
   - Click on it to select and test the connection

### For Windows Users 🪟

1. **Open PowerShell as Administrator**
   - Right-click PowerShell → "Run as Administrator"

2. **Navigate to the project directory**
   ```powershell
   cd C:\path\to\vast_api
   ```

3. **Run the setup script**
   ```powershell
   .\scripts\setup-local-host-windows.bat -ComfyUIPath "C:\Users\username\ComfyUI"
   ```
   
   Replace the path with your actual ComfyUI installation path.

4. **Follow the prompts**
   - The script will:
     - Install OpenSSH Server Windows feature
     - Create a dedicated Windows user
     - Generate SSH keys
     - Configure firewall rules
     - Generate configuration files

5. **Copy the generated files**
   ```powershell
   # The script creates these files in the current directory:
   # - local-support-config.yml
   # - local_host_key
   # - local_host_key.pub
   
   # They're already in your project directory, so no need to copy
   ```

6. **Update docker-compose.yml**
   
   Add these volume mounts to your `docker-compose.yml`:
   ```yaml
   services:
     media-sync-api:
       volumes:
         # ... existing volumes ...
         - ./local-support-config.yml:/app/local-support-config.yml:ro
         - ./local_host_key:/root/.ssh/local_host_key:ro
   ```

7. **Restart the container**
   ```powershell
   docker-compose down
   docker-compose up -d
   ```

8. **Done!** 🎉
   - Open the web UI at http://localhost:5000
   - You should see your local instance in the connection toolbar
   - Click on it to select and test the connection

## Verifying the Setup

### 1. Check SSH Service

**Linux:**
```bash
sudo systemctl status sshd-local-comfyui
```

**Windows:**
```powershell
Get-Service sshd-local-comfyui
```

### 2. Test SSH Connection

**From your host machine:**
```bash
# Linux
ssh -i local_host_key -p 22022 comfyui@127.0.0.1 "echo Connected"

# Windows (in PowerShell)
ssh -i local_host_key -p 22022 comfyui_service@127.0.0.1 "echo Connected"
```

If you see "Connected", SSH is working! ✅

### 3. Check Container Access

**From inside the Docker container:**
```bash
docker exec -it media-sync-api ssh -i /root/.ssh/local_host_key -p 22022 comfyui@host.docker.internal "echo Connected"
```

### 4. Verify in Web UI

1. Open the web UI: http://localhost:5000
2. Look at the connection toolbar at the top
3. You should see a tile labeled "Local ComfyUI (your-hostname)"
4. The tile should show:
   - 🏠 icon (indicating local)
   - Status: "local"
   - Connection: host.docker.internal:22022
   - Cost: $0.00/hr (FREE)
5. Click "Select" to choose the local instance
6. Click "Test" to verify connectivity

If the test passes, you're all set! 🎉

## Using Your Local Instance

### Executing Workflows

1. **Go to the Workflow Executor tab**
2. **Make sure your local instance is selected** in the connection toolbar
3. **Choose a workflow** from the available templates
4. **Configure the workflow parameters**
5. **Click "Execute Workflow"**
6. **Monitor progress** in real-time
7. **View outputs** when complete

### Installing Resources

1. **Go to the Resource Manager tab**
2. **Select your local instance** in the connection toolbar
3. **Browse or search for resources**
   - Models (checkpoints, LoRAs, VAEs)
   - Custom nodes
   - Upscalers
4. **Click "Install"** on desired resources
5. **Wait for installation** to complete
6. **Resources are now available** in ComfyUI

### Managing Custom Nodes

1. **Select your local instance**
2. **Go to the Workflow Executor tab**
3. **Use the "Install Custom Nodes" option**
4. **Monitor installation progress**
5. **Restart ComfyUI** if needed (some nodes require restart)

## Troubleshooting

### Problem: "Cannot connect to local instance"

**Solutions:**
1. Check SSH service is running (see verification steps above)
2. Verify firewall rules allow Docker network access
3. Test SSH connection manually
4. Check the `local-support-config.yml` has correct paths
5. Ensure SSH key has correct permissions (600)

### Problem: "Permission denied" errors

**Solutions:**
1. Verify the SSH user has access to ComfyUI directory
2. Check file ownership and permissions
3. On Linux: `sudo chown -R comfyui:comfyui /path/to/ComfyUI`
4. On Windows: Check ACL permissions for the user

### Problem: "ComfyUI not found" or "main.py not found"

**Solutions:**
1. Verify `comfyui.home` path in `local-support-config.yml`
2. Ensure path uses Unix-style slashes (even on Windows)
3. Test: `ssh -i local_host_key -p 22022 user@host "ls /path/to/ComfyUI"`

### Problem: "Connection timeout"

**Solutions:**
1. Check Docker network configuration
2. Verify `host.docker.internal` resolves correctly
3. On Linux, try using `172.17.0.1` instead
4. Check if SSH port is firewalled

### Problem: "Key authentication failed"

**Solutions:**
1. Verify key file is mounted in container: 
   ```bash
   docker exec -it media-sync-api ls -la /root/.ssh/local_host_key
   ```
2. Check key permissions are 600
3. Verify public key is in authorized_keys on host
4. Re-run setup script to regenerate keys

### Getting More Help

1. **Check the logs:**
   - Linux: `/var/log/comfyui-local-setup.log`
   - Windows: `C:\ProgramData\comfyui-local-setup.log`
   - Container: `docker logs media-sync-api`

2. **Run setup script in test mode:**
   ```bash
   # Linux
   sudo ./scripts/setup-local-host-linux.sh --test-only
   
   # Windows
   .\scripts\setup-local-host-windows.bat -TestOnly
   ```

3. **Check the full proposal document:**
   - See `docs/LOCAL_COMFYUI_SUPPORT_PROPOSAL.md`

4. **Open an issue on GitHub:**
   - Include setup logs
   - Include error messages
   - Describe your environment (OS, Docker version, etc.)

## Security Notes

### What was configured?

1. **SSH Server on alternate port (22022)**
   - Only accessible from localhost and Docker network
   - Uses key-based authentication only (no passwords)

2. **Dedicated SSH user**
   - Limited permissions
   - No shell access (Linux)
   - Can only access ComfyUI directory

3. **Firewall rules**
   - Restricts access to Docker network range
   - Blocks external connections

### Best Practices

1. **Keep SSH keys secure**
   - Never commit them to git
   - Store with restricted permissions (600)
   - Rotate periodically

2. **Monitor access logs**
   - Linux: `journalctl -u sshd-local-comfyui`
   - Windows: Event Viewer → Applications and Services Logs → OpenSSH

3. **Regular updates**
   - Keep OpenSSH server updated
   - Apply security patches promptly

4. **Backup your keys**
   - Store `local_host_key` securely
   - If lost, re-run setup script

### Uninstalling

If you want to remove local support:

**Linux:**
```bash
sudo ./scripts/setup-local-host-linux.sh --uninstall
```

**Windows:**
```powershell
.\scripts\setup-local-host-windows.bat -Uninstall
```

This will:
- Stop and remove the SSH service
- Remove firewall rules
- Optionally remove the SSH user
- Clean up configuration files

## Advanced Configuration

### Custom SSH Port

If port 22022 is already in use:

```bash
# Linux
sudo ./scripts/setup-local-host-linux.sh --comfyui-path /path --ssh-port 23000

# Windows
.\scripts\setup-local-host-windows.bat -ComfyUIPath C:\path -SSHPort 23000
```

Then update `local-support-config.yml`:
```yaml
ssh:
  port: 23000
```

### Custom SSH User

```bash
# Linux
sudo ./scripts/setup-local-host-linux.sh --comfyui-path /path --ssh-user myuser

# Windows
.\scripts\setup-local-host-windows.bat -ComfyUIPath C:\path -SSHUser myuser
```

### Multiple ComfyUI Installations

To use multiple ComfyUI installations:

1. Run setup script multiple times with different ports and users
2. Create multiple configuration files
3. Switch between them by mounting different configs
4. Or manually edit `local-support-config.yml` as needed

### Using with Docker Engine on Linux

If using Docker Engine (not Desktop) on Linux:

1. Update `local-support-config.yml`:
   ```yaml
   ssh:
     host: "172.17.0.1"  # Instead of host.docker.internal
   ```

2. Ensure SSH server listens on Docker bridge IP:
   ```
   ListenAddress 172.17.0.1
   ```

3. Update firewall to allow from Docker bridge network

## FAQ

### Q: Does this work with WSL2?

**A:** Yes! If ComfyUI is in WSL2, run the Linux setup script inside WSL2, then configure Docker Desktop to access it.

### Q: Can I use this with a remote host?

**A:** The scripts are designed for localhost. For remote hosts, manually configure SSH with proper security and update the config file.

### Q: Does this affect my existing ComfyUI setup?

**A:** No! This only adds SSH access. Your ComfyUI installation remains unchanged.

### Q: Can I still use VastAI instances?

**A:** Yes! Local and cloud instances appear side-by-side in the UI. Switch between them as needed.

### Q: What's the performance difference vs cloud?

**A:** Performance depends on your local GPU. The workflow execution itself is the same.

### Q: Can multiple containers access the same host?

**A:** Yes, but ensure each uses different SSH keys and configuration.

### Q: Is this secure?

**A:** Yes, when configured correctly. The setup uses industry-standard SSH security practices.

### Q: How much does it cost?

**A:** Local execution is **FREE**! No VastAI charges. You only pay for your electricity. ⚡

---

## Summary

You now have local ComfyUI support configured! 🎉

**What you can do:**
- ✅ Execute workflows on your local GPU
- ✅ Install resources and custom nodes
- ✅ Sync outputs back to container
- ✅ Save money on cloud GPU rentals
- ✅ Use familiar ComfyUI setup

**Next steps:**
- Try executing a simple workflow
- Install some models or custom nodes
- Explore the Resource Manager
- Check out the full proposal for advanced features

**Need help?**
- Check the troubleshooting section above
- Read the full proposal: `docs/LOCAL_COMFYUI_SUPPORT_PROPOSAL.md`
- Open an issue on GitHub

Happy workflow executing! 🚀
