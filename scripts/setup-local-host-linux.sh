#!/bin/bash
#
# Local ComfyUI Support Setup Script for Linux
#
# This script configures a Linux host to allow the Media Sync Tool Docker container
# to execute workflows on a local ComfyUI installation via SSH.
#
# Requirements:
#   - Root or sudo access
#   - ComfyUI installed on the host
#   - OpenSSH server package available
#   - Linux kernel 3.10+ (for Docker compatibility)
#
# Usage:
#   sudo ./setup-local-host-linux.sh --comfyui-path /path/to/ComfyUI [options]
#
# Options:
#   --comfyui-path PATH     Path to ComfyUI installation (required)
#   --ssh-port PORT         SSH port to use (default: 22022)
#   --ssh-user USER         SSH username (default: comfyui)
#   --docker-network CIDR   Docker network CIDR (default: 172.17.0.0/16)
#   --output-dir DIR        Where to save generated files (default: current directory)
#   --test-only             Only test existing configuration
#   --uninstall             Remove local support setup
#   --help                  Show this help message
#

set -e  # Exit on error

# Default values
SSH_PORT=22022
SSH_USER="comfyui"
DOCKER_NETWORK="172.17.0.0/16"
OUTPUT_DIR="$(pwd)"
COMFYUI_PATH=""
TEST_ONLY=false
UNINSTALL=false
LOG_FILE="/var/log/comfyui-local-setup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Show help message
show_help() {
    cat << EOF
Local ComfyUI Support Setup Script for Linux

This script configures your Linux host to allow the Media Sync Tool Docker
container to execute workflows on your local ComfyUI installation.

USAGE:
    sudo $0 --comfyui-path /path/to/ComfyUI [options]

REQUIRED:
    --comfyui-path PATH     Path to ComfyUI installation directory

OPTIONS:
    --ssh-port PORT         SSH port (default: 22022)
    --ssh-user USER         SSH username (default: comfyui)
    --docker-network CIDR   Docker network range (default: 172.17.0.0/16)
    --output-dir DIR        Output directory for files (default: current dir)
    --test-only             Test existing setup without changes
    --uninstall             Remove local support configuration
    --help                  Show this help message

EXAMPLES:
    # Basic setup
    sudo $0 --comfyui-path /home/myuser/ComfyUI

    # Custom SSH port and user
    sudo $0 --comfyui-path /home/myuser/ComfyUI --ssh-port 23000 --ssh-user comfy

    # Test existing configuration
    sudo $0 --test-only

    # Remove setup
    sudo $0 --uninstall

WHAT THIS SCRIPT DOES:
    1. Validates prerequisites and ComfyUI installation
    2. Installs OpenSSH server if needed
    3. Creates dedicated SSH user with restricted permissions
    4. Generates SSH key pair for container authentication
    5. Configures SSH server on alternate port
    6. Sets up firewall rules for Docker network access
    7. Generates local-support-config.yml configuration file
    8. Tests the SSH connection

OUTPUT FILES:
    - local-support-config.yml  Configuration for container
    - local_host_key            SSH private key for container (mount as volume)
    - local_host_key.pub        SSH public key (for reference)

SECURITY NOTES:
    - SSH key-based authentication only (no passwords)
    - Dedicated user with minimal permissions
    - Firewall restricted to Docker network
    - SSH runs on non-standard port

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --comfyui-path)
                COMFYUI_PATH="$2"
                shift 2
                ;;
            --ssh-port)
                SSH_PORT="$2"
                shift 2
                ;;
            --ssh-user)
                SSH_USER="$2"
                shift 2
                ;;
            --docker-network)
                DOCKER_NETWORK="$2"
                shift 2
                ;;
            --output-dir)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --test-only)
                TEST_ONLY=true
                shift
                ;;
            --uninstall)
                UNINSTALL=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                error "Unknown option: $1. Use --help for usage information."
                ;;
        esac
    done
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
    fi
}

# Check if running inside Docker container
check_not_in_container() {
    if [ -f /.dockerenv ]; then
        error "This script must be run on the HOST machine, not inside the Docker container"
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Linux
    if [[ ! "$OSTYPE" == "linux-gnu"* ]]; then
        error "This script is for Linux only. Use setup-local-host-windows.bat for Windows."
    fi
    
    # Check required commands
    local required_cmds="ssh-keygen useradd systemctl"
    for cmd in $required_cmds; do
        if ! command -v "$cmd" &> /dev/null; then
            error "Required command not found: $cmd"
        fi
    done
    
    log "Prerequisites check passed"
}

# Validate ComfyUI installation
validate_comfyui() {
    if [[ -z "$COMFYUI_PATH" ]]; then
        error "ComfyUI path is required. Use --comfyui-path option."
    fi
    
    log "Validating ComfyUI installation at: $COMFYUI_PATH"
    
    if [[ ! -d "$COMFYUI_PATH" ]]; then
        error "ComfyUI directory not found: $COMFYUI_PATH"
    fi
    
    # Check for main.py or server.py (ComfyUI entry point)
    if [[ ! -f "$COMFYUI_PATH/main.py" ]] && [[ ! -f "$COMFYUI_PATH/server.py" ]]; then
        error "ComfyUI main.py or server.py not found in: $COMFYUI_PATH"
    fi
    
    log "ComfyUI installation validated"
}

# Install OpenSSH server
install_ssh_server() {
    log "Checking OpenSSH server installation..."
    
    if command -v sshd &> /dev/null; then
        log "OpenSSH server already installed"
        return 0
    fi
    
    log "Installing OpenSSH server..."
    
    # Detect package manager
    if command -v apt-get &> /dev/null; then
        apt-get update -qq
        apt-get install -y openssh-server
    elif command -v yum &> /dev/null; then
        yum install -y openssh-server
    elif command -v dnf &> /dev/null; then
        dnf install -y openssh-server
    elif command -v pacman &> /dev/null; then
        pacman -S --noconfirm openssh
    else
        error "Unable to determine package manager. Please install openssh-server manually."
    fi
    
    log "OpenSSH server installed successfully"
}

# Create dedicated SSH user
create_ssh_user() {
    log "Creating dedicated SSH user: $SSH_USER"
    
    if id "$SSH_USER" &>/dev/null; then
        warn "User $SSH_USER already exists. Skipping user creation."
        return 0
    fi
    
    # Create user with no shell (for security)
    useradd -r -m -s /usr/sbin/nologin -c "ComfyUI Local Container Access" "$SSH_USER"
    
    # Create .ssh directory
    mkdir -p "/home/$SSH_USER/.ssh"
    chmod 700 "/home/$SSH_USER/.ssh"
    
    log "User $SSH_USER created successfully"
}

# Generate SSH keys
generate_ssh_keys() {
    log "Generating SSH key pair..."
    
    local key_path="$OUTPUT_DIR/local_host_key"
    
    if [[ -f "$key_path" ]]; then
        warn "SSH key already exists at $key_path"
        read -p "Overwrite existing key? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Using existing SSH key"
            return 0
        fi
    fi
    
    # Generate ED25519 key (modern, secure, fast)
    if ! ssh-keygen -t ed25519 -f "$key_path" -N "" -C "comfyui-local-container@$(hostname)"; then
        error "Failed to generate SSH key. Check that ssh-keygen is installed and you have write permissions."
    fi
    
    # Set proper permissions
    chmod 600 "$key_path"
    chmod 644 "$key_path.pub"
    
    # Copy public key to authorized_keys
    mkdir -p "/home/$SSH_USER/.ssh"
    cp "$key_path.pub" "/home/$SSH_USER/.ssh/authorized_keys"
    chmod 600 "/home/$SSH_USER/.ssh/authorized_keys"
    chown -R "$SSH_USER:$SSH_USER" "/home/$SSH_USER/.ssh"
    
    log "SSH keys generated and configured"
    info "Private key: $key_path"
    info "Public key: $key_path.pub"
}

# Configure SSH server
configure_ssh_server() {
    log "Configuring SSH server..."
    
    local config_file="/etc/ssh/sshd_config.local_comfyui"
    
    # Create SSH config for local ComfyUI access
    cat > "$config_file" << EOF
# SSH Configuration for Local ComfyUI Container Access
# Generated by setup-local-host-linux.sh on $(date)

# Port and network binding
Port $SSH_PORT
ListenAddress 127.0.0.1
ListenAddress 172.17.0.1

# Authentication
PubkeyAuthentication yes
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM no
PermitRootLogin no

# User restrictions
AllowUsers $SSH_USER

# Security
X11Forwarding no
AllowTcpForwarding no
AllowAgentForwarding no
PermitTunnel no
GatewayPorts no

# Session
MaxSessions 5
MaxStartups 5:50:10

# Logging
LogLevel INFO
SyslogFacility AUTH

# Host keys
HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_ecdsa_key
HostKey /etc/ssh/ssh_host_ed25519_key
EOF
    
    log "SSH configuration created: $config_file"
    
    # Create systemd service
    create_systemd_service
}

# Create systemd service
create_systemd_service() {
    log "Creating systemd service..."
    
    local service_file="/etc/systemd/system/sshd-local-comfyui.service"
    
    cat > "$service_file" << EOF
[Unit]
Description=OpenSSH Server for Local ComfyUI Container Access
After=network.target
Documentation=man:sshd(8) man:sshd_config(5)

[Service]
Type=notify
ExecStart=/usr/sbin/sshd -D -f /etc/ssh/sshd_config.local_comfyui
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=process
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable sshd-local-comfyui.service
    systemctl restart sshd-local-comfyui.service
    
    log "Systemd service created and started"
}

# Configure firewall
configure_firewall() {
    log "Configuring firewall..."
    
    # Check which firewall is in use
    if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
        configure_ufw
    elif command -v firewall-cmd &> /dev/null && systemctl is-active firewalld &> /dev/null; then
        configure_firewalld
    elif command -v iptables &> /dev/null; then
        configure_iptables
    else
        warn "No firewall detected. Skipping firewall configuration."
        warn "Please manually allow port $SSH_PORT from Docker network $DOCKER_NETWORK"
    fi
}

# Configure UFW (Ubuntu/Debian)
configure_ufw() {
    log "Configuring UFW firewall..."
    
    # Allow from Docker network
    ufw allow from "$DOCKER_NETWORK" to any port "$SSH_PORT" proto tcp comment "ComfyUI Local Container"
    
    # Allow from localhost
    ufw allow from 127.0.0.1 to any port "$SSH_PORT" proto tcp
    
    log "UFW rules added"
}

# Configure firewalld (RHEL/Fedora)
configure_firewalld() {
    log "Configuring firewalld..."
    
    # Create rich rule for Docker network
    firewall-cmd --permanent --add-rich-rule="rule family=ipv4 source address=$DOCKER_NETWORK port port=$SSH_PORT protocol=tcp accept"
    firewall-cmd --reload
    
    log "Firewalld rules added"
}

# Configure iptables (fallback)
configure_iptables() {
    log "Configuring iptables..."
    
    # Allow from Docker network
    iptables -A INPUT -s "$DOCKER_NETWORK" -p tcp --dport "$SSH_PORT" -j ACCEPT
    
    # Allow from localhost
    iptables -A INPUT -s 127.0.0.1 -p tcp --dport "$SSH_PORT" -j ACCEPT
    
    # Save rules (method depends on distribution)
    if command -v iptables-save &> /dev/null; then
        iptables-save > /etc/iptables/rules.v4 2>/dev/null || true
    fi
    
    warn "iptables rules added but may not persist after reboot"
    warn "Consider using iptables-persistent or saving rules manually"
}

# Set file permissions
set_permissions() {
    log "Setting file permissions..."
    
    # Give SSH user access to ComfyUI directory
    # Add to the same group as the ComfyUI files owner
    local comfyui_owner=$(stat -c '%U' "$COMFYUI_PATH")
    local comfyui_group=$(stat -c '%G' "$COMFYUI_PATH")
    
    log "ComfyUI owned by: $comfyui_owner:$comfyui_group"
    
    # Add SSH user to ComfyUI owner's group
    if [[ "$comfyui_group" != "$SSH_USER" ]]; then
        usermod -a -G "$comfyui_group" "$SSH_USER" || warn "Could not add $SSH_USER to group $comfyui_group"
    fi
    
    # Ensure key directories have correct permissions
    chmod 755 "$COMFYUI_PATH"
    
    log "Permissions configured"
}

# Generate configuration file
generate_config() {
    log "Generating local-support-config.yml..."
    
    local config_file="$OUTPUT_DIR/local-support-config.yml"
    
    # Detect if using Docker Desktop or Docker Engine
    # Note: This detection is best-effort. Verify the host address works for your setup.
    local docker_host="host.docker.internal"
    if ! grep -q "docker" /proc/1/cgroup 2>/dev/null; then
        # Running on host, likely Docker Engine (use bridge IP)
        docker_host="172.17.0.1"
    fi
    
    warn "Detected Docker host: $docker_host"
    warn "If you're using a custom Docker network, update the 'host' value in local-support-config.yml"
    
    cat > "$config_file" << EOF
# Local ComfyUI Support Configuration
# Generated by setup-local-host-linux.sh on $(date)
# Host: $(hostname)

local_support:
  # Enable local support (set to true to activate)
  enabled: true
  
  # Display name in UI
  display_name: "Local ComfyUI ($(hostname))"
  
  # SSH connection details
  ssh:
    # Host address (adjust if needed)
    # - Use "host.docker.internal" for Docker Desktop
    # - Use "172.17.0.1" for Docker Engine on Linux
    host: "$docker_host"
    
    # SSH port
    port: $SSH_PORT
    
    # SSH username
    username: "$SSH_USER"
    
    # Path to private key inside container (mount as volume)
    private_key: "/root/.ssh/local_host_key"
    
  # ComfyUI installation details
  comfyui:
    # Path to ComfyUI installation
    home: "$COMFYUI_PATH"
    
    # Python executable
    python_path: "python3"
    
    # ComfyUI API port
    api_port: 8188
    
    # Auto-start ComfyUI if not running
    auto_start: true
    
  # File system paths
  paths:
    output_sync_path: "$COMFYUI_PATH/output"
    models_path: "$COMFYUI_PATH/models"
    custom_nodes_path: "$COMFYUI_PATH/custom_nodes"
    
  # Features
  features:
    workflow_execution: true
    resource_installation: true
    output_sync: true
    
  # Limits
  limits:
    max_concurrent_workflows: 1
    max_upload_size_mb: 10000
    workflow_timeout_seconds: 3600
EOF
    
    log "Configuration file generated: $config_file"
    info ""
    info "Next steps:"
    info "1. Copy local-support-config.yml to your Docker project directory"
    info "2. Copy local_host_key to your Docker project directory"
    info "3. Update docker-compose.yml to mount these files:"
    info "   volumes:"
    info "     - ./local-support-config.yml:/app/local-support-config.yml:ro"
    info "     - ./local_host_key:/root/.ssh/local_host_key:ro"
    info "4. Restart the Docker container"
}

# Test SSH connection
test_connection() {
    log "Testing SSH connection..."
    
    local key_path="$OUTPUT_DIR/local_host_key"
    local test_host="127.0.0.1"  # Test from localhost
    
    if [[ ! -f "$key_path" ]]; then
        error "SSH key not found at $key_path"
    fi
    
    # Test connection
    if ssh -i "$key_path" -p "$SSH_PORT" -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
        "$SSH_USER@$test_host" "echo 'Connection successful'" 2>/dev/null; then
        log "✅ SSH connection test PASSED"
        
        # Test ComfyUI directory access
        if ssh -i "$key_path" -p "$SSH_PORT" -o StrictHostKeyChecking=no \
            "$SSH_USER@$test_host" "ls -la '$COMFYUI_PATH'" &>/dev/null; then
            log "✅ ComfyUI directory access test PASSED"
        else
            warn "⚠️  Cannot access ComfyUI directory. Check permissions."
        fi
    else
        error "❌ SSH connection test FAILED"
    fi
}

# Test existing configuration
test_existing() {
    log "Testing existing configuration..."
    
    # Check if service is running
    if systemctl is-active sshd-local-comfyui.service &> /dev/null; then
        log "✅ SSH service is running"
    else
        error "❌ SSH service is not running"
    fi
    
    # Check if user exists
    if id "$SSH_USER" &>/dev/null; then
        log "✅ SSH user exists"
    else
        error "❌ SSH user does not exist"
    fi
    
    # Check if key exists
    if [[ -f "$OUTPUT_DIR/local_host_key" ]]; then
        log "✅ SSH key exists"
        test_connection
    else
        error "❌ SSH key not found at $OUTPUT_DIR/local_host_key"
    fi
}

# Uninstall local support
uninstall() {
    log "Uninstalling local ComfyUI support..."
    
    # Stop and disable service
    if systemctl is-active sshd-local-comfyui.service &> /dev/null; then
        systemctl stop sshd-local-comfyui.service
        systemctl disable sshd-local-comfyui.service
        log "Service stopped and disabled"
    fi
    
    # Remove service file
    rm -f /etc/systemd/system/sshd-local-comfyui.service
    systemctl daemon-reload
    
    # Remove SSH config
    rm -f /etc/ssh/sshd_config.local_comfyui
    
    # Remove firewall rules
    if command -v ufw &> /dev/null; then
        ufw delete allow from "$DOCKER_NETWORK" to any port "$SSH_PORT" || true
    fi
    
    # Ask about removing user
    read -p "Remove SSH user $SSH_USER? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        userdel -r "$SSH_USER" 2>/dev/null || warn "Could not remove user $SSH_USER"
        log "User $SSH_USER removed"
    fi
    
    log "Uninstallation complete"
}

# Main execution
main() {
    echo "========================================"
    echo "Local ComfyUI Support Setup for Linux"
    echo "========================================"
    echo ""
    
    parse_args "$@"
    
    # Create log file
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    
    check_root
    check_not_in_container
    check_prerequisites
    
    if [[ "$UNINSTALL" == true ]]; then
        uninstall
        exit 0
    fi
    
    if [[ "$TEST_ONLY" == true ]]; then
        test_existing
        exit 0
    fi
    
    validate_comfyui
    install_ssh_server
    create_ssh_user
    generate_ssh_keys
    configure_ssh_server
    configure_firewall
    set_permissions
    generate_config
    test_connection
    
    echo ""
    log "✅ Setup complete!"
    info ""
    info "Configuration files created:"
    info "  - $OUTPUT_DIR/local-support-config.yml"
    info "  - $OUTPUT_DIR/local_host_key (private key)"
    info "  - $OUTPUT_DIR/local_host_key.pub (public key)"
    info ""
    info "SSH service running on port $SSH_PORT"
    info ""
    info "See the configuration file for next steps."
}

# Run main function
main "$@"
