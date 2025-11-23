# Custom Nodes Progress Tracking - Architecture Documentation

## Overview

This document describes the asynchronous architecture implemented for real-time progress tracking during custom nodes installation in ComfyUI workflows.

## Problem Statement

The original implementation had a critical architectural flaw:
- Installation endpoint blocked HTTP request thread for 30+ minutes
- Progress updates only written during blocking stdout parsing
- Frontend polling couldn't retrieve progress due to request blocking
- UI showed only "Clone Auto-installer" with no real-time updates

## Solution Architecture

### High-Level Design

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│                 │         │                  │         │                 │
│  Frontend       │         │  Flask API       │         │  Remote         │
│  Workflow       │         │  Server          │         │  Instance       │
│  Executor       │         │                  │         │  (VastAI)       │
│                 │         │                  │         │                 │
└────────┬────────┘         └────────┬─────────┘         └────────┬────────┘
         │                           │                            │
         │  1. POST install-custom-  │                            │
         │     nodes                 │                            │
         ├──────────────────────────>│                            │
         │                           │                            │
         │  2. Return task_id        │                            │
         │     (immediate)           │                            │
         │<──────────────────────────┤                            │
         │                           │                            │
         │                           │  3. Start background       │
         │                           │     thread                 │
         │                           │                            │
         │                           ├────────┐                   │
         │                           │        │                   │
         │                           │   Background               │
         │                           │   Thread:                  │
         │                           │   - SSH install script     │
         │                           │   - Parse stdout          │
         │                           │   - Write progress via SCP │
         │                           │        │                   │
         │                           │<───────┘                   │
         │                           │                            │
         │                           │  4. Write progress file    │
         │                           │     via SCP                │
         │                           ├───────────────────────────>│
         │                           │                            │
         │  5. Poll progress         │                            │
         │     (with task_id)        │                            │
         ├──────────────────────────>│                            │
         │                           │                            │
         │                           │  6. Read progress file     │
         │                           │     via SSH                │
         │                           ├───────────────────────────>│
         │                           │                            │
         │                           │  7. Return progress JSON   │
         │                           │<───────────────────────────┤
         │                           │                            │
         │  8. Return progress       │                            │
         │<──────────────────────────┤                            │
         │                           │                            │
         │  (Repeat 5-8 every 2s)    │                            │
         │                           │                            │
```

### Component Architecture

#### 1. BackgroundTaskManager (`app/sync/background_tasks.py`)

**Purpose:** Manages lifecycle of background tasks with thread-safe operations.

**Key Features:**
- Thread-safe task registration and status tracking
- Automatic cleanup of old tasks (2-hour retention)
- Support for multiple concurrent tasks
- Error handling and failure tracking

**API:**
```python
class BackgroundTaskManager:
    def start_task(task_id: str, target_func: Callable, *args, **kwargs) -> str
    def get_status(task_id: str) -> Optional[Dict]
    def is_task_running(task_id: str) -> bool
    def cleanup_task(task_id: str) -> bool
    def get_all_tasks() -> Dict[str, Dict]
```

**Task States:**
- `running`: Task is actively executing
- `completed`: Task finished successfully
- `failed`: Task raised an exception

#### 2. Installation Endpoint (`app/sync/sync_api.py`)

**Endpoint:** `POST /ssh/install-custom-nodes`

**Old Behavior:**
- Blocked for entire installation duration (30+ minutes)
- Returned results only after completion
- Frontend timeout issues
- No progress tracking possible

**New Behavior:**
- Returns immediately (< 1 second)
- Generates unique task_id (UUID)
- Starts background thread via BackgroundTaskManager
- Client uses task_id to poll progress

**Request:**
```json
{
  "ssh_connection": "root@ssh6.vast.ai -p 12345",
  "ui_home": "/workspace/ComfyUI"
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Installation started in background"
}
```

#### 3. Background Worker (`app/sync/sync_api.py`)

**Function:** `_run_installation_background(task_id, ssh_connection, ui_home)`

**Responsibilities:**
1. Write initial progress file
2. Check/clone ComfyUI-Auto_installer if needed
3. Execute installation script via SSH
4. Parse stdout in real-time
5. Update progress file via SCP after each node
6. Write completion status

**Progress Updates:**
- Written after each custom node starts
- Includes requirements installation status
- Success/failure tracking
- Final statistics on completion

**Progress File Location:** `/tmp/custom_nodes_progress_{task_id}.json`

**Why Task-Specific Files:**
- Supports concurrent installations
- No race conditions between instances
- Clean separation of concerns
- Easy cleanup per task

#### 4. Progress Endpoint (`app/sync/sync_api.py`)

**Endpoint:** `POST /ssh/install-custom-nodes/progress`

**Old Behavior:**
- Single global progress file
- Race conditions with concurrent installs
- No task association

**New Behavior:**
- Requires task_id parameter
- Reads task-specific progress file
- Returns real-time installation state
- Works during active installation

**Request:**
```json
{
  "ssh_connection": "root@ssh6.vast.ai -p 12345",
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response (In Progress):**
```json
{
  "success": true,
  "in_progress": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_nodes": 34,
  "processed": 15,
  "current_node": "ComfyUI-Manager",
  "current_status": "running",
  "successful": 14,
  "failed": 0,
  "has_requirements": true,
  "requirements_status": "running"
}
```

**Response (Completed):**
```json
{
  "success": true,
  "in_progress": false,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "completed": true,
  "success": true,
  "total_nodes": 34,
  "processed": 34,
  "successful_clones": 32,
  "failed_clones": 2
}
```

#### 5. Workflow Executor (`app/sync/workflow_executor.py`)

**Method:** `_execute_install_custom_nodes()`

**Old Behavior:**
```python
# Start installation in thread
install_thread = threading.Thread(target=run_install, daemon=True)
install_thread.start()

# Poll progress while thread runs
while install_thread.is_alive():
    progress = poll_progress()  # No task context
```

**Problems:**
- Installation thread blocked on HTTP request
- Progress polling happened in parallel but got no data
- Thread deadlock scenario

**New Behavior:**
```python
# Start installation (returns immediately with task_id)
response = requests.post('/ssh/install-custom-nodes', json={...})
task_id = response.json()['task_id']

# Poll progress using task_id
while not installation_completed:
    progress = requests.post('/ssh/install-custom-nodes/progress',
                           json={'task_id': task_id, ...})
    
    if progress['completed']:
        installation_completed = True
    
    # Update tasklist from progress
    update_tasklist(progress)
    time.sleep(2)
```

**Benefits:**
- No thread blocking on HTTP request
- Real progress data from background worker
- Proper completion detection
- Clean timeout handling

## Data Flow

### Installation Start Flow

1. Frontend calls `/ssh/install-custom-nodes`
2. API generates unique `task_id` (UUID)
3. API clears any old progress file for safety
4. API starts background task via `BackgroundTaskManager`
5. Background worker immediately writes initial progress file
6. API returns `task_id` to frontend (< 1 second elapsed)
7. Background worker continues installation independently

### Progress Update Flow

1. Background worker executes SSH command to run install script
2. Script outputs: `[1/34] Processing custom node: ComfyUI-Manager`
3. Worker parses line and extracts progress data
4. Worker writes JSON progress file to remote via SCP
5. Frontend polls `/ssh/install-custom-nodes/progress` with `task_id`
6. API reads progress file from remote via SSH
7. API returns progress JSON to frontend
8. Frontend updates tasklist UI
9. Repeat every 2 seconds until completion

### Completion Flow

1. Install script exits (all nodes processed)
2. Background worker calls `process.wait()` to get exit code
3. Worker determines success based on exit code and failures
4. Worker writes final progress with `in_progress: false`
5. Frontend detects completion in next poll
6. Frontend shows final status and moves to next step
7. BackgroundTaskManager marks task as `completed`
8. Task auto-cleaned after 2 hours

## Thread Safety

### Concurrent Access Patterns

**Multiple Installations:**
- Each gets unique task_id
- Separate progress files: `/tmp/custom_nodes_progress_{task_id}.json`
- No shared state between installations
- BackgroundTaskManager handles thread-safe task registry

**Progress Polling:**
- Read-only operation via SSH subprocess
- No locking needed for file reads
- SCP writes are atomic at file level

**Task Manager:**
- Uses `threading.Lock()` for all state modifications
- Task dictionary is thread-safe
- Status queries are protected by lock

## Error Handling

### Installation Errors

**Scenario:** SSH connection fails
- Background worker catches exception
- Writes error to progress file
- Task marked as `failed`
- Frontend displays error message

**Scenario:** Install script fails
- Worker detects non-zero exit code
- Writes completion status with success=false
- Includes error details in progress
- Frontend shows failure state

### Progress Polling Errors

**Scenario:** Progress file doesn't exist
- SSH cat returns empty or '{}'
- API returns `in_progress: false`
- Frontend knows to check task completion

**Scenario:** SSH connection timeout
- API catches exception
- Returns error response to frontend
- Frontend can retry or fail gracefully

### Task Manager Errors

**Scenario:** Task already running
- `start_task()` raises `ValueError`
- API returns 409 Conflict
- Frontend displays appropriate error

## Performance Characteristics

### Response Times

| Operation | Old | New | Improvement |
|-----------|-----|-----|-------------|
| Start installation | 30+ minutes | < 1 second | 1800x faster |
| First progress update | Never | 2-5 seconds | ∞ improvement |
| Progress poll interval | N/A | 2 seconds | Real-time |
| Completion detection | After timeout | Immediate | Instant |

### Resource Usage

**Old:**
- 1 blocked HTTP worker thread per installation
- Entire Flask worker pool could be exhausted
- No cleanup mechanism

**New:**
- HTTP request completes immediately
- 1 daemon background thread per installation
- Automatic cleanup after 2 hours
- Unlimited concurrent installations (bounded by system resources)

### Scalability

**Concurrent Installations:**
- Old: Limited by Flask worker pool size (~4-8)
- New: Limited only by system thread limit (~thousands)

**Memory:**
- Old: Progress data in memory only during request
- New: Minimal memory per task (status dict + thread overhead)
- Cleanup prevents unbounded growth

## Migration Notes

### API Changes

**Breaking Changes:**
- `/ssh/install-custom-nodes` response format changed
- `/ssh/install-custom-nodes/progress` requires task_id

**Backward Compatibility:**
- Old frontend code will break (expects different response)
- Must update workflow_executor.py in sync
- Progress endpoint parameter is required

### Deployment Steps

1. Deploy new backend code
2. Restart Flask server
3. Frontend automatically uses new API
4. Old in-progress installations will be orphaned (acceptable)

### Rollback Plan

If issues arise:
1. Revert code changes
2. Restart server
3. Any in-progress installations will fail (expected)
4. Users can retry installations

## Testing Strategy

See `TESTING_GUIDE.md` for comprehensive testing procedures.

**Key Test Areas:**
1. Unit tests for BackgroundTaskManager (14 tests)
2. Integration tests for API endpoints
3. End-to-end workflow testing
4. Concurrent installation testing
5. Error condition testing
6. Performance regression testing

## Future Enhancements

### Potential Improvements

1. **WebSocket Support:** Replace polling with push notifications
2. **Installation Queuing:** Queue installations instead of concurrent execution
3. **Detailed Logs:** Stream full installation logs in real-time
4. **Installation History:** Persist installation history in database
5. **Retry Mechanism:** Auto-retry failed installations
6. **Resource Limits:** Cap concurrent installations per user/instance

### Technical Debt

- Progress file cleanup could be more aggressive
- SCP for progress writes could be replaced with SSH echo
- Error messages could be more detailed
- Task manager could use persistent storage

## Conclusion

The async architecture successfully addresses the original problem:
- ✅ Non-blocking installation start
- ✅ Real-time progress updates
- ✅ Concurrent installations support
- ✅ Clean error handling
- ✅ Automatic resource cleanup
- ✅ Improved user experience

The implementation is production-ready and fully tested.
