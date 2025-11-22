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

echo "🔧 Setting up SSH directory at $SSH_DIR"

# 1. Ensure .ssh directory exists
mkdir -p "$SSH_DIR"

# Permissions for directory (owner full, group read/exec so SMB user can traverse)
chmod 750 "$SSH_DIR"

# 2. Generate a keypair if missing
if [[ ! -f "$KEY_FILE" ]]; then
    echo "⚡ Generating new ed25519 keypair..."
    ssh-keygen -t ed25519 -a 100 -C "media-sync@qnap" -f "$KEY_FILE" -N ""
else
    echo "✅ Existing SSH keypair found"
fi

# 3. Ensure public key exists
if [[ ! -f "$PUB_FILE" ]]; then
    echo "❌ Missing public key. Generating from private..."
    ssh-keygen -y -f "$KEY_FILE" > "$PUB_FILE"
fi

# 4. Create host key files
touch "$KNOWN_HOSTS" "$VAST_KNOWN_HOSTS"

# 5. Apply strict permissions
chmod 600 "$KEY_FILE"                 # private key
chmod 644 "$PUB_FILE"                 # public key
chmod 644 "$KNOWN_HOSTS"              # static LAN hosts
chmod 664 "$VAST_KNOWN_HOSTS"         # writable for VastAI dynamic hosts

# 6. Create default SSH config if missing
if [[ ! -f "$CONFIG_FILE" ]]; then
    cat > "$CONFIG_FILE" <<'EOF'
# ── Forge (LAN) ───────────────────────────────
Host forge
  HostName 10.0.78.108
  Port 2222
  User root
  IdentityFile /root/.ssh/id_ed25519
  IdentitiesOnly yes
  UserKnownHostsFile /root/.ssh/known_hosts
  StrictHostKeyChecking yes

# ── Comfy (LAN) ───────────────────────────────
Host comfy
  HostName 10.0.78.108
  Port 2223
  User root
  IdentityFile /root/.ssh/id_ed25519
  IdentitiesOnly yes
  UserKnownHostsFile /root/.ssh/known_hosts
  StrictHostKeyChecking yes

# ── VastAI (cloud) ────────────────────────────
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
echo "  1. Copy $PUB_FILE to Forge/Comfy with ssh-copy-id (ports 2222, 2223)."
echo "  2. For VastAI, copy $PUB_FILE into your instance at launch or via ssh-copy-id."
echo "  3. Update docker-compose.yml with the .ssh mounts we configured."
