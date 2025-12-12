# Headless Server-Side Workflow Execution - Implementation Summary

**Branch:** `feature/headless-workflow-execution`  
**Status:** Phase 3 Complete - Core Implementation Done  
**Date:** December 2024

## Overview

This document summarizes the implementation of server-side workflow execution for the VastAI management WebUI. The feature enables headless, background execution of cloud instance setup workflows that continue running even if the browser is closed or refreshed.

## Architecture

### Unified Server-Side Model

All workflow execution happens server-side in background threads. The WebUI is a pure visualization client that polls workflow state from the server.

```
┌─────────────────────────────────────────────────────────────┐
│                     WebUI (Browser)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  workflow-refactored.js (Visualization Client)       │  │
│  │  - Polls /workflow/state every 2 seconds            │  │
│  │  - Renders progress from server state               │  │
│  │  - Restores state on page load                      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP/JSON
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Flask Server (sync_api.py)                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Workflow API Endpoints:                            │  │
│  │  - POST /workflow/start                             │  │
│  │  - POST /workflow/stop                              │  │
│  │  - GET  /workflow/state                             │  │
│  │  - GET  /workflow/state/summary                     │  │
│  │  - POST /workflow/clear                             │  │
│  └──────────────────────────────────────────────────────┘  │
│              │                                    ▲          │
│              │ calls                              │          │
│              ▼                                    │          │
│  ┌──────────────────────┐          ┌─────────────────────┐ │
│  │  WorkflowExecutor    │          │ WorkflowStateManager│ │
│  │  (Background Thread) │◄─────────┤ (JSON Persistence)  │ │
│  │  - Executes steps    │  updates │ /tmp/workflow_state │ │
│  │  - Calls SSH APIs    │          │     .json           │ │
│  │  - Updates state     │          └─────────────────────┘ │
│  └──────────────────────┘                                   │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Details

### Phase 1: Server-Side Execution ✅

**Files Created:**
- `app/sync/workflow_state.py` - Persistent state management
- `app/sync/workflow_executor.py` - Background thread execution

**Key Components:**

#### WorkflowStateManager
- **Purpose:** Thread-safe persistent state storage
- **State File:** `/tmp/workflow_state.json`
- **Methods:**
  - `save_state(state)` - Atomic write with temp file + rename
  - `load_state()` - Thread-safe JSON loading with corruption recovery
  - `clear_state()` - Remove state file
  - `update_step_progress(step_index, status, data)` - Update individual step
  - `get_state_summary()` - Lightweight summary with progress %

**State Schema:**
```json
{
  "workflow_id": "uuid",
  "status": "running|completed|failed|cancelled",
  "current_step": 0,
  "steps": [
    {
      "action": "test_ssh",
      "label": "🔧 Test SSH Connection",
      "status": "completed|in_progress|failed|pending",
      "progress": { ... }
    }
  ],
  "start_time": "2024-12-01T10:00:00.000Z",
  "last_update": "2024-12-01T10:05:00.000Z",
  "ssh_connection": "ssh -p 12345 root@1.2.3.4 ..."
}
```

#### WorkflowExecutor
- **Purpose:** Execute workflows in background daemon threads
- **Thread Safety:** Daemon threads with stop flags
- **Execution Flow:**
  1. `start_workflow()` - Create and start background thread
  2. `_execute_workflow()` - Main loop executing steps sequentially
  3. `_execute_step()` - Dispatch to specific step executor
  4. Step executors call actual SSH API endpoints via HTTP

**Step Executors Implemented:**

| Method | Endpoint | Purpose | Timeout |
|--------|----------|---------|---------|
| `_execute_test_ssh` | `/ssh/test` | Test SSH connectivity | 30s |
| `_execute_set_ui_home` | `/ssh/set-ui-home` | Set UI_HOME env var | 30s |
| `_execute_get_ui_home` | `/ssh/get-ui-home` | Read UI_HOME value | 30s |
| `_execute_setup_civitdl` | `/ssh/setup-civitdl` | Install CivitDL | 180s |
| `_execute_test_civitdl` | `/ssh/test-civitdl` | Validate CivitDL | 60s |
| `_execute_sync_instance` | `/sync/vastai-connection` | Sync media | 600s |
| `_execute_install_custom_nodes` | `/ssh/install-custom-nodes` | Install ComfyUI nodes | 1800s |
| `_execute_verify_dependencies` | `/ssh/verify-dependencies` | Check/install deps | 300s |
| `_execute_reboot_instance` | `/ssh/reboot-instance` | Reboot instance | 30s + 30s wait |

**Error Handling:**
- All API calls wrapped in try/except
- HTTP timeouts configured per step
- Detailed logging of failures
- State persisted on error

### Phase 2: API Endpoints ✅

**File Modified:** `app/sync/sync_api.py`

**Endpoints Added:**

#### POST /workflow/start
**Purpose:** Start workflow execution in background thread  
**Request Body:**
```json
{
  "workflow_id": "optional-uuid",
  "steps": [
    {
      "action": "test_ssh",
      "label": "🔧 Test SSH Connection",
      "status": "pending"
    }
  ],
  "ssh_connection": "ssh -p 12345 root@1.2.3.4 ...",
  "step_delay": 5,
  "instance_id": 12345
}
```
**Response:**
```json
{
  "success": true,
  "message": "Workflow started successfully",
  "workflow_id": "uuid"
}
```

#### POST /workflow/stop
**Purpose:** Request workflow cancellation  
**Request Body:**
```json
{
  "workflow_id": "uuid"
}
```
**Response:**
```json
{
  "success": true,
  "message": "Workflow stop requested"
}
```

#### GET /workflow/state
**Purpose:** Get full workflow state for visualization  
**Query Params:** `?workflow_id=uuid` (optional)  
**Response:**
```json
{
  "success": true,
  "state": {
    "workflow_id": "uuid",
    "status": "running",
    "current_step": 2,
    "steps": [ ... ],
    "start_time": "...",
    "last_update": "..."
  }
}
```

#### GET /workflow/state/summary
**Purpose:** Lightweight summary for progress updates  
**Query Params:** `?workflow_id=uuid` (optional)  
**Response:**
```json
{
  "success": true,
  "has_workflow": true,
  "summary": {
    "active": true,
    "workflow_id": "uuid",
    "status": "running",
    "current_step": 2,
    "total_steps": 10,
    "progress_percent": 30.0,
    "is_running": true,
    "start_time": "...",
    "last_update": "..."
  }
}
```

#### POST /workflow/clear
**Purpose:** Clear workflow state file  
**Response:**
```json
{
  "success": true,
  "message": "Workflow state cleared"
}
```

### Phase 3: WebUI Refactor ✅

**File Created:** `app/webui/js/workflow-refactored.js`

**Key Changes:**
- Removed all client-side step execution logic
- Individual step buttons disabled (workflow-only mode)
- Added server API integration
- State polling every 2 seconds
- Automatic state restoration on page load

**New Functions:**

| Function | Purpose |
|----------|---------|
| `initWorkflow()` | Initialize + restore state on page load |
| `restoreWorkflowState()` | Restore workflow state from server |
| `runWorkflow()` | Start workflow on server (POST /workflow/start) |
| `stopWorkflow()` | Stop workflow on server (POST /workflow/stop) |
| `startWorkflowPolling()` | Begin 2-second polling interval |
| `stopWorkflowPolling()` | Stop polling when workflow finishes |
| `updateWorkflowVisualization()` | Fetch + render server state |
| `renderWorkflowState(state)` | Update UI from state object |
| `resetWorkflowVisualization()` | Clear all visual indicators |

**Polling Logic:**
```javascript
// Poll every 2 seconds while running
workflowPollingInterval = setInterval(async () => {
  await updateWorkflowVisualization();
}, 2000);

// Stop polling when workflow finishes
if (status === 'completed' || status === 'failed' || status === 'cancelled') {
  stopWorkflowPolling();
}
```

**State Restoration Flow:**
```
Page Load
   ↓
initWorkflow()
   ↓
restoreWorkflowState()
   ↓
GET /workflow/state/summary
   ↓
if (is_running) → startWorkflowPolling()
if (finished)   → renderFinalState()
```

## Configuration

### Workflow Settings
- **Step Delay:** 5 seconds (configurable in `config.yaml`)
- **Poll Interval:** 2 seconds (hardcoded in `workflow-refactored.js`)
- **State File:** `/tmp/workflow_state.json`

### Timeouts by Step
- Standard steps: 30-60 seconds
- CivitDL setup: 180 seconds (3 minutes)
- Sync instance: 600 seconds (10 minutes)
- Install custom nodes: 1800 seconds (30 minutes)
- Verify dependencies: 300 seconds (5 minutes)

## Testing

### Manual Testing Checklist

**Phase 4: End-to-End Testing** (Not yet complete)

- [ ] Test workflow start with all steps enabled
- [ ] Test workflow with mixed enabled/disabled steps
- [ ] Test workflow cancellation mid-execution
- [ ] Test browser refresh during workflow execution
- [ ] Test browser close + reopen during workflow
- [ ] Test workflow state restoration after completion
- [ ] Test workflow failure handling (e.g., SSH failure)
- [ ] Test parallel workflows (should reject)
- [ ] Test state clearing after workflow
- [ ] Verify all API endpoints respond correctly
- [ ] Verify SSH API calls are made correctly
- [ ] Check log output for each step
- [ ] Verify state file updates in real-time
- [ ] Test arrow animations and progress indicators
- [ ] Validate final status messages (success/failure/cancelled)

### API Testing with curl

```bash
# Start workflow
curl -X POST http://localhost:5000/workflow/start \
  -H 'Content-Type: application/json' \
  -d '{
    "steps": [
      {"action": "test_ssh", "label": "Test SSH", "status": "pending"}
    ],
    "ssh_connection": "ssh -p 12345 root@1.2.3.4 ...",
    "step_delay": 5
  }'

# Check state
curl http://localhost:5000/workflow/state

# Stop workflow
curl -X POST http://localhost:5000/workflow/stop \
  -H 'Content-Type: application/json' \
  -d '{"workflow_id": "uuid"}'

# Clear state
curl -X POST http://localhost:5000/workflow/clear
```

## Remaining Work

### Phase 4: Replace Old Workflow ⏳
- [ ] Backup original `workflow.js`
- [ ] Replace with `workflow-refactored.js`
- [ ] Update HTML script tags
- [ ] Test all template configurations
- [ ] Verify backward compatibility

### Phase 5: Enhanced Testing ⏳
- [ ] Create automated test suite
- [ ] Add unit tests for WorkflowExecutor
- [ ] Add integration tests for API endpoints
- [ ] Test error recovery scenarios
- [ ] Performance testing with long workflows

### Phase 6: Documentation ⏳
- [ ] Update README with workflow feature
- [ ] Create user guide for workflow execution
- [ ] Document API endpoints in OpenAPI/Swagger
- [ ] Add troubleshooting guide
- [ ] Update deployment docs

## Known Limitations

1. **Single Workflow:** Only one workflow can run at a time (enforced by WorkflowExecutor)
2. **State Persistence:** State file in `/tmp` - will be lost on system reboot
3. **No History:** Previous workflow states are overwritten
4. **No Rollback:** Failed steps don't automatically rollback changes
5. **Progress Detail:** Limited progress detail for long-running steps (custom nodes)

## Future Enhancements

1. **Multiple Workflows:** Support parallel workflow execution
2. **Workflow History:** Store past workflow executions in database
3. **Granular Progress:** Real-time progress for custom nodes installation
4. **Resume/Retry:** Resume failed workflows from last successful step
5. **Workflow Templates:** Save/load custom workflow configurations
6. **Notifications:** Email/webhook notifications on workflow completion
7. **Scheduling:** Schedule workflows to run at specific times
8. **State Persistence:** Move to SQLite database instead of JSON file

## Migration Notes

### For Developers

**Before:**
```javascript
// Client-side execution (OLD)
async function executeWorkflowStep(stepElement) {
  const action = stepElement.dataset.action;
  const result = await callSSHEndpoint(action);
  return result.success;
}
```

**After:**
```javascript
// Server-side execution (NEW)
async function runWorkflow() {
  const response = await fetch('/workflow/start', {
    method: 'POST',
    body: JSON.stringify({ steps, ssh_connection })
  });
  startWorkflowPolling();
}
```

### For Users

**Benefits:**
- ✅ Workflows continue if browser crashes
- ✅ Can close browser during long operations
- ✅ Refresh page to check progress
- ✅ Better error recovery
- ✅ Centralized logging on server

**Changes:**
- Individual step buttons disabled (use workflow runner)
- Must use "Run Workflow" button for execution
- Progress shown via polling (slight delay)

## Commits

1. **c3d786f** - Phase 1: Server-side execution foundation
2. **22c176f** - Phase 3: WebUI visualization client

## References

- Original Proposal: `docs/PROPOSAL_Headless Server-Side Workflow Execution.md`
- Reference Branch: `copilot/add-server-side-workflow-status`
- Feature Branch: `feature/headless-workflow-execution`
- Flask API: `app/sync/sync_api.py`
- Workflow Executor: `app/sync/workflow_executor.py`
- State Manager: `app/sync/workflow_state.py`
- WebUI Client: `app/webui/js/workflow-refactored.js`

---

**Status:** Core implementation complete. Ready for Phase 4 (integration) and Phase 5 (testing).
