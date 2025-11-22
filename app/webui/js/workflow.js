// ==============================
// Workflow Management Module
// ==============================
// Handles workflow execution, progress tracking, and UI updates

let workflowRunning = false;
let workflowCancelled = false;
let currentWorkflowSteps = [];
let workflowConfig = {
  stepDelay: 5000 // Default 5 seconds, will be loaded from config
};
let currentWorkflowId = null;

/**
 * Create an SVG downward arrow with vertical fill progress
 * The arrow is revealed from the top down as `progress` goes from 0 → 1.
 *
 * @param {number} progress - Progress from 0 to 1 (0% to 100%)
 * @returns {string} - SVG markup
 */
function createArrowSVG(progress = 0) {
  // Clamp progress to [0, 1]
  const clamped = Math.max(0, Math.min(1, progress));

  const width = 50;
  const height = 60;

  // Arrow geometry
  const shaftWidth = 14;
  const shaftHeight = 32;      // straight vertical part
  const headWidth = 32;
  const headHeight = height - shaftHeight; // remaining height for the head

  const centerX = width / 2;

  const shaftLeft   = centerX - shaftWidth / 2;
  const shaftRight  = centerX + shaftWidth / 2;
  const shaftTopY   = 0;
  const shaftBotY   = shaftHeight;

  const headBaseY   = shaftBotY;      // where the head starts
  const headTipY    = height;         // bottom point
  const headLeftX   = centerX - headWidth / 2;
  const headRightX  = centerX + headWidth / 2;

  // Single path for a clean, bold downward arrow
  const arrowPath = [
    // Shaft top edge
    `M ${shaftLeft} ${shaftTopY}`,
    `L ${shaftRight} ${shaftTopY}`,
    // Shaft sides down
    `L ${shaftRight} ${headBaseY}`,
    // Head right edge
    `L ${headRightX} ${headBaseY}`,
    // Tip
    `L ${centerX} ${headTipY}`,
    // Head left edge
    `L ${headLeftX} ${headBaseY}`,
    // Back up left side of shaft
    `L ${shaftLeft} ${headBaseY}`,
    'Z'
  ].join(' ');

  // If you want literal “row of pixels at a time”, quantize the fill height:
  // const pixelStepHeight = 1; // 1 SVG unit per "row"; tweak if needed
  // const filledHeight = Math.floor(clamped * height / pixelStepHeight) * pixelStepHeight;
  const filledHeight = clamped * height;

  // Unique clipPath ID
  const clipId = `arrow-clip-${Math.random().toString(36).slice(2)}`;

  return `
<svg viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <!-- Arrow outline -->
  <path class="arrow-body" d="${arrowPath}" />

  <defs>
    <!-- Rect that grows from the top downward -->
    <clipPath id="${clipId}">
      <rect x="0" y="0" width="${width}" height="${filledHeight}" />
    </clipPath>
  </defs>

  <!-- Filled portion of the arrow, revealed from top down -->
  <g clip-path="url(#${clipId})">
    <path class="arrow-fill" d="${arrowPath}" />
  </g>
</svg>
  `;
}


/**
 * Update arrow SVG with new progress
 * @param {HTMLElement} arrowElement - The arrow element
 * @param {number} progress - Progress from 0 to 1
 */
function updateArrowProgress(arrowElement, progress) {
  arrowElement.innerHTML = createArrowSVG(progress);
}

/**
 * Save workflow state to server
 */
async function saveWorkflowState(state) {
  try {
    const response = await fetch('/workflow/state', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(state)
    });
    
    if (response.ok) {
      console.log('✅ Workflow state saved to server');
      return true;
    } else {
      console.warn('⚠️ Failed to save workflow state to server');
      return false;
    }
  } catch (error) {
    console.error('❌ Error saving workflow state:', error);
    return false;
  }
}

/**
 * Load workflow state from server
 */
async function loadWorkflowState() {
  try {
    const response = await fetch('/workflow/state');
    if (response.ok) {
      const data = await response.json();
      if (data.success && data.active && data.state) {
        console.log('📥 Loaded workflow state from server:', data.state);
        return data.state;
      }
    }
    return null;
  } catch (error) {
    console.error('❌ Error loading workflow state:', error);
    return null;
  }
}

/**
 * Clear workflow state from server
 */
async function clearWorkflowState() {
  try {
    const response = await fetch('/workflow/state', {
      method: 'DELETE'
    });
    
    if (response.ok) {
      console.log('✅ Workflow state cleared from server');
      return true;
    } else {
      console.warn('⚠️ Failed to clear workflow state from server');
      return false;
    }
  } catch (error) {
    console.error('❌ Error clearing workflow state:', error);
    return false;
  }
}

/**
 * Restore workflow state from server on page load
 */
async function restoreWorkflowState() {
  console.log('🔄 Checking for active workflow state...');
  
  const state = await loadWorkflowState();
  if (!state) {
    console.log('ℹ️ No active workflow state found');
    return;
  }
  
  console.log('📋 Restoring workflow state:', state);
  
  // Switch to vastai-setup tab
  const vastaiSetupTab = document.querySelector('.tab-button:nth-child(2)');
  if (vastaiSetupTab) {
    vastaiSetupTab.click();
  }
  
  // Restore workflow ID
  currentWorkflowId = state.workflow_id;
  
  // Restore step states
  const workflowStepsContainer = document.getElementById('workflow-steps');
  if (!workflowStepsContainer) return;
  
  const stepElements = workflowStepsContainer.querySelectorAll('.workflow-step');
  const steps = state.steps || [];
  
  steps.forEach((stepState, index) => {
    if (index < stepElements.length) {
      const stepElement = stepElements[index];
      const arrow = stepElement.nextElementSibling;
      
      // Apply step status classes
      if (stepState.status === 'completed') {
        stepElement.classList.add('completed');
        if (arrow && arrow.classList.contains('workflow-arrow')) {
          arrow.classList.remove('loading');
          arrow.classList.add('completed');
          updateArrowProgress(arrow, 1.0);
        }
      } else if (stepState.status === 'in_progress') {
        stepElement.classList.add('in-progress');
        if (arrow && arrow.classList.contains('workflow-arrow')) {
          arrow.classList.add('loading');
        }
      } else if (stepState.status === 'failed') {
        stepElement.classList.add('failed');
      }
    }
  });
  
  // Update UI to show workflow status
  if (state.status === 'running') {
    showSetupResult('⚠️ Workflow was in progress. You may need to restart it.', 'warning');
  } else if (state.status === 'completed') {
    showSetupResult('✅ Previous workflow completed successfully!', 'success');
  } else if (state.status === 'failed') {
    showSetupResult('❌ Previous workflow failed.', 'error');
  }
}

/**
 * Initialize workflow system
 */
async function initWorkflow() {
  console.log('🔄 Initializing workflow system...');
  
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
  
  // Check for and restore active workflow state
  await restoreWorkflowState();
}

/**
 * Toggle step enable/disable state
 * @param {HTMLElement} toggleButton - The toggle button that was clicked
 */
function toggleStep(toggleButton) {
  const workflowStep = toggleButton.closest('.workflow-step');
  if (!workflowStep) return;
  
  // Don't allow toggling during workflow execution
  if (workflowRunning) {
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
 * Run the complete workflow
 */
async function runWorkflow() {
  if (workflowRunning) {
    // Cancel workflow
    console.log('🛑 Cancelling workflow...');
    workflowCancelled = true;
    return;
  }
  
  console.log('▶️ Starting workflow execution...');
  
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
  
  // Update UI to show workflow is running
  workflowRunning = true;
  workflowCancelled = false;
  const runButton = document.getElementById('run-workflow-btn');
  runButton.textContent = '⏸️ Cancel Workflow';
  runButton.classList.add('cancel');
  
  // Generate workflow ID
  currentWorkflowId = `workflow_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
  
  // Build initial workflow state
  const workflowState = {
    workflow_id: currentWorkflowId,
    status: 'running',
    current_step: 0,
    steps: Array.from(stepElements).map((el, idx) => ({
      action: el.dataset.action,
      label: el.querySelector('.step-button')?.textContent.trim() || '',
      status: 'pending',
      index: idx
    })),
    start_time: new Date().toISOString(),
    ssh_connection: sshConnectionString
  };
  
  // Save initial state to server
  await saveWorkflowState(workflowState);
  
  // Set all arrows to grey/loading state with 0% progress
  const allArrows = workflowStepsContainer.querySelectorAll('.workflow-arrow');
  allArrows.forEach(arrow => {
    arrow.classList.remove('completed');
    arrow.classList.add('loading');
    updateArrowProgress(arrow, 0);
  });
  
  // Disable all step buttons and toggles during execution
  const allSteps = workflowStepsContainer.querySelectorAll('.workflow-step');
  allSteps.forEach(step => {
    const stepButton = step.querySelector('.step-button');
    const toggleButton = step.querySelector('.step-toggle');
    if (stepButton) stepButton.disabled = true;
    if (toggleButton) toggleButton.disabled = true;
  });
  
  // Grey out disabled steps
  const disabledSteps = workflowStepsContainer.querySelectorAll('.workflow-step.disabled');
  disabledSteps.forEach(step => {
    step.style.opacity = '0.3';
  });
  
  try {
    // Execute each enabled step in sequence
    for (let i = 0; i < stepElements.length; i++) {
      if (workflowCancelled) {
        showSetupResult('Workflow cancelled by user.', 'error');
        break;
      }
      
      const stepElement = stepElements[i];
      const action = stepElement.dataset.action;
      const stepButton = stepElement.querySelector('.step-button');
      
      console.log(`📍 Executing step ${i + 1}/${stepElements.length}: ${action}`);
      
      // Update workflow state - step starting
      workflowState.current_step = i;
      workflowState.steps[i].status = 'in_progress';
      await saveWorkflowState(workflowState);
      
      // Mark step as in-progress
      stepElement.classList.add('in-progress');
      showSetupResult(`Executing: ${stepButton.textContent.trim()}...`, 'info');
      
      // Execute the step
      const success = await executeWorkflowStep(stepElement);
      
      // Remove in-progress state
      stepElement.classList.remove('in-progress');
      
      if (success) {
        // Mark step as completed
        stepElement.classList.add('completed');
        console.log(`✅ Step ${i + 1} completed: ${action}`);
        
        // Update workflow state - step completed
        workflowState.steps[i].status = 'completed';
        await saveWorkflowState(workflowState);
        
        // Animate arrow with 11-step loading bar if not the last step
        if (i < stepElements.length - 1 && !workflowCancelled) {
          const nextArrow = stepElement.nextElementSibling;
          if (nextArrow && nextArrow.classList.contains('workflow-arrow')) {
            console.log(`🎬 Starting arrow loading animation (11 steps)`);
            
            // Animate arrow filling over the delay period with 11 discrete steps
            const steps = 11; // 0%, 10%, 20%, ..., 100%
            const stepDuration = workflowConfig.stepDelay / (steps - 1);
            
            for (let step = 0; step < steps; step++) {
              if (workflowCancelled) break;
              
              const progress = step / (steps - 1); // 0.0 to 1.0
              updateArrowProgress(nextArrow, progress);
              
              // Wait for next step (except on the last step)
              if (step < steps - 1) {
                await sleep(stepDuration);
              }
            }
            
            // Mark arrow as completed (full color)
            nextArrow.classList.remove('loading');
            nextArrow.classList.add('completed');
          }
        }
      } else {
        // Mark step as failed
        stepElement.classList.add('failed');
        console.log(`❌ Step ${i + 1} failed: ${action}`);
        
        // Update workflow state - step failed
        workflowState.status = 'failed';
        workflowState.steps[i].status = 'failed';
        await saveWorkflowState(workflowState);
        
        showSetupResult(`Workflow failed at step: ${stepButton.textContent.trim()}`, 'error');
        break; // Stop workflow on failure
      }
      
      // Note: Arrow animation now happens inline above, no separate wait needed
      // The arrow fills during the delay, so we don't need additional waiting
    }
    
    if (!workflowCancelled) {
      showSetupResult('✅ Workflow completed successfully!', 'success');
      
      // Update workflow state - completed
      workflowState.status = 'completed';
      await saveWorkflowState(workflowState);
    } else {
      // Update workflow state - cancelled
      workflowState.status = 'cancelled';
      await saveWorkflowState(workflowState);
    }
  } catch (error) {
    console.error('❌ Workflow error:', error);
    showSetupResult(`Workflow error: ${error.message}`, 'error');
    
    // Update workflow state - error
    if (workflowState) {
      workflowState.status = 'failed';
      await saveWorkflowState(workflowState);
    }
  } finally {
    // Clear workflow state from server after a delay
    // This allows the user to see the final state if they refresh immediately
    // The delay is configurable via STATE_CLEANUP_DELAY_MS constant
    setTimeout(async () => {
      await clearWorkflowState();
    }, 30000); // 30 seconds delay
    
    // Reset UI state
    workflowRunning = false;
    workflowCancelled = false;
    currentWorkflowId = null;
    runButton.textContent = '▶️ Run Workflow';
    runButton.classList.remove('cancel');
    
    // Re-enable buttons and toggles
    allSteps.forEach(step => {
      const stepButton = step.querySelector('.step-button');
      const toggleButton = step.querySelector('.step-toggle');
      if (stepButton) stepButton.disabled = false;
      if (toggleButton) toggleButton.disabled = false;
      step.style.opacity = '';
    });
  }
}

/**
 * Execute a single workflow step
 * @param {HTMLElement} stepElement - The workflow step element
 * @returns {Promise<boolean>} - True if step succeeded, false otherwise
 */
async function executeWorkflowStep(stepElement) {
  const action = stepElement.dataset.action;
  const stepButton = stepElement.querySelector('.step-button');
  
  return new Promise((resolve) => {
    // Create a temporary handler to capture the result
    const originalOnclick = stepButton.onclick;
    let resultReceived = false;
    
    // Set up a result listener
    const resultListener = (event) => {
      if (event.detail && event.detail.stepAction === action) {
        resultReceived = true;
        document.removeEventListener('stepExecutionComplete', resultListener);
        resolve(event.detail.success);
      }
    };
    
    document.addEventListener('stepExecutionComplete', resultListener);
    
    // Trigger the step's onclick handler
    if (originalOnclick) {
      try {
        originalOnclick.call(stepButton);
        
        // If no result is received within a reasonable time, consider it a timeout
        // For long-running operations like install_custom_nodes and reboot_instance, use a longer timeout
        let timeout = 30000; // Default 30s for most steps
        if (action === 'install_custom_nodes') {
          timeout = 1200000; // 20 minutes for custom nodes installation
        } else if (action === 'reboot_instance') {
          timeout = 120000; // 2 minutes for reboot (container stop/start + verification)
        }
        
        setTimeout(() => {
          if (!resultReceived) {
            console.warn(`⏱️ Step ${action} timed out after ${timeout/1000}s without completion event`);
            document.removeEventListener('stepExecutionComplete', resultListener);
            resolve(false); // Changed from true to false - timeout should be treated as failure
          }
        }, timeout);
      } catch (error) {
        console.error('Error executing step:', error);
        document.removeEventListener('stepExecutionComplete', resultListener);
        resolve(false);
      }
    } else {
      console.warn('No onclick handler for step:', action);
      document.removeEventListener('stepExecutionComplete', resultListener);
      resolve(false);
    }
  });
}

/**
 * Sleep for specified milliseconds
 * @param {number} ms - Milliseconds to sleep
 * @returns {Promise}
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
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
    
    // Create step button
    const stepButton = document.createElement('button');
    stepButton.className = 'step-button';
    stepButton.textContent = button.label;
    
    // Set onclick handler based on action
    switch (button.action) {
      case 'test_ssh':
        stepButton.onclick = testVastAISSH;
        break;
      case 'sync_instance':
        stepButton.onclick = syncFromConnectionString;
        break;
      case 'setup_civitdl':
        stepButton.onclick = setupCivitDL;
        break;
      case 'test_civitdl':
        stepButton.onclick = testCivitDL;
        break;
      case 'install_custom_nodes':
        stepButton.onclick = installCustomNodes;
        break;
      case 'verify_dependencies':
        stepButton.onclick = verifyDependencies;
        break;
      case 'set_ui_home':
        stepButton.onclick = setUIHome;
        break;
      case 'setup_python_venv':
        stepButton.onclick = setupPythonVenv;
        break;
      case 'clone_auto_installer':
        stepButton.onclick = cloneAutoInstaller;
        break;
      case 'get_ui_home':
        stepButton.onclick = getUIHome;
        break;
      case 'terminate_connection':
        stepButton.onclick = terminateConnection;
        break;
      case 'reboot_instance':
        stepButton.onclick = rebootInstance;
        break;
      default:
        stepButton.onclick = () => console.log(`Unknown action: ${button.action}`);
    }
    
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
    
    // Add arrow between steps (except after the last one)
    if (index < buttons.length - 1) {
      const arrow = document.createElement('div');
      arrow.className = 'workflow-arrow';
      arrow.innerHTML = createArrowSVG(1.0); // Start with full arrow visible
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
    { action: 'test_ssh', label: '🔧 Test SSH Connection', onclick: 'testVastAISSH()' },
    { action: 'sync_instance', label: '🔄 Sync Instance', onclick: 'syncFromConnectionString()' }
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
    
    if (step.action === 'test_ssh') {
      stepButton.onclick = testVastAISSH;
    } else if (step.action === 'sync_instance') {
      stepButton.onclick = syncFromConnectionString;
    }
    
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
      arrow.className = 'workflow-arrow';
      arrow.textContent = '↓';
      container.appendChild(arrow);
    }
  });
}

// Initialize workflow system when loaded
console.log('📄 Workflow module loaded');
