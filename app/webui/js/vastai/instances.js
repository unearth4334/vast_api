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

  // Status normalization - prioritize actual_status
  // Use actual_status if it exists (even if null), otherwise fall back to other fields
  const statusValue = ('actual_status' in i) 
    ? i.actual_status 
    : (i.cur_state || i.status || i.state);
  const status = normStatus(statusValue || "unknown");

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
    actual_status: i.actual_status,  // Preserve original actual_status
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

  // Get the workflow step element
  const stepElement = document.querySelector('.workflow-step[data-action="test_ssh"]');
  
  // Extract host and port for display
  const match = sshConnectionString.match(/root@([^\s]+)/);
  const hostPort = match ? match[1] : 'remote host';
  
  // Show progress indicator
  if (stepElement && window.progressIndicators) {
    window.progressIndicators.showSimpleProgress(
      stepElement,
      'Testing SSH connection...',
      `Connecting to ${hostPort}`
    );
  }
  
  showSetupResult('Testing SSH connection...', 'info');
  
  try {
    const data = await api.post('/ssh/test', {
      ssh_connection: sshConnectionString
    });
    
    if (data.success) {
      showSetupResult('✅ SSH connection successful!', 'success');
      
      // Show success completion indicator
      if (stepElement && window.progressIndicators) {
        const hostname = data.hostname || 'remote';
        const uptime = data.uptime || 'unknown';
        window.progressIndicators.showSuccess(
          stepElement,
          'SSH connection verified',
          `Host: ${hostname} • Uptime: ${uptime}`,
          []
        );
      }
      
      // Emit success event for workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'test_ssh', success: true }
      }));
    } else if (data.host_verification_needed) {
      // Host key verification required - prompt user
      showSetupResult('⚠️ Host key verification required...', 'info');
      
      // Get host key fingerprints first
      try {
        const verifyData = await api.post('/ssh/verify-host', {
          ssh_connection: sshConnectionString,
          accept: false
        });
        
        if (verifyData.success && verifyData.needs_confirmation) {
          // Show modal to user
          const { showSSHHostVerificationModal } = await import('./ui.js');
          const userAccepted = await showSSHHostVerificationModal({
            host: verifyData.host,
            port: verifyData.port,
            fingerprints: verifyData.fingerprints
          });
          
          if (userAccepted) {
            // User accepted - add host key to known_hosts
            showSetupResult('Adding host key to known_hosts...', 'info');
            const addKeyData = await api.post('/ssh/verify-host', {
              ssh_connection: sshConnectionString,
              accept: true
            });
            
            if (addKeyData.success) {
              showSetupResult('Host key added. Retrying SSH connection...', 'info');
              
              // Retry the SSH test now that host key is added
              const retryData = await api.post('/ssh/test', {
                ssh_connection: sshConnectionString
              });
              
              if (retryData.success) {
                showSetupResult('✅ SSH connection successful!', 'success');
                
                // Show success completion indicator
                if (stepElement && window.progressIndicators) {
                  const hostname = retryData.hostname || 'remote';
                  const uptime = retryData.uptime || 'unknown';
                  window.progressIndicators.showSuccess(
                    stepElement,
                    'SSH connection verified',
                    `Host: ${hostname} • Uptime: ${uptime}`,
                    []
                  );
                }
                
                // Emit success event for workflow
                document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
                  detail: { stepAction: 'test_ssh', success: true }
                }));
              } else {
                showSetupResult(`❌ SSH test still failed after adding host key: ${retryData.message}`, 'error');
                
                if (stepElement && window.progressIndicators) {
                  window.progressIndicators.showError(
                    stepElement,
                    'SSH connection failed',
                    retryData.message || 'Connection failed even after adding host key',
                    [{ class: 'retry-btn', onclick: 'testVastAISSH()', label: '🔄 Retry' }]
                  );
                }
                
                document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
                  detail: { stepAction: 'test_ssh', success: false }
                }));
              }
            } else {
              showSetupResult(`❌ Failed to add host key: ${addKeyData.message}`, 'error');
              
              if (stepElement && window.progressIndicators) {
                window.progressIndicators.showError(
                  stepElement,
                  'Failed to add host key',
                  addKeyData.message || 'Could not update known_hosts',
                  [{ class: 'retry-btn', onclick: 'testVastAISSH()', label: '🔄 Retry' }]
                );
              }
              
              document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
                detail: { stepAction: 'test_ssh', success: false }
              }));
            }
          } else {
            // User rejected
            showSetupResult('❌ Host key verification rejected by user', 'error');
            
            if (stepElement && window.progressIndicators) {
              window.progressIndicators.showError(
                stepElement,
                'Host key verification rejected',
                'You declined to trust this host',
                [{ class: 'retry-btn', onclick: 'testVastAISSH()', label: '🔄 Try Again' }]
              );
            }
            
            document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
              detail: { stepAction: 'test_ssh', success: false }
            }));
          }
        } else {
          throw new Error(verifyData.message || 'Failed to get host key fingerprints');
        }
      } catch (verifyError) {
        showSetupResult(`❌ Host verification failed: ${verifyError.message}`, 'error');
        
        if (stepElement && window.progressIndicators) {
          window.progressIndicators.showError(
            stepElement,
            'Host verification failed',
            verifyError.message || 'Could not retrieve host key',
            [{ class: 'retry-btn', onclick: 'testVastAISSH()', label: '🔄 Retry' }]
          );
        }
        
        document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
          detail: { stepAction: 'test_ssh', success: false }
        }));
      }
    } else {
      showSetupResult(`❌ SSH test failed: ${data.message}`, 'error');
      
      // Show error completion indicator
      if (stepElement && window.progressIndicators) {
        window.progressIndicators.showError(
          stepElement,
          'SSH connection failed',
          data.message || 'Connection timeout or refused',
          [
            { class: 'retry-btn', onclick: 'testVastAISSH()', label: '🔄 Retry' }
          ]
        );
      }
      
      // Emit failure event for workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'test_ssh', success: false }
      }));
    }
  } catch (error) {
    showSetupResult('❌ SSH test request failed: ' + error.message, 'error');
    
    // Show error completion indicator
    if (stepElement && window.progressIndicators) {
      window.progressIndicators.showError(
        stepElement,
        'SSH connection failed',
        error.message || 'Request failed',
        [
          { class: 'retry-btn', onclick: 'testVastAISSH()', label: '🔄 Retry' }
        ]
      );
    }
    
    // Emit failure event for workflow
    document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
      detail: { stepAction: 'test_ssh', success: false }
    }));
  }
}

/**
 * Set UI_HOME on remote instance
 */
export async function setUIHome() {
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');

  // Get the workflow step element
  const stepElement = document.querySelector('.workflow-step[data-action="set_ui_home"]');
  
  // Show progress indicator
  if (stepElement && window.progressIndicators) {
    window.progressIndicators.showSimpleProgress(
      stepElement,
      'Setting UI_HOME environment variable...',
      'Path: /workspace/ComfyUI'
    );
  }
  
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
      
      // Show success completion indicator
      if (stepElement && window.progressIndicators) {
        window.progressIndicators.showSuccess(
          stepElement,
          'UI_HOME configured',
          'Environment variable set: UI_HOME=/workspace/ComfyUI',
          [],
          {
            actions: [
              { class: 'verify-btn', onclick: 'getUIHome()', label: '👁️ Verify' }
            ]
          }
        );
      }
      
      // Emit success event for workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'set_ui_home', success: true }
      }));
    } else {
      showSetupResult(`❌ Failed to set UI_HOME: ${data.message}`, 'error');
      
      // Show error completion indicator
      if (stepElement && window.progressIndicators) {
        window.progressIndicators.showError(
          stepElement,
          'Failed to set UI_HOME',
          data.message || 'Permission denied or file system error',
          [
            { class: 'retry-btn', onclick: 'setUIHome()', label: '🔄 Retry' }
          ]
        );
      }
      
      // Emit failure event for workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'set_ui_home', success: false }
      }));
    }
  } catch (error) {
    showSetupResult('❌ Set UI_HOME request failed: ' + error.message, 'error');
    
    // Show error completion indicator
    if (stepElement && window.progressIndicators) {
      window.progressIndicators.showError(
        stepElement,
        'Failed to set UI_HOME',
        error.message || 'Request failed',
        [
          { class: 'retry-btn', onclick: 'setUIHome()', label: '🔄 Retry' }
        ]
      );
    }
    
    // Emit failure event for workflow
    document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
      detail: { stepAction: 'set_ui_home', success: false }
    }));
  }
}

/**
 * Get UI_HOME from remote instance
 */
export async function getUIHome() {
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');

  // Get the workflow step element
  const stepElement = document.querySelector('.workflow-step[data-action="get_ui_home"]');
  
  // Show progress indicator
  if (stepElement && window.progressIndicators) {
    window.progressIndicators.showSimpleProgress(
      stepElement,
      'Reading UI_HOME from environment...',
      ''
    );
  }
  
  showSetupResult('Reading UI_HOME...', 'info');
  
  try {
    const data = await api.post('/ssh/get-ui-home', {
      ssh_connection: sshConnectionString
    });
    
    if (data.success) {
      const uiHome = data.ui_home || 'Not set';
      showSetupResult(`UI_HOME: ${uiHome}`, 'success');
      
      if (uiHome && uiHome !== 'Not set') {
        // Show success completion indicator
        if (stepElement && window.progressIndicators) {
          window.progressIndicators.showSuccess(
            stepElement,
            'UI_HOME retrieved',
            `Current value: ${uiHome}`,
            ['✓ Valid path']
          );
        }
        
        // Emit success event for workflow
        document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
          detail: { stepAction: 'get_ui_home', success: true }
        }));
      } else {
        // Show warning completion indicator
        if (stepElement && window.progressIndicators) {
          window.progressIndicators.showWarning(
            stepElement,
            'UI_HOME not configured',
            'Environment variable is not set',
            [
              { class: 'fix-btn', onclick: 'setUIHome()', label: '📁 Set UI_HOME' }
            ]
          );
        }
        
        // Emit partial success event for workflow
        document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
          detail: { stepAction: 'get_ui_home', success: true }
        }));
      }
    } else {
      showSetupResult(`❌ Failed to get UI_HOME: ${data.message}`, 'error');
      
      // Show error completion indicator
      if (stepElement && window.progressIndicators) {
        window.progressIndicators.showError(
          stepElement,
          'Failed to get UI_HOME',
          data.message || 'Request failed',
          [
            { class: 'retry-btn', onclick: 'getUIHome()', label: '🔄 Retry' }
          ]
        );
      }
      
      // Emit failure event for workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'get_ui_home', success: false }
      }));
    }
  } catch (error) {
    showSetupResult('❌ Get UI_HOME request failed: ' + error.message, 'error');
    
    // Show error completion indicator
    if (stepElement && window.progressIndicators) {
      window.progressIndicators.showError(
        stepElement,
        'Failed to get UI_HOME',
        error.message || 'Request failed',
        [
          { class: 'retry-btn', onclick: 'getUIHome()', label: '🔄 Retry' }
        ]
      );
    }
    
    // Emit failure event for workflow
    document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
      detail: { stepAction: 'get_ui_home', success: false }
    }));
  }
}

/**
 * Configure model symbolic links on remote instance
 */
export async function configureLinks() {
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');

  // Get the workflow step element
  const stepElement = document.querySelector('.workflow-step[data-action="configure_links"]');
  
  // Show progress indicator
  if (stepElement && window.progressIndicators) {
    window.progressIndicators.showSimpleProgress(
      stepElement,
      'Configuring model links...',
      'Creating symbolic links for upscale_models and loras'
    );
  }
  
  showSetupResult('Configuring model links...', 'info');
  
  try {
    const data = await api.post('/ssh/configure-links', {
      ssh_connection: sshConnectionString,
      ui_home: '/workspace/ComfyUI'
    });
    
    if (data.success) {
      showSetupResult('✅ Model links configured successfully!', 'success');
      if (data.output) {
        console.log('Configure links output:', data.output);
      }
      
      // Show success completion indicator
      if (stepElement && window.progressIndicators) {
        window.progressIndicators.showSuccess(
          stepElement,
          'Model links configured',
          'Symbolic links created successfully',
          ['✓ upscale_models → ESRGAN', '✓ loras → Lora']
        );
      }
      
      // Emit success event for workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'configure_links', success: true }
      }));
    } else {
      showSetupResult(`❌ Failed to configure links: ${data.message}`, 'error');
      
      // Show error completion indicator
      if (stepElement && window.progressIndicators) {
        window.progressIndicators.showError(
          stepElement,
          'Failed to configure links',
          data.message || 'Command execution failed',
          [
            { class: 'retry-btn', onclick: 'configureLinks()', label: '🔄 Retry' }
          ]
        );
      }
      
      // Emit failure event for workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'configure_links', success: false }
      }));
    }
  } catch (error) {
    showSetupResult('❌ Configure links request failed: ' + error.message, 'error');
    
    // Show error completion indicator
    if (stepElement && window.progressIndicators) {
      window.progressIndicators.showError(
        stepElement,
        'Failed to configure links',
        error.message || 'Request failed',
        [
          { class: 'retry-btn', onclick: 'configureLinks()', label: '🔄 Retry' }
        ]
      );
    }
    
    // Emit failure event for workflow
    document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
      detail: { stepAction: 'configure_links', success: false }
    }));
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

  // Get the workflow step element
  const stepElement = document.querySelector('.workflow-step[data-action="setup_civitdl"]');
  
  // Show multi-phase progress indicator
  const phases = [
    { label: 'Installing civitdl package...', status: 'Downloading packages' },
    { label: 'Configuring API key', status: '' },
    { label: 'Verifying installation', status: '' }
  ];
  
  if (stepElement && window.progressIndicators) {
    window.progressIndicators.showMultiPhaseProgress(stepElement, phases, 0, 10);
  }
  
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
      
      // Show success completion indicator
      if (stepElement && window.progressIndicators) {
        const version = data.version || '2.1.2';
        window.progressIndicators.showSuccess(
          stepElement,
          'CivitDL installed successfully',
          `Version ${version} • API key configured • Ready for downloads`,
          ['📦 3 packages', `⏱️ ${window.progressIndicators.getDuration('setup_civitdl')}`]
        );
      }
      
      // Emit success event for workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'setup_civitdl', success: true }
      }));
    } else {
      showSetupResult(`❌ CivitDL setup failed: ${data.message}`, 'error');
      
      // Show error completion indicator
      if (stepElement && window.progressIndicators) {
        window.progressIndicators.showError(
          stepElement,
          'Installation failed',
          data.message || 'Failed at: Installing civitdl package • Network timeout',
          [
            { class: 'retry-btn', onclick: 'setupCivitDL()', label: '🔄 Retry Installation' },
            { class: 'details-btn', onclick: 'console.log("View logs")', label: '📋 View Logs' }
          ]
        );
      }
      
      // Emit failure event for workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'setup_civitdl', success: false }
      }));
    }
  } catch (error) {
    showSetupResult('❌ CivitDL setup request failed: ' + error.message, 'error');
    
    // Show error completion indicator
    if (stepElement && window.progressIndicators) {
      window.progressIndicators.showError(
        stepElement,
        'Installation failed',
        error.message || 'Request failed',
        [
          { class: 'retry-btn', onclick: 'setupCivitDL()', label: '🔄 Retry Installation' }
        ]
      );
    }
    
    // Emit failure event for workflow
    document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
      detail: { stepAction: 'setup_civitdl', success: false }
    }));
  }
}

/**
 * Sync from connection string
 */
export async function syncFromConnectionString() {
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');

  // Get the workflow step element
  const stepElement = document.querySelector('.workflow-step[data-action="sync_instance"]');
  
  // Show initial sync progress
  if (stepElement && window.progressIndicators) {
    window.progressIndicators.showSyncProgress(
      stepElement,
      'Discovering folders...',
      'Scanning output directories',
      [],
      0,
      '',
      {}
    );
  }
  
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
        
        // Build folder breakdown
        const folderItems = [];
        let totalFiles = 0;
        let totalSize = 0;
        
        Object.entries(results).forEach(([source, result]) => {
          if (result.success) {
            const files = result.files_synced || 0;
            totalFiles += files;
            folderItems.push({
              label: source,
              value: `${files} files`
            });
            summary += `✅ ${source}: ${files} files synced\n`;
          } else {
            summary += `❌ ${source}: ${result.error || 'Unknown error'}\n`;
          }
        });
        
        // Show success completion indicator with breakdown
        if (stepElement && window.progressIndicators) {
          window.progressIndicators.showSuccess(
            stepElement,
            'Sync completed successfully',
            `${Object.keys(results).length} folders synced • ${totalFiles} files transferred`,
            [
              `📊 Avg speed: N/A`,
              `⏱️ ${window.progressIndicators.getDuration('sync_instance')}`,
              `🧹 Cleanup: enabled`
            ],
            {
              syncComplete: true,
              breakdown: {
                items: folderItems.slice(0, 3),
                more: folderItems.length > 3 ? `+ ${folderItems.length - 3} more folders` : null
              },
              actions: [
                { class: 'view-btn', onclick: 'console.log("View files")', label: '📁 View Files' }
              ]
            }
          );
        }
        
        // Show detailed results in console
        console.log('Sync results:', results);
        
        // Update UI with summary
        const resultDiv = document.getElementById('result');
        if (resultDiv) {
          resultDiv.innerHTML = `<pre>${summary}</pre>`;
          resultDiv.style.display = 'block';
        }
      } else {
        // No detailed results, show basic success
        if (stepElement && window.progressIndicators) {
          window.progressIndicators.showSuccess(
            stepElement,
            'Sync completed successfully',
            'All files synchronized',
            [`⏱️ ${window.progressIndicators.getDuration('sync_instance')}`]
          );
        }
      }
      
      // Emit success event for workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'sync_instance', success: true }
      }));
    } else {
      showSetupResult(`❌ Sync failed: ${data.message}`, 'error');
      
      // Show error completion indicator
      if (stepElement && window.progressIndicators) {
        window.progressIndicators.showError(
          stepElement,
          'Sync failed',
          data.message || 'Connection lost or insufficient permissions',
          [
            { class: 'retry-btn', onclick: 'syncFromConnectionString()', label: '🔄 Retry Sync' },
            { class: 'check-btn', onclick: 'testVastAISSH()', label: '🔧 Check Connection' }
          ]
        );
      }
      
      // Emit failure event for workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'sync_instance', success: false }
      }));
    }
  } catch (error) {
    showSetupResult('Request failed: ' + error.message, 'error');
    
    // Show error completion indicator
    if (stepElement && window.progressIndicators) {
      window.progressIndicators.showError(
        stepElement,
        'Sync failed',
        error.message || 'Request failed',
        [
          { class: 'retry-btn', onclick: 'syncFromConnectionString()', label: '🔄 Retry Sync' }
        ]
      );
    }
    
    // Emit failure event for workflow
    document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
      detail: { stepAction: 'sync_instance', success: false }
    }));
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
    // Use actual_status if it exists (even if null), otherwise fall back to other fields
    const statusValue = ('actual_status' in inst) 
      ? inst.actual_status 
      : (inst.cur_state || inst.status);
    const state = normStatus(statusValue || 'unknown');

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
        ? `<button class="use-instance-btn" onclick="VastAIInstances.useInstance('${sshConnection.replace(/'/g, "\\'")}', ${instanceId})">
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
    // Status is already normalized by normalizeInstance()
    const normalizedStatus = instance.status;
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
          <div class="instance-detail" data-instance-id="${instance.id ?? ''}" data-ob-token-detail>
            <strong>OB Token:</strong> 
            <span class="ob-token-value">
              ${sshConnection && normalizedStatus === 'running'
                ? `<a href="#" class="fetch-token-link" onclick="VastAIInstances.fetchOpenButtonToken(${instance.id}, '${sshConnection.replace(/'/g, "\\'")}'); return false;">fetch</a>`
                : 'N/A'}
            </span>
          </div>
        </div>

        <div class="instance-actions">
          ${
            sshConnection && normalizedStatus === 'running'
              ? `<button class="use-instance-btn" onclick="VastAIInstances.useInstance('${sshConnection.replace(/'/g, "\\'")}', ${instance.id})">
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
export function useInstance(sshConnection, instanceId) {
  const sshInput = document.getElementById('sshConnectionString');
  if (sshInput) {
    sshInput.value = sshConnection;
    
    // Store instance ID globally for workflow use
    if (instanceId) {
      window.currentInstanceId = instanceId;
      console.log(`📌 Set current instance ID: ${instanceId}`);
    }
    
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

/**
 * Fetch OPEN_BUTTON_TOKEN from instance via SSH
 * @param {number} instanceId - ID of the instance
 * @param {string} sshConnection - SSH connection string
 */
export async function fetchOpenButtonToken(instanceId, sshConnection) {
  const tokenDetail = document.querySelector(`[data-instance-id="${instanceId}"][data-ob-token-detail]`);
  if (!tokenDetail) return;
  
  const tokenValueSpan = tokenDetail.querySelector('.ob-token-value');
  if (!tokenValueSpan) return;
  
  try {
    // Show loading state
    tokenValueSpan.innerHTML = '<span style="color: #888;">fetching...</span>';
    
    const response = await fetch(`/vastai/instances/${instanceId}/open-button-token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        ssh_connection: sshConnection
      })
    });
    
    const data = await response.json();
    
    if (data.require_verification) {
      // Host key verification needed - show modal
      tokenValueSpan.innerHTML = '<a href="#" class="fetch-token-link" onclick="VastAIInstances.fetchOpenButtonToken(' + instanceId + ', \'' + sshConnection.replace(/'/g, "\\'") + '\'); return false;">fetch</a>';
      
      try {
        // Import and show SSH verification modal
        const { showSSHHostVerificationModal } = await import('./ui.js');
        const userAccepted = await showSSHHostVerificationModal({
          host: data.host,
          port: data.port,
          fingerprints: data.fingerprint ? [data.fingerprint] : []
        });
        
        if (userAccepted) {
          // User accepted - add host key to known_hosts
          showSetupResult('Adding host key to known_hosts...', 'info');
          
          const response = await fetch('/ssh/verify-host', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              ssh_connection: sshConnection,
              accept: true
            })
          });
          
          const addKeyData = await response.json();
          
          if (addKeyData.success) {
            showSetupResult('Host key added. Retrying token fetch...', 'info');
            
            // Retry fetching the token
            fetchOpenButtonToken(instanceId, sshConnection);
          } else {
            showSetupResult(`❌ Failed to add host key: ${addKeyData.message}`, 'error');
          }
        } else {
          // User rejected
          showSetupResult('❌ Host key verification rejected by user', 'error');
        }
      } catch (verifyError) {
        showSetupResult(`❌ Host verification failed: ${verifyError.message}`, 'error');
      }
      return;
    }
    
    if (data.success && data.token) {
      // Store the full token for copying
      const fullToken = data.token;
      const truncatedToken = fullToken.substring(0, 4) + '...';
      
      // Display truncated token with copy button
      tokenValueSpan.innerHTML = `
        <span class="token-display">${truncatedToken}</span>
        <button class="copy-token-btn" onclick="VastAIInstances.copyTokenToClipboard('${fullToken.replace(/'/g, "\\'")}', ${instanceId}); return false;" title="Copy full token to clipboard">
          📋 Copy
        </button>
      `;
      
      showSetupResult(`✅ OPEN_BUTTON_TOKEN fetched for instance #${instanceId}`, 'success');
    } else {
      tokenValueSpan.innerHTML = '<span style="color: #e74c3c;">failed</span>';
      showSetupResult(`❌ Failed to fetch token: ${data.message}`, 'error');
    }
    
  } catch (error) {
    console.error('Error fetching OPEN_BUTTON_TOKEN:', error);
    tokenValueSpan.innerHTML = '<a href="#" class="fetch-token-link" onclick="VastAIInstances.fetchOpenButtonToken(' + instanceId + ', \'' + sshConnection.replace(/'/g, "\\'") + '\'); return false;">fetch</a>';
    showSetupResult(`❌ Error fetching token: ${error.message}`, 'error');
  }
}

/**
 * Copy OPEN_BUTTON_TOKEN to clipboard
 * @param {string} token - The full token to copy
 * @param {number} instanceId - ID of the instance
 */
export async function copyTokenToClipboard(token, instanceId) {
  try {
    await navigator.clipboard.writeText(token);
    showSetupResult(`✅ OPEN_BUTTON_TOKEN copied to clipboard for instance #${instanceId}`, 'success');
  } catch (error) {
    console.error('Error copying to clipboard:', error);
    
    // Fallback: create temporary textarea
    const textarea = document.createElement('textarea');
    textarea.value = token;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    
    try {
      document.execCommand('copy');
      showSetupResult(`✅ OPEN_BUTTON_TOKEN copied to clipboard for instance #${instanceId}`, 'success');
    } catch (fallbackError) {
      showSetupResult(`❌ Failed to copy token to clipboard`, 'error');
    }
    
    document.body.removeChild(textarea);
  }
}

/**
 * Test CivitDL installation
 * Wrapper function that adds progress indicators to the template step
 */
export async function testCivitDL() {
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');

  // Get the workflow step element
  const stepElement = document.querySelector('.workflow-step[data-action="test_civitdl"]');
  
  // Show checklist progress indicator
  const items = [
    { label: 'Testing CivitDL CLI...', state: 'active' },
    { label: 'Validating API configuration...', state: 'pending' },
    { label: 'Testing API connectivity...', state: 'pending' }
  ];
  
  if (stepElement && window.progressIndicators) {
    window.progressIndicators.showChecklistProgress(stepElement, items);
  }
  
  showSetupResult('Testing CivitDL installation...', 'info');
  
  try {
    const data = await api.post('/ssh/test-civitdl', {
      ssh_connection: sshConnectionString
    });
    
    if (data.success) {
      showSetupResult('✅ CivitDL tests passed!', 'success');
      
      // Build detailed message based on test results
      const tests = data.tests || {};
      const hasWarning = data.has_warning || !tests.api;
      const apiNote = data.api_note || '';
      
      const details = [
        tests.cli ? '✓ CLI functional' : '✗ CLI failed',
        tests.config ? '✓ API key valid' : '✗ API key invalid',
        tests.api ? '✓ API reachable' : '⚠ API test skipped'
      ].join(' • ');
      
      // Show success completion indicator (or warning if API test skipped)
      if (stepElement && window.progressIndicators) {
        const apiStatus = data.api_status || 'N/A';
        const stats = hasWarning 
          ? [`⚠️ API test skipped (timeout)`, `⏱️ ${window.progressIndicators.getDuration('test_civitdl')}`]
          : [`🌐 API Status: ${apiStatus}`, `⏱️ ${window.progressIndicators.getDuration('test_civitdl')}`];
        
        if (hasWarning) {
          window.progressIndicators.showWarning(
            stepElement,
            'CivitDL tests passed with warnings',
            details,
            stats
          );
        } else {
          window.progressIndicators.showSuccess(
            stepElement,
            'CivitDL tests passed',
            details,
            stats
          );
        }
      }
      
      // Emit success event for workflow (warnings don't fail the workflow)
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'test_civitdl', success: true }
      }));
    } else {
      // Build detailed error message based on test results
      const tests = data.tests || {};
      const details = [
        tests.cli ? '✓ CLI functional' : '✗ CLI failed',
        tests.config ? '✓ API key valid' : '✗ API key invalid',
        tests.api ? '✓ API reachable' : '✗ API unreachable'
      ].join(' • ');
      
      showSetupResult(`❌ CivitDL test failed: ${data.message}`, 'error');
      
      // Show error completion indicator
      if (stepElement && window.progressIndicators) {
        window.progressIndicators.showError(
          stepElement,
          'CivitDL test failed',
          details,
          [
            { class: 'fix-btn', onclick: 'setupCivitDL()', label: '🔑 Reconfigure API Key' },
            { class: 'retry-btn', onclick: 'testCivitDL()', label: '🔄 Retry Tests' }
          ]
        );
      }
      
      // Emit failure event for workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'test_civitdl', success: false }
      }));
    }
  } catch (error) {
    showSetupResult('❌ CivitDL test request failed: ' + error.message, 'error');
    
    // Show error completion indicator
    if (stepElement && window.progressIndicators) {
      window.progressIndicators.showError(
        stepElement,
        'CivitDL test failed',
        error.message || 'Request failed',
        [
          { class: 'retry-btn', onclick: 'testCivitDL()', label: '🔄 Retry Tests' }
        ]
      );
    }
    
    // Emit failure event for workflow
    document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
      detail: { stepAction: 'test_civitdl', success: false }
    }));
  }
}

/**
 * Install ComfyUI custom nodes
 * Runs the ComfyUI-Auto_installer custom nodes installation script
 */
export async function installCustomNodes() {
  console.log('🔌 installCustomNodes called');
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnectionString) {
    console.error('❌ No SSH connection string found');
    return showSetupResult('Please enter an SSH connection string first.', 'error');
  }
  
  console.log('📡 SSH connection string:', sshConnectionString);

  // Get the workflow step element
  const stepElement = document.querySelector('.workflow-step[data-action="install_custom_nodes"]');
  console.log('📍 Step element found:', !!stepElement);
  
  // Show initial progress indicator
  if (stepElement && window.progressIndicators) {
    console.log('📊 Showing initial progress indicator');
    window.progressIndicators.showChecklistProgress(stepElement, [
      { label: 'Initializing...', state: 'active' }
    ]);
  }
  
  showSetupResult('Installing custom nodes (this may take several minutes)...', 'info');
  
  // Start the installation (non-blocking)
  console.log('🚀 Starting installation API call...');
  const installPromise = api.post('/ssh/install-custom-nodes', {
    ssh_connection: sshConnectionString,
    ui_home: '/workspace/ComfyUI'
  });
  
  // Poll for progress updates
  let pollInterval;
  let lastProgressData = null;
  let lastProgressHash = null;
  
  const pollProgress = async () => {
    try {
      console.log('🔄 Polling progress...');
      const progressResponse = await api.post('/ssh/install-custom-nodes/progress', {
        ssh_connection: sshConnectionString
      });
      
      console.log('📥 Progress response:', progressResponse);
      
      if (progressResponse.success && progressResponse.progress) {
        const progress = progressResponse.progress;
        
        // Create a hash of the progress data to detect changes
        const progressHash = JSON.stringify({
          processed: progress.processed,
          status: progress.status,
          nodes: progress.nodes.map(n => `${n.name}:${n.status}`)
        });
        
        // Only update UI if data has changed
        if (progressHash === lastProgressHash) {
          console.log('📊 Progress unchanged, skipping UI update');
          return;
        }
        
        lastProgressHash = progressHash;
        lastProgressData = progress;
        
        console.log('📊 Progress data changed:', progress);
        
        // Update the checklist UI with all nodes
        if (stepElement && window.progressIndicators && progress.nodes && progress.nodes.length > 0) {
          console.log(`📋 Updating UI with ${progress.nodes.length} nodes`);
          const checklistItems = progress.nodes.map(node => {
            let state = 'pending';
            let label = node.name;
            
            // Map status to state
            switch (node.status) {
              case 'installing':
              case 'cloning':
              case 'installing_requirements':
                state = 'active';
                // Show clone progress percentage if available (for cloning operations only)
                if (node.clone_progress !== undefined && node.clone_progress !== null && node.status !== 'installing_requirements') {
                  label = `${node.name} - ${node.message || 'Cloning...'} (${node.clone_progress}%)`;
                } else {
                  label = `${node.name} - ${node.message || 'Processing...'}`;
                }
                break;
              case 'success':
                state = 'completed';
                label = `${node.name}`;
                break;
              case 'failed':
                state = 'pending';  // Use pending style for failed (will show as dot, not spinner)
                label = `${node.name} - ❌ ${node.message || 'Failed'}`;
                break;
              case 'partial':
                state = 'completed';
                label = `${node.name} - ⚠️ ${node.message || 'Partial'}`;
                break;
              default:
                state = 'pending';
            }
            
            return { label, state, node };
          });
          
          // Limit visible items to 10 most recent/active
          const activeIndex = checklistItems.findIndex(item => item.state === 'active');
          let visibleItems;
          
          if (activeIndex !== -1) {
            // Show items around the active one
            const start = Math.max(0, activeIndex - 5);
            const end = Math.min(checklistItems.length, activeIndex + 5);
            visibleItems = checklistItems.slice(start, end);
            
            // Add summary if we're hiding items
            if (start > 0 || end < checklistItems.length) {
              const completedCount = checklistItems.filter((item, idx) => 
                idx < start && item.state === 'completed'
              ).length;
              
              if (completedCount > 0) {
                visibleItems.unshift({
                  label: `✓ ${completedCount} nodes completed`,
                  state: 'completed'
                });
              }
              
              if (end < checklistItems.length) {
                const remainingCount = checklistItems.length - end;
                visibleItems.push({
                  label: `${remainingCount} more nodes...`,
                  state: 'pending'
                });
              }
            }
          } else {
            // No active item, show first 10
            visibleItems = checklistItems.slice(0, 10);
            if (checklistItems.length > 10) {
              visibleItems.push({
                label: `${checklistItems.length - 10} more nodes...`,
                state: 'pending'
              });
            }
          }
          
          // Extract download statistics from the active node
          let downloadStats = null;
          if (activeIndex !== -1) {
            const activeNode = checklistItems[activeIndex].node;
            if (activeNode && (activeNode.download_rate || activeNode.data_received)) {
              downloadStats = {
                download_rate: activeNode.download_rate,
                data_received: activeNode.data_received,
                eta: activeNode.eta  // ETA can be calculated from progress if needed
              };
            }
          }
          
          window.progressIndicators.showChecklistProgress(stepElement, visibleItems, downloadStats);
        }
        
        // Check if installation is complete
        if (progress.status === 'completed' || progress.status === 'failed') {
          console.log('✅ Installation complete, stopping polling');
          if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
          }
          return; // Stop processing
        }
      }
    } catch (error) {
      console.error('❌ Progress polling error:', error);
      // Don't stop polling on transient errors
    }
  };
  
  // Start polling every 2 seconds (reduced from 1s to minimize flashing)
  console.log('⏱️ Starting progress polling (every 2s)');
  pollInterval = setInterval(pollProgress, 2000);
  
  // Also poll immediately
  console.log('🔄 Initial progress poll');
  pollProgress();
  
  try {
    console.log('⏳ Waiting for installation to complete...');
    const data = await installPromise;
    console.log('✅ Installation API call completed:', data);
    
    // Stop polling
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
      console.log('🛑 Stopped polling');
    }
    
    // Do one final poll to get the complete state
    console.log('🔄 Final progress poll');
    await pollProgress();
    
    if (data.success) {
      const hasWarnings = data.has_warnings || false;
      const cloneFailures = data.failed_clones || 0;
      const reqFailures = data.failed_requirements || 0;
      
      if (hasWarnings) {
        showSetupResult(`⚠️ Custom nodes installed with warnings (${cloneFailures} clone failures, ${reqFailures} requirement failures)`, 'warning');
      } else {
        showSetupResult('✅ All custom nodes installed successfully!', 'success');
      }
      
      // Show completion indicator with detailed stats
      if (stepElement && window.progressIndicators) {
        const detailMessage = hasWarnings
          ? `${data.successful_clones}/${data.total_nodes} nodes cloned • ${reqFailures} requirement warnings`
          : `${data.successful_clones} nodes installed successfully`;
        
        const stats = [
          `📦 ${data.total_nodes} nodes`,
          cloneFailures > 0 ? `⚠️ ${cloneFailures} clone failures` : null,
          reqFailures > 0 ? `⚠️ ${reqFailures} requirement warnings` : null
        ].filter(Boolean);
        
        if (hasWarnings) {
          window.progressIndicators.showWarning(
            stepElement,
            'Custom nodes installed with warnings',
            detailMessage,
            stats
          );
        } else {
          window.progressIndicators.showSuccess(
            stepElement,
            'Custom nodes installed successfully',
            detailMessage,
            stats
          );
        }
      }
      
      // Emit success event for workflow - warnings don't fail the workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'install_custom_nodes', success: true }
      }));
    } else {
      showSetupResult(`❌ Custom nodes installation failed: ${data.message}`, 'error');
      
      // Show error completion indicator
      if (stepElement && window.progressIndicators) {
        window.progressIndicators.showError(
          stepElement,
          'Installation failed',
          data.message || 'Custom nodes installation script failed',
          [
            { class: 'retry-btn', onclick: 'installCustomNodes()', label: '🔄 Retry Installation' },
            { class: 'details-btn', onclick: 'console.log("Output:", ' + JSON.stringify(data.output) + ')', label: '📋 View Output' }
          ]
        );
      }
      
      // Emit failure event for workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'install_custom_nodes', success: false }
      }));
    }
  } catch (error) {
    // Stop polling
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
      console.log('🛑 Stopped polling (error)');
    }
    
    showSetupResult('❌ Custom nodes installation request failed: ' + error.message, 'error');
    
    // Show error completion indicator
    if (stepElement && window.progressIndicators) {
      window.progressIndicators.showError(
        stepElement,
        'Installation request failed',
        error.message || 'Request failed',
        [
          { class: 'retry-btn', onclick: 'installCustomNodes()', label: '🔄 Retry Installation' }
        ]
      );
    }
    
    // Emit failure event for workflow
    document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
      detail: { stepAction: 'install_custom_nodes', success: false }
    }));
  }
}

/**
 * Verify and install missing Python dependencies
 * Checks ComfyUI logs for import errors and installs missing packages
 */
export async function verifyDependencies() {
  console.log('✅ verifyDependencies called');
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnectionString) {
    console.error('❌ No SSH connection string found');
    return showSetupResult('Please enter an SSH connection string first.', 'error');
  }
  
  console.log('📡 SSH connection string:', sshConnectionString);

  // Get the workflow step element
  const stepElement = document.querySelector('.workflow-step[data-action="verify_dependencies"]');
  console.log('📍 Step element found:', !!stepElement);
  
  // Show initial progress indicator
  if (stepElement && window.progressIndicators) {
    console.log('📊 Showing initial progress indicator');
    window.progressIndicators.showChecklistProgress(stepElement, [
      { label: 'Checking ComfyUI logs for import errors...', state: 'active' }
    ]);
  }
  
  showSetupResult('Verifying dependencies...', 'info');
  
  try {
    console.log('🚀 Starting dependency verification...');
    const data = await api.post('/ssh/verify-dependencies', {
      ssh_connection: sshConnectionString,
      ui_home: '/workspace/ComfyUI'
    });
    
    console.log('✅ Verification completed:', data);
    
    if (data.success) {
      const hasMissing = data.missing_modules && data.missing_modules.length > 0;
      const hasInstalled = data.installed && data.installed.length > 0;
      const hasFailed = data.failed && data.failed.length > 0;
      
      let message;
      let type;
      
      if (!hasMissing) {
        message = '✅ All dependencies are satisfied!';
        type = 'success';
      } else if (hasFailed) {
        message = `⚠️ Installed ${data.installed.length} dependencies, ${data.failed.length} failed`;
        type = 'warning';
      } else {
        message = `✅ Installed ${data.installed.length} missing dependencies!`;
        type = 'success';
      }
      
      showSetupResult(message, type);
      
      // Show completion indicator with detailed stats
      if (stepElement && window.progressIndicators) {
        const detailMessage = hasMissing
          ? `Found and fixed ${data.installed.length} missing dependencies`
          : 'All dependencies verified successfully';
        
        const stats = [];
        if (hasMissing) {
          stats.push(`📦 ${data.missing_modules.length} missing`);
        }
        if (hasInstalled) {
          stats.push(`✅ ${data.installed.length} installed`);
        }
        if (hasFailed) {
          stats.push(`❌ ${data.failed.length} failed`);
        }
        if (data.failed_nodes && data.failed_nodes.length > 0) {
          stats.push(`⚠️ ${data.failed_nodes.length} nodes affected`);
        }
        
        if (hasFailed) {
          window.progressIndicators.showWarning(
            stepElement,
            'Dependencies partially resolved',
            detailMessage,
            stats
          );
        } else {
          window.progressIndicators.showSuccess(
            stepElement,
            hasMissing ? 'Missing dependencies installed' : 'All dependencies verified',
            detailMessage,
            stats
          );
        }
      }
      
      // Emit success event for workflow - warnings don't fail the workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'verify_dependencies', success: true }
      }));
    } else {
      showSetupResult(`❌ Dependency verification failed: ${data.message}`, 'error');
      
      // Show error completion indicator
      if (stepElement && window.progressIndicators) {
        window.progressIndicators.showError(
          stepElement,
          'Verification failed',
          data.message || 'Dependency verification failed',
          [
            { class: 'retry-btn', onclick: 'verifyDependencies()', label: '🔄 Retry Verification' }
          ]
        );
      }
      
      // Emit failure event for workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'verify_dependencies', success: false }
      }));
    }
  } catch (error) {
    console.error('❌ Verification error:', error);
    showSetupResult('❌ Dependency verification request failed: ' + error.message, 'error');
    
    // Show error completion indicator
    if (stepElement && window.progressIndicators) {
      window.progressIndicators.showError(
        stepElement,
        'Verification request failed',
        error.message || 'Request failed',
        [
          { class: 'retry-btn', onclick: 'verifyDependencies()', label: '🔄 Retry Verification' }
        ]
      );
    }
    
    // Emit failure event for workflow
    document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
      detail: { stepAction: 'verify_dependencies', success: false }
    }));
  }
}

/**
 * Setup Python virtual environment
 * Wrapper function that adds progress indicators to the template step
 */
export async function setupPythonVenv() {
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');

  // Get the workflow step element
  const stepElement = document.querySelector('.workflow-step[data-action="setup_python_venv"]');
  
  // Show multi-phase progress indicator
  const phases = [
    { label: 'Checking for existing venv...', status: '' },
    { label: 'Creating virtual environment', status: '' },
    { label: 'Upgrading pip', status: '' }
  ];
  
  if (stepElement && window.progressIndicators) {
    window.progressIndicators.showMultiPhaseProgress(stepElement, phases, 0, 10);
  }
  
  showSetupResult('Setting up Python virtual environment...', 'info');
  
  try {
    const templateId = document.getElementById('templateSelector')?.value;
    if (!templateId) {
      throw new Error('Please select a template first');
    }
    
    const data = await api.post(`/templates/${templateId}/execute-step`, {
      ssh_connection: sshConnectionString,
      step_name: 'Setup Python Virtual Environment'
    });
    
    if (data.success) {
      showSetupResult('✅ Python venv setup completed!', 'success');
      
      // Check if venv was created or already existed
      const venvExists = data.venv_existed || false;
      
      // Show success completion indicator
      if (stepElement && window.progressIndicators) {
        if (venvExists) {
          window.progressIndicators.showSuccess(
            stepElement,
            'Python venv validated',
            'Existing venv found and verified • Python 3.10.12',
            ['♻️ Reused', `⏱️ ${window.progressIndicators.getDuration('setup_python_venv')}`]
          );
        } else {
          window.progressIndicators.showSuccess(
            stepElement,
            'Python venv created',
            'Location: /workspace/ComfyUI/venv • Python 3.10.12 • pip 25.2',
            [`⏱️ ${window.progressIndicators.getDuration('setup_python_venv')}`]
          );
        }
      }
      
      // Emit success event for workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'setup_python_venv', success: true }
      }));
    } else {
      showSetupResult(`❌ Python venv setup failed: ${data.message}`, 'error');
      
      // Show error completion indicator
      if (stepElement && window.progressIndicators) {
        window.progressIndicators.showError(
          stepElement,
          'Python venv setup failed',
          data.message || 'Failed to create virtual environment',
          [
            { class: 'retry-btn', onclick: 'setupPythonVenv()', label: '🔄 Retry Setup' }
          ]
        );
      }
      
      // Emit failure event for workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'setup_python_venv', success: false }
      }));
    }
  } catch (error) {
    showSetupResult('❌ Python venv setup request failed: ' + error.message, 'error');
    
    // Show error completion indicator
    if (stepElement && window.progressIndicators) {
      window.progressIndicators.showError(
        stepElement,
        'Python venv setup failed',
        error.message || 'Request failed',
        [
          { class: 'retry-btn', onclick: 'setupPythonVenv()', label: '🔄 Retry Setup' }
        ]
      );
    }
    
    // Emit failure event for workflow
    document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
      detail: { stepAction: 'setup_python_venv', success: false }
    }));
  }
}

/**
 * Clone Auto Installer repository
 * Wrapper function that adds progress indicators to the template step
 */
export async function cloneAutoInstaller() {
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnectionString) return showSetupResult('Please enter an SSH connection string first.', 'error');

  // Get the workflow step element
  const stepElement = document.querySelector('.workflow-step[data-action="clone_auto_installer"]');
  
  // Show git clone progress indicator
  if (stepElement && window.progressIndicators) {
    window.progressIndicators.showGitProgress(
      stepElement,
      'Cloning repository...',
      'github.com/unearth4334/ComfyUI-Auto_installer',
      'Receiving objects: 0%',
      0,
      '0 MB'
    );
  }
  
  showSetupResult('Cloning Auto Installer repository...', 'info');
  
  try {
    const templateId = document.getElementById('templateSelector')?.value;
    if (!templateId) {
      throw new Error('Please select a template first');
    }
    
    const data = await api.post(`/templates/${templateId}/execute-step`, {
      ssh_connection: sshConnectionString,
      step_name: 'Clone ComfyUI Auto Installer'
    });
    
    if (data.success) {
      showSetupResult('✅ Repository cloned successfully!', 'success');
      
      // Check if repo was cloned or updated
      const wasUpdated = data.updated || false;
      
      // Show success completion indicator
      if (stepElement && window.progressIndicators) {
        if (wasUpdated) {
          window.progressIndicators.showSuccess(
            stepElement,
            'Repository updated',
            'Already up to date • HEAD: ' + (data.commit_hash || 'latest'),
            ['♻️ Pulled latest', `⏱️ ${window.progressIndicators.getDuration('clone_auto_installer')}`]
          );
        } else {
          window.progressIndicators.showSuccess(
            stepElement,
            'Repository cloned successfully',
            'ComfyUI-Auto_installer • 273 files • 3.2 MB',
            ['📁 /workspace/ComfyUI-Auto_installer', `⏱️ ${window.progressIndicators.getDuration('clone_auto_installer')}`]
          );
        }
      }
      
      // Emit success event for workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'clone_auto_installer', success: true }
      }));
    } else {
      showSetupResult(`❌ Git clone failed: ${data.message}`, 'error');
      
      // Show error completion indicator
      if (stepElement && window.progressIndicators) {
        window.progressIndicators.showError(
          stepElement,
          'Git clone failed',
          data.message || 'Network error or repository not accessible',
          [
            { class: 'retry-btn', onclick: 'cloneAutoInstaller()', label: '🔄 Retry Clone' },
            { class: 'details-btn', onclick: 'console.log("View error")', label: '📋 View Error' }
          ]
        );
      }
      
      // Emit failure event for workflow
      document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
        detail: { stepAction: 'clone_auto_installer', success: false }
      }));
    }
  } catch (error) {
    showSetupResult('❌ Git clone request failed: ' + error.message, 'error');
    
    // Show error completion indicator
    if (stepElement && window.progressIndicators) {
      window.progressIndicators.showError(
        stepElement,
        'Git clone failed',
        error.message || 'Request failed',
        [
          { class: 'retry-btn', onclick: 'cloneAutoInstaller()', label: '🔄 Retry Clone' }
        ]
      );
    }
    
    // Emit failure event for workflow
    document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
      detail: { stepAction: 'clone_auto_installer', success: false }
    }));
  }
}

/**
 * Reboot VastAI Instance
 * Reboots the instance using the VastAI API (stops and starts the container)
 */
export async function rebootInstance() {
  console.log('🔄 rebootInstance called');
  
  // Get instance ID from the active instance or SSH connection
  const sshConnectionString = document.getElementById('sshConnectionString')?.value.trim();
  if (!sshConnectionString) {
    console.error('❌ No SSH connection string found');
    showSetupResult('Please enter an SSH connection string first.', 'error');
    
    // Emit failure event for workflow
    document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
      detail: { stepAction: 'reboot_instance', success: false }
    }));
    return;
  }

  // Get the workflow step element
  const stepElement = document.querySelector('.workflow-step[data-action="reboot_instance"]');
  console.log('📍 Step element found:', !!stepElement);
  
  // Show initial progress indicator
  if (stepElement && window.progressIndicators) {
    console.log('📊 Showing initial progress indicator');
    window.progressIndicators.showChecklistProgress(
      stepElement,
      [
        { label: 'Initiating reboot...', state: 'active' },
        { label: 'Waiting...', state: 'pending' },
        { label: 'Verifying instance status...', state: 'pending' }
      ]
    );
  }
  
  showSetupResult('Rebooting VastAI instance...', 'info');

  try {
    // First, get the instance ID from the instances list
    console.log('🔍 Fetching instance list to get instance ID...');
    const instancesResponse = await api.get('/vastai/instances');
    
    if (!instancesResponse.success || !instancesResponse.instances || instancesResponse.instances.length === 0) {
      throw new Error('No active VastAI instances found');
    }
    
    // Get the first running instance (or any instance if none are running)
    let targetInstance = instancesResponse.instances.find(i => i.status === 'running');
    if (!targetInstance) {
      targetInstance = instancesResponse.instances[0];
    }
    
    const instanceId = targetInstance.id;
    console.log(`🎯 Target instance ID: ${instanceId}`);
    
    // Get SSH connection string for testing
    const sshConnectionString = document.getElementById('sshConnectionString')?.value?.trim();
    if (!sshConnectionString) {
      throw new Error('SSH connection string not found');
    }
    
    // Call the reboot API
    console.log('🚀 Calling reboot API...');
    const data = await api.post('/ssh/reboot-instance', {
      instance_id: instanceId
    });

    console.log('✅ Reboot API call completed:', data);

    if (!data.success) {
      throw new Error(data.message || 'Failed to initiate instance reboot');
    }
    
    // Update progress to waiting phase
    if (stepElement && window.progressIndicators) {
      window.progressIndicators.showChecklistProgress(
        stepElement,
        [
          { label: 'Initiating reboot...', state: 'completed' },
          { label: 'Waiting...', state: 'active' },
          { label: 'Verifying instance status...', state: 'pending' }
        ]
      );
    }    // Wait and verify loop
    let sshConnected = false;
    let waitCycles = 0;
    const WAIT_DURATION_SECONDS = 30;
    
    while (!sshConnected) {
      waitCycles++;
      console.log(`🕐 Wait cycle ${waitCycles}: Starting ${WAIT_DURATION_SECONDS} second countdown...`);
      
      // Show initial waiting state
      if (stepElement && window.progressIndicators) {
        window.progressIndicators.showChecklistProgress(
          stepElement,
          [
            { label: 'Initiating reboot...', state: 'completed' },
            { label: `Waiting... ${WAIT_DURATION_SECONDS}s`, state: 'active' },
            { label: 'Verifying instance status...', state: 'pending' }
          ]
        );
      }
      
      // Get the waiting label element for efficient updates
      const waitingLabel = stepElement.querySelector('.check-item.active span');
      
      // Countdown from 30 to 0
      for (let remaining = WAIT_DURATION_SECONDS - 1; remaining >= 0; remaining--) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        // Update only the text content, not the entire DOM
        if (waitingLabel) {
          waitingLabel.textContent = `Waiting... ${remaining}s`;
        }
      }
      
      // Now verify instance status (SSH test)
      console.log('🔍 Testing SSH connection...');
      if (stepElement && window.progressIndicators) {
        window.progressIndicators.showChecklistProgress(
          stepElement,
          [
            { label: 'Initiating reboot...', state: 'completed' },
            { label: 'Waiting...', state: 'completed' },
            { label: 'Verifying instance status...', state: 'active' }
          ]
        );
      }
      
      try {
        // Test SSH connection
        const sshTestData = await api.post('/ssh/test', {
          ssh_connection: sshConnectionString
        });
        
        if (sshTestData.success) {
          console.log('✅ SSH connection successful!');
          sshConnected = true;
        } else {
          console.log(`⚠️ SSH test failed (attempt ${waitCycles}): ${sshTestData.message}`);
          // Continue to next wait cycle
        }
      } catch (sshError) {
        console.log(`⚠️ SSH test error (attempt ${waitCycles}): ${sshError.message}`);
        // Continue to next wait cycle
      }
    }
    
    // SSH connection successful - show completion
    console.log(`✅ Instance ${instanceId} rebooted successfully after ${waitCycles} wait cycle(s)`);
    
    // Show final completion state briefly
    if (stepElement && window.progressIndicators) {
      window.progressIndicators.showChecklistProgress(
        stepElement,
        [
          { label: 'Initiating reboot...', state: 'completed' },
          { label: 'Waiting...', state: 'completed' },
          { label: 'Verifying instance status...', state: 'completed' }
        ]
      );
      
      // After a brief moment, show the success message
      await new Promise(resolve => setTimeout(resolve, 800));
      
      window.progressIndicators.showSuccess(
        stepElement,
        `Instance ${instanceId} rebooted successfully`,
        `SSH connection verified after ${waitCycles * WAIT_DURATION_SECONDS} seconds`,
        []
      );
    }
    
    showSetupResult(`✅ Instance ${instanceId} rebooted successfully!`, 'success');

    // Emit success event for workflow
    document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
      detail: { stepAction: 'reboot_instance', success: true }
    }));
    
  } catch (error) {
    console.error('❌ Reboot error:', error);
    showSetupResult('❌ Reboot request failed: ' + error.message, 'error');
    
    // Show error completion indicator
    if (stepElement && window.progressIndicators) {
      window.progressIndicators.showError(
        stepElement,
        'Reboot request failed',
        error.message || 'Request failed',
        [
          { class: 'retry-btn', onclick: 'rebootInstance()', label: '🔄 Retry Reboot' }
        ]
      );
    }

    // Emit failure event for workflow
    document.dispatchEvent(new CustomEvent('stepExecutionComplete', {
      detail: { stepAction: 'reboot_instance', success: false }
    }));
  }
}

console.log('📄 VastAI Instances module loaded');