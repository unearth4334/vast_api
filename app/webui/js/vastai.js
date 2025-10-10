// ==============================
// vastai.js — drop-in replacement
// ==============================
//
// Assumes a global `api` object with { get(path), post(path, body) } returning JSON.
// Exposes helpers on `window` for use in HTML attributes.
//

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

// Get country flag emoji from geolocation
function getCountryFlag(geolocation) {
  if (!geolocation || geolocation === 'N/A') return '';

  const countryFlags = {
    'CA': '🇨🇦', 'US': '🇺🇸', 'TT': '🇹🇹', 'VN': '🇻🇳', 'KR': '🇰🇷', 
    'FR': '🇫🇷', 'CZ': '🇨🇿', 'AU': '🇦🇺', 'HK': '🇭🇰', 'CN': '🇨🇳',
    'HU': '🇭🇺', 'IN': '🇮🇳', 'BG': '🇧🇬', 'DE': '🇩🇪', 'JP': '🇯🇵',
    'SG': '🇸🇬', 'BR': '🇧🇷', 'NL': '🇳🇱', 'GB': '🇬🇧', 'UK': '🇬🇧'
  };

  // Extract parts like "City, CC" or "Country, CC"
  const parts = geolocation.split(',').map(s => s.trim());

  // Check for country codes (2 letters)
  for (let part of parts) {
    if (part.length === 2) {
      const code = part.toUpperCase();
      if (countryFlags[code]) return countryFlags[code];
      return code; // fallback: show 2-letter abbreviation
    }
  }

  // Check for country names
  for (let part of parts) {
    if (countryFlags[part]) {
      return countryFlags[part];
    }
  }

  // Last resort: take last word if it looks like code
  const last = parts[parts.length - 1];
  if (last && last.length === 2) return last.toUpperCase();

  // If we can't parse anything, show just the raw geolocation
  return geolocation;
}


// Always regard Public IP as the SSH host (authoritative)
function resolveSSH(i) {
  const host =
    i.public_ip ??
    i.public_ipaddr ??
    i.ip_address ??
    i.publicIp ??
    null;                       // <- we do NOT fall back to ssh_host; public IP wins
  const port = i.ssh_port || 22;
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
  const cpuCores = i.cpu_cores ?? i.cpu_cores_effective ?? i.cores ?? i.vcpus ?? i.threads ?? null;

  // Disk (normalized, not always displayed)
  let diskGb = i.disk_gb ?? i.disk ?? i.storage_gb ?? null;
  if (!truthy(diskGb) && truthy(i.disk_bytes)) diskGb = (+i.disk_bytes) / (1024 ** 3);

  // Network (normalized, not always displayed)
  const down = i.net_down_mbps ?? i.download_mbps ?? i.down_mbps ?? i.net_down ?? i.inet_down ?? null;
  const up   = i.net_up_mbps   ?? i.upload_mbps   ?? i.up_mbps   ?? i.net_up   ?? i.inet_up   ?? null;

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
    ssh_host,    // <-- always from public IP fields
    ssh_port,    // may be missing from list payload; refresh fills it
    template
  };
}

// Build the “Use This Instance” SSH string
function buildSSHString(inst) {
  if (!inst.ssh_host || !inst.ssh_port) return null;
  return `ssh -p ${inst.ssh_port} root@${inst.ssh_host} -L 8080:localhost:8080`;
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

// ---------- VastAI: set/get UI_HOME, terminate, install civitdl ----------
async function setUIHome() {
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
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
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
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
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
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
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');

  showSetupResult('Installing and configuring CivitDL...', 'info');
  try {
    const data = await api.post('/vastai/setup-civitdl', { ssh_connection: sshConnectionString });
    if (data.success) {
      const outputDiv = document.getElementById('setup-result');
      if (outputDiv) {
        outputDiv.innerHTML =
          '<strong>CivitDL Setup Completed Successfully!</strong><br><br>' +
          '<strong>Output:</strong><pre style="white-space: pre-wrap; margin-top: 8px;">' +
          String(data.output || '').replace(/</g, '&lt;').replace(/>/g, '&gt;') +
          '</pre>';
        outputDiv.className = 'setup-result success';
        outputDiv.style.display = 'block';
      }
    } else {
      showSetupResult('Error: ' + (data.message || 'Unknown') + (data.output ? '\n\nOutput:\n' + data.output : ''), 'error');
    }
  } catch (error) {
    showSetupResult('Request failed: ' + error.message, 'error');
  }
}

async function syncFromConnectionString() {
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
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

    // Authoritative values — host must come from public IP fields:
    const sshHost =
      inst.public_ipaddr ||
      inst.public_ip ||
      inst.ip_address ||
      inst.publicIp ||
      null;
    const sshPort = inst.ssh_port || 22;
    const state   = normStatus(inst.cur_state || inst.status || 'unknown');

    const sshConnection = (sshHost && sshPort)
      ? `ssh -p ${sshPort} root@${sshHost} -L 8080:localhost:8080`
      : null;

    // Update the existing card
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
          <div class="instance-detail"><strong>SSH Host:</strong> <span data-field="ssh_host">${instance.ssh_host || 'N/A'}</span></div>
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

  // Note: Auto-refresh removed to prevent excessive API calls.
  // Users can manually refresh individual instances using the "Refresh details" button.
}

function useInstance(sshConnection) {
  const sshInput = document.getElementById('sshConnectionString');
  if (sshInput) {
    sshInput.value = sshConnection;
    showSetupResult('✅ SSH connection parameters copied to SSH Connection String field', 'success');
  }
}

// Global offer storage to prevent XSS vulnerabilities
window.offerStore = new Map();

// Global state for mobile tap reveal functionality
window.mobileOfferState = {
  expandedEl: null,
  clickHandler: null,
  keydownHandler: null
};

// Expose the functions you call from HTML or other scripts
window.setUIHome = setUIHome;
window.getUIHome = getUIHome;
window.terminateConnection = terminateConnection;
window.setupCivitDL = setupCivitDL;
window.syncFromConnectionString = syncFromConnectionString;
window.loadVastaiInstances = loadVastaiInstances;
window.useInstance = useInstance;
window.refreshInstanceCard = refreshInstanceCard;

// ---------- Search offers functionality ----------

// State management for pill bar filters
window.vastaiSearchState = {
  sortBy: 'dph_total',          // 'dph_total' | 'score' | 'gpu_ram' | 'reliability'
  vramMinGb: null,              // number | null
  pcieMinGbps: null,            // number | null
  netUpMinMbps: null,           // number | null
  netDownMinMbps: null,         // number | null
  priceMaxPerHour: null,        // number | null
  locations: [],                // string[] (country codes)
  gpuModelQuery: ''             // string
};

// Current open editor state
window.pillBarState = {
  activeEditor: null,           // string | null - which editor is open
  isMobile: () => window.matchMedia('(max-width: 560px)').matches
};

// Label formatters for pills
const pillLabelFormatters = {
  search: () => 'Search',
  sort: () => {
    const sortLabels = {
      'dph_total': 'Price/hr',
      'score': 'Score', 
      'gpu_ram': 'GPU RAM',
      'reliability': 'Reliability'
    };
    return `Sort: ${sortLabels[window.vastaiSearchState.sortBy] || 'Price/hr'}`;
  },
  vram: () => {
    const min = window.vastaiSearchState.vramMinGb;
    return min ? `VRAM: ≥${min} GB` : 'VRAM: Any';
  },
  pcie: () => {
    const min = window.vastaiSearchState.pcieMinGbps;
    return min ? `PCIe: ≥${min} GB/s` : 'PCIe: Any';
  },
  net: () => {
    const up = window.vastaiSearchState.netUpMinMbps;
    const down = window.vastaiSearchState.netDownMinMbps;
    if (up && down) return `Net: ≥${up}↑/${down}↓`;
    if (up) return `Net Up: ≥${up} Mbps`;
    if (down) return `Net Down: ≥${down} Mbps`;
    return 'Net: Any';
  },
  location: () => {
    const locs = window.vastaiSearchState.locations;
    if (locs.length === 0) return 'Location: Any';
    if (locs.length === 1) return `Location: ${locs[0]}`;
    return `Location: ${locs.length} selected`;
  },
  gpuModel: () => {
    const query = window.vastaiSearchState.gpuModelQuery;
    return query ? `GPU: ${query}` : 'GPU Model: Any';
  },
  priceCap: () => {
    const max = window.vastaiSearchState.priceMaxPerHour;
    return max ? `Price: ≤$${max}/hr` : 'Price: Any';
  }
};

function openSearchOffersModal() {
  const overlay = document.getElementById('searchOffersOverlay');
  if (overlay) {
    overlay.style.display = 'flex';
    // Initialize pill bar after modal opens
    initializePillBar();
  }
}

function closeSearchOffersModal() {
  const overlay = document.getElementById('searchOffersOverlay');
  if (overlay) {
    overlay.style.display = 'none';
    // Clean up any open editors
    closePillEditor();
  }
}

// Initialize pill bar functionality
function initializePillBar() {
  updateAllPillLabels();
  setupPillEventListeners();
  
  // Add ARIA live region for announcements
  if (!document.getElementById('pill-announcements')) {
    const liveRegion = document.createElement('div');
    liveRegion.id = 'pill-announcements';
    liveRegion.setAttribute('aria-live', 'polite');
    liveRegion.className = 'sr-only';
    document.body.appendChild(liveRegion);
  }
}

// Update all pill labels based on current state
function updateAllPillLabels() {
  Object.keys(pillLabelFormatters).forEach(filterType => {
    updatePillLabel(filterType);
  });
}

// Update a specific pill's label and active state
function updatePillLabel(filterType) {
  const pill = document.getElementById(`pill-${filterType}`);
  if (!pill) return;
  
  const label = pillLabelFormatters[filterType]();
  pill.textContent = label;
  
  // Update active state based on whether filter has a value
  const hasValue = hasFilterValue(filterType);
  pill.classList.toggle('pill--has-value', hasValue);
}

// Check if a filter has a non-default value
function hasFilterValue(filterType) {
  const state = window.vastaiSearchState;
  switch (filterType) {
    case 'search': return false; // Search button doesn't have a "value"
    case 'sort': return state.sortBy !== 'dph_total';
    case 'vram': return state.vramMinGb !== null;
    case 'pcie': return state.pcieMinGbps !== null;
    case 'net': return state.netUpMinMbps !== null || state.netDownMinMbps !== null;
    case 'location': return state.locations.length > 0;
    case 'gpuModel': return state.gpuModelQuery !== '';
    case 'priceCap': return state.priceMaxPerHour !== null;
    default: return false;
  }
}

// Setup event listeners for pills
function setupPillEventListeners() {
  const pillbar = document.getElementById('pillbar');
  if (!pillbar) return;
  
  // Add click handlers to all pills
  pillbar.addEventListener('click', handlePillClick);
  
  // Add keyboard handlers
  pillbar.addEventListener('keydown', handlePillKeydown);
  
  // Close editors when clicking outside (desktop only)
  document.addEventListener('click', handleOutsideClick);
  
  // ESC key handler
  document.addEventListener('keydown', handleEscKey);
}

// Handle pill clicks
function handlePillClick(event) {
  const pill = event.target.closest('.pill');
  if (!pill) return;
  
  const filterType = pill.dataset.filter;
  if (!filterType) return;
  
  event.preventDefault();
  event.stopPropagation();
  
  // Special handling for search pill
  if (filterType === 'search') {
    searchVastaiOffers();
    return;
  }
  
  // Open the appropriate editor
  openPillEditor(filterType, pill);
}

// Handle keyboard navigation
function handlePillKeydown(event) {
  const pill = event.target.closest('.pill');
  if (!pill) return;
  
  switch (event.key) {
    case 'Enter':
    case ' ':
      event.preventDefault();
      pill.click();
      break;
    case 'ArrowLeft':
      event.preventDefault();
      focusPreviousPill(pill);
      break;
    case 'ArrowRight':
      event.preventDefault();
      focusNextPill(pill);
      break;
  }
}

// Focus management for keyboard navigation
function focusPreviousPill(currentPill) {
  const pills = [...document.querySelectorAll('.pill')];
  const currentIndex = pills.indexOf(currentPill);
  const previousPill = pills[currentIndex - 1] || pills[pills.length - 1];
  previousPill.focus();
}

function focusNextPill(currentPill) {
  const pills = [...document.querySelectorAll('.pill')];
  const currentIndex = pills.indexOf(currentPill);
  const nextPill = pills[currentIndex + 1] || pills[0];
  nextPill.focus();
}

// Open pill editor (mobile or desktop popover)
function openPillEditor(filterType, pill) {
  // Close any existing editor first
  closePillEditor();
  
  // Update active editor state
  window.pillBarState.activeEditor = filterType;
  
  // Update ARIA states
  document.querySelectorAll('.pill').forEach(p => p.setAttribute('aria-expanded', 'false'));
  pill.setAttribute('aria-expanded', 'true');
  
  if (window.pillBarState.isMobile()) {
    openMobileEditor(filterType);
  } else {
    openDesktopPopover(filterType, pill);
  }
}

// Close any open pill editor
function closePillEditor() {
  // Close mobile editor
  const mobileEditor = document.getElementById('pill-editor');
  if (mobileEditor) {
    mobileEditor.style.display = 'none';
    mobileEditor.innerHTML = '';
  }
  
  // Close desktop popover
  const popover = document.querySelector('.pill-popover');
  if (popover) {
    popover.remove();
  }
  
  // Reset ARIA states
  document.querySelectorAll('.pill').forEach(p => p.setAttribute('aria-expanded', 'false'));
  
  // Clear active editor
  window.pillBarState.activeEditor = null;
}

// Handle clicks outside pills/editors (desktop only)
function handleOutsideClick(event) {
  if (window.pillBarState.isMobile()) return;
  
  const isInsidePill = event.target.closest('.pill');
  const isInsidePopover = event.target.closest('.pill-popover');
  
  if (!isInsidePill && !isInsidePopover) {
    closePillEditor();
  }
}

// Handle ESC key
function handleEscKey(event) {
  if (event.key === 'Escape' && window.pillBarState.activeEditor) {
    closePillEditor();
  }
}

// Mobile editor implementation
function openMobileEditor(filterType) {
  const editorContainer = document.getElementById('pill-editor');
  if (!editorContainer) return;
  
  editorContainer.innerHTML = '';
  editorContainer.style.display = 'block';
  
  // Build header
  const header = document.createElement('div');
  header.className = 'pill-editor__header';
  const filterNames = {
    sort: 'Sort Options',
    vram: 'GPU RAM Filter',
    pcie: 'PCIe Bandwidth Filter',
    net: 'Network Speed Filter',
    location: 'Location Filter',
    gpuModel: 'GPU Model Filter',
    priceCap: 'Price Cap Filter'
  };
  header.innerHTML = `
    <strong>${filterNames[filterType] || 'Filter'}</strong>
    <button class="pill-editor__close" aria-label="Close ${filterNames[filterType] || 'Filter'} editor">×</button>
  `;
  
  // Build content
  const content = document.createElement('div');
  content.className = 'pill-editor__content';
  content.appendChild(buildEditor(filterType));
  
  // Build actions
  const actions = document.createElement('div');
  actions.className = 'pill-editor__actions';
  actions.innerHTML = `
    <button class="search-button" data-action="apply">Apply</button>
    <button class="search-button secondary" data-action="clear">Clear</button>
  `;
  
  editorContainer.appendChild(header);
  editorContainer.appendChild(content);
  editorContainer.appendChild(actions);
  
  // Wire up event handlers
  header.querySelector('.pill-editor__close').addEventListener('click', closePillEditor);
  actions.querySelector('[data-action="apply"]').addEventListener('click', () => applyEditorChanges(filterType));
  actions.querySelector('[data-action="clear"]').addEventListener('click', () => clearEditorFilter(filterType));
  
  // Set focus to first interactive element
  const firstInput = content.querySelector('input, select, button');
  if (firstInput) {
    setTimeout(() => firstInput.focus(), 100);
  }
}

// Desktop popover implementation
function openDesktopPopover(filterType, pill) {
  const popover = document.createElement('div');
  popover.className = 'pill-popover';
  popover.setAttribute('role', 'dialog');
  popover.setAttribute('aria-labelledby', pill.id);
  
  // Build editor content
  popover.appendChild(buildEditor(filterType));
  
  // Position popover
  document.body.appendChild(popover);
  positionPopover(popover, pill);
  popover.style.display = 'block';
  
  // Set focus to first interactive element
  const firstInput = popover.querySelector('input, select, button');
  if (firstInput) {
    setTimeout(() => firstInput.focus(), 100);
  }
  
  // Setup popover event handlers
  setupPopoverHandlers(popover, filterType);
}

// Position desktop popover relative to pill
function positionPopover(popover, pill) {
  const pillRect = pill.getBoundingClientRect();
  const popoverRect = popover.getBoundingClientRect();
  
  let left = pillRect.left;
  let top = pillRect.bottom + 8;
  
  // Adjust if popover would go off-screen
  if (left + popoverRect.width > window.innerWidth) {
    left = window.innerWidth - popoverRect.width - 16;
  }
  if (left < 16) {
    left = 16;
  }
  
  popover.style.left = `${left}px`;
  popover.style.top = `${top}px`;
}

// Setup popover-specific event handlers
function setupPopoverHandlers(popover, filterType) {
  // Add Apply/Clear buttons for desktop popovers
  const actionsDiv = document.createElement('div');
  actionsDiv.className = 'pill-editor__actions';
  actionsDiv.innerHTML = `
    <button class="search-button" data-action="apply">Apply</button>
    <button class="search-button secondary" data-action="clear">Clear</button>
  `;
  popover.appendChild(actionsDiv);
  
  // Wire up handlers
  actionsDiv.querySelector('[data-action="apply"]').addEventListener('click', () => applyEditorChanges(filterType));
  actionsDiv.querySelector('[data-action="clear"]').addEventListener('click', () => clearEditorFilter(filterType));
}

async function searchVastaiOffers() {
  const params = new URLSearchParams();
  const s = window.vastaiSearchState || {};

  if (s.vramMinGb) params.set('gpu_ram', s.vramMinGb);
  if (s.sortBy)    params.set('sort', s.sortBy);

  // NEW: forward the rest of the filters if set
  if (s.pcieMinGbps != null)          params.set('pcie_min', s.pcieMinGbps);
  if (s.gpuModelQuery && s.gpuModelQuery.trim()) params.set('gpu_model', s.gpuModelQuery.trim());
  if (s.netUpMinMbps != null)         params.set('net_up_min', s.netUpMinMbps);
  if (s.netDownMinMbps != null)       params.set('net_down_min', s.netDownMinMbps);
  if (Array.isArray(s.locations) && s.locations.length > 0) {
    // Expect array of ISO country codes (e.g. ["CA","US"])
    params.set('locations', s.locations.join(','));
  }
  if (s.priceMaxPerHour != null)      params.set('price_max', s.priceMaxPerHour);

  const resultsDiv = document.getElementById('searchResults');
  if (!resultsDiv) return;
  resultsDiv.innerHTML = '<div class="no-results-message">🔍 Searching for available offers...</div>';

  try {
    const data = await api.get(`/vastai/search-offers?${params.toString()}`);
    if (!data || data.success === false) {
      const msg = (data && data.message) ? data.message : 'Failed to search offers';
      resultsDiv.innerHTML = `<div class="no-results-message" style="color: var(--text-error);">❌ Error: ${msg}</div>`;
      return;
    }
    const offers = Array.isArray(data.offers) ? data.offers : [];
    displaySearchResults(offers);
    closePillEditor();
  } catch (error) {
    resultsDiv.innerHTML = `<div class="no-results-message" style="color: var(--text-error);">❌ Request failed: ${error.message}</div>`;
  }
}


// Build editor UI for specific filter type
function buildEditor(filterType) {
  const container = document.createElement('div');
  
  switch (filterType) {
    case 'sort':
      container.appendChild(buildSortEditor());
      break;
    case 'vram':
      container.appendChild(buildVramEditor());
      break;
    case 'pcie':
      container.appendChild(buildPcieEditor());
      break;
    case 'net':
      container.appendChild(buildNetEditor());
      break;
    case 'location':
      container.appendChild(buildLocationEditor());
      break;
    case 'gpuModel':
      container.appendChild(buildGpuModelEditor());
      break;
    case 'priceCap':
      container.appendChild(buildPriceCapEditor());
      break;
    default:
      container.innerHTML = '<div class="editor-section">Editor not implemented yet</div>';
  }
  
  return container;
}

// Sort editor (radio buttons)
function buildSortEditor() {
  const section = document.createElement('div');
  section.className = 'editor-section';
  
  const options = [
    { value: 'dph_total', label: 'Price per hour' },
    { value: 'score', label: 'Score' },
    { value: 'gpu_ram', label: 'GPU RAM' },
    { value: 'reliability', label: 'Reliability' }
  ];
  
  const radioList = document.createElement('div');
  radioList.className = 'editor-radio-list';
  
  options.forEach(option => {
    const item = document.createElement('div');
    item.className = 'editor-radio-item';
    
    const radio = document.createElement('input');
    radio.type = 'radio';
    radio.name = 'sort-option';
    radio.value = option.value;
    radio.id = `sort-${option.value}`;
    radio.checked = window.vastaiSearchState.sortBy === option.value;
    
    const label = document.createElement('label');
    label.htmlFor = radio.id;
    label.textContent = option.label;
    
    item.appendChild(radio);
    item.appendChild(label);
    radioList.appendChild(item);
  });
  
  section.appendChild(radioList);
  return section;
}

// VRAM editor (slider + input + chips)
function buildVramEditor() {
  const section = document.createElement('div');
  section.className = 'editor-section';
  
  const label = document.createElement('label');
  label.className = 'editor-label';
  label.textContent = 'Minimum GB VRAM';
  
  const input = document.createElement('input');
  input.type = 'number';
  input.className = 'editor-input';
  input.id = 'vram-input';
  input.min = '1';
  input.max = '128';
  input.value = window.vastaiSearchState.vramMinGb || '';
  input.placeholder = 'Any amount';
  
  const slider = document.createElement('input');
  slider.type = 'range';
  slider.className = 'editor-slider';
  slider.id = 'vram-slider';
  slider.min = '1';
  slider.max = '128';
  slider.value = window.vastaiSearchState.vramMinGb || '16';
  
  const chips = document.createElement('div');
  chips.className = 'editor-chips';
  [8, 16, 24, 32, 48, 80].forEach(value => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'editor-chip';
    chip.textContent = `${value} GB`;
    chip.dataset.value = value;
    if (window.vastaiSearchState.vramMinGb == value) {
      chip.classList.add('selected');
    }
    chips.appendChild(chip);
  });
  
  const helper = document.createElement('div');
  helper.className = 'editor-helper-text';
  helper.textContent = 'Set minimum GPU VRAM requirement';
  
  // Sync slider and input
  input.addEventListener('input', () => {
    slider.value = input.value || '16';
    updateChipSelection(chips, input.value);
  });
  
  slider.addEventListener('input', () => {
    input.value = slider.value;
    updateChipSelection(chips, slider.value);
  });
  
  // Handle chip clicks
  chips.addEventListener('click', (e) => {
    if (e.target.classList.contains('editor-chip')) {
      const value = e.target.dataset.value;
      input.value = value;
      slider.value = value;
      updateChipSelection(chips, value);
    }
  });
  
  section.appendChild(label);
  section.appendChild(input);
  section.appendChild(slider);
  section.appendChild(chips);
  section.appendChild(helper);
  
  return section;
}

// PCIe editor (similar to VRAM)
function buildPcieEditor() {
  const section = document.createElement('div');
  section.className = 'editor-section';
  
  const label = document.createElement('label');
  label.className = 'editor-label';
  label.textContent = 'Minimum PCIe Bandwidth (GB/s)';
  
  const input = document.createElement('input');
  input.type = 'number';
  input.className = 'editor-input';
  input.id = 'pcie-input';
  input.min = '1';
  input.max = '64';
  input.step = '0.1';
  input.value = window.vastaiSearchState.pcieMinGbps || '';
  input.placeholder = 'Any speed';
  
  const chips = document.createElement('div');
  chips.className = 'editor-chips';
  [8, 16, 32].forEach(value => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'editor-chip';
    chip.textContent = `${value} GB/s`;
    chip.dataset.value = value;
    if (window.vastaiSearchState.pcieMinGbps == value) {
      chip.classList.add('selected');
    }
    chips.appendChild(chip);
  });
  
  const helper = document.createElement('div');
  helper.className = 'editor-helper-text';
  helper.textContent = 'Set minimum PCIe bandwidth requirement';
  
  // Handle chip clicks
  chips.addEventListener('click', (e) => {
    if (e.target.classList.contains('editor-chip')) {
      const value = e.target.dataset.value;
      input.value = value;
      updateChipSelection(chips, value);
    }
  });
  
  section.appendChild(label);
  section.appendChild(input);
  section.appendChild(chips);
  section.appendChild(helper);
  
  return section;
}

// Network editor (two sliders for up/down)
function buildNetEditor() {
  const section = document.createElement('div');
  section.className = 'editor-section';
  
  // Upload speed
  const upLabel = document.createElement('label');
  upLabel.className = 'editor-label';
  upLabel.textContent = 'Minimum Upload Speed (Mbps)';
  
  const upInput = document.createElement('input');
  upInput.type = 'number';
  upInput.className = 'editor-input';
  upInput.id = 'net-up-input';
  upInput.min = '1';
  upInput.max = '10000';
  upInput.value = window.vastaiSearchState.netUpMinMbps || '';
  upInput.placeholder = 'Any speed';
  
  // Download speed
  const downLabel = document.createElement('label');
  downLabel.className = 'editor-label';
  downLabel.textContent = 'Minimum Download Speed (Mbps)';
  downLabel.style.marginTop = '12px';
  
  const downInput = document.createElement('input');
  downInput.type = 'number';
  downInput.className = 'editor-input';
  downInput.id = 'net-down-input';
  downInput.min = '1';
  downInput.max = '10000';
  downInput.value = window.vastaiSearchState.netDownMinMbps || '';
  downInput.placeholder = 'Any speed';
  
  const helper = document.createElement('div');
  helper.className = 'editor-helper-text';
  helper.textContent = 'Set minimum network speed requirements';
  
  section.appendChild(upLabel);
  section.appendChild(upInput);
  section.appendChild(downLabel);
  section.appendChild(downInput);
  section.appendChild(helper);
  
  return section;
}

// Location editor (searchable checkboxes)
function buildLocationEditor() {
  const section = document.createElement('div');
  section.className = 'editor-section';
  
  const searchInput = document.createElement('input');
  searchInput.type = 'text';
  searchInput.className = 'editor-search';
  searchInput.placeholder = 'Search countries...';
  
  const checkboxList = document.createElement('div');
  checkboxList.className = 'editor-checkbox-list';
  
  const countries = [
    { code: 'US', name: 'United States' },
    { code: 'CA', name: 'Canada' },
    { code: 'DE', name: 'Germany' },
    { code: 'FR', name: 'France' },
    { code: 'GB', name: 'United Kingdom' },
    { code: 'JP', name: 'Japan' },
    { code: 'KR', name: 'South Korea' },
    { code: 'AU', name: 'Australia' },
    { code: 'SG', name: 'Singapore' },
    { code: 'NL', name: 'Netherlands' },
    { code: 'BR', name: 'Brazil' },
    { code: 'IN', name: 'India' },
    { code: 'CN', name: 'China' },
    { code: 'HK', name: 'Hong Kong' }
  ];
  
  countries.forEach(country => {
    const item = document.createElement('div');
    item.className = 'editor-checkbox-item';
    
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.id = `loc-${country.code}`;
    checkbox.value = country.code;
    checkbox.checked = window.vastaiSearchState.locations.includes(country.code);
    
    const label = document.createElement('label');
    label.htmlFor = checkbox.id;
    label.textContent = `${country.name} (${country.code})`;
    
    item.appendChild(checkbox);
    item.appendChild(label);
    checkboxList.appendChild(item);
  });
  
  // Search functionality
  searchInput.addEventListener('input', () => {
    const query = searchInput.value.toLowerCase();
    checkboxList.querySelectorAll('.editor-checkbox-item').forEach(item => {
      const label = item.querySelector('label').textContent.toLowerCase();
      item.style.display = label.includes(query) ? 'flex' : 'none';
    });
  });
  
  section.appendChild(searchInput);
  section.appendChild(checkboxList);
  
  return section;
}

// GPU Model editor (typeahead input)
function buildGpuModelEditor() {
  const section = document.createElement('div');
  section.className = 'editor-section';
  
  const label = document.createElement('label');
  label.className = 'editor-label';
  label.textContent = 'GPU Model';
  
  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'editor-input';
  input.id = 'gpu-model-input';
  input.value = window.vastaiSearchState.gpuModelQuery || '';
  input.placeholder = 'e.g., RTX 4090, A100, V100...';
  
  const helper = document.createElement('div');
  helper.className = 'editor-helper-text';
  helper.textContent = 'Enter GPU model name or part of it';
  
  section.appendChild(label);
  section.appendChild(input);
  section.appendChild(helper);
  
  return section;
}

// Price Cap editor (slider + input)
function buildPriceCapEditor() {
  const section = document.createElement('div');
  section.className = 'editor-section';
  
  const label = document.createElement('label');
  label.className = 'editor-label';
  label.textContent = 'Maximum Price per Hour ($)';
  
  const input = document.createElement('input');
  input.type = 'number';
  input.className = 'editor-input';
  input.id = 'price-cap-input';
  input.min = '0.01';
  input.max = '50';
  input.step = '0.01';
  input.value = window.vastaiSearchState.priceMaxPerHour || '';
  input.placeholder = 'No limit';
  
  const helper = document.createElement('div');
  helper.className = 'editor-helper-text';
  helper.textContent = 'Set maximum price per hour limit';
  
  section.appendChild(label);
  section.appendChild(input);
  section.appendChild(helper);
  
  return section;
}

// Utility function to update chip selection
function updateChipSelection(chipsContainer, value) {
  chipsContainer.querySelectorAll('.editor-chip').forEach(chip => {
    chip.classList.toggle('selected', chip.dataset.value == value);
  });
}

// Apply editor changes to state
function applyEditorChanges(filterType) {
  const state = window.vastaiSearchState;
  
  switch (filterType) {
    case 'sort':
      const selectedSort = document.querySelector('input[name="sort-option"]:checked');
      if (selectedSort) {
        state.sortBy = selectedSort.value;
      }
      break;
      
    case 'vram':
      const vramValue = document.getElementById('vram-input')?.value;
      state.vramMinGb = vramValue && vramValue > 0 ? parseInt(vramValue) : null;
      break;
      
    case 'pcie':
      const pcieValue = document.getElementById('pcie-input')?.value;
      state.pcieMinGbps = pcieValue && pcieValue > 0 ? parseFloat(pcieValue) : null;
      break;
      
    case 'net':
      const upValue = document.getElementById('net-up-input')?.value;
      const downValue = document.getElementById('net-down-input')?.value;
      state.netUpMinMbps = upValue && upValue > 0 ? parseInt(upValue) : null;
      state.netDownMinMbps = downValue && downValue > 0 ? parseInt(downValue) : null;
      break;
      
    case 'location':
      const selectedLocations = [];
      document.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
        if (cb.id && cb.id.startsWith('loc-')) {
          selectedLocations.push(cb.value);
        }
      });
      state.locations = selectedLocations;
      break;
      
    case 'gpuModel':
      const gpuValue = document.getElementById('gpu-model-input')?.value;
      state.gpuModelQuery = gpuValue ? gpuValue.trim() : '';
      break;
      
    case 'priceCap':
      const priceValue = document.getElementById('price-cap-input')?.value;
      state.priceMaxPerHour = priceValue && priceValue > 0 ? parseFloat(priceValue) : null;
      break;
  }
  
  // Update pill label and close editor
  updatePillLabel(filterType);
  closePillEditor();
  
  // Announce the change
  announceFilterChange(filterType);
}

// Clear a specific filter
function clearEditorFilter(filterType) {
  const state = window.vastaiSearchState;
  
  switch (filterType) {
    case 'sort':
      state.sortBy = 'dph_total';
      break;
    case 'vram':
      state.vramMinGb = null;
      break;
    case 'pcie':
      state.pcieMinGbps = null;
      break;
    case 'net':
      state.netUpMinMbps = null;
      state.netDownMinMbps = null;
      break;
    case 'location':
      state.locations = [];
      break;
    case 'gpuModel':
      state.gpuModelQuery = '';
      break;
    case 'priceCap':
      state.priceMaxPerHour = null;
      break;
  }
  
  // Update pill label and close editor
  updatePillLabel(filterType);
  closePillEditor();
  
  // Announce the change
  announceFilterChange(filterType, true);
}

// Announce filter changes for screen readers
function announceFilterChange(filterType, cleared = false) {
  const announcements = document.getElementById('pill-announcements');
  if (!announcements) return;
  
  const filterNames = {
    sort: 'Sort',
    vram: 'VRAM',
    pcie: 'PCIe',
    net: 'Network',
    location: 'Location',
    gpuModel: 'GPU Model',
    priceCap: 'Price Cap'
  };
  
  const filterName = filterNames[filterType] || 'Filter';
  const action = cleared ? 'cleared' : 'updated';
  announcements.textContent = `${filterName} filter ${action}`;
  
  // Clear the announcement after a delay
  setTimeout(() => {
    announcements.textContent = '';
  }, 1000);
}

function clearSearchResults() {
  const resultsDiv = document.getElementById('searchResults');
  if (resultsDiv) {
    resultsDiv.innerHTML = '<div class="no-results-message">Enter search criteria and click "Search Offers" to find available instances</div>';
  }
  
  // Reset all filters to default state
  window.vastaiSearchState = {
    sortBy: 'dph_total',
    vramMinGb: null,
    pcieMinGbps: null,
    netUpMinMbps: null,
    netDownMinMbps: null,
    priceMaxPerHour: null,
    locations: [],
    gpuModelQuery: ''
  };
  
  // Update all pill labels
  updateAllPillLabels();
  
  // Close any open editors
  closePillEditor();
}

function displaySearchResults(offers) {
  const resultsDiv = document.getElementById('searchResults');
  if (!resultsDiv) return;

  if (!offers || offers.length === 0) {
    resultsDiv.innerHTML = '<div class="no-results-message">No offers found matching your criteria</div>';
    return;
  }

  // Clear previous offers from store
  window.offerStore.clear();

  let html = '';
  offers.forEach((offer, index) => {
    const offerKey = `offer_${offer.id || index}_${Date.now()}`;
    window.offerStore.set(offerKey, offer);

    const gpuInfo  = offer.gpu_name || 'Unknown GPU';
    const gpuCount = offer.num_gpus || 1;
    const vram     = offer.gpu_ram ? `${Math.round(offer.gpu_ram / 1024)} GB` : 'N/A';
    const price    = offer.dph_total ? `$${offer.dph_total.toFixed(3)}/hr` : 'N/A';
    const location = offer.geolocation || [offer.country, offer.city].filter(Boolean).join(', ') || 'N/A';
    const pcieBw   = offer.pcie_bw ? `${offer.pcie_bw.toFixed(1)} GB/s` : 'N/A';
    const upDown   = `${offer.inet_up ? Math.round(offer.inet_up) : 0}↑/${offer.inet_down ? Math.round(offer.inet_down) : 0}↓ Mbps`;
    const flag     = getCountryFlag(location);

    html += `
      <div class="offer-item compact" data-offer-id="${offer.id || index}" data-offer-key="${offerKey}" tabindex="0" aria-expanded="false">
        <div class="offer-header">
          <div class="offer-title">${gpuInfo}${gpuCount > 1 ? ` (${gpuCount}x)` : ''}</div>
          <div class="offer-price">${price}</div>
        </div>

        <div class="offer-row">
          <div class="offer-meta">
            <span class="kv"><span class="k">VRAM</span><span class="v">${vram}</span></span>
            <span class="kv"><span class="k">PCIe</span><span class="v">${pcieBw}</span></span>
            <span class="kv"><span class="k">Net</span><span class="v">${upDown}</span></span>
            <span class="kv"><span class="k">Loc</span><span class="v">${flag}</span></span>
          </div>

          <div class="offer-actions compact-actions" aria-label="Actions">
            <button class="offer-action-btn icon" title="Details" aria-label="Details"
                    onclick="viewOfferDetails('${offerKey}')">ⓘ</button>
            <button class="offer-action-btn" onclick="createInstanceFromOffer('${offer.id}','${offer.gpu_name || 'GPU'}')">
              🚀 Create
            </button>
          </div>
        </div>
      </div>
    `;
  });

  resultsDiv.innerHTML = html;

  // NEW: enable mobile tap-to-reveal behavior
  setupMobileOfferTapReveal();

  showSetupResult(`Found ${offers.length} available offers`, 'success');
}

// Mobile-only: tap an offer to reveal its action buttons.
// Only one offer can be expanded at a time. Desktop unaffected.
function setupMobileOfferTapReveal() {
  const results = document.getElementById('searchResults');
  if (!results) return;

  // Remove existing event listeners to prevent duplicates
  if (window.mobileOfferState.clickHandler) {
    results.removeEventListener('click', window.mobileOfferState.clickHandler);
  }
  if (window.mobileOfferState.keydownHandler) {
    results.removeEventListener('keydown', window.mobileOfferState.keydownHandler);
  }

  // Clear any previously expanded element
  window.mobileOfferState.expandedEl = null;

  // Create new event handlers
  window.mobileOfferState.clickHandler = (e) => {
    // Only for mobile width
    if (!window.matchMedia('(max-width: 560px)').matches) return;

    // If the user tapped an action button, don't toggle the card
    if (e.target.closest('.offer-action-btn')) return;

    const item = e.target.closest('.offer-item');
    if (!item) return;

    // Toggle current; collapse previous
    if (window.mobileOfferState.expandedEl && window.mobileOfferState.expandedEl !== item) {
      window.mobileOfferState.expandedEl.classList.remove('expanded');
      window.mobileOfferState.expandedEl.setAttribute('aria-expanded', 'false');
    }

    const willExpand = !item.classList.contains('expanded');
    item.classList.toggle('expanded', willExpand);
    item.setAttribute('aria-expanded', willExpand ? 'true' : 'false');
    window.mobileOfferState.expandedEl = willExpand ? item : null;
  };

  window.mobileOfferState.keydownHandler = (e) => {
    if (!window.matchMedia('(max-width: 560px)').matches) return;

    const item = e.target.closest('.offer-item');
    if (!item) return;

    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      item.click();
    }
  };

  // Add the new event listeners
  results.addEventListener('click', window.mobileOfferState.clickHandler);
  results.addEventListener('keydown', window.mobileOfferState.keydownHandler);
}



// Modal dialog for offer details
function showOfferDetailsModal(details) {
  // Inject modal CSS once
  if (!document.getElementById('vastai-offer-modal-style')) {
    const style = document.createElement('style');
    style.id = 'vastai-offer-modal-style';
    style.textContent = `
      .vastai-modal-overlay {
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.4);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .vastai-modal {
        background: #fff;
        border-radius: 8px;
        max-width: 400px;
        width: 90%;
        box-shadow: 0 2px 16px rgba(0,0,0,0.2);
        padding: 24px 20px 16px 20px;
        position: relative;
        font-family: inherit;
        animation: fadeIn 0.2s;
      }
      .vastai-modal-close {
        position: absolute;
        top: 8px;
        right: 12px;
        background: none;
        border: none;
        font-size: 1.5em;
        color: #888;
        cursor: pointer;
      }
      .vastai-modal h2 {
        margin-top: 0;
        font-size: 1.2em;
        margin-bottom: 12px;
      }
      .vastai-modal table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 8px;
      }
      .vastai-modal td {
        padding: 4px 0;
        vertical-align: top;
      }
      .vastai-modal td:first-child {
        font-weight: bold;
        color: #333;
        width: 40%;
        padding-right: 8px;
      }
      @keyframes fadeIn {
        from { opacity: 0; transform: scale(0.98);}
        to { opacity: 1; transform: scale(1);}
      }
    `;
    document.head.appendChild(style);
  }

  // Remove any existing modal
  const old = document.getElementById('vastai-offer-modal-overlay');
  if (old) old.remove();

  // Create overlay
  const overlay = document.createElement('div');
  overlay.className = 'vastai-modal-overlay';
  overlay.id = 'vastai-offer-modal-overlay';

  // Modal content
  const modal = document.createElement('div');
  modal.className = 'vastai-modal';

  // Close button
  const closeBtn = document.createElement('button');
  closeBtn.className = 'vastai-modal-close';
  closeBtn.innerHTML = '&times;';
  closeBtn.onclick = () => overlay.remove();
  modal.appendChild(closeBtn);

  // Title
  const title = document.createElement('h2');
  title.textContent = 'Offer Details';
  modal.appendChild(title);

  // Details table
  const table = document.createElement('table');
  details.forEach(row => {
    const tr = document.createElement('tr');
    const tdLabel = document.createElement('td');
    tdLabel.textContent = row.label;
    const tdValue = document.createElement('td');
    tdValue.textContent = row.value;
    tr.appendChild(tdLabel);
    tr.appendChild(tdValue);
    table.appendChild(tr);
  });
  modal.appendChild(table);

  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  // Close modal on overlay click (but not when clicking inside modal)
  overlay.addEventListener('click', function(e) {
    if (e.target === overlay) overlay.remove();
  });
}

function viewOfferDetails(offerKey) {
  // Retrieve offer from secure storage
  const offer = window.offerStore.get(offerKey);
  if (!offer) {
    console.error('Offer not found for key:', offerKey);
    return;
  }
  
  let details = [
    { label: "Offer ID", value: offer.id },
    { label: "GPU", value: offer.gpu_name || 'N/A' },
    { label: "GPU Count", value: offer.num_gpus || 1 },
    { label: "GPU RAM", value: offer.gpu_ram ? Math.round(offer.gpu_ram / 1024) + ' GB' : 'N/A' },
    { label: "CPU RAM", value: offer.cpu_ram ? Math.round(offer.cpu_ram / 1024) + ' GB' : 'N/A' },
    { label: "Disk Space", value: offer.disk_space ? Math.round(offer.disk_space) + ' GB' : 'N/A' },
    { label: "Price", value: offer.dph_total ? '$' + offer.dph_total.toFixed(3) + '/hr' : 'N/A' },
    { label: "Location", value: offer.geolocation || [offer.country, offer.city].filter(Boolean).join(', ') || 'N/A' },
    { label: "Reliability", value: offer.reliability ? (offer.reliability * 100).toFixed(1) + '%' : 'N/A' },
    { label: "Score", value: offer.score ? offer.score.toFixed(2) : 'N/A' },
    { label: "CPU", value: offer.cpu_name || 'N/A' },
    { label: "Download Speed", value: offer.download_speed ? offer.download_speed + ' Mbps' : 'N/A' },
    { label: "Upload Speed", value: offer.upload_speed ? offer.upload_speed + ' Mbps' : 'N/A' }
  ];
  showOfferDetailsModal(details);
}

async function createInstanceFromOffer(offerId, gpuName) {
  if (!confirm(`Create instance from offer: ${gpuName}?\n\nThis will use your VastAI account to create a new instance.`)) {
    return;
  }
  
  showSetupResult(`Creating instance from offer ${offerId}...`, 'info');
  
  try {
    const data = await api.post('/vastai/create-instance', {
      offer_id: offerId
    });
    
    if (data.success) {
      showSetupResult(`✅ Instance created successfully! Instance ID: ${data.instance_id || 'Unknown'}`, 'success');
      // Refresh the instances list
      loadVastaiInstances();
      // Close the search modal
      closeSearchOffersModal();
    } else {
      showSetupResult(`❌ Failed to create instance: ${data.message || 'Unknown error'}`, 'error');
    }
  } catch (error) {
    showSetupResult(`❌ Request failed: ${error.message}`, 'error');
  }
}

// Expose search functions
window.openSearchOffersModal = openSearchOffersModal;
window.closeSearchOffersModal = closeSearchOffersModal;
window.searchVastaiOffers = searchVastaiOffers;
window.clearSearchResults = clearSearchResults;
window.viewOfferDetails = viewOfferDetails;
window.createInstanceFromOffer = createInstanceFromOffer;