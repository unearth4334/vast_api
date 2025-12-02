/**
 * ExecutionQueue Component
 * Displays workflow execution queue with status, execution time, and thumbnails
 * Supports compact and detailed view modes
 * Supports hiding items via temporary ignore list
 */

export class ExecutionQueue {
    constructor(containerId, sshConnection) {
        this.container = document.getElementById(containerId);
        this.sshConnection = sshConnection;
        this.isLoading = false;
        this.downloadedFiles = new Map(); // Track downloaded files: prompt_id -> Set of filenames
        this.activePopoverId = null; // Track which popover is currently open
        this.viewMode = 'compact'; // 'compact' or 'detailed'
        this.deleteMode = false; // Delete/hide mode state
        this.ignoredItems = new Set(); // Set of ignored prompt_ids
        this.initializeViewToggle();
        this.setupEventListeners();
    }

    /**
     * Setup global event listeners for delete mode
     */
    setupEventListeners() {
        // Listen for clicks anywhere to exit delete mode
        document.addEventListener('click', (e) => {
            if (!this.deleteMode) return;
            
            // Don't exit if clicking delete buttons or queue items
            if (e.target.closest('.execution-queue-delete-btn') || 
                e.target.closest('.execution-queue-delete-all-btn')) {
                return;
            }
            
            // Don't exit if clicking a queue item to enter delete mode
            if (e.target.closest('.execution-queue-item') && !this.deleteMode) {
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
        
        const wrappers = this.container.querySelectorAll('.execution-queue-item-wrapper');
        wrappers.forEach(wrapper => wrapper.classList.add('delete-mode'));
        
        const deleteAllBtn = this.container.querySelector('.execution-queue-delete-all-btn');
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
        
        const wrappers = this.container.querySelectorAll('.execution-queue-item-wrapper');
        wrappers.forEach(wrapper => wrapper.classList.remove('delete-mode'));
        
        const deleteAllBtn = this.container.querySelector('.execution-queue-delete-all-btn');
        if (deleteAllBtn) {
            deleteAllBtn.classList.remove('visible');
        }
    }

    /**
     * Handle queue item click
     */
    handleItemClick(e) {
        // Don't toggle if clicking delete button, preview button, or popover
        if (e.target.closest('.execution-queue-delete-btn') ||
            e.target.closest('.execution-queue-preview-btn') ||
            e.target.closest('.execution-queue-popover')) {
            return;
        }
        
        e.stopPropagation();
        
        if (this.deleteMode) {
            // If already in delete mode and clicking item, exit
            this.exitDeleteMode();
        } else {
            // Enter delete mode
            this.enterDeleteMode();
        }
    }

    /**
     * Hide/ignore a single queue item
     */
    hideItem(promptId) {
        this.ignoredItems.add(promptId);
        // Refresh to update the view
        this.refresh();
        // Stay in delete mode
    }

    /**
     * Hide/ignore all visible queue items
     */
    hideAllItems() {
        const confirmed = confirm('Hide all execution queue items? They will remain hidden until the page is refreshed.');
        if (!confirmed) return;
        
        // Add all visible items to ignore list
        const items = this.container.querySelectorAll('.execution-queue-item');
        items.forEach(item => {
            const promptId = item.dataset.promptId;
            if (promptId) {
                this.ignoredItems.add(promptId);
            }
        });
        
        // Refresh and exit delete mode
        this.refresh();
        this.exitDeleteMode();
    }

    /**
     * Clear the ignore list
     */
    clearIgnoreList() {
        this.ignoredItems.clear();
        this.refresh();
    }

    /**
     * Initialize view toggle buttons
     */
    initializeViewToggle() {
        const viewToggle = document.querySelector('.execution-queue-view-toggle');
        if (!viewToggle) return;

        const buttons = viewToggle.querySelectorAll('.view-btn');
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                const view = btn.dataset.view;
                this.setViewMode(view);
            });
        });
    }

    /**
     * Set view mode
     */
    setViewMode(mode) {
        this.viewMode = mode;

        // Update button states
        const viewToggle = document.querySelector('.execution-queue-view-toggle');
        if (viewToggle) {
            const buttons = viewToggle.querySelectorAll('.view-btn');
            buttons.forEach(btn => {
                if (btn.dataset.view === mode) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });
        }

        // Update container class
        if (this.container) {
            this.container.classList.toggle('detailed-view', mode === 'detailed');
        }

        // Re-render if we have data
        if (!this.isLoading && this.container && this.container.querySelector('.execution-queue-item')) {
            // Trigger a refresh to update the view
            this.refresh();
        }
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
        
        // Filter out ignored items
        const filteredRunning = queue_running.filter(item => !this.ignoredItems.has(item.prompt_id));
        const filteredPending = queue_pending.filter(item => !this.ignoredItems.has(item.prompt_id));
        const filteredHistory = recent_history.filter(item => !this.ignoredItems.has(item.prompt_id));
        
        const hasActiveItems = filteredRunning.length > 0 || filteredPending.length > 0;
        const hasHistory = filteredHistory.length > 0;

        if (!hasActiveItems && !hasHistory) {
            this.renderEmptyState('No Executions', 'No workflows in queue or recent history');
            return;
        }

        let html = '<div class="execution-queue-content">';
        
        // Add "Delete All" button (hidden by default, shown in delete mode)
        html += `<button class="execution-queue-delete-all-btn" onclick="window.executionQueueInstance?.hideAllItems()">🗑️ Hide All</button>`;

        // Render active queue (running + pending)
        if (hasActiveItems) {
            html += '<div class="execution-queue-section">';
            html += '<div class="execution-queue-section-header">';
            html += '<span class="execution-queue-section-title">Active Queue</span>';
            html += `<span class="execution-queue-section-count">${filteredRunning.length + filteredPending.length}</span>`;
            html += '</div>';
            html += '<div class="execution-queue-items">';

            // Running items
            filteredRunning.forEach(item => {
                html += this.renderQueueItem(item, 'running');
            });

            // Pending items
            filteredPending.forEach(item => {
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
            html += `<span class="execution-queue-section-count">${filteredHistory.length}</span>`;
            html += '</div>';
            html += '<div class="execution-queue-items">';

            filteredHistory.forEach(item => {
                html += this.renderHistoryItem(item);
            });

            html += '</div>';
            html += '</div>';
        }

        html += '</div>';
        this.container.innerHTML = html;
    }

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

        // Render thumbnail if in detailed view and thumbnail exists
        let thumbnailHtml = '';
        if (this.viewMode === 'detailed' && item.thumbnail) {
            thumbnailHtml = `
                <div class="execution-queue-item-thumbnail">
                    <img src="/create/thumbnail/${this.escapeHtml(item.thumbnail)}" 
                         alt="Workflow thumbnail"
                         onerror="this.parentElement.style.display='none'">
                </div>
            `;
        }

        return `
            <div class="execution-queue-item-wrapper" onclick="window.executionQueueInstance?.handleItemClick(event)">
                <div class="execution-queue-item ${statusClass}" data-prompt-id="${this.escapeHtml(item.prompt_id)}">
                    ${thumbnailHtml}
                    <div class="execution-queue-item-content">
                        <div class="execution-queue-item-header">
                            <span class="execution-queue-item-icon">${statusIcon}</span>
                            <span class="execution-queue-item-id" title="${this.escapeHtml(item.prompt_id)}">
                                ${this.escapeHtml(promptIdShort)}
                            </span>
                            <span class="execution-queue-item-status">${this.escapeHtml(statusText)}</span>
                        </div>
                    </div>
                </div>
                <button class="execution-queue-delete-btn" onclick="event.stopPropagation(); window.executionQueueInstance?.hideItem('${this.escapeHtml(item.prompt_id)}')">🗑️</button>
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

        // Render thumbnail if in detailed view and thumbnail exists
        let thumbnailHtml = '';
        if (this.viewMode === 'detailed' && item.thumbnail) {
            thumbnailHtml = `
                <div class="execution-queue-item-thumbnail">
                    <img src="/create/thumbnail/${this.escapeHtml(item.thumbnail)}" 
                         alt="Workflow thumbnail"
                         onerror="this.parentElement.style.display='none'">
                </div>
            `;
        }

        return `
            <div class="execution-queue-item-wrapper" onclick="window.executionQueueInstance?.handleItemClick(event)">
                <div class="execution-queue-item ${statusClass}" data-prompt-id="${this.escapeHtml(item.prompt_id)}">
                    ${thumbnailHtml}
                    <div class="execution-queue-item-content">
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
                    </div>
                    <div class="execution-queue-popover" id="popover-${this.escapeHtml(item.prompt_id)}" style="display: none;">
                        <div class="execution-queue-popover-content">
                            <div class="execution-queue-popover-loading">Loading outputs...</div>
                        </div>
                    </div>
                </div>
                <button class="execution-queue-delete-btn" onclick="event.stopPropagation(); window.executionQueueInstance?.hideItem('${this.escapeHtml(item.prompt_id)}')">🗑️</button>
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
     * Preview an output file - opens in new browser tab
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

            // Update UI to show downloaded state - use data attribute selector
            const outputItem = document.querySelector(`[data-prompt-id="${promptId}"][data-filename="${output.filename}"]`);
            if (outputItem) {
                outputItem.classList.add('downloaded');
                if (!outputItem.querySelector('.execution-queue-output-viewed')) {
                    outputItem.insertAdjacentHTML('beforeend', '<span class="execution-queue-output-viewed">✓</span>');
                }
            }

            // Open in new tab
            window.open(url, '_blank');

        } catch (error) {
            console.error('Error previewing output:', error);
            alert(`Error: ${error.message}`);
        }
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
