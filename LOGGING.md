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