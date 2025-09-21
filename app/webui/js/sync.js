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