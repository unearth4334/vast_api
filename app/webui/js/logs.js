// Logs functionality - recent logs list and log modal

async function refreshLogs() {
    const logsList = document.getElementById('logsList');
    const refreshBtn = document.querySelector('.refresh-logs-btn');
    
    // Show loading state
    refreshBtn.textContent = '⟳ Loading...';
    refreshBtn.disabled = true;
    logsList.innerHTML = '<div class="no-logs-message">Loading logs...</div>';
    
    try {
        const data = await api.get('/logs/manifest');
        
        if (data.success && data.logs && data.logs.length > 0) {
            // Get latest 5 logs
            const recentLogs = data.logs.slice(0, 5);
            displayLogs(recentLogs);
        } else {
            logsList.innerHTML = '<div class="no-logs-message">No logs available</div>';
        }
    } catch (error) {
        logsList.innerHTML = '<div class="no-logs-message">Failed to load logs: ' + error.message + '</div>';
    } finally {
        refreshBtn.textContent = '🔄 Refresh';
        refreshBtn.disabled = false;
    }
}

function displayLogs(logs) {
    const logsList = document.getElementById('logsList');
    logsList.innerHTML = '';
    
    logs.forEach(log => {
        const logItem = document.createElement('div');
        logItem.className = `log-item ${log.success ? 'success' : 'error'}`;
        logItem.onclick = () => showLogDetails(log.filename);
        
        // Format timestamp
        const date = new Date(log.timestamp);
        const formattedDate = date.toLocaleDateString('en-US', { 
            month: '2-digit', 
            day: '2-digit', 
            year: 'numeric' 
        });
        const formattedTime = date.toLocaleTimeString('en-US', { 
            hour12: false,
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
        });
        
        // Format duration
        const duration = log.duration_seconds ? `(${log.duration_seconds}s)` : '';
        
        // Create log summary in the requested format
        const statusIcon = log.success ? '✅' : '❌';
        const syncType = log.sync_type ? log.sync_type.charAt(0).toUpperCase() + log.sync_type.slice(1) : 'Unknown';
        
        logItem.innerHTML = `
            <div class="log-summary">
                ${statusIcon} ${syncType} - ${formattedDate}, ${formattedTime}<br>
                ${log.message} ${duration}
            </div>
            <div class="log-meta">Click to view details</div>
        `;
        
        logsList.appendChild(logItem);
    });
}

async function showLogDetails(filename) {
    const overlay = document.getElementById('logOverlay');
    const modalTitle = document.getElementById('logModalTitle');
    const modalContent = document.getElementById('logModalContent');
    
    // Show loading state
    modalTitle.textContent = 'Loading log details...';
    modalContent.innerHTML = '<div class="no-logs-message">Loading...</div>';
    overlay.style.display = 'flex';
    
    try {
        const data = await api.get(`/logs/${filename}`);
        
        if (data.success && data.log) {
            const log = data.log;
            
            // Update modal title
            const syncType = log.sync_type ? log.sync_type.charAt(0).toUpperCase() + log.sync_type.slice(1) : 'Unknown';
            const date = new Date(log.timestamp);
            const formattedDateTime = date.toLocaleString('en-US');
            modalTitle.textContent = `${syncType} Sync - ${formattedDateTime}`;
            
            // Build modal content
            let content = '';
            
            // Basic info section
            content += '<div class="log-detail-section">';
            content += '<h4>Summary</h4>';
            content += '<div class="log-detail-content">';
            content += `Status: ${log.success ? '✅ Success' : '❌ Failed'}\n`;
            content += `Type: ${syncType}\n`;
            content += `Message: ${log.message}\n`;
            if (log.duration_seconds) {
                content += `Duration: ${log.duration_seconds} seconds\n`;
            }
            if (log.sync_id) {
                content += `Sync ID: ${log.sync_id}\n`;
            }
            content += '</div>';
            content += '</div>';
            
            // Output section (scrollable callout as requested)
            if (log.output) {
                content += '<div class="log-detail-section">';
                content += '<h4>Output</h4>';
                content += '<div class="log-detail-content">';
                content += log.output;
                content += '</div>';
                content += '</div>';
            }
            
            // Error section if there's an error
            if (log.error) {
                content += '<div class="log-detail-section">';
                content += '<h4>Error</h4>';
                content += '<div class="log-detail-content">';
                content += log.error;
                content += '</div>';
                content += '</div>';
            }
            
            modalContent.innerHTML = content;
        } else {
            modalTitle.textContent = 'Error';
            modalContent.innerHTML = '<div class="no-logs-message">Failed to load log details</div>';
        }
    } catch (error) {
        modalTitle.textContent = 'Error';
        modalContent.innerHTML = '<div class="no-logs-message">Failed to load log details: ' + error.message + '</div>';
    }
}

function closeLogModal() {
    const overlay = document.getElementById('logOverlay');
    overlay.style.display = 'none';
}

// VastAI Logs functionality

function getActionLabel(log) {
    // Get user-friendly action labels based on log data
    if (log.operation) {
        switch (log.operation) {
            case 'test_ssh_start':
                return '🔍 Testing SSH Connection';
            case 'test_ssh_success':
                return '✅ SSH Connection Test';
            case 'get_ui_home_start':
                return '📖 Reading UI_HOME';
            case 'get_ui_home_success':
                return '✅ UI_HOME Retrieved';
            case 'terminate_vastai':
                return '🛑 Terminating Instance';
            case 'create_instance':
                return '🚀 Creating Instance';
            case 'list_instances':
                return '📋 Listing Instances';
            case 'show_instance':
                return '👁️ Viewing Instance';
            case 'template_execution_start':
                return '⚙️ Running Template';
            case 'template_execution_complete':
                return '✅ Template Complete';
            default:
                return `🔧 ${log.operation.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}`;
        }
    } else if (log.method && log.endpoint) {
        // Fallback for older API logs
        return `${log.method} ${log.endpoint.replace('/api/v0', '')}`;
    } else if (log.category) {
        return `📊 ${log.category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}`;
    }
    return '📝 VastAI Operation';
}

async function refreshVastAILogs() {
    const logsList = document.getElementById('vastai-logs-list');
    const refreshBtn = document.querySelector('.vastai-logs-section .setup-button');
    const linesInput = document.getElementById('vastaiLogLines');
    
    // Show loading state
    refreshBtn.textContent = '⟳ Loading...';
    refreshBtn.disabled = true;
    logsList.innerHTML = '<div class="no-logs-message">Loading VastAI logs...</div>';
    
    try {
        const maxLines = parseInt(linesInput.value) || 50;
        const data = await api.get(`/vastai/logs?lines=${maxLines}`);
        
        if (data.success && data.logs && data.logs.length > 0) {
            displayVastAILogs(data.logs);
        } else {
            logsList.innerHTML = '<div class="no-logs-message">No VastAI API logs available</div>';
        }
    } catch (error) {
        logsList.innerHTML = '<div class="no-logs-message">Failed to load VastAI logs: ' + error.message + '</div>';
    } finally {
        refreshBtn.textContent = '🔄 Refresh';
        refreshBtn.disabled = false;
    }
}

function displayVastAILogs(logs) {
    const logsList = document.getElementById('vastai-logs-list');
    logsList.innerHTML = '';
    
    logs.forEach(log => {
        const logItem = document.createElement('div');
        logItem.className = `log-item ${log.error ? 'error' : 'success'}`;
        logItem.onclick = () => showVastAILogDetails(log);
        
        // Format timestamp
        const date = new Date(log.timestamp);
        const formattedDate = date.toLocaleDateString('en-US', { 
            month: '2-digit', 
            day: '2-digit', 
            year: 'numeric' 
        });
        const formattedTime = date.toLocaleTimeString('en-US', { 
            hour12: false,
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
        });
        
        // Format duration
        const duration = log.duration_ms ? `(${Math.round(log.duration_ms)}ms)` : '';
        
        // Create log summary with informative action label
        const actionLabel = getActionLabel(log);
        const statusIcon = log.level === 'ERROR' || log.error ? '❌' : '✅';
        const statusText = log.level === 'ERROR' || log.error ? 'Failed' : 'Success';
        
        // Extract meaningful message from log
        let displayMessage = '';
        if (log.message) {
            // Clean up common prefixes for better readability
            displayMessage = log.message
                .replace(/^✅\s*/, '')
                .replace(/^❌\s*/, '')
                .replace(/^Operation - \w+:\s*/, '')
                .replace(/^API - /, '')
                .replace(/^Performance - \w+:\s*/, '');
        } else if (log.error) {
            displayMessage = log.error;
        } else {
            displayMessage = statusText;
        }
        
        logItem.innerHTML = `
            <div class="log-summary">
                ${actionLabel} - ${formattedDate}, ${formattedTime}<br>
                <span class="log-status-${statusText.toLowerCase()}">${statusIcon} ${displayMessage}</span> ${duration}
            </div>
            <div class="log-meta">Click to view details</div>
        `;
        
        logsList.appendChild(logItem);
    });
}

function showVastAILogDetails(log) {
    const overlay = document.getElementById('logOverlay');
    const modalTitle = document.getElementById('logModalTitle');
    const modalContent = document.getElementById('logModalContent');
    
    // Show modal
    const date = new Date(log.timestamp);
    const formattedDateTime = date.toLocaleString('en-US');
    modalTitle.textContent = `VastAI API Call - ${formattedDateTime}`;
    
    // Build modal content
    let content = '';
    
    // Basic info section
    content += '<div class="log-detail-section">';
    content += '<h4>Request Details</h4>';
    content += '<div class="log-detail-content">';
    content += `Method: ${log.method || 'Unknown'}\n`;
    content += `Endpoint: ${log.endpoint || 'Unknown'}\n`;
    content += `Status Code: ${log.status_code || 'N/A'}\n`;
    if (log.duration_ms) {
        content += `Duration: ${Math.round(log.duration_ms)}ms\n`;
    }
    content += '</div>';
    content += '</div>';
    
    // Request data section
    if (log.request) {
        content += '<div class="log-detail-section">';
        content += '<h4>Request Data</h4>';
        content += '<div class="log-detail-content">';
        content += JSON.stringify(log.request, null, 2);
        content += '</div>';
        content += '</div>';
    }
    
    // Response data section
    if (log.response) {
        content += '<div class="log-detail-section">';
        content += '<h4>Response Data</h4>';
        content += '<div class="log-detail-content">';
        content += JSON.stringify(log.response, null, 2);
        content += '</div>';
        content += '</div>';
    }
    
    // Error section if there's an error
    if (log.error) {
        content += '<div class="log-detail-section">';
        content += '<h4>Error</h4>';
        content += '<div class="log-detail-content">';
        content += log.error;
        content += '</div>';
        content += '</div>';
    }
    
    modalContent.innerHTML = content;
    overlay.style.display = 'flex';
}