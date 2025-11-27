/**
 * Create Tab - Main Controller
 * Orchestrates workflow selection, form generation, and execution
 */

// Create Tab state
const CreateTabState = {
    workflows: [],
    selectedWorkflow: null,
    workflowDetails: null,
    formValues: {},
    isExecuting: false,
    taskId: null
};

/**
 * Initialize the Create tab
 */
async function initCreateTab() {
    console.log('🎨 Initializing Create tab...');
    
    // Load workflows
    await loadWorkflows();
    
    // Set up event listeners
    setupCreateTabEventListeners();
    
    console.log('✅ Create tab initialized');
}

/**
 * Load available workflows from the API
 */
async function loadWorkflows() {
    const container = document.getElementById('create-workflows-grid');
    if (!container) return;
    
    container.innerHTML = '<div class="create-empty-state"><div class="create-empty-state-icon">⏳</div><div class="create-empty-state-description">Loading workflows...</div></div>';
    
    try {
        const response = await fetch('/create/workflows/list');
        const data = await response.json();
        
        if (data.success && data.workflows) {
            CreateTabState.workflows = data.workflows;
            renderWorkflowGrid(data.workflows);
        } else {
            container.innerHTML = `<div class="create-empty-state"><div class="create-empty-state-icon">⚠️</div><div class="create-empty-state-title">Error Loading Workflows</div><div class="create-empty-state-description">${data.message || 'Unknown error'}</div></div>`;
        }
    } catch (error) {
        console.error('Error loading workflows:', error);
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
            renderWorkflowForm(data.workflow);
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
    
    // Presets (if available)
    if (workflow.presets && workflow.presets.length > 0) {
        html += `
            <div class="create-form-section">
                <div class="create-form-section-header">
                    <h4 class="create-form-section-title">⚡ Quick Presets</h4>
                </div>
                <div class="presets-container">
                    ${workflow.presets.map((preset, idx) => `
                        <button class="preset-button" onclick="applyPreset(${idx})" title="${escapeHtml(preset.description || '')}">
                            ${escapeHtml(preset.name)}
                        </button>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
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
    
    // Requirements info
    if (workflow.requirements) {
        html += renderRequirementsInfo(workflow.requirements);
    }
    
    formContainer.innerHTML = html;
    formContainer.style.display = 'block';
    
    // Initialize form values with defaults
    initializeFormDefaults(workflow);
}

/**
 * Render a single form field
 * @param {Object} field - Field definition
 * @returns {string} HTML string
 */
function renderFormField(field) {
    const id = `create-field-${field.id}`;
    const requiredClass = field.required ? 'required' : '';
    const description = field.description ? `<div class="field-description">${escapeHtml(field.description)}</div>` : '';
    
    let inputHtml = '';
    
    switch (field.type) {
        case 'image':
            inputHtml = `
                <div class="image-upload-container" id="${id}-container" onclick="document.getElementById('${id}').click()">
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
 * Render requirements info section
 * @param {Object} requirements - Requirements object
 * @returns {string} HTML string
 */
function renderRequirementsInfo(requirements) {
    let items = [];
    
    if (requirements.vram) {
        items.push(`<span class="workflow-requirement-item"><span class="workflow-requirement-icon">🎮</span> ${escapeHtml(requirements.vram)}</span>`);
    }
    
    if (requirements.compute) {
        items.push(`<span class="workflow-requirement-item"><span class="workflow-requirement-icon">💻</span> ${escapeHtml(requirements.compute)}</span>`);
    }
    
    if (requirements.models && requirements.models.length > 0) {
        items.push(`<span class="workflow-requirement-item"><span class="workflow-requirement-icon">📦</span> ${requirements.models.length} model(s) required</span>`);
    }
    
    if (requirements.custom_nodes && requirements.custom_nodes.length > 0) {
        items.push(`<span class="workflow-requirement-item"><span class="workflow-requirement-icon">🔌</span> ${requirements.custom_nodes.length} custom node(s)</span>`);
    }
    
    if (items.length === 0) return '';
    
    return `
        <div class="workflow-requirements">
            <div class="workflow-requirements-title">📋 Requirements</div>
            <div class="workflow-requirements-list">
                ${items.join('')}
            </div>
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
    
    const container = document.getElementById(`create-field-${fieldId}-container`);
    if (!container) return;
    
    // Show preview
    const reader = new FileReader();
    reader.onload = function(e) {
        container.innerHTML = `
            <input type="file" id="create-field-${fieldId}" accept="${input.accept || 'image/*'}" onchange="handleImageUpload('${fieldId}', this)">
            <img src="${e.target.result}" class="image-upload-preview" alt="Preview">
            <button type="button" class="image-upload-clear" onclick="clearImageUpload('${fieldId}')" title="Remove">✕</button>
        `;
        container.classList.add('has-image');
        
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
    
    updateFormValue(fieldId, null);
}

/**
 * Apply a preset to the form
 * @param {number} presetIndex - Index of the preset
 */
function applyPreset(presetIndex) {
    const workflow = CreateTabState.workflowDetails;
    if (!workflow || !workflow.presets || !workflow.presets[presetIndex]) return;
    
    const preset = workflow.presets[presetIndex];
    const values = preset.values || {};
    
    // Apply each preset value
    Object.entries(values).forEach(([fieldId, value]) => {
        updateFormValue(fieldId, value);
        
        // Update the UI
        const input = document.getElementById(`create-field-${fieldId}`);
        if (input) {
            if (input.type === 'checkbox') {
                input.checked = value;
            } else if (input.type === 'range') {
                input.value = value;
                const valueInput = document.getElementById(`create-field-${fieldId}-value`);
                if (valueInput) valueInput.value = value;
            } else {
                input.value = value;
            }
        }
    });
    
    // Update preset button states
    document.querySelectorAll('.preset-button').forEach((btn, idx) => {
        btn.classList.toggle('active', idx === presetIndex);
    });
    
    console.log(`Applied preset: ${preset.name}`);
}

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
    
    // Get SSH connection string
    const sshInput = document.getElementById('createSshConnectionString') || 
                     document.getElementById('sshConnectionString') ||
                     document.getElementById('resourcesSshConnectionString');
    const sshConnection = sshInput?.value?.trim();
    
    if (!sshConnection) {
        showCreateError('Please enter an SSH connection string');
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
    // SSH connection string sync
    const createSshInput = document.getElementById('createSshConnectionString');
    const vastaiSshInput = document.getElementById('sshConnectionString');
    const resourcesSshInput = document.getElementById('resourcesSshConnectionString');
    
    if (createSshInput) {
        // Sync from Create tab to other tabs
        createSshInput.addEventListener('input', function() {
            if (vastaiSshInput) vastaiSshInput.value = this.value;
            if (resourcesSshInput) resourcesSshInput.value = this.value;
        });
        
        // Initialize from other tabs if they have values
        if (vastaiSshInput?.value) {
            createSshInput.value = vastaiSshInput.value;
        } else if (resourcesSshInput?.value) {
            createSshInput.value = resourcesSshInput.value;
        }
    }
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

// Export for use in HTML
window.initCreateTab = initCreateTab;
window.loadWorkflows = loadWorkflows;
window.selectWorkflow = selectWorkflow;
window.applyPreset = applyPreset;
window.toggleAdvancedSection = toggleAdvancedSection;
window.executeWorkflow = executeWorkflow;
window.updateFormValue = updateFormValue;
window.updateSliderValue = updateSliderValue;
window.updateSliderFromInput = updateSliderFromInput;
window.randomizeSeed = randomizeSeed;
window.handleImageUpload = handleImageUpload;
window.clearImageUpload = clearImageUpload;
