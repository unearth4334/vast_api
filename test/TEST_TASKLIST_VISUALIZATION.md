# Install Custom Nodes Tasklist Visualization Test

## Purpose
This test suite verifies that the install-custom-nodes workflow correctly displays progress in the web UI tasklist.

## What is Tested

### 1. Task Progression Sequence (`test_tasklist_progression_sequence`)
Verifies that tasks appear in the correct order:
1. Clone Auto-installer
2. Configure venv path
3. Individual custom nodes
4. Verify Dependencies

### 2. Rolling Display (`test_rolling_display_with_max_4_nodes`)
Tests that only 4 custom nodes are visible at once, with:
- First 4 nodes shown initially
- "# others" summary for remaining nodes
- Rolling window as installation progresses

### 3. Dependencies as Subtasks (`test_subtask_for_dependencies`)
Verifies that when a custom node has dependencies:
- Node appears with status
- "Install dependencies" appears as a subtask
- Subtask status updates independently

### 4. Verify Dependencies Task (`test_verify_dependencies_appears_at_end`)
Confirms that "Verify Dependencies" task appears after all nodes are installed.

### 5. Progress Updates (`test_progress_updates_populate_tasklist`)
Tests that backend progress updates correctly populate the tasklist through the sequence:
- Initializing
- Configure venv path
- Individual nodes (with dependencies)
- Completion

### 6. Completed Others Summary (`test_completed_others_summary`)
When more than 4 nodes are completed, tests that:
- Completed nodes show as "# others" with success count (e.g., "3 others: success (3/3)")
- Last 4 nodes are displayed
- Remaining nodes show as pending "# others"

### 7. Task Status Transitions (`test_task_status_transitions`)
Verifies that task statuses transition correctly:
- pending → running → success
- pending → running → failed

### 8. Full Workflow Integration (`test_full_workflow_tasklist_visualization`)
End-to-end test that:
- Starts installation via API
- Receives task_id
- Polls progress endpoint
- Verifies progress data structure
- Confirms tasks appear in UI

## How to Run

### With Flask Installed (Full Test Suite)
```bash
cd /home/runner/work/vast_api/vast_api
python3 test/test_install_custom_nodes_tasklist.py -v
```

### Without Flask (Unit Tests Only)
The unit tests that don't require Flask can be run individually. The integration tests will be skipped.

## Expected Output

All tests should pass with output like:
```
test_completed_others_summary (__main__.TestInstallCustomNodesTasklist) ... ok
test_progress_updates_populate_tasklist (__main__.TestInstallCustomNodesTasklist) ... ok
test_rolling_display_with_max_4_nodes (__main__.TestInstallCustomNodesTasklist) ... ok
test_subtask_for_dependencies (__main__.TestInstallCustomNodesTasklist) ... ok
test_tasklist_progression_sequence (__main__.TestInstallCustomNodesTasklist) ... ok
test_task_status_transitions (__main__.TestInstallCustomNodesTasklist) ... ok
test_verify_dependencies_appears_at_end (__main__.TestInstallCustomNodesTasklist) ... ok
test_full_workflow_tasklist_visualization (__main__.TestTasklistIntegrationWithAPI) ... ok

----------------------------------------------------------------------
Ran 8 tests in X.XXXs

OK
```

## Test Data Structures

### Task Object
```python
{
    'name': 'Clone Auto-installer',
    'status': 'success',  # pending, running, success, failed
    'subtasks': [  # Optional
        {
            'name': 'Install dependencies',
            'status': 'running'
        }
    ]
}
```

### Progress Object
```python
{
    'in_progress': True,
    'task_id': 'uuid',
    'total_nodes': 34,
    'processed': 5,
    'current_node': 'ComfyUI-Manager',
    'current_status': 'running',
    'successful': 4,
    'failed': 0,
    'has_requirements': True,  # Optional
    'requirements_status': 'running'  # Optional
}
```

## Manual Testing

To manually verify the tasklist visualization:

1. Start a workflow with "Install Custom Nodes" step
2. Observe the web UI during installation
3. Verify you see:
   - ✅ Clone Auto-installer (appears first, completes quickly)
   - ✅ Configure venv path (appears after clone, completes quickly)
   - ✅ Individual custom nodes (rolling display of 4 at a time)
   - ✅ "# others" summary (appears when total > 4 nodes)
   - ✅ Dependencies as subtasks (when a node has requirements)
   - ✅ Verify Dependencies (appears at end)

## Troubleshooting

### Tasks Not Appearing
- Check that progress endpoint is returning task_id
- Verify progress file is being written to `/tmp/custom_nodes_progress_{task_id}.json`
- Check workflow_executor logs for progress polling

### Rolling Display Not Working
- Verify MAX_VISIBLE_NODES = 4 in workflow_executor.py
- Check that nodes_seen list is being maintained
- Ensure task list is being updated in state_manager

### Dependencies Not Showing as Subtasks
- Verify 'has_requirements' flag in progress data
- Check that 'requirements_status' is being set
- Ensure subtasks array is being added to node task

## Related Files

- **Test**: `test/test_install_custom_nodes_tasklist.py`
- **Backend**: `app/sync/sync_api.py` - `_run_installation_background()`
- **Frontend**: `app/sync/workflow_executor.py` - `_execute_install_custom_nodes()`
- **State**: `app/sync/workflow_state.py` - `WorkflowStateManager`
- **Background Tasks**: `app/sync/background_tasks.py` - `BackgroundTaskManager`
