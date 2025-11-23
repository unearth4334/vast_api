# Custom Nodes Progress Tracking - Architecture Proposal

## Problem Statement

The Install Custom Nodes workflow displays only "Clone Auto-installer" in the tasklist, failing to show real-time progress of individual node installations. This occurs due to architectural issues in how the backend tracks and communicates installation progress to the frontend.

### Current Issues

1. **Synchronous Installation Blocking**: The `/ssh/install-custom-nodes` endpoint runs synchronously (blocking) using `subprocess.Popen` with `process.wait()`, preventing concurrent progress updates
2. **Progress File Timing**: Progress JSON is only written during stdout parsing loop, after subprocess starts but before any output
3. **Frontend Polling Mismatch**: Workflow executor expects asynchronous installation with real-time progress polling, but backend operates synchronously
4. **Thread Deadlock**: Workflow executor starts installation in background thread, then polls progress, but installation thread blocks waiting for completion

### Observed Behavior

```
Backend logs show: "Processing node 1/34: ComfyUI-Manager"
Frontend sees: Only "Clone Auto-installer" task visible
Progress endpoint returns: "No active installation" or stale "Initializing" state
```

## Root Cause Analysis

### Architecture Mismatch

**Frontend Expectation (workflow_executor.py:752-753)**
```python
# Expects: Start installation async, return immediately, poll progress
install_thread = threading.Thread(target=run_install, daemon=True)
install_thread.start()

# Then polls while thread runs
while install_thread.is_alive():
    progress = poll_progress()
```

**Backend Reality (sync_api.py:1430)**
```python
# Reality: Blocks until entire installation completes
return_code = process.wait(timeout=1800)  # 30 min timeout
```

### Progress Writing Flow

1. `subprocess.Popen` starts installation script
2. Backend writes **initial progress** immediately (recent fix)
3. Backend enters **blocking loop** reading stdout line-by-line
4. Progress updates written **inside** this loop as output parsed
5. Frontend polls progress endpoint **concurrently** via separate request
6. Progress endpoint reads `/tmp/custom_nodes_progress.json` via SSH
7. **Problem**: Installation blocks in thread, preventing timely progress updates

### File Locations

- **Script writes**: `/tmp/custom_nodes_install.log` (text log format)
- **Backend writes**: `/tmp/custom_nodes_progress.json` (JSON format)
- **Progress endpoint reads**: `/tmp/custom_nodes_progress.json`

## Proposed Solutions

### Option 1: True Asynchronous Installation (Recommended)

**Architecture**: Decouple installation execution from progress tracking using background workers.

#### Implementation Plan

1. **Create Background Task Manager**
   ```python
   # app/sync/background_tasks.py
   class BackgroundTaskManager:
       def __init__(self):
           self.tasks = {}  # task_id -> {'thread': Thread, 'status': dict}
           self.lock = threading.Lock()
       
       def start_task(self, task_id, target_func, *args):
           """Start background task, return immediately"""
           thread = threading.Thread(target=target_func, args=args, daemon=True)
           with self.lock:
               self.tasks[task_id] = {
                   'thread': thread,
                   'status': {'state': 'running', 'started_at': time.time()}
               }
           thread.start()
           return task_id
       
       def get_status(self, task_id):
           """Get current task status"""
           with self.lock:
               return self.tasks.get(task_id)
   ```

2. **Refactor Installation Endpoint**
   ```python
   @app.route('/ssh/install-custom-nodes', methods=['POST'])
   def ssh_install_custom_nodes():
       """Start installation asynchronously, return task ID immediately"""
       # Validate inputs
       ssh_connection = request.json.get('ssh_connection')
       ui_home = request.json.get('ui_home')
       
       # Generate unique task ID
       task_id = str(uuid.uuid4())
       
       # Start installation in background
       task_manager.start_task(
           task_id,
           _run_installation_background,
           task_id, ssh_connection, ui_home
       )
       
       # Return immediately with task ID
       return jsonify({
           'success': True,
           'task_id': task_id,
           'message': 'Installation started'
       })
   ```

3. **Background Installation Worker**
   ```python
   def _run_installation_background(task_id, ssh_connection, ui_home):
       """Runs in background thread, writes progress to remote"""
       ssh_host, ssh_port = _extract_host_port(ssh_connection)
       ssh_key = '/root/.ssh/id_ed25519'
       progress_file = f'/tmp/custom_nodes_progress_{task_id}.json'
       
       # Write initial progress
       write_progress_to_remote(ssh_host, ssh_port, ssh_key, progress_file, {
           'in_progress': True,
           'task_id': task_id,
           'current_node': 'Starting',
           'processed': 0
       })
       
       # Start subprocess
       process = subprocess.Popen([...])
       
       # Parse stdout and write progress
       for line in process.stdout:
           if 'Processing custom node:' in line:
               # Parse and write progress
               write_progress_to_remote(...)
       
       # Write completion
       write_progress_to_remote(ssh_host, ssh_port, ssh_key, progress_file, {
           'in_progress': False,
           'completed': True
       })
   ```

4. **Update Progress Endpoint**
   ```python
   @app.route('/ssh/install-custom-nodes/progress', methods=['POST'])
   def ssh_install_custom_nodes_progress():
       """Read progress file by task_id"""
       task_id = request.json.get('task_id')
       ssh_connection = request.json.get('ssh_connection')
       
       ssh_host, ssh_port = _extract_host_port(ssh_connection)
       progress_file = f'/tmp/custom_nodes_progress_{task_id}.json'
       
       # Read progress via SSH subprocess
       result = subprocess.run([
           'ssh', '-i', ssh_key, '-p', str(ssh_port),
           ssh_connection,
           f"cat {progress_file} 2>/dev/null || echo '{{}}'"
       ], capture_output=True, text=True)
       
       return jsonify(json.loads(result.stdout))
   ```

5. **Update Workflow Executor**
   ```python
   # workflow_executor.py
   def _execute_install_custom_nodes(self, ssh_connection, ui_home, ...):
       # Start installation (returns immediately with task_id)
       response = requests.post(
           f"{API_BASE_URL}/ssh/install-custom-nodes",
           json={'ssh_connection': ssh_connection, 'ui_home': ui_home}
       )
       task_id = response.json()['task_id']
       
       # Poll progress using task_id
       while True:
           progress = requests.post(
               f"{API_BASE_URL}/ssh/install-custom-nodes/progress",
               json={'ssh_connection': ssh_connection, 'task_id': task_id}
           ).json()
           
           if not progress.get('in_progress'):
               break
           
           # Update tasklist from progress
           self._update_tasklist_from_progress(progress, ...)
           time.sleep(2)
   ```

#### Advantages
- ✅ Clean separation of concerns
- ✅ Non-blocking installation endpoint
- ✅ Real-time progress updates
- ✅ Scalable to multiple concurrent installations
- ✅ Proper error handling and timeout management

#### Disadvantages
- ⚠️ Requires significant refactoring (~200-300 lines changed)
- ⚠️ Need background task cleanup mechanism
- ⚠️ More complex state management

#### Estimated Effort
- **Implementation**: 4-6 hours
- **Testing**: 2-3 hours
- **Total**: 6-9 hours

---

### Option 2: Dual-Thread Progress Writer (Intermediate)

**Architecture**: Keep synchronous installation, add separate thread that periodically reads script log and writes JSON progress.

#### Implementation Plan

1. **Progress Monitor Thread**
   ```python
   def _monitor_installation_progress(ssh_host, ssh_port, ssh_key, stop_event):
       """Runs in separate thread, monitors log file, writes JSON progress"""
       progress_file = '/tmp/custom_nodes_progress.json'
       log_file = '/tmp/custom_nodes_install.log'
       
       while not stop_event.is_set():
           # Read script's log file via SSH
           result = subprocess.run([
               'ssh', '-i', ssh_key, '-p', str(ssh_port),
               f'root@{ssh_host}',
               f'tail -n 50 {log_file} 2>/dev/null'
           ], capture_output=True, text=True)
           
           # Parse log for progress
           progress = _parse_log_for_progress(result.stdout)
           
           # Write JSON progress
           if progress:
               write_progress_to_remote(ssh_host, ssh_port, ssh_key, 
                                      progress_file, progress)
           
           time.sleep(1)  # Poll every second
   ```

2. **Update Installation Endpoint**
   ```python
   @app.route('/ssh/install-custom-nodes', methods=['POST'])
   def ssh_install_custom_nodes():
       # Start progress monitor thread
       stop_event = threading.Event()
       monitor_thread = threading.Thread(
           target=_monitor_installation_progress,
           args=(ssh_host, ssh_port, ssh_key, stop_event),
           daemon=True
       )
       monitor_thread.start()
       
       try:
           # Run installation (blocking)
           process = subprocess.Popen([...])
           return_code = process.wait(timeout=1800)
       finally:
           # Stop monitor thread
           stop_event.set()
           monitor_thread.join(timeout=5)
   ```

#### Advantages
- ✅ Minimal refactoring required
- ✅ Leverages existing script log output
- ✅ Progress updates independent of main thread

#### Disadvantages
- ⚠️ Still blocks main request thread
- ⚠️ Additional SSH overhead for log polling
- ⚠️ Log parsing fragility
- ⚠️ Thread synchronization complexity

#### Estimated Effort
- **Implementation**: 2-3 hours
- **Testing**: 1-2 hours
- **Total**: 3-5 hours

---

### Option 3: Script-Native JSON Progress (Simple)

**Architecture**: Modify installation script to write JSON progress directly, backend just proxies it.

#### Implementation Plan

1. **Update Installation Script**
   ```bash
   # scripts/install-custom-nodes.sh
   
   # Add JSON progress writer
   write_json_progress() {
       local total="$1"
       local processed="$2"
       local current_node="$3"
       local status="$4"
       
       cat > /tmp/custom_nodes_progress.json <<EOF
   {
     "in_progress": true,
     "total_nodes": $total,
     "processed": $processed,
     "current_node": "$current_node",
     "current_status": "$status",
     "timestamp": "$(date -Iseconds)"
   }
   EOF
   }
   
   # In node processing loop
   while IFS=',' read -r name repo_url ...; do
       ((CURRENT_NODE++))
       write_json_progress "$TOTAL_NODES" "$CURRENT_NODE" "$name" "running"
       
       # Install node...
       
       write_json_progress "$TOTAL_NODES" "$CURRENT_NODE" "$name" "success"
   done
   ```

2. **Simplify Backend**
   ```python
   @app.route('/ssh/install-custom-nodes', methods=['POST'])
   def ssh_install_custom_nodes():
       """Just start script, no progress parsing needed"""
       # Clear existing progress
       subprocess.run(['ssh', ..., 'rm -f /tmp/custom_nodes_progress.json'])
       
       # Run installation script (it writes progress)
       process = subprocess.Popen([
           'ssh', ...,
           './install-custom-nodes.sh ...'
       ])
       
       # Wait for completion
       return_code = process.wait(timeout=1800)
       
       return jsonify({'success': return_code == 0})
   ```

3. **Progress Endpoint Unchanged**
   - Already reads `/tmp/custom_nodes_progress.json`
   - No changes needed

#### Advantages
- ✅ Minimal backend changes
- ✅ Script has full control over progress
- ✅ Single source of truth for progress data
- ✅ Easy to test script independently

#### Disadvantages
- ⚠️ Still synchronous/blocking
- ⚠️ Progress updates limited by script execution speed
- ⚠️ JSON generation in bash (error-prone)

#### Estimated Effort
- **Implementation**: 1-2 hours
- **Testing**: 1 hour
- **Total**: 2-3 hours

---

## Recommended Approach

### Phased Implementation Strategy

#### Phase 1: Quick Win (Option 3)
**Timeline**: Immediate (2-3 hours)

Implement script-native JSON progress to get basic functionality working:
- Modify `install-custom-nodes.sh` to write JSON progress
- Test with current infrastructure
- Provides immediate value with minimal risk

#### Phase 2: Full Solution (Option 1)
**Timeline**: Sprint +1 (6-9 hours)

Implement true asynchronous architecture:
- Develop background task manager
- Refactor installation endpoint
- Update workflow executor
- Comprehensive testing

### Hybrid Approach (Recommended)

Combine Option 1 with existing progress parsing for robustness:

```python
def _run_installation_background(task_id, ssh_connection, ui_home):
    """Background worker with dual progress tracking"""
    
    # Start subprocess
    process = subprocess.Popen([...])
    
    # Parse stdout for detailed progress
    for line in process.stdout:
        progress = _parse_line_for_progress(line)
        if progress:
            # Write to remote immediately
            write_progress_to_remote(ssh_host, ssh_port, ssh_key, 
                                   progress_file, progress)
    
    # Also monitor script's native JSON (fallback)
    # If stdout parsing fails, script JSON provides backup
```

## Implementation Checklist

### Phase 1: Script-Native Progress (Week 1)
- [ ] Add JSON progress writer to `install-custom-nodes.sh`
- [ ] Test JSON format validity
- [ ] Verify progress endpoint reads correctly
- [ ] Test with workflow executor
- [ ] Handle edge cases (script failures, incomplete JSON)

### Phase 2: Async Architecture (Week 2)
- [ ] Create `background_tasks.py` module
- [ ] Implement `BackgroundTaskManager` class
- [ ] Refactor `/ssh/install-custom-nodes` endpoint
- [ ] Add `_run_installation_background` worker function
- [ ] Update progress endpoint with task_id support
- [ ] Modify workflow executor to handle async pattern
- [ ] Add task cleanup mechanism
- [ ] Implement timeout and error handling

### Phase 3: Testing & Validation (Week 3)
- [ ] Unit tests for BackgroundTaskManager
- [ ] Integration tests for async installation flow
- [ ] Test progress polling with varying network delays
- [ ] Test concurrent installations (multiple instances)
- [ ] Test error scenarios (script failure, SSH disconnect, timeout)
- [ ] Performance testing (30+ nodes installation)
- [ ] Frontend tasklist display verification

### Phase 4: Monitoring & Cleanup (Week 4)
- [ ] Add logging for task lifecycle
- [ ] Implement stale task cleanup (24-hour TTL)
- [ ] Add metrics collection (install duration, success rate)
- [ ] Document API changes
- [ ] Update user documentation

## Testing Strategy

### Unit Tests
```python
# test/test_background_tasks.py
def test_task_manager_start():
    manager = BackgroundTaskManager()
    task_id = manager.start_task('test', lambda: time.sleep(1))
    assert task_id in manager.tasks
    assert manager.get_status(task_id)['status']['state'] == 'running'

def test_progress_file_parsing():
    progress = _parse_progress_json('{"in_progress": true, ...}')
    assert progress['in_progress'] == True
```

### Integration Tests
```python
# test/test_install_custom_nodes_async.py
def test_async_installation_flow():
    # Start installation
    response = client.post('/ssh/install-custom-nodes', json={...})
    task_id = response.json['task_id']
    
    # Poll progress
    for _ in range(30):
        progress = client.post('/ssh/install-custom-nodes/progress', 
                             json={'task_id': task_id})
        if not progress.json.get('in_progress'):
            break
        time.sleep(1)
    
    assert progress.json.get('completed') == True
```

### Manual Testing
1. Start installation via workflow UI
2. Verify tasklist shows "Clone Auto-installer" immediately
3. Confirm individual nodes appear as processed
4. Check rolling window (4 visible nodes)
5. Verify "# others" placeholders
6. Test with node failures
7. Verify "Verify Dependencies" appears at end

## Rollback Plan

If issues arise during deployment:

1. **Phase 1 Rollback**: Revert script changes, progress endpoint reads empty
2. **Phase 2 Rollback**: Feature flag to switch between sync/async modes
   ```python
   ASYNC_INSTALLATION_ENABLED = os.getenv('ASYNC_INSTALL', 'false') == 'true'
   
   if ASYNC_INSTALLATION_ENABLED:
       return _install_async(...)
   else:
       return _install_sync(...)
   ```

## Success Criteria

### Functional Requirements
- ✅ Tasklist shows "Clone Auto-installer" immediately when step starts
- ✅ Individual node names appear in tasklist as they install
- ✅ Maximum 4 nodes visible at once
- ✅ "# others (X/Y)" placeholders for processed and pending nodes
- ✅ Sub-tasks visible for nodes with requirements
- ✅ "Verify Dependencies" task appears at completion
- ✅ Progress updates within 2 seconds of actual installation progress

### Non-Functional Requirements
- ✅ Installation endpoint responds within 1 second (async mode)
- ✅ Progress polling overhead < 5% of CPU
- ✅ Supports concurrent installations (2+ instances)
- ✅ Graceful handling of SSH disconnects
- ✅ Clean task cleanup (no orphaned processes)

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Background task orphaning | Medium | Low | Implement cleanup job, task TTL |
| Race condition in progress writes | High | Medium | Use file locking or atomic writes |
| SSH connection pool exhaustion | High | Low | Reuse connections, connection pooling |
| Script JSON corruption | Medium | Medium | Validate JSON before write, fallback to log parsing |
| Frontend polling timeout | Low | Low | Configurable polling interval, exponential backoff |

## Future Enhancements

1. **WebSocket Progress Streaming**: Replace polling with real-time push updates
2. **Progress History**: Store installation history in database
3. **Retry Mechanism**: Auto-retry failed node installations
4. **Parallel Node Installation**: Install independent nodes concurrently
5. **Progress Persistence**: Survive backend restarts

## References

- Current Implementation: `app/sync/sync_api.py` (lines 1200-1475)
- Workflow Executor: `app/sync/workflow_executor.py` (lines 690-850)
- Installation Script: `scripts/install-custom-nodes.sh`
- Progress Endpoint: `app/sync/sync_api.py` (lines 1477-1562)

## Approval & Sign-off

**Proposed By**: Development Team  
**Date**: November 22, 2025  
**Status**: Pending Review

**Recommended Option**: Phased implementation starting with Option 3 (Quick Win), followed by Option 1 (Async Architecture)

---

*This proposal outlines a comprehensive path to resolve the custom nodes progress tracking issue while maintaining system stability and providing incremental value delivery.*
