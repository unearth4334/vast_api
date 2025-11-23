# Install Custom Nodes Progress Tracking - Debug Session Summary

## Date: November 23, 2025

## Problem

The Install Custom Nodes tasklist tile only showed "Clone Auto-installer" and failed to display the full task progression sequence showing individual node installation progress.

## Debugging Approach

Connected directly to the cloud instance (`ssh -p 48263 root@174.88.163.72`) to trace data flow from the source and verify the script's output format.

## Key Findings

### 1. Bash Subshell Variable Persistence Issue

**Problem**: The original script used `tail | while read` which creates a subshell, causing `SUCCESSFUL_NODES` and `FAILED_NODES` counters to reset after the loop.

**Original Code**:
```bash
tail -n +2 "$CUSTOM_NODES_CSV" | while IFS=',' read -r name repo_url subfolder requirements_file; do
    ((SUCCESSFUL_NODES++))  # This increment is lost!
done
```

**Fix**: Used process substitution to avoid subshell:
```bash
while IFS=',' read -r name repo_url subfolder requirements_file; do
    ((SUCCESSFUL_NODES++))  # Now persists correctly
done < <(tail -n +2 "$CUSTOM_NODES_CSV")
```

**Result**: Counters now properly track successful/failed installations (verified: `successful: 34` instead of `successful: 0`).

### 2. Progress File Path Mismatch

**Problem**: 
- Backend writes to task-specific file: `/tmp/custom_nodes_progress_{task_id}.json`
- Script wrote to fixed file: `/tmp/custom_nodes_progress.json`
- Backend couldn't read script's progress because files didn't match

**Fix**: Added `--progress-file` parameter to script:

**Script Changes**:
```bash
# New parameter parsing
CUSTOM_PROGRESS_FILE=""
if [ $# -ge 5 ] && [ "$4" = "--progress-file" ]; then
    CUSTOM_PROGRESS_FILE="$5"
fi

# Use custom or default
if [ -n "$CUSTOM_PROGRESS_FILE" ]; then
    PROGRESS_JSON="$CUSTOM_PROGRESS_FILE"
else
    PROGRESS_JSON="/tmp/custom_nodes_progress.json"
fi
```

**Backend Changes**:
```python
# sync_api.py - Pass progress file to script
install_cmd = [
    'ssh', '-p', str(ssh_port), '-i', ssh_key,
    '-o', 'ConnectTimeout=10',
    '-o', 'StrictHostKeyChecking=yes',
    '-o', 'UserKnownHostsFile=/root/.ssh/known_hosts',
    '-o', 'IdentitiesOnly=yes',
    f'root@{ssh_host}',
    f'source /etc/environment 2>/dev/null; cd /workspace/ComfyUI-Auto_installer/scripts && ./install-custom-nodes.sh {ui_home} --venv-path /venv/main/bin/python --progress-file {progress_file} 2>&1'
]
```

**Result**: Backend and script now use the same progress file, enabling proper progress tracking.

### 3. JSON Progress Format

The script now writes structured JSON progress:

```json
{
  "in_progress": true,
  "total_nodes": 34,
  "processed": 5,
  "current_node": "ComfyUI-Manager",
  "current_status": "running",
  "successful": 4,
  "failed": 0,
  "has_requirements": false,
  "requirements_status": "pending"
}
```

Fields support the rolling tasklist display:
- `total_nodes`: Total count for "X others" calculations
- `processed`: Current position in installation
- `current_node`: Node being processed (displayed in tasklist)
- `current_status`: `running`, `success`, `failed`
- `successful`/`failed`: Counts for "X/Y" display
- `has_requirements`: Whether current node has dependencies
- `requirements_status`: `pending`, `running`, `success`, `failed`

## Testing Results

### Manual Script Test
```bash
# Test with custom progress file
ssh -p 48263 root@174.88.163.72 \
  "bash /workspace/ComfyUI-Auto_installer/scripts/install-custom-nodes.sh \
   /workspace/ComfyUI \
   --venv-path /venv/main/bin/python \
   --progress-file /tmp/test_progress.json"

# Check progress at intervals
$ cat /tmp/test_progress.json
{
  "in_progress": false,
  "total_nodes": 34,
  "processed": 34,
  "current_node": "Installation complete",
  "current_status": "completed",
  "successful": 34,  # ✓ Counter working!
  "failed": 0,
  "has_requirements": false
}
```

### Integration Test
- ✅ Script accepts `--progress-file` parameter
- ✅ Writes JSON to specified path
- ✅ Counters persist correctly (no subshell issue)
- ✅ Backend can read progress via SSH
- ✅ Progress format matches workflow executor expectations

## Architecture Flow

```
┌─────────────────┐
│  Workflow UI    │
│  (Browser)      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Workflow Executor                  │
│  (workflow_executor.py)             │
│                                     │
│  1. POST /ssh/install-custom-nodes  │
│     → Returns task_id immediately   │
│                                     │
│  2. Poll every 2s:                  │
│     POST /ssh/install-custom-nodes/ │
│          progress?task_id=xxx       │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Backend (sync_api.py)              │
│                                     │
│  • Generate task_id                 │
│  • Start background worker          │
│  • Worker runs SSH install script   │
│  • Progress endpoint reads JSON     │
└────────┬────────────────────────────┘
         │ SSH
         ▼
┌─────────────────────────────────────┐
│  Cloud Instance                     │
│  (VastAI GPU Instance)              │
│                                     │
│  install-custom-nodes.sh executes   │
│  • Writes to:                       │
│    /tmp/custom_nodes_progress_      │
│    {task_id}.json                   │
│                                     │
│  JSON format:                       │
│  {                                  │
│    "in_progress": true,             │
│    "total_nodes": 34,               │
│    "processed": 5,                  │
│    "current_node": "NodeName",      │
│    "current_status": "running",     │
│    "successful": 4,                 │
│    "failed": 0                      │
│  }                                  │
└─────────────────────────────────────┘
```

## Expected Tasklist Display

With the fixes, the tasklist should now display:

```
Clone Auto-installer (✓ success)
Configure venv path (✓ success)
27 others (✓ success 27/27)
CustomNode-28 (✓ success)
CustomNode-29 (✓ success)
CustomNode-30 (✓ success)
CustomNode-31 (⟳ running)
3 others (⊙ pending 0/3)
```

The rolling window shows:
- Completed nodes rolled into "# others" at top
- Last 4 completed nodes
- Current node being installed
- Pending nodes rolled into "# others" at bottom

## Remaining Work

### 1. Backend stdout Parsing Redundancy

Currently, the backend has **two** progress tracking mechanisms:

1. **Script's JSON progress** (✅ Working) - Script writes complete progress
2. **Backend stdout parsing** (⚠️ Redundant) - Backend parses script output and writes its own progress

**Issue**: Both write to the same file, potentially causing conflicts or redundant updates.

**Recommendation**: Simplify backend to only read script's JSON progress, remove stdout parsing:

```python
# Instead of parsing stdout in background worker, just monitor script's JSON
for line in process.stdout:
    # Remove this parsing logic
    if 'Processing custom node:' in line:
        # Parse and write progress
        _write_progress_to_remote(...)  # Delete this
```

The script already provides complete, accurate progress data. The backend should trust it.

### 2. Error Handling

Need to handle edge cases:
- Script crashes before writing final progress
- JSON file becomes corrupted
- Network interruption during SSH read

**Suggestion**: Add validation and fallback:
```python
try:
    progress_data = json.loads(progress_json)
except json.JSONDecodeError:
    # Fallback: check if process is still alive
    if process.poll() is None:
        return {'in_progress': True, 'current_node': 'Processing...'}
    else:
        return {'in_progress': False, 'error': 'Installation failed'}
```

### 3. Testing

Create automated tests:
- Unit test for script JSON output format
- Integration test for full workflow
- Test with intentional failures (git clone fail, requirements fail)
- Test with network interruptions

## Files Modified

1. **scripts/install-custom-nodes.sh**
   - Added `--progress-file` parameter support
   - Fixed subshell variable persistence (process substitution)
   - Enhanced `write_json_progress()` function

2. **app/sync/sync_api.py**
   - Updated `_run_installation_background()` to pass progress file path
   - Modified install command to include `--progress-file` parameter

## Deployment

```bash
git add scripts/install-custom-nodes.sh app/sync/sync_api.py
git commit -m "Fix custom nodes progress tracking"
git push
./scripts/deploy.sh deploy --branch copilot/add-tasklist-tile-functionality --clean --build
```

## Next Steps

1. **Test full workflow** via WebUI with a fresh instance
2. **Monitor logs** for any progress reading issues
3. **Simplify backend** to remove redundant stdout parsing
4. **Add error handling** for edge cases
5. **Create automated tests** for regression prevention

## Success Criteria

- ✅ Script writes JSON progress to custom file path
- ✅ Variable counters persist correctly
- ✅ Backend reads progress from correct file
- ⏳ WebUI displays rolling tasklist (needs testing)
- ⏳ Progress updates within 2 seconds (needs testing)
- ⏳ Error states properly displayed (needs testing)

## Notes

The script now provides **complete, self-contained progress tracking**. The backend's role is simplified to:
1. Generate task_id
2. Start script with progress file path
3. Read progress JSON on demand
4. Forward to frontend

This is cleaner and more maintainable than having the backend parse stdout and duplicate progress logic.

---

**Debug Session Completed**: November 23, 2025  
**Status**: Core fixes implemented and verified. Ready for end-to-end WebUI testing.
