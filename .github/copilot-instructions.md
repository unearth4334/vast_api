# GitHub Copilot Instructions

## Container Management

### Checking Container Status on QNAP

When checking container status on the QNAP NAS, ensure proper PATH setup to access Docker commands:

```bash
ssh qnap 'export PATH=$PATH:/share/CACHEDEV1_DATA/.qpkg/container-station/bin:/usr/sbin:/sbin; cd /share/Container/vast_api && docker logs media-sync-api'
```

This command:
- Exports the PATH to include Container Station binaries and system utilities
- Changes to the vast_api container directory
- Runs docker commands (e.g., `docker logs`, `docker ps`, `docker inspect`)

Replace `docker logs media-sync-api` with other docker commands as needed, such as:
- `docker ps -a` - List all containers
- `docker inspect <container-name>` - Detailed container information
- `docker exec -it <container-name> /bin/bash` - Access container shell
