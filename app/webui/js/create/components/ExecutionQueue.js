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

        return `
            <div class="execution-queue-item ${statusClass}">
                <div class="execution-queue-item-header">
                    <span class="execution-queue-item-icon">${statusIcon}</span>
                    <span class="execution-queue-item-id" title="${this.escapeHtml(item.prompt_id)}">
                        ${this.escapeHtml(promptIdShort)}
                    </span>
                    <span class="execution-queue-item-status">${this.escapeHtml(status)}</span>
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

        return `
            <div class="execution-queue-item ${statusClass}">
                <div class="execution-queue-item-header">
                    <span class="execution-queue-item-icon">${statusIcon}</span>
                    <span class="execution-queue-item-id" title="${this.escapeHtml(item.prompt_id)}">
                        ${this.escapeHtml(promptIdShort)}
                    </span>
                    <span class="execution-queue-item-status">${this.escapeHtml(item.status)}</span>
                </div>
                ${executionTimeStr ? `
                    <div class="execution-queue-item-footer">
                        <span class="execution-queue-item-time">⏱️ ${this.escapeHtml(executionTimeStr)}</span>
                    </div>
                ` : ''}
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
}
