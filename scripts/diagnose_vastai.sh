#!/bin/bash

# VastAI Connection Diagnostics Script
# Usage: ./diagnose_vastai.sh <ssh_connection_string>
# Example: ./diagnose_vastai.sh "ssh -p 28276 root@39.114.238.31 -L 8080:localhost:8080"

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to parse SSH connection string
parse_ssh_connection() {
    local ssh_string="$1"
    
    # Extract port
    if [[ $ssh_string =~ -p[[:space:]]+([0-9]+) ]]; then
        SSH_PORT="${BASH_REMATCH[1]}"
    else
        SSH_PORT="22"
    fi
    
    # Extract host
    if [[ $ssh_string =~ root@([0-9.]+|[a-zA-Z0-9.-]+) ]]; then
        SSH_HOST="${BASH_REMATCH[1]}"
    else
        log_error "Could not extract host from SSH connection string"
        exit 1
    fi
}

# Function to test network connectivity
test_network() {
    local host="$1"
    local port="$2"
    
    log_info "Testing network connectivity to $host:$port"
    
    # Test 1: Ping
    log_info "Running ping test..."
    if ping -c 3 -W 5 "$host" >/dev/null 2>&1; then
        log_success "Ping test: Host $host is reachable"
    else
        log_warning "Ping test: Host $host is not responding to ping (this may be normal)"
    fi
    
    # Test 2: Port connectivity
    log_info "Testing port connectivity..."
    if command -v nc >/dev/null 2>&1; then
        if nc -z -w 5 "$host" "$port" 2>/dev/null; then
            log_success "Port test: SSH port $port is accessible on $host"
            return 0
        else
            log_error "Port test: SSH port $port is NOT accessible on $host"
            return 1
        fi
    elif command -v telnet >/dev/null 2>&1; then
        if timeout 5 telnet "$host" "$port" >/dev/null 2>&1; then
            log_success "Port test: SSH port $port is accessible on $host"
            return 0
        else
            log_error "Port test: SSH port $port is NOT accessible on $host"
            return 1
        fi
    else
        log_warning "Neither nc (netcat) nor telnet is available for port testing"
        return 2
    fi
}

# Function to test SSH connectivity
test_ssh() {
    local host="$1"
    local port="$2"
    
    log_info "Testing SSH connectivity to $host:$port"
    
    local ssh_cmd="ssh -p $port -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o BatchMode=yes root@$host echo 'SSH connection successful'"
    
    if eval "$ssh_cmd" >/dev/null 2>&1; then
        log_success "SSH test: Connection successful to $host:$port"
        return 0
    else
        log_error "SSH test: Connection failed to $host:$port"
        
        # Try to get more detailed error information
        local error_output
        error_output=$(eval "$ssh_cmd" 2>&1 || true)
        
        if [[ $error_output == *"Connection refused"* ]]; then
            log_error "SSH Error: Connection refused"
            echo "  → The SSH service might not be running on the target host"
            echo "  → Check if the VastAI instance is running and SSH is enabled"
            echo "  → Verify the port number is correct"
        elif [[ $error_output == *"Permission denied"* ]]; then
            log_error "SSH Error: Permission denied"
            echo "  → SSH authentication failed"
            echo "  → Check if SSH keys are properly configured"
            echo "  → Verify the public key is installed on the VastAI instance"
        elif [[ $error_output == *"No route to host"* ]]; then
            log_error "SSH Error: No route to host"
            echo "  → Network connectivity issue"
            echo "  → Check if the host IP address is correct"
            echo "  → Verify network routing and firewall settings"
        elif [[ $error_output == *"Connection timed out"* ]]; then
            log_error "SSH Error: Connection timed out"
            echo "  → The host might be unreachable or overloaded"
            echo "  → Check firewall settings"
            echo "  → The instance might be starting up"
        else
            log_error "SSH Error: Unknown error"
            echo "  → Error details: $error_output"
        fi
        
        return 1
    fi
}

# Function to provide recommendations
provide_recommendations() {
    local network_ok="$1"
    local ssh_ok="$2"
    
    echo
    log_info "=== RECOMMENDATIONS ==="
    
    if [[ $network_ok == "0" ]] && [[ $ssh_ok == "0" ]]; then
        log_success "All tests passed! Your VastAI connection should work properly."
        echo "  → You can now use the UI_HOME setup buttons in the web interface"
        echo "  → SSH connection string appears to be valid and working"
    elif [[ $network_ok == "0" ]] && [[ $ssh_ok != "0" ]]; then
        log_warning "Network connectivity is OK, but SSH authentication failed"
        echo "  → Check SSH key configuration:"
        echo "    - Ensure SSH keys are properly mounted in Docker"
        echo "    - Verify private key permissions are 600"
        echo "    - Check if public key is installed on VastAI instance"
        echo "  → Try connecting manually: ssh -p $SSH_PORT root@$SSH_HOST"
    elif [[ $network_ok != "0" ]]; then
        log_error "Network connectivity issues detected"
        echo "  → Check if the VastAI instance is running:"
        echo "    - Log into vast.ai and check instance status"
        echo "    - Ensure the instance is not stopped or terminated"
        echo "    - Wait a few minutes if the instance is starting up"
        echo "  → Verify the connection string:"
        echo "    - Double-check the IP address and port number"
        echo "    - Get a fresh SSH connection string from vast.ai"
        echo "  → Network troubleshooting:"
        echo "    - Try from a different network if possible"
        echo "    - Check for firewall or VPN interference"
    fi
}

# Main function
main() {
    local ssh_connection="$1"
    
    if [[ -z "$ssh_connection" ]]; then
        echo "Usage: $0 <ssh_connection_string>"
        echo "Example: $0 \"ssh -p 28276 root@39.114.238.31 -L 8080:localhost:8080\""
        exit 1
    fi
    
    log_info "=== VastAI CONNECTION DIAGNOSTICS ==="
    log_info "Connection string: $ssh_connection"
    echo
    
    # Parse the SSH connection string
    parse_ssh_connection "$ssh_connection"
    log_info "Parsed connection: $SSH_HOST:$SSH_PORT"
    echo
    
    # Test network connectivity
    test_network "$SSH_HOST" "$SSH_PORT"
    local network_result=$?
    echo
    
    # Test SSH connectivity
    test_ssh "$SSH_HOST" "$SSH_PORT"
    local ssh_result=$?
    echo
    
    # Provide recommendations
    provide_recommendations "$network_result" "$ssh_result"
}

# Run the main function with all arguments
main "$@"