// VastAI setup and instances UI functionality

async function setUIHome() {
    const sshConnectionString = document.getElementById('sshConnectionString').value.trim();
    const resultDiv = document.getElementById('setup-result');
    
    if (!sshConnectionString) {
        showSetupResult('Please enter an SSH connection string first.', 'error');
        return;
    }
    
    showSetupResult('Setting UI_HOME to /workspace/ComfyUI/...', 'info');
    
    try {
        const data = await api.post('/vastai/set-ui-home', {
            ssh_connection: sshConnectionString,
            ui_home: '/workspace/ComfyUI/'
        });
        
        if (data.success) {
            showSetupResult(data.message, 'success');
        } else {
            showSetupResult('Error: ' + data.message, 'error');
        }
    } catch (error) {
        showSetupResult('Request failed: ' + error.message, 'error');
    }
}

async function getUIHome() {
    const sshConnectionString = document.getElementById('sshConnectionString').value.trim();
    
    if (!sshConnectionString) {
        showSetupResult('Please enter an SSH connection string first.', 'error');
        return;
    }
    
    showSetupResult('Reading UI_HOME...', 'info');
    
    try {
        const data = await api.post('/vastai/get-ui-home', {
            ssh_connection: sshConnectionString
        });
        
        if (data.success) {
            showSetupResult('UI_HOME: ' + data.ui_home, 'success');
        } else {
            showSetupResult('Error: ' + data.message, 'error');
        }
    } catch (error) {
        showSetupResult('Request failed: ' + error.message, 'error');
    }
}

async function terminateConnection() {
    const sshConnectionString = document.getElementById('sshConnectionString').value.trim();
    
    if (!sshConnectionString) {
        showSetupResult('Please enter an SSH connection string first.', 'error');
        return;
    }
    
    if (!confirm('Are you sure you want to terminate the SSH connection?')) {
        return;
    }
    
    showSetupResult('Terminating SSH connection...', 'info');
    
    try {
        const data = await api.post('/vastai/terminate-connection', {
            ssh_connection: sshConnectionString
        });
        
        if (data.success) {
            showSetupResult(data.message, 'success');
        } else {
            showSetupResult('Error: ' + data.message, 'error');
        }
    } catch (error) {
        showSetupResult('Request failed: ' + error.message, 'error');
    }
}

async function setupCivitDL() {
    const sshConnectionString = document.getElementById('sshConnectionString').value.trim();
    
    if (!sshConnectionString) {
        showSetupResult('Please enter an SSH connection string first.', 'error');
        return;
    }
    
    showSetupResult('Installing and configuring CivitDL...', 'info');
    
    try {
        const data = await api.post('/vastai/setup-civitdl', {
            ssh_connection: sshConnectionString
        });
        
        if (data.success) {
            // Show output with newlines preserved
            const outputDiv = document.getElementById('setup-result');
            outputDiv.innerHTML = '<strong>CivitDL Setup Completed Successfully!</strong><br><br>' +
                                '<strong>Output:</strong><pre style="white-space: pre-wrap; margin-top: 8px;">' + 
                                (data.output || '').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</pre>';
            outputDiv.className = 'setup-result success';
            outputDiv.style.display = 'block';
        } else {
            showSetupResult('Error: ' + data.message + (data.output ? '\\n\\nOutput:\\n' + data.output : ''), 'error');
        }
    } catch (error) {
        showSetupResult('Request failed: ' + error.message, 'error');
    }
}

async function syncFromConnectionString() {
    const sshConnectionString = document.getElementById('sshConnectionString').value.trim();
    
    if (!sshConnectionString) {
        showSetupResult('Please enter an SSH connection string first.', 'error');
        return;
    }
    
    showSetupResult('Starting sync from connection string...', 'info');
    
    try {
        const data = await api.post('/sync/vastai-connection', {
            ssh_connection: sshConnectionString,
            cleanup: true  // Default cleanup to true
        });
        
        if (data.success) {
            // Show success message first
            showSetupResult('Sync started successfully! Check sync tab for progress.', 'success');
            
            // Switch to sync tab to show progress
            showTab('sync');
            
            // Show sync results in the main result panel
            const resultDiv = document.getElementById('result');
            const progressDiv = document.getElementById('progress');
            
            resultDiv.className = 'result-panel loading';
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<h3>Starting VastAI sync from connection string...</h3><p>This may take several minutes.</p>';
            
            // Start polling for progress if sync_id is available 
            if (data.sync_id) {
                progressDiv.style.display = 'block';
                const progressBar = document.getElementById('progressBar');
                const progressText = document.getElementById('progressText');
                const progressDetails = document.getElementById('progressDetails');
                progressBar.style.width = '0%';
                progressText.textContent = 'Starting sync...';
                progressDetails.textContent = '';
                
                pollProgress(data.sync_id);
            }
            
            // Update result panel with final result after a short delay
            setTimeout(() => {
                if (data.summary) {
                    const duration = data.summary.duration_seconds ? 
                        `${Math.round(data.summary.duration_seconds)}s` : 'Unknown';
                    const bytesFormatted = data.summary.bytes_transferred > 0 ?
                        formatBytes(data.summary.bytes_transferred) : '0 bytes';
                    const cleanupStatus = data.summary.cleanup_enabled ? 'enabled' : 'disabled';

                    let byExtLine = '';
                    if (data.summary.by_ext) {
                        const pairs = Object.entries(data.summary.by_ext)
                          .sort((a,b)=>b[1]-a[1]).slice(0,4)
                          .map(([k,v]) => `${k}:${v}`).join(' · ');
                        if (pairs) byExtLine = `<br>🧩 By type: ${pairs}`;
                    }
                    
                    resultDiv.className = 'result-panel success';
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
                    resultDiv.className = 'result-panel success';
                    resultDiv.innerHTML = `<h3>✅ ${data.message}</h3><pre>${data.output || ''}</pre>`;
                }
            }, 1000);
            
        } else {
            showSetupResult('Error: ' + data.message, 'error');
        }
    } catch (error) {
        showSetupResult('Request failed: ' + error.message, 'error');
    }
}

async function loadVastaiInstances() {
    const instancesList = document.getElementById('vastai-instances-list');
    instancesList.innerHTML = '<div class="no-instances-message">Loading instances...</div>';
    
    try {
        const data = await api.get('/vastai/instances');
        
        if (data.success) {
            displayVastaiInstances(data.instances);
        } else {
            instancesList.innerHTML = '<div class="no-instances-message" style="color: var(--text-error);">Error: ' + data.message + '</div>';
        }
    } catch (error) {
        instancesList.innerHTML = '<div class="no-instances-message" style="color: var(--text-error);">Request failed: ' + error.message + '</div>';
    }
}

function displayVastaiInstances(instances) {
    const instancesList = document.getElementById('vastai-instances-list');
    
    if (!instances || instances.length === 0) {
        instancesList.innerHTML = '<div class="no-instances-message">No active VastAI instances found</div>';
        return;
    }
    
    let html = '';
    instances.forEach(instance => {
        const statusClass = instance.status ? instance.status.toLowerCase() : 'unknown';
        const sshConnection = instance.ssh_host && instance.ssh_port ? 
            `ssh -p ${instance.ssh_port} root@${instance.ssh_host} -L 8080:localhost:8080` : 'N/A';
        
        html += `
            <div class="instance-item">
                <div class="instance-header">
                    <div class="instance-title">Instance #${instance.id}</div>
                    <div class="instance-status ${statusClass}">${instance.status || 'Unknown'}</div>
                </div>
                <div class="instance-details">
                    <div class="instance-detail"><strong>GPU:</strong> ${instance.gpu || 'N/A'} ${instance.gpu_count ? '(' + instance.gpu_count + 'x)' : ''}</div>
                    <div class="instance-detail"><strong>GPU RAM:</strong> ${instance.gpu_ram_gb || 0} GB</div>
                    <div class="instance-detail"><strong>Location:</strong> ${instance.geolocation || 'N/A'}</div>
                    <div class="instance-detail"><strong>Cost:</strong> $${instance.cost_per_hour || 0}/hr</div>
                    <div class="instance-detail"><strong>SSH Host:</strong> ${instance.ssh_host || 'N/A'}</div>
                    <div class="instance-detail"><strong>SSH Port:</strong> ${instance.ssh_port || 'N/A'}</div>
                </div>
                ${instance.ssh_host && instance.ssh_port && instance.status === 'running' ? `
                <div class="instance-actions">
                    <button class="use-instance-btn" onclick="useInstance('${sshConnection}')">
                        📋 Use This Instance
                    </button>
                </div>
                ` : ''}
            </div>
        `;
    });
    
    instancesList.innerHTML = html;
}

function useInstance(sshConnection) {
    const sshInput = document.getElementById('sshConnectionString');
    sshInput.value = sshConnection;
    showSetupResult('SSH connection string copied to input field', 'success');
}

function showSetupResult(message, type) {
    const resultDiv = document.getElementById('setup-result');
    resultDiv.textContent = message;
    resultDiv.className = 'setup-result ' + type;
    resultDiv.style.display = 'block';
    
    // Auto-hide info messages after 5 seconds
    if (type === 'info') {
        setTimeout(() => {
            if (resultDiv.classList.contains('info')) {
                resultDiv.style.display = 'none';
            }
        }, 5000);
    }
}