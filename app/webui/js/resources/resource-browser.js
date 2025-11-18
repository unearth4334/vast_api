/**
 * Resource Browser
 * 
 * Main component for browsing, filtering, and selecting resources
 */

import { createResourceCard, updateCardSelection, expandCard, collapseCard } from './resource-card.js';

export class ResourceBrowser {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.selectedResources = new Set();
        this.resources = [];
        this.expandedCard = null; // Track currently expanded card
        this.filters = {
            ecosystem: null,
            type: null,
            tags: [],
            search: ''
        };
        
        // Make globally available
        window.resourceBrowser = this;
    }
    
    /**
     * Initialize the browser UI
     */
    async initialize() {
        console.log('Initializing Resource Browser');
        
        // Create UI structure
        this.container.innerHTML = `
            <div class="resource-browser">
                <div class="resource-header">
                    <h2>Resource Manager</h2>
                    <p>Browse and install workflows, models, and other assets</p>
                </div>
                
                <div class="resource-filters">
                    <div class="filter-group">
                        <label for="filter-ecosystem">Ecosystem:</label>
                        <select id="filter-ecosystem" class="filter-select">
                            <option value="">All Ecosystems</option>
                        </select>
                    </div>
                    
                    <div class="filter-group">
                        <label for="filter-type">Type:</label>
                        <select id="filter-type" class="filter-select">
                            <option value="">All Types</option>
                        </select>
                    </div>
                    
                    <div class="filter-group">
                        <label for="filter-search">Search:</label>
                        <input type="text" id="filter-search" class="filter-input" placeholder="Search resources...">
                    </div>
                    
                    <button id="btn-clear-filters" class="btn-secondary">Clear Filters</button>
                </div>
                
                <div class="resource-content">
                    <div id="resource-grid" class="resource-grid">
                        <div class="loading">Loading resources...</div>
                    </div>
                </div>
                
                <div class="resource-footer">
                    <div class="selection-info">
                        <span id="selection-count">No resources selected</span>
                    </div>
                    <div class="action-buttons">
                        <button id="btn-clear-selection" class="btn-secondary" disabled>Clear Selection</button>
                        <button id="btn-install-selected" class="btn-primary" disabled>Install Selected</button>
                    </div>
                </div>
            </div>
        `;
        
        // Attach event listeners
        this._attachEventListeners();
        
        // Load filter options and resources
        await this._loadFilterOptions();
        await this.loadResources();
    }
    
    /**
     * Attach event listeners to UI elements
     */
    _attachEventListeners() {
        const ecosystemFilter = document.getElementById('filter-ecosystem');
        const typeFilter = document.getElementById('filter-type');
        const searchInput = document.getElementById('filter-search');
        const clearFiltersBtn = document.getElementById('btn-clear-filters');
        const clearSelectionBtn = document.getElementById('btn-clear-selection');
        const installBtn = document.getElementById('btn-install-selected');
        
        ecosystemFilter.addEventListener('change', (e) => {
            this.filters.ecosystem = e.target.value || null;
            this.loadResources();
        });
        
        typeFilter.addEventListener('change', (e) => {
            this.filters.type = e.target.value || null;
            this.loadResources();
        });
        
        // Debounce search input
        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.filters.search = e.target.value;
                this.loadResources();
            }, 300);
        });
        
        clearFiltersBtn.addEventListener('click', () => {
            this.clearFilters();
        });
        
        clearSelectionBtn.addEventListener('click', () => {
            this.clearSelection();
        });
        
        installBtn.addEventListener('click', () => {
            this.installSelected();
        });
    }
    
    /**
     * Load filter options from API
     */
    async _loadFilterOptions() {
        try {
            const [ecosystems, types] = await Promise.all([
                window.api.get('/resources/ecosystems'),
                window.api.get('/resources/types')
            ]);
            
            if (ecosystems.success) {
                const select = document.getElementById('filter-ecosystem');
                ecosystems.ecosystems.forEach(eco => {
                    const option = document.createElement('option');
                    option.value = eco;
                    option.textContent = eco.toUpperCase();
                    select.appendChild(option);
                });
            }
            
            if (types.success) {
                const select = document.getElementById('filter-type');
                types.types.forEach(type => {
                    const option = document.createElement('option');
                    option.value = type;
                    option.textContent = type.charAt(0).toUpperCase() + type.slice(1);
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading filter options:', error);
        }
    }
    
    /**
     * Load resources from API with current filters
     */
    async loadResources() {
        const grid = document.getElementById('resource-grid');
        grid.innerHTML = '<div class="loading">Loading resources...</div>';
        
        try {
            const params = new URLSearchParams();
            if (this.filters.ecosystem) params.append('ecosystem', this.filters.ecosystem);
            if (this.filters.type) params.append('type', this.filters.type);
            if (this.filters.search) params.append('search', this.filters.search);
            
            const response = await window.api.get(`/resources/list?${params}`);
            
            if (response.success) {
                this.resources = response.resources;
                this.renderResources(response.resources);
            } else {
                grid.innerHTML = `<div class="error">Error: ${response.message}</div>`;
            }
        } catch (error) {
            console.error('Error loading resources:', error);
            grid.innerHTML = '<div class="error">Failed to load resources</div>';
        }
    }
    
    /**
     * Render resources in grid
     */
    renderResources(resources) {
        const grid = document.getElementById('resource-grid');
        grid.innerHTML = '';
        
        if (resources.length === 0) {
            grid.innerHTML = '<div class="no-results">No resources found</div>';
            return;
        }
        
        resources.forEach(resource => {
            const card = createResourceCard(resource);
            
            // Update selection state if already selected
            if (this.selectedResources.has(resource.filepath)) {
                updateCardSelection(card, true);
            }
            
            grid.appendChild(card);
        });
    }
    
    /**
     * Toggle resource selection
     */
    toggleSelection(filepath) {
        if (this.selectedResources.has(filepath)) {
            this.selectedResources.delete(filepath);
        } else {
            this.selectedResources.add(filepath);
        }
        
        // Update card visuals
        const card = document.querySelector(`[data-resource-path="${filepath}"]`);
        if (card) {
            updateCardSelection(card, this.selectedResources.has(filepath));
        }
        
        this.updateSelectionUI();
    }
    
    /**
     * Expand a card to show full details
     */
    expandCard(filepath) {
        const card = document.querySelector(`[data-resource-path="${filepath}"]`);
        if (!card) return;
        
        // Collapse previously expanded card
        if (this.expandedCard && this.expandedCard !== card) {
            collapseCard(this.expandedCard);
        }
        
        // Toggle current card
        if (this.expandedCard === card) {
            collapseCard(card);
            this.expandedCard = null;
        } else {
            expandCard(card);
            this.expandedCard = card;
        }
    }
    
    /**
     * Clear all selections
     */
    clearSelection() {
        this.selectedResources.clear();
        
        // Update all cards
        document.querySelectorAll('.resource-card').forEach(card => {
            updateCardSelection(card, false);
        });
        
        this.updateSelectionUI();
    }
    
    /**
     * Update selection count and button states
     */
    updateSelectionUI() {
        const count = this.selectedResources.size;
        const countEl = document.getElementById('selection-count');
        const clearBtn = document.getElementById('btn-clear-selection');
        const installBtn = document.getElementById('btn-install-selected');
        
        if (count === 0) {
            countEl.textContent = 'No resources selected';
            clearBtn.disabled = true;
            installBtn.disabled = true;
        } else {
            // Calculate total size
            let totalSize = 0;
            this.resources.forEach(r => {
                if (this.selectedResources.has(r.filepath) && r.metadata.size) {
                    totalSize += r.metadata.size;
                }
            });
            
            const sizeStr = totalSize > 0 ? ` (${this._formatBytes(totalSize)})` : '';
            countEl.textContent = `${count} resource${count !== 1 ? 's' : ''} selected${sizeStr}`;
            clearBtn.disabled = false;
            installBtn.disabled = false;
        }
    }
    
    /**
     * Clear all filters
     */
    clearFilters() {
        this.filters = {
            ecosystem: null,
            type: null,
            tags: [],
            search: ''
        };
        
        document.getElementById('filter-ecosystem').value = '';
        document.getElementById('filter-type').value = '';
        document.getElementById('filter-search').value = '';
        
        this.loadResources();
    }
    
    /**
     * View resource details (show modal or sidebar)
     */
    viewResource(resource) {
        // For now, just show an alert with details
        // In a full implementation, this would open a modal with full details
        const title = resource.description.split('\n')[0].replace(/^#\s+/, '');
        alert(`Resource: ${title}\n\nType: ${resource.metadata.type}\nEcosystem: ${resource.metadata.ecosystem}\n\n${resource.description.substring(0, 200)}...`);
    }
    
    /**
     * Install selected resources
     */
    async installSelected() {
        if (this.selectedResources.size === 0) {
            return;
        }
        
        // Get SSH connection string (should come from UI state)
        const sshConnection = document.getElementById('sshConnectionString')?.value;
        
        if (!sshConnection) {
            alert('Please provide an SSH connection string first');
            return;
        }
        
        const installBtn = document.getElementById('btn-install-selected');
        const originalText = installBtn.textContent;
        installBtn.disabled = true;
        installBtn.textContent = 'Installing...';
        
        try {
            const response = await window.api.post('/resources/install', {
                ssh_connection: sshConnection,
                resources: Array.from(this.selectedResources),
                ui_home: '/workspace/ComfyUI'
            });
            
            if (response.success) {
                alert(`Successfully installed ${response.installed}/${response.total} resources!`);
                this.clearSelection();
            } else {
                alert(`Installation failed: ${response.message}`);
            }
        } catch (error) {
            console.error('Installation error:', error);
            alert(`Installation error: ${error.message}`);
        } finally {
            installBtn.disabled = false;
            installBtn.textContent = originalText;
        }
    }
    
    /**
     * Format bytes helper
     */
    _formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }
}
