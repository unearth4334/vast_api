// Sync functionality and progress polling

async function sync(type) {
    const resultDiv = document.getElementById('result');
    const progressDiv = document.getElementById('progress');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const progressDetails = document.getElementById('progressDetails');
    const cleanupCheckbox = document.getElementById('cleanupCheckbox');
    
    lastFullReport = null;
    resultDiv.className = 'result-panel loading';
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = `<h3>Starting ${type} sync...</h3><p>This may take several minutes.</p>`;
    
    // Show progress bar
    progressDiv.style.display = 'block';
    progressBar.style.width = '0%';
    progressText.textContent = 'Starting sync...';
    progressDetails.textContent = '';
    
    try {
        const data = await api.post(`/sync/${type}`, {
            cleanup: cleanupCheckbox.checked
        });

        // remember full response for the overlay
        lastFullReport = data;
        
        // Start polling for progress if sync_id is available (regardless of initial success)
        if (data.sync_id) {
            pollProgress(data.sync_id);
        } else {
            progressDiv.style.display = 'none';
        }
        
        if (data.success) {
            resultDiv.className = 'result-panel success';
            
            // Show condensed summary if available, otherwise fall back to message
            if (data.summary) {
                const duration = data.summary.duration_seconds ? 
                    `${Math.round(data.summary.duration_seconds)}s` : 'Unknown';
                const bytesFormatted = data.summary.bytes_transferred > 0 ?
                    formatBytes(data.summary.bytes_transferred) : '0 bytes';
                const cleanupStatus = data.summary.cleanup_enabled ? 'enabled' : 'disabled';

                // optional per-extension line (top 4)
                let byExtLine = '';
                if (data.summary.by_ext) {
                    const pairs = Object.entries(data.summary.by_ext)
                      .sort((a,b)=>b[1]-a[1]).slice(0,4)
                      .map(([k,v]) => `${k}:${v}`).join(' · ');
                    if (pairs) byExtLine = `<br>🧩 By type: ${pairs}`;
                }
                
                resultDiv.innerHTML = `
                    <h3>✅ ${data.message}</h3>
                    <div style="margin-top: 12px;">
                        <strong>Summary:</strong><br>
                        📁 Folders synced: ${data.summary.folders_synced}<br>
                        📄 Files transferred: ${data.summary.files_transferred}<br>
                        💾 Data transferred: ${bytesFormatted}<br>
                        ⏱️ Duration: ${duration}<br>
                        🧹 Cleanup: ${cleanupStatus}
                        ${byExtLine}
                        <div style="margin-top:8px;color:var(--text-muted);font-size:12px;">Click to view full report</div>
                    </div>
                `;
            } else {
                // Fallback for older format
                resultDiv.innerHTML = `<h3>✅ ${data.message}</h3><pre>${data.output || ''}</pre>`;
            }
        } else {
            resultDiv.className = 'result-panel error';
            const brief = (data.error || data.output || '').split('\\n').slice(0,6).join('\\n');
            resultDiv.innerHTML = `<h3>❌ ${data.message}</h3><pre>${brief}\\n\\n(Click for full report)</pre>`;
            
            // Check for host key error
            if (data.host_key_error) {
                showHostKeyErrorModal(data.host_key_error);
            }
        }
    } catch (error) {
        resultDiv.className = 'result-panel error';
        resultDiv.innerHTML = `<h3>❌ Request failed</h3><p>${error.message}</p>`;
        // Keep progress bar visible if we might have a sync running
        progressDiv.style.display = 'none';
    }
}

function pollProgress(syncId) {
    let pollCount = 0;
    const maxPolls = 60; // 5 minutes at 5-second intervals
    
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const progressDetails = document.getElementById('progressDetails');
    const progressDiv = document.getElementById('progress');
    
    const poll = async () => {
        try {
            const data = await api.get(`/sync/progress/${syncId}`);
            
            if (data.success && data.progress) {
                const progress = data.progress;
                
                // Update progress bar
                progressBar.style.width = `${progress.progress_percent}%`;
                
                // Update progress text
                progressText.textContent = `${progress.current_stage}: ${progress.progress_percent}%`;
                
                // Update progress details
                let details = "";
                if (progress.total_folders > 0) {
                    details += `Folders: ${progress.completed_folders}/${progress.total_folders} `;
                }
                if (progress.current_folder) {
                    details += `Current: ${progress.current_folder}`;
                }
                progressDetails.textContent = details;
                
                // Show recent messages
                if (progress.messages && progress.messages.length > 0) {
                    const lastMessage = progress.messages[progress.messages.length - 1];
                    if (lastMessage && lastMessage.message) {
                        progressDetails.textContent = lastMessage.message;
                    }
                }
                
                // Check if completed or failed
                if (progress.status === 'completed' || progress.progress_percent >= 100) {
                    progressText.textContent = "Sync completed successfully!";
                    setTimeout(() => {
                        progressDiv.style.display = 'none';
                    }, 3000);
                    return;
                } else if (progress.status === 'error' || progress.status === 'failed') {
                    progressText.textContent = "Sync failed";
                    if (progress.messages && progress.messages.length > 0) {
                        const lastMessage = progress.messages[progress.messages.length - 1];
                        if (lastMessage && lastMessage.message) {
                            progressDetails.textContent = lastMessage.message;
                        }
                    }
                    setTimeout(() => {
                        progressDiv.style.display = 'none';
                    }, 3000);
                    return;
                }
                
                // Continue polling if not completed and under max polls
                if (pollCount < maxPolls && progress.status !== 'error') {
                    pollCount++;
                    setTimeout(poll, 5000); // Poll every 5 seconds
                } else {
                    // Timeout or error
                    if (pollCount >= maxPolls) {
                        progressText.textContent = "Progress polling timed out";
                    }
                    setTimeout(() => {
                        progressDiv.style.display = 'none';
                    }, 3000);
                }
            } else {
                // Progress not found or error
                progressText.textContent = "Progress tracking unavailable";
                setTimeout(() => {
                    progressDiv.style.display = 'none';
                }, 3000);
            }
        } catch (error) {
            console.error("Error polling progress:", error);
            progressText.textContent = `Progress error: ${error.message}`;
            setTimeout(() => {
                progressDiv.style.display = 'none';
            }, 3000);
        }
    };
    
    // Start polling immediately
    poll();
}

async function testSSH() {
    const resultDiv = document.getElementById('result');
    resultDiv.className = 'result-panel loading';
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '<h3>Testing SSH connectivity...</h3><p>Checking connections to all configured hosts.</p>';
    
    try {
        const data = await api.post('/test/ssh');
        
        if (data.success) {
            let output = `<h3>✅ SSH connectivity test completed</h3>`;
            output += `<p><strong>Summary:</strong><br>`;
            output += `Total hosts: ${data.summary.total_hosts}<br>`;
            output += `Successful: ${data.summary.successful}<br>`;
            output += `Failed: ${data.summary.failed}<br>`;
            output += `Success rate: ${data.summary.success_rate}</p>`;
            output += `<p><strong>Results:</strong></p><pre>`;
            
            for (const [host, result] of Object.entries(data.results)) {
                const status = result.success ? '✅' : '❌';
                output += `${status} ${host}: ${result.message}\\n`;
                if (!result.success && result.error) {
                    output += `    Error: ${result.error}\\n`;
                }
            }
            output += `</pre>`;
            
            resultDiv.className = 'result-panel success';
            resultDiv.innerHTML = output;
        } else {
            resultDiv.className = 'result-panel error';
            resultDiv.innerHTML = `<h3>❌ SSH test failed</h3><p>${data.message}</p><pre>${data.error || ''}</pre>`;
        }
    } catch (error) {
        resultDiv.className = 'result-panel error';
        resultDiv.innerHTML = `<h3>❌ Request failed</h3><p>${error.message}</p>`;
    }
}

// Sync Configuration Overlay functions

// Cache for sync configuration data - will be populated from API
let syncConfigCache = {
    forge: { ip: null, port: null, lastSync: null },
    comfy: { ip: null, port: null, lastSync: null },
    vastai: { sshConnection: '', instances: [] }
};

// Default fallback values (used when API doesn't provide config)
const SYNC_CONFIG_DEFAULTS = {
    forge: { ip: '10.0.78.108', port: '2222' },
    comfy: { ip: '10.0.78.108', port: '2223' }
};

/**
 * Fetch sync configuration from API
 */
async function fetchSyncConfig() {
    try {
        const data = await api.get('/status');
        if (data.success && data.sync_targets) {
            if (data.sync_targets.forge) {
                syncConfigCache.forge.ip = data.sync_targets.forge.host || SYNC_CONFIG_DEFAULTS.forge.ip;
                syncConfigCache.forge.port = data.sync_targets.forge.port || SYNC_CONFIG_DEFAULTS.forge.port;
            }
            if (data.sync_targets.comfy) {
                syncConfigCache.comfy.ip = data.sync_targets.comfy.host || SYNC_CONFIG_DEFAULTS.comfy.ip;
                syncConfigCache.comfy.port = data.sync_targets.comfy.port || SYNC_CONFIG_DEFAULTS.comfy.port;
            }
        }
    } catch (e) {
        // Use defaults on API error
        console.warn('Failed to fetch sync config, using defaults:', e);
        syncConfigCache.forge.ip = SYNC_CONFIG_DEFAULTS.forge.ip;
        syncConfigCache.forge.port = SYNC_CONFIG_DEFAULTS.forge.port;
        syncConfigCache.comfy.ip = SYNC_CONFIG_DEFAULTS.comfy.ip;
        syncConfigCache.comfy.port = SYNC_CONFIG_DEFAULTS.comfy.port;
    }
}

/**
 * Open the sync configuration overlay for a specific sync type
 * @param {string} syncType - 'forge', 'comfy', or 'vastai'
 */
async function openSyncConfigOverlay(syncType) {
    const overlay = document.getElementById('syncConfigOverlay');
    const title = document.getElementById('syncConfigTitle');
    const content = document.getElementById('syncConfigContent');
    
    // Set the title based on sync type
    const titles = {
        forge: '🔥 Forge Sync Configuration',
        comfy: '🖼️ Comfy Sync Configuration',
        vastai: '☁️ VastAI Sync Configuration'
    };
    title.textContent = titles[syncType] || 'Sync Configuration';
    
    // Show loading state
    content.innerHTML = '<div class="sync-config-loading">Loading configuration...</div>';
    overlay.style.display = 'flex';
    
    // Fetch config from API if not already loaded (for local targets)
    if (syncType !== 'vastai' && !syncConfigCache[syncType].ip) {
        await fetchSyncConfig();
    }
    
    if (syncType === 'vastai') {
        await renderVastAIConfig(content);
    } else {
        await renderLocalConfig(content, syncType);
    }
}

/**
 * Close the sync configuration overlay
 */
function closeSyncConfigOverlay() {
    const overlay = document.getElementById('syncConfigOverlay');
    overlay.style.display = 'none';
}

/**
 * Render the configuration for local sync (Forge or Comfy)
 */
async function renderLocalConfig(content, syncType) {
    // Fetch last sync info
    let lastSyncInfo = null;
    try {
        const logsData = await api.get('/logs/manifest');
        if (logsData.success && logsData.logs) {
            // Find most recent sync of this type
            lastSyncInfo = logsData.logs.find(log => log.sync_type === syncType);
        }
    } catch (e) {
        console.error('Failed to fetch sync logs:', e);
    }
    
    // Get config from cache, with fallback to defaults
    const config = syncConfigCache[syncType];
    const ip = config.ip || SYNC_CONFIG_DEFAULTS[syncType]?.ip || 'N/A';
    const port = config.port || SYNC_CONFIG_DEFAULTS[syncType]?.port || 'N/A';
    const ipAddress = `${ip}:${port}`;
    
    // Format last sync info
    let lastSyncHtml = '';
    if (lastSyncInfo) {
        const date = new Date(lastSyncInfo.timestamp);
        const formattedDate = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        const formattedTime = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        const statusClass = lastSyncInfo.success ? 'sync-status-success' : 'sync-status-failed';
        const statusText = lastSyncInfo.success ? '✅ Success' : '❌ Failed';
        const duration = lastSyncInfo.duration_seconds ? ` (${lastSyncInfo.duration_seconds}s)` : '';
        
        lastSyncHtml = `
            <div class="sync-config-item">
                <div class="sync-config-label">Last Sync</div>
                <div class="sync-config-value">
                    <span class="${statusClass}">${statusText}</span>
                    <span class="sync-time">${formattedDate}, ${formattedTime}${duration}</span>
                </div>
            </div>
        `;
    } else {
        lastSyncHtml = `
            <div class="sync-config-item">
                <div class="sync-config-label">Last Sync</div>
                <div class="sync-config-value">
                    <span class="sync-status-none">Never synced</span>
                </div>
            </div>
        `;
    }
    
    content.innerHTML = `
        <div class="sync-config-section">
            <div class="sync-config-item">
                <div class="sync-config-label">IP Address</div>
                <div class="sync-config-value sync-config-ip">${escapeHtml(ipAddress)}</div>
            </div>
            ${lastSyncHtml}
        </div>
        <div class="sync-config-actions">
            <button class="setup-button" onclick="testConnection('${syncType}')">
                🔧 Test Connection
            </button>
            <button class="setup-button secondary" onclick="closeSyncConfigOverlay()">
                Close
            </button>
        </div>
        <div id="syncConfigResult-${syncType}" class="sync-config-result"></div>
    `;
}

/**
 * Render the configuration for VastAI sync
 */
async function renderVastAIConfig(content) {
    // Get current SSH connection string from other tabs (if set)
    const vastaiInput = document.getElementById('sshConnectionString');
    const resourcesInput = document.getElementById('resourcesSshConnectionString');
    const createInput = document.getElementById('createSshConnectionString');
    const currentSSH = vastaiInput?.value || resourcesInput?.value || createInput?.value || '';
    
    // Store in cache
    syncConfigCache.vastai.sshConnection = currentSSH;
    
    content.innerHTML = `
        <div class="sync-config-section">
            <!-- VastAI Instances Section -->
            <div class="sync-vastai-instances">
                <h4>🖥️ Active VastAI Instances</h4>
                <div class="instances-buttons">
                    <button class="setup-button secondary" onclick="loadVastaiInstancesForSync()">
                        🔄 Load Instances
                    </button>
                </div>
                <div id="sync-vastai-instances-list" class="instances-list">
                    <div class="no-instances-message">Click "Load Instances" to see your active VastAI instances</div>
                </div>
            </div>
            
            <hr style="margin: 16px 0; border: 1px solid var(--background-modifier-border);">
            
            <!-- SSH Connection String -->
            <div class="sync-config-item">
                <div class="sync-config-label">SSH Connection String</div>
                <div class="sync-config-ssh-field">
                    <input type="text" id="syncSshConnectionString" 
                           placeholder="ssh -p 2838 root@104.189.178.116 -L 8080:localhost:8080"
                           value="${escapeHtml(currentSSH)}"
                           title="Enter the SSH connection string from your VastAI instance">
                </div>
                <div class="sync-config-hint">Required for Sync VastAI operation</div>
            </div>
        </div>
        <div class="sync-config-actions">
            <button class="setup-button" onclick="testVastAIConnection()">
                🔧 Test Connection
            </button>
            <button class="setup-button" onclick="saveVastAISSHAndClose()">
                ✓ Save & Close
            </button>
            <button class="setup-button secondary" onclick="closeSyncConfigOverlay()">
                Cancel
            </button>
        </div>
        <div id="syncConfigResult-vastai" class="sync-config-result"></div>
    `;
}

/**
 * Helper function to escape HTML to prevent XSS
 */
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/**
 * Test connection for a local sync target
 */
async function testConnection(syncType) {
    const resultDiv = document.getElementById(`syncConfigResult-${syncType}`);
    resultDiv.className = 'sync-config-result sync-config-result-loading';
    resultDiv.textContent = 'Testing connection...';
    
    try {
        const data = await api.post('/test/ssh', { targets: [syncType] });
        
        if (data.success && data.results) {
            // Build host key using cached config values
            const config = syncConfigCache[syncType];
            const ip = config.ip || SYNC_CONFIG_DEFAULTS[syncType]?.ip;
            const port = config.port || SYNC_CONFIG_DEFAULTS[syncType]?.port;
            const hostKey = `${syncType}:${ip}:${port}`;
            const result = data.results[syncType] || data.results[hostKey] || Object.values(data.results)[0];
            
            if (result && result.success) {
                resultDiv.className = 'sync-config-result sync-config-result-success';
                resultDiv.textContent = `✅ Connection successful: ${result.message}`;
            } else if (result && result.host_verification_needed) {
                // Show host verification modal
                resultDiv.className = 'sync-config-result sync-config-result-loading';
                resultDiv.textContent = '🔐 Host verification required...';
                
                try {
                    // Get the host info for verification
                    const hostInfo = {
                        ssh_host: ip,
                        ssh_port: port,
                        host_alias: syncType
                    };
                    
                    // Show the host verification modal
                    const userAccepted = await window.VastAIUI.showSSHHostVerificationModal(hostInfo);
                    
                    if (userAccepted) {
                        resultDiv.className = 'sync-config-result sync-config-result-success';
                        resultDiv.textContent = '✅ Host key verified and connection successful';
                    } else {
                        resultDiv.className = 'sync-config-result sync-config-result-error';
                        resultDiv.textContent = '❌ Host verification cancelled by user';
                    }
                } catch (modalError) {
                    console.error('Host verification modal error:', modalError);
                    resultDiv.className = 'sync-config-result sync-config-result-error';
                    resultDiv.textContent = `❌ Host verification error: ${modalError.message}`;
                }
            } else {
                resultDiv.className = 'sync-config-result sync-config-result-error';
                resultDiv.textContent = `❌ Connection failed: ${result?.message || 'Unknown error'}`;
            }
        } else {
            resultDiv.className = 'sync-config-result sync-config-result-error';
            resultDiv.textContent = `❌ Test failed: ${data.message || 'Unknown error'}`;
        }
    } catch (error) {
        resultDiv.className = 'sync-config-result sync-config-result-error';
        resultDiv.textContent = `❌ Request failed: ${error.message}`;
    }
}

/**
 * Test VastAI SSH connection
 */
async function testVastAIConnection() {
    const resultDiv = document.getElementById('syncConfigResult-vastai');
    const sshInput = document.getElementById('syncSshConnectionString');
    const sshConnection = sshInput?.value?.trim();
    
    if (!sshConnection) {
        resultDiv.className = 'sync-config-result sync-config-result-error';
        resultDiv.textContent = '❌ Please enter an SSH connection string first';
        return;
    }
    
    resultDiv.className = 'sync-config-result sync-config-result-loading';
    resultDiv.textContent = 'Testing connection...';
    
    try {
        const data = await api.post('/ssh/test', { ssh_connection: sshConnection });
        
        if (data.success) {
            resultDiv.className = 'sync-config-result sync-config-result-success';
            resultDiv.textContent = `✅ Connection successful: ${data.message}`;
        } else if (data.host_verification_needed) {
            // Show host verification modal
            resultDiv.className = 'sync-config-result sync-config-result-loading';
            resultDiv.textContent = '🔐 Host verification required...';
            
            try {
                const hostInfo = {
                    ssh_host: data.ssh_host,
                    ssh_port: data.ssh_port,
                    ssh_connection: sshConnection
                };
                
                // Show the host verification modal
                const userAccepted = await window.VastAIUI.showSSHHostVerificationModal(hostInfo);
                
                if (userAccepted) {
                    resultDiv.className = 'sync-config-result sync-config-result-success';
                    resultDiv.textContent = '✅ Host key verified and connection successful';
                } else {
                    resultDiv.className = 'sync-config-result sync-config-result-error';
                    resultDiv.textContent = '❌ Host verification cancelled by user';
                }
            } catch (modalError) {
                console.error('Host verification modal error:', modalError);
                resultDiv.className = 'sync-config-result sync-config-result-error';
                resultDiv.textContent = `❌ Host verification error: ${modalError.message}`;
            }
        } else {
            resultDiv.className = 'sync-config-result sync-config-result-error';
            resultDiv.textContent = `❌ Connection failed: ${data.message || 'Unknown error'}`;
        }
    } catch (error) {
        resultDiv.className = 'sync-config-result sync-config-result-error';
        resultDiv.textContent = `❌ Request failed: ${error.message}`;
    }
}

/**
 * Load VastAI instances for the sync config overlay
 */
async function loadVastaiInstancesForSync() {
    const instancesList = document.getElementById('sync-vastai-instances-list');
    if (instancesList) {
        instancesList.innerHTML = '<div class="no-instances-message">Loading instances...</div>';
    }

    try {
        const data = await api.get('/vastai/instances');
        if (!data || data.success === false) {
            const msg = (data && data.message) ? data.message : 'Failed to load instances';
            if (instancesList) {
                instancesList.innerHTML = `<div class="no-instances-message" style="color: var(--text-error);">❌ ${escapeHtml(msg)}</div>`;
            }
            return;
        }

        const rawInstances = Array.isArray(data.instances) ? data.instances : [];
        
        // Normalize instances with proper error handling
        const instances = rawInstances.map(inst => {
            // Use VastAIInstances module if available, otherwise apply basic normalization
            if (window.VastAIInstances && typeof window.VastAIInstances.normalizeInstance === 'function') {
                return window.VastAIInstances.normalizeInstance(inst);
            }
            // Fallback basic normalization
            return {
                id: inst.id || inst.instance_id,
                status: inst.actual_status || inst.status || 'unknown',
                gpu: inst.gpu_name || inst.gpu || 'Unknown GPU',
                gpu_count: inst.num_gpus || 1,
                geolocation: inst.geolocation || 'N/A',
                ssh_host: inst.public_ipaddr || inst.ssh_host,
                ssh_port: inst.ssh_port || inst.direct_port_ssh
            };
        });
        
        displayVastaiInstancesForSync(instances);
    } catch (error) {
        if (instancesList) {
            instancesList.innerHTML = `<div class="no-instances-message" style="color: var(--text-error);">❌ Error: ${escapeHtml(error.message)}</div>`;
        }
    }
}

/**
 * Display VastAI instances in the sync config overlay
 */
function displayVastaiInstancesForSync(instances) {
    const instancesList = document.getElementById('sync-vastai-instances-list');

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
        const normalizedStatus = instance.status || 'unknown';
        const sshConnection = buildSSHStringForSync(instance);
        
        const instanceId = typeof instance.id === 'number' ? instance.id : parseInt(instance.id, 10);
        if (isNaN(instanceId)) {
            console.warn('Invalid instance ID:', instance.id);
            return;
        }

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
        instanceStatus.textContent = normalizedStatus;
        
        instanceHeader.appendChild(instanceTitle);
        instanceHeader.appendChild(instanceStatus);
        
        const instanceDetails = document.createElement('div');
        instanceDetails.className = 'instance-details';
        
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
        instanceDetails.appendChild(createDetail('Location:', ` ${instance.geolocation || 'N/A'}`));
        
        const instanceActions = document.createElement('div');
        instanceActions.className = 'instance-actions';
        
        const actionButton = document.createElement('button');
        actionButton.className = 'use-instance-btn';
        
        if (sshConnection && normalizedStatus === 'running') {
            actionButton.textContent = '🔗 Use This Instance';
            actionButton.addEventListener('click', function() {
                useInstanceForSync(sshConnection, instanceId);
            });
        } else {
            actionButton.textContent = '⚠️ Not Available';
            actionButton.disabled = true;
            actionButton.style.opacity = '0.5';
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

/**
 * Build SSH string for sync overlay
 */
function buildSSHStringForSync(inst) {
    if (!inst.ssh_host || !inst.ssh_port) return null;
    return `ssh -p ${inst.ssh_port} root@${inst.ssh_host} -L 8080:localhost:8080`;
}

/**
 * Use instance SSH connection string in sync config overlay
 */
function useInstanceForSync(sshConnection, instanceId) {
    const syncInput = document.getElementById('syncSshConnectionString');
    
    if (syncInput) {
        syncInput.value = sshConnection;
    }
    
    // Also update the cache
    syncConfigCache.vastai.sshConnection = sshConnection;
    
    // Store instance ID globally
    if (instanceId) {
        window.currentInstanceId = instanceId;
        console.log(`📌 Set current instance ID: ${instanceId}`);
    }
    
    // Show brief confirmation
    const resultDiv = document.getElementById('syncConfigResult-vastai');
    if (resultDiv) {
        resultDiv.className = 'sync-config-result sync-config-result-success';
        resultDiv.textContent = '✅ SSH connection string set';
        setTimeout(() => {
            resultDiv.textContent = '';
            resultDiv.className = 'sync-config-result';
        }, 2000);
    }
}

/**
 * Save VastAI SSH connection and close overlay
 */
function saveVastAISSHAndClose() {
    const syncInput = document.getElementById('syncSshConnectionString');
    const sshConnection = syncInput?.value?.trim() || '';
    
    // Save to all SSH inputs for cross-tab sync
    const vastaiInput = document.getElementById('sshConnectionString');
    const resourcesInput = document.getElementById('resourcesSshConnectionString');
    const createInput = document.getElementById('createSshConnectionString');
    
    if (vastaiInput) vastaiInput.value = sshConnection;
    if (resourcesInput) resourcesInput.value = sshConnection;
    if (createInput) createInput.value = sshConnection;
    
    // Update cache
    syncConfigCache.vastai.sshConnection = sshConnection;
    
    closeSyncConfigOverlay();
}

/**
 * Sync VastAI with SSH connection string check
 */
async function syncVastAI() {
    // Check if SSH connection string is set
    const vastaiInput = document.getElementById('sshConnectionString');
    const resourcesInput = document.getElementById('resourcesSshConnectionString');
    const createInput = document.getElementById('createSshConnectionString');
    const sshConnection = vastaiInput?.value?.trim() || resourcesInput?.value?.trim() || createInput?.value?.trim() || syncConfigCache.vastai.sshConnection;
    
    if (!sshConnection) {
        // Show error and open config overlay
        const resultDiv = document.getElementById('result');
        resultDiv.className = 'result-panel error';
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = `<h3>⚠️ SSH Connection Required</h3><p>Please configure the SSH Connection String before syncing VastAI.</p><p>Click the ⚙️ button next to "Sync VastAI" to configure.</p>`;
        
        // Open the config overlay
        setTimeout(() => openSyncConfigOverlay('vastai'), 500);
        return;
    }
    
    // Proceed with normal sync
    sync('vastai');
}