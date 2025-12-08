/**
 * Create Tab - Main Controller
 * Orchestrates workflow selection, form generation, and execution
 * Supports extensible component architecture driven by *.webui.yml definitions
 */

import { ExecutionQueue } from './components/ExecutionQueue.js';

// Create Tab state
const CreateTabState = {
    workflows: [],
    selectedWorkflow: null,
    workflowDetails: null,
    formValues: {},
    isExecuting: false,
    taskId: null,
    // Store component instances for cleanup and value retrieval
    componentInstances: new Map(),
    // Current SSH connection
    sshConnection: null,
    // Execution queue component
    executionQueue: null
};

/**
 * Initialize the Create tab
 */
async function initCreateTab() {
    console.log('🎨 Initializing Create tab...');
    
    try {
        // Initialize ExecutionQueue component
        CreateTabState.executionQueue = new ExecutionQueue('execution-queue-content', null);
        
        // Expose globally for onclick handlers
        window.executionQueueInstance = CreateTabState.executionQueue;
    } catch (error) {
        console.error('Error initializing ExecutionQueue:', error);
    }
    
    // Load workflows
    try {
        await loadWorkflows();
        console.log('✅ Workflows loaded successfully');
    } catch (error) {
        console.error('❌ Failed to load workflows:', error);
        const container = document.getElementById('create-workflows-grid');
        if (container) {
            container.innerHTML = `<div class="create-empty-state"><div class="create-empty-state-icon">❌</div><div class="create-empty-state-title">Initialization Error</div><div class="create-empty-state-description">${error.message}</div></div>`;
        }
    }
    
    // Set up event listeners
    setupCreateTabEventListeners();
    
    // Check if SSH connection already exists (from new toolbar) and initialize ExecutionQueue
    const sshConnection = getCurrentSSHConnection();
    if (sshConnection) {
        CreateTabState.sshConnection = sshConnection;
        if (CreateTabState.executionQueue) {
            CreateTabState.executionQueue.setSshConnection(sshConnection);
        }
    }
    
    console.log('✅ Create tab initialized');
}

/**
 * Load available workflows from the API
 */
async function loadWorkflows() {
    console.log('📋 Loading workflows from API...');
    const container = document.getElementById('create-workflows-grid');
    if (!container) {
        console.error('❌ create-workflows-grid container not found');
        return;
    }
    
    container.innerHTML = '<div class="create-empty-state"><div class="create-empty-state-icon">⏳</div><div class="create-empty-state-description">Loading workflows...</div></div>';
    
    try {
        console.log('📡 Fetching /create/workflows/list...');
        const response = await fetch('/create/workflows/list');
        console.log('📡 Response status:', response.status);
        const data = await response.json();
        console.log('📋 Workflows data:', data);
        
        if (data.success && data.workflows) {
            console.log(`✅ Loaded ${data.workflows.length} workflow(s)`);
            CreateTabState.workflows = data.workflows;
            renderWorkflowGrid(data.workflows);
        } else {
            console.error('⚠️ API returned error:', data.message);
            container.innerHTML = `<div class="create-empty-state"><div class="create-empty-state-icon">⚠️</div><div class="create-empty-state-title">Error Loading Workflows</div><div class="create-empty-state-description">${data.message || 'Unknown error'}</div></div>`;
        }
    } catch (error) {
        console.error('❌ Error loading workflows:', error);
        container.innerHTML = `<div class="create-empty-state"><div class="create-empty-state-icon">❌</div><div class="create-empty-state-title">Connection Error</div><div class="create-empty-state-description">${error.message}</div></div>`;
    }
}

/**
 * Render the workflow grid
 * @param {Array} workflows - Array of workflow objects
 */
function renderWorkflowGrid(workflows) {
    const container = document.getElementById('create-workflows-grid');
    if (!container) return;
    
    if (!workflows || workflows.length === 0) {
        container.innerHTML = '<div class="create-empty-state"><div class="create-empty-state-icon">📭</div><div class="create-empty-state-title">No Workflows Available</div><div class="create-empty-state-description">No workflow definitions found in the workflows directory.</div></div>';
        return;
    }
    
    container.innerHTML = workflows.map(workflow => `
        <div class="workflow-card" data-workflow-id="${escapeHtml(workflow.id)}" onclick="selectWorkflow('${escapeHtml(workflow.id)}')">
            <div class="workflow-card-header">
                <span class="workflow-card-icon">${workflow.icon || '⚙️'}</span>
                <span class="workflow-card-title">${escapeHtml(workflow.name)}</span>
            </div>
            <div class="workflow-card-description">${escapeHtml(workflow.description || '')}</div>
            <div class="workflow-card-meta">
                <span class="workflow-tag category">${escapeHtml(workflow.category || 'other')}</span>
                ${workflow.vram_estimate ? `<span class="workflow-tag">🎮 ${escapeHtml(workflow.vram_estimate)}</span>` : ''}
                ${(workflow.tags || []).slice(0, 2).map(tag => `<span class="workflow-tag">${escapeHtml(tag)}</span>`).join('')}
            </div>
        </div>
    `).join('');
}

/**
 * Select a workflow and load its details
 * @param {string} workflowId - The workflow ID to select
 */
async function selectWorkflow(workflowId) {
    // Update selection UI
    document.querySelectorAll('.workflow-card').forEach(card => {
        card.classList.remove('selected');
        if (card.dataset.workflowId === workflowId) {
            card.classList.add('selected');
        }
    });
    
    CreateTabState.selectedWorkflow = workflowId;
    
    // Clean up previous components
    cleanupComponents();
    
    // Show loading state in form container
    const formContainer = document.getElementById('create-form-container');
    if (formContainer) {
        formContainer.innerHTML = '<div class="create-empty-state"><div class="create-empty-state-icon">⏳</div><div class="create-empty-state-description">Loading workflow configuration...</div></div>';
        formContainer.style.display = 'block';
    }
    
    try {
        const response = await fetch(`/create/workflows/${encodeURIComponent(workflowId)}`);
        const data = await response.json();
        
        if (data.success && data.workflow) {
            CreateTabState.workflowDetails = data.workflow;
            CreateTabState.formValues = {};
            
            // Use section-based layout if workflow defines it
            if (data.workflow.layout && data.workflow.layout.sections) {
                renderWorkflowFormWithSections(data.workflow);
            } else {
                renderWorkflowForm(data.workflow);
            }
            showExecuteSection(true);
        } else {
            if (formContainer) {
                formContainer.innerHTML = `<div class="create-empty-state"><div class="create-empty-state-icon">⚠️</div><div class="create-empty-state-title">Error</div><div class="create-empty-state-description">${data.message || 'Failed to load workflow'}</div></div>`;
            }
        }
    } catch (error) {
        console.error('Error loading workflow:', error);
        if (formContainer) {
            formContainer.innerHTML = `<div class="create-empty-state"><div class="create-empty-state-icon">❌</div><div class="create-empty-state-title">Error</div><div class="create-empty-state-description">${error.message}</div></div>`;
        }
    }
}

/**
 * Render the workflow configuration form
 * @param {Object} workflow - Workflow details object
 */
function renderWorkflowForm(workflow) {
    const formContainer = document.getElementById('create-form-container');
    if (!formContainer) return;
    
    let html = '';
    
    // Workflow info header
    html += `
        <div class="create-form-section">
            <h3 style="margin: 0 0 var(--size-4-2) 0;">${escapeHtml(workflow.name)}</h3>
            <p style="margin: 0; color: var(--text-muted);">${escapeHtml(workflow.description)}</p>
        </div>
    `;
    
    // Main inputs
    if (workflow.inputs && workflow.inputs.length > 0) {
        html += `
            <div class="create-form-section">
                <div class="create-form-section-header">
                    <h4 class="create-form-section-title">📝 Inputs</h4>
                </div>
                <div class="create-form-section-content">
                    ${workflow.inputs.map(input => renderFormField(input)).join('')}
                </div>
            </div>
        `;
    }
    
    // Advanced settings (collapsed by default)
    if (workflow.advanced && workflow.advanced.length > 0) {
        html += `
            <div class="create-form-section">
                <div class="create-form-section-header">
                    <h4 class="create-form-section-title">🔧 Advanced Settings</h4>
                    <button class="create-form-section-toggle collapsed" onclick="toggleAdvancedSection(this)">▼</button>
                </div>
                <div class="create-form-section-content collapsed" id="advanced-section-content">
                    ${workflow.advanced.map(input => renderFormField(input)).join('')}
                </div>
            </div>
        `;
    }
    
    formContainer.innerHTML = html;
    formContainer.style.display = 'block';
    
    // Initialize form values with defaults
    initializeFormDefaults(workflow);
}

/**
 * Render a single form field based on type
 * Supports both simple HTML-rendered fields and complex component-based fields
 * @param {Object} field - Field definition from webui.yml
 * @returns {string|HTMLElement} HTML string or DOM element
 */
function renderFormField(field) {
    const id = `create-field-${field.id}`;
    const requiredClass = field.required ? 'required' : '';
    const description = field.description ? `<div class="field-description">${escapeHtml(field.description)}</div>` : '';
    
    // Check for advanced component types that need JavaScript components
    if (isAdvancedComponentType(field.type)) {
        return renderAdvancedComponent(field);
    }
    
    let inputHtml = '';
    
    switch (field.type) {
        case 'image':
            inputHtml = `
                <div class="image-upload-container" id="${id}-container">
                    <input type="file" id="${id}" accept="${field.accept || 'image/*'}" onchange="handleImageUpload('${field.id}', this)">
                    <div class="image-upload-icon">📷</div>
                    <div class="image-upload-text">Click or drag to upload image</div>
                </div>
            `;
            break;
            
        case 'textarea':
            inputHtml = `
                <textarea 
                    id="${id}" 
                    placeholder="${escapeHtml(field.placeholder || '')}"
                    rows="${field.rows || 4}"
                    maxlength="${field.max_length || 10000}"
                    onchange="updateFormValue('${field.id}', this.value)"
                >${escapeHtml(field.default || '')}</textarea>
            `;
            break;
            
        case 'text':
            inputHtml = `
                <input 
                    type="text" 
                    id="${id}" 
                    placeholder="${escapeHtml(field.placeholder || '')}"
                    maxlength="${field.max_length || 1000}"
                    value="${escapeHtml(field.default || '')}"
                    onchange="updateFormValue('${field.id}', this.value)"
                >
            `;
            break;
            
        case 'slider':
            const unit = field.unit ? `<span class="slider-unit">${escapeHtml(field.unit)}</span>` : '';
            inputHtml = `
                <div class="slider-container">
                    <input 
                        type="range" 
                        id="${id}" 
                        class="slider-input"
                        min="${field.min || 0}"
                        max="${field.max || 100}"
                        step="${field.step || 1}"
                        value="${field.default || field.min || 0}"
                        oninput="updateSliderValue('${field.id}', this.value)"
                    >
                    <input 
                        type="number" 
                        id="${id}-value" 
                        class="slider-value"
                        min="${field.min || 0}"
                        max="${field.max || 100}"
                        step="${field.step || 1}"
                        value="${field.default || field.min || 0}"
                        onchange="updateSliderFromInput('${field.id}', this.value)"
                    >
                    ${unit}
                </div>
            `;
            break;
            
        case 'seed':
            inputHtml = `
                <div class="seed-container">
                    <input 
                        type="number" 
                        id="${id}" 
                        class="seed-input"
                        value="${field.default || -1}"
                        onchange="updateFormValue('${field.id}', parseInt(this.value))"
                    >
                    <button type="button" class="seed-randomize" onclick="randomizeSeed('${field.id}')" title="Randomize">🎲</button>
                </div>
            `;
            break;
            
        case 'checkbox':
            inputHtml = `
                <div class="checkbox-field-container">
                    <input 
                        type="checkbox" 
                        id="${id}" 
                        ${field.default ? 'checked' : ''}
                        onchange="updateFormValue('${field.id}', this.checked)"
                    >
                    <label for="${id}" class="checkbox-field-label">${escapeHtml(field.label)}</label>
                </div>
            `;
            // Don't show the label twice for checkboxes
            return `<div class="create-form-field">${description}${inputHtml}</div>`;
            
        case 'select':
            inputHtml = `
                <select id="${id}" onchange="updateFormValue('${field.id}', this.value)">
                    ${(field.options || []).map(opt => `
                        <option value="${escapeHtml(opt.value || opt)}" ${(opt.value || opt) === field.default ? 'selected' : ''}>
                            ${escapeHtml(opt.label || opt)}
                        </option>
                    `).join('')}
                </select>
            `;
            break;
            
        default:
            inputHtml = `<input type="text" id="${id}" value="${escapeHtml(field.default || '')}">`;
    }
    
    return `
        <div class="create-form-field" data-field-id="${field.id}">
            <label for="${id}" class="${requiredClass}">${escapeHtml(field.label)}</label>
            ${description}
            ${inputHtml}
        </div>
    `;
}

/**
 * Initialize form values with defaults from workflow
 * @param {Object} workflow - Workflow details
 */
function initializeFormDefaults(workflow) {
    const allFields = [...(workflow.inputs || []), ...(workflow.advanced || [])];
    
    allFields.forEach(field => {
        if (field.default !== undefined) {
            CreateTabState.formValues[field.id] = field.default;
        }
    });
}

/**
 * Update a form value
 * @param {string} fieldId - Field ID
 * @param {any} value - New value
 */
function updateFormValue(fieldId, value) {
    CreateTabState.formValues[fieldId] = value;
    console.log(`Updated ${fieldId}:`, value);
}

/**
 * Update slider value from range input
 * @param {string} fieldId - Field ID
 * @param {string} value - New value
 */
function updateSliderValue(fieldId, value) {
    const valueInput = document.getElementById(`create-field-${fieldId}-value`);
    if (valueInput) {
        valueInput.value = value;
    }
    updateFormValue(fieldId, parseFloat(value));
}

/**
 * Update slider from number input
 * @param {string} fieldId - Field ID
 * @param {string} value - New value
 */
function updateSliderFromInput(fieldId, value) {
    const slider = document.getElementById(`create-field-${fieldId}`);
    if (slider) {
        slider.value = value;
    }
    updateFormValue(fieldId, parseFloat(value));
}

/**
 * Randomize a seed value
 * @param {string} fieldId - Field ID
 */
function randomizeSeed(fieldId) {
    const input = document.getElementById(`create-field-${fieldId}`);
    if (input) {
        // Use a safe maximum that matches backend range (2^53 - 1 is JS safe integer max)
        const randomSeed = Math.floor(Math.random() * Number.MAX_SAFE_INTEGER);
        input.value = randomSeed;
        updateFormValue(fieldId, randomSeed);
    }
}

/**
 * Handle image upload
 * @param {string} fieldId - Field ID
 * @param {HTMLInputElement} input - File input element
 */
function handleImageUpload(fieldId, input) {
    const file = input.files[0];
    if (!file) return;
    
    // Validate file is actually an image
    if (!file.type.startsWith('image/')) {
        console.warn('Invalid file type:', file.type);
        return;
    }
    
    const container = document.getElementById(`create-field-${fieldId}-container`);
    if (!container) return;
    
    // Show preview using DOM methods for security
    const reader = new FileReader();
    reader.onload = function(e) {
        // Clear container safely
        container.innerHTML = '';
        
        // Create file input
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.id = `create-field-${fieldId}`;
        fileInput.accept = input.accept || 'image/*';
        fileInput.addEventListener('change', function() {
            handleImageUpload(fieldId, this);
        });
        
        // Create preview image
        const img = document.createElement('img');
        img.src = e.target.result;
        img.className = 'image-upload-preview';
        img.alt = 'Preview';
        
        // Create clear button
        const clearBtn = document.createElement('button');
        clearBtn.type = 'button';
        clearBtn.className = 'image-upload-clear';
        clearBtn.title = 'Remove';
        clearBtn.textContent = '✕';
        clearBtn.addEventListener('click', function(e) {
            e.stopPropagation(); // Prevent triggering container click
            clearImageUpload(fieldId);
        });
        
        container.appendChild(fileInput);
        container.appendChild(img);
        container.appendChild(clearBtn);
        container.classList.add('has-image');
        
        // Re-add click handler to container to allow changing the image
        container.onclick = function(e) {
            // Don't trigger if clicking the clear button
            if (e.target === clearBtn || e.target.closest('.image-upload-clear')) {
                return;
            }
            fileInput.click();
        };
        
        // Store base64 data
        updateFormValue(fieldId, e.target.result);
    };
    reader.readAsDataURL(file);
}

/**
 * Clear image upload
 * @param {string} fieldId - Field ID
 */
function clearImageUpload(fieldId) {
    const container = document.getElementById(`create-field-${fieldId}-container`);
    if (!container) return;
    
    container.innerHTML = `
        <input type="file" id="create-field-${fieldId}" accept="image/*" onchange="handleImageUpload('${fieldId}', this)">
        <div class="image-upload-icon">📷</div>
        <div class="image-upload-text">Click or drag to upload image</div>
    `;
    container.classList.remove('has-image');
    
    // Re-add click handler to container
    container.onclick = function() {
        document.getElementById(`create-field-${fieldId}`).click();
    };
    
    updateFormValue(fieldId, null);
}

/**
 * Apply a preset to the form
 * @param {number} presetIndex - Index of the preset
 */
/**
 * Toggle advanced section visibility
 * @param {HTMLElement} button - Toggle button element
 */
function toggleAdvancedSection(button) {
    const content = document.getElementById('advanced-section-content');
    if (!content) return;
    
    const isCollapsed = content.classList.contains('collapsed');
    content.classList.toggle('collapsed');
    button.classList.toggle('collapsed');
    button.textContent = isCollapsed ? '▲' : '▼';
}

/**
 * Show or hide the execute section
 * @param {boolean} show - Whether to show
 */
function showExecuteSection(show) {
    const section = document.getElementById('create-execute-section');
    if (section) {
        section.style.display = show ? 'block' : 'none';
    }
    
    // Update connection notice visibility based on current connection state
    if (show) {
        updateConnectionNotice();
    }
}

/**
 * Update connection notice visibility based on toolbar connection state
 */
function updateConnectionNotice() {
    const notice = document.getElementById('create-connection-notice');
    if (!notice) return;
    
    const sshConnection = getCurrentSSHConnection();
    
    // Show notice only if no connection
    notice.style.display = sshConnection ? 'none' : 'block';
}

/**
 * Execute the current workflow
 */
async function executeWorkflow() {
    if (CreateTabState.isExecuting) return;
    
    const workflowId = CreateTabState.selectedWorkflow;
    if (!workflowId) {
        showCreateError('Please select a workflow first');
        return;
    }
    
    // Get SSH connection string from toolbar (or fallback to legacy inputs)
    const sshConnection = getCurrentSSHConnection();
    
    if (!sshConnection) {
        showCreateError('Please connect to an instance using the connection toolbar above');
        // Show connection notice
        const notice = document.getElementById('create-connection-notice');
        if (notice) {
            notice.style.display = 'block';
            // Hide notice after 5 seconds
            setTimeout(() => {
                notice.style.display = 'none';
            }, 5000);
        }
        return;
    }
    
    // Validate required fields
    const workflow = CreateTabState.workflowDetails;
    if (workflow && workflow.inputs) {
        for (const field of workflow.inputs) {
            if (field.required && !CreateTabState.formValues[field.id]) {
                showCreateError(`Please fill in required field: ${field.label}`);
                return;
            }
        }
    }
    
    CreateTabState.isExecuting = true;
    updateExecuteButton(true);
    
    try {
        const response = await fetch('/create/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ssh_connection: sshConnection,
                workflow_id: workflowId,
                inputs: CreateTabState.formValues
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            CreateTabState.taskId = data.task_id;
            showCreateSuccess(`Workflow queued successfully! Task ID: ${data.task_id}`);
            // TODO: Start polling for status
        } else {
            showCreateError(data.message || 'Failed to execute workflow');
        }
    } catch (error) {
        console.error('Error executing workflow:', error);
        showCreateError(`Error: ${error.message}`);
    } finally {
        CreateTabState.isExecuting = false;
        updateExecuteButton(false);
    }
}

/**
 * Update execute button state
 * @param {boolean} executing - Whether currently executing
 */
function updateExecuteButton(executing) {
    const button = document.getElementById('create-execute-button');
    if (!button) return;
    
    if (executing) {
        button.classList.add('executing');
        button.innerHTML = '<span>⏳</span> Executing...';
        button.disabled = true;
    } else {
        button.classList.remove('executing');
        button.innerHTML = '<span>▶️</span> Run Workflow';
        button.disabled = false;
    }
}

/**
 * Show error message
 * @param {string} message - Error message
 */
function showCreateError(message) {
    const result = document.getElementById('create-result');
    if (result) {
        result.className = 'setup-result error';
        result.textContent = `❌ ${message}`;
        result.style.display = 'block';
    }
}

/**
 * Show success message
 * @param {string} message - Success message
 */
function showCreateSuccess(message) {
    const result = document.getElementById('create-result');
    if (result) {
        result.className = 'setup-result success';
        result.textContent = `✅ ${message}`;
        result.style.display = 'block';
    }
}

/**
 * Set up event listeners for Create tab
 */
function setupCreateTabEventListeners() {
    // Monitor connection toolbar state changes
    // Poll for connection changes every 2 seconds to update components
    let lastKnownConnection = getCurrentSSHConnection();
    
    setInterval(() => {
        const currentConnection = getCurrentSSHConnection();
        
        // If connection changed, update all components
        if (currentConnection !== lastKnownConnection) {
            console.log('🔄 SSH connection changed in toolbar, updating Create tab components...');
            lastKnownConnection = currentConnection;
            CreateTabState.sshConnection = currentConnection;
            
            // Update connection notice visibility
            updateConnectionNotice();
            
            // Update execution queue
            if (CreateTabState.executionQueue) {
                CreateTabState.executionQueue.setSshConnection(currentConnection);
            }
            
            // Update model selector components
            if (currentConnection) {
                updateComponentsSSHConnection(currentConnection);
                // Auto-refresh model selectors with new connection
                refreshAllModelSelectors(false);
            }
        }
    }, 2000);
}

/**
 * Escape HTML to prevent XSS
 * @param {string} str - String to escape
 * @returns {string} Escaped string
 */
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// =========================================
// ADVANCED COMPONENT TYPE SUPPORT
// =========================================

/**
 * List of advanced component types that require JavaScript rendering
 */
const ADVANCED_COMPONENT_TYPES = [
    'high_low_pair_model',
    'high_low_pair_lora_list',
    'single_model',
    'feature_toggle_group'
];

/**
 * Check if a field type requires advanced component rendering
 * @param {string} type - Field type
 * @returns {boolean}
 */
function isAdvancedComponentType(type) {
    return ADVANCED_COMPONENT_TYPES.includes(type);
}

/**
 * Render an advanced component based on field type
 * @param {Object} field - Field definition from webui.yml
 * @returns {HTMLElement} DOM element for the component
 */
function renderAdvancedComponent(field) {
    const container = document.createElement('div');
    container.className = 'create-form-field advanced-component';
    container.dataset.fieldId = field.id;
    container.dataset.fieldType = field.type;

    let component = null;

    switch (field.type) {
        case 'high_low_pair_model':
            if (typeof HighLowPairModelSelector !== 'undefined') {
                component = new HighLowPairModelSelector(field, (id, value) => {
                    updateFormValue(id, value);
                });
                container.appendChild(component.render());
                CreateTabState.componentInstances.set(field.id, component);
            } else {
                container.innerHTML = `<div class="field-error">Component not loaded: HighLowPairModelSelector</div>`;
            }
            break;

        case 'high_low_pair_lora_list':
            if (typeof HighLowPairLoRASelector !== 'undefined') {
                component = new HighLowPairLoRASelector(field, (id, value) => {
                    updateFormValue(id, value);
                });
                container.appendChild(component.render());
                CreateTabState.componentInstances.set(field.id, component);
            } else {
                container.innerHTML = `<div class="field-error">Component not loaded: HighLowPairLoRASelector</div>`;
            }
            break;

        case 'single_model':
            if (typeof SingleModelSelector !== 'undefined') {
                component = new SingleModelSelector(field, (id, value) => {
                    updateFormValue(id, value);
                });
                container.appendChild(component.render());
                CreateTabState.componentInstances.set(field.id, component);
            } else {
                container.innerHTML = `<div class="field-error">Component not loaded: SingleModelSelector</div>`;
            }
            break;

        case 'feature_toggle_group':
            if (typeof FeatureToggleGroup !== 'undefined') {
                component = new FeatureToggleGroup(field, (id, value) => {
                    updateFormValue(id, value);
                });
                container.appendChild(component.render());
                CreateTabState.componentInstances.set(field.id, component);
            } else {
                container.innerHTML = `<div class="field-error">Component not loaded: FeatureToggleGroup</div>`;
            }
            break;

        default:
            container.innerHTML = `<div class="field-error">Unknown advanced component type: ${field.type}</div>`;
    }

    return container;
}

/**
 * Update SSH connection for all model selector components
 * @param {string} sshConnection - SSH connection string
 */
function updateComponentsSSHConnection(sshConnection) {
    CreateTabState.sshConnection = sshConnection;
    
    for (const [fieldId, component] of CreateTabState.componentInstances) {
        if (component && typeof component.setSSHConnection === 'function') {
            component.setSSHConnection(sshConnection);
        }
    }
}

/**
 * Refresh all model selector components
 * @param {boolean} forceRefresh - Force refresh bypassing cache
 */
async function refreshAllModelSelectors(forceRefresh = false) {
    const refreshPromises = [];
    
    for (const [fieldId, component] of CreateTabState.componentInstances) {
        if (component && typeof component.refreshModels === 'function') {
            refreshPromises.push(component.refreshModels(forceRefresh));
        }
    }
    
    await Promise.allSettled(refreshPromises);
}

/**
 * Get current SSH connection string from UI
 * Prioritizes new connection toolbar over legacy input fields
 * @returns {string|null} SSH connection string or null
 */
function getCurrentSSHConnection() {
    // Check new connection toolbar first
    if (window.VastAIConnectionToolbar) {
        const toolbarConnection = window.VastAIConnectionToolbar.getSSHConnectionString();
        if (toolbarConnection) {
            return toolbarConnection;
        }
    }
    
    // Fallback to legacy SSH input fields (for backward compatibility)
    const sshInput = document.getElementById('createSshConnectionString') || 
                     document.getElementById('sshConnectionString') ||
                     document.getElementById('resourcesSshConnectionString');
    return sshInput?.value?.trim() || null;
}

/**
 * Clean up component instances when switching workflows
 */
function cleanupComponents() {
    CreateTabState.componentInstances.clear();
}

/**
 * Render workflow form with section-based layout support
 * @param {Object} workflow - Workflow details with layout config
 */
function renderWorkflowFormWithSections(workflow) {
    const formContainer = document.getElementById('create-form-container');
    if (!formContainer) return;

    // Clear existing components
    cleanupComponents();

    // Check if workflow has section-based layout
    if (workflow.layout && workflow.layout.sections) {
        renderSectionBasedLayout(workflow, formContainer);
    } else {
        // Fall back to standard rendering
        renderWorkflowForm(workflow);
    }
}

/**
 * Render form using section-based layout from webui.yml
 * @param {Object} workflow - Workflow configuration
 * @param {HTMLElement} container - Form container element
 */
function renderSectionBasedLayout(workflow, container) {
    let html = '';
    
    // Workflow info header
    html += `
        <div class="create-form-section">
            <h3 style="margin: 0 0 var(--size-4-2) 0;">${escapeHtml(workflow.name)}</h3>
            <p style="margin: 0; color: var(--text-muted);">${escapeHtml(workflow.description)}</p>
        </div>
    `;
    
    container.innerHTML = html;

    // Build sections based on layout
    const allInputs = [...(workflow.inputs || []), ...(workflow.advanced || [])];
    const sections = workflow.layout.sections;
    
    for (const sectionConfig of sections) {
        const sectionEl = document.createElement('div');
        sectionEl.className = 'create-form-section';
        sectionEl.id = `section-${sectionConfig.id}`;
        
        // Section header
        const headerHtml = `
            <div class="create-form-section-header">
                <h4 class="create-form-section-title">${escapeHtml(sectionConfig.title)}</h4>
                <button class="create-form-section-toggle ${sectionConfig.collapsed ? 'collapsed' : ''}" 
                        onclick="toggleSection('${sectionConfig.id}')" 
                        aria-expanded="${!sectionConfig.collapsed}">
                    ${sectionConfig.collapsed ? '▶' : '▼'}
                </button>
            </div>
        `;
        sectionEl.innerHTML = headerHtml;
        
        // Section content
        const contentEl = document.createElement('div');
        contentEl.className = `create-form-section-content ${sectionConfig.collapsed ? 'collapsed' : ''}`;
        contentEl.id = `section-content-${sectionConfig.id}`;
        
        // Add inputs that belong to this section
        const sectionInputs = allInputs.filter(input => input.section === sectionConfig.id);
        
        for (const input of sectionInputs) {
            const fieldContent = renderFormField(input);
            if (typeof fieldContent === 'string') {
                contentEl.innerHTML += fieldContent;
            } else {
                contentEl.appendChild(fieldContent);
            }
        }
        
        sectionEl.appendChild(contentEl);
        container.appendChild(sectionEl);
    }
    
    // Add any inputs without a section assignment to an "Other" section
    const unassignedInputs = allInputs.filter(input => 
        !input.section || !sections.find(s => s.id === input.section)
    );
    
    if (unassignedInputs.length > 0) {
        const otherSection = document.createElement('div');
        otherSection.className = 'create-form-section';
        otherSection.innerHTML = `
            <div class="create-form-section-header">
                <h4 class="create-form-section-title">📋 Other Settings</h4>
            </div>
        `;
        
        const contentEl = document.createElement('div');
        contentEl.className = 'create-form-section-content';
        
        for (const input of unassignedInputs) {
            const fieldContent = renderFormField(input);
            if (typeof fieldContent === 'string') {
                contentEl.innerHTML += fieldContent;
            } else {
                contentEl.appendChild(fieldContent);
            }
        }
        
        otherSection.appendChild(contentEl);
        container.appendChild(otherSection);
    }
    
    container.style.display = 'block';
    
    // Initialize form values with defaults
    initializeFormDefaults(workflow);
    
    // Update SSH connection for components
    const sshConnection = getCurrentSSHConnection();
    if (sshConnection) {
        updateComponentsSSHConnection(sshConnection);
        // Auto-refresh model selectors
        refreshAllModelSelectors(false);
    }
}

/**
 * Toggle a section's collapsed state
 * @param {string} sectionId - Section ID to toggle
 */
function toggleSection(sectionId) {
    const content = document.getElementById(`section-content-${sectionId}`);
    const button = document.querySelector(`#section-${sectionId} .create-form-section-toggle`);
    
    if (!content || !button) return;
    
    const isCollapsed = content.classList.contains('collapsed');
    content.classList.toggle('collapsed');
    button.classList.toggle('collapsed');
    button.textContent = isCollapsed ? '▼' : '▶';
    button.setAttribute('aria-expanded', isCollapsed);
}

/**
 * Export the generated workflow JSON file
 */
async function exportWorkflowJSON() {
    const workflowId = CreateTabState.selectedWorkflow;
    if (!workflowId) {
        showCreateError('Please select a workflow first');
        return;
    }

    const workflow = CreateTabState.workflowDetails;
    if (!workflow) {
        showCreateError('Workflow details not loaded');
        return;
    }

    try {
        // Log form values for debugging
        console.log('Form values being sent:', CreateTabState.formValues);
        
        // Generate the workflow JSON with current form values
        const response = await fetch('/create/generate-workflow', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                workflow_id: workflowId,
                inputs: CreateTabState.formValues
            })
        });

        const data = await response.json();

        if (data.success && data.workflow) {
            // Create a blob from the workflow JSON
            const blob = new Blob([JSON.stringify(data.workflow, null, 2)], {
                type: 'application/json'
            });

            // Create download link
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // Generate filename with timestamp
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
            a.download = `${workflowId}_${timestamp}.json`;
            
            // Trigger download
            document.body.appendChild(a);
            a.click();
            
            // Cleanup
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            showCreateSuccess('Workflow JSON exported successfully!');
        } else {
            // Log detailed validation errors for debugging
            if (data.errors && Array.isArray(data.errors)) {
                console.error('Validation errors:');
                data.errors.forEach(err => {
                    console.error(`  - ${err.field}: ${err.message}`);
                });
                const errorMessages = data.errors.map(e => `• ${e.field}: ${e.message}`).join('\n');
                showCreateError(`Validation failed:\n${errorMessages}`);
            } else {
                console.error('Error response:', data);
                showCreateError(data.message || 'Failed to generate workflow JSON');
            }
        }
    } catch (error) {
        console.error('Error exporting workflow:', error);
        showCreateError(`Error: ${error.message}`);
    }
}

/**
 * Refresh execution queue
 */
async function refreshExecutionQueue() {
    if (CreateTabState.executionQueue) {
        await CreateTabState.executionQueue.refresh();
    }
}

// Export for use in HTML
window.initCreateTab = initCreateTab;
window.loadWorkflows = loadWorkflows;
window.selectWorkflow = selectWorkflow;
window.toggleAdvancedSection = toggleAdvancedSection;
window.executeWorkflow = executeWorkflow;
window.exportWorkflowJSON = exportWorkflowJSON;
window.updateFormValue = updateFormValue;
window.updateSliderValue = updateSliderValue;
window.updateSliderFromInput = updateSliderFromInput;
window.randomizeSeed = randomizeSeed;
window.handleImageUpload = handleImageUpload;
window.clearImageUpload = clearImageUpload;
// New exports for advanced components
window.toggleSection = toggleSection;
window.updateComponentsSSHConnection = updateComponentsSSHConnection;
window.refreshAllModelSelectors = refreshAllModelSelectors;
window.renderWorkflowFormWithSections = renderWorkflowFormWithSections;
window.refreshExecutionQueue = refreshExecutionQueue;
window.updateConnectionNotice = updateConnectionNotice;
