// ==============================
// VastAI Templates Module
// ==============================
// Template management, button generation, and template execution

import { showSetupResult } from './ui.js';
import { testVastAISSH, setUIHome, getUIHome, terminateConnection, setupCivitDL, syncFromConnectionString } from './instances.js';

// Template state
let currentTemplate = null;
let availableTemplates = [];

/**
 * Load templates from API
 */
export async function loadTemplates() {
  try {
    const data = await api.get('/templates');
    
    if (data.success) {
      availableTemplates = data.templates;
      populateTemplateSelector();
    } else {
      console.error('Failed to load templates:', data.message);
      showTemplateError('Failed to load templates');
    }
  } catch (error) {
    console.error('Error loading templates:', error);
    showTemplateError('Error loading templates');
  }
}

/**
 * Populate template selector dropdown
 */
function populateTemplateSelector() {
  const selector = document.getElementById('templateSelector');
  if (!selector) return;
  
  // Clear existing options
  selector.innerHTML = '<option value="">Select a template...</option>';
  
  // Add template options
  availableTemplates.forEach(template => {
    const option = document.createElement('option');
    option.value = template.id;
    option.textContent = `${template.name} (${template.version})`;
    option.title = template.description;
    selector.appendChild(option);
  });
  
  // If only one template available, select it automatically
  if (availableTemplates.length === 1) {
    selector.value = availableTemplates[0].id;
    onTemplateChange();
  }
}

/**
 * Show template error in selector
 * @param {string} message - Error message to display
 */
function showTemplateError(message) {
  const selector = document.getElementById('templateSelector');
  if (selector) {
    selector.innerHTML = `<option value="">❌ ${message}</option>`;
  }
}

/**
 * Handle template selection change
 */
export async function onTemplateChange() {
  console.log(`🎛️ onTemplateChange called`);
  const selector = document.getElementById('templateSelector');
  const templateId = selector?.value;
  
  console.log(`📋 Template ID selected: "${templateId}"`);
  console.log(`📍 Template selector exists:`, !!selector);
  
  if (!templateId) {
    console.log(`❌ No template ID, resetting buttons`);
    currentTemplate = null;
    hideTemplateInfo();
    resetSetupButtons();
    return;
  }
  
  try {
    console.log(`🔄 Loading template: ${templateId}`);
    const data = await api.get(`/templates/${templateId}`);
    console.log(`📦 Template API response:`, data);
    
    if (data.success) {
      currentTemplate = data.template;
      console.log(`✅ Template loaded successfully:`, currentTemplate);
      showTemplateInfo(currentTemplate);
      updateSetupButtons(currentTemplate);
      console.log(`🔧 Template buttons updated`);
    } else {
      console.log(`❌ Template loading failed:`, data.message);
      currentTemplate = null;
      showSetupResult(`Failed to load template: ${data.message}`, 'error');
      hideTemplateInfo();
      resetSetupButtons();
    }
  } catch (error) {
    console.log(`🚨 Template loading error:`, error);
    currentTemplate = null;
    showSetupResult(`Error loading template: ${error.message}`, 'error');
    hideTemplateInfo();
    resetSetupButtons();
  }
}

/**
 * Show template information
 * @param {object} template - Template object to display
 */
function showTemplateInfo(template) {
  const infoDiv = document.getElementById('template-info');
  const nameSpan = document.getElementById('template-name');
  const descSpan = document.getElementById('template-description');
  
  if (infoDiv && nameSpan && descSpan) {
    nameSpan.textContent = `${template.name} v${template.version || '1.0.0'}`;
    descSpan.textContent = template.description || 'No description available';
    infoDiv.style.display = 'block';
  }
}

/**
 * Hide template information
 */
function hideTemplateInfo() {
  const infoDiv = document.getElementById('template-info');
  if (infoDiv) {
    infoDiv.style.display = 'none';
  }
}

/**
 * Update setup buttons based on template
 * @param {object} template - Template object containing button configuration
 */
function updateSetupButtons(template) {
  // Use the new workflow UI instead
  if (typeof updateWorkflowSteps === 'function') {
    updateWorkflowSteps(template);
    return;
  }
  
  // Fallback to old button container if workflow module not loaded
  const container = document.getElementById('setup-buttons-container');
  if (!container) return;
  
  const uiConfig = template.ui_config || {};
  const buttons = uiConfig.setup_buttons || [];
  
  // Clear existing buttons
  container.innerHTML = '';
  
  // Always include basic buttons first
  const testSSHBtn = document.createElement('button');
  testSSHBtn.className = 'setup-button';
  testSSHBtn.textContent = '🔧 Test SSH Connection';
  testSSHBtn.onclick = testVastAISSH;
  container.appendChild(testSSHBtn);
  
  const syncBtn = document.createElement('button');
  syncBtn.className = 'setup-button';
  syncBtn.textContent = '🔄 Sync Instance';
  syncBtn.onclick = syncFromConnectionString;
  container.appendChild(syncBtn);
  
  // Add template-specific buttons
  console.log(`🔧 Adding ${buttons.length} template buttons`);
  buttons.forEach((button, index) => {
    if (button.action !== 'test_ssh' && button.action !== 'sync_instance') {
      const btnElement = document.createElement('button');
      btnElement.className = getButtonClass(button.style);
      btnElement.textContent = button.label;
      
      // Set onclick handler based on action
      switch (button.action) {
        case 'setup_civitdl':
          btnElement.onclick = () => {
            console.log('🎨 Setup CivitDL button clicked');
            executeTemplateStep('Install CivitDL');
          };
          break;
        case 'set_ui_home':
          btnElement.onclick = () => {
            console.log('📁 Set UI Home button clicked');
            executeTemplateStep('Set UI Home');
          };
          break;
        case 'install_browser_agent':
          btnElement.onclick = () => {
            console.log('🌐 Install BrowserAgent button clicked');
            console.log('  Action:', button.action);
            console.log('  Step name: Install BrowserAgent');
            executeTemplateStep('Install BrowserAgent');
          };
          break;
        case 'setup_python_venv':
          btnElement.onclick = () => {
            console.log('🐍 Setup Python venv button clicked');
            executeTemplateStep('Setup Python Virtual Environment');
          };
          break;
        case 'clone_auto_installer':
          btnElement.onclick = () => {
            console.log('🔗 Clone auto-installer button clicked');
            executeTemplateStep('Clone ComfyUI Auto Installer');
          };
          break;
        case 'get_ui_home':
          btnElement.onclick = () => {
            console.log('📍 Get UI Home button clicked');
            getUIHome();
          };
          break;
        case 'terminate_connection':
          btnElement.onclick = () => {
            console.log('🔌 Terminate connection button clicked');
            terminateConnection();
          };
          break;
        default:
          btnElement.onclick = () => console.log(`❌ Unknown action: ${button.action}`);
      }
      
      console.log(`  ${index+1}. Creating button: "${button.label}" (${button.action})`);
      container.appendChild(btnElement);
    }
  });
  
  console.log(`✅ Template buttons created. Total buttons:`, container.children.length);
}

/**
 * Reset setup buttons to defaults
 */
function resetSetupButtons() {
  // Use the new workflow UI instead
  if (typeof resetWorkflowSteps === 'function') {
    resetWorkflowSteps();
    return;
  }
  
  // Fallback to old button container if workflow module not loaded
  const container = document.getElementById('setup-buttons-container');
  if (container) {
    container.innerHTML = '';
    
    const testSSHBtn = document.createElement('button');
    testSSHBtn.className = 'setup-button';
    testSSHBtn.textContent = '🔧 Test SSH Connection';
    testSSHBtn.onclick = testVastAISSH;
    container.appendChild(testSSHBtn);
    
    const syncBtn = document.createElement('button');
    syncBtn.className = 'setup-button';
    syncBtn.textContent = '🔄 Sync Instance';
    syncBtn.onclick = syncFromConnectionString;
    container.appendChild(syncBtn);
  }
}

/**
 * Get button CSS class based on style
 * @param {string} style - Button style identifier
 * @returns {string} CSS class name
 */
function getButtonClass(style) {
  switch (style) {
    case 'primary': return 'setup-button';
    case 'secondary': return 'setup-button secondary';
    case 'danger': return 'setup-button danger';
    default: return 'setup-button';
  }
}

/**
 * Execute a template step
 * @param {string} stepName - Name of the step to execute
 */
export async function executeTemplateStep(stepName) {
  // Enhanced debugging for template execution
  console.log(`🔧 executeTemplateStep called with: "${stepName}"`);
  
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  const templateId = document.getElementById('templateSelector')?.value;
  
  console.log(`🔗 SSH Connection String: "${sshConnectionString}"`);
  console.log(`🎛️ Template ID: "${templateId}"`);
  console.log(`📋 Current Template:`, currentTemplate);
  console.log(`📍 SSH Element exists:`, !!document.getElementById('sshConnectionString'));
  console.log(`📍 Template Selector exists:`, !!document.getElementById('templateSelector'));
  
  if (!sshConnectionString) {
    console.log(`❌ No SSH connection string provided`);
    showSetupResult('Please enter an SSH connection string first.', 'error');
    return;
  }
  
  if (!templateId || !currentTemplate) {
    console.log(`❌ Template validation failed - templateId: "${templateId}", currentTemplate:`, currentTemplate);
    showSetupResult('Please select a template first.', 'error');
    return;
  }
  
  console.log(`✅ All validations passed, executing template step...`);
  console.log(`📤 POST /templates/${templateId}/execute-step`);
  console.log(`   Request data:`, { ssh_connection: sshConnectionString, step_name: stepName });
  showSetupResult(`Executing: ${stepName}...`, 'info');
  
  try {
    console.log(`⏳ Sending API request...`);
    const data = await api.post(`/templates/${templateId}/execute-step`, {
      ssh_connection: sshConnectionString,
      step_name: stepName
    });
    
    console.log(`📥 API response received:`, data);
    console.log(`   success: ${data.success}`);
    console.log(`   message: ${data.message}`);
    
    if (data.success) {
      console.log(`✅ ${stepName} completed successfully!`);
      showSetupResult(`✅ ${stepName} completed successfully!`, 'success');
      if (data.output) {
        console.log(`📄 ${stepName} output:`);
        console.log(data.output);
      }
    } else {
      console.log(`❌ ${stepName} failed:`, data.message);
      let errorMsg = `❌ ${stepName} failed: ${data.message}`;
      if (data.error) {
        console.log(`   Error details:`, data.error);
        errorMsg += `\n\nDetails: ${data.error}`;
      }
      showSetupResult(errorMsg, 'error');
    }
  } catch (error) {
    console.error(`💥 Exception during ${stepName}:`, error);
    console.error(`   Error type: ${error.constructor.name}`);
    console.error(`   Error message: ${error.message}`);
    if (error.response) {
      console.error(`   Response status: ${error.response.status}`);
      console.error(`   Response data:`, error.response.data);
    }
    showSetupResult(`❌ ${stepName} request failed: ${error.message}`, 'error');
  }
}

/**
 * Debug function to manually test template functionality
 */
export function debugTemplateState() {
  console.log('🔧 TEMPLATE DEBUG STATE');
  console.log('========================');
  
  const sshElement = document.getElementById('sshConnectionString');
  const templateElement = document.getElementById('templateSelector');
  // setup-result element removed
  const buttonsContainer = document.getElementById('setup-buttons-container');
  
  console.log('📍 Elements:');
  console.log('  - SSH Input:', !!sshElement, sshElement?.value);
  console.log('  - Template Select:', !!templateElement, templateElement?.value);
  console.log('  - Buttons Container:', !!buttonsContainer);
  
  console.log('📋 State:');
  console.log('  - currentTemplate:', currentTemplate);
  
  if (currentTemplate && currentTemplate.ui_config) {
    console.log('🔧 Template Buttons:');
    const buttons = currentTemplate.ui_config.setup_buttons || [];
    buttons.forEach((btn, i) => {
      console.log(`  ${i+1}. ${btn.label} (${btn.action})`);
    });
  }
  
  if (buttonsContainer) {
    console.log('🎯 Actual DOM Buttons:');
    const domButtons = buttonsContainer.querySelectorAll('button');
    domButtons.forEach((btn, i) => {
      console.log(`  ${i+1}. "${btn.textContent.trim()}" onclick="${btn.onclick || btn.getAttribute('onclick')}"`);
    });
  }
  
  console.log('🧪 Test executeTemplateStep:');
  if (sshElement?.value && templateElement?.value && currentTemplate) {
    console.log('  ✅ Ready to test - all requirements met');
  } else {
    console.log('  ❌ Not ready:');
    if (!sshElement?.value) console.log('    - Missing SSH connection');
    if (!templateElement?.value) console.log('    - Missing template selection');  
    if (!currentTemplate) console.log('    - currentTemplate not loaded');
  }
  
  return {
    sshConnection: sshElement?.value,
    templateId: templateElement?.value,
    currentTemplate: currentTemplate,
    buttonCount: buttonsContainer?.querySelectorAll('button').length || 0,
    ready: !!(sshElement?.value && templateElement?.value && currentTemplate)
  };
}

/**
 * Test function to simulate button click
 */
export function testSetUIHomeButton() {
  console.log('🧪 Testing Set UI Home button click...');
  const buttonsContainer = document.getElementById('setup-buttons-container');
  if (buttonsContainer) {
    console.log('🔍 Inspecting all buttons in container:');
    const allButtons = Array.from(buttonsContainer.querySelectorAll('button'));
    allButtons.forEach((btn, i) => {
      console.log(`  ${i+1}. "${btn.textContent.trim()}" 
        - onclick property: ${typeof btn.onclick}
        - onclick attribute: "${btn.getAttribute('onclick')}"
        - class: "${btn.className}"`);
    });
    
    const setUIHomeButton = allButtons.find(btn => 
      btn.textContent.includes('Set UI_HOME') || 
      btn.textContent.includes('📁 Set UI_HOME') ||
      btn.textContent.includes('Set UI Home')
    );
    
    if (setUIHomeButton) {
      console.log('✅ Found Set UI_HOME button, simulating click...');
      console.log('Button details:', {
        textContent: setUIHomeButton.textContent.trim(),
        onclick: typeof setUIHomeButton.onclick,
        onclickAttr: setUIHomeButton.getAttribute('onclick'),
        className: setUIHomeButton.className
      });
      
      // Try to call the onclick handler directly
      if (typeof setUIHomeButton.onclick === 'function') {
        console.log('🎯 Calling onclick handler directly...');
        setUIHomeButton.onclick();
      } else {
        console.log('❌ No onclick handler found, trying click() event...');
        setUIHomeButton.click();
      }
    } else {
      console.log('❌ Set UI_HOME button not found in DOM');
      console.log('Available buttons:', allButtons.map(btn => btn.textContent.trim()));
    }
  } else {
    console.log('❌ Buttons container not found');
  }
}

/**
 * Debug function to check button generation
 */
export function debugButtonGeneration() {
  console.log('🔧 BUTTON GENERATION DEBUG');
  console.log('==========================');
  
  const container = document.getElementById('setup-buttons-container');
  const templateSelect = document.getElementById('templateSelector');
  
  console.log('Container exists:', !!container);
  console.log('Template selector exists:', !!templateSelect);
  console.log('Template selector value:', templateSelect?.value);
  console.log('Current template:', currentTemplate);
  
  if (container) {
    console.log('Container children count:', container.children.length);
    
    if (currentTemplate && currentTemplate.ui_config) {
      console.log('Expected template buttons:');
      const buttons = currentTemplate.ui_config.setup_buttons || [];
      buttons.forEach((btn, i) => {
        console.log(`  ${i+1}. ${btn.label} (${btn.action})`);
      });
      
      console.log('Calling updateSetupButtons manually...');
      updateSetupButtons(currentTemplate);
    }
  }
}

// Get current template (for debugging)
export function getCurrentTemplate() {
  return currentTemplate;
}

// Get available templates (for debugging)
export function getAvailableTemplates() {
  return availableTemplates;
}

console.log('📄 VastAI Templates module loaded');