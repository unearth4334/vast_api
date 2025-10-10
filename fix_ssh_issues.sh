#!/bin/bash
# fix_ssh_issues.sh - Diagnose and fix SSH connectivity issues for the vast_api sync system

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SSH_DIR="/root/.ssh"
SSH_KEY="$SSH_DIR/id_ed25519"
SSH_PUB_KEY="$SSH_KEY.pub"
KNOWN_HOSTS="$SSH_DIR/known_hosts"
VAST_KNOWN_HOSTS="$SSH_DIR/vast_known_hosts"
SSH_CONFIG="$SSH_DIR/config"

# Target hosts
FORGE_HOST="10.0.78.108"
FORGE_PORT="2222"
COMFY_HOST="10.0.78.108"
COMFY_PORT="2223"

echo -e "${BLUE}=== VastAI SSH Connection Fix Script ===${NC}"
echo -e "${BLUE}This script will diagnose and fix SSH connectivity issues${NC}"
echo

# Check if running in container
if [[ -f /.dockerenv ]]; then
    echo -e "${GREEN}✅ Running inside Docker container${NC}"
else
    echo -e "${YELLOW}⚠️  Not running in Docker container - this may not work as expected${NC}"
fi

echo

# Function to fix permissions
fix_permissions() {
    echo -e "${BLUE}🔧 Fixing SSH directory and key permissions...${NC}"
    
    if [[ -d "$SSH_DIR" ]]; then
        chmod 700 "$SSH_DIR"
        echo -e "${GREEN}✅ SSH directory permissions fixed (700)${NC}"
    else
        echo -e "${RED}❌ SSH directory not found at $SSH_DIR${NC}"
        return 1
    fi
    
    if [[ -f "$SSH_KEY" ]]; then
        chmod 600 "$SSH_KEY"
        echo -e "${GREEN}✅ Private key permissions fixed (600)${NC}"
    else
        echo -e "${RED}❌ Private key not found at $SSH_KEY${NC}"
        return 1
    fi
    
    if [[ -f "$SSH_PUB_KEY" ]]; then
        chmod 644 "$SSH_PUB_KEY"
        echo -e "${GREEN}✅ Public key permissions fixed (644)${NC}"
    fi
    
    if [[ -f "$KNOWN_HOSTS" ]]; then
        chmod 644 "$KNOWN_HOSTS"
        echo -e "${GREEN}✅ Known hosts permissions fixed (644)${NC}"
    fi
    
    if [[ -f "$VAST_KNOWN_HOSTS" ]]; then
        chmod 664 "$VAST_KNOWN_HOSTS"
        echo -e "${GREEN}✅ Vast known hosts permissions fixed (664)${NC}"
    fi
    
    return 0
}

# Function to test SSH connection
test_ssh_connection() {
    local host="$1"
    local port="$2"
    local name="$3"
    
    echo -e "${BLUE}🧪 Testing SSH connection to $name ($host:$port)...${NC}"
    
    if ssh -p "$port" -i "$SSH_KEY" \
           -o UserKnownHostsFile="$KNOWN_HOSTS" \
           -o IdentitiesOnly=yes \
           -o StrictHostKeyChecking=yes \
           -o ConnectTimeout=10 \
           -o BatchMode=yes \
           "root@$host" 'echo "Connection successful"' >/dev/null 2>&1; then
        echo -e "${GREEN}✅ $name connection successful${NC}"
        return 0
    else
        echo -e "${RED}❌ $name connection failed${NC}"
        return 1
    fi
}

# Function to test SSH agent
test_ssh_agent() {
    echo -e "${BLUE}🔧 Testing SSH agent functionality...${NC}"
    
    # Kill any existing agent
    ssh-agent -k >/dev/null 2>&1 || true
    
    # Start new agent
    eval "$(ssh-agent -s)" || {
        echo -e "${RED}❌ Failed to start SSH agent${NC}"
        return 1
    }
    
    echo -e "${GREEN}✅ SSH agent started (PID: $SSH_AGENT_PID)${NC}"
    
    # Add key
    if ssh-add "$SSH_KEY" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ SSH key added to agent${NC}"
        
        # List keys
        echo -e "${BLUE}📋 Keys in agent:${NC}"
        ssh-add -l
        
        ssh-agent -k >/dev/null 2>&1
        return 0
    else
        echo -e "${RED}❌ Failed to add SSH key to agent${NC}"
        ssh-agent -k >/dev/null 2>&1
        return 1
    fi
}

# Function to show SSH configuration
show_ssh_config() {
    echo -e "${BLUE}📋 SSH Configuration Status:${NC}"
    echo
    
    echo -e "${BLUE}SSH Directory:${NC} $SSH_DIR"
    if [[ -d "$SSH_DIR" ]]; then
        echo -e "  Status: ${GREEN}✅ Exists${NC}"
        echo -e "  Permissions: $(stat -c %a "$SSH_DIR")"
    else
        echo -e "  Status: ${RED}❌ Missing${NC}"
    fi
    echo
    
    echo -e "${BLUE}Private Key:${NC} $SSH_KEY"
    if [[ -f "$SSH_KEY" ]]; then
        echo -e "  Status: ${GREEN}✅ Exists${NC}"
        echo -e "  Permissions: $(stat -c %a "$SSH_KEY")"
        echo -e "  Size: $(stat -c %s "$SSH_KEY") bytes"
    else
        echo -e "  Status: ${RED}❌ Missing${NC}"
    fi
    echo
    
    echo -e "${BLUE}Public Key:${NC} $SSH_PUB_KEY"
    if [[ -f "$SSH_PUB_KEY" ]]; then
        echo -e "  Status: ${GREEN}✅ Exists${NC}"
        echo -e "  Permissions: $(stat -c %a "$SSH_PUB_KEY")"
    else
        echo -e "  Status: ${RED}❌ Missing${NC}"
    fi
    echo
    
    echo -e "${BLUE}Known Hosts:${NC} $KNOWN_HOSTS"
    if [[ -f "$KNOWN_HOSTS" ]]; then
        echo -e "  Status: ${GREEN}✅ Exists${NC}"
        echo -e "  Entries: $(wc -l < "$KNOWN_HOSTS")"
    else
        echo -e "  Status: ${RED}❌ Missing${NC}"
    fi
    echo
}

# Main diagnostic and fix routine
main() {
    echo -e "${BLUE}🔍 Starting SSH diagnostics...${NC}"
    echo
    
    # Show current status
    show_ssh_config
    
    # Fix permissions
    if fix_permissions; then
        echo -e "${GREEN}✅ Permissions fixed${NC}"
    else
        echo -e "${RED}❌ Failed to fix permissions${NC}"
        exit 1
    fi
    echo
    
    # Test SSH agent
    if test_ssh_agent; then
        echo -e "${GREEN}✅ SSH agent working${NC}"
    else
        echo -e "${RED}❌ SSH agent issues${NC}"
    fi
    echo
    
    # Test connections
    forge_ok=false
    comfy_ok=false
    
    if test_ssh_connection "$FORGE_HOST" "$FORGE_PORT" "Forge"; then
        forge_ok=true
    fi
    
    if test_ssh_connection "$COMFY_HOST" "$COMFY_PORT" "ComfyUI"; then
        comfy_ok=true
    fi
    echo
    
    # Summary
    echo -e "${BLUE}=== Summary ===${NC}"
    if $forge_ok; then
        echo -e "${GREEN}✅ Forge connection: Working${NC}"
    else
        echo -e "${RED}❌ Forge connection: Failed${NC}"
    fi
    
    if $comfy_ok; then
        echo -e "${GREEN}✅ ComfyUI connection: Working${NC}"
    else
        echo -e "${RED}❌ ComfyUI connection: Failed${NC}"
    fi
    echo
    
    if $forge_ok && $comfy_ok; then
        echo -e "${GREEN}🎉 All SSH connections are working!${NC}"
        echo -e "${GREEN}The sync functionality should work correctly.${NC}"
    else
        echo -e "${YELLOW}⚠️  Some connections failed.${NC}"
        echo -e "${YELLOW}Please check:${NC}"
        echo -e "${YELLOW}1. SSH keys are properly copied to target hosts${NC}"
        echo -e "${YELLOW}2. Target hosts are accessible from this container${NC}"
        echo -e "${YELLOW}3. Known hosts entries are correct${NC}"
        echo
        echo -e "${BLUE}To copy SSH key to targets:${NC}"
        echo -e "${YELLOW}ssh-copy-id -i $SSH_PUB_KEY root@$FORGE_HOST -p $FORGE_PORT${NC}"
        echo -e "${YELLOW}ssh-copy-id -i $SSH_PUB_KEY root@$COMFY_HOST -p $COMFY_PORT${NC}"
    fi
}

# Handle command line arguments
case "${1:-}" in
    --check-only)
        show_ssh_config
        exit 0
        ;;
    --fix-permissions)
        fix_permissions
        exit 0
        ;;
    --test-agent)
        test_ssh_agent
        exit 0
        ;;
    --test-connections)
        test_ssh_connection "$FORGE_HOST" "$FORGE_PORT" "Forge"
        test_ssh_connection "$COMFY_HOST" "$COMFY_PORT" "ComfyUI"
        exit 0
        ;;
    --help)
        echo "Usage: $0 [option]"
        echo "Options:"
        echo "  --check-only        Show SSH configuration status only"
        echo "  --fix-permissions   Fix SSH file permissions only"
        echo "  --test-agent        Test SSH agent functionality only"
        echo "  --test-connections  Test SSH connections only"
        echo "  --help              Show this help message"
        echo ""
        echo "Run without arguments to perform full diagnostics and fixes."
        exit 0
        ;;
    "")
        main
        ;;
    *)
        echo "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac