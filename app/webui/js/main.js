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
    
    // Sync SSH connection strings between tabs
    syncSshConnectionStrings();
}

// Sync SSH connection strings between VastAI Setup and Resources tabs
function syncSshConnectionStrings() {
    const vastaiInput = document.getElementById('sshConnectionString');
    const resourcesInput = document.getElementById('resourcesSshConnectionString');
    
    if (vastaiInput && resourcesInput) {
        // Sync from VastAI Setup to Resources if Resources is empty
        if (!resourcesInput.value && vastaiInput.value) {
            resourcesInput.value = vastaiInput.value;
        }
        // Sync from Resources to VastAI Setup if VastAI Setup is empty
        else if (!vastaiInput.value && resourcesInput.value) {
            vastaiInput.value = resourcesInput.value;
        }
    }
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
    
    if (vastaiInput && resourcesInput) {
        vastaiInput.addEventListener('input', function() {
            resourcesInput.value = vastaiInput.value;
        });
        
        resourcesInput.addEventListener('input', function() {
            vastaiInput.value = resourcesInput.value;
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

    let html = '';
    instances.forEach(instance => {
        const normalizedStatus = window.normStatus ? window.normStatus(instance.status) : (instance.status || 'unknown');
        const sshConnection = buildSSHStringForResources(instance);

        html += `
          <div class="instance-item" data-instance-id="${instance.id ?? ''}">
            <div class="instance-header">
              <div class="instance-title">Instance #${instance.id ?? 'Unknown'}</div>
              <div class="instance-status ${normalizedStatus}" data-field="status">${normalizedStatus}</div>
            </div>

            <div class="instance-details">
              <div class="instance-detail"><strong>GPU:</strong> ${instance.gpu ? instance.gpu : 'N/A'}${instance.gpu_count ? ` (${instance.gpu_count}x)` : ''}</div>
              <div class="instance-detail"><strong>GPU RAM:</strong> ${window.fmtGb ? window.fmtGb(instance.gpu_ram_gb) : (instance.gpu_ram_gb || 'N/A')}</div>
              <div class="instance-detail"><strong>Location:</strong> ${instance.geolocation || 'N/A'}</div>
              <div class="instance-detail"><strong>Cost:</strong> ${window.fmtMoney ? window.fmtMoney(instance.cost_per_hour) : (instance.cost_per_hour || 'N/A')}</div>
              <div class="instance-detail"><strong>SSH Host:</strong> <span data-field="ssh_host">${instance.ssh_host || 'N/A'}</span></div>
              <div class="instance-detail"><strong>SSH Port:</strong> <span data-field="ssh_port">${instance.ssh_port || 'N/A'}</span></div>
            </div>

            <div class="instance-actions">
              ${
                sshConnection && normalizedStatus === 'running'
                  ? `<button class="use-instance-btn" onclick="useInstanceForResources('${sshConnection.replace(/'/g, "\\'")}', ${instance.id})">
                       🔗 Use This Instance
                     </button>`
                  : `<button class="use-instance-btn" onclick="refreshInstanceCardForResources(${instance.id})">
                       🔄 Load SSH
                     </button>`
              }
            </div>
          </div>
        `;
    });

    if (instancesList) {
        instancesList.innerHTML = html;
    }
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