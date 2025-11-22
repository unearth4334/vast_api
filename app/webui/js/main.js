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
});

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

// ============================================================================
// ComfyUI Workflow Functions
// ============================================================================

/**
 * Execute ComfyUI workflow
 */
async function executeComfyUIWorkflow() {
    const sshConnection = document.getElementById('comfyuiSshConnection').value.trim();
    const workflowFile = document.getElementById('comfyuiWorkflowFile').value.trim();
    const workflowName = document.getElementById('comfyuiWorkflowName').value.trim();
    const inputImagesText = document.getElementById('comfyuiInputImages').value.trim();
    const outputDir = document.getElementById('comfyuiOutputDir').value.trim();

    // Validate required fields
    if (!sshConnection) {
        showSetupResult('❌ Please enter an SSH connection string', 'error');
        return;
    }

    if (!workflowFile) {
        showSetupResult('❌ Please enter a workflow file path', 'error');
        return;
    }

    // Parse input images (one per line)
    const inputImages = inputImagesText
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0);

    const stepElement = document.getElementById('comfyui-workflow-step');
    const executeBtn = document.getElementById('execute-comfyui-workflow-btn');
    const cancelBtn = document.getElementById('cancel-comfyui-workflow-btn');

    try {
        // Disable execute button, show cancel button
        executeBtn.disabled = true;
        cancelBtn.style.display = 'inline-block';

        showSetupResult('🚀 Starting workflow execution...', 'info');

        // Execute workflow
        const workflowId = await window.comfyuiWorkflowManager.executeWorkflow(
            sshConnection,
            workflowFile,
            workflowName || null,
            inputImages,
            outputDir || '/tmp/comfyui_outputs'
        );

        showSetupResult(`✅ Workflow started: ${workflowId}`, 'success');

        // Start progress monitoring
        window.comfyuiWorkflowManager.startProgressPolling(
            workflowId,
            (progress) => {
                // Update progress UI
                window.comfyuiWorkflowManager.updateProgressUI(stepElement, progress);
            },
            async (progress) => {
                // Workflow completed
                window.comfyuiWorkflowManager.updateProgressUI(stepElement, progress);
                await handleComfyUIWorkflowComplete(progress);
                
                // Re-enable execute button, hide cancel button
                executeBtn.disabled = false;
                cancelBtn.style.display = 'none';
            },
            (progress) => {
                // Workflow error
                window.comfyuiWorkflowManager.updateProgressUI(stepElement, progress);
                handleComfyUIWorkflowError(progress);
                
                // Re-enable execute button, hide cancel button
                executeBtn.disabled = false;
                cancelBtn.style.display = 'none';
            }
        );

    } catch (error) {
        console.error('Failed to execute workflow:', error);
        showSetupResult(`❌ Failed to execute workflow: ${error.message}`, 'error');
        
        // Re-enable execute button, hide cancel button
        executeBtn.disabled = false;
        cancelBtn.style.display = 'none';
    }
}

/**
 * Cancel ComfyUI workflow
 */
async function cancelComfyUIWorkflow() {
    if (!window.comfyuiWorkflowManager.currentWorkflowId) {
        showSetupResult('❌ No workflow is currently running', 'error');
        return;
    }

    if (!confirm('Are you sure you want to cancel the running workflow?')) {
        return;
    }

    try {
        showSetupResult('⏹️ Cancelling workflow...', 'info');

        await window.comfyuiWorkflowManager.cancelWorkflow(
            window.comfyuiWorkflowManager.currentWorkflowId
        );

        showSetupResult('✅ Workflow cancellation requested', 'success');

        // Stop polling
        window.comfyuiWorkflowManager.stopProgressPolling();

        // Re-enable execute button, hide cancel button
        document.getElementById('execute-comfyui-workflow-btn').disabled = false;
        document.getElementById('cancel-comfyui-workflow-btn').style.display = 'none';

    } catch (error) {
        console.error('Failed to cancel workflow:', error);
        showSetupResult(`❌ Failed to cancel workflow: ${error.message}`, 'error');
    }
}

/**
 * Handle workflow completion
 */
async function handleComfyUIWorkflowComplete(progress) {
    console.log('Workflow completed:', progress);

    try {
        // Get outputs
        const outputs = await window.comfyuiWorkflowManager.getOutputs(progress.workflow_id);

        if (outputs.length > 0) {
            // Show outputs section
            const outputsSection = document.getElementById('comfyui-outputs-section');
            const outputsList = document.getElementById('comfyui-outputs-list');

            outputsSection.style.display = 'block';
            outputsList.innerHTML = '';

            // Display each output
            outputs.forEach(output => {
                const outputItem = document.createElement('div');
                outputItem.className = 'output-item';
                
                const statusIcon = output.downloaded ? '✅' : '⏳';
                const statusText = output.downloaded ? 'Downloaded' : 'Pending';
                
                outputItem.innerHTML = `
                    <div class="output-info">
                        <div class="output-filename">${statusIcon} ${escapeHtml(output.filename)}</div>
                        <div class="output-details">
                            <span>Type: ${escapeHtml(output.file_type)}</span>
                            ${output.downloaded ? `<span>Path: ${escapeHtml(output.local_path)}</span>` : ''}
                            <span>Status: ${statusText}</span>
                        </div>
                    </div>
                `;
                
                outputsList.appendChild(outputItem);
            });

            const downloadedCount = outputs.filter(o => o.downloaded).length;
            showSetupResult(
                `✅ Workflow completed! Downloaded ${downloadedCount}/${outputs.length} output(s)`,
                'success'
            );
        } else {
            showSetupResult('✅ Workflow completed (no outputs generated)', 'success');
        }

    } catch (error) {
        console.error('Failed to get outputs:', error);
        showSetupResult('⚠️ Workflow completed but failed to retrieve outputs', 'warning');
    }
}

/**
 * Handle workflow error
 */
function handleComfyUIWorkflowError(progress) {
    console.error('Workflow error:', progress);

    const errorMsg = progress.error_message || progress.error || 'Workflow execution failed';
    const failedNode = progress.failed_node ? ` (failed at node: ${progress.failed_node})` : '';
    
    showSetupResult(`❌ ${errorMsg}${failedNode}`, 'error');
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
