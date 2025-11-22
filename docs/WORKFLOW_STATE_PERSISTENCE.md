# Workflow State Persistence

## Overview

This feature implements server-side workflow state persistence that allows the web UI to display and restore in-progress workflows when the page is opened or refreshed during execution.

## How It Works

### 1. State Storage

When a workflow is started:
- A unique workflow ID is generated
- Initial state is saved to `/tmp/workflow_state.json` including:
  - `workflow_id`: Unique identifier for the workflow
  - `status`: Current status (running, completed, failed, cancelled)
  - `current_step`: Index of the current step being executed (0-based)
  - `steps`: Array of step configurations with their status
  - `start_time`: ISO timestamp when workflow started
  - `ssh_connection`: SSH connection string (for restoration)

### 2. State Updates

As the workflow executes:
- State is updated before each step begins (status: `in_progress`)
- State is updated after each step completes (status: `completed`)
- State is updated if a step fails (status: `failed`)
- All updates include a `last_update` timestamp

### 3. State Restoration

When the page loads:
1. `initWorkflow()` is called during `DOMContentLoaded`
2. The function checks for active workflow state via GET `/workflow/state`
3. If an active workflow is found:
   - The vastai-setup tab is automatically opened
   - Step statuses are restored (completed, in-progress, failed)
   - Arrow progress indicators are updated
   - A status message is displayed to the user

### 4. State Cleanup

After workflow completion:
- State persists for 30 seconds (configurable)
- This allows users to see the final state if they refresh immediately
- State is automatically cleared after the delay

## API Endpoints

### GET /workflow/state
Returns the current workflow state if one exists.

**Response:**
```json
{
  "success": true,
  "active": true,
  "state": {
    "workflow_id": "workflow_1234567890_abc123",
    "status": "running",
    "current_step": 2,
    "steps": [...],
    "start_time": "2024-01-01T00:00:00Z",
    "last_update": "2024-01-01T00:05:30Z",
    "ssh_connection": "ssh -p 2222 root@example.com"
  }
}
```

### POST /workflow/state
Saves or updates workflow state.

**Request Body:**
```json
{
  "workflow_id": "workflow_1234567890_abc123",
  "status": "running",
  "current_step": 1,
  "steps": [
    {"action": "test_ssh", "status": "completed", "index": 0},
    {"action": "sync_instance", "status": "in_progress", "index": 1}
  ],
  "start_time": "2024-01-01T00:00:00Z",
  "ssh_connection": "ssh -p 2222 root@example.com"
}
```

### DELETE /workflow/state
Clears the current workflow state.

**Response:**
```json
{
  "success": true,
  "message": "Workflow state cleared"
}
```

### GET /workflow/state/summary
Returns a summary of the current workflow state.

**Response:**
```json
{
  "success": true,
  "summary": {
    "active": true,
    "workflow_id": "workflow_1234567890_abc123",
    "status": "running",
    "current_step": 2,
    "total_steps": 5,
    "progress_percent": 60.0,
    "start_time": "2024-01-01T00:00:00Z",
    "last_update": "2024-01-01T00:05:30Z"
  }
}
```

## Progress Calculation

The progress percentage is calculated based on the number of completed steps:
- `progress_percent = (current_step + 1) / total_steps * 100`
- `current_step` is 0-based (0 means first step is in progress)
- Adding 1 accounts for the current step being processed

Example:
- If `current_step = 2` and `total_steps = 5`
- This means steps 0, 1, and 2 are being/have been processed (3 steps)
- Progress = (2 + 1) / 5 * 100 = 60%

## Configuration

### State File Location
Default: `/tmp/workflow_state.json`

To change the location, modify the `DEFAULT_STATE_FILE` constant in `app/sync/workflow_state.py`.

### Cleanup Delay
Default: 30 seconds (30000ms)

The delay before clearing completed workflow state can be adjusted by modifying the timeout value in `workflow.js`:
```javascript
setTimeout(async () => {
  await clearWorkflowState();
}, 30000); // Adjust this value
```

## User Experience

### Normal Workflow
1. User starts a workflow
2. Steps execute one by one with visual feedback
3. Workflow completes
4. Success message is displayed
5. State is cleared after 30 seconds

### Page Refresh During Workflow
1. User refreshes the page while workflow is running
2. Page loads and checks for active workflow state
3. Vastai-setup tab is automatically selected
4. Previous step statuses are restored
5. Warning message: "⚠️ Workflow was in progress. You may need to restart it."
6. User can see which steps completed before the refresh

### Opening New Tab/Window
1. User opens a new tab or window while workflow is running
2. Same restoration behavior as refresh
3. Both tabs can see the workflow state
4. State is shared across all sessions

## Testing

The implementation includes comprehensive tests:

### Unit Tests (`test/test_workflow_state.py`)
- Save and load state
- Clear state
- Check if workflow is active
- Update step progress
- Get state summary
- Invalid JSON recovery
- Concurrent access

### Integration Tests (`test/test_workflow_state_api.py`)
- GET /workflow/state with and without state
- POST /workflow/state
- DELETE /workflow/state
- GET /workflow/state/summary
- CORS OPTIONS requests
- Complete workflow lifecycle

Run tests with:
```bash
python3 -m pytest test/test_workflow_state.py test/test_workflow_state_api.py -v
```

## Thread Safety

The WorkflowStateManager uses a threading.Lock to ensure thread-safe access to the state file. This prevents race conditions when multiple requests try to update the state simultaneously.

## Error Handling

- Corrupted JSON files are automatically detected and removed
- Failed file operations return False and log errors
- API endpoints return appropriate HTTP status codes (400, 500)
- Frontend gracefully handles missing or invalid state

## Security Considerations

### Current Implementation
- State file is stored in `/tmp/workflow_state.json`
- File permissions inherit from system defaults (typically 644)
- No sensitive data should be stored in workflow state

### Recommendations
For production deployments:
1. Use a more secure location (e.g., `/var/lib/vast_api/workflow_state.json`)
2. Set restrictive file permissions (600 or 640)
3. Consider encrypting sensitive data like SSH connection strings
4. Implement state file rotation/cleanup for long-running systems

## Limitations

1. **Single Workflow**: Only one workflow can be tracked at a time. Starting a new workflow overwrites the previous state.

2. **Shared State**: All users/sessions share the same workflow state. This is by design but may not be suitable for multi-user scenarios.

3. **No Persistence Across Restarts**: If the server restarts, the state file in `/tmp` may be lost (depending on OS configuration).

4. **Manual Restart Required**: If a workflow is interrupted by a page refresh, it must be manually restarted. The system does not auto-resume workflows.

## Future Enhancements

Potential improvements for future versions:

1. **Multi-Workflow Support**: Track multiple concurrent workflows with unique IDs
2. **Per-User State**: Implement session-based state management
3. **Auto-Resume**: Automatically resume interrupted workflows
4. **State History**: Keep a history of recent workflows
5. **Persistent Storage**: Use a database instead of file-based storage
6. **Secure Storage**: Encrypt sensitive data in state files
7. **State Expiration**: Automatic cleanup of old workflow states
8. **Progress Streaming**: Real-time progress updates via WebSocket
