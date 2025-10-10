#!/bin/bash
#
# SSH connection validation and retry utility for sync operations
#

validate_ssh_key() {
    local ssh_key="$1"
    local host="$2"
    local port="$3"
    local user="${4:-root}"
    
    echo "🔑 Validating SSH key and connection..."
    
    # Check if SSH key exists
    if [[ ! -f "$ssh_key" ]]; then
        echo "❌ SSH key not found at $ssh_key"
        return 1
    fi
    
    # Check SSH key permissions
    local perms=$(stat -c %a "$ssh_key" 2>/dev/null)
    if [[ "$perms" != "600" ]]; then
        echo "⚠️  SSH key permissions are $perms, should be 600. Fixing..."
        chmod 600 "$ssh_key" || {
            echo "❌ Failed to fix SSH key permissions"
            return 1
        }
    fi
    
    # Test SSH connection without ssh-agent first
    echo "🧪 Testing direct SSH connection..."
    if ssh -p "$port" -i "$ssh_key" \
           -o UserKnownHostsFile=/root/.ssh/known_hosts \
           -o IdentitiesOnly=yes \
           -o StrictHostKeyChecking=yes \
           -o ConnectTimeout=10 \
           -o BatchMode=yes \
           "$user@$host" 'echo "SSH direct connection successful"' >/dev/null 2>&1; then
        echo "✅ Direct SSH connection successful"
        return 0
    else
        echo "❌ Direct SSH connection failed"
        return 1
    fi
}

setup_ssh_agent_robust() {
    local ssh_key="$1"
    local max_retries=3
    local retry_count=0
    
    while [[ $retry_count -lt $max_retries ]]; do
        echo "🔧 Setting up SSH agent (attempt $((retry_count + 1))/$max_retries)..."
        
        # Kill any existing ssh-agent
        ssh-agent -k >/dev/null 2>&1 || true
        
        # Start fresh ssh-agent
        eval "$(ssh-agent -s)" || {
            echo "❌ Failed to start ssh-agent"
            ((retry_count++))
            sleep 2
            continue
        }
        
        echo "Agent pid $SSH_AGENT_PID"
        
        # Add SSH key with timeout
        if timeout 10 ssh-add "$ssh_key" >/dev/null 2>&1; then
            echo "✅ SSH key added successfully"
            return 0
        else
            echo "❌ Failed to add SSH key (attempt $((retry_count + 1)))"
            ssh-agent -k >/dev/null 2>&1 || true
            ((retry_count++))
            sleep 2
        fi
    done
    
    echo "❌ Failed to set up SSH agent after $max_retries attempts"
    return 1
}

test_ssh_with_agent() {
    local host="$1"
    local port="$2"
    local user="${3:-root}"
    
    echo "🧪 Testing SSH connection with agent..."
    
    if ssh -p "$port" \
           -o UserKnownHostsFile=/root/.ssh/known_hosts \
           -o IdentitiesOnly=yes \
           -o StrictHostKeyChecking=yes \
           -o ConnectTimeout=10 \
           -o BatchMode=yes \
           "$user@$host" 'echo "SSH agent connection successful"' >/dev/null 2>&1; then
        echo "✅ SSH agent connection successful"
        return 0
    else
        echo "❌ SSH agent connection failed"
        return 1
    fi
}

# Export functions for use in sync_outputs.sh
export -f validate_ssh_key
export -f setup_ssh_agent_robust  
export -f test_ssh_with_agent