# Custom Nodes Progress Tracking - Testing Guide

## Overview

This document describes how to test the async architecture implementation for custom nodes installation progress tracking.

## Unit Tests

### Background Task Manager Tests

Located in: `test/test_background_tasks.py`

**Run tests:**
```bash
cd /home/runner/work/vast_api/vast_api
python3 test/test_background_tasks.py -v
```

**Test Coverage:**
- Task creation and lifecycle
- Concurrent task execution
- Error handling and failure states
- Task cleanup and management
- Thread safety

**Expected Results:** 14 tests, all passing

### Integration Tests

Located in: `test/test_custom_nodes_async_api.py`

**Requirements:**
- Flask and dependencies must be installed
- Run with: `pip install -r requirements.txt`

**Run tests:**
```bash
cd /home/runner/work/vast_api/vast_api
python3 test/test_custom_nodes_async_api.py -v
```

**Test Coverage:**
- API endpoint behavior
- task_id generation and validation
- Progress polling with task_id
- Error conditions and edge cases
- Background worker initialization

## Manual Testing

### Prerequisites

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Have SSH access to a VastAI instance with ComfyUI

3. Start the sync API server:
   ```bash
   python3 scripts/run_sync_api.py
   ```

### Test Scenario 1: Start Installation

**Request:**
```bash
curl -X POST http://localhost:5000/ssh/install-custom-nodes \
  -H "Content-Type: application/json" \
  -d '{
    "ssh_connection": "root@ssh6.vast.ai -p 12345",
    "ui_home": "/workspace/ComfyUI"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Installation started in background"
}
```

**Validation:**
- Response is immediate (< 1 second)
- task_id is a valid UUID
- success is true

### Test Scenario 2: Poll Progress

**Request:**
```bash
curl -X POST http://localhost:5000/ssh/install-custom-nodes/progress \
  -H "Content-Type: application/json" \
  -d '{
    "ssh_connection": "root@ssh6.vast.ai -p 12345",
    "task_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

**Expected Response (In Progress):**
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

**Expected Response (Completed):**
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
  "failed_clones": 2,
  "successful_requirements": 28,
  "failed_requirements": 4,
  "return_code": 0
}
```

**Validation:**
- Progress updates in real-time (poll every 2 seconds)
- processed count increments
- current_node changes as installation progresses
- Completion is detected when in_progress becomes false

### Test Scenario 3: Frontend Workflow Integration

**Test Steps:**
1. Open the web UI
2. Start a workflow that includes "Install Custom Nodes" step
3. Observe the tasklist during installation

**Expected Behavior:**
- "Clone Auto-installer" task appears and completes quickly
- Individual custom nodes appear in rolling window (max 4 visible)
- "# others" summary shows remaining nodes
- Progress updates smoothly every 2 seconds
- Dependencies shown as sub-tasks when applicable
- "Verify Dependencies" task appears at the end

### Test Scenario 4: Concurrent Installations

**Test Steps:**
1. Start installation on Instance A
2. Start installation on Instance B (different SSH connection)
3. Both should proceed independently

**Expected Behavior:**
- Each installation gets unique task_id
- Progress for each can be polled independently
- No interference between installations
- Both complete successfully

### Test Scenario 5: Error Handling

**Test Case 5.1: Invalid SSH Connection**
```bash
curl -X POST http://localhost:5000/ssh/install-custom-nodes \
  -H "Content-Type: application/json" \
  -d '{
    "ssh_connection": "invalid-format",
    "ui_home": "/workspace/ComfyUI"
  }'
```

**Expected:**
```json
{
  "success": false,
  "message": "Invalid SSH connection format: ..."
}
```

**Test Case 5.2: Missing Parameters**
```bash
curl -X POST http://localhost:5000/ssh/install-custom-nodes \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected:**
```json
{
  "success": false,
  "message": "SSH connection string is required"
}
```

**Test Case 5.3: Nonexistent task_id**
```bash
curl -X POST http://localhost:5000/ssh/install-custom-nodes/progress \
  -H "Content-Type: application/json" \
  -d '{
    "ssh_connection": "root@ssh6.vast.ai -p 12345",
    "task_id": "nonexistent-uuid"
  }'
```

**Expected:**
```json
{
  "success": true,
  "in_progress": false,
  "task_id": "nonexistent-uuid",
  "message": "No progress available for this task"
}
```

## Performance Testing

### Metrics to Monitor

1. **Response Time:**
   - Installation start: < 1 second (was 30+ minutes before)
   - Progress polling: < 2 seconds per request
   
2. **Resource Usage:**
   - Background threads should be daemon threads
   - Completed tasks cleaned up after 2 hours
   - No memory leaks from long-running installations

3. **Concurrency:**
   - Multiple installations can run simultaneously
   - Progress polling doesn't block installation
   - Task manager handles thread safety correctly

## Troubleshooting

### Installation Not Starting

Check server logs for:
- SSH connection errors
- Task manager initialization errors
- Background thread creation failures

### Progress Not Updating

1. Verify progress file exists on remote:
   ```bash
   ssh root@ssh6.vast.ai -p 12345 "cat /tmp/custom_nodes_progress_{task_id}.json"
   ```

2. Check for SCP errors in server logs

3. Verify task is actually running:
   ```bash
   ssh root@ssh6.vast.ai -p 12345 "ps aux | grep install-custom-nodes"
   ```

### Task Stuck in Running State

1. Check if background thread is alive (server logs)
2. Check if remote process completed (SSH to instance)
3. Verify completion detection logic in background worker

## Success Criteria

✅ Installation endpoint returns immediately (< 1 second)
✅ Progress updates appear within 2-3 seconds of polling
✅ Frontend tasklist shows real-time progress
✅ Multiple concurrent installations work independently
✅ Error conditions handled gracefully
✅ No memory leaks or resource exhaustion
✅ All unit tests pass (14/14)
✅ Background tasks cleaned up automatically

## Regression Testing

Run existing test suite to ensure no breakage:
```bash
cd /home/runner/work/vast_api/vast_api
python3 -m unittest discover -s test -p "test_*.py"
```

**Expected:** No new failures compared to baseline (some unrelated import errors may exist)
