#!/bin/bash
# setup_ssh.sh - Prepare project-local SSH directory for Media Sync Tool
# Run this inside vast_api/ on your QNAP NAS.

set -euo pipefail

SSH_DIR="./.ssh"
KEY_FILE="$SSH_DIR/id_ed25519"
PUB_FILE="$KEY_FILE.pub"
KNOWN_HOSTS="$SSH_DIR/known_hosts"
VAST_KNOWN_HOSTS="$SSH_DIR/vast_known_hosts"
CONFIG_FILE="$SSH_DIR/config"

echo "🔧 Setting up project-local SSH directory at $SSH_DIR"

# 1. Ensure .ssh directory exists with correct perms
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

# 2. Generate a keypair if missing
if [[ ! -f "$KEY_FILE" ]]; then
    echo "⚡ Generating new ed25519 keypair..."
    ssh-keygen -t ed25519 -a 100 -C "media-sync@qnap" -f "$KEY_FILE" -N ""
else
    echo "✅ Existing SSH keypair found"
fi

# 3. Touch known_hosts files
touch "$KNOWN_HOSTS" "$VAST_KNOWN_HOSTS"

# 4. Apply correct permissions
chmod 600 "$KEY_FILE" "$VAST_KNOWN_HOSTS"
chmod 644 "$PUB_FILE" "$KNOWN_HOSTS"

# 5. Create a default ssh_config if missing
if [[ ! -f "$CONFIG_FILE" ]]; then
    cat > "$CONFIG_FILE" <<'EOF'
# Static LAN targets
Host forge
  HostName 10.0.78.108
  Port 2222
  User root
  IdentityFile /root/.ssh/id_ed25519
  IdentitiesOnly yes
  UserKnownHostsFile /root/.ssh/known_hosts
  StrictHostKeyChecking yes

Host comfy
  HostName 10.0.78.108
  Port 2223
  User root
  IdentityFile /root/.ssh/id_ed25519
  IdentitiesOnly yes
  UserKnownHostsFile /root/.ssh/known_hosts
  StrictHostKeyChecking yes

# VastAI cloud hosts
Host vast-*
  User ubuntu
  IdentityFile /root/.ssh/id_ed25519
  IdentitiesOnly yes
  UserKnownHostsFile /root/.ssh/vast_known_hosts
  StrictHostKeyChecking accept-new
EOF
    chmod 644 "$CONFIG_FILE"
    echo "⚡ Created default SSH config at $CONFIG_FILE"
else
    echo "✅ SSH config already exists"
fi

echo "🎉 SSH setup complete!"
echo "Next steps:"
echo "  - Copy $PUB_FILE to your Forge/Comfy/VastAI hosts using ssh-copy-id"
echo "  - Mount .ssh into the container via docker-compose.yml"

