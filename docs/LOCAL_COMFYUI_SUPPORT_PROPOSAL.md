# Local ComfyUI Support - Feature Proposal

## Executive Summary

This proposal outlines the design and implementation plan for adding support to execute workflows on a ComfyUI installation that is local to the container host. This feature enables users who already have ComfyUI installed on their host machine to leverage this Docker container's workflow execution capabilities without needing to rent a VastAI instance.

## Problem Statement

Currently, the Media Sync Tool is designed to work exclusively with:
- Remote VastAI cloud instances
- Local Docker containers (Forge at port 2222, ComfyUI at port 2223)

Users who have ComfyUI installed directly on their host machine (outside of Docker) cannot use the workflow execution features of this tool. This creates a gap for users who:
1. Want to use the tool's workflow management and resource installation features
2. Already have a working ComfyUI installation on their host
3. Don't want to pay for cloud instances or run duplicate local containers

## Proposed Solution

### Overview

Add an optional configuration system that allows the Docker container to connect to a ComfyUI installation on the host machine via SSH. The host will run a minimal SSH server that the container can connect to for executing workflows and managing resources.

### Key Components

1. **Local Support Configuration File** (`local-support-config.yml`)
2. **Host Setup Script for Linux** (`setup-local-host-linux.sh`)
3. **Host Setup Script for Windows** (`setup-local-host-windows.bat`)
4. **Container Integration** (modifications to existing codebase)
5. **UI Integration** (instance tile in connection toolbar)

## Detailed Design

### 1. Configuration File: `local-support-config.yml`

**Location:** `/home/runner/work/vast_api/vast_api/local-support-config.yml`

**Purpose:** Store all configuration needed to connect to the host's ComfyUI installation.

**Structure:**

```yaml
# Local ComfyUI Support Configuration
# This file enables the container to execute workflows on a ComfyUI installation
# that is local to the container host.

local_support:
  # Enable or disable local support (default: false)
  enabled: false
  
  # Display name for the local instance in the UI
  display_name: "Local ComfyUI (Host)"
  
  # SSH connection details for host
  ssh:
    # Host address - use host.docker.internal for Docker Desktop
    # or the actual host IP for Linux hosts
    host: "host.docker.internal"
    
    # SSH port on the host (default: 22022 to avoid conflicts)
    port: 22022
    
    # SSH username for connection
    username: "comfyui"
    
    # Path to SSH private key inside container
    # This should be mounted as a volume
    private_key: "/root/.ssh/local_host_key"
    
  # ComfyUI installation details on host
  comfyui:
    # Full path to ComfyUI installation on host
    home: "/home/user/ComfyUI"
    
    # Python executable path (for running workflows)
    python_path: "python3"
    
    # Port where ComfyUI server runs (default: 8188)
    api_port: 8188
    
    # Whether ComfyUI is currently running
    # If false, scripts will start it automatically
    auto_start: true
    
  # Resource paths on host
  paths:
    # Where to sync outputs to (optional)
    output_sync_path: "/home/user/ComfyUI/output"
    
    # Where models are stored
    models_path: "/home/user/ComfyUI/models"
    
    # Custom nodes directory
    custom_nodes_path: "/home/user/ComfyUI/custom_nodes"
    
  # Feature flags
  features:
    # Allow workflow execution
    workflow_execution: true
    
    # Allow resource installation (models, custom nodes, etc.)
    resource_installation: true
    
    # Allow output syncing back to container
    output_sync: true
    
  # Resource limits (optional)
  limits:
    # Maximum concurrent workflow executions
    max_concurrent_workflows: 1
    
    # Maximum upload size for resources (MB)
    max_upload_size_mb: 5000
```

**Validation Requirements:**
- File must be valid YAML
- `enabled` field is required (defaults to false)
- If enabled, all `ssh.*` and `comfyui.home` fields are required
- Paths must be absolute
- Port must be in valid range (1-65535)

### 2. Linux Host Setup Script

**File:** `scripts/setup-local-host-linux.sh`

**Purpose:** Automate the setup of SSH server and user on Linux hosts.

**Key Features:**

1. **Check Prerequisites**
   - Verify running on Linux host (not inside container)
   - Check for root/sudo access
   - Verify ComfyUI installation exists

2. **Install SSH Server**
   - Install OpenSSH server if not present
   - Configure sshd to run on alternate port (22022)
   - Create separate sshd_config for this instance

3. **Create Dedicated User**
   - Create `comfyui` user with no shell (for security)
   - Add user to necessary groups for file access
   - Configure SSH key-based authentication only

4. **Generate SSH Keys**
   - Create SSH key pair for container-to-host authentication
   - Store public key in `~comfyui/.ssh/authorized_keys`
   - Export private key for container mounting

5. **Configure Firewall**
   - Open port 22022 for localhost connections only
   - Optionally allow from Docker network IP range

6. **Create local-support-config.yml**
   - Generate configuration file with detected values
   - Prompt user for ComfyUI installation path
   - Set appropriate defaults

7. **Test Connection**
   - Verify SSH server is running
   - Test key-based authentication
   - Verify access to ComfyUI directory

**Usage:**
```bash
# Run on the host machine (not in Docker)
sudo ./setup-local-host-linux.sh --comfyui-path /home/user/ComfyUI

# Options:
#   --comfyui-path PATH     Path to ComfyUI installation (required)
#   --ssh-port PORT         SSH port to use (default: 22022)
#   --ssh-user USER         SSH username (default: comfyui)
#   --docker-network CIDR   Docker network CIDR (default: 172.17.0.0/16)
#   --test-only             Only test existing configuration
#   --uninstall             Remove local support setup
```

**Output:**
- Creates `/etc/ssh/sshd_config.local_comfyui`
- Creates systemd service `sshd-local-comfyui.service`
- Generates `local-support-config.yml` in current directory
- Generates `local_host_key` private key for container
- Creates log file in `/var/log/comfyui-local-setup.log`

### 3. Windows Host Setup Script

**File:** `scripts/setup-local-host-windows.bat`

**Purpose:** Automate setup of OpenSSH server on Windows hosts.

**Key Features:**

1. **Check Prerequisites**
   - Verify running on Windows (PowerShell available)
   - Check for Administrator privileges
   - Verify ComfyUI installation exists
   - Check Windows version (requires Windows 10 1809+ or Windows Server 2019+)

2. **Install OpenSSH Server**
   - Use Windows Optional Features to install OpenSSH Server
   - Or use Chocolatey/winget if available
   - Configure service to start automatically

3. **Configure OpenSSH**
   - Create custom sshd_config_local_comfyui
   - Set alternate port (22022)
   - Disable password authentication
   - Enable key-based authentication only

4. **Create Dedicated User**
   - Create local user `comfyui_service`
   - Set strong random password (SSH will use keys only)
   - Grant read/write access to ComfyUI directory
   - Configure user profile

5. **Generate SSH Keys**
   - Use ssh-keygen from OpenSSH
   - Place public key in `C:\Users\comfyui_service\.ssh\authorized_keys`
   - Export private key for container mounting

6. **Configure Windows Firewall**
   - Create inbound rule for port 22022
   - Restrict to localhost and Docker NAT network
   - Name rule "ComfyUI Local Container Access"

7. **Create local-support-config.yml**
   - Generate configuration with Windows paths
   - Convert paths to Unix-style for SSH
   - Set appropriate defaults

8. **Test Connection**
   - Start OpenSSH service
   - Test key-based authentication
   - Verify file access permissions

**Usage:**
```powershell
# Run in PowerShell as Administrator (on host, not in Docker)
.\setup-local-host-windows.bat -ComfyUIPath "C:\Users\username\ComfyUI"

# Options:
#   -ComfyUIPath PATH       Path to ComfyUI installation (required)
#   -SSHPort PORT          SSH port to use (default: 22022)
#   -SSHUser USER          SSH username (default: comfyui_service)
#   -DockerNetwork CIDR    Docker network CIDR (default: 172.17.0.0/16)
#   -TestOnly              Only test existing configuration
#   -Uninstall             Remove local support setup
```

**Output:**
- Installs OpenSSH Server Windows feature
- Creates `C:\ProgramData\ssh\sshd_config_local_comfyui`
- Creates Windows service `sshd-local-comfyui`
- Generates `local-support-config.yml` in current directory
- Generates `local_host_key` private key for container
- Creates log file in `C:\ProgramData\comfyui-local-setup.log`

### 4. Container Integration

#### 4.1 Docker Compose Modifications

**File:** `docker-compose.yml`

Add volume mount for local support configuration and SSH key:

```yaml
services:
  media-sync-api:
    # ... existing config ...
    volumes:
      # ... existing volumes ...
      
      # Local support configuration (optional)
      - ./local-support-config.yml:/app/local-support-config.yml:ro
      
      # Local host SSH key (optional)
      - ./local_host_key:/root/.ssh/local_host_key:ro
    
    extra_hosts:
      # Enable host.docker.internal on Linux
      - "host.docker.internal:host-gateway"
```

#### 4.2 Configuration Loader Modifications

**File:** `app/utils/config_loader.py`

Add function to load local support configuration:

```python
def load_local_support_config(config_path='/app/local-support-config.yml'):
    """
    Load local ComfyUI support configuration.
    
    Returns:
        dict: Local support configuration or None if disabled/not found
    """
    try:
        if not os.path.exists(config_path):
            return None
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        local_config = config.get('local_support', {})
        
        # Check if enabled
        if not local_config.get('enabled', False):
            logger.info("Local ComfyUI support is disabled")
            return None
            
        # Validate required fields
        required_fields = [
            'ssh.host', 'ssh.port', 'ssh.username', 
            'ssh.private_key', 'comfyui.home'
        ]
        
        for field in required_fields:
            parts = field.split('.')
            value = local_config
            for part in parts:
                value = value.get(part, {})
            if not value:
                logger.error(f"Local support config missing required field: {field}")
                return None
                
        logger.info(f"Local ComfyUI support enabled: {local_config['display_name']}")
        return local_config
        
    except Exception as e:
        logger.error(f"Error loading local support config: {e}")
        return None
```

#### 4.3 VastAI Manager Extension

**File:** `app/vastai/vast_manager.py`

Add method to include local instance in instance list:

```python
def get_all_available_instances(self, include_local=True):
    """
    Get all available instances including VastAI and local host.
    
    Args:
        include_local: Whether to include local host instance
        
    Returns:
        list: Combined list of VastAI and local instances
    """
    instances = []
    
    # Get VastAI instances
    vastai_instances = self.get_running_instances()
    instances.extend(vastai_instances)
    
    # Add local instance if configured
    if include_local:
        local_instance = self._get_local_instance()
        if local_instance:
            instances.append(local_instance)
            
    return instances

def _get_local_instance(self):
    """
    Get local host instance from configuration.
    
    Returns:
        dict: Instance object for local host or None
    """
    from ..utils.config_loader import load_local_support_config
    
    config = load_local_support_config()
    if not config:
        return None
        
    # Build instance object matching VastAI instance structure
    ssh_config = config['ssh']
    comfyui_config = config['comfyui']
    
    instance = {
        'id': 'local',
        'instance_id': 'local',
        'type': 'local',
        'display_name': config.get('display_name', 'Local ComfyUI'),
        'actual_status': 'running',
        'status': 'running',
        'gpu_name': 'Local GPU',
        'num_gpus': 1,
        'public_ipaddr': ssh_config['host'],
        'public_ip': ssh_config['host'],
        'ssh_port': ssh_config['port'],
        'ssh_user': ssh_config['username'],
        'ssh_key_path': ssh_config['private_key'],
        'ui_home': comfyui_config['home'],
        'api_port': comfyui_config.get('api_port', 8188),
        'dph_total': 0.0,  # No cost for local
        'cost_per_hour': 0.0,
        'is_local': True,
        'features': config.get('features', {}),
        'limits': config.get('limits', {})
    }
    
    return instance
```

#### 4.4 SSH Connection Handler

**File:** `app/sync/ssh_utils.py` (new file)

Create helper to handle local instance SSH connections:

```python
def get_ssh_command_for_instance(instance):
    """
    Build SSH command for connecting to an instance.
    Handles both VastAI and local instances.
    
    Args:
        instance: Instance object
        
    Returns:
        str: SSH connection string
    """
    if instance.get('is_local', False):
        # Local instance - use custom key and settings
        host = instance['public_ipaddr']
        port = instance['ssh_port']
        user = instance['ssh_user']
        key_path = instance['ssh_key_path']
        
        return f"ssh -i {key_path} -p {port} {user}@{host} -o StrictHostKeyChecking=no"
    else:
        # VastAI instance - use standard connection
        host = instance['public_ipaddr']
        port = instance.get('ssh_port', 22)
        
        return f"ssh -p {port} root@{host}"
```

#### 4.5 API Endpoints

**File:** `app/sync/sync_api.py`

Add endpoint to get local instance status:

```python
@app.route('/api/local/status', methods=['GET'])
def get_local_status():
    """Get status of local ComfyUI instance"""
    try:
        from ..utils.config_loader import load_local_support_config
        
        config = load_local_support_config()
        
        if not config:
            return jsonify({
                'success': True,
                'enabled': False,
                'message': 'Local support is not enabled'
            })
            
        # Test SSH connection
        ssh_config = config['ssh']
        test_cmd = f"ssh -i {ssh_config['private_key']} -p {ssh_config['port']} " \
                   f"{ssh_config['username']}@{ssh_config['host']} -o StrictHostKeyChecking=no " \
                   f"-o ConnectTimeout=5 'echo connected'"
        
        result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True)
        ssh_connected = result.returncode == 0
        
        # Check if ComfyUI is running
        comfyui_running = False
        if ssh_connected:
            check_cmd = f"ssh -i {ssh_config['private_key']} -p {ssh_config['port']} " \
                       f"{ssh_config['username']}@{ssh_config['host']} " \
                       f"'curl -s http://localhost:{config['comfyui']['api_port']}/system_stats'"
            
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            comfyui_running = result.returncode == 0
        
        return jsonify({
            'success': True,
            'enabled': True,
            'config': {
                'display_name': config.get('display_name'),
                'host': ssh_config['host'],
                'port': ssh_config['port'],
                'comfyui_home': config['comfyui']['home']
            },
            'status': {
                'ssh_connected': ssh_connected,
                'comfyui_running': comfyui_running
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting local status: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
```

Modify `/vastai/instances` endpoint to include local instance:

```python
@app.route('/vastai/instances', methods=['GET'])
def get_vastai_instances():
    """Get all available instances (VastAI + local)"""
    try:
        vast_manager = VastManager(api_key_file='/app/api_key.txt')
        
        # Get both VastAI and local instances
        instances = vast_manager.get_all_available_instances(include_local=True)
        
        return jsonify({
            'success': True,
            'instances': instances,
            'count': len(instances)
        })
        
    except Exception as e:
        logger.error(f"Error fetching instances: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'instances': []
        }), 500
```

### 5. UI Integration

#### 5.1 Instance Tile Rendering

**File:** `app/webui/js/vastai-connection-toolbar.js`

Modify `renderInstanceTile()` to handle local instances:

```javascript
renderInstanceTile(instance) {
    const instanceId = instance.id || instance.instance_id || instance.instanceId;
    const isLocal = instance.is_local || instance.type === 'local';
    
    // Different rendering for local vs VastAI instances
    if (isLocal) {
        return this.renderLocalInstanceTile(instance);
    } else {
        return this.renderVastAIInstanceTile(instance);
    }
}

renderLocalInstanceTile(instance) {
    const instanceId = instance.id;
    const displayName = instance.display_name || 'Local ComfyUI';
    const sshHost = instance.public_ipaddr || instance.ssh_host;
    const sshPort = instance.ssh_port || 22022;
    const comfyuiHome = instance.ui_home;
    const isSelected = this.state.selected_instance_id === instanceId;
    
    return `
        <div class="toolbar-instance-tile local-instance ${isSelected ? 'selected' : ''}" 
             data-instance-id="${instanceId}">
            <div class="toolbar-instance-info">
                <div class="toolbar-instance-header">
                    <span class="toolbar-instance-id">🏠 ${this._escapeAttr(displayName)}</span>
                    <span class="instance-status status-running">local</span>
                </div>
                <div class="toolbar-instance-gpu">
                    <strong>Host Machine</strong>
                </div>
                <div class="toolbar-instance-details">
                    <div>📡 ${sshHost}:${sshPort}</div>
                    <div>📁 ${this._escapeAttr(comfyuiHome)}</div>
                    <div>💰 $0.00/hr (FREE)</div>
                </div>
            </div>
            <div class="toolbar-instance-actions">
                <button class="toolbar-action-btn btn-select" 
                        data-action="select" 
                        data-instance-id="${instanceId}">
                    ${isSelected ? '✓ Selected' : 'Select'}
                </button>
                <button class="toolbar-action-btn btn-test" 
                        data-action="test" 
                        data-instance-id="${instanceId}">
                    🔌 Test
                </button>
            </div>
        </div>
    `;
}
```

#### 5.2 CSS Styling

**File:** `app/webui/css/vastai-connection-toolbar.css`

Add styles for local instance tiles:

```css
/* Local instance tile styling */
.toolbar-instance-tile.local-instance {
    border-left: 4px solid #10b981; /* Green border for local */
    background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%);
}

.toolbar-instance-tile.local-instance.selected {
    background: linear-gradient(135deg, #dcfce7 0%, #f0fdf4 100%);
    border-left-color: #059669;
}

.toolbar-instance-tile.local-instance .instance-status.status-local {
    background-color: #10b981;
    color: white;
}

/* Free badge for cost */
.toolbar-instance-tile.local-instance .toolbar-instance-details div:last-child {
    color: #10b981;
    font-weight: bold;
}
```

### 6. Security Considerations

#### 6.1 SSH Security

1. **Dedicated SSH User**
   - Create user with minimal permissions
   - No shell access (set to `/usr/sbin/nologin`)
   - Only allow connection from localhost/Docker network
   - Use SSH keys only (no password authentication)

2. **Port Configuration**
   - Use non-standard port (22022) to avoid conflicts
   - Bind to localhost only if possible
   - Use firewall rules to restrict access

3. **Key Management**
   - Generate unique SSH key pair
   - Store private key with strict permissions (600)
   - Rotate keys periodically
   - Never commit keys to version control

4. **SSH Configuration Hardening**
   ```
   # /etc/ssh/sshd_config.local_comfyui
   Port 22022
   ListenAddress 127.0.0.1
   ListenAddress 172.17.0.1  # Docker bridge
   
   PermitRootLogin no
   PubkeyAuthentication yes
   PasswordAuthentication no
   ChallengeResponseAuthentication no
   UsePAM no
   
   AllowUsers comfyui
   
   # Disable tunneling features not needed
   AllowTcpForwarding no
   X11Forwarding no
   AllowAgentForwarding no
   ```

#### 6.2 File System Security

1. **Path Validation**
   - Validate all paths are within ComfyUI directory
   - Prevent directory traversal attacks
   - Use absolute paths only

2. **File Permissions**
   - ComfyUI user should own all ComfyUI files
   - Grant read/write only to necessary directories
   - Models, outputs, custom_nodes need write access
   - Main code directories can be read-only

3. **Resource Limits**
   - Limit file upload sizes
   - Limit concurrent operations
   - Implement timeout for long-running operations

#### 6.3 Container Security

1. **Network Isolation**
   - Container should only access host via SSH
   - No direct file system mounts to host
   - Use Docker networks properly

2. **Volume Permissions**
   - Mount configuration as read-only
   - Mount SSH key as read-only
   - Never write to mounted volumes from container

#### 6.4 Monitoring and Logging

1. **SSH Access Logs**
   - Log all SSH connection attempts
   - Monitor for failed authentication
   - Alert on suspicious activity

2. **Operation Logging**
   - Log all workflow executions
   - Log resource installations
   - Track which operations are from local vs cloud

### 7. Testing Requirements

#### 7.1 Unit Tests

1. **Configuration Loading**
   - Test valid YAML parsing
   - Test invalid configurations
   - Test missing required fields
   - Test disabled configuration

2. **SSH Connection**
   - Test successful connection
   - Test connection failures
   - Test timeout handling
   - Test key authentication

3. **Instance Detection**
   - Test local instance discovery
   - Test mixing local and VastAI instances
   - Test instance selection

#### 7.2 Integration Tests

1. **Workflow Execution**
   - Execute simple workflow on local instance
   - Verify output files are created
   - Test workflow with custom nodes
   - Test workflow failure handling

2. **Resource Installation**
   - Install model to local instance
   - Install custom node to local instance
   - Verify file permissions
   - Test concurrent installations

3. **SSH Operations**
   - Test file upload to host
   - Test file download from host
   - Test remote command execution
   - Test connection pooling

#### 7.3 System Tests

1. **Linux Host Testing**
   - Test on Ubuntu 20.04, 22.04
   - Test on Debian 11, 12
   - Test on Fedora
   - Test with Docker Desktop and Docker Engine

2. **Windows Host Testing**
   - Test on Windows 10 (1809+)
   - Test on Windows 11
   - Test with Docker Desktop for Windows
   - Test with WSL2 backend

3. **End-to-End Scenarios**
   - Setup from scratch on clean host
   - Execute complete workflow pipeline
   - Test failover between instances
   - Test configuration changes
   - Test uninstall process

#### 7.4 Security Tests

1. **Penetration Testing**
   - Test SSH access restrictions
   - Test path traversal attempts
   - Test privilege escalation attempts
   - Test key exposure scenarios

2. **Permission Testing**
   - Verify file permissions are correct
   - Test user isolation
   - Test write restrictions
   - Test network restrictions

### 8. Documentation Requirements

#### 8.1 User Documentation

1. **Setup Guide**
   - Prerequisites
   - Step-by-step installation
   - Configuration options
   - Troubleshooting common issues

2. **Usage Guide**
   - How to select local instance
   - How to execute workflows
   - How to install resources
   - How to monitor operations

3. **Security Guide**
   - Best practices
   - Firewall configuration
   - Key rotation
   - Monitoring recommendations

#### 8.2 Developer Documentation

1. **Architecture Documentation**
   - Component overview
   - Data flow diagrams
   - API specifications
   - Integration points

2. **API Documentation**
   - New endpoints
   - Modified endpoints
   - Request/response formats
   - Error codes

3. **Troubleshooting Guide**
   - Common errors
   - Debug logging
   - Connection issues
   - Permission problems

### 9. Implementation Phases

#### Phase 1: Core Infrastructure (Week 1)
- [ ] Create configuration file structure
- [ ] Implement configuration loader
- [ ] Add local instance detection
- [ ] Basic SSH connection testing

#### Phase 2: Host Setup Scripts (Week 2)
- [ ] Develop Linux setup script
- [ ] Develop Windows setup script
- [ ] Test on multiple platforms
- [ ] Create uninstall procedures

#### Phase 3: Container Integration (Week 3)
- [ ] Modify Docker Compose
- [ ] Update VastAI manager
- [ ] Implement SSH utilities
- [ ] Add API endpoints

#### Phase 4: UI Integration (Week 4)
- [ ] Update toolbar JavaScript
- [ ] Add CSS styling
- [ ] Test instance selection
- [ ] Implement status indicators

#### Phase 5: Testing & Documentation (Week 5)
- [ ] Write unit tests
- [ ] Perform integration tests
- [ ] System testing on multiple platforms
- [ ] Write comprehensive documentation

#### Phase 6: Security Hardening (Week 6)
- [ ] Security audit
- [ ] Penetration testing
- [ ] Fix vulnerabilities
- [ ] Update security documentation

### 10. Success Criteria

The feature will be considered complete when:

1. ✅ Users can set up local ComfyUI support on both Linux and Windows
2. ✅ Local instance appears in connection toolbar alongside VastAI instances
3. ✅ Workflows execute successfully on local instance
4. ✅ Resources can be installed to local instance
5. ✅ SSH connection is secure and restricted
6. ✅ All tests pass on supported platforms
7. ✅ Documentation is complete and clear
8. ✅ No security vulnerabilities identified
9. ✅ Performance is acceptable (comparable to VastAI instances)
10. ✅ Setup process takes less than 15 minutes

### 11. Future Enhancements

Potential improvements for future versions:

1. **Auto-Discovery**
   - Automatically detect ComfyUI installations on host
   - Suggest optimal configuration settings

2. **GUI Setup Wizard**
   - Web-based setup interface
   - Eliminate need for command-line scripts
   - Interactive testing and validation

3. **Multi-Instance Support**
   - Support multiple local ComfyUI installations
   - Load balancing between local instances
   - Different installations for different purposes

4. **Performance Optimization**
   - Connection pooling
   - Caching of remote file system state
   - Parallel operations

5. **Advanced Monitoring**
   - Real-time GPU utilization display
   - Workflow execution history
   - Performance metrics dashboard

6. **Automatic Updates**
   - Update custom nodes on local instance
   - Sync models with cloud instances
   - Configuration migration tools

### 12. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SSH security vulnerability | Medium | High | Extensive security testing, hardened configuration |
| Complex setup process | High | Medium | Clear documentation, automated scripts |
| Platform compatibility issues | Medium | Medium | Test on multiple platforms, provide alternatives |
| Performance degradation | Low | Medium | Performance testing, optimization |
| File permission problems | High | Low | Clear permission setup, validation checks |
| User confusion | Medium | Low | Clear UI indicators, good documentation |
| Docker networking issues | Medium | Medium | Multiple network configuration options |

### 13. Alternatives Considered

#### Alternative 1: Direct File System Mount
Mount host ComfyUI directory directly into container.

**Pros:**
- Simpler setup
- No SSH required
- Better performance

**Cons:**
- Security risks (container has direct file access)
- Difficult to manage permissions
- Can't execute Python in host environment
- Breaks container isolation principle

**Decision:** Rejected due to security concerns

#### Alternative 2: HTTP API Only
Use ComfyUI's HTTP API for all operations.

**Pros:**
- No SSH required
- Simpler authentication
- Standard REST interface

**Cons:**
- Can't install resources or custom nodes
- Limited file system access
- Can't start/stop ComfyUI
- Missing many management features

**Decision:** Rejected due to limited functionality

#### Alternative 3: Dedicated Management Agent
Install a management agent on host that container talks to.

**Pros:**
- Better security model
- More control over operations
- Cleaner API

**Cons:**
- Additional software to install
- More complex architecture
- Maintenance burden
- Requires daemon running on host

**Decision:** Rejected due to complexity (may revisit for v2)

### 14. Migration Plan

For existing users, no migration is needed as this is a new opt-in feature.

**New Users:**
1. Follow setup guide to install scripts
2. Run appropriate script for their platform
3. Copy generated configuration to Docker mount
4. Restart container
5. Select local instance in UI

**Configuration Updates:**
If configuration format changes in future versions:
1. Provide migration script
2. Support both old and new formats temporarily
3. Log warnings for deprecated fields
4. Auto-convert when possible

### 15. Support Plan

**Community Support:**
- GitHub Issues for bug reports
- Discussions for questions and feature requests
- Wiki for community tips and tricks

**Documentation:**
- Comprehensive README
- Video walkthrough
- FAQ section
- Troubleshooting guide

**Monitoring:**
- Track common error messages
- Identify documentation gaps
- Prioritize improvements based on feedback

### 16. Conclusion

This proposal outlines a comprehensive plan for adding local ComfyUI support to the Media Sync Tool. The implementation balances functionality, security, and usability while maintaining the existing architecture and patterns of the codebase.

The SSH-based approach provides:
- ✅ Secure isolation between container and host
- ✅ Full functionality (workflows, resources, management)
- ✅ Compatibility with existing infrastructure
- ✅ Clear security boundaries
- ✅ Manageable complexity

With proper implementation and testing, this feature will significantly enhance the value of the tool for users who already have ComfyUI installed on their host machines.

## Next Steps

1. **Review and Feedback**: Share this proposal with stakeholders for review
2. **Refinement**: Incorporate feedback and adjust design as needed
3. **Approval**: Get sign-off to proceed with implementation
4. **Implementation**: Follow the phased approach outlined above
5. **Testing**: Comprehensive testing on all supported platforms
6. **Documentation**: Complete all user and developer documentation
7. **Release**: Ship as part of next major version with announcement

---

**Document Version:** 1.0  
**Last Updated:** 2025-12-09  
**Status:** Draft - Awaiting Review  
**Author:** GitHub Copilot Agent
