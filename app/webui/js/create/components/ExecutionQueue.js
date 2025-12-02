/**
 * ExecutionQueue Component
 * Displays workflow execution queue with status and execution time
 * Similar to ResourceDownloadStatus but simpler - shows status only with manual refresh
 */

export class ExecutionQueue {
    constructor(containerId, sshConnection) {
        this.container = document.getElementById(containerId);
        this.sshConnection = sshConnection;
        this.isLoading = false;
        this.downloadedFiles = new Map(); // Track downloaded files: prompt_id -> Set of filenames
        this.activePopoverId = null; // Track which popover is currently open
    }

    /**
     * Update SSH connection string
     */
    setSshConnection(sshConnection) {
        this.sshConnection = sshConnection;
    }

    /**
     * Fetch and display execution queue status
     */
    async refresh() {
        if (!this.container) return;
        if (!this.sshConnection) {
            this.renderEmptyState('No instance selected', 'Select an instance to view execution queue');
            return;
        }

        this.isLoading = true;
        this.renderLoadingState();

        try {
            const response = await fetch('/create/execution-queue', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ssh_connection: this.sshConnection
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.message || 'Failed to fetch execution queue');
            }

            this.render(data.queue);
        } catch (error) {
            console.error('Error fetching execution queue:', error);
            this.renderErrorState(error.message);
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Render loading state
     */
    renderLoadingState() {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="execution-queue-loading">
                <div class="execution-queue-spinner"></div>
                <div class="execution-queue-loading-text">Loading execution queue...</div>
            </div>
        `;
    }

    /**
     * Render empty state
     */
    renderEmptyState(title, message) {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="execution-queue-empty">
                <div class="execution-queue-empty-icon">📋</div>
                <div class="execution-queue-empty-title">${this.escapeHtml(title)}</div>
                <div class="execution-queue-empty-message">${this.escapeHtml(message)}</div>
            </div>
        `;
    }

    /**
     * Render error state
     */
    renderErrorState(message) {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="execution-queue-error">
                <div class="execution-queue-error-icon">⚠️</div>
                <div class="execution-queue-error-title">Error Loading Queue</div>
                <div class="execution-queue-error-message">${this.escapeHtml(message)}</div>
            </div>
        `;
    }

    /**
     * Render execution queue
     */
    render(queueData) {
        if (!this.container) return;

        const { queue_running = [], queue_pending = [], recent_history = [] } = queueData;
        const hasActiveItems = queue_running.length > 0 || queue_pending.length > 0;
        const hasHistory = recent_history.length > 0;

        if (!hasActiveItems && !hasHistory) {
            this.renderEmptyState('No Executions', 'No workflows in queue or recent history');
            return;
        }

        let html = '<div class="execution-queue-content">';

        // Render active queue (running + pending)
        if (hasActiveItems) {
            html += '<div class="execution-queue-section">';
            html += '<div class="execution-queue-section-header">';
            html += '<span class="execution-queue-section-title">Active Queue</span>';
            html += `<span class="execution-queue-section-count">${queue_running.length + queue_pending.length}</span>`;
            html += '</div>';
            html += '<div class="execution-queue-items">';

            // Running items
            queue_running.forEach(item => {
                html += this.renderQueueItem(item, 'running');
            });

            // Pending items
            queue_pending.forEach(item => {
                html += this.renderQueueItem(item, 'pending');
            });

            html += '</div>';
            html += '</div>';
        }

        // Render recent history
        if (hasHistory) {
            html += '<div class="execution-queue-section">';
            html += '<div class="execution-queue-section-header">';
            html += '<span class="execution-queue-section-title">Recent History</span>';
            html += `<span class="execution-queue-section-count">${recent_history.length}</span>`;
            html += '</div>';
            html += '<div class="execution-queue-items">';

            recent_history.forEach(item => {
                html += this.renderHistoryItem(item);
            });

            html += '</div>';
            html += '</div>';
        }

        html += '</div>';
        this.container.innerHTML = html;
    }

    /**
     * Render a single queue item (running or pending)
     */
    renderQueueItem(item, status) {
        const statusIcon = status === 'running' ? '▶️' : '⏸️';
        const statusClass = `status-${status}`;
        const promptIdShort = item.prompt_id.substring(0, 8);

        // Calculate elapsed time for running items
        let statusText = status;
        if (status === 'running' && item.start_time) {
            const currentTime = Date.now() / 1000;
            const elapsedTime = currentTime - item.start_time;
            statusText = `${status} (${this.formatExecutionTime(elapsedTime)})`;
        }

        return `
            <div class="execution-queue-item ${statusClass}">
                <div class="execution-queue-item-header">
                    <span class="execution-queue-item-icon">${statusIcon}</span>
                    <span class="execution-queue-item-id" title="${this.escapeHtml(item.prompt_id)}">
                        ${this.escapeHtml(promptIdShort)}
                    </span>
                    <span class="execution-queue-item-status">${this.escapeHtml(statusText)}</span>
                </div>
            </div>
        `;
    }

    /**
     * Render a single history item
     */
    renderHistoryItem(item) {
        const statusIcons = {
            'success': '✅',
            'failed': '❌',
            'error': '❌',
            'unknown': '❓'
        };

        const statusIcon = statusIcons[item.status] || '❓';
        const statusClass = `status-${item.status}`;
        const promptIdShort = item.prompt_id.substring(0, 8);

        let executionTimeStr = '';
        if (item.execution_time !== null && item.execution_time !== undefined) {
            executionTimeStr = this.formatExecutionTime(item.execution_time);
        } else if (item.start_time && !item.end_time) {
            // Still running (in history but not completed)
            const currentTime = Date.now() / 1000;
            const elapsedTime = currentTime - item.start_time;
            executionTimeStr = this.formatExecutionTime(elapsedTime) + ' (ongoing)';
        }

        // Add preview button for successful executions
        const previewButton = item.status === 'success' ? `
            <button class="execution-queue-preview-btn" 
                    onclick="window.executionQueueInstance?.showOutputsPopover('${this.escapeHtml(item.prompt_id)}')"
                    title="Preview outputs">
                👁️ Preview
            </button>
        ` : '';

        return `
            <div class="execution-queue-item ${statusClass}" data-prompt-id="${this.escapeHtml(item.prompt_id)}">
                <div class="execution-queue-item-header">
                    <span class="execution-queue-item-icon">${statusIcon}</span>
                    <span class="execution-queue-item-id" title="${this.escapeHtml(item.prompt_id)}">
                        ${this.escapeHtml(promptIdShort)}
                    </span>
                    <span class="execution-queue-item-status">${this.escapeHtml(item.status)}</span>
                </div>
                ${executionTimeStr || previewButton ? `
                    <div class="execution-queue-item-footer">
                        ${executionTimeStr ? `<span class="execution-queue-item-time">⏱️ ${this.escapeHtml(executionTimeStr)}</span>` : ''}
                        ${previewButton}
                    </div>
                ` : ''}
                <div class="execution-queue-popover" id="popover-${this.escapeHtml(item.prompt_id)}" style="display: none;">
                    <div class="execution-queue-popover-content">
                        <div class="execution-queue-popover-loading">Loading outputs...</div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Format execution time in human-readable format
     */
    formatExecutionTime(seconds) {
        if (seconds < 1) {
            return `${Math.round(seconds * 1000)}ms`;
        } else if (seconds < 60) {
            return `${Math.round(seconds)}s`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const secs = Math.round(seconds % 60);
            return `${minutes}m ${secs}s`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Clear the queue display
     */
    clear() {
        if (!this.container) return;
        this.container.innerHTML = '';
    }

    /**
     * Show outputs popover for a prompt_id
     */
    async showOutputsPopover(promptId) {
        // Close any existing popover
        if (this.activePopoverId && this.activePopoverId !== promptId) {
            this.closePopover(this.activePopoverId);
        }

        const popover = document.getElementById(`popover-${promptId}`);
        if (!popover) return;

        // Toggle if clicking the same one
        if (this.activePopoverId === promptId) {
            this.closePopover(promptId);
            return;
        }

        // Show and load outputs
        popover.style.display = 'block';
        this.activePopoverId = promptId;

        try {
            const response = await fetch(`/create/execution-outputs/${promptId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ssh_connection: this.sshConnection
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.message || 'Failed to fetch outputs');
            }

            this.renderOutputsList(promptId, data.outputs);
        } catch (error) {
            console.error('Error fetching outputs:', error);
            this.renderOutputsError(promptId, error.message);
        }
    }

    /**
     * Close popover
     */
    closePopover(promptId) {
        const popover = document.getElementById(`popover-${promptId}`);
        if (popover) {
            popover.style.display = 'none';
        }
        if (this.activePopoverId === promptId) {
            this.activePopoverId = null;
        }
    }

    /**
     * Render outputs list in popover
     */
    renderOutputsList(promptId, outputs) {
        const popover = document.getElementById(`popover-${promptId}`);
        if (!popover) return;

        const content = popover.querySelector('.execution-queue-popover-content');
        if (!content) return;

        if (!outputs || outputs.length === 0) {
            content.innerHTML = '<div class="execution-queue-popover-empty">No outputs found</div>';
            return;
        }

        // Initialize downloaded files set for this prompt if it doesn't exist
        if (!this.downloadedFiles.has(promptId)) {
            this.downloadedFiles.set(promptId, new Set());
        }
        const downloaded = this.downloadedFiles.get(promptId);

        const outputsHtml = outputs.map(output => {
            const isDownloaded = downloaded.has(output.filename);
            const downloadedClass = isDownloaded ? 'downloaded' : '';
            
            return `
                <div class="execution-queue-output-item ${downloadedClass}" 
                     data-prompt-id="${this.escapeHtml(promptId)}"
                     data-fullpath="${this.escapeHtml(output.fullpath)}"
                     data-filename="${this.escapeHtml(output.filename)}"
                     data-format="${this.escapeHtml(output.format || output.output_type)}">
                    <span class="execution-queue-output-icon">${this.getOutputIcon(output.output_type)}</span>
                    <span class="execution-queue-output-name">${this.escapeHtml(output.filename)}</span>
                    ${isDownloaded ? '<span class="execution-queue-output-viewed">✓</span>' : ''}
                </div>
            `;
        }).join('');

        content.innerHTML = `
            <div class="execution-queue-popover-header">
                <span class="execution-queue-popover-title">Outputs (${outputs.length})</span>
                <button class="execution-queue-popover-close" onclick="window.executionQueueInstance?.closePopover('${this.escapeHtml(promptId)}')">&times;</button>
            </div>
            <div class="execution-queue-outputs-list">
                ${outputsHtml}
            </div>
        `;

        // Attach click event listeners to output items
        const outputItems = content.querySelectorAll('.execution-queue-output-item');
        outputItems.forEach(item => {
            item.addEventListener('click', () => {
                const outputData = {
                    fullpath: item.dataset.fullpath,
                    filename: item.dataset.filename,
                    format: item.dataset.format
                };
                this.previewOutput(item.dataset.promptId, outputData);
            });
        });
    }

    /**
     * Render error in popover
     */
    renderOutputsError(promptId, message) {
        const popover = document.getElementById(`popover-${promptId}`);
        if (!popover) return;

        const content = popover.querySelector('.execution-queue-popover-content');
        if (!content) return;

        content.innerHTML = `
            <div class="execution-queue-popover-header">
                <span class="execution-queue-popover-title">Error</span>
                <button class="execution-queue-popover-close" onclick="window.executionQueueInstance?.closePopover('${this.escapeHtml(promptId)}')">&times;</button>
            </div>
            <div class="execution-queue-popover-error">${this.escapeHtml(message)}</div>
        `;
    }

    /**
     * Preview an output file
     */
    async previewOutput(promptId, output) {
        try {
            // Check if already downloaded
            const downloadedSet = this.downloadedFiles.get(promptId) || new Set();
            
            // Download the file
            const response = await fetch('/create/download-output', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ssh_connection: this.sshConnection,
                    file_path: output.fullpath,
                    filename: output.filename
                })
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.message || 'Failed to download file');
            }

            // Get the file blob
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);

            // Mark as downloaded
            downloadedSet.add(output.filename);
            this.downloadedFiles.set(promptId, downloadedSet);

            // Update UI to show downloaded state
            const outputItem = document.querySelector(`[onclick*="'${promptId}'"][onclick*="${output.filename}"]`);
            if (outputItem) {
                outputItem.classList.add('downloaded');
                if (!outputItem.querySelector('.execution-queue-output-viewed')) {
                    outputItem.insertAdjacentHTML('beforeend', '<span class="execution-queue-output-viewed">✓</span>');
                }
            }

            // Show in overlay
            this.showOverlay(output.filename, url, output.format || output.output_type);

        } catch (error) {
            console.error('Error previewing output:', error);
            alert(`Error: ${error.message}`);
        }
    }

    /**
     * Show file in overlay
     */
    showOverlay(filename, url, format) {
        // Remove existing overlay if any
        const existingOverlay = document.getElementById('execution-queue-overlay');
        if (existingOverlay) {
            existingOverlay.remove();
        }

        // Create overlay
        const overlay = document.createElement('div');
        overlay.id = 'execution-queue-overlay';
        overlay.className = 'execution-queue-overlay';

        let contentHtml = '';
        const isVideo = format.includes('video') || format.includes('mp4') || format.includes('webm');
        const isImage = format.includes('image') || /\\.(jpg|jpeg|png|gif|webp)$/i.test(filename);

        if (isVideo) {
            contentHtml = `
                <video controls autoplay loop>
                    <source src="${url}" type="${format}">
                    Your browser does not support the video tag.
                </video>
            `;
        } else if (isImage) {
            contentHtml = `<img src="${url}" alt="${this.escapeHtml(filename)}">`;
        } else {
            contentHtml = `
                <div class="execution-queue-overlay-unsupported">
                    <p>Preview not supported for this file type</p>
                    <a href="${url}" download="${filename}" class="execution-queue-download-btn">Download ${this.escapeHtml(filename)}</a>
                </div>
            `;
        }

        overlay.innerHTML = `
            <div class="execution-queue-overlay-backdrop" onclick="document.getElementById('execution-queue-overlay').remove()"></div>
            <div class="execution-queue-overlay-content">
                <div class="execution-queue-overlay-header">
                    <span class="execution-queue-overlay-title">${this.escapeHtml(filename)}</span>
                    <button class="execution-queue-overlay-close" onclick="document.getElementById('execution-queue-overlay').remove()">&times;</button>
                </div>
                <div class="execution-queue-overlay-body">
                    ${contentHtml}
                </div>
            </div>
        `;

        document.body.appendChild(overlay);
    }

    /**
     * Get icon for output type
     */
    getOutputIcon(outputType) {
        const icons = {
            'images': '🖼️',
            'videos': '🎬',
            'gifs': '🎞️'
        };
        return icons[outputType] || '📄';
    }
}
