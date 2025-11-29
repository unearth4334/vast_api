/**
 * Resource Browser
 * 
 * Main component for browsing, filtering, and selecting resources
 * Tile viewer design with lazy loading, sorting, and media controls
 */

import { createResourceCard, updateCardSelection, expandCard, collapseCard } from './resource-card.js';
import { ResourceDownloadStatus } from '../resource-download-status.js';

// Tile Viewer Configuration
const TILE_VIEWER_CONFIG = {
    // Media settings
    lazyLoadThreshold: 200,     // pixels before viewport to start loading
    autoplayVideos: true,       // autoplay videos on hover
    videoHoverDelay: 300,       // ms delay before video starts
    
    // Sorting options
    sortOptions: [
        { value: 'name-asc', label: 'Name (A-Z)', field: 'title', order: 'asc' },
        { value: 'name-desc', label: 'Name (Z-A)', field: 'title', order: 'desc' },
        { value: 'type-asc', label: 'Type (A-Z)', field: 'type', order: 'asc' },
        { value: 'size-desc', label: 'Size (Largest)', field: 'size', order: 'desc' },
        { value: 'size-asc', label: 'Size (Smallest)', field: 'size', order: 'asc' },
        { value: 'date-desc', label: 'Newest First', field: 'published', order: 'desc' },
        { value: 'date-asc', label: 'Oldest First', field: 'published', order: 'asc' }
    ],
    
    // View modes
    viewModes: ['grid', 'list'],
    defaultView: 'grid'
};

export class ResourceBrowser {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.selectedResources = new Set();
        this.resources = [];
        this.expandedCard = null; // Track currently expanded card
        this.filters = {
            ecosystems: [],  // Changed to array for multiple selection
            types: [],       // Changed to array for multiple selection
            tags: [],
            search: ''
        };
        
        // Tile viewer state
        this.sortBy = 'name-asc';
        this.viewMode = TILE_VIEWER_CONFIG.defaultView;
        this.lazyLoadObserver = null;
        
        // Make globally available
        window.resourceBrowser = this;

        // Download status UI
        this.downloadStatus = new ResourceDownloadStatus('download-status-container');
    }
    
    /**
     * Initialize the browser UI
     */
    async initialize() {
        console.log('Initializing Resource Browser with Tile Viewer');
        
        // Create UI structure with tile viewer design
        this.container.innerHTML = `
            <div class="resource-browser">
                <div class="resource-header">
                    <h2>Resource Manager</h2>
                    <p>Browse and install workflows, models, and other assets</p>
                </div>
                
                <!-- Tile Viewer Filter Bar -->
                <div class="tile-viewer-filters">
                    <div class="filter-pills">
                        <button class="filter-pill filter-pill-ecosystem" data-filter="ecosystem">
                            <span class="pill-icon">🌐</span>
                            <span class="pill-label">Ecosystem</span>
                            <span class="pill-value">All</span>
                            <span class="pill-dropdown">▾</span>
                        </button>
                        <button class="filter-pill filter-pill-type" data-filter="type">
                            <span class="pill-icon">📁</span>
                            <span class="pill-label">Type</span>
                            <span class="pill-value">All</span>
                            <span class="pill-dropdown">▾</span>
                        </button>
                    </div>
                    
                    <div class="filter-search-container">
                        <span class="search-icon">🔍</span>
                        <input type="text" id="filter-search" class="filter-search-input" placeholder="Search resources...">
                    </div>
                    
                    <div class="filter-controls">
                        <div class="sort-control">
                            <label for="sort-select">Sort:</label>
                            <select id="sort-select" class="sort-select">
                                ${TILE_VIEWER_CONFIG.sortOptions.map(opt => 
                                    `<option value="${opt.value}">${opt.label}</option>`
                                ).join('')}
                            </select>
                        </div>
                        
                        <div class="view-toggle">
                            <button class="view-btn view-btn-grid active" data-view="grid" title="Grid View">
                                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                                    <rect x="1" y="1" width="6" height="6" rx="1"/>
                                    <rect x="9" y="1" width="6" height="6" rx="1"/>
                                    <rect x="1" y="9" width="6" height="6" rx="1"/>
                                    <rect x="9" y="9" width="6" height="6" rx="1"/>
                                </svg>
                            </button>
                            <button class="view-btn view-btn-list" data-view="list" title="List View">
                                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                                    <rect x="1" y="2" width="14" height="3" rx="1"/>
                                    <rect x="1" y="7" width="14" height="3" rx="1"/>
                                    <rect x="1" y="12" width="14" height="3" rx="1"/>
                                </svg>
                            </button>
                        </div>
                        
                        <button id="btn-clear-filters" class="btn-clear-filters" title="Clear All Filters">
                            <span>✕</span> Clear
                        </button>
                    </div>
                </div>
                
                <!-- Filter Dropdowns (hidden by default) -->
                <div id="filter-dropdown-ecosystem" class="filter-dropdown" style="display: none;">
                    <div class="dropdown-header">Select Ecosystems</div>
                    <div class="dropdown-options" id="ecosystem-options">
                        <!-- Options will be populated dynamically -->
                    </div>
                    <div class="dropdown-footer">
                        <button class="dropdown-apply-btn" data-filter="ecosystem">Apply</button>
                        <button class="dropdown-clear-btn" data-filter="ecosystem">Clear</button>
                    </div>
                </div>
                
                <div id="filter-dropdown-type" class="filter-dropdown" style="display: none;">
                    <div class="dropdown-header">Select Types</div>
                    <div class="dropdown-options" id="type-options">
                        <!-- Options will be populated dynamically -->
                    </div>
                    <div class="dropdown-footer">
                        <button class="dropdown-apply-btn" data-filter="type">Apply</button>
                        <button class="dropdown-clear-btn" data-filter="type">Clear</button>
                    </div>
                </div>
                
                <!-- Resource Stats Bar -->
                <div class="resource-stats-bar">
                    <span id="resource-count" class="stat-item">
                        <span class="stat-icon">📊</span>
                        <span class="stat-value">0</span> resources
                    </span>
                    <span id="filter-status" class="stat-item filter-active" style="display: none;">
                        <span class="stat-icon">🔍</span>
                        Filtered results
                    </span>
                </div>
                
                <div class="resource-content">
                    <div id="resource-grid" class="resource-grid view-grid">
                        <div class="loading">Loading resources...</div>
                    </div>
                    <div id="resource-preview-pane" class="resource-preview-pane" style="display: none;">
                        <div class="preview-close" id="preview-close">✕</div>
                        <div id="preview-content" class="preview-content">
                        </div>
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
        
        // Add download status container to UI
        const footer = this.container.querySelector('.resource-footer');
        const statusDiv = document.createElement('div');
        statusDiv.id = 'download-status-container';
        statusDiv.className = 'download-status-container';
        footer.parentNode.insertBefore(statusDiv, footer.nextSibling);
        
        // Setup lazy loading observer
        this._setupLazyLoading();
        
        // Attach event listeners
        this._attachEventListeners();
        
        // Load filter options and resources
        await this._loadFilterOptions();
        await this.loadResources();
    }
    
    /**
     * Setup lazy loading for media elements using Intersection Observer
     */
    _setupLazyLoading() {
        if ('IntersectionObserver' in window) {
            this.lazyLoadObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const element = entry.target;
                        if (element.dataset.src) {
                            element.src = element.dataset.src;
                            element.removeAttribute('data-src');
                            element.classList.add('loaded');
                        }
                        observer.unobserve(element);
                    }
                });
            }, {
                rootMargin: `${TILE_VIEWER_CONFIG.lazyLoadThreshold}px`
            });
        }
    }
    
    /**
     * Attach event listeners to UI elements
     */
    _attachEventListeners() {
        const searchInput = document.getElementById('filter-search');
        const clearFiltersBtn = document.getElementById('btn-clear-filters');
        const clearSelectionBtn = document.getElementById('btn-clear-selection');
        const installBtn = document.getElementById('btn-install-selected');
        const sortSelect = document.getElementById('sort-select');
        
        // Filter pill click handlers
        const ecosystemPill = this.container.querySelector('.filter-pill-ecosystem');
        const typePill = this.container.querySelector('.filter-pill-type');
        
        if (ecosystemPill) {
            ecosystemPill.addEventListener('click', (e) => {
                e.stopPropagation();
                this._toggleFilterDropdown('ecosystem');
            });
        }
        
        if (typePill) {
            typePill.addEventListener('click', (e) => {
                e.stopPropagation();
                this._toggleFilterDropdown('type');
            });
        }
        
        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.filter-dropdown') && !e.target.closest('.filter-pill')) {
                this._closeAllDropdowns();
            }
        });
        
        // Dropdown apply/clear button handlers
        this.container.querySelectorAll('.dropdown-apply-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const filterType = btn.dataset.filter;
                this._applyFilterSelection(filterType);
            });
        });
        
        this.container.querySelectorAll('.dropdown-clear-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const filterType = btn.dataset.filter;
                this._clearFilterSelection(filterType);
            });
        });
        
        // Sort change handler
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                this.sortBy = e.target.value;
                this._sortAndRenderResources();
            });
        }
        
        // View toggle handlers
        const viewButtons = this.container.querySelectorAll('.view-btn');
        viewButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const view = btn.dataset.view;
                this._setViewMode(view);
            });
        });
        
        // Debounce search input
        let searchTimeout;
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.filters.search = e.target.value;
                    this.loadResources();
                }, 300);
            });
        }
        
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', () => {
                this.clearFilters();
            });
        }
        
        if (clearSelectionBtn) {
            clearSelectionBtn.addEventListener('click', () => {
                this.clearSelection();
            });
        }
        
        if (installBtn) {
            installBtn.addEventListener('click', () => {
                this.installSelected();
            });
        }
        
        // Preview pane close button
        const previewClose = document.getElementById('preview-close');
        if (previewClose) {
            previewClose.addEventListener('click', () => {
                this.closePreview();
            });
        }
        
        // Set instance ID for download status polling
        const sshInput = document.getElementById('resourcesSshConnectionString');
        if (sshInput) {
            sshInput.addEventListener('change', (e) => {
                const instanceId = this._extractInstanceId(e.target.value);
                // Don't auto-start polling, wait for user to click refresh
                this.downloadStatus.instanceId = instanceId;
            });
            // Store initial value if present, but don't start polling
            if (sshInput.value) {
                const instanceId = this._extractInstanceId(sshInput.value);
                this.downloadStatus.instanceId = instanceId;
            }
        }
        
        // Add refresh button handler
        const refreshBtn = document.getElementById('btn-refresh-downloads');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                const sshInput = document.getElementById('resourcesSshConnectionString');
                let instanceId = this.downloadStatus.instanceId;
                
                // Try to get instance ID from SSH input if not already set
                if (!instanceId && sshInput && sshInput.value) {
                    instanceId = this._extractInstanceId(sshInput.value);
                }
                
                // Set instance ID if available (can be null for local downloads)
                if (instanceId) {
                    this.downloadStatus.setInstanceId(instanceId);
                } else {
                    // Start polling even without instance ID to show local downloads
                    this.downloadStatus.startPolling();
                }
            });
        }
    }
    
    /**
     * Toggle filter dropdown visibility
     */
    _toggleFilterDropdown(filterType) {
        const dropdown = document.getElementById(`filter-dropdown-${filterType}`);
        const pill = this.container.querySelector(`.filter-pill-${filterType}`);
        
        if (!dropdown) return;
        
        const isVisible = dropdown.style.display !== 'none';
        
        // Close all dropdowns first
        this._closeAllDropdowns();
        
        if (!isVisible) {
            // Position dropdown below the pill
            const pillRect = pill.getBoundingClientRect();
            const containerRect = this.container.getBoundingClientRect();
            
            dropdown.style.display = 'block';
            dropdown.style.position = 'absolute';
            dropdown.style.left = `${pillRect.left - containerRect.left}px`;
            dropdown.style.top = `${pillRect.bottom - containerRect.top + 4}px`;
            
            pill.classList.add('active');
        }
    }
    
    /**
     * Close all filter dropdowns
     */
    _closeAllDropdowns() {
        const dropdowns = this.container.querySelectorAll('.filter-dropdown');
        const pills = this.container.querySelectorAll('.filter-pill');
        
        dropdowns.forEach(d => d.style.display = 'none');
        pills.forEach(p => p.classList.remove('active'));
    }
    
    /**
     * Apply filter selection from checkboxes
     */
    _applyFilterSelection(filterType) {
        const optionsContainer = document.getElementById(`${filterType}-options`);
        if (!optionsContainer) return;
        
        const checkedBoxes = optionsContainer.querySelectorAll('input[type="checkbox"]:checked');
        const selectedValues = Array.from(checkedBoxes).map(cb => cb.value);
        
        if (filterType === 'ecosystem') {
            this.filters.ecosystems = selectedValues;
        } else if (filterType === 'type') {
            this.filters.types = selectedValues;
        }
        
        this._updatePillValue(filterType, selectedValues);
        this._closeAllDropdowns();
        this.loadResources();
    }
    
    /**
     * Clear filter selection
     */
    _clearFilterSelection(filterType) {
        const optionsContainer = document.getElementById(`${filterType}-options`);
        if (optionsContainer) {
            optionsContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                cb.checked = false;
            });
        }
        
        if (filterType === 'ecosystem') {
            this.filters.ecosystems = [];
        } else if (filterType === 'type') {
            this.filters.types = [];
        }
        
        this._updatePillValue(filterType, []);
        this._closeAllDropdowns();
        this.loadResources();
    }
    
    /**
     * Update pill display value (supports multiple selections)
     */
    _updatePillValue(filterType, values) {
        const pill = this.container.querySelector(`.filter-pill-${filterType}`);
        if (!pill) return;
        
        const valueSpan = pill.querySelector('.pill-value');
        if (valueSpan) {
            if (Array.isArray(values)) {
                if (values.length === 0) {
                    valueSpan.textContent = 'All';
                } else if (values.length === 1) {
                    valueSpan.textContent = values[0].toUpperCase();
                } else {
                    valueSpan.textContent = `${values.length} selected`;
                }
            } else {
                valueSpan.textContent = values ? values.toUpperCase() : 'All';
            }
        }
        
        // Add/remove has-value class
        const hasValue = Array.isArray(values) ? values.length > 0 : !!values;
        if (hasValue) {
            pill.classList.add('has-value');
        } else {
            pill.classList.remove('has-value');
        }
    }
    
    /**
     * Set view mode (grid or list)
     */
    _setViewMode(mode) {
        this.viewMode = mode;
        const grid = document.getElementById('resource-grid');
        
        // Update grid class
        if (grid) {
            grid.classList.remove('view-grid', 'view-list');
            grid.classList.add(`view-${mode}`);
        }
        
        // Update button states
        const viewButtons = this.container.querySelectorAll('.view-btn');
        viewButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === mode);
        });
    }
    
    /**
     * Sort resources and re-render
     */
    _sortAndRenderResources() {
        const sortConfig = TILE_VIEWER_CONFIG.sortOptions.find(opt => opt.value === this.sortBy);
        if (!sortConfig) return;
        
        // Handle empty resources array
        if (this.resources.length === 0) {
            this.renderResources([]);
            return;
        }
        
        const sorted = [...this.resources].sort((a, b) => {
            let aVal, bVal;
            
            switch (sortConfig.field) {
                case 'title':
                    aVal = (a.metadata.title || this._extractTitle(a.description)).toLowerCase();
                    bVal = (b.metadata.title || this._extractTitle(b.description)).toLowerCase();
                    break;
                case 'type':
                    aVal = (a.metadata.type || '').toLowerCase();
                    bVal = (b.metadata.type || '').toLowerCase();
                    break;
                case 'size':
                    aVal = a.metadata.size || 0;
                    bVal = b.metadata.size || 0;
                    break;
                case 'published':
                    aVal = a.metadata.published ? new Date(a.metadata.published).getTime() : 0;
                    bVal = b.metadata.published ? new Date(b.metadata.published).getTime() : 0;
                    break;
                default:
                    return 0;
            }
            
            if (aVal < bVal) return sortConfig.order === 'asc' ? -1 : 1;
            if (aVal > bVal) return sortConfig.order === 'asc' ? 1 : -1;
            return 0;
        });
        
        this.renderResources(sorted);
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
                const optionsContainer = document.getElementById('ecosystem-options');
                if (optionsContainer) {
                    optionsContainer.innerHTML = ''; // Clear existing options
                    ecosystems.ecosystems.forEach(eco => {
                        const label = document.createElement('label');
                        label.className = 'dropdown-option';
                        label.innerHTML = `
                            <input type="checkbox" name="ecosystem" value="${eco}">
                            <span>${eco.toUpperCase()}</span>
                        `;
                        optionsContainer.appendChild(label);
                    });
                }
            }
            
            if (types.success) {
                const optionsContainer = document.getElementById('type-options');
                if (optionsContainer) {
                    optionsContainer.innerHTML = ''; // Clear existing options
                    types.types.forEach(type => {
                        const label = document.createElement('label');
                        label.className = 'dropdown-option';
                        label.innerHTML = `
                            <input type="checkbox" name="type" value="${type}">
                            <span>${type.charAt(0).toUpperCase() + type.slice(1)}</span>
                        `;
                        optionsContainer.appendChild(label);
                    });
                }
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
        grid.innerHTML = '<div class="loading"><span class="loading-spinner"></span>Loading resources...</div>';
        
        try {
            const params = new URLSearchParams();
            // Support multiple ecosystem selections
            if (this.filters.ecosystems && this.filters.ecosystems.length > 0) {
                this.filters.ecosystems.forEach(eco => params.append('ecosystem', eco));
            }
            // Support multiple type selections
            if (this.filters.types && this.filters.types.length > 0) {
                this.filters.types.forEach(type => params.append('type', type));
            }
            if (this.filters.search) params.append('search', this.filters.search);
            
            const response = await window.api.get(`/resources/list?${params}`);
            
            if (response.success) {
                this.resources = response.resources;
                this._updateResourceCount(response.resources.length);
                this._updateFilterStatus();
                this._sortAndRenderResources();
            } else {
                grid.innerHTML = `<div class="error">Error: ${response.message}</div>`;
            }
        } catch (error) {
            console.error('Error loading resources:', error);
            grid.innerHTML = '<div class="error">Failed to load resources</div>';
        }
    }
    
    /**
     * Update resource count display
     */
    _updateResourceCount(count) {
        const countEl = document.getElementById('resource-count');
        if (countEl) {
            const valueSpan = countEl.querySelector('.stat-value');
            if (valueSpan) {
                valueSpan.textContent = count;
            }
        }
    }
    
    /**
     * Update filter status indicator
     */
    _updateFilterStatus() {
        const statusEl = document.getElementById('filter-status');
        if (statusEl) {
            const hasFilters = (this.filters.ecosystems && this.filters.ecosystems.length > 0) || 
                               (this.filters.types && this.filters.types.length > 0) || 
                               this.filters.search;
            statusEl.style.display = hasFilters ? 'inline-flex' : 'none';
        }
    }
    
    /**
     * Render resources in grid
     */
    renderResources(resources) {
        const grid = document.getElementById('resource-grid');
        grid.innerHTML = '';
        
        if (resources.length === 0) {
            grid.innerHTML = `
                <div class="no-results">
                    <span class="no-results-icon">📭</span>
                    <span class="no-results-text">No resources found</span>
                    <span class="no-results-hint">Try adjusting your filters or search query</span>
                </div>
            `;
            return;
        }
        
        resources.forEach(resource => {
            const card = createResourceCard(resource, this.viewMode);
            
            // Update selection state if already selected
            if (this.selectedResources.has(resource.filepath)) {
                updateCardSelection(card, true);
            }
            
            // Setup lazy loading for media (images and videos)
            if (this.lazyLoadObserver) {
                const mediaElements = card.querySelectorAll('[data-src]');
                mediaElements.forEach(el => this.lazyLoadObserver.observe(el));
            }
            
            // Setup video hover autoplay
            if (TILE_VIEWER_CONFIG.autoplayVideos) {
                const video = card.querySelector('video');
                if (video) {
                    this._setupVideoAutoplay(card, video);
                }
            }
            
            grid.appendChild(card);
        });
    }
    
    /**
     * Setup video autoplay on hover
     */
    _setupVideoAutoplay(card, video) {
        let hoverTimeout;
        
        card.addEventListener('mouseenter', () => {
            hoverTimeout = setTimeout(() => {
                video.play().catch(err => {
                    // Log autoplay failures (often due to browser policies)
                    console.warn('Video autoplay failed:', err.message);
                });
            }, TILE_VIEWER_CONFIG.videoHoverDelay);
        });
        
        card.addEventListener('mouseleave', () => {
            clearTimeout(hoverTimeout);
            video.pause();
            video.currentTime = 0;
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
        
        // Check if we're on mobile (viewport width < 768px)
        const isMobile = window.innerWidth < 768;
        
        if (isMobile) {
            // Mobile: Use inline expansion with 4:3 aspect ratio
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
        } else {
            // Desktop: Use preview pane on the right
            this.showPreview(filepath);
        }
    }
    
    /**
     * Show resource preview in the desktop preview pane
     */
    showPreview(filepath) {
        const resource = this.resources.find(r => r.filepath === filepath);
        if (!resource) return;
        
        const previewPane = document.getElementById('resource-preview-pane');
        const previewContent = document.getElementById('preview-content');
        
        if (!previewPane || !previewContent) return;
        
        // Get resource details
        const metadata = resource.metadata;
        const title = this._extractTitle(resource.description);
        const imagePath = metadata.image || 'placeholder.png';
        const sizeStr = metadata.size ? this._formatBytes(metadata.size) : null;
        const hasDeps = metadata.dependencies && metadata.dependencies.length > 0;
        
        // Extract description
        const descLines = resource.description.split('\n').filter(l => l.trim());
        let fullDesc = '';
        for (let i = 0; i < descLines.length; i++) {
            if (!descLines[i].startsWith('#')) {
                fullDesc += descLines[i] + '\n';
            }
        }
        
        const isSelected = this.selectedResources.has(filepath);
        
        // Build preview HTML
        previewContent.innerHTML = `
            <div class="preview-header">
                <div class="preview-thumbnail">
                    <img src="/resources/images/${imagePath}" 
                         alt="${title}"
                         onerror="this.style.display='none'; this.parentElement.style.background='linear-gradient(135deg, #667eea 0%, #764ba2 100%)'; this.onerror=null;">
                </div>
            </div>
            <div class="preview-body">
                <h3 class="preview-title">${title}</h3>
                <div class="preview-tags">
                    <span class="tag tag-ecosystem">${metadata.ecosystem}</span>
                    <span class="tag tag-type">${metadata.type}</span>
                </div>
                ${fullDesc ? `<p class="preview-description">${fullDesc}</p>` : ''}
                ${sizeStr ? `<div class="preview-meta">📦 Size: ${sizeStr}</div>` : ''}
                ${hasDeps ? `<div class="preview-meta">⚠ ${metadata.dependencies.length} dependencies</div>` : ''}
                ${metadata.author ? `<div class="preview-meta">👤 Author: ${metadata.author}</div>` : ''}
                ${metadata.version ? `<div class="preview-meta">🏷 Version: ${metadata.version}</div>` : ''}
            </div>
            <div class="preview-footer">
                <button class="btn-select-preview ${isSelected ? 'selected' : ''}" 
                        data-filepath="${filepath}">
                    ${isSelected ? '☑ Selected' : '☐ Select'}
                </button>
            </div>
        `;
        
        // Show the preview pane
        previewPane.style.display = 'block';
        
        // Add event listener to select button
        const selectBtn = previewContent.querySelector('.btn-select-preview');
        if (selectBtn) {
            selectBtn.addEventListener('click', () => {
                this.toggleSelection(filepath);
                // Update button state
                const isNowSelected = this.selectedResources.has(filepath);
                selectBtn.className = `btn-select-preview ${isNowSelected ? 'selected' : ''}`;
                selectBtn.textContent = isNowSelected ? '☑ Selected' : '☐ Select';
            });
        }
    }
    
    /**
     * Close the preview pane
     */
    closePreview() {
        const previewPane = document.getElementById('resource-preview-pane');
        if (previewPane) {
            previewPane.style.display = 'none';
        }
    }
    
    /**
     * Helper: Extract title from description
     */
    _extractTitle(description) {
        const match = description.match(/^#\s+(.+)$/m);
        return match ? match[1] : 'Untitled Resource';
    }
    
    /**
     * Helper: Format bytes to human-readable
     */
    _formatBytes(bytes) {
        if (!bytes || bytes === 0) return null;
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
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
            ecosystems: [],
            types: [],
            tags: [],
            search: ''
        };
        
        // Reset search input
        const searchInput = document.getElementById('filter-search');
        if (searchInput) searchInput.value = '';
        
        // Reset pill values
        this._updatePillValue('ecosystem', []);
        this._updatePillValue('type', []);
        
        // Reset checkboxes in dropdowns
        const ecosystemCheckboxes = document.querySelectorAll('input[name="ecosystem"]');
        const typeCheckboxes = document.querySelectorAll('input[name="type"]');
        
        ecosystemCheckboxes.forEach(cb => {
            cb.checked = false;
        });
        
        typeCheckboxes.forEach(cb => {
            cb.checked = false;
        });
        
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
        const sshConnection = document.getElementById('resourcesSshConnectionString')?.value;
        
        if (!sshConnection) {
            alert('Please provide an SSH connection string first');
            return;
        }
        
        const installBtn = document.getElementById('btn-install-selected');
        const originalText = installBtn.textContent;
        installBtn.disabled = true;
        installBtn.textContent = 'Installing...';
        
        try {
            // Convert filepaths to resource objects with filepath property
            const resources = Array.from(this.selectedResources).map(filepath => ({
                filepath: filepath
            }));
            
            const response = await window.api.post('/downloads/queue', {
                ssh_connection: sshConnection,
                resources: resources,
                ui_home: '/workspace/ComfyUI'
            });
            
            if (response.success) {
                alert(`Successfully queued ${resources.length} resource(s) for installation!\n\nClick the 🔄 Refresh button to monitor progress.`);
                this.clearSelection();
                
                // Store instance ID but don't start polling - user must click refresh
                const instanceId = this._extractInstanceId(sshConnection);
                if (instanceId) this.downloadStatus.instanceId = instanceId;
            } else {
                alert(`Failed to queue downloads: ${response.message}`);
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
     * Extract instance ID from SSH connection string
     */
    _extractInstanceId(sshConnection) {
        // Example: ssh -p 44686 root@109.231.106.68 -L 8080:localhost:8080
        // Use IP as instance ID, replacing dots with underscores to match backend
        const match = sshConnection.match(/@([\d.]+)/);
        return match ? match[1].replace(/\./g, '_') : null;
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
