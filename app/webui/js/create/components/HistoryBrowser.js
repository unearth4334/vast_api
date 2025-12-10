/**
 * Workflow History Browser Component
 * Displays a tiled view of previous workflow submissions with thumbnails and timestamps
 */

export class HistoryBrowser {
    constructor(containerId, onSelectCallback) {
        this.containerId = containerId;
        this.onSelectCallback = onSelectCallback;
        this.workflowId = null;
        this.records = [];
        this.offset = 0;
        this.limit = 10;
        this.hasMore = false;
        this.isLoading = false;
    }

    /**
     * Open the history browser overlay
     * @param {string} workflowId - Current workflow ID to filter by
     */
    async open(workflowId) {
        this.workflowId = workflowId;
        this.records = [];
        this.offset = 0;
        
        // Create overlay
        this.createOverlay();
        
        // Load initial records
        await this.loadRecords();
    }

    /**
     * Create the overlay UI
     */
    createOverlay() {
        // Remove existing overlay if any
        const existing = document.getElementById('history-browser-overlay');
        if (existing) {
            existing.remove();
        }

        // Create overlay
        const overlay = document.createElement('div');
        overlay.id = 'history-browser-overlay';
        overlay.className = 'history-browser-overlay';
        overlay.innerHTML = `
            <div class="history-browser-modal">
                <div class="history-browser-header">
                    <h3>📜 Workflow History</h3>
                    <button class="history-browser-close" onclick="window.historyBrowserInstance.close()">✕</button>
                </div>
                <div class="history-browser-content">
                    <div id="history-browser-grid" class="history-browser-grid">
                        <!-- History tiles will be loaded here -->
                    </div>
                    <div class="history-browser-loading" id="history-browser-loading" style="display: none;">
                        <span>⏳</span> Loading...
                    </div>
                    <div class="history-browser-empty" id="history-browser-empty" style="display: none;">
                        <div class="history-browser-empty-icon">📭</div>
                        <div class="history-browser-empty-text">No history found for this workflow</div>
                    </div>
                    <div class="history-browser-load-more-container" id="history-browser-load-more-container" style="display: none;">
                        <button class="history-browser-load-more" onclick="window.historyBrowserInstance.loadMore()">
                            Load More
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        // Close on overlay click (but not modal click)
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                this.close();
            }
        });
    }

    /**
     * Load history records from the API
     */
    async loadRecords() {
        if (this.isLoading) return;

        this.isLoading = true;
        this.showLoading(true);

        try {
            const url = `/create/history/list?workflow_id=${encodeURIComponent(this.workflowId)}&limit=${this.limit}&offset=${this.offset}`;
            const response = await fetch(url);
            const data = await response.json();

            if (data.success) {
                this.records = this.records.concat(data.records);
                this.hasMore = data.pagination.has_more;
                this.renderRecords();
            } else {
                console.error('Failed to load history:', data.message);
                this.showEmpty();
            }
        } catch (error) {
            console.error('Error loading history:', error);
            this.showEmpty();
        } finally {
            this.isLoading = false;
            this.showLoading(false);
        }
    }

    /**
     * Load more records (for pagination)
     */
    async loadMore() {
        this.offset += 5;  // Load 5 more at a time
        // Keep limit at 5 for subsequent loads
        const previousLimit = this.limit;
        this.limit = 5;
        await this.loadRecords();
        // Don't restore limit - keep it at 5 for consistent pagination
    }

    /**
     * Group consecutive identical records (except timestamp and seed)
     * @param {Array} records - Array of history records
     * @returns {Array} Array of grouped records with count
     */
    groupConsecutiveRecords(records) {
        if (records.length === 0) return [];

        const grouped = [];
        let currentGroup = {
            representative: records[0],
            records: [records[0]],
            count: 1
        };

        for (let i = 1; i < records.length; i++) {
            const current = records[i];
            const previous = records[i - 1];

            // Check if records are identical except timestamp and seed
            if (this.areRecordsIdentical(current, previous)) {
                currentGroup.records.push(current);
                currentGroup.count++;
            } else {
                // Push the completed group
                grouped.push(currentGroup);
                // Start a new group
                currentGroup = {
                    representative: current,
                    records: [current],
                    count: 1
                };
            }
        }

        // Don't forget the last group
        grouped.push(currentGroup);

        return grouped;
    }

    /**
     * Check if two records are identical except for timestamp and seed
     * @param {Object} record1 - First record
     * @param {Object} record2 - Second record
     * @returns {boolean} True if records are identical (ignoring timestamp and seed)
     */
    areRecordsIdentical(record1, record2) {
        // Must have same workflow_id
        if (record1.workflow_id !== record2.workflow_id) {
            return false;
        }

        // Compare inputs, excluding seed values
        const inputs1 = { ...record1.inputs };
        const inputs2 = { ...record2.inputs };

        // Remove seed-related fields (common names: seed, random_seed, noise_seed)
        delete inputs1.seed;
        delete inputs2.seed;
        delete inputs1.random_seed;
        delete inputs2.random_seed;
        delete inputs1.noise_seed;
        delete inputs2.noise_seed;

        // Compare remaining inputs
        return JSON.stringify(inputs1) === JSON.stringify(inputs2);
    }

    /**
     * Render history records as tiles
     */
    renderRecords() {
        const grid = document.getElementById('history-browser-grid');
        const empty = document.getElementById('history-browser-empty');
        const loadMoreContainer = document.getElementById('history-browser-load-more-container');

        if (this.records.length === 0) {
            grid.style.display = 'none';
            empty.style.display = 'flex';
            loadMoreContainer.style.display = 'none';
            return;
        }

        grid.style.display = 'grid';
        empty.style.display = 'none';

        // Group consecutive identical records
        const groupedRecords = this.groupConsecutiveRecords(this.records);

        // Clear grid and render tiles using DOM methods for security
        grid.innerHTML = '';
        groupedRecords.forEach(group => {
            const tile = this.createRecordTile(group.representative, group.count, group.records);
            grid.appendChild(tile);
        });

        // Show/hide load more button
        if (this.hasMore) {
            loadMoreContainer.style.display = 'block';
        } else {
            loadMoreContainer.style.display = 'none';
        }
    }

    /**
     * Create a single history record tile element
     * @param {Object} record - History record (representative of the group)
     * @param {number} count - Number of identical consecutive records
     * @param {Array} allRecords - All records in this group (for potential future use)
     * @returns {HTMLElement} Tile element
     */
    createRecordTile(record, count = 1, allRecords = [record]) {
        const timestamp = this.formatTimestamp(record.timestamp);
        const thumbnailUrl = record.thumbnail 
            ? `/create/thumbnail/${encodeURIComponent(record.thumbnail)}`
            : null;

        // Create tile container
        const tile = document.createElement('div');
        tile.className = 'history-tile';
        
        // Add stacked class if count > 1
        if (count > 1) {
            tile.classList.add('history-tile-stacked');
        }
        
        // Add click handler securely
        tile.addEventListener('click', () => {
            this.selectRecord(record.record_id);
        });

        // Create image container
        const imageContainer = document.createElement('div');
        imageContainer.className = 'history-tile-image';

        if (thumbnailUrl) {
            const img = document.createElement('img');
            img.src = thumbnailUrl;
            img.alt = 'Thumbnail';
            img.className = 'history-tile-thumbnail';
            imageContainer.appendChild(img);
        } else {
            const noThumb = document.createElement('div');
            noThumb.className = 'history-tile-no-thumbnail';
            noThumb.textContent = '📷';
            imageContainer.appendChild(noThumb);
        }

        // Add count badge if count > 1
        if (count > 1) {
            const countBadge = document.createElement('div');
            countBadge.className = 'history-tile-count-badge';
            countBadge.textContent = `x${count}`;
            imageContainer.appendChild(countBadge);
        }

        // Create info container
        const infoContainer = document.createElement('div');
        infoContainer.className = 'history-tile-info';

        const timeDiv = document.createElement('div');
        timeDiv.className = 'history-tile-time';
        timeDiv.textContent = timestamp;

        const workflowDiv = document.createElement('div');
        workflowDiv.className = 'history-tile-workflow';
        workflowDiv.textContent = record.workflow_id;

        infoContainer.appendChild(timeDiv);
        infoContainer.appendChild(workflowDiv);

        tile.appendChild(imageContainer);
        tile.appendChild(infoContainer);

        return tile;
    }

    /**
     * Render a single history record tile (deprecated - use createRecordTile)
     * @param {Object} record - History record
     * @returns {string} HTML string
     */
    renderRecordTile(record) {
        const timestamp = this.formatTimestamp(record.timestamp);
        const thumbnailUrl = record.thumbnail 
            ? `/create/thumbnail/${encodeURIComponent(record.thumbnail)}`
            : null;

        const thumbnailHtml = thumbnailUrl
            ? `<img src="${thumbnailUrl}" alt="Thumbnail" class="history-tile-thumbnail">`
            : `<div class="history-tile-no-thumbnail">📷</div>`;

        return `
            <div class="history-tile" data-record-id="${this.escapeHtml(record.record_id)}">
                <div class="history-tile-image">
                    ${thumbnailHtml}
                </div>
                <div class="history-tile-info">
                    <div class="history-tile-time">${this.escapeHtml(timestamp)}</div>
                    <div class="history-tile-workflow">${this.escapeHtml(record.workflow_id)}</div>
                </div>
            </div>
        `;
    }

    /**
     * Format timestamp for display
     * @param {string} timestamp - ISO timestamp
     * @returns {string} Formatted timestamp (YY/MM/DD-HH:MM:SS)
     */
    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        const year = String(date.getFullYear()).slice(-2);
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        
        return `${year}/${month}/${day}-${hours}:${minutes}:${seconds}`;
    }

    /**
     * Select a history record and populate the form
     * @param {string} recordId - Record ID
     */
    async selectRecord(recordId) {
        try {
            const response = await fetch(`/create/history/${encodeURIComponent(recordId)}`);
            const data = await response.json();

            if (data.success) {
                // Close the browser
                this.close();

                // Call the callback with the record
                if (this.onSelectCallback) {
                    this.onSelectCallback(data.record);
                }
            } else {
                console.error('Failed to load record:', data.message);
                alert('Failed to load record: ' + data.message);
            }
        } catch (error) {
            console.error('Error loading record:', error);
            alert('Error loading record: ' + error.message);
        }
    }

    /**
     * Close the history browser
     */
    close() {
        const overlay = document.getElementById('history-browser-overlay');
        if (overlay) {
            overlay.remove();
        }
    }

    /**
     * Show/hide loading indicator
     * @param {boolean} show - Whether to show loading
     */
    showLoading(show) {
        const loading = document.getElementById('history-browser-loading');
        if (loading) {
            loading.style.display = show ? 'flex' : 'none';
        }
    }

    /**
     * Show empty state
     */
    showEmpty() {
        const grid = document.getElementById('history-browser-grid');
        const empty = document.getElementById('history-browser-empty');
        const loadMoreContainer = document.getElementById('history-browser-load-more-container');

        if (grid) grid.style.display = 'none';
        if (empty) empty.style.display = 'flex';
        if (loadMoreContainer) loadMoreContainer.style.display = 'none';
    }

    /**
     * Escape HTML to prevent XSS
     * @param {string} str - String to escape
     * @returns {string} Escaped string
     */
    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}
