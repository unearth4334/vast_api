# VastAI Logging System

## Overview

The VastAI application now uses a centralized logging system that stores all logs in Docker volumes for persistence and easier management.

## Log Directory Structure

All logs are stored under `/app/logs` (inside the container) which is mounted as the `vast_api_logs` Docker volume:

```
/app/logs/
├── app/                    # Application-level logs
│   └── app_log_YYYYMMDD.json
├── sync/                   # Sync operation logs  
│   ├── operations/         # Completed sync operation results
│   │   └── sync_log_YYYYMMDD_HHMM.json
│   └── progress/           # Active sync progress tracking
│       └── sync_progress_{uuid}.json
└── vastai/                 # VastAI API interaction logs
    ├── api/                # API call logs
    │   └── api_log_YYYYMMDD.json
    └── instances/          # Instance management logs (future use)
```

## Environment Variables

- `LOG_BASE`: Base directory for all logs (default: `/app/logs`)

## Log Types

### Application Logs (`/app/logs/app/`)
- **Format**: JSON array of log entries
- **Filename**: `app_log_YYYYMMDD.json`
- **Content**: Application startup, shutdown, and general events
- **Fields**:
  - `timestamp`: ISO timestamp
  - `event_type`: Type of event (startup, shutdown, error.*, info.*)
  - `message`: Human-readable message
  - `details`: Additional event details (optional)

### Sync Operation Logs (`/app/logs/sync/operations/`)
- **Format**: Single JSON object per file
- **Filename**: `sync_log_YYYYMMDD_HHMM.json`
- **Content**: Complete sync operation results
- **Fields**:
  - `timestamp`: Start time
  - `end_time`: End time
  - `sync_type`: Type of sync operation
  - `duration`: Duration in seconds
  - `result`: Sync result details

### Sync Progress Files (`/app/logs/sync/progress/`)
- **Format**: Single JSON object per file
- **Filename**: `sync_progress_{uuid}.json`
- **Content**: Real-time sync progress tracking
- **Fields**:
  - `sync_id`: Unique sync identifier
  - `status`: Current status (running, completed, failed, timeout, error)
  - `progress_percent`: Completion percentage
  - `last_update`: Last update timestamp
  - `sync_type`: Type of sync operation
  - `host`: Target host
  - `port`: Target port

### VastAI API Logs (`/app/logs/vastai/api/`)
- **Format**: JSON array of API interaction entries
- **Filename**: `api_log_YYYYMMDD.json`
- **Content**: All VastAI API interactions
- **Fields**:
  - `timestamp`: ISO timestamp
  - `method`: HTTP method
  - `endpoint`: API endpoint
  - `status_code`: HTTP status code
  - `duration_ms`: Request duration
  - `request`: Sanitized request data
  - `response`: Sanitized response data
  - `error`: Error message (if applicable)

## API Endpoints

### Log Management
- `GET /logs/info`: Get log directory information and status
- `GET /logs/manifest`: Get list of available sync log files
- `GET /logs/{filename}`: Get specific sync log file content

### VastAI Logs
- `GET /vastai/logs`: Get VastAI API logs with optional parameters
  - `max_lines`: Limit number of entries (default: 100)
  - `date_filter`: Date filter (YYYYMMDD format)
- `GET /vastai/logs/manifest`: Get VastAI log file manifest

## Docker Volume Management

### Viewing Logs via Deploy Script
```bash
# Show all available log files
./deploy.sh app-logs

# Show specific log file
./deploy.sh app-logs app_log_20251019.json

# Show container logs (Docker level)
./deploy.sh logs vast_api
```

### Direct Docker Commands
```bash
# List all files in log volume
docker run --rm -v vast_api_vast_api_logs:/logs alpine find /logs -type f

# View specific log file
docker run --rm -v vast_api_vast_api_logs:/logs alpine cat /logs/app/app_log_20251019.json

# Monitor sync progress
docker run --rm -v vast_api_vast_api_logs:/logs alpine sh -c 'watch -n1 "ls -la /logs/sync/progress/"'
```

## Benefits

1. **Persistence**: Logs survive container restarts and updates
2. **Organization**: Clear separation between different log types
3. **Accessibility**: Logs available via API and direct volume access
4. **Debugging**: Easy to trace sync operations and API interactions
5. **Monitoring**: Real-time progress tracking for long-running operations
6. **Privacy**: Sensitive data is automatically sanitized in API logs

## Migration Notes

- Previous logs were stored in `/media/.sync_log` and `/media/.vastai_log`
- New logs are stored in `/app/logs/sync/` and `/app/logs/vastai/` respectively
- Progress files moved from `/tmp/sync_progress_*.json` to `/app/logs/sync/progress/`
- All log directories are created automatically on application startup

## Troubleshooting SSH Connection Issues

### Common "Failed to set UI_HOME" Errors

When you see "Failed to set UI_HOME" errors in the VastAI Setup tab, this usually indicates SSH connection problems. Here's how to diagnose and fix them:

#### 1. Use the SSH Test Button
Before trying to set UI_HOME, click the "🔧 Test SSH Connection" button to verify basic connectivity:
- This will test if SSH keys are working
- Shows detailed error messages for authentication/connection issues
- Verifies the SSH connection string parsing

#### 2. Common Error Types and Solutions

**Authentication Failed (Permission denied)**
```
Error: SSH authentication failed - check SSH keys
```
**Solution:** Ensure SSH keys are properly mounted in the Docker container
- Check that `SSH_DIR_PATH` environment variable points to your SSH keys
- Verify the private key has correct permissions (600)
- Ensure the key matches what's configured on the VastAI instance

**Connection Refused**
```
Error: SSH connection refused - check host and port
```
**Solution:** Verify the SSH connection string format
- Ensure the format is: `ssh -p PORT root@HOST -L 8080:localhost:8080`
- Verify the port number is correct
- Check that the VastAI instance is running

**Network/Timeout Issues**
```
Error: SSH connection timed out - check host and firewall
Error: Network unreachable - check host address
```
**Solution:** Check network connectivity
- Verify the host IP address is reachable
- Check firewall settings
- Ensure the VastAI instance is accessible from your network

#### 3. SSH Connection String Format

The system expects SSH connection strings in this format:
```bash
ssh -p 28276 root@39.114.238.31 -L 8080:localhost:8080
```

Components:
- `-p PORT`: SSH port number
- `root@HOST`: Username and host IP/hostname
- `-L 8080:localhost:8080`: Local port forwarding (optional for UI_HOME operations)

#### 4. Manual SSH Testing

You can manually test SSH connectivity from your local machine:
```bash
# Test basic SSH connectivity
ssh -p 28276 root@39.114.238.31 -o ConnectTimeout=10 echo "Connection successful"

# Test with the same options the application uses
ssh -p 28276 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@39.114.238.31 whoami
```

#### 5. Checking SSH Keys in Docker

If running in Docker, verify SSH keys are properly mounted:
```bash
# Check if SSH keys are accessible in container
docker exec -it media-sync-api ls -la /root/.ssh/

# Test SSH from within container
docker exec -it media-sync-api ssh -p 28276 root@39.114.238.31 -o ConnectTimeout=10 echo "test"
```

#### 6. Application Logs

Check application logs for detailed SSH error information:
```bash
# View recent application logs
./deploy.sh app-logs

# Check specific error logs
./deploy.sh app-logs app_log_20251019.json
```

The logs will contain detailed SSH command output, return codes, and error messages that can help identify the specific issue.