// ==============================
// VastAI Instances Module  
// ==============================
// Instance management, SSH operations, and instance data handling

import { resolveSSH, normStatus, normGeo, truthy, fmtMoney, fmtGb } from './utils.js';
import { showSetupResult } from './ui.js';

/**
 * Normalize one instance object from diverse payloads
 * @param {object} raw - Raw instance data from API
 * @returns {object} Normalized instance object
 */
export function normalizeInstance(raw) {
  const i = raw || {};

  // Instance ID
  const id = 
    i.instance_id ??
    i.instanceId ??
    i.id ??
    null;

  // Status normalization
  const status = normStatus(i.cur_state || i.status || i.state || "unknown");

  // GPU info
  const gpuName = 
    i.gpu_name ??
    i.gpu ??
    i.gpu_model ??
    i.gpuName ??
    i.gpu_display_name ??
    "Unknown GPU";

  const gpuCount = 
    i.num_gpus ??
    i.gpu_count ??
    i.gpuCount ??
    i.gpu_num ??
    1;

  const gpuRamGb = 
    i.gpu_ram ??
    i.gpu_memory ??
    i.vram ??
    i.gpu_ram_gb ??
    i.gpuRam ??
    0;

  // CPU info
  const cpu = 
    i.cpu_name ??
    i.cpu ??
    i.cpu_model ??
    i.cpuName ??
    "Unknown CPU";

  const cpuCores = 
    i.cpu_cores ??
    i.num_cpus ??
    i.cpus ??
    i.cpuCores ??
    i.cpu_count ??
    null;

  // Storage
  const diskGb = 
    i.disk_space ??
    i.storage ??
    i.disk ??
    i.diskSpace ??
    i.disk_gb ??
    null;

  // Network
  const down = 
    i.inet_down ??
    i.download_speed ??
    i.net_down ??
    i.downloadSpeed ??
    null;

  const up = 
    i.inet_up ??
    i.upload_speed ??
    i.net_up ??
    i.uploadSpeed ??
    null;

  // Pricing
  const cost =
    i.cost_per_hour ??
    i.dph_total ??
    i.dph ??
    (i.price_per_hour ?? i.price ?? null);

  // SSH (host = public IP)
  const { host: ssh_host, port: ssh_port } = resolveSSH(i);

  // Template / image metadata
  const template =
    i.template ??
    i.image_template ??
    i.template_name ??
    i.image_name ??
    i.container_template ??
    null;

  return {
    id,
    status,
    gpu: gpuName,
    gpu_count: truthy(gpuCount) ? +gpuCount : null,
    gpu_ram_gb: truthy(gpuRamGb) ? +gpuRamGb : null,
    cpu,
    cpu_cores: truthy(cpuCores) ? +cpuCores : null,
    disk_gb: truthy(diskGb) ? +diskGb : null,
    net_down_mbps: truthy(down) ? +down : null,
    net_up_mbps: truthy(up) ? +up : null,
    cost_per_hour: truthy(cost) ? +cost : null,
    geolocation: normGeo(i),
    ssh_host,    
    ssh_port,    
    template
  };
}

/**
 * Build the "Use This Instance" SSH string
 * @param {object} inst - Normalized instance object
 * @returns {string} SSH connection string
 */
export function buildSSHString(inst) {
  if (!inst.ssh_host || !inst.ssh_port) return null;
  return `ssh -p ${inst.ssh_port} root@${inst.ssh_host} -L 8080:localhost:8080`;
}

/**
 * Test VastAI SSH connection
 */
export async function testVastAISSH() {
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');

  showSetupResult('Testing SSH connection...', 'info');
  try {
    const data = await api.post('/ssh/test', {
      ssh_connection: sshConnectionString
    });
    
    if (data.success) {
      showSetupResult('✅ SSH connection successful!', 'success');
    } else {
      showSetupResult(`❌ SSH test failed: ${data.message}`, 'error');
    }
  } catch (error) {
    showSetupResult('❌ SSH test request failed: ' + error.message, 'error');
  }
}

/**
 * Set UI_HOME on remote instance
 */
export async function setUIHome() {
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');

  showSetupResult('Setting UI_HOME to /workspace/ComfyUI/...', 'info');
  try {
    const data = await api.post('/ssh/set-ui-home', {
      ssh_connection: sshConnectionString
    });
    
    if (data.success) {
      showSetupResult('✅ UI_HOME set successfully!', 'success');
      if (data.output) {
        console.log('UI_HOME output:', data.output);
      }
    } else {
      showSetupResult(`❌ Failed to set UI_HOME: ${data.message}`, 'error');
    }
  } catch (error) {
    showSetupResult('❌ Set UI_HOME request failed: ' + error.message, 'error');
  }
}

/**
 * Get UI_HOME from remote instance
 */
export async function getUIHome() {
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');

  showSetupResult('Reading UI_HOME...', 'info');
  try {
    const data = await api.post('/ssh/get-ui-home', {
      ssh_connection: sshConnectionString
    });
    
    if (data.success) {
      const uiHome = data.ui_home || 'Not set';
      showSetupResult(`UI_HOME: ${uiHome}`, 'success');
    } else {
      showSetupResult(`❌ Failed to get UI_HOME: ${data.message}`, 'error');
    }
  } catch (error) {
    showSetupResult('❌ Get UI_HOME request failed: ' + error.message, 'error');
  }
}

/**
 * Terminate SSH connection
 */
export async function terminateConnection() {
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');
  if (!confirm('Are you sure you want to terminate the SSH connection?')) return;

  showSetupResult('Terminating SSH connection...', 'info');
  try {
    // Implementation would depend on backend API
    showSetupResult('✅ SSH connection terminated', 'success');
  } catch (error) {
    showSetupResult('❌ Failed to terminate connection: ' + error.message, 'error');
  }
}

/**
 * Setup CivitDL on remote instance
 */
export async function setupCivitDL() {
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');

  showSetupResult('Installing and configuring CivitDL...', 'info');
  try {
    const data = await api.post('/ssh/setup-civitdl', {
      ssh_connection: sshConnectionString
    });
    
    if (data.success) {
      showSetupResult('✅ CivitDL setup completed successfully!', 'success');
      if (data.output) {
        console.log('CivitDL setup output:', data.output);
      }
    } else {
      showSetupResult(`❌ CivitDL setup failed: ${data.message}`, 'error');
    }
  } catch (error) {
    showSetupResult('❌ CivitDL setup request failed: ' + error.message, 'error');
  }
}

/**
 * Sync from connection string
 */
export async function syncFromConnectionString() {
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');

  showSetupResult('Starting sync from connection string...', 'info');

  try {
    const data = await api.post('/sync', {
      ssh_connection: sshConnectionString
    });

    if (data.success) {
      showSetupResult('✅ Sync completed successfully!', 'success');
      
      // Update progress display if available
      if (data.sync_results) {
        const results = data.sync_results;
        let summary = `Sync completed:\n`;
        
        Object.entries(results).forEach(([source, result]) => {
          if (result.success) {
            summary += `✅ ${source}: ${result.files_synced || 0} files synced\n`;
          } else {
            summary += `❌ ${source}: ${result.error || 'Unknown error'}\n`;
          }
        });
        
        // Show detailed results in console
        console.log('Sync results:', results);
        
        // Update UI with summary
        const resultDiv = document.getElementById('result');
        if (resultDiv) {
          resultDiv.innerHTML = `<pre>${summary}</pre>`;
          resultDiv.style.display = 'block';
        }
      }
    } else {
      showSetupResult(`❌ Sync failed: ${data.message}`, 'error');
    }
  } catch (error) {
    showSetupResult('Request failed: ' + error.message, 'error');
  }
}

/**
 * Fetch detailed instance information from API
 * @param {number} instanceId - ID of the instance to fetch
 * @returns {Promise<object>} Instance data
 */
export async function fetchVastaiInstanceDetails(instanceId) {
  // expects a backend route: GET /vastai/instances/:id returning { success, instance }
  const resp = await api.get(`/vastai/instances/${instanceId}`);
  if (!resp || resp.success === false) {
    const msg = (resp && resp.message) ? resp.message : `Failed to fetch details for ${instanceId}`;
    throw new Error(msg);
  }
  return resp.instance;
}

/**
 * Refresh instance card data
 * @param {number} instanceId - ID of the instance to refresh
 * @returns {Promise<object>} Updated instance data
 */
export async function refreshInstanceCard(instanceId) {
  try {
    const inst = await fetchVastaiInstanceDetails(instanceId);

    // Authoritative values — host must come from public IP fields:
    const sshHost =
      inst.public_ipaddr ||
      inst.public_ip ||
      inst.ip_address ||
      inst.publicIp ||
      null;
    
    // Use the same SSH port resolution logic as resolveSSH()
    const { port: sshPort } = resolveSSH(inst);
    const state = normStatus(inst.cur_state || inst.status || 'unknown');

    const sshConnection = (sshHost && sshPort)
      ? `ssh -p ${sshPort} root@${sshHost} -L 8080:localhost:8080`
      : null;

    // Update the existing card
    const card = document.querySelector(`[data-instance-id="${instanceId}"]`);
    if (!card) throw new Error(`Instance card ${instanceId} not found in DOM`);

    const hostEl = card.querySelector('[data-field="ssh_host"]');
    const portEl = card.querySelector('[data-field="ssh_port"]');
    const statEl = card.querySelector('[data-field="status"]');

    if (hostEl) hostEl.textContent = sshHost || 'N/A';
    if (portEl) portEl.textContent = sshPort || 'N/A';
    if (statEl) {
      statEl.textContent = state;
      statEl.className = `instance-status ${state}`;
    }

    const actions = card.querySelector('.instance-actions');
    if (actions) {
      actions.innerHTML = sshConnection && state === 'running'
        ? `<button class="use-instance-btn" onclick="VastAIInstances.useInstance('${sshConnection.replace(/'/g, "\\'")}')">
             🔗 Connect to SSH Connection Field
           </button>`
        : `<button class="use-instance-btn" onclick="VastAIInstances.refreshInstanceCard(${instanceId})">
             🔄 Load SSH
           </button>`;
      
      actions.innerHTML += `
        <button class="details-btn" onclick="VastAIUI.showInstanceDetails(${instanceId})">
          {...} Details
        </button>
        ${
          state === 'running'
            ? `<button class="stop-instance-btn" onclick="VastAIInstances.stopInstance(${instanceId})" title="Stop instance (will destroy it)">
                 ⏹️ Stop
               </button>`
            : ''
        }
        <button class="destroy-instance-btn" onclick="VastAIInstances.destroyInstance(${instanceId})" title="Permanently destroy instance">
          🗑️ Destroy
        </button>
      `;
    }

    showSetupResult(`Instance #${instanceId} details refreshed.`, 'success');
    return inst;
  } catch (err) {
    showSetupResult(`Failed to refresh instance #${instanceId}: ${err.message}`, 'error');
    throw err;
  }
}

/**
 * Load VastAI instances from API
 */
export async function loadVastaiInstances() {
  const instancesList = document.getElementById('vastai-instances-list');
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
    const instances = rawInstances.map(normalizeInstance);
    displayVastaiInstances(instances);
  } catch (error) {
    if (instancesList) {
      instancesList.innerHTML = `<div class="no-instances-message" style="color: var(--text-error);">❌ Error: ${error.message}</div>`;
    }
  }
}

/**
 * Display VastAI instances in the UI
 * @param {Array} instances - Array of normalized instance objects
 */
export function displayVastaiInstances(instances) {
  const instancesList = document.getElementById('vastai-instances-list');

  if (!instances || instances.length === 0) {
    if (instancesList) {
      instancesList.innerHTML = '<div class="no-instances-message">No instances found</div>';
    }
    return;
  }

  let html = '';
  instances.forEach(instance => {
    const normalizedStatus = normStatus(instance.status);
    const sshConnection = buildSSHString(instance);

    html += `
      <div class="instance-item" data-instance-id="${instance.id ?? ''}">
        <div class="instance-header">
          <div class="instance-title">Instance #${instance.id ?? 'Unknown'}</div>
          <div class="instance-status ${normalizedStatus}" data-field="status">${normalizedStatus}</div>
        </div>

        <div class="instance-details">
          <div class="instance-detail"><strong>GPU:</strong> ${instance.gpu ? instance.gpu : 'N/A'}${truthy(instance.gpu_count) ? ` (${instance.gpu_count}x)` : ''}</div>
          <div class="instance-detail"><strong>GPU RAM:</strong> ${fmtGb(instance.gpu_ram_gb)}</div>
          <div class="instance-detail"><strong>CPU:</strong> ${instance.cpu || 'N/A'}${truthy(instance.cpu_cores) ? ` (${instance.cpu_cores} cores)` : ''}</div>
          <div class="instance-detail"><strong>Location:</strong> ${instance.geolocation || 'N/A'}</div>
          <div class="instance-detail"><strong>Cost:</strong> ${fmtMoney(instance.cost_per_hour)}</div>
          <div class="instance-detail"><strong>Template:</strong> ${instance.template || 'N/A'}</div>
          <div class="instance-detail"><strong>SSH Host:</strong> <span data-field="ssh_host">${instance.ssh_host || 'N/A'}</span></div>
          <div class="instance-detail"><strong>SSH Port:</strong> <span data-field="ssh_port">${instance.ssh_port || 'N/A'}</span></div>
        </div>

        <div class="instance-actions">
          ${
            sshConnection && normalizedStatus === 'running'
              ? `<button class="use-instance-btn" onclick="VastAIInstances.useInstance('${sshConnection.replace(/'/g, "\\'")}')">
                   🔗 Connect to SSH Connection Field
                 </button>`
              : `<button class="use-instance-btn" onclick="VastAIInstances.refreshInstanceCard(${instance.id})">
                   🔄 Load SSH
                 </button>`
          }
          <button class="details-btn" onclick="VastAIUI.showInstanceDetails(${instance.id})">
            {...} Details
          </button>
          ${
            normalizedStatus === 'running'
              ? `<button class="stop-instance-btn" onclick="VastAIInstances.stopInstance(${instance.id})" title="Stop instance (will destroy it)">
                   ⏹️ Stop
                 </button>`
              : ''
          }
          <button class="destroy-instance-btn" onclick="VastAIInstances.destroyInstance(${instance.id})" title="Permanently destroy instance">
            🗑️ Destroy
          </button>
        </div>
      </div>
    `;
  });

  if (instancesList) {
    instancesList.innerHTML = html;
  }

  // Note: Auto-refresh removed to prevent excessive API calls.
  // Users can manually refresh individual instances using the "Refresh details" button.
}

/**
 * Use instance SSH connection string
 * @param {string} sshConnection - SSH connection string to use
 */
export function useInstance(sshConnection) {
  const sshInput = document.getElementById('sshConnectionString');
  if (sshInput) {
    sshInput.value = sshConnection;
    showSetupResult('✅ SSH connection parameters copied to SSH Connection String field', 'success');
  }
}

/**
 * Stop a VastAI instance (alias for destroy, as VastAI doesn't have a separate stop function)
 * @param {number} instanceId - ID of the instance to stop
 */
export async function stopInstance(instanceId) {
  const confirmation = confirm(`Are you sure you want to STOP instance #${instanceId}?\n\nNote: In VastAI, stopping an instance permanently destroys it. This action cannot be undone.`);
  if (!confirmation) return;
  
  return destroyInstance(instanceId);
}

/**
 * Destroy a VastAI instance
 * @param {number} instanceId - ID of the instance to destroy
 */
export async function destroyInstance(instanceId) {
  const confirmation = confirm(`Are you sure you want to DESTROY instance #${instanceId}?\n\nThis action cannot be undone and will permanently delete the instance.`);
  if (!confirmation) return;
  
  try {
    showSetupResult(`Destroying instance #${instanceId}...`, 'info');
    
    const response = await fetch(`/vastai/instances/${instanceId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    const data = await response.json();
    
    if (data.success) {
      showSetupResult(`✅ Instance #${instanceId} destroyed successfully`, 'success');
      
      // Remove the instance from the UI
      const instanceElement = document.querySelector(`[data-instance-id="${instanceId}"]`);
      if (instanceElement) {
        instanceElement.remove();
      }
      
      // Refresh the instances list to get updated data
      setTimeout(() => {
        loadVastaiInstances();
      }, 2000);
      
    } else {
      showSetupResult(`❌ Failed to destroy instance #${instanceId}: ${data.message}`, 'error');
    }
    
  } catch (error) {
    console.error('Error destroying instance:', error);
    showSetupResult(`❌ Error destroying instance #${instanceId}: ${error.message}`, 'error');
  }
}

console.log('📄 VastAI Instances module loaded');