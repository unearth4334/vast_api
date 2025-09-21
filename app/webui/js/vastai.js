// ==============================
// vastai.js — drop-in replacement
// ==============================

// ---------- Small helpers ----------
function fmtMoney(n) {
  if (n === null || n === undefined || isNaN(n)) return "$0/hr";
  return `$${(+n).toFixed(3)}/hr`;
}
function fmtGb(v) {
  if (v === null || v === undefined || isNaN(v)) return "0 GB";
  return `${(+v).toFixed(v < 10 ? 2 : 1)} GB`;
}
function truthy(x) { return x !== undefined && x !== null && x !== ""; }

function normStatus(s) {
  if (!s) return "unknown";
  const t = String(s).toLowerCase();
  if (["running", "active", "started"].some(k => t.includes(k))) return "running";
  if (["stopped", "terminated", "off"].some(k => t.includes(k))) return "stopped";
  if (["starting", "pending", "init"].some(k => t.includes(k))) return "starting";
  return t;
}

// Build a consistent geolocation string
function normGeo(i) {
  if (i.geolocation) return i.geolocation;
  const city = i.city || i.location || i.region;
  const cc = i.country_code || i.countryCode || i.cc;
  const country = i.country || i.country_name || i.countryName;
  if (country && cc) return `${country}, ${cc}`;
  if (city && country) return `${city}, ${country}`;
  if (country) return country;
  return "N/A";
}

// Try to guess SSH host/port no matter how backend shapes it
function normSSH(i) {
  let host = i.ssh_host || (i.ssh && i.ssh.host) || i.sshHost;
  let port = i.ssh_port || (i.ssh && i.ssh.port) || i.sshPort;

  // Vast sometimes uses a gateway host when not yet resolved
  if (!truthy(host)) host = "ssh2.vast.ai";

  if (!truthy(port)) {
    port = i.ssh_port_vast || i.sshPortVast || i.sshport || i.port || i.sshPort;
  }

  const maybeStr = i.ssh_string || i.sshString || i.ssh_connection || i.sshConnection;
  if ((!truthy(host) || !truthy(port)) && truthy(maybeStr)) {
    const m = String(maybeStr).match(/-p\s+(\d+)\s+[^@]+@([\w\.\-]+)/);
    if (m) { port = port || m[1]; host = host || m[2]; }
  }

  return { host, port };
}

// Normalize one instance object from diverse payloads
function normalizeInstance(raw) {
  const i = { ...raw };

  const id = i.id ?? i.instance_id ?? i.vast_id ?? i._id;
  const status = normStatus(i.status ?? i.state ?? i.instance_status ?? i.cur_state);

  // GPU fields
  const gpuName =
    i.gpu ??
    i.gpu_name ??
    (i.gpu_brand && i.gpu_model ? `${i.gpu_brand} ${i.gpu_model}` : null) ??
    i.gpuType ??
    null;

  const gpuCount = i.gpu_count ?? i.num_gpus ?? i.gpus ?? i.numGpus;

  // GPU RAM normalization (MB→GB heuristic)
  let gpuRamGb = i.gpu_ram_gb ?? i.gpu_mem_gb ?? i.vram_gb ?? null;
  if (!truthy(gpuRamGb)) {
    const ramMb = i.gpu_ram_mb ?? i.gpu_mem_mb ?? i.vram_mb;
    if (truthy(ramMb)) gpuRamGb = (+ramMb) / 1024;
  }
  if (!truthy(gpuRamGb) && truthy(i.gpu_ram)) {
    const val = +i.gpu_ram;
    gpuRamGb = isFinite(val) ? (val > 256 ? val / 1024 : val) : null;
  }

  // CPU
  const cpu = i.cpu ?? i.cpu_name ?? i.cpuModel ?? null;
  const cpuCores = i.cpu_cores ?? i.cores ?? i.vcpus ?? i.threads ?? i.cpu_cores_effective ?? null;

  // Disk (kept normalized but not displayed)
  let diskGb = i.disk_gb ?? i.disk ?? i.storage_gb ?? null;
  if (!truthy(diskGb) && truthy(i.disk_bytes)) diskGb = (+i.disk_bytes) / (1024 ** 3);

  // Network (kept normalized but not displayed)
  const down = i.net_down_mbps ?? i.download_mbps ?? i.down_mbps ?? i.net_down ?? i.inet_down ?? null;
  const up = i.net_up_mbps ?? i.upload_mbps ?? i.up_mbps ?? i.net_up ?? i.inet_up ?? null;

  // Pricing
  const cost =
    i.cost_per_hour ??
    i.dph_total ??
    i.dph ??
    (i.price_per_hour ?? i.price ?? null);

  // Public IP (may show as "SSH Host" when ssh_host absent)
  const publicIp =
    i.public_ip ??
    i.public_ipaddr ??
    i.ip_address ??
    i.publicIp ??
    null;

  const { host: ssh_host, port: ssh_port } = normSSH(i);

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
    public_ip: publicIp, // shown as "SSH Host" when ssh_host missing
    ssh_host,            // internal; used to build SSH string
    ssh_port,
    template
  };
}

// Build the “Use This Instance” SSH string
function buildSSHString(inst) {
  const host = inst.ssh_host || inst.public_ip || "ssh2.vast.ai";
  const port = inst.ssh_port;
  if (!host || !port) return null;
  return `ssh -p ${port} root@${host} -L 8080:localhost:8080`;
}

// ---------- UI feedback ----------
function showSetupResult(message, type) {
  const resultDiv = document.getElementById('setup-result');
  if (!resultDiv) return;
  resultDiv.textContent = message;
  resultDiv.className = 'setup-result ' + type;
  resultDiv.style.display = 'block';

  if (type === 'info') {
    setTimeout(() => {
      if (resultDiv.classList.contains('info')) {
        resultDiv.style.display = 'none';
      }
    }, 5000);
  }
}

// ---------- Backend API wrapper expectation ----------
// Assumes a global `api` with { get(path), post(path, body) } returning JSON.
// If you don't have it, swap to fetch() calls.

// ---------- VastAI: set/get UI_HOME, terminate, install civitdl ----------
async function setUIHome() {
  const sshConnectionString = document.getElementById('sshConnectionString').value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');

  showSetupResult('Setting UI_HOME to /workspace/ComfyUI/...', 'info');
  try {
    const data = await api.post('/vastai/set-ui-home', {
      ssh_connection: sshConnectionString,
      ui_home: '/workspace/ComfyUI/'
    });
    data.success ? showSetupResult(data.message, 'success')
                 : showSetupResult('Error: ' + (data.message || 'Unknown'), 'error');
  } catch (error) {
    showSetupResult('Request failed: ' + error.message, 'error');
  }
}

async function getUIHome() {
  const sshConnectionString = document.getElementById('sshConnectionString').value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');

  showSetupResult('Reading UI_HOME...', 'info');
  try {
    const data = await api.post('/vastai/get-ui-home', { ssh_connection: sshConnectionString });
    data.success ? showSetupResult('UI_HOME: ' + (data.ui_home || 'Unknown'), 'success')
                 : showSetupResult('Error: ' + (data.message || 'Unknown'), 'error');
  } catch (error) {
    showSetupResult('Request failed: ' + error.message, 'error');
  }
}

async function terminateConnection() {
  const sshConnectionString = document.getElementById('sshConnectionString').value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');
  if (!confirm('Are you sure you want to terminate the SSH connection?')) return;

  showSetupResult('Terminating SSH connection...', 'info');
  try {
    const data = await api.post('/vastai/terminate-connection', { ssh_connection: sshConnectionString });
    data.success ? showSetupResult(data.message, 'success')
                 : showSetupResult('Error: ' + (data.message || 'Unknown'), 'error');
  } catch (error) {
    showSetupResult('Request failed: ' + error.message, 'error');
  }
}

async function setupCivitDL() {
  const sshConnectionString = document.getElementById('sshConnectionString').value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');

  showSetupResult('Installing and configuring CivitDL...', 'info');
  try {
    const data = await api.post('/vastai/setup-civitdl', { ssh_connection: sshConnectionString });
    if (data.success) {
      const outputDiv = document.getElementById('setup-result');
      outputDiv.innerHTML =
        '<strong>CivitDL Setup Completed Successfully!</strong><br><br>' +
        '<strong>Output:</strong><pre style="white-space: pre-wrap; margin-top: 8px;">' +
        String(data.output || '').replace(/</g, '&lt;').replace(/>/g, '&gt;') +
        '</pre>';
      outputDiv.className = 'setup-result success';
      outputDiv.style.display = 'block';
    } else {
      showSetupResult('Error: ' + (data.message || 'Unknown') + (data.output ? '\n\nOutput:\n' + data.output : ''), 'error');
    }
  } catch (error) {
    showSetupResult('Request failed: ' + error.message, 'error');
  }
}

async function syncFromConnectionString() {
  const sshConnectionString = document.getElementById('sshConnectionString').value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');

  showSetupResult('Starting sync from connection string...', 'info');

  try {
    const data = await api.post('/sync/vastai-connection', {
      ssh_connection: sshConnectionString,
      cleanup: true
    });

    if (data.success) {
      showSetupResult('Sync started successfully! Check sync tab for progress.', 'success');
      if (typeof showTab === 'function') showTab('sync');

      const resultDiv = document.getElementById('result');
      const progressDiv = document.getElementById('progress');
      if (resultDiv) {
        resultDiv.className = 'result-panel loading';
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = '<h3>Starting VastAI sync from connection string...</h3><p>This may take several minutes.</p>';
      }
      if (data.sync_id && progressDiv && typeof pollProgress === 'function') {
        progressDiv.style.display = 'block';
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        const progressDetails = document.getElementById('progressDetails');
        if (progressBar) progressBar.style.width = '0%';
        if (progressText) progressText.textContent = 'Starting sync...';
        if (progressDetails) progressDetails.textContent = '';
        pollProgress(data.sync_id);
      }

      setTimeout(() => {
        if (!resultDiv) return;
        if (data.summary) {
          const duration = data.summary.duration_seconds ?
            `${Math.round(data.summary.duration_seconds)}s` : 'Unknown';
          const bytesFormatted = data.summary.bytes_transferred > 0 ?
            formatBytes(data.summary.bytes_transferred) : '0 bytes';
          const cleanupStatus = data.summary.cleanup_enabled ? 'enabled' : 'disabled';

          let byExtLine = '';
          if (data.summary.by_ext) {
            const pairs = Object.entries(data.summary.by_ext)
              .sort((a, b) => b[1] - a[1]).slice(0, 4)
              .map(([k, v]) => `${k}:${v}`).join(' · ');
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
      showSetupResult('Error: ' + (data.message || 'Unknown'), 'error');
    }
  } catch (error) {
    showSetupResult('Request failed: ' + error.message, 'error');
  }
}

// ---------- Instances detail fetch (authoritative) ----------
async function fetchVastaiInstanceDetails(instanceId) {
  // expects a backend route: GET /vastai/instances/:id returning { success, instance }
  const resp = await api.get(`/vastai/instances/${instanceId}`);
  if (!resp || resp.success === false) {
    const msg = (resp && resp.message) ? resp.message : `Failed to fetch details for ${instanceId}`;
    throw new Error(msg);
  }
  return resp.instance;
}

async function refreshInstanceCard(instanceId) {
  try {
    const inst = await fetchVastaiInstanceDetails(instanceId);

    // authoritative fields (match Vast detail endpoint)
    const sshHost = inst.ssh_host || inst.public_ipaddr || null;
    const sshPort = inst.ssh_port || 22;
    const state   = normStatus(inst.cur_state || inst.status || 'unknown');

    const sshConnection = (sshHost && sshPort)
      ? `ssh -p ${sshPort} root@${sshHost} -L 8080:localhost:8080`
      : null;

    // update the existing card
    const card = document.querySelector(`[data-instance-id="${instanceId}"]`);
    if (!card) return inst;

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
      if (sshConnection && state === 'running') {
        actions.innerHTML = `
          <button class="use-instance-btn" onclick="useInstance('${sshConnection.replace(/'/g, "\\'")}')">
            🔗 Connect to SSH Connection Field
          </button>
          <button class="use-instance-btn" onclick="refreshInstanceCard(${instanceId})">
            🔄 Refresh details
          </button>
        `;
      } else {
        actions.innerHTML = `
          <button class="use-instance-btn" onclick="refreshInstanceCard(${instanceId})">
            🔄 Load SSH
          </button>
        `;
      }
    }

    showSetupResult(`Instance #${instanceId} details refreshed.`, 'success');
    return inst;
  } catch (err) {
    showSetupResult(`Failed to refresh instance #${instanceId}: ${err.message}`, 'error');
    throw err;
  }
}

// ---------- Instances list ----------
async function loadVastaiInstances() {
  const instancesList = document.getElementById('vastai-instances-list');
  if (instancesList) {
    instancesList.innerHTML = '<div class="no-instances-message">Loading instances...</div>';
  }

  try {
    const data = await api.get('/vastai/instances');
    if (!data || data.success === false) {
      const msg = (data && data.message) ? data.message : 'Unknown error';
      if (instancesList) {
        instancesList.innerHTML =
          '<div class="no-instances-message" style="color: var(--text-error);">Error: ' + msg + '</div>';
      }
      return;
    }

    const rawInstances = Array.isArray(data.instances) ? data.instances : [];
    const instances = rawInstances.map(normalizeInstance);
    displayVastaiInstances(instances);
  } catch (error) {
    if (instancesList) {
      instancesList.innerHTML =
        '<div class="no-instances-message" style="color: var(--text-error);">Request failed: ' + error.message + '</div>';
    }
  }
}

function displayVastaiInstances(instances) {
  const instancesList = document.getElementById('vastai-instances-list');

  if (!instances || instances.length === 0) {
    if (instancesList) {
      instancesList.innerHTML = '<div class="no-instances-message">No active VastAI instances found</div>';
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
          <div class="instance-detail"><strong>SSH Host:</strong> <span data-field="ssh_host">${instance.public_ip || instance.ssh_host || 'N/A'}</span></div>
          <div class="instance-detail"><strong>SSH Port:</strong> <span data-field="ssh_port">${instance.ssh_port || 'N/A'}</span></div>
        </div>

        <div class="instance-actions">
          ${
            sshConnection && normalizedStatus === 'running'
              ? `<button class="use-instance-btn" onclick="useInstance('${sshConnection.replace(/'/g, "\\'")}')">
                   🔗 Connect to SSH Connection Field
                 </button>`
              : `<button class="use-instance-btn" onclick="refreshInstanceCard(${instance.id})">
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

  // Auto-refresh each card to pull authoritative ssh_host/ssh_port from detail endpoint
  instances.forEach(i => {
    if (i && i.id != null) {
      // fire-and-forget; errors are surfaced via showSetupResult
      refreshInstanceCard(i.id);
    }
  });
}

function useInstance(sshConnection) {
  const sshInput = document.getElementById('sshConnectionString');
  if (sshInput) {
    sshInput.value = sshConnection;
    showSetupResult('✅ SSH connection parameters copied to SSH Connection String field', 'success');
  }
}

// Expose the functions you call from HTML or other scripts
window.setUIHome = setUIHome;
window.getUIHome = getUIHome;
window.terminateConnection = terminateConnection;
window.setupCivitDL = setupCivitDL;
window.syncFromConnectionString = syncFromConnectionString;
window.loadVastaiInstances = loadVastaiInstances;
window.useInstance = useInstance;
window.refreshInstanceCard = refreshInstanceCard;