// Main application bootstrapping - tabs, overlays, and page wiring

// Tab switching functionality
function showTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(tab => tab.classList.remove('active'));
    
    // Remove active class from all tab buttons
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => button.classList.remove('active'));
    
    // Show selected tab content
    const selectedTab = document.getElementById(tabName + '-tab');
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Add active class to clicked tab button
    const clickedButton = event.target;
    clickedButton.classList.add('active');
    
    // Initialize resource browser when resources tab is shown
    if (tabName === 'resources' && !window.resourceBrowserInitialized) {
        initResourceBrowser();
    }
    
    // Initialize Create tab when shown
    if (tabName === 'create' && !window.createTabInitialized) {
        if (typeof initCreateTab === 'function') {
            initCreateTab();
            window.createTabInitialized = true;
        }
    }
    
    // Sync SSH connection strings between tabs
    syncSshConnectionStrings();
}

// Sync SSH connection strings between all tabs
function syncSshConnectionStrings() {
    const vastaiInput = document.getElementById('sshConnectionString');
    const resourcesInput = document.getElementById('resourcesSshConnectionString');
    const createInput = document.getElementById('createSshConnectionString');
    
    // Get the first non-empty value
    const value = vastaiInput?.value || resourcesInput?.value || createInput?.value || '';
    
    // Sync to all inputs
    if (vastaiInput && !vastaiInput.value && value) vastaiInput.value = value;
    if (resourcesInput && !resourcesInput.value && value) resourcesInput.value = value;
    if (createInput && !createInput.value && value) createInput.value = value;
}

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Setup log modal overlay click handling
    const overlay = document.getElementById('logOverlay');
    overlay.addEventListener('click', function(e) {
        if (e.target === overlay) {
            closeLogModal();
        }
    });
    
    // Setup result panel click handler for viewing full reports
    attachResultClickHandler();
    
    // Initialize workflow system (server-side execution + state restoration)
    if (typeof initWorkflow === 'function') {
        initWorkflow();
    }
    
    // Setup bidirectional sync for SSH connection strings
    setupSshInputSync();
});

// Setup bidirectional sync between SSH connection inputs
function setupSshInputSync() {
    const vastaiInput = document.getElementById('sshConnectionString');
    const resourcesInput = document.getElementById('resourcesSshConnectionString');
    const createInput = document.getElementById('createSshConnectionString');
    
    // Sync VastAI input to all others
    if (vastaiInput) {
        vastaiInput.addEventListener('input', function() {
            if (resourcesInput) resourcesInput.value = vastaiInput.value;
            if (createInput) createInput.value = vastaiInput.value;
        });
    }
    
    // Sync Resources input to all others
    if (resourcesInput) {
        resourcesInput.addEventListener('input', function() {
            if (vastaiInput) vastaiInput.value = resourcesInput.value;
            if (createInput) createInput.value = resourcesInput.value;
        });
    }
    
    // Sync Create input to all others
    if (createInput) {
        createInput.addEventListener('input', function() {
            if (vastaiInput) vastaiInput.value = createInput.value;
            if (resourcesInput) resourcesInput.value = createInput.value;
        });
    }
}

// Load VastAI instances for Resources tab
async function loadVastaiInstancesForResources() {
    const instancesList = document.getElementById('resources-vastai-instances-list');
    if (instancesList) {
        instancesList.innerHTML = '<div class="no-instances-message">Loading instances...</div>';
    }

    try {
        const data = await api.get('/vastai/instances');
        if (!data || data.success === false) {
            const msg = (data && data.message) ? data.message : 'Failed to load instances';
            if (instancesList) {
                instancesList.innerHTML = `<div class="no-instances-message" style="color: var(--text-error);">❌ ${msg}</div>`;
            }
            return;
        }

        const rawInstances = Array.isArray(data.instances) ? data.instances : [];
        // Use VastAI modular system's normalizeInstance if available for consistent data format,
        // otherwise use raw instance data which will be handled by display function
        const instances = rawInstances.map(inst => window.VastAIInstances ? window.VastAIInstances.normalizeInstance(inst) : inst);
        displayVastaiInstancesForResources(instances);
    } catch (error) {
        if (instancesList) {
            instancesList.innerHTML = `<div class="no-instances-message" style="color: var(--text-error);">❌ Error: ${error.message}</div>`;
        }
    }
}

// Display VastAI instances in the Resources tab
function displayVastaiInstancesForResources(instances) {
    const instancesList = document.getElementById('resources-vastai-instances-list');

    if (!instances || instances.length === 0) {
        if (instancesList) {
            instancesList.innerHTML = '<div class="no-instances-message">No instances found</div>';
        }
        return;
    }

    // Clear the list first
    if (instancesList) {
        instancesList.innerHTML = '';
    }
    
    instances.forEach(instance => {
        // Normalize instance data using available functions
        const normalizedStatus = window.normStatus ? window.normStatus(instance.status) : (instance.status || 'unknown');
        const sshConnection = buildSSHStringForResources(instance);
        
        // Validate instance.id is a number to prevent XSS
        const instanceId = typeof instance.id === 'number' ? instance.id : parseInt(instance.id, 10);
        if (isNaN(instanceId)) {
            console.warn('Invalid instance ID:', instance.id);
            return; // Skip this instance
        }

        // Create DOM elements safely instead of using innerHTML with untrusted data
        const instanceItem = document.createElement('div');
        instanceItem.className = 'instance-item';
        instanceItem.setAttribute('data-instance-id', instanceId);
        
        const instanceHeader = document.createElement('div');
        instanceHeader.className = 'instance-header';
        
        const instanceTitle = document.createElement('div');
        instanceTitle.className = 'instance-title';
        instanceTitle.textContent = `Instance #${instanceId}`;
        
        const instanceStatus = document.createElement('div');
        instanceStatus.className = `instance-status ${normalizedStatus}`;
        instanceStatus.setAttribute('data-field', 'status');
        instanceStatus.textContent = normalizedStatus;
        
        instanceHeader.appendChild(instanceTitle);
        instanceHeader.appendChild(instanceStatus);
        
        const instanceDetails = document.createElement('div');
        instanceDetails.className = 'instance-details';
        
        // Helper function to create detail element
        const createDetail = (label, value) => {
            const detail = document.createElement('div');
            detail.className = 'instance-detail';
            const strong = document.createElement('strong');
            strong.textContent = label;
            detail.appendChild(strong);
            detail.appendChild(document.createTextNode(value));
            return detail;
        };
        
        // Helper function to create detail with span
        const createDetailWithSpan = (label, value, dataField) => {
            const detail = document.createElement('div');
            detail.className = 'instance-detail';
            const strong = document.createElement('strong');
            strong.textContent = label;
            detail.appendChild(strong);
            const span = document.createElement('span');
            span.setAttribute('data-field', dataField);
            span.textContent = value || 'N/A';
            detail.appendChild(span);
            return detail;
        };
        
        const gpuValue = instance.gpu ? (instance.gpu_count ? ` ${instance.gpu} (${instance.gpu_count}x)` : ` ${instance.gpu}`) : ' N/A';
        instanceDetails.appendChild(createDetail('GPU:', gpuValue));
        
        const gpuRamValue = window.fmtGb ? ` ${window.fmtGb(instance.gpu_ram_gb)}` : ` ${instance.gpu_ram_gb || 'N/A'}`;
        instanceDetails.appendChild(createDetail('GPU RAM:', gpuRamValue));
        
        instanceDetails.appendChild(createDetail('Location:', ` ${instance.geolocation || 'N/A'}`));
        
        const costValue = window.fmtMoney ? ` ${window.fmtMoney(instance.cost_per_hour)}` : ` ${instance.cost_per_hour || 'N/A'}`;
        instanceDetails.appendChild(createDetail('Cost:', costValue));
        
        instanceDetails.appendChild(createDetailWithSpan('SSH Host: ', instance.ssh_host, 'ssh_host'));
        instanceDetails.appendChild(createDetailWithSpan('SSH Port: ', instance.ssh_port, 'ssh_port'));
        
        const instanceActions = document.createElement('div');
        instanceActions.className = 'instance-actions';
        
        const actionButton = document.createElement('button');
        actionButton.className = 'use-instance-btn';
        
        if (sshConnection && normalizedStatus === 'running') {
            actionButton.textContent = '🔗 Use This Instance';
            actionButton.addEventListener('click', function() {
                useInstanceForResources(sshConnection, instanceId);
            });
        } else {
            actionButton.textContent = '🔄 Load SSH';
            actionButton.addEventListener('click', function() {
                refreshInstanceCardForResources(instanceId);
            });
        }
        
        instanceActions.appendChild(actionButton);
        
        instanceItem.appendChild(instanceHeader);
        instanceItem.appendChild(instanceDetails);
        instanceItem.appendChild(instanceActions);
        
        if (instancesList) {
            instancesList.appendChild(instanceItem);
        }
    });
}

// Build SSH string for Resources tab
function buildSSHStringForResources(inst) {
    if (!inst.ssh_host || !inst.ssh_port) return null;
    return `ssh -p ${inst.ssh_port} root@${inst.ssh_host} -L 8080:localhost:8080`;
}

// Use instance SSH connection string in Resources tab
function useInstanceForResources(sshConnection, instanceId) {
    const resourcesInput = document.getElementById('resourcesSshConnectionString');
    const vastaiInput = document.getElementById('sshConnectionString');
    
    if (resourcesInput) {
        resourcesInput.value = sshConnection;
    }
    
    // Also sync to VastAI Setup tab
    if (vastaiInput) {
        vastaiInput.value = sshConnection;
    }
    
    // Store instance ID globally for workflow use
    if (instanceId) {
        window.currentInstanceId = instanceId;
        console.log(`📌 Set current instance ID: ${instanceId}`);
    }
    
    if (window.showSetupResult) {
        window.showSetupResult('✅ SSH connection parameters copied to SSH Connection String field', 'success');
    }
}

// Refresh instance card in Resources tab
async function refreshInstanceCardForResources(instanceId) {
    try {
        if (window.VastAIInstances && window.VastAIInstances.fetchVastaiInstanceDetails) {
            const inst = await window.VastAIInstances.fetchVastaiInstanceDetails(instanceId);
            // Reload the instances list to get updated data
            await loadVastaiInstancesForResources();
            if (window.showSetupResult) {
                window.showSetupResult(`Instance #${instanceId} details refreshed.`, 'success');
            }
        } else {
            // Fallback - just reload the list
            await loadVastaiInstancesForResources();
        }
    } catch (err) {
        if (window.showSetupResult) {
            window.showSetupResult(`Failed to refresh instance #${instanceId}: ${err.message}`, 'error');
        }
    }
}

// Load VastAI instances for Create tab
async function loadVastaiInstancesForCreate() {
    const instancesList = document.getElementById('create-vastai-instances-list');
    if (instancesList) {
        instancesList.innerHTML = '<div class="no-instances-message">Loading instances...</div>';
    }

    try {
        const data = await api.get('/vastai/instances');
        if (!data || data.success === false) {
            const msg = (data && data.message) ? data.message : 'Failed to load instances';
            if (instancesList) {
                instancesList.innerHTML = `<div class="no-instances-message" style="color: var(--text-error);">❌ ${msg}</div>`;
            }
            return;
        }

        const rawInstances = Array.isArray(data.instances) ? data.instances : [];
        const instances = rawInstances.map(inst => window.VastAIInstances ? window.VastAIInstances.normalizeInstance(inst) : inst);
        displayVastaiInstancesForCreate(instances);
    } catch (error) {
        if (instancesList) {
            instancesList.innerHTML = `<div class="no-instances-message" style="color: var(--text-error);">❌ Error: ${error.message}</div>`;
        }
    }
}

// Display VastAI instances in the Create tab
function displayVastaiInstancesForCreate(instances) {
    const instancesList = document.getElementById('create-vastai-instances-list');

    if (!instances || instances.length === 0) {
        if (instancesList) {
            instancesList.innerHTML = '<div class="no-instances-message">No instances found</div>';
        }
        return;
    }

    // Clear the list first
    if (instancesList) {
        instancesList.innerHTML = '';
    }
    
    instances.forEach(instance => {
        // Normalize instance data using available functions
        const normalizedStatus = window.normStatus ? window.normStatus(instance.status) : (instance.status || 'unknown');
        const sshConnection = buildSSHStringForCreate(instance);
        
        // Validate instance.id is a number to prevent XSS
        const instanceId = typeof instance.id === 'number' ? instance.id : parseInt(instance.id, 10);
        if (isNaN(instanceId)) {
            console.warn('Invalid instance ID:', instance.id);
            return; // Skip this instance
        }

        // Create DOM elements safely instead of using innerHTML with untrusted data
        const instanceItem = document.createElement('div');
        instanceItem.className = 'instance-item';
        instanceItem.setAttribute('data-instance-id', instanceId);
        
        const instanceHeader = document.createElement('div');
        instanceHeader.className = 'instance-header';
        
        const instanceTitle = document.createElement('div');
        instanceTitle.className = 'instance-title';
        instanceTitle.textContent = `Instance #${instanceId}`;
        
        const instanceStatus = document.createElement('div');
        instanceStatus.className = `instance-status ${normalizedStatus}`;
        instanceStatus.setAttribute('data-field', 'status');
        instanceStatus.textContent = normalizedStatus;
        
        instanceHeader.appendChild(instanceTitle);
        instanceHeader.appendChild(instanceStatus);
        
        const instanceDetails = document.createElement('div');
        instanceDetails.className = 'instance-details';
        
        // Helper function to create detail element
        const createDetail = (label, value) => {
            const detail = document.createElement('div');
            detail.className = 'instance-detail';
            const strong = document.createElement('strong');
            strong.textContent = label;
            detail.appendChild(strong);
            detail.appendChild(document.createTextNode(value));
            return detail;
        };
        
        const gpuValue = instance.gpu ? (instance.gpu_count ? ` ${instance.gpu} (${instance.gpu_count}x)` : ` ${instance.gpu}`) : ' N/A';
        instanceDetails.appendChild(createDetail('GPU:', gpuValue));
        
        const gpuRamValue = window.fmtGb ? ` ${window.fmtGb(instance.gpu_ram_gb)}` : ` ${instance.gpu_ram_gb || 'N/A'}`;
        instanceDetails.appendChild(createDetail('GPU RAM:', gpuRamValue));
        
        instanceDetails.appendChild(createDetail('Location:', ` ${instance.geolocation || 'N/A'}`));
        
        const instanceActions = document.createElement('div');
        instanceActions.className = 'instance-actions';
        
        const actionButton = document.createElement('button');
        actionButton.className = 'use-instance-btn';
        
        if (sshConnection && normalizedStatus === 'running') {
            actionButton.textContent = '🔗 Use This Instance';
            actionButton.addEventListener('click', function() {
                useInstanceForCreate(sshConnection, instanceId);
            });
        } else {
            actionButton.textContent = '🔄 Load SSH';
            actionButton.addEventListener('click', function() {
                refreshInstanceCardForCreate(instanceId);
            });
        }
        
        instanceActions.appendChild(actionButton);
        
        instanceItem.appendChild(instanceHeader);
        instanceItem.appendChild(instanceDetails);
        instanceItem.appendChild(instanceActions);
        
        if (instancesList) {
            instancesList.appendChild(instanceItem);
        }
    });
}

// Build SSH string for Create tab
function buildSSHStringForCreate(inst) {
    if (!inst.ssh_host || !inst.ssh_port) return null;
    return `ssh -p ${inst.ssh_port} root@${inst.ssh_host} -L 8080:localhost:8080`;
}

// Use instance SSH connection string in Create tab
function useInstanceForCreate(sshConnection, instanceId) {
    const createInput = document.getElementById('createSshConnectionString');
    const vastaiInput = document.getElementById('sshConnectionString');
    const resourcesInput = document.getElementById('resourcesSshConnectionString');
    
    if (createInput) {
        createInput.value = sshConnection;
    }
    
    // Also sync to other tabs
    if (vastaiInput) {
        vastaiInput.value = sshConnection;
    }
    if (resourcesInput) {
        resourcesInput.value = sshConnection;
    }
    
    // Store instance ID globally for workflow use
    if (instanceId) {
        window.currentInstanceId = instanceId;
        console.log(`📌 Set current instance ID: ${instanceId}`);
    }
    
    // Show result message
    const result = document.getElementById('create-result');
    if (result) {
        result.className = 'setup-result success';
        result.textContent = '✅ SSH connection parameters copied to SSH Connection String field';
        result.style.display = 'block';
    }
}

// Refresh instance card in Create tab
async function refreshInstanceCardForCreate(instanceId) {
    try {
        if (window.VastAIInstances && window.VastAIInstances.fetchVastaiInstanceDetails) {
            await window.VastAIInstances.fetchVastaiInstanceDetails(instanceId);
            // Reload the instances list to get updated data
            await loadVastaiInstancesForCreate();
        } else {
            // Fallback - just reload the list
            await loadVastaiInstancesForCreate();
        }
    } catch (err) {
        console.error(`Failed to refresh instance #${instanceId}:`, err);
    }
}

// Initialize resource browser
async function initResourceBrowser() {
    try {
        const { ResourceBrowser } = await import('./resources/resource-browser.js');
        const browser = new ResourceBrowser('resource-manager-container');
        await browser.initialize();
        window.resourceBrowserInitialized = true;
    } catch (error) {
        console.error('Failed to initialize resource browser:', error);
        document.getElementById('resource-manager-container').innerHTML = 
            '<div class="error">Failed to load Resource Manager</div>';
    }
}

// Attach click handler to result panel for viewing full sync reports
function attachResultClickHandler() {
    const resultDiv = document.getElementById('result');
    resultDiv.addEventListener('click', () => {
        if (!lastFullReport) return;

        const overlay = document.getElementById('logOverlay');
        const modalTitle = document.getElementById('logModalTitle');
        const modalContent = document.getElementById('logModalContent');

        modalTitle.textContent = 'Sync Report';

        let content = '';
        // summary
        content += '<div class="log-detail-section"><h4>Summary</h4><div class="log-detail-content">';
        content += (lastFullReport.message || '') + '\\n';
        if (lastFullReport.summary) {
            const s = lastFullReport.summary;
            const bytes = s.bytes_transferred > 0 ? formatBytes(s.bytes_transferred) : '0 bytes';
            content += `Files: ${s.files_transferred}\\nFolders: ${s.folders_synced}\\nBytes: ${bytes}\\n`;
            if (s.by_ext) {
                const extLine = Object.entries(s.by_ext).sort((a,b)=>b[1]-a[1]).map(([k,v])=>k+': '+v).join(', ');
                if (extLine) content += `By type: ${extLine}\\n`;
            }
        }
        content += '</div></div>';

        // stdout
        if (lastFullReport.output) {
            content += '<div class="log-detail-section"><h4>Output</h4><div class="log-detail-content">';
            content += String(lastFullReport.output).replace(/</g,'&lt;');
            content += '</div></div>';
        }
        // stderr
        if (lastFullReport.error) {
            content += '<div class="log-detail-section"><h4>Error</h4><div class="log-detail-content">';
            content += String(lastFullReport.error).replace(/</g,'&lt;');
            content += '</div></div>';
        }

        modalContent.innerHTML = content;
        overlay.style.display = 'flex';
    });
}