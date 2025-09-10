# SSH Identity Management Feature

## Overview

The SSH Identity Management feature provides a comprehensive solution for handling SSH keys, identities, and user confirmation prompts in the Media Sync Tool. This addresses the common issue where users see "Identity added" messages and need guidance on SSH setup.

## Key Features

### 1. SSH Status Monitoring
- **Real-time status display** in the web UI
- **Comprehensive validation** of SSH setup components
- **Visual indicators** for different status levels (success ✅, warning ⚠️, error ❌)

### 2. User Confirmation System
- **Interactive prompts** when SSH identity setup is required
- **Clear messaging** explaining what actions will be taken
- **User choice** to proceed or cancel SSH setup

### 3. Automatic Permission Management
- **Container startup script** that fixes SSH file permissions
- **Write access** for dynamic SSH components (like `vast_known_hosts`)
- **Secure permissions** that satisfy SSH security requirements

### 4. Enhanced Error Handling
- **Distinction between success and error messages**
- **Specific guidance** for resolving SSH issues
- **Comprehensive logging** for troubleshooting

## API Endpoints

### GET /ssh/status
Returns comprehensive SSH status information.

**Response:**
```json
{
  "success": true,
  "status": {
    "timestamp": "2025-01-01T12:00:00Z",
    "ssh_key_path": "/root/.ssh/id_ed25519",
    "validation": {
      "valid": true,
      "ssh_key_exists": true,
      "ssh_key_readable": true,
      "ssh_agent_running": true,
      "identity_loaded": true,
      "permissions_ok": true
    },
    "ready_for_sync": true
  }
}
```

### POST /ssh/setup
Sets up SSH agent and adds identity with optional user confirmation.

**Request:**
```json
{
  "confirmed": true
}
```

**Response (requires confirmation):**
```json
{
  "success": false,
  "requires_confirmation": true,
  "confirmation_message": "Do you want to add the SSH identity for media sync?",
  "details": "SSH key setup requires user confirmation"
}
```

**Response (success):**
```json
{
  "success": true,
  "message": "SSH identity added successfully",
  "identity_added": true,
  "permissions_fixed": ["Fixed SSH key permissions: 644 -> 600"]
}
```

### POST /ssh/test
Tests SSH connection to a specific host.

**Request:**
```json
{
  "host": "localhost",
  "port": 22,
  "user": "root",
  "timeout": 10
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "success": true,
    "host": "localhost",
    "port": 22,
    "user": "root",
    "message": "Connection successful in 0.5s",
    "response_time": 0.5
  }
}
```

### POST /ssh/cleanup
Cleans up SSH agent.

**Response:**
```json
{
  "success": true,
  "message": "SSH agent cleaned up"
}
```

## Web UI Components

### SSH Status Panel
The web interface includes a dedicated SSH status panel that shows:
- Overall SSH readiness status
- Individual component status (key, agent, identity, permissions)
- Setup button when SSH configuration is required

### Confirmation Dialog
When SSH setup requires user confirmation, a modal dialog appears with:
- Clear explanation of what will happen
- Technical details about the operation
- "Yes" and "Cancel" options

## Container Integration

### Dockerfile Updates
```dockerfile
# Create a script to fix SSH permissions at runtime
RUN echo '#!/bin/bash\n\
# Fix SSH directory and file permissions if needed\n\
if [ -d "/root/.ssh" ]; then\n\
    chmod 700 /root/.ssh 2>/dev/null || true\n\
    [ -f "/root/.ssh/id_ed25519" ] && chmod 600 /root/.ssh/id_ed25519 2>/dev/null || true\n\
    [ -f "/root/.ssh/id_ed25519.pub" ] && chmod 644 /root/.ssh/id_ed25519.pub 2>/dev/null || true\n\
    [ -f "/root/.ssh/config" ] && chmod 644 /root/.ssh/config 2>/dev/null || true\n\
    [ -f "/root/.ssh/known_hosts" ] && chmod 644 /root/.ssh/known_hosts 2>/dev/null || true\n\
    [ -f "/root/.ssh/vast_known_hosts" ] && chmod 664 /root/.ssh/vast_known_hosts 2>/dev/null || true\n\
fi\n\
exec "$@"' > /usr/local/bin/fix-ssh-permissions.sh && \
    chmod +x /usr/local/bin/fix-ssh-permissions.sh

ENTRYPOINT ["/usr/local/bin/fix-ssh-permissions.sh"]
```

### Docker Compose Integration
The SSH files should be mounted with appropriate permissions:

```yaml
volumes:
  - ./.ssh/id_ed25519:/root/.ssh/id_ed25519:ro
  - ./.ssh/id_ed25519.pub:/root/.ssh/id_ed25519.pub:ro
  - ./.ssh/known_hosts:/root/.ssh/known_hosts:ro
  - ./.ssh/config:/root/.ssh/config:ro
  - ./.ssh/vast_known_hosts:/root/.ssh/vast_known_hosts    # RW for dynamic updates
```

## Usage Examples

### Basic SSH Setup
1. User opens the web interface
2. Clicks "Refresh" on SSH status panel
3. Sees "Setup required" status
4. Clicks "Set Up SSH" button
5. Confirms the action in the dialog
6. SSH identity is configured automatically

### Troubleshooting SSH Issues
1. Check SSH status via web UI or API
2. Review specific component failures
3. Use the setup endpoint to fix issues
4. Test connections to specific hosts

### Programmatic Integration
```python
from app.sync.ssh_manager import SSHIdentityManager

# Create manager
ssh_manager = SSHIdentityManager()

# Check status
status = ssh_manager.get_ssh_status()
if not status['ready_for_sync']:
    # Setup SSH
    result = ssh_manager.setup_ssh_agent()
    if result['requires_user_confirmation']:
        # Handle user confirmation
        pass

# Test connection
test_result = ssh_manager.test_ssh_connection('localhost', 22)
```

## Error Resolution

### Common Issues and Solutions

#### "SSH key not found"
- **Cause:** SSH key file doesn't exist at expected path
- **Solution:** Generate SSH key or mount correct key file
- **UI Action:** Setup button will guide through resolution

#### "SSH agent not running"
- **Cause:** SSH agent process not started
- **Solution:** Click "Set Up SSH" to start agent and add identity
- **Automatic:** Handled by SSH manager during sync operations

#### "Permission denied"
- **Cause:** SSH files have incorrect permissions
- **Solution:** Container startup script fixes permissions automatically
- **Manual:** Use the setup endpoint to fix permissions

#### "Identity requires passphrase"
- **Cause:** SSH key is protected with passphrase
- **Solution:** User confirmation dialog will prompt for setup
- **Alternative:** Use passwordless key for automated operations

## Security Considerations

### File Permissions
- SSH directory: 700 (owner only)
- Private key: 600 (owner read/write only)
- Public key/config: 644 (owner read/write, others read)
- Dynamic files: 664 (owner/group read/write, others read)

### User Confirmation
- Required for any SSH identity changes
- Clear messaging about security implications
- Option to cancel operations

### Logging
- All SSH operations are logged
- No sensitive information (keys, passphrases) in logs
- Detailed error information for troubleshooting

## Testing

The feature includes comprehensive tests covering:
- SSH manager functionality (16 tests)
- API endpoints (13 tests)
- Integration with existing systems
- Error conditions and edge cases

Run tests with:
```bash
pytest test/test_ssh_manager.py -v
pytest test/test_ssh_api_endpoints.py -v
```

## Migration from Previous Version

### For Existing Users
1. Existing SSH setup continues to work
2. New UI provides enhanced visibility
3. No breaking changes to existing functionality
4. Enhanced error messages provide better guidance

### For New Users
1. Clear setup guidance through web UI
2. Step-by-step SSH configuration
3. Automatic permission handling
4. Built-in testing and validation

This feature significantly improves the user experience around SSH setup while maintaining security and providing comprehensive troubleshooting capabilities.