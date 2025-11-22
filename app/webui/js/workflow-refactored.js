// ==============================
// Server-Side Workflow Client
// ==============================
// WebUI client for server-side workflow execution
// This module is a pure visualization client that polls workflow state from the server

let workflowPollingInterval = null;
let currentWorkflowId = null;
let workflowConfig = {
  stepDelay: 5000, // Default 5 seconds, will be loaded from config
  pollInterval: 2000 // Poll every 2 seconds
};

/**
 * Create transition indicator HTML with spinner and icons
 * @returns {string} - HTML markup for transition indicator
 */
function createTransitionIndicator() {
  return `
    <div class="spinner"></div>
    <div class="checkmark">✓</div>
    <div class="failed-icon">✗</div>
    <div class="down-arrow">↓</div>
  `;
}

/**
 * Initialize workflow system
 */
async function initWorkflow() {
  console.log('🔄 Initializing server-side workflow client...');
  
  // Load workflow configuration from server
  try {
    const response = await fetch('/config/workflow');
    if (response.ok) {
      const config = await response.json();
      if (config.workflow_step_delay) {
        workflowConfig.stepDelay = config.workflow_step_delay * 1000; // Convert to milliseconds
        console.log(`✅ Workflow step delay set to ${config.workflow_step_delay} seconds`);
      }
    }
  } catch (error) {
    console.warn('⚠️ Could not load workflow config, using defaults:', error);
  }
  
  // Restore workflow state on page load
  await restoreWorkflowState();
}

/**
 * Restore workflow state from server on page load
 */
async function restoreWorkflowState() {
  console.log('🔄 Checking for existing workflow state...');
  
  try {
    const response = await fetch('/workflow/state/summary');
    if (!response.ok) {
      console.log('No workflow state found on server');
      return;
    }
    
    const result = await response.json();
    if (result.success && result.has_workflow) {
      const summary = result.summary;
      console.log('📍 Found existing workflow state:', summary);
      
      // Restore workflow ID
      currentWorkflowId = summary.workflow_id;
      
      // Check if workflow is still running
      if (summary.is_running) {
        console.log('▶️ Workflow is still running, starting state polling...');
        startWorkflowPolling();
        
        // Update run button state
        const runButton = document.getElementById('run-workflow-btn');
        if (runButton) {
          runButton.textContent = '⏸️ Stop Workflow';
          runButton.classList.add('cancel');
        }
        
        showSetupResult(`Workflow in progress: ${summary.current_step + 1}/${summary.total_steps} steps completed`, 'info');
      } else {
        // Workflow finished, get full state to restore visualization
        console.log('✅ Workflow finished, restoring final state...');
        await updateWorkflowVisualization();
        
        // Show final status
        if (summary.status === 'completed') {
          showSetupResult('✅ Workflow completed successfully!', 'success');
        } else if (summary.status === 'failed') {
          showSetupResult('❌ Workflow failed', 'error');
        } else if (summary.status === 'cancelled') {
          showSetupResult('⏸️ Workflow cancelled', 'error');
        }
      }
    } else {
      console.log('No active workflow found');
    }
  } catch (error) {
    console.error('❌ Error restoring workflow state:', error);
  }
}

/**
 * Toggle step enable/disable state
 * @param {HTMLElement} toggleButton - The toggle button that was clicked
 */
function toggleStep(toggleButton) {
  const workflowStep = toggleButton.closest('.workflow-step');
  if (!workflowStep) return;
  
  // Don't allow toggling during workflow execution
  if (currentWorkflowId && workflowPollingInterval) {
    return;
  }
  
  const isDisabled = workflowStep.classList.contains('disabled');
  
  if (isDisabled) {
    // Enable the step
    workflowStep.classList.remove('disabled');
    toggleButton.style.background = 'var(--text-success)';
    console.log('✅ Step enabled:', workflowStep.dataset.action);
  } else {
    // Disable the step
    workflowStep.classList.add('disabled');
    toggleButton.style.background = 'var(--interactive-normal)';
    console.log('❌ Step disabled:', workflowStep.dataset.action);
  }
}

/**
 * Run the complete workflow on server
 */
async function runWorkflow() {
  if (currentWorkflowId && workflowPollingInterval) {
    // Stop workflow
    console.log('🛑 Stopping workflow...');
    await stopWorkflow();
    return;
  }
  
  console.log('▶️ Starting workflow execution on server...');
  
  // Get all enabled workflow steps
  const workflowStepsContainer = document.getElementById('workflow-steps');
  const stepElements = workflowStepsContainer.querySelectorAll('.workflow-step:not(.disabled)');
  
  if (stepElements.length === 0) {
    showSetupResult('No steps are enabled. Please enable at least one step.', 'error');
    return;
  }
  
  // Validate SSH connection
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnectionString) {
    showSetupResult('Please enter an SSH connection string first.', 'error');
    return;
  }
  
  // Get instance ID for reboot step (if present)
  const instanceId = window.currentInstanceId || null;
  
  // Build steps array for server
  const steps = [];
  stepElements.forEach(stepElement => {
    const action = stepElement.dataset.action;
    const stepButton = stepElement.querySelector('.step-button');
    
    const stepConfig = {
      action: action,
      label: stepButton.textContent.trim(),
      status: 'pending'
    };
    
    // Add action-specific parameters
    if (action === 'set_ui_home' || action === 'install_custom_nodes' || action === 'verify_dependencies') {
      stepConfig.ui_home = '/workspace/ComfyUI'; // TODO: Make configurable
    }
    
    if (action === 'reboot_instance' && instanceId) {
      stepConfig.instance_id = instanceId;
    }
    
    steps.push(stepConfig);
  });
  
  // Update UI to show workflow is starting
  const runButton = document.getElementById('run-workflow-btn');
  runButton.textContent = '⏸️ Stop Workflow';
  runButton.classList.add('cancel');
  
  // Clear previous state
  resetWorkflowVisualization();
  
  try {
    // Start workflow on server
    const response = await fetch('/workflow/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        steps: steps,
        ssh_connection: sshConnectionString,
        step_delay: workflowConfig.stepDelay / 1000, // Convert to seconds
        instance_id: instanceId
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    
    if (result.success) {
      currentWorkflowId = result.workflow_id;
      console.log(`✅ Workflow started on server: ${currentWorkflowId}`);
      showSetupResult('Workflow started on server...', 'info');
      
      // Start polling for state updates
      startWorkflowPolling();
    } else {
      throw new Error(result.message || 'Failed to start workflow');
    }
  } catch (error) {
    console.error('❌ Error starting workflow:', error);
    showSetupResult(`Error starting workflow: ${error.message}`, 'error');
    
    // Reset button state
    runButton.textContent = '▶️ Run Workflow';
    runButton.classList.remove('cancel');
  }
}

/**
 * Stop workflow on server
 */
async function stopWorkflow() {
  if (!currentWorkflowId) {
    console.warn('No active workflow to stop');
    return;
  }
  
  try {
    const response = await fetch('/workflow/stop', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        workflow_id: currentWorkflowId
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      console.log('✅ Workflow stop requested');
      showSetupResult('Workflow stop requested...', 'info');
    } else {
      console.warn('⚠️ Failed to stop workflow:', result.message);
    }
  } catch (error) {
    console.error('❌ Error stopping workflow:', error);
    showSetupResult(`Error stopping workflow: ${error.message}`, 'error');
  }
}

/**
 * Start polling for workflow state updates
 */
function startWorkflowPolling() {
  if (workflowPollingInterval) {
    console.warn('Polling already active');
    return;
  }
  
  console.log('🔄 Starting workflow state polling...');
  
  // Poll immediately
  updateWorkflowVisualization();
  
  // Then poll every N seconds
  workflowPollingInterval = setInterval(async () => {
    await updateWorkflowVisualization();
  }, workflowConfig.pollInterval);
}

/**
 * Stop polling for workflow state updates
 */
function stopWorkflowPolling() {
  if (workflowPollingInterval) {
    console.log('⏸️ Stopping workflow state polling');
    clearInterval(workflowPollingInterval);
    workflowPollingInterval = null;
  }
}

/**
 * Handle workflow blockage (e.g., host key verification required)
 * @param {object} state - Workflow state with block_info
 */
async function handleWorkflowBlockage(state) {
  const blockInfo = state.block_info;
  const blockReason = blockInfo.block_reason;
  
  if (blockReason === 'host_verification_needed') {
    console.log('🔐 Host verification required, showing modal...');
    
    try {
      // Show SSH host verification modal (from VastAIUI module)
      const userAccepted = await window.VastAIUI.showSSHHostVerificationModal({
        host: blockInfo.host,
        port: blockInfo.port,
        fingerprints: blockInfo.fingerprints || []
      });
      
      if (userAccepted) {
        console.log('✅ User accepted host key, adding to known_hosts...');
        
        // Call verify-host endpoint to add the key
        const sshConnection = state.ssh_connection;
        const verifyResponse = await fetch('/ssh/verify-host', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            ssh_connection: sshConnection,
            accept: true
          })
        });
        
        const verifyResult = await verifyResponse.json();
        
        if (verifyResult.success) {
          console.log('✅ Host key added successfully, resuming workflow...');
          
          // Resume the workflow
          const resumeResponse = await fetch('/workflow/resume', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              workflow_id: state.workflow_id
            })
          });
          
          const resumeResult = await resumeResponse.json();
          
          if (resumeResult.success) {
            console.log('✅ Workflow resumed');
            // Restart polling
            startWorkflowPolling();
          } else {
            console.error('❌ Failed to resume workflow:', resumeResult.message);
            showSetupResult(`Failed to resume workflow: ${resumeResult.message}`, 'error');
            currentWorkflowId = null;
          }
        } else {
          console.error('❌ Failed to add host key:', verifyResult.message);
          showSetupResult(`Failed to add host key: ${verifyResult.message}`, 'error');
          
          // Stop the workflow
          await stopWorkflow();
          currentWorkflowId = null;
        }
      } else {
        console.log('❌ User rejected host key, stopping workflow...');
        showSetupResult('Host key verification rejected. Workflow cancelled.', 'error');
        
        // Stop the workflow
        await stopWorkflow();
        currentWorkflowId = null;
      }
    } catch (error) {
      console.error('❌ Error handling host verification:', error);
      showSetupResult(`Error during host verification: ${error.message}`, 'error');
      
      // Stop the workflow
      await stopWorkflow();
      currentWorkflowId = null;
    }
  } else {
    console.warn('⚠️ Unknown block reason:', blockReason);
    showSetupResult(`Workflow blocked: ${blockReason}`, 'error');
    await stopWorkflow();
    currentWorkflowId = null;
  }
}

/**
 * Update workflow visualization from server state
 */
async function updateWorkflowVisualization() {
  try {
    const response = await fetch('/workflow/state');
    if (!response.ok) {
      console.warn('No workflow state available');
      return;
    }
    
    const result = await response.json();
    
    if (!result.success || !result.state) {
      console.warn('No workflow state in response');
      return;
    }
    
    const state = result.state;
    
    // Update visualization based on state
    renderWorkflowState(state);
    
    // Check if workflow is blocked (e.g., needs host verification)
    if (state.status === 'blocked' && state.block_info) {
      console.log('⚠️ Workflow blocked, handling user interaction:', state.block_info.block_reason);
      stopWorkflowPolling(); // Stop polling while modal is shown
      await handleWorkflowBlockage(state);
      return;
    }
    
    // Check if workflow finished
    if (state.status === 'completed' || state.status === 'failed' || state.status === 'cancelled') {
      console.log(`✅ Workflow finished with status: ${state.status}`);
      stopWorkflowPolling();
      
      // Reset button state
      const runButton = document.getElementById('run-workflow-btn');
      if (runButton) {
        runButton.textContent = '▶️ Run Workflow';
        runButton.classList.remove('cancel');
      }
      
      // Show final status
      if (state.status === 'completed') {
        showSetupResult('✅ Workflow completed successfully!', 'success');
      } else if (state.status === 'failed') {
        const failedStep = state.steps[state.current_step];
        const stepLabel = failedStep?.label || 'unknown step';
        const errorMsg = state.error_message || failedStep?.error || 'Unknown error';
        
        // Show detailed error message
        showSetupResult(`❌ Workflow failed at: ${stepLabel}\n${errorMsg}`, 'error');
      } else if (state.status === 'cancelled') {
        showSetupResult('⏸️ Workflow cancelled', 'error');
      }
      
      // Clear workflow ID after a delay
      setTimeout(() => {
        currentWorkflowId = null;
      }, 5000);
    }
  } catch (error) {
    console.error('❌ Error updating workflow visualization:', error);
  }
}

/**
 * Render workflow state to UI
 * @param {object} state - Workflow state from server
 */
function renderWorkflowState(state) {
  const workflowStepsContainer = document.getElementById('workflow-steps');
  if (!workflowStepsContainer) return;
  
  const stepElements = workflowStepsContainer.querySelectorAll('.workflow-step:not(.disabled)');
  const arrowElements = workflowStepsContainer.querySelectorAll('.workflow-arrow');
  
  const currentStepIndex = state.current_step;
  const stepsData = state.steps || [];
  
  // Update each step's visual state
  stepElements.forEach((stepElement, index) => {
    const stepData = stepsData[index];
    if (!stepData) return;
    
    const stepStatus = stepData.status;
    
    // Remove all status classes
    stepElement.classList.remove('pending', 'in-progress', 'completed', 'failed', 'blocked');
    
    // Add current status class
    if (stepStatus) {
      stepElement.classList.add(stepStatus.replace('_', '-'));
    }
    
    // Render tasklist if step is in-progress or finished
    if (stepStatus && (stepStatus === 'in_progress' || stepStatus === 'completed' || stepStatus === 'failed')) {
      renderTasklist(stepElement, stepData);
    }
  });
  
  // Update arrows between steps
  arrowElements.forEach((arrow, index) => {
    const prevStepData = stepsData[index];
    const nextStepData = stepsData[index + 1];
    
    if (!prevStepData || !nextStepData) return;
    
    // Remove all status classes
    arrow.classList.remove('pending', 'loading', 'completed', 'failed');
    
    // Determine arrow status based on surrounding steps
    if (prevStepData.status === 'completed' && nextStepData.status === 'in_progress') {
      // Previous step done, next step in progress - show loading spinner
      arrow.classList.add('loading');
    } else if (prevStepData.status === 'completed' && nextStepData.status === 'completed') {
      // Both steps done - show completed checkmark
      arrow.classList.add('completed');
    } else if (prevStepData.status === 'failed') {
      // Previous step failed
      arrow.classList.add('failed');
    } else {
      // Pending - show down arrow
      arrow.classList.add('pending');
    }
  });
  
  // Update status message
  if (state.status === 'running') {
    const currentStepData = stepsData[currentStepIndex];
    if (currentStepData) {
      showSetupResult(`Executing: ${currentStepData.label}... (${currentStepIndex + 1}/${stepsData.length})`, 'info');
    }
  } else if (state.status === 'blocked') {
    const blockReason = state.block_info?.block_reason || 'unknown';
    showSetupResult(`⚠️ Workflow paused: ${blockReason.replace(/_/g, ' ')}`, 'warning');
  }
}

/**
 * Render tasklist for a workflow step
 * @param {HTMLElement} stepElement - The workflow step element
 * @param {object} stepData - Step data from workflow state
 */
function renderTasklist(stepElement, stepData) {
  const tasks = stepData.tasks || [];
  const completionNote = stepData.completion_note || '';
  
  // Check if tasklist already exists
  let tasklistElement = stepElement.querySelector('.tasklist');
  
  if (tasks.length === 0 && !completionNote) {
    // No tasks or note, remove tasklist if it exists
    if (tasklistElement) {
      tasklistElement.remove();
    }
    return;
  }
  
  if (!tasklistElement) {
    // Create new tasklist element
    tasklistElement = document.createElement('div');
    tasklistElement.className = 'tasklist';
    stepElement.appendChild(tasklistElement);
  }
  
  // Build tasklist HTML
  let tasklistHTML = '<ul class="task-list">';
  
  tasks.forEach(task => {
    const taskName = task.name;
    const taskStatus = task.status || 'pending';
    const taskNote = task.note || '';
    
    // Check if it's a countdown status
    if (taskStatus.startsWith('countdown:')) {
      const seconds = taskStatus.split(':')[1];
      tasklistHTML += `<li class="task-item">
        <span class="task-name">${escapeHtml(taskName)}</span>
        <span class="task-status countdown">${seconds}s</span>
      </li>`;
    } else {
      // Check if it's a success with count (e.g., "success (3/5)")
      let statusDisplay = taskStatus;
      let statusClass = taskStatus;
      
      if (taskStatus.startsWith('success (')) {
        statusDisplay = taskStatus;
        statusClass = 'success';
      }
      
      tasklistHTML += `<li class="task-item">
        <span class="task-name">${escapeHtml(taskName)}</span>
        <span class="task-status ${statusClass}">${escapeHtml(statusDisplay)}</span>
      </li>`;
    }
  });
  
  tasklistHTML += '</ul>';
  
  // Add completion note if present
  if (completionNote) {
    tasklistHTML += `<div class="completion-note">${escapeHtml(completionNote)}</div>`;
  }
  
  tasklistElement.innerHTML = tasklistHTML;
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} - Escaped text
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Reset workflow visualization to initial state
 */
function resetWorkflowVisualization() {
  const workflowStepsContainer = document.getElementById('workflow-steps');
  if (!workflowStepsContainer) return;
  
  const stepElements = workflowStepsContainer.querySelectorAll('.workflow-step');
  const arrowElements = workflowStepsContainer.querySelectorAll('.workflow-arrow');
  
  // Reset all steps
  stepElements.forEach(step => {
    step.classList.remove('in-progress', 'completed', 'failed', 'blocked');
  });
  
  // Reset all arrows to pending state
  arrowElements.forEach(arrow => {
    arrow.classList.remove('loading', 'completed', 'failed');
    arrow.classList.add('pending');
  });
}

/**
 * Update workflow steps from template
 * @param {object} template - Template object containing button configuration
 */
function updateWorkflowSteps(template) {
  const container = document.getElementById('workflow-steps');
  if (!container) return;
  
  const uiConfig = template.ui_config || {};
  const buttons = uiConfig.setup_buttons || [];
  
  // Clear existing steps
  container.innerHTML = '';
  
  console.log(`🔧 Creating ${buttons.length} workflow steps`);
  
  // Create workflow steps for each button
  buttons.forEach((button, index) => {
    // Create step element
    const stepDiv = document.createElement('div');
    stepDiv.className = 'workflow-step';
    stepDiv.dataset.action = button.action;
    
    // Create button container for horizontal layout
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'step-button-container';
    
    // Create step label (buttons no longer executable in server-side mode)
    const stepButton = document.createElement('button');
    stepButton.className = 'step-button';
    stepButton.textContent = button.label;
    stepButton.disabled = true; // Individual steps not executable in workflow mode
    stepButton.title = 'Steps are executed as part of workflow';
    
    // Create toggle button
    const toggleButton = document.createElement('button');
    toggleButton.className = 'step-toggle';
    toggleButton.title = 'Enable/Disable this step';
    toggleButton.onclick = function() { toggleStep(this); };
    
    const toggleIcon = document.createElement('span');
    toggleIcon.className = 'toggle-icon';
    toggleButton.appendChild(toggleIcon);
    
    // Add buttons to container
    buttonContainer.appendChild(stepButton);
    buttonContainer.appendChild(toggleButton);
    
    // Add container to step
    stepDiv.appendChild(buttonContainer);
    
    // Add step to container
    container.appendChild(stepDiv);
    
    // Add transition indicator between steps (except after the last one)
    if (index < buttons.length - 1) {
      const arrow = document.createElement('div');
      arrow.className = 'workflow-arrow pending';
      arrow.innerHTML = createTransitionIndicator();
      container.appendChild(arrow);
    }
    
    console.log(`  ${index + 1}. Created workflow step: "${button.label}" (${button.action})`);
  });
  
  console.log(`✅ Workflow steps created. Total steps:`, buttons.length);
}

/**
 * Reset workflow steps to defaults
 */
function resetWorkflowSteps() {
  const container = document.getElementById('workflow-steps');
  if (!container) return;
  
  container.innerHTML = '';
  
  // Create default steps
  const defaultSteps = [
    { action: 'test_ssh', label: '🔧 Test SSH Connection' },
    { action: 'sync_instance', label: '🔄 Sync Instance' }
  ];
  
  defaultSteps.forEach((step, index) => {
    const stepDiv = document.createElement('div');
    stepDiv.className = 'workflow-step';
    stepDiv.dataset.action = step.action;
    
    // Create button container
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'step-button-container';
    
    const stepButton = document.createElement('button');
    stepButton.className = 'step-button';
    stepButton.textContent = step.label;
    stepButton.disabled = true;
    stepButton.title = 'Steps are executed as part of workflow';
    
    const toggleButton = document.createElement('button');
    toggleButton.className = 'step-toggle';
    toggleButton.title = 'Enable/Disable this step';
    toggleButton.onclick = function() { toggleStep(this); };
    
    const toggleIcon = document.createElement('span');
    toggleIcon.className = 'toggle-icon';
    toggleButton.appendChild(toggleIcon);
    
    buttonContainer.appendChild(stepButton);
    buttonContainer.appendChild(toggleButton);
    stepDiv.appendChild(buttonContainer);
    container.appendChild(stepDiv);
    
    if (index < defaultSteps.length - 1) {
      const arrow = document.createElement('div');
      arrow.className = 'workflow-arrow pending';
      arrow.innerHTML = createTransitionIndicator();
      container.appendChild(arrow);
    }
  });
}

// Initialize workflow system when loaded
console.log('📄 Server-side workflow client loaded');
