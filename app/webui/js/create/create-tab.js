/**
 * Create Tab - Main Controller
 * Orchestrates workflow selection, form generation, and execution
 * Supports extensible component architecture driven by *.webui.yml definitions
 */

import { ExecutionQueue } from './components/ExecutionQueue.js';
import { HistoryBrowser } from './components/HistoryBrowser.js';

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
    executionQueue: null,
    // History browser component
    historyBrowser: null
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
    
    try {
        // Initialize HistoryBrowser component
        CreateTabState.historyBrowser = new HistoryBrowser('history-browser-container', onHistoryRecordSelected);
        
        // Expose globally for onclick handlers
        window.historyBrowserInstance = CreateTabState.historyBrowser;
    } catch (error) {
        console.error('Error initializing HistoryBrowser:', error);
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
        console.error('❌ DOM element #create-workflows-grid is missing from the page');
        return;
    }
    
    console.log('✅ Found container:', container);
    container.innerHTML = '<div class="create-empty-state"><div class="create-empty-state-icon">⏳</div><div class="create-empty-state-description">Loading workflows...</div></div>';
    console.log('🔄 Set loading state in container');
    
    try {
        console.log('📡 Fetching /create/workflows/list...');
        const response = await fetch('/create/workflows/list');
        console.log('📡 Response received:', {
            status: response.status,
            statusText: response.statusText,
            ok: response.ok,
            headers: Object.fromEntries(response.headers.entries())
        });
        
        const data = await response.json();
        console.log('📋 Workflows data received:', {
            success: data.success,
            workflowCount: data.workflows ? data.workflows.length : 0,
            message: data.message,
            fullData: data
        });
        
        if (data.success && data.workflows) {
            console.log(`✅ Loaded ${data.workflows.length} workflow(s)`);
            console.log('📋 Workflow details:', data.workflows.map(w => ({
                id: w.id,
                name: w.name,
                category: w.category,
                description: w.description
            })));
            
            CreateTabState.workflows = data.workflows;
            console.log('💾 Stored workflows in CreateTabState');
            
            console.log('🎨 Calling renderWorkflowGrid()...');
            renderWorkflowGrid(data.workflows);
        } else {
            console.error('⚠️ API returned error or missing workflows:', {
                success: data.success,
                hasWorkflows: !!data.workflows,
                message: data.message,
                data: data
            });
            container.innerHTML = `<div class="create-empty-state"><div class="create-empty-state-icon">⚠️</div><div class="create-empty-state-title">Error Loading Workflows</div><div class="create-empty-state-description">${data.message || 'Unknown error'}</div></div>`;
        }
    } catch (error) {
        console.error('❌ Error loading workflows:', {
            message: error.message,
            stack: error.stack,
            error: error
        });
        container.innerHTML = `<div class="create-empty-state"><div class="create-empty-state-icon">❌</div><div class="create-empty-state-title">Connection Error</div><div class="create-empty-state-description">${error.message}</div></div>`;
    }
}

/**
 * Render the workflow grid
 * @param {Array} workflows - Array of workflow objects
 */
function renderWorkflowGrid(workflows) {
    console.log('🎨 renderWorkflowGrid() called with:', {
        workflowCount: workflows ? workflows.length : 0,
        workflows: workflows
    });
    
    const container = document.getElementById('create-workflows-grid');
    if (!container) {
        console.error('❌ Container not found in renderWorkflowGrid');
        return;
    }
    
    console.log('✅ Container found:', container);
    
    if (!workflows || workflows.length === 0) {
        console.warn('⚠️ No workflows to render - showing empty state');
        console.warn('⚠️ Empty condition:', {
            workflowsIsNull: workflows === null,
            workflowsIsUndefined: workflows === undefined,
            workflowsLength: workflows ? workflows.length : 'N/A'
        });
        container.innerHTML = '<div class="create-empty-state"><div class="create-empty-state-icon">📭</div><div class="create-empty-state-title">No Workflows Available</div><div class="create-empty-state-description">No workflow definitions found in the workflows directory.</div></div>';
        return;
    }
    
    console.log(`🎨 Rendering ${workflows.length} workflow card(s)...`);
    const html = workflows.map(workflow => {
        console.log(`  📄 Rendering card for workflow: ${workflow.id} (${workflow.name})`);
        return `
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
    `;
    }).join('');
    
    console.log('📝 Generated HTML length:', html.length);
    console.log('📝 HTML preview (first 200 chars):', html.substring(0, 200));
    
    container.innerHTML = html;
    console.log('✅ Updated container innerHTML');
    console.log('✅ Container now has', container.children.length, 'child elements');
    console.log('✅ Workflow grid rendering complete');
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
    
    // Helper tools (if present)
    if (workflow.helper_tools && workflow.helper_tools.length > 0) {
        html += renderHelperTools(workflow.helper_tools);
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
            
        case 'node_mode_toggle':
            // Node mode toggle: maps checkbox to ComfyUI node mode values
            // Checked (enabled) = mode 0, Unchecked (disabled) = mode 2 or 4
            const isEnabled = field.default === 0;
            // Preserve the disabled mode type - valid modes are 2 (bypass) and 4 (muted)
            let disabledMode = 2; // Default to bypass
            if (field.default === 4) {
                disabledMode = 4;
            } else if (field.default === 2) {
                disabledMode = 2;
            } else if (field.default !== 0) {
                console.warn(`Unknown node mode default ${field.default} for ${field.id}, using mode 2 (bypass)`);
            }
            inputHtml = `
                <div class="checkbox-field-container">
                    <input 
                        type="checkbox" 
                        id="${id}" 
                        ${isEnabled ? 'checked' : ''}
                        data-disabled-mode="${disabledMode}"
                        onchange="updateNodeModeToggle('${field.id}', this)"
                    >
                    <label for="${id}" class="checkbox-field-label">${escapeHtml(field.label)}</label>
                </div>
            `;
            // Don't show the label twice for toggles
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
 * Update node mode toggle value
 * Maps checkbox state to ComfyUI node mode values
 * @param {string} fieldId - Field ID
 * @param {HTMLInputElement} checkbox - Checkbox element
 */
function updateNodeModeToggle(fieldId, checkbox) {
    const disabledMode = parseInt(checkbox.dataset.disabledMode) || 2;
    const modeValue = checkbox.checked ? 0 : disabledMode;
    updateFormValue(fieldId, modeValue);
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
    
    // If this is a width or height field, update apply button state
    const { targets } = HelperToolState.autoSizing;
    if (fieldId === targets.width_field || fieldId === targets.height_field) {
        updateApplyButtonState();
    }
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
    
    // If this is a width or height field, update apply button state
    const { targets } = HelperToolState.autoSizing;
    if (fieldId === targets.width_field || fieldId === targets.height_field) {
        updateApplyButtonState();
    }
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
 * Scale image to fit within max megapixels
 * @param {string} dataUrl - Base64 data URL of image
 * @param {number} maxMegapixels - Maximum size in megapixels
 * @returns {Promise<string>} - Scaled image data URL
 */
async function scaleImageToMaxSize(dataUrl, maxMegapixels) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = function() {
            const currentMegapixels = (img.width * img.height) / 1000000;
            
            // If image is already within limit, return as-is
            if (currentMegapixels <= maxMegapixels) {
                resolve(dataUrl);
                return;
            }
            
            // Calculate new dimensions
            const scaleFactor = Math.sqrt(maxMegapixels / currentMegapixels);
            const newWidth = Math.round(img.width * scaleFactor);
            const newHeight = Math.round(img.height * scaleFactor);
            
            console.log(`Scaling image from ${img.width}x${img.height} (${currentMegapixels.toFixed(2)}MP) to ${newWidth}x${newHeight} (${maxMegapixels}MP)`);
            
            // Create canvas and scale
            const canvas = document.createElement('canvas');
            canvas.width = newWidth;
            canvas.height = newHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, newWidth, newHeight);
            
            // Convert to data URL
            resolve(canvas.toDataURL('image/jpeg', 0.92));
        };
        img.onerror = reject;
        img.src = dataUrl;
    });
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
    
    // Get max size from helper tools slider
    const maxSizeSlider = document.getElementById('helper-max_image_size');
    const maxMegapixels = maxSizeSlider ? parseFloat(maxSizeSlider.value) : 1.0;
    
    // Show preview using DOM methods for security
    const reader = new FileReader();
    reader.onload = async function(e) {
        try {
            // Scale image if needed
            const scaledDataUrl = await scaleImageToMaxSize(e.target.result, maxMegapixels);
            
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
            img.src = scaledDataUrl;
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
            
            // Store scaled base64 data
            updateFormValue(fieldId, scaledDataUrl);
            
            // Get actual image dimensions and trigger auto-sizing
            const dimensionImg = new Image();
            dimensionImg.onload = function() {
                storeImageDimensions(dimensionImg.width, dimensionImg.height);
            };
            dimensionImg.src = scaledDataUrl;
        } catch (error) {
            console.error('Error processing image:', error);
            alert('Failed to process image. Please try again.');
        }
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
    
    // Get SSH connection string from toolbar
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
        console.log('🚀 Queueing workflow via BrowserAgent...');
        console.log('   Workflow ID:', workflowId);
        console.log('   SSH Connection:', sshConnection);
        console.log('   Form inputs:', CreateTabState.formValues);
        
        // Use new BrowserAgent-based queueing endpoint
        const response = await fetch('/create/queue-workflow', {
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
            console.log('✅ Workflow queued successfully!');
            console.log('   Prompt ID:', data.prompt_id);
            
            CreateTabState.taskId = data.prompt_id;
            showCreateSuccess(data.message || `Workflow queued! Prompt ID: ${data.prompt_id}`);
            
            // Add to execution queue display
            if (window.ExecutionQueue) {
                window.ExecutionQueue.addTask({
                    id: data.prompt_id,
                    workflow_id: workflowId,
                    status: 'queued',
                    started_at: new Date().toISOString(),
                    message: 'Workflow queued on ComfyUI'
                });
            }
        } else {
            console.error('❌ Failed to queue workflow:', data.message);
            if (data.details) {
                console.error('   Details:', data.details);
            }
            showCreateError(data.message || 'Failed to queue workflow');
        }
    } catch (error) {
        console.error('💥 Error queueing workflow:', error);
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
 * Render helper tools section
 * @param {Array} helperTools - Array of helper tool configurations
 * @returns {string} HTML for helper tools section
 */
function renderHelperTools(helperTools) {
    if (!helperTools || helperTools.length === 0) return '';
    
    let html = '<div class="create-form-section helper-tools-section">';
    html += '<div class="create-form-section-header">';
    html += '<h4 class="create-form-section-title">🛠️ Helper Tools</h4>';
    html += '</div>';
    html += '<div class="create-form-section-content">';
    
    for (const tool of helperTools) {
        html += `<div class="helper-tool" data-tool-id="${escapeHtml(tool.id)}">`;
        
        // Render controls directly without extra header/label/description
        if (tool.controls && tool.controls.length > 0) {
            for (const control of tool.controls) {
                if (control.type === 'slider_with_apply') {
                    html += `<div class="create-form-field">`;
                    // Create a flex container for label and apply button
                    html += `<div class="helper-tool-header-row">`;
                    // Include unit in label if present
                    const labelText = control.unit ? `${control.label} (${control.unit})` : control.label;
                    html += `<label>${escapeHtml(labelText)}</label>`;
                    // Apply button right-justified on same line as label
                    if (control.apply_button) {
                        html += `<button type="button" id="helper-${escapeHtml(control.id)}-apply" class="helper-tool-apply-button" `;
                        html += `onclick="handleApplyMaxSize('${escapeHtml(tool.id)}')">`;
                        html += `${escapeHtml(control.apply_button_label || 'Apply')}`;
                        html += `</button>`;
                    }
                    html += `</div>`; // helper-tool-header-row
                    // Add short description if present
                    if (control.description) {
                        html += `<div class="field-description">${escapeHtml(control.description)}</div>`;
                    }
                    html += `<div class="slider-container">`;
                    html += `<input type="range" id="helper-${escapeHtml(control.id)}" class="slider-input" `;
                    html += `min="${control.min || 0}" max="${control.max || 100}" step="${control.step || 1}" `;
                    html += `value="${control.default || control.min || 0}" `;
                    html += `onchange="handleMaxSizeChange('${escapeHtml(tool.id)}', this.value)">`;
                    html += `<input type="number" id="helper-${escapeHtml(control.id)}-value" class="slider-value" `;
                    html += `min="${control.min || 0}" max="${control.max || 100}" step="${control.step || 1}" `;
                    html += `value="${control.default || control.min || 0}" `;
                    html += `oninput="handleMaxSizeInputChange('${escapeHtml(tool.id)}', this.value)">`;
                    html += `</div>`; // slider-container
                    html += `</div>`; // create-form-field
                } else if (control.type === 'checkbox') {
                    // Skip checkbox rendering - we're removing the toggle
                }
            }
        }
        
        html += `</div>`; // helper-tool
    }
    
    html += '</div>'; // create-form-section-content
    html += '</div>'; // helper-tools-section
    return html;
}

/**
 * Helper tool state
 */
const HelperToolState = {
    autoSizing: {
        maxSize: 1.0,  // in megapixels (MP)
        currentImageDimensions: null,
        calculatedDimensions: null,  // Store last calculated values
        targets: { width_field: 'size_x', height_field: 'size_y' }
    }
};

/**
 * Handle max size slider change
 */
function handleMaxSizeChange(toolId, value) {
    const numberInput = document.getElementById(`helper-max_image_size-value`);
    
    if (numberInput) {
        numberInput.value = value;
    }
    
    HelperToolState.autoSizing.maxSize = parseFloat(value);
    
    // Recalculate dimensions and update button state
    updateCalculatedDimensions();
    updateApplyButtonState();
}

/**
 * Handle max size number input change
 */
function handleMaxSizeInputChange(toolId, value) {
    const slider = document.getElementById(`helper-max_image_size`);
    
    if (slider) {
        slider.value = value;
    }
    
    HelperToolState.autoSizing.maxSize = parseFloat(value);
    
    // Recalculate dimensions and update button state
    updateCalculatedDimensions();
    updateApplyButtonState();
}

/**
 * Handle apply button click - fills in calculated values
 */
function handleApplyMaxSize(toolId) {
    const { calculatedDimensions } = HelperToolState.autoSizing;
    
    if (!calculatedDimensions) return;
    
    const widthField = HelperToolState.autoSizing.targets.width_field;
    const heightField = HelperToolState.autoSizing.targets.height_field;
    
    const widthSlider = document.getElementById(`create-field-${widthField}`);
    const widthInput = document.getElementById(`create-field-${widthField}-value`);
    const heightSlider = document.getElementById(`create-field-${heightField}`);
    const heightInput = document.getElementById(`create-field-${heightField}-value`);
    
    // Apply calculated values to form fields
    if (widthSlider) widthSlider.value = calculatedDimensions.width;
    if (widthInput) widthInput.value = calculatedDimensions.width;
    if (heightSlider) heightSlider.value = calculatedDimensions.height;
    if (heightInput) heightInput.value = calculatedDimensions.height;
    
    // Update form values
    updateFormValue(widthField, calculatedDimensions.width);
    updateFormValue(heightField, calculatedDimensions.height);
    
    // Update button state (will be disabled since values now match)
    updateApplyButtonState();
    
    console.log(`✅ Applied dimensions: ${calculatedDimensions.width}x${calculatedDimensions.height}`);
}

/**
 * Calculate dimensions based on current settings
 */
function updateCalculatedDimensions() {
    const { currentImageDimensions, maxSize } = HelperToolState.autoSizing;
    
    if (!currentImageDimensions) {
        // No image loaded - set to null (will show as "?")
        HelperToolState.autoSizing.calculatedDimensions = null;
        return;
    }
    
    const { width: imgWidth, height: imgHeight } = currentImageDimensions;
    const aspectRatio = imgWidth / imgHeight;
    
    // Calculate current megapixels
    const currentMP = (imgWidth * imgHeight) / 1000000;
    const maxMP = maxSize;
    
    let targetWidth, targetHeight;
    
    // Only scale down if image exceeds max megapixels
    if (currentMP > maxMP) {
        // Calculate target total pixels from megapixels
        const targetPixels = maxMP * 1000000;
        
        // Calculate new dimensions maintaining aspect ratio
        targetWidth = Math.sqrt(targetPixels * aspectRatio);
        targetHeight = targetWidth / aspectRatio;
        
        // Round to integers
        targetWidth = Math.round(targetWidth);
        targetHeight = Math.round(targetHeight);
        
        // Snap to 64px grid
        targetWidth = Math.round(targetWidth / 64) * 64;
        targetHeight = Math.round(targetHeight / 64) * 64;
        
        // Ensure minimum size
        targetWidth = Math.max(64, targetWidth);
        targetHeight = Math.max(64, targetHeight);
    } else {
        // Image is already within limits, use original dimensions (snapped to grid)
        targetWidth = Math.round(imgWidth / 64) * 64;
        targetHeight = Math.round(imgHeight / 64) * 64;
    }
    
    HelperToolState.autoSizing.calculatedDimensions = {
        width: targetWidth,
        height: targetHeight
    };
}

/**
 * Update apply button state based on whether current values match calculated values
 */
function updateApplyButtonState() {
    const applyBtn = document.getElementById(`helper-max_image_size-apply`);
    if (!applyBtn) return;
    
    const { calculatedDimensions } = HelperToolState.autoSizing;
    
    // If no image loaded (calculatedDimensions is null), disable button
    if (!calculatedDimensions) {
        applyBtn.disabled = true;
        return;
    }
    
    const widthField = HelperToolState.autoSizing.targets.width_field;
    const heightField = HelperToolState.autoSizing.targets.height_field;
    
    const widthInput = document.getElementById(`create-field-${widthField}-value`);
    const heightInput = document.getElementById(`create-field-${heightField}-value`);
    
    if (!widthInput || !heightInput) {
        applyBtn.disabled = true;
        return;
    }
    
    const currentWidth = parseInt(widthInput.value);
    const currentHeight = parseInt(heightInput.value);
    
    // Enable button if values don't match calculated values
    const valuesMatch = (currentWidth === calculatedDimensions.width && 
                        currentHeight === calculatedDimensions.height);
    applyBtn.disabled = valuesMatch;
}

/**
 * Store image dimensions for auto-sizing
 * Called when an image is uploaded
 */
function storeImageDimensions(width, height) {
    HelperToolState.autoSizing.currentImageDimensions = { width, height };
    console.log(`📷 Image dimensions stored: ${width}x${height}`);
    
    // Recalculate dimensions and update button state
    updateCalculatedDimensions();
    updateApplyButtonState();
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
    
    // Helper tools (if present)
    if (workflow.helper_tools && workflow.helper_tools.length > 0) {
        html += renderHelperTools(workflow.helper_tools);
    }
    
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
        // Note: updateComponentsSSHConnection triggers auto-refresh in each component's setSSHConnection
        // so we don't need to call refreshAllModelSelectors here
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

/**
 * Open workflow history browser
 */
function openHistoryBrowser() {
    if (!CreateTabState.selectedWorkflow) {
        showCreateError('Please select a workflow first');
        return;
    }
    
    if (CreateTabState.historyBrowser) {
        CreateTabState.historyBrowser.open(CreateTabState.selectedWorkflow);
    }
}

/**
 * Handle history record selection
 * @param {Object} record - History record with inputs
 */
function onHistoryRecordSelected(record) {
    console.log('Loading history record:', record);
    
    // Ensure the correct workflow is selected
    if (record.workflow_id !== CreateTabState.selectedWorkflow) {
        console.warn('History record is for different workflow, switching...');
        selectWorkflow(record.workflow_id)
            .then(() => {
                populateFormFromHistory(record);
            })
            .catch((error) => {
                console.error('Failed to switch workflow:', error);
                showCreateError(`Failed to load workflow: ${error.message}`);
            });
    } else {
        populateFormFromHistory(record);
    }
}

/**
 * Populate form with values from history record
 * @param {Object} record - History record
 */
function populateFormFromHistory(record) {
    const inputs = record.inputs || {};
    
    // Clear current form values
    CreateTabState.formValues = {};
    
    // Populate each field
    for (const [fieldId, value] of Object.entries(inputs)) {
        const fieldElement = document.getElementById(`create-field-${fieldId}`);
        
        if (!fieldElement) {
            console.warn(`Field element not found: ${fieldId}`);
            continue;
        }
        
        // Handle different field types
        const field = findFieldById(fieldId);
        if (!field) continue;
        
        switch (field.type) {
            case 'image':
                // Restore image upload
                if (value && typeof value === 'string' && value.startsWith('data:image/')) {
                    // Simulate file upload by setting the value and triggering preview
                    handleImageUploadFromData(fieldId, value);
                }
                break;
                
            case 'textarea':
            case 'text':
                fieldElement.value = value || '';
                updateFormValue(fieldId, value);
                break;
                
            case 'slider':
                fieldElement.value = value || field.default || 0;
                const valueInput = document.getElementById(`create-field-${fieldId}-value`);
                if (valueInput) {
                    valueInput.value = value || field.default || 0;
                }
                updateFormValue(fieldId, value);
                break;
                
            case 'seed':
                fieldElement.value = value || -1;
                updateFormValue(fieldId, value);
                break;
                
            case 'checkbox':
                fieldElement.checked = !!value;
                updateFormValue(fieldId, !!value);
                break;
                
            case 'select':
                fieldElement.value = value || '';
                updateFormValue(fieldId, value);
                break;
                
            default:
                // For advanced components, we need to restore their state
                const component = CreateTabState.componentInstances.get(fieldId);
                if (component && typeof component.setValue === 'function') {
                    component.setValue(value);
                }
                updateFormValue(fieldId, value);
        }
    }
    
    showCreateSuccess('History record loaded successfully!');
}

/**
 * Find field definition by ID
 * @param {string} fieldId - Field ID
 * @returns {Object|null} Field definition
 */
function findFieldById(fieldId) {
    if (!CreateTabState.workflowDetails) return null;
    
    const allFields = [
        ...(CreateTabState.workflowDetails.inputs || []),
        ...(CreateTabState.workflowDetails.advanced || [])
    ];
    
    return allFields.find(f => f.id === fieldId);
}

/**
 * Handle image upload from base64 data (for history restoration)
 * @param {string} fieldId - Field ID
 * @param {string} base64Data - Base64 image data
 */
function handleImageUploadFromData(fieldId, base64Data) {
    const container = document.getElementById(`create-field-${fieldId}-container`);
    if (!container) return;
    
    // Clear container properly by removing children
    while (container.firstChild) {
        container.removeChild(container.firstChild);
    }
    
    // Create file input
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.id = `create-field-${fieldId}`;
    fileInput.accept = 'image/*';
    fileInput.addEventListener('change', function() {
        handleImageUpload(fieldId, this);
    });
    
    // Create preview image
    const img = document.createElement('img');
    img.src = base64Data;
    img.className = 'image-upload-preview';
    img.alt = 'Preview';
    
    // Create clear button
    const clearBtn = document.createElement('button');
    clearBtn.type = 'button';
    clearBtn.className = 'image-upload-clear';
    clearBtn.title = 'Remove';
    clearBtn.textContent = '✕';
    clearBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        clearImageUpload(fieldId);
    });
    
    container.appendChild(fileInput);
    container.appendChild(img);
    container.appendChild(clearBtn);
    container.classList.add('has-image');
    
    // Re-add click handler
    container.onclick = function(e) {
        if (e.target === clearBtn || e.target.closest('.image-upload-clear')) {
            return;
        }
        fileInput.click();
    };
    
    // Store value
    updateFormValue(fieldId, base64Data);
}

// Export for use in HTML
window.initCreateTab = initCreateTab;
window.loadWorkflows = loadWorkflows;
window.selectWorkflow = selectWorkflow;
window.toggleAdvancedSection = toggleAdvancedSection;
window.executeWorkflow = executeWorkflow;
window.exportWorkflowJSON = exportWorkflowJSON;
window.updateFormValue = updateFormValue;
window.updateNodeModeToggle = updateNodeModeToggle;
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
// History browser exports
window.openHistoryBrowser = openHistoryBrowser;
window.onHistoryRecordSelected = onHistoryRecordSelected;
// Helper tool exports
window.handleMaxSizeChange = handleMaxSizeChange;
window.handleMaxSizeInputChange = handleMaxSizeInputChange;
window.handleApplyMaxSize = handleApplyMaxSize;
window.handleAutoSizeToggle = handleAutoSizeToggle;
window.storeImageDimensions = storeImageDimensions;

// Auto-initialize if Create tab is already visible when module loads
// This handles the case where the module loads after the tab is shown
if (document.getElementById('create-tab')?.classList.contains('active') && !window.createTabInitialized) {
    console.log('🎨 Auto-initializing Create tab (tab is already visible)...');
    // Set flag first to prevent multiple simultaneous initializations
    window.createTabInitialized = true;
    initCreateTab().catch(error => {
        console.error('❌ Auto-initialization failed:', error);
        // Reset flag on failure to allow retry
        window.createTabInitialized = false;
    });
}
