# SSH Host Key Error Detection and Resolution Feature

## Overview

This feature automatically detects SSH host key changes during sync operations and provides a user-friendly interface to resolve them. When a sync operation fails due to a changed host identification error, the system:

1. **Detects** the error from SSH output
2. **Displays** a clear warning modal with security information
3. **Provides** a one-click resolution to accept the new host key

## Problem Statement

When SSH host keys change (e.g., after server reinstallation or VastAI instance recreation), sync operations fail with an error like:

```
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
IT IS POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!
Someone could be eavesdropping on you right now (man-in-the-middle attack)!
It is also possible that a host key has just been changed.
The fingerprint for the ED25519 key sent by the remote host is
SHA256:6Dhif6lu1QviP6aTLpbkbv/U3CBxf89FsGSLTm1GhJw.
Please contact your system administrator.
Add correct host key in /root/.ssh/known_hosts to get rid of this message.
Offending ED25519 key in /root/.ssh/known_hosts:6
  remove with:
  ssh-keygen -f '/root/.ssh/known_hosts' -R '[10.0.78.108]:2222'
Host key for [10.0.78.108]:2222 has changed and you have requested strict checking.
Host key verification failed.
```

Previously, users had to manually:
1. Identify the problem from the error message
2. Run `ssh-keygen` to remove the old key
3. Reconnect to accept the new key

This feature automates the entire process with a single click.

## Implementation

### Components

#### 1. SSH Host Key Manager (`app/sync/ssh_host_key_manager.py`)
Core module that handles detection and resolution:
- `detect_host_key_error()` - Detects errors using regex patterns
- `remove_old_host_key()` - Removes old key using `ssh-keygen`
- `accept_new_host_key()` - Accepts new key using SSH
- `resolve_host_key_error()` - Complete resolution workflow

#### 2. API Endpoints (`app/sync/sync_api.py`)
Three new REST endpoints:
- `POST /ssh/host-keys/check` - Check if output contains host key error
- `POST /ssh/host-keys/resolve` - Resolve a host key error
- `POST /ssh/host-keys/remove` - Remove specific host key

#### 3. Sync Integration (`app/sync/sync_utils.py`)
Modified `run_sync()` to detect host key errors and include them in response:
```python
if host_key_error:
    sync_result['host_key_error'] = host_key_error
```

#### 4. UI Components
- **HTML Modal** (`app/webui/index_template.html`) - Warning dialog
- **JavaScript Handler** (`app/webui/js/ssh-host-key.js`) - Modal management
- **Sync Integration** (`app/webui/js/sync.js`) - Automatic modal display
- **Styling** (`app/webui/css/app.css`) - Modal and warning box styles

### User Experience Flow

1. **User initiates sync** (Forge, ComfyUI, or VastAI)
2. **Sync fails** due to host key change
3. **System detects** the host key error from SSH output
4. **Modal appears** automatically with:
   - Clear warning about potential security risks
   - Host, port, and fingerprint details
   - "Accept New Host Key" button
   - "Cancel" button
5. **User clicks** "Accept New Host Key"
6. **System resolves** by:
   - Removing old key from known_hosts
   - Accepting new key via SSH
7. **Success message** confirms resolution
8. **User retries** sync operation

### Security Considerations

The implementation includes several security features:

1. **Clear Warnings**: Users are informed about potential man-in-the-middle attacks
2. **Informed Consent**: Shows all details (host, port, fingerprint) before accepting
3. **Secure Resolution**: Uses SSH's `StrictHostKeyChecking=accept-new` option
4. **Logging**: All operations are logged for audit purposes

## API Documentation

### Check for Host Key Error

**Endpoint**: `POST /ssh/host-keys/check`

**Request**:
```json
{
  "ssh_output": "<SSH error output>"
}
```

**Response** (error detected):
```json
{
  "success": true,
  "has_error": true,
  "error": {
    "host": "10.0.78.108",
    "port": 2222,
    "known_hosts_file": "/root/.ssh/known_hosts",
    "line_number": 6,
    "new_fingerprint": "SHA256:6Dhif6lu1QviP6aTLpbkbv/U3CBxf89FsGSLTm1GhJw",
    "detected_at": "2025-11-03T17:17:55.747Z"
  }
}
```

**Response** (no error):
```json
{
  "success": true,
  "has_error": false
}
```

### Resolve Host Key Error

**Endpoint**: `POST /ssh/host-keys/resolve`

**Request**:
```json
{
  "host": "10.0.78.108",
  "port": 2222,
  "known_hosts_file": "/root/.ssh/known_hosts",
  "user": "root"
}
```

**Response** (success):
```json
{
  "success": true,
  "message": "Host key resolved successfully for 10.0.78.108:2222"
}
```

**Response** (failure):
```json
{
  "success": false,
  "message": "Failed to remove old key: <error details>"
}
```

### Remove Host Key

**Endpoint**: `POST /ssh/host-keys/remove`

**Request**:
```json
{
  "host": "10.0.78.108",
  "port": 2222,
  "known_hosts_file": "/root/.ssh/known_hosts"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Old host key for [10.0.78.108]:2222 removed successfully"
}
```

## Testing

### Unit Tests

Run the comprehensive test suite:
```bash
python3 test/test_ssh_host_key_manager.py -v
```

Tests cover:
- Host key error detection (various formats)
- False positive prevention
- Host key removal (success, failure, timeout)
- Host key acceptance (success, failure, connection issues)
- Complete resolution workflow

### Integration Tests

API endpoint tests (requires Flask):
```bash
python3 test/test_ssh_host_key_api.py -v
```

### Manual Testing

Run the demonstration script:
```bash
python3 test_host_key_manual.py
```

This validates:
- Error detection accuracy
- No false positives
- Resolution workflow

## Files Changed/Added

### New Files
- `app/sync/ssh_host_key_manager.py` - Core manager class
- `app/webui/js/ssh-host-key.js` - UI JavaScript handler
- `test/test_ssh_host_key_manager.py` - Unit tests
- `test/test_ssh_host_key_api.py` - API integration tests
- `test_host_key_manual.py` - Manual test/demo script
- `UI_MOCKUP.py` - Visual UI documentation

### Modified Files
- `app/sync/sync_api.py` - Added 3 new API endpoints
- `app/sync/sync_utils.py` - Integrated error detection
- `app/webui/index_template.html` - Added modal HTML and script include
- `app/webui/js/sync.js` - Added modal trigger
- `app/webui/css/app.css` - Added modal styles

## Usage Examples

### From UI
1. Click "Sync Forge", "Sync ComfyUI", or "Sync VastAI"
2. If host key error occurs, modal appears automatically
3. Review the warning and host details
4. Click "Accept New Host Key" to resolve
5. Retry the sync operation

### From API
```python
import requests

# Check for host key error
response = requests.post('http://localhost:5000/ssh/host-keys/check', json={
    'ssh_output': ssh_error_output
})

if response.json()['has_error']:
    error = response.json()['error']
    
    # Resolve the error
    resolve_response = requests.post('http://localhost:5000/ssh/host-keys/resolve', json={
        'host': error['host'],
        'port': error['port'],
        'user': 'root'
    })
    
    print(resolve_response.json()['message'])
```

## Future Enhancements

Potential improvements for future versions:

1. **Key Fingerprint History**: Store history of fingerprints for audit
2. **Manual Verification**: Option to manually verify fingerprint before accepting
3. **Email Notifications**: Alert administrators when keys change
4. **Multiple Hosts**: Batch resolution for multiple host key errors
5. **Custom Known Hosts**: Support for custom known_hosts file locations
6. **Key Type Preferences**: Configure preferred key types (ED25519, RSA, etc.)

## Troubleshooting

### Issue: Modal doesn't appear
**Solution**: Check browser console for JavaScript errors. Ensure `ssh-host-key.js` is loaded.

### Issue: Resolution fails
**Solution**: Verify SSH access to the host. Check that `ssh-keygen` is available.

### Issue: False positives
**Solution**: Review the regex patterns in `SSHHostKeyManager.detect_host_key_error()`.

## References

- SSH Host Key Verification: https://www.ssh.com/academy/ssh/host-key
- ssh-keygen Manual: https://man.openbsd.org/ssh-keygen
- Flask API Documentation: https://flask.palletsprojects.com/
