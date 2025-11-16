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
      } else {
        // Mark step as failed
        stepElement.classList.add('failed');
        console.log(`❌ Step ${i + 1} failed: ${action}`);
        showSetupResult(`Workflow failed at step: ${stepButton.textContent.trim()}`, 'error');
        break; // Stop workflow on failure
      }
      
      // Wait between steps (except after the last step)
      if (i < stepElements.length - 1 && !workflowCancelled) {
        console.log(`⏳ Waiting ${workflowConfig.stepDelay / 1000} seconds before next step...`);
        showSetupResult(`Waiting ${workflowConfig.stepDelay / 1000} seconds before next step...`, 'info');
        await sleep(workflowConfig.stepDelay);
      }
    }
    
    if (!workflowCancelled) {
      showSetupResult('✅ Workflow completed successfully!', 'success');
    }
  } catch (error) {
    console.error('❌ Workflow error:', error);
    showSetupResult(`Workflow error: ${error.message}`, 'error');
  } finally {
    // Reset UI state
    workflowRunning = false;
    workflowCancelled = false;
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
        
        // If no result is received within 30 seconds, consider it a success
        // (for steps that don't emit events)
        setTimeout(() => {
          if (!resultReceived) {
            document.removeEventListener('stepExecutionComplete', resultListener);
            resolve(true);
          }
        }, 30000);
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
        stepButton.onclick = () => executeTemplateStep('Install CivitDL');
        break;
      case 'set_ui_home':
        stepButton.onclick = () => executeTemplateStep('Set UI Home');
        break;
      case 'setup_python_venv':
        stepButton.onclick = () => executeTemplateStep('Setup Python Virtual Environment');
        break;
      case 'clone_auto_installer':
        stepButton.onclick = () => executeTemplateStep('Clone ComfyUI Auto Installer');
        break;
      case 'get_ui_home':
        stepButton.onclick = getUIHome;
        break;
      case 'terminate_connection':
        stepButton.onclick = terminateConnection;
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
      arrow.textContent = '↓';
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
