// Resource Download Status UI
// Polls /downloads/status and renders download queue/progress for the selected instance
// Similar to custom nodes installer tasklist visualization pattern

export class ResourceDownloadStatus {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.instanceId = null;
        this.pollInterval = null;
        this.isPolling = false;
        this.deleteMode = false;
        this.setupEventListeners();
    }

    /**
     * Setup global event listeners for delete mode
     */
    setupEventListeners() {
        // Listen for clicks anywhere to exit delete mode
        document.addEventListener('click', (e) => {
            if (!this.deleteMode) return;
            
            // Don't exit if clicking delete buttons or task items
            if (e.target.closest('.download-task-delete-btn') || 
                e.target.closest('.download-delete-all-btn')) {
                return;
            }
            
            // Don't exit if clicking a task item to enter delete mode
            if (e.target.closest('.download-task-item') && !this.deleteMode) {
                return;
            }
            
            // Exit delete mode
            this.exitDeleteMode();
        });
    }

    /**
     * Enter delete mode - show delete buttons
     */
    enterDeleteMode() {
        if (!this.container) return;
        this.deleteMode = true;
        
        const wrappers = this.container.querySelectorAll('.download-task-item-wrapper');
        wrappers.forEach(wrapper => wrapper.classList.add('delete-mode'));
        
        const deleteAllBtn = this.container.querySelector('.download-delete-all-btn');
        if (deleteAllBtn) {
            deleteAllBtn.classList.add('visible');
        }
    }

    /**
     * Exit delete mode - hide delete buttons
     */
    exitDeleteMode() {
        if (!this.container) return;
        this.deleteMode = false;
        
        const wrappers = this.container.querySelectorAll('.download-task-item-wrapper');
        wrappers.forEach(wrapper => wrapper.classList.remove('delete-mode'));
        
        const deleteAllBtn = this.container.querySelector('.download-delete-all-btn');
        if (deleteAllBtn) {
            deleteAllBtn.classList.remove('visible');
        }
    }

    /**
     * Handle task item click
     */
    handleTaskItemClick(e) {
        // Don't toggle if clicking delete button
        if (e.target.closest('.download-task-delete-btn')) {
            return;
        }
        
        e.stopPropagation();
        
        if (this.deleteMode) {
            // If already in delete mode and clicking task, exit
            this.exitDeleteMode();
        } else {
            // Enter delete mode
            this.enterDeleteMode();
        }
    }

    /**
     * Delete a single task
     */
    async deleteTask(jobId) {
        try {
            await window.api.delete(`/downloads/job/${jobId}`);
            // Refresh the list
            await this.pollStatus();
            // Stay in delete mode
        } catch (e) {
            console.error('Error deleting task:', e);
            alert('Failed to delete task');
        }
    }

    /**
     * Delete all tasks
     */
    async deleteAllTasks() {
        if (!this.instanceId) return;
        
        const confirmed = confirm('Delete all download tasks for this instance?');
        if (!confirmed) return;
        
        try {
            const jobs = await window.api.get(`/downloads/status?instance_id=${this.instanceId}`);
            
            // Delete each job
            for (const job of jobs) {
                await window.api.delete(`/downloads/job/${job.id}`);
            }
            
            // Refresh and exit delete mode
            await this.pollStatus();
            this.exitDeleteMode();
        } catch (e) {
            console.error('Error deleting all tasks:', e);
            alert('Failed to delete all tasks');
        }
    }

    /**
     * Set the instance ID and start polling
     */
    setInstanceId(instanceId) {
        this.instanceId = instanceId;
        this.startPolling();
    }

    /**
     * Start polling for status updates every 2 seconds
     */
    startPolling() {
        if (this.pollInterval) clearInterval(this.pollInterval);
        this.isPolling = true;
        this.pollInterval = setInterval(() => this.pollStatus(), 2000);
        // Poll immediately on start
        this.pollStatus();
    }

    /**
     * Stop polling for status updates
     */
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        this.isPolling = false;
    }

    /**
     * Poll the status endpoint for download progress
     */
    async pollStatus() {
        if (!this.instanceId || !this.container) return;
        try {
            const jobs = await window.api.get(`/downloads/status?instance_id=${this.instanceId}`);
            
            // Check for host verification needed
            const hostVerificationJob = jobs && jobs.find(j => j.status === 'HOST_VERIFICATION_NEEDED');
            if (hostVerificationJob) {
                // Show host verification modal
                await this.handleHostVerification(hostVerificationJob);
            }
            
            this.render(jobs);
            
            // If no jobs are in progress, we can slow down polling
            const hasActiveJobs = jobs && jobs.some(j => j.status === 'PENDING' || j.status === 'RUNNING');
            if (!hasActiveJobs && this.isPolling) {
                // Keep polling but at a slower rate when no active jobs
                // This ensures we still catch new jobs being added
            }
        } catch (e) {
            console.error('Error polling download status:', e);
            if (this.container) {
                this.container.innerHTML = '<div class="download-error">Failed to load download status</div>';
            }
        }
    }

    /**
     * Handle host key verification needed
     */
    async handleHostVerification(job) {
        // Only show modal once per job
        if (this._verificationShownForJob === job.id) {
            return;
        }
        this._verificationShownForJob = job.id;
        
        try {
            // Import the UI module for the verification modal
            const VastAIUI = await import('./vastai/ui.js');
            
            // First, get the host key fingerprints
            const ssh_connection = job.ssh_connection || `ssh -p ${job.port} root@${job.host}`;
            const verifyData = await window.api.post('/ssh/verify-host', {
                ssh_connection: ssh_connection,
                accept: false
            });
            
            if (verifyData.success && verifyData.needs_confirmation) {
                // Show modal to user
                const userAccepted = await VastAIUI.showSSHHostVerificationModal({
                    host: verifyData.host,
                    port: verifyData.port,
                    fingerprints: verifyData.fingerprints
                });
                
                if (userAccepted) {
                    // User accepted - add host key to known_hosts
                    const addKeyData = await window.api.post('/ssh/verify-host', {
                        ssh_connection: ssh_connection,
                        accept: true
                    });
                    
                    if (addKeyData.success) {
                        // Reset the job status to PENDING so it will be retried
                        // This is done by updating the queue
                        await window.api.post('/downloads/retry', {
                            job_id: job.id
                        });
                        
                        // Reset the flag so we can show again if needed
                        this._verificationShownForJob = null;
                    } else {
                        alert('Failed to add host key. Please try again.');
                        this._verificationShownForJob = null;
                    }
                } else {
                    // User rejected - mark job as failed
                    this._verificationShownForJob = null;
                }
            }
        } catch (error) {
            console.error('Error handling host verification:', error);
            this._verificationShownForJob = null;
        }
    }

    /**
     * Render the download status list (tasklist format with status tags)
     */
    render(jobs) {
        if (!this.container) return;
        
        if (!jobs || jobs.length === 0) {
            this.container.innerHTML = `
                <div class="download-tasklist-empty">
                    <span class="empty-icon">📭</span>
                    <span class="empty-text">No downloads queued for this instance.</span>
                </div>`;
            return;
        }

        // Group jobs by status for summary
        const pending = jobs.filter(j => j.status === 'PENDING');
        const running = jobs.filter(j => j.status === 'RUNNING');
        const complete = jobs.filter(j => j.status === 'COMPLETE');
        const failed = jobs.filter(j => j.status === 'FAILED');
        const hostVerification = jobs.filter(j => j.status === 'HOST_VERIFICATION_NEEDED');

        // Build the tasklist HTML
        let html = '<div class="download-tasklist">';
        // Summary header
        html += `
            <div class="download-summary">
                <span class="summary-item summary-total">${jobs.length} total</span>
                ${pending.length > 0 ? `<span class="summary-item summary-pending">${pending.length} queued</span>` : ''}
                ${running.length > 0 ? `<span class="summary-item summary-running">${running.length} in progress</span>` : ''}
                ${complete.length > 0 ? `<span class="summary-item summary-complete">${complete.length} complete</span>` : ''}
                ${failed.length > 0 ? `<span class="summary-item summary-failed">${failed.length} failed</span>` : ''}
                ${hostVerification.length > 0 ? `<span class="summary-item summary-host-verification">${hostVerification.length} needs verification</span>` : ''}
            </div>
        `;

        // Render each job as a task item
        html += '<div class="download-task-list">';
        html += '<button class="download-delete-all-btn">🗑️ Delete All</button>';
        jobs.forEach(job => {
            html += this.renderTaskItem(job);
        });
        html += '</div>';
        
        html += '</div>';
        
        this.container.innerHTML = html;
        
        // Attach event listeners
        this.attachEventListeners();
    }

    /**
     * Attach event listeners to task items and buttons
     */
    attachEventListeners() {
        if (!this.container) return;
        
        // Task item clicks
        const taskItems = this.container.querySelectorAll('.download-task-item');
        taskItems.forEach(item => {
            item.addEventListener('click', (e) => this.handleTaskItemClick(e));
        });
        
        // Delete button clicks
        const deleteButtons = this.container.querySelectorAll('.download-task-delete-btn');
        deleteButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const jobId = btn.dataset.jobId;
                if (jobId) {
                    this.deleteTask(jobId);
                }
            });
        });
        
        // Delete all button click
        const deleteAllBtn = this.container.querySelector('.download-delete-all-btn');
        if (deleteAllBtn) {
            deleteAllBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteAllTasks();
            });
        }
    }

    /**
     * Render a single download task item with status tag on the right
     */
    renderTaskItem(job) {
        const statusClass = job.status.toLowerCase();
        const statusIcon = this.getStatusIcon(job.status);
        const statusTag = this.getStatusTag(job);
        
        // Extract resource name from resource_paths or commands
        const resourceName = this.extractResourceName(job);
        
        // Progress bar for running jobs
        let progressBar = '';
        if (job.status === 'RUNNING' && job.progress && typeof job.progress.percent === 'number') {
            const percent = job.progress.percent;
            progressBar = `
                <div class="task-progress-bar">
                    <div class="task-progress-fill" style="width: ${percent}%;"></div>
                </div>
            `;
        }
        
        // Progress details
        let progressDetails = '';
        if (job.status === 'RUNNING') {
            const parts = [];
            
            // Show progress stats if available
            if (job.progress) {
                if (job.progress.percent !== undefined) {
                    parts.push(`${job.progress.percent}%`);
                }
                if (job.progress.speed) {
                    parts.push(job.progress.speed);
                }
                if (job.progress.stage) {
                    parts.push(job.progress.stage);
                }
                if (job.progress.name) {
                    parts.push(`"${job.progress.name}"`);
                }
                if (job.progress.downloaded) {
                    parts.push(job.progress.downloaded);
                }
                if (job.progress.eta) {
                    parts.push(`ETA: ${job.progress.eta}`);
                }
            }
            
            // Show command progress if no detailed stats
            if (parts.length === 0 && job.command_index && job.total_commands) {
                parts.push(`Command ${job.command_index}/${job.total_commands}`);
            }
            
            if (parts.length > 0) {
                progressDetails = `<div class="task-progress-details">${parts.join(' • ')}</div>`;
            }
        }
        
        // Error message for failed jobs
        let errorMsg = '';
        if (job.status === 'FAILED' && job.error) {
            errorMsg = `<div class="task-error-msg">${this.escapeHtml(job.error)}</div>`;
        } else if (job.status === 'HOST_VERIFICATION_NEEDED' && job.error) {
            errorMsg = `<div class="task-error-msg task-verify-msg">🔐 ${this.escapeHtml(job.error)}</div>`;
        }

        return `
            <div class="download-task-item-wrapper">
                <div class="download-task-item ${statusClass}" data-job-id="${job.id}">
                    <div class="task-main-row">
                        <span class="task-icon">${statusIcon}</span>
                        <span class="task-name">${this.escapeHtml(resourceName)}</span>
                        <span class="task-status-tag ${statusClass}">${statusTag}</span>
                    </div>
                    ${progressBar}
                    ${progressDetails}
                    ${errorMsg}
                </div>
                <button class="download-task-delete-btn" data-job-id="${job.id}">🗑️</button>
            </div>
        `;
    }

    /**
     * Get status icon based on job status
     */
    getStatusIcon(status) {
        switch (status) {
            case 'PENDING': return '⏳';
            case 'RUNNING': return '⬇️';
            case 'COMPLETE': return '✅';
            case 'FAILED': return '❌';
            case 'HOST_VERIFICATION_NEEDED': return '🔐';
            default: return '❓';
        }
    }
    /**
     * Get status tag text and any additional info
     */
    getStatusTag(job) {
        switch (job.status) {
            case 'PENDING':
                return 'Queued';
            case 'RUNNING':
                if (job.progress && job.progress.percent !== undefined) {
                    return `${job.progress.percent}%`;
                }
                // Show command progress if available
                if (job.command_index && job.total_commands) {
                    return `${job.command_index}/${job.total_commands}`;
                }
                return 'Downloading...';
            case 'COMPLETE':
                return 'Complete';
            case 'FAILED':
                return 'Failed';
            case 'HOST_VERIFICATION_NEEDED':
                return 'Verify Host';
            default:
                return job.status;
        }
    }

    /**
     * Extract a human-readable resource name from job data
     */
    extractResourceName(job) {
        // Try resource_paths first
        if (job.resource_paths && job.resource_paths.length > 0) {
            const path = job.resource_paths[0];
            // Handle both string paths and object with filepath
            const filepath = typeof path === 'object' ? path.filepath : path;
            if (filepath) {
                // Extract filename from path, e.g., "loras/my_lora.md" -> "my_lora"
                const filename = filepath.split('/').pop();
                return filename.replace('.md', '').replace(/_/g, ' ');
            }
        }
        
        // Try to extract from commands
        if (job.commands && job.commands.length > 0) {
            const cmd = job.commands[0];
            // Try to extract model name from civitdl command
            const civitMatch = cmd.match(/civitdl\s+"([^"]+)"/i);
            if (civitMatch) {
                // Extract model ID from URL
                const urlMatch = civitMatch[1].match(/models\/(\d+)/);
                if (urlMatch) {
                    return `Civitai Model ${urlMatch[1]}`;
                }
                return 'Civitai Download';
            }
            // Try to extract filename from wget command
            const wgetMatch = cmd.match(/wget.*\/([^\/\s]+\.(?:safetensors|ckpt|pt|bin))/i);
            if (wgetMatch) {
                return wgetMatch[1];
            }
        }
        
        // Fallback to job ID
        return `Download ${job.id.slice(0, 8)}`;
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
