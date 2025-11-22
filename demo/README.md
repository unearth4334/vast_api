# Workflow Visualization Demo

This demo demonstrates the on-the-fly webui rendering of in-progress workflows using temporary state files.

## Overview

The `workflow_visualization_demo.py` script creates:
1. Sample workflow state files (JSON) representing different workflow states
2. HTML visualizations that render these state files as a user would see them in the web UI

## Running the Demo

```bash
cd /home/runner/work/vast_api/vast_api
python3 demo/workflow_visualization_demo.py
```

## Output

The script generates files in `/tmp/workflow_demo/`:

### State Files
- `state_in_progress.json` - Workflow with 3/5 steps completed, 1 in progress
- `state_completed.json` - Successfully completed workflow (all 5 steps done)
- `state_failed.json` - Failed workflow (failed at step 3)

### HTML Visualizations
- `visualization_in_progress.html` - Shows workflow in progress with spinner animation
- `visualization_completed.html` - Shows all steps completed with green checkmarks
- `visualization_failed.html` - Shows failed step with red X and remaining steps pending

## Screenshots

### Workflow In Progress (3/5 steps completed)
![Workflow In Progress](https://github.com/user-attachments/assets/011d69d2-aa4c-4488-8089-ac4dd4302811)

**State:** 60% complete, 4th step actively running with spinner animation

### Workflow Completed (5/5 steps completed)
![Workflow Completed](https://github.com/user-attachments/assets/35d664fc-8dd5-42ac-ad16-6df179a4a5cb)

**State:** 100% complete, all steps marked with green checkmarks

### Workflow Failed (failed at step 3)
![Workflow Failed](https://github.com/user-attachments/assets/13d52453-417c-44c5-bcd3-b7b4ef8838d4)

**State:** Failed at 40% progress, step 3 marked with red X

## Key Features Demonstrated

1. **Real-time State Persistence**: State files contain workflow_id, status, current_step, and step details
2. **Visual Status Indicators**: 
   - ✓ Green checkmark for completed steps
   - ⟳ Blue spinner for in-progress steps (with CSS animation)
   - ✗ Red X for failed steps
   - ○ Grey circle for pending steps
3. **Progress Tracking**: Shows X/Y steps completed with percentage
4. **Status Messages**: Clear banner messages indicating workflow state
5. **Metadata Display**: Workflow ID, timestamps, progress metrics

## How It Works

The workflow state file (`/tmp/workflow_state.json`) is continuously updated by the server-side `WorkflowExecutor` as steps complete. The web UI polls this file every second via the `/workflow/state` API endpoint and renders the progress visualization in real-time.

This allows users to:
- Refresh the page during workflow execution and see current progress
- Open multiple tabs/windows showing the same workflow
- Navigate away and return later to see the workflow state

## Integration with Main Application

In the actual application:
- State files are managed by `WorkflowStateManager` (`app/sync/workflow_state.py`)
- Workflows execute in background threads via `WorkflowExecutor` (`app/sync/workflow_executor.py`)
- Frontend polls `/workflow/state` API endpoint every 1 second
- UI updates are handled by `updateWorkflowUI()` in `workflow.js`
- Page refresh triggers `restoreWorkflowState()` to reconnect to active workflows
