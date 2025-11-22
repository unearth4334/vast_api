
## **Comprehensive Implementation Plan: Headless Server-Side Workflow Execution**

### **Executive Summary**

This plan restructures the cloud-instance-setup workflow system to use a **server-side execution model** where:
1. **All workflows execute server-side**: Background threads handle all workflow execution independent of browser state
2. **Persistent state tracking**: JSON-based state file maintains real-time progress for all steps
3. **WebUI as visualization client**: Browser renders progress by reading state, not by executing steps
4. **Interruption-proof UX**: Page refreshes, closes, or new sessions seamlessly reconnect to running workflows

---

## **Architecture Overview**

### **Core Components**

```
┌─────────────────────────────────────────────────────────────┐
│                    WebUI Layer (Client)                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐   │
│  │ workflow.js│  │  main.js   │  │ progress-          │   │
│  │            │  │            │  │ indicators.js      │   │
│  │ • Start    │  │ • Init     │  │ • Visualize        │   │
│  │ • Stop     │  │ • Poll     │  │ • Restore          │   │
│  │ • Visualize│  │ • Restore  │  │ • Update           │   │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────────────┘   │
│        │               │               │                    │
│        └───────────────┴───────────────┘                    │
│                        │                                     │
│           API Calls (REST/JSON - Read State)                │
│                  + Control Commands                          │
└────────────────────────┼────────────────────────────────────┘
                         │
┌────────────────────────┼────────────────────────────────────┐
│                   Backend API Layer                          │
│  ┌────────────────────┴─────────────────────────┐          │
│  │         sync_api.py (Flask Routes)           │          │
│  │  ┌────────────────────────────────────────┐  │          │
│  │  │ • POST /workflow/start                 │  │  Control │
│  │  │ • POST /workflow/stop                  │  │  Workflow│
│  │  │ • GET  /workflow/state                 │  │  State   │
│  │  │ • GET  /workflow/state/summary         │  │  Queries │
│  │  │ • DELETE /workflow/state               │  │  Only    │
│  │  └────────────────────────────────────────┘  │          │
│  └────────────────┬───────────────┬─────────────┘          │
│                   │               │                          │
└───────────────────┼───────────────┼──────────────────────────┘
                    │               │
┌───────────────────┼───────────────┼──────────────────────────┐
│             Workflow Execution Layer (Server)                │
│  ┌────────────────┴──────┐  ┌────┴──────────────────┐      │
│  │  workflow_executor.py │  │ workflow_state.py     │      │
│  │  ┌──────────────────┐ │  │ ┌───────────────────┐ │      │
│  │  │ WorkflowExecutor │ │  │ │WorkflowStateManager│ │      │
│  │  │                  │ │  │ │                   │ │      │
│  │  │ • start_workflow │ │  │ │ • save_state      │ │      │
│  │  │ • stop_workflow  │ │  │ │ • load_state      │ │      │
│  │  │ • _execute_step  │ │  │ │ • clear_state     │ │      │
│  │  │ • _execute_*     │ │  │ │ • get_summary     │ │      │
│  │  │ • progress_cb    │ │  │ │ • atomic_update   │ │      │
│  │  │ • Background     │ │  │ │                   │ │      │
│  │  │   Thread         │ │  │ │                   │ │      │
│  │  └──────────────────┘ │  │ └───────────────────┘ │      │
│  └───────────────────────┘  └───────┬───────────────┘      │
│                                      │                       │
│                   All step execution happens here            │
│                   (SSH commands, API calls, etc.)            │
└──────────────────────────────────────┼───────────────────────┘
                                       │
                    ┌──────────────────┴────────────────┐
                    │  /tmp/workflow_state.json         │
                    │  ┌─────────────────────────────┐  │
                    │  │ {                           │  │
                    │  │   "workflow_id": "...",     │  │
                    │  │   "status": "running",      │  │
                    │  │   "current_step": 2,        │  │
                    │  │   "steps": [...],           │  │
                    │  │   "ssh_connection": "..."   │  │
                    │  │ }                           │  │
                    │  └─────────────────────────────┘  │
                    └───────────────────────────────────┘

Key Architecture Principles:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Server executes ALL workflow steps
2. WebUI NEVER executes workflow logic
3. WebUI only: starts, stops, and visualizes
4. State file is source of truth
5. Multiple browser sessions can view same workflow
```

---

## **Implementation Phases**

### **Phase 1: Backend Foundation** ✓ (Exists in branch)

**Status**: Already implemented in `copilot/add-server-side-workflow-status`

**Components**:
- `app/sync/workflow_state.py` - State persistence manager
- `app/sync/workflow_executor.py` - Background thread executor
- API endpoints in `sync_api.py`

**What needs enhancement**:
1. ✅ Thread safety (already has locks)
2. ✅ Error handling and recovery
3. ⚠️ **Critical**: Replace stub `_execute_step()` with real SSH endpoint calls
4. ⚠️ **Critical**: Add progress callbacks for long-running steps
5. ➕ **New**: Remove any client-side step execution logic from WebUI
6. ➕ **New**: Ensure WorkflowExecutor handles ALL step execution server-side

---

### **Phase 2: Enhanced State Management**

**Objectives**:
- Extend state schema to support granular progress
- Add sub-step progress for long operations
- Implement state versioning for backwards compatibility

**New State Schema**:
```json
{
  "schema_version": "1.0",
  "workflow_id": "workflow_1732189234_abc123",
  "status": "running",  // running | completed | failed | cancelled | paused
  "current_step": 2,
  "total_steps": 8,
  "steps": [
    {
      "index": 0,
      "action": "test_ssh",
      "label": "🔧 Test SSH Connection",
      "status": "completed",  // pending | in_progress | completed | failed | skipped
      "start_time": "2025-11-21T10:30:00Z",
      "end_time": "2025-11-21T10:30:02Z",
      "duration_ms": 2341,
      "result": {
        "success": true,
        "message": "SSH connection verified",
        "details": {
          "hostname": "6ecc5da8c823",
          "uptime": "6 days"
        }
      },
      "progress": {
        "type": "simple",  // simple | multi_phase | checklist | percentage
        "percent": 100,
        "message": "Connection established"
      }
    },
    {
      "index": 1,
      "action": "install_custom_nodes",
      "label": "📦 Install Custom Nodes",
      "status": "in_progress",
      "start_time": "2025-11-21T10:35:00Z",
      "progress": {
        "type": "checklist",
        "percent": 45,
        "message": "Installing nodes...",
        "items": [
          {"label": "Fetching repository list", "state": "completed"},
          {"label": "Installing ComfyUI-Manager", "state": "completed"},
          {"label": "Installing rgthree-comfy", "state": "active"},
          {"label": "Installing ComfyUI_essentials", "state": "pending"}
        ]
      }
    }
  ],
  "ssh_connection": "ssh -p 2838 root@104.189.178.116",
  "template_id": "b3a852d995cac99809607b2f52a2fe36",
  "start_time": "2025-11-21T10:30:00Z",
  "last_update": "2025-11-21T10:35:15Z",
  "metadata": {
    "user_agent": "Mozilla/5.0...",
    "initiated_from": "webui"
  }
}
```

**Implementation Tasks**:
1. Update `WorkflowStateManager.save_state()` to handle nested progress
2. Add `update_step_progress()` method for real-time updates
3. Add state migration for schema version changes
4. Add state validation to prevent corruption

---

### **Phase 3: Workflow Executor Enhancement**

**Current Limitation**: `workflow_executor.py` has stub implementation for `_execute_step()`

**Enhancement Required**:

```python
# app/sync/workflow_executor.py

def _execute_step(self, step: Dict, ssh_connection: str, 
                  state_manager: WorkflowStateManager, 
                  workflow_id: str, step_index: int) -> bool:
    """
    Execute a workflow step with progress tracking.
    """
    action = step['action']
    
    # Map actions to actual API functions
    step_executors = {
        'test_ssh': self._execute_test_ssh,
        'setup_civitdl': self._execute_setup_civitdl,
        'test_civitdl': self._execute_test_civitdl,
        'install_custom_nodes': self._execute_install_custom_nodes,
        'setup_python_venv': self._execute_setup_python_venv,
        'set_ui_home': self._execute_set_ui_home,
        'get_ui_home': self._execute_get_ui_home,
        'verify_dependencies': self._execute_verify_dependencies,
        'sync_instance': self._execute_sync_instance,
        'reboot_instance': self._execute_reboot_instance,
    }
    
    executor_fn = step_executors.get(action)
    if not executor_fn:
        logger.error(f"No executor for action: {action}")
        return False
    
    try:
        # Execute with progress callbacks
        return executor_fn(
            ssh_connection=ssh_connection,
            progress_callback=lambda progress: self._update_step_progress(
                state_manager, workflow_id, step_index, progress
            )
        )
    except Exception as e:
        logger.error(f"Step execution failed: {action} - {e}")
        return False

def _update_step_progress(self, state_manager, workflow_id, step_index, progress):
    """Update step progress in state file."""
    state = state_manager.load_state()
    if state and state['workflow_id'] == workflow_id:
        state['steps'][step_index]['progress'] = progress
        state_manager.save_state(state)
```

**New Step Executors** (example for complex step):
```python
def _execute_install_custom_nodes(self, ssh_connection: str, 
                                   progress_callback: Callable) -> bool:
    """Execute custom nodes installation with progress tracking."""
    
    # Phase 1: Fetch repository list
    progress_callback({
        'type': 'checklist',
        'percent': 10,
        'items': [
            {'label': 'Fetching repository list', 'state': 'active'},
            {'label': 'Installing nodes', 'state': 'pending'},
            {'label': 'Verifying installation', 'state': 'pending'}
        ]
    })
    
    # Call actual SSH endpoint
    response = requests.post('http://localhost:5000/ssh/install-custom-nodes', 
                            json={'ssh_connection': ssh_connection})
    
    if not response.ok:
        return False
    
    data = response.json()
    
    # Phase 2: Installing nodes (with streaming if available)
    progress_callback({
        'type': 'checklist',
        'percent': 50,
        'items': [
            {'label': 'Fetching repository list', 'state': 'completed'},
            {'label': 'Installing nodes', 'state': 'active'},
            {'label': 'Verifying installation', 'state': 'pending'}
        ]
    })
    
    # Wait for completion (or poll progress endpoint)
    # ...
    
    return data.get('success', False)
```

---

### **Phase 4: WebUI Refactoring - Visualization Client**

**Objective**: Transform WebUI from step executor to visualization client

**Key Changes**:

1. **Remove client-side execution logic**:
   - Current: `executeWorkflowStep()` calls step functions directly
   - New: Button clicks only send start/stop commands to server
   
2. **Implement state polling and restoration**:
   - Poll `/workflow/state` every 2 seconds when workflow active
   - Restore visualization on page load if workflow running
   - Update progress indicators based on server state

3. **Simplify workflow controls**:
   - "Run Workflow" → POST to `/workflow/start` with step list
   - "Stop Workflow" → POST to `/workflow/stop`
   - No mode selection needed (always server-side)

**Implementation in `workflow.js`**:

```javascript
/**
 * Initialize workflow system and check for active workflows
 */
async function initWorkflow() {
  console.log('🔄 Initializing workflow system...');
  
  // Load workflow configuration
  try {
    const response = await fetch('/config/workflow');
    if (response.ok) {
      const config = await response.json();
      if (config.workflow_step_delay) {
        workflowConfig.stepDelay = config.workflow_step_delay * 1000;
      }
    }
  } catch (error) {
    console.warn('⚠️ Could not load workflow config:', error);
  }
  
  // Check for active workflow and restore state
  await restoreWorkflowState();
  
  // Set up continuous polling for workflow updates
  setInterval(async () => {
    const state = await checkWorkflowState();
    if (state && state.status === 'running') {
      updateWorkflowVisualization(state);
    }
  }, 2000); // Poll every 2 seconds
}

/**
 * Start workflow execution on server
 * This is the ONLY way to start a workflow - always server-side
 */
async function runWorkflow() {
  if (workflowRunning) {
    // Stop the running workflow
    await stopWorkflow();
    return;
  }
  
  console.log('🚀 Starting server-side workflow execution...');
  
  // Validate prerequisites
  const sshConnection = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnection) {
    showSetupResult('Please enter an SSH connection string first.', 'error');
    return;
  }
  
  // Get enabled steps
  const steps = getEnabledSteps();
  if (steps.length === 0) {
    showSetupResult('No steps are enabled. Please enable at least one step.', 'error');
    return;
  }
  
  // Generate workflow ID
  const workflowId = `workflow_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  const templateId = document.getElementById('templateSelector')?.value;
  
  try {
    // Send workflow to server for execution
    const response = await fetch('/workflow/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workflow_id: workflowId,
        steps: steps,
        ssh_connection: sshConnection,
        template_id: templateId,
        step_delay: workflowConfig.stepDelay / 1000
      })
    });
    
    const data = await response.json();
    
    if (!data.success) {
      showSetupResult(`❌ Failed to start workflow: ${data.message}`, 'error');
      return;
    }
    
    // Update UI to reflect running state
    workflowRunning = true;
    const runButton = document.getElementById('run-workflow-btn');
    runButton.textContent = '⏸️ Stop Workflow';
    runButton.classList.add('cancel');
    
    // Disable step toggles during execution
    disableStepToggles();
    
    showSetupResult(
      `✅ Workflow started on server (ID: ${workflowId}).\n` +
      `The workflow will continue running even if you close this page.`,
      'success'
    );
    
    // Start visualization polling
    startPollingWorkflowState();
    
  } catch (error) {
    console.error('❌ Failed to start workflow:', error);
    showSetupResult(`❌ Error: ${error.message}`, 'error');
  }
}

/**
 * Stop a running workflow on the server
 */
async function stopWorkflow() {
  try {
    const response = await fetch('/workflow/stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    const data = await response.json();
    
    if (data.success) {
      workflowRunning = false;
      showSetupResult('⏸️ Workflow stopped', 'info');
      resetWorkflowUI();
    } else {
      showSetupResult(`❌ Failed to stop workflow: ${data.message}`, 'error');
    }
  } catch (error) {
    console.error('❌ Failed to stop workflow:', error);
    showSetupResult(`❌ Error: ${error.message}`, 'error');
  }
}

/**
 * Check current workflow state from server
 */
async function checkWorkflowState() {
  try {
    const response = await fetch('/workflow/state');
    if (!response.ok) return null;
    
    const data = await response.json();
    return data.success && data.state ? data.state : null;
  } catch (error) {
    console.error('❌ Failed to check workflow state:', error);
    return null;
  }
}

/**
 * Restore workflow state on page load
 * Called during initialization to reconnect to any running workflow
 */
async function restoreWorkflowState() {
  try {
    const response = await fetch('/workflow/state');
    if (!response.ok) return;
    
    const data = await response.json();
    
    if (!data.success || !data.active || !data.state) return;
    
    const state = data.state;
    console.log('📥 Restoring workflow state:', state.workflow_id);
    
    // Switch to vastai-setup tab
    showTab('vastai-setup');
    
    // Restore SSH connection string
    const sshInput = document.getElementById('sshConnectionString');
    if (sshInput && state.ssh_connection) {
      sshInput.value = state.ssh_connection;
    }
    
    // Update UI to reflect running state
    workflowRunning = true;
    const runButton = document.getElementById('run-workflow-btn');
    if (runButton) {
      runButton.textContent = '⏸️ Stop Workflow';
      runButton.classList.add('cancel');
    }
    
    // Disable step toggles
    disableStepToggles();
    
    // Restore all step visualizations
    updateWorkflowVisualization(state);
    
    // Show restoration message
    showSetupResult(
      `⚠️ Workflow Reconnected\n` +
      `Step ${state.current_step + 1}/${state.total_steps} currently running.\n` +
      `You can close this page - the workflow will continue on the server.`,
      'info'
    );
    
    // Start polling for updates
    startPollingWorkflowState();
    
  } catch (error) {
    console.error('❌ Failed to restore workflow state:', error);
  }
}

/**
 * Update workflow visualization based on server state
 * This is the core function that renders all progress indicators
 */
function updateWorkflowVisualization(state) {
  if (!state || !state.steps) return;
  
  const steps = state.steps;
  
  steps.forEach((step, index) => {
    const stepElement = document.querySelector(
      `.workflow-step[data-action="${step.action}"]`
    );
    
    if (!stepElement) return;
    
    // Clear previous state classes
    stepElement.classList.remove('in-progress', 'completed', 'failed');
    
    // Apply current state
    if (step.status === 'completed') {
      stepElement.classList.add('completed');
      renderCompletionIndicator(stepElement, step);
      updateStepArrow(stepElement, 'completed');
      
    } else if (step.status === 'in_progress') {
      stepElement.classList.add('in-progress');
      renderProgressIndicator(stepElement, step);
      updateStepArrow(stepElement, 'loading', step.progress?.percent || 0);
      
    } else if (step.status === 'failed') {
      stepElement.classList.add('failed');
      renderErrorIndicator(stepElement, step);
      
    } else {
      // pending state - clear any indicators
      clearStepIndicators(stepElement);
    }
  });
  
  // Update overall progress
  updateOverallProgress(state);
}

/**
 * Render progress indicator based on step's progress data
 */
function renderProgressIndicator(stepElement, step) {
  if (!step.progress || !window.progressIndicators) return;
  
  switch (step.progress.type) {
    case 'simple':
      window.progressIndicators.showSimpleProgress(
        stepElement,
        step.progress.message || 'Processing...',
        step.progress.detail || ''
      );
      break;
      
    case 'checklist':
      window.progressIndicators.showChecklistProgress(
        stepElement,
        step.progress.items || []
      );
      break;
      
    case 'multi_phase':
      window.progressIndicators.showMultiPhaseProgress(
        stepElement,
        step.progress.phases || [],
        step.progress.active_phase || 0,
        step.progress.percent || 0
      );
      break;
      
    case 'percentage':
      window.progressIndicators.showPercentageProgress(
        stepElement,
        step.progress.percent || 0,
        step.progress.message || ''
      );
      break;
  }
}

/**
 * Render completion indicator for finished steps
 */
function renderCompletionIndicator(stepElement, step) {
  if (!step.result || !window.progressIndicators) return;
  
  if (step.result.success) {
    window.progressIndicators.showSuccess(
      stepElement,
      step.result.message || 'Step completed',
      formatDetails(step.result.details),
      [`⏱️ ${formatDuration(step.duration_ms)}`]
    );
  } else {
    window.progressIndicators.showError(
      stepElement,
      step.result.message || 'Step failed',
      step.result.error || ''
    );
  }
}

/**
 * Render error indicator for failed steps
 */
function renderErrorIndicator(stepElement, step) {
  if (!window.progressIndicators) return;
  
  window.progressIndicators.showError(
    stepElement,
    step.result?.message || 'Step failed',
    step.result?.error || 'Unknown error',
    [
      { class: 'retry-btn', onclick: 'retryFromStep()', label: '🔄 Retry Workflow' }
    ]
  );
}

/**
 * Update arrow between steps based on state
 */
function updateStepArrow(stepElement, state, progress = 1.0) {
  const nextArrow = stepElement.nextElementSibling;
  if (!nextArrow || !nextArrow.classList.contains('workflow-arrow')) return;
  
  nextArrow.classList.remove('loading', 'completed');
  
  if (state === 'completed') {
    nextArrow.classList.add('completed');
    updateArrowProgress(nextArrow, 1.0);
  } else if (state === 'loading') {
    nextArrow.classList.add('loading');
    updateArrowProgress(nextArrow, progress / 100);
  }
}

/**
 * Start polling for workflow state updates
 */
function startPollingWorkflowState() {
  // Polling is already set up in initWorkflow()
  // This function exists for explicit control if needed
  console.log('📡 Polling workflow state...');
}

/**
 * Helper: Get enabled workflow steps
 */
function getEnabledSteps() {
  const container = document.getElementById('workflow-steps');
  const stepElements = container.querySelectorAll('.workflow-step:not(.disabled)');
  
  return Array.from(stepElements).map((el, index) => ({
    index: index,
    action: el.dataset.action,
    label: el.querySelector('.step-button')?.textContent.trim() || el.dataset.action,
    status: 'pending'
  }));
}

/**
 * Helper: Disable step toggles during execution
 */
function disableStepToggles() {
  const toggles = document.querySelectorAll('.step-toggle');
  toggles.forEach(toggle => {
    toggle.disabled = true;
    toggle.style.opacity = '0.5';
  });
}

/**
 * Helper: Enable step toggles after execution
 */
function enableStepToggles() {
  const toggles = document.querySelectorAll('.step-toggle');
  toggles.forEach(toggle => {
    toggle.disabled = false;
    toggle.style.opacity = '';
  });
}

/**
 * Helper: Reset workflow UI after completion
 */
function resetWorkflowUI() {
  workflowRunning = false;
  
  const runButton = document.getElementById('run-workflow-btn');
  if (runButton) {
    runButton.textContent = '▶️ Run Workflow';
    runButton.classList.remove('cancel');
  }
  
  enableStepToggles();
}

/**
 * Helper: Format duration in milliseconds
 */
function formatDuration(ms) {
  if (!ms) return '0s';
  if (ms < 1000) return `${ms}ms`;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

/**
 * Helper: Format result details
 */
function formatDetails(details) {
  if (!details) return '';
  if (typeof details === 'string') return details;
  return Object.entries(details)
    .map(([key, value]) => `${key}: ${value}`)
    .join(' • ');
}

/**
 * Helper: Clear step indicators
 */
function clearStepIndicators(stepElement) {
  if (window.progressIndicators) {
    window.progressIndicators.clearIndicators(stepElement);
  }
}

/**
 * Helper: Update overall progress display
 */
function updateOverallProgress(state) {
  const completed = state.steps.filter(s => s.status === 'completed').length;
  const total = state.steps.length;
  const percent = Math.round((completed / total) * 100);
  
  // Update progress display if exists
  const progressDisplay = document.getElementById('workflow-overall-progress');
  if (progressDisplay) {
    progressDisplay.textContent = `${completed}/${total} steps (${percent}%)`;
  }
}
```

---

### **Phase 5: API Endpoint Updates**

**Objective**: Ensure API endpoints support server-side execution model

**Required API Endpoints**:

```python
# app/sync/sync_api.py

@app.route('/workflow/start', methods=['POST', 'OPTIONS'])
def start_workflow():
    """
    Start a new workflow execution on the server.
    The workflow runs in a background thread.
    """
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json(force=True, silent=True)
        
        # Validate required fields
        workflow_id = data.get('workflow_id')
        steps = data.get('steps', [])
        ssh_connection = data.get('ssh_connection')
        step_delay = data.get('step_delay', 5)
        
        if not all([workflow_id, steps, ssh_connection]):
            return jsonify({
                'success': False,
                'message': 'workflow_id, steps, and ssh_connection are required'
            }), 400
        
        # Start workflow in background
        executor = get_workflow_executor()
        success = executor.start_workflow(
            workflow_id=workflow_id,
            steps=steps,
            ssh_connection=ssh_connection,
            step_delay=step_delay
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Workflow started on server',
                'workflow_id': workflow_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to start workflow - may already be running'
            }), 409
            
    except Exception as e:
        logger.error(f"Error starting workflow: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/workflow/stop', methods=['POST', 'OPTIONS'])
def stop_workflow():
    """Stop the currently running workflow."""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        state_manager = get_workflow_state_manager()
        state = state_manager.load_state()
        
        if not state:
            return jsonify({
                'success': False,
                'message': 'No active workflow'
            }), 404
        
        workflow_id = state.get('workflow_id')
        executor = get_workflow_executor()
        success = executor.stop_workflow(workflow_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Workflow stopped'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to stop workflow'
            }), 500
            
    except Exception as e:
        logger.error(f"Error stopping workflow: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/workflow/state', methods=['GET', 'OPTIONS'])
def get_workflow_state():
    """
    Get current workflow state.
    This endpoint is polled by the WebUI for visualization.
    """
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        state_manager = get_workflow_state_manager()
        state = state_manager.load_state()
        
        if state is None:
            return jsonify({
                'success': True,
                'active': False,
                'state': None
            })
        
        return jsonify({
            'success': True,
            'active': state.get('status') == 'running',
            'state': state
        })
        
    except Exception as e:
        logger.error(f"Error getting workflow state: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'active': False,
            'state': None
        }), 500


@app.route('/workflow/state/summary', methods=['GET', 'OPTIONS'])
def get_workflow_state_summary():
    """Get a summary of the current workflow state."""
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        state_manager = get_workflow_state_manager()
        summary = state_manager.get_state_summary()
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"Error getting workflow summary: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'summary': {'active': False}
        }), 500
```

**Key Changes**:
1. Rename `/workflow/execute` → `/workflow/start` (clearer intent)
2. Remove `/workflow/state` POST endpoint (server manages state internally)
3. Keep `/workflow/state` GET for WebUI polling
4. Add `/workflow/stop` for cancellation

---

### **Phase 6: Advanced Features**

#### **6.1 Workflow Pause/Resume**
```python
# workflow_executor.py
def pause_workflow(self, workflow_id: str) -> bool:
    """Pause a running workflow."""
    with self._lock:
        if workflow_id in self.pause_flags:
            self.pause_flags[workflow_id].set()
            return True
        return False

def resume_workflow(self, workflow_id: str) -> bool:
    """Resume a paused workflow."""
    with self._lock:
        if workflow_id in self.pause_flags:
            self.pause_flags[workflow_id].clear()
            return True
        return False
```

#### **6.2 Workflow History**
```python
# workflow_state.py
def archive_state(self, workflow_id: str):
    """Archive completed workflow to history."""
    state = self.load_state()
    if not state or state['workflow_id'] != workflow_id:
        return
    
    archive_dir = "/tmp/workflow_history"
    os.makedirs(archive_dir, exist_ok=True)
    
    archive_file = f"{archive_dir}/{workflow_id}.json"
    with open(archive_file, 'w') as f:
        json.dump(state, f, indent=2)
```

#### **6.3 Real-Time WebSocket Updates** (Optional)
For even more responsive UI updates without polling:

```python
# sync_api.py (add Flask-SocketIO)
from flask_socketio import SocketIO, emit

socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('subscribe_workflow')
def handle_subscribe(data):
    workflow_id = data.get('workflow_id')
    # Subscribe client to workflow updates
    join_room(workflow_id)

# In workflow_executor.py, emit updates
def _update_step_progress(self, state_manager, workflow_id, step_index, progress):
    state = state_manager.load_state()
    if state:
        state['steps'][step_index]['progress'] = progress
        state_manager.save_state(state)
        
        # Emit real-time update
        socketio.emit('workflow_progress', state, room=workflow_id)
```

---

## **File Structure**

```
app/
├── sync/
│   ├── workflow_state.py          ✓ (exists in branch)
│   ├── workflow_executor.py       ⚠️ (needs step executors)
│   └── sync_api.py                ⚠️ (merge + update endpoints)
├── webui/
│   ├── js/
│   │   ├── workflow.js            ⚠️ (refactor to visualization client)
│   │   ├── main.js                ⚠️ (add polling init)
│   │   ├── vastai/
│   │   │   └── instances.js       ⚠️ (remove step execution logic)
│   │   └── progress-indicators.js ✓ (already good)
│   ├── css/
│   │   └── workflow.css           ✓ (no changes needed)
│   └── index_template.html        ⚠️ (remove mode selector if added)
└── ...

docs/
├── WORKFLOW_STATE_PERSISTENCE.md  ✓ (exists in branch)
├── WORKFLOW_STATE_QUICK_REF.md    ✓ (exists in branch)
├── PROPOSAL_Headless...md         ✓ (this document)
└── MIGRATION_GUIDE.md             ➕ (new - migration steps)

test/
├── test_workflow_state.py          ✓ (exists in branch)
├── test_workflow_state_api.py      ✓ (exists in branch)
├── test_workflow_executor.py       ➕ (test step executors)
├── test_workflow_integration.py    ➕ (end-to-end server tests)
└── test_workflow_ui_restoration.py ➕ (UI reconnection tests)
```

**Note**: The key architectural change is:
- **Before**: WebUI JS functions execute SSH commands
- **After**: WebUI only renders state; server executes everything

---

## **Migration Plan**

### **Step 1**: Merge existing branch
```bash
git checkout main
git merge copilot/add-server-side-workflow-status
# Resolve any conflicts
```

### **Step 2**: Enhance workflow_executor.py
- Implement `_execute_step()` with real SSH API calls
- Add progress callbacks for each step type
- Add error handling and retry logic

### **Step 3**: Refactor WebUI workflow.js
- **Remove** all client-side step execution logic (`executeWorkflowStep()` and individual step functions)
- **Keep** step button UI but change onclick handlers to call server API
- Implement `runWorkflow()` to call `/workflow/start`
- Implement continuous state polling (every 2 seconds)
- Implement `restoreWorkflowState()` for page load
- Implement `updateWorkflowVisualization()` to render based on server state

### **Step 4**: Update configuration
```yaml
# config.yaml
workflow:
  step_delay: 5  # seconds between steps
  state_file: /tmp/workflow_state.json
  history_dir: /tmp/workflow_history
  max_history: 50
  poll_interval: 2  # seconds for WebUI polling
  cleanup_delay: 30  # seconds after completion
```

### **Step 5**: Testing
1. Unit tests for each step executor in `workflow_executor.py`
2. Integration tests for full server-side workflow execution
3. UI restoration tests (simulate refresh during execution)
4. Multi-session tests (multiple browsers viewing same workflow)
5. Stress tests (long-running workflows, network interruptions)

### **Step 6**: Remove legacy client-side execution
- Search codebase for `executeWorkflowStep()` calls and remove/refactor
- Remove `stepExecutionComplete` event dispatching from step functions
- Ensure all workflow control flows through server API
- Update documentation to reflect server-only execution model

---

## **UX Considerations**

### **Visual Feedback**

The WebUI always displays the server's workflow state:

```
┌─────────────────────────────────────────────────────────┐
│ ⚙️ VastAI Setup                                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ ⚠️ Workflow Reconnected                                 │
│ Step 3/8 currently running on server.                   │
│ You can close this page - execution will continue.      │
│ [View Logs]                                             │
│                                                          │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ▶️ Step 3: Execute Workflow                         │ │
│ │                                                      │ │
│ │ [⏸️ Stop Workflow]                                  │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                          │
│ ✅ 1. Test SSH Connection         [2.3s]               │
│      └─ SSH verified: host 6ecc5da8c823                 │
│                                                          │
│ ✅ 2. Setup CivitDL               [12.4s]              │
│      └─ v2.1.2 installed, API configured                │
│                                                          │
│ 🔄 3. Install Custom Nodes        [2m 15s]             │
│    ├─ ✓ Fetching repository list                       │
│    ├─ ✓ Installing ComfyUI-Manager                     │
│    ├─ ⏳ Installing rgthree-comfy (45%)                │
│    └─ ⚪ Installing ComfyUI_essentials                 │
│                                                          │
│ ⚪ 4. Verify Dependencies                              │
│                                                          │
│ ⚪ 5. Sync Instance                                    │
│                                                          │
│ Status: Polling server every 2 seconds...              │
└─────────────────────────────────────────────────────────┘
```

**Key UX Points**:
1. Clear indication that workflow runs on server
2. Reassurance that closing page won't interrupt execution
3. Automatic reconnection message on page load
4. Real-time progress updates via polling
5. Visual distinction between completed/running/pending steps

---

### **Error Handling**

Errors are captured server-side and reflected in state:

```javascript
// Server saves error to state
state.steps[stepIndex].status = 'failed';
state.steps[stepIndex].result = {
  success: false,
  error: error.message,
  details: error.details
};

// WebUI polls and renders error indicator
function updateWorkflowVisualization(state) {
  // ... render failed step with error message
  if (step.status === 'failed') {
    renderErrorIndicator(stepElement, step);
  }
}
```

**User Actions on Error**:
- **Stop**: Cancel the workflow
- **View Logs**: See detailed error information
- **Retry**: Start a new workflow from beginning

---

## **Performance Optimizations**

1. **Debounced State Writes**: Don't write state on every progress update
   ```python
   def _update_step_progress(self, ...):
       # Only write if 500ms have passed since last write
       if time.time() - self._last_write < 0.5:
           return
       self._last_write = time.time()
       state_manager.save_state(state)
   ```

2. **Efficient Polling**: Use long-polling or WebSocket for real-time updates

3. **State Compression**: For large workflows, compress JSON state

4. **Lazy Loading**: Don't restore full history, only current workflow

---

## **Security Considerations**

1. **State File Permissions**:
   ```python
   os.chmod(self.state_file, 0o600)  # Read/write for owner only
   ```

2. **Sanitize SSH Connections**: Don't store passwords in state

3. **Rate Limiting**: Prevent abuse of workflow start endpoint

4. **CSRF Protection**: Add tokens to workflow control endpoints

---

## **Testing Strategy**

### **Unit Tests**
- `test_workflow_state.py` ✓ (exists)
- `test_workflow_executor_steps.py` (new)
- `test_progress_indicators.py` (new)

### **Integration Tests**
- `test_full_workflow_execution.py`
- `test_workflow_restoration.py`
- `test_concurrent_workflows.py`

### **E2E Tests**
- Selenium tests for UI restoration
- Test page refresh during workflow
- Test browser close/reopen

---

## **Summary & Implementation Checklist**

### **Core Architectural Principle**

```
┌──────────────────────────────────────────────────────────┐
│  OLD ARCHITECTURE (Client-Side Execution)                │
│  ┌────────────┐                                          │
│  │   WebUI    │ ──executes SSH commands──> Remote Host  │
│  └────────────┘                                          │
│       ↓ Dies if browser closes                           │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  NEW ARCHITECTURE (Server-Side Execution)                │
│  ┌────────────┐    polls state    ┌────────────┐        │
│  │   WebUI    │ <───────────────> │   Server   │        │
│  │ (renders)  │                    │ (executes) │        │
│  └────────────┘                    └──────┬─────┘        │
│       ↓ Can close/refresh              ↓                 │
│       ↓ Reconnects anytime         SSH commands          │
│       ↓ Multiple sessions OK            ↓                │
│                                    Remote Host            │
└──────────────────────────────────────────────────────────┘
```

### **What Changes**

✅ **Preserved**:
- All existing workflow visualization UI
- Progress indicators and arrow animations  
- Step enable/disable toggles
- Setup result messages
- Error handling UI

🔄 **Changed**:
- Workflow execution moved from client to server
- Step buttons trigger server API instead of direct execution
- WebUI polls state instead of tracking local progress
- Page refresh reconnects to running workflow seamlessly

➕ **Added**:
- Background thread execution on server
- Persistent JSON state file
- State polling mechanism (every 2 seconds)
- Automatic reconnection on page load
- Multi-session support (multiple browsers can view same workflow)

### **Benefits**

1. **Interruption-Proof**: Workflows survive browser closes, refreshes, network issues
2. **Multi-Device**: View progress from any device/browser
3. **Long-Running**: Ideal for workflows that take 20+ minutes
4. **Reliable**: Server-side error handling and retry logic
5. **Auditable**: State file provides complete execution history

### **Implementation Priorities**

**Phase 1: Core Server Execution** (Critical)
- [ ] Implement all `_execute_*` methods in `workflow_executor.py`
- [ ] Add progress callbacks to long-running steps
- [ ] Test each step executor individually

**Phase 2: API Updates** (Critical)
- [ ] Add `/workflow/start` endpoint
- [ ] Add `/workflow/stop` endpoint
- [ ] Update `/workflow/state` to support polling
- [ ] Test API with Postman/curl

**Phase 3: WebUI Refactor** (Critical)
- [ ] Remove client-side step execution from `workflow.js`
- [ ] Implement `runWorkflow()` to call server API
- [ ] Implement state polling (every 2 seconds)
- [ ] Implement `restoreWorkflowState()` on page load
- [ ] Implement `updateWorkflowVisualization()` renderer

**Phase 4: Testing** (Important)
- [ ] Unit tests for step executors
- [ ] Integration tests for full workflows
- [ ] UI restoration tests (simulate refresh)
- [ ] Multi-session tests

**Phase 5: Cleanup** (Nice-to-have)
- [ ] Remove `executeWorkflowStep()` from codebase
- [ ] Remove `stepExecutionComplete` event system
- [ ] Update documentation
- [ ] Add workflow history viewing

### **Success Criteria**

✅ User can start a workflow and close browser  
✅ User can reopen browser and see workflow still running  
✅ User can view live progress from multiple devices  
✅ Workflow completes successfully without browser intervention  
✅ All existing visualizations (arrows, indicators, messages) work  
✅ Error states are properly captured and displayed  

### **Rollback Plan**

If issues arise during implementation:
1. Keep old `executeWorkflowStep()` logic in git history
2. Can revert WebUI changes easily via git
3. Server-side execution is additive—doesn't break existing SSH endpoints
4. State file can be disabled via config

### **Estimated Timeline**

- **Phase 1-2** (Server-side core): 2-3 days
- **Phase 3** (WebUI refactor): 2-3 days  
- **Phase 4** (Testing): 1-2 days
- **Phase 5** (Cleanup): 1 day

**Total**: 6-9 days for complete implementation

---

## **Next Steps**

**Immediate Actions**:
1. ✅ Review and approve this revised proposal (single unified architecture)
2. Merge `copilot/add-server-side-workflow-status` branch to `main`
3. Begin **Phase 1**: Implement step executors in `workflow_executor.py`
4. Iterate through phases, testing each component thoroughly

**Questions to Address**:
- Should we implement WebSocket (Phase 6.3) for real-time updates, or is 2-second polling sufficient?
- Do we need workflow pause/resume (Phase 6.1) in v1, or defer to v2?
- Where should state file be stored in production? (`/tmp` vs `/var/lib/vast_api/`)

**Ready to implement?** The architecture is now unified—all workflows run server-side, with WebUI as a pure visualization client. This ensures zero interruptions regardless of browser state.