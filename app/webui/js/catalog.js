/**
 * Asset Catalog
 * 
 * Browse and view the complete library of assets with category filtering
 */

// State management
let catalogState = {
    assets: [],
    selectedCategory: 'all',
    loading: false
};

/**
 * Initialize the catalog when the page loads
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing Asset Catalog');
    
    // Set up event listeners
    const categorySelect = document.getElementById('catalog-category-select');
    if (categorySelect) {
        categorySelect.addEventListener('change', handleCategoryChange);
        
        // Load saved category from server or localStorage
        loadSavedCategory();
    }
    
    // Load assets when catalog tab is opened
    const catalogTab = document.getElementById('catalog-tab');
    if (catalogTab) {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                    if (catalogTab.classList.contains('active') && catalogState.assets.length === 0) {
                        loadAssets();
                    }
                }
            });
        });
        
        observer.observe(catalogTab, { attributes: true });
        
        // Store observer for cleanup
        catalogState.observer = observer;
    }
});

/**
 * Cleanup function (can be called when needed)
 */
function cleanupCatalog() {
    if (catalogState.observer) {
        catalogState.observer.disconnect();
        catalogState.observer = null;
    }
}

/**
 * Load saved category preference
 */
async function loadSavedCategory() {
    try {
        // Try to load from server first
        const response = await fetch('/catalog/state');
        if (response.ok) {
            const state = await response.json();
            if (state.selectedCategory) {
                catalogState.selectedCategory = state.selectedCategory;
                document.getElementById('catalog-category-select').value = state.selectedCategory;
            }
        }
    } catch (error) {
        console.log('Could not load saved category from server, using localStorage');
        // Fallback to localStorage
        const savedCategory = localStorage.getItem('catalog-selected-category');
        if (savedCategory) {
            catalogState.selectedCategory = savedCategory;
            document.getElementById('catalog-category-select').value = savedCategory;
        }
    }
}

/**
 * Save category preference
 */
async function saveCategoryPreference(category) {
    // Save to localStorage
    localStorage.setItem('catalog-selected-category', category);
    
    // Try to save to server
    try {
        await fetch('/catalog/state', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ selectedCategory: category })
        });
    } catch (error) {
        console.log('Could not save category to server:', error);
    }
}

/**
 * Handle category dropdown change
 */
function handleCategoryChange(event) {
    const category = event.target.value;
    catalogState.selectedCategory = category;
    saveCategoryPreference(category);
    filterAssets();
}

/**
 * Load assets from the API
 */
async function loadAssets() {
    if (catalogState.loading) return;
    
    catalogState.loading = true;
    const gridContainer = document.getElementById('catalog-grid');
    
    try {
        console.log('Loading assets from API...');
        const response = await fetch('/resources/list');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        catalogState.assets = data.resources || [];
        
        console.log(`Loaded ${catalogState.assets.length} assets`);
        
        // Display assets
        filterAssets();
        
    } catch (error) {
        console.error('Error loading assets:', error);
        gridContainer.innerHTML = `
            <div class="catalog-error">
                <div class="error-icon">⚠️</div>
                <h3>Failed to load assets</h3>
                <p>${error.message}</p>
                <button class="retry-button" onclick="loadAssets()">Retry</button>
            </div>
        `;
    } finally {
        catalogState.loading = false;
    }
}

/**
 * Filter and display assets based on selected category
 */
function filterAssets() {
    const category = catalogState.selectedCategory;
    let filteredAssets = catalogState.assets;
    
    // Filter by category
    if (category !== 'all') {
        filteredAssets = catalogState.assets.filter(asset => 
            asset.metadata && asset.metadata.type === category
        );
    }
    
    // Update count
    const countEl = document.getElementById('catalog-count');
    if (countEl) {
        countEl.textContent = `${filteredAssets.length} asset${filteredAssets.length !== 1 ? 's' : ''}`;
    }
    
    // Render assets
    renderAssets(filteredAssets);
}

/**
 * Render assets in the grid
 */
function renderAssets(assets) {
    const gridContainer = document.getElementById('catalog-grid');
    
    if (assets.length === 0) {
        gridContainer.innerHTML = `
            <div class="catalog-empty">
                <div class="empty-icon">📭</div>
                <h3>No assets found</h3>
                <p>Try selecting a different category</p>
            </div>
        `;
        return;
    }
    
    // Create asset tiles
    const tilesHTML = assets.map(asset => createAssetTile(asset)).join('');
    gridContainer.innerHTML = tilesHTML;
    
    // Add click handlers
    assets.forEach((asset, index) => {
        const tile = gridContainer.children[index];
        if (tile) {
            tile.addEventListener('click', () => showAssetDetail(asset));
        }
    });
}

/**
 * Create HTML for an asset tile
 */
function createAssetTile(asset) {
    const metadata = asset.metadata || {};
    const title = metadata.title || asset.filename || 'Untitled';
    const type = metadata.type || 'unknown';
    const ecosystem = metadata.ecosystem || 'other';
    const version = metadata.version || '';
    const size = formatSize(metadata.size);
    const image = metadata.image ? `/resources/images/${metadata.image}` : null;
    
    // Type emoji mapping
    const typeEmoji = {
        checkpoint: '🎯',
        lora: '✨',
        vae: '🔧',
        upscaler: '📐',
        workflow: '🔄'
    };
    
    // Ecosystem color mapping
    const ecosystemColors = {
        wan: '#00f5ff',
        flux: '#ff00ff',
        ltxv: '#00ff88',
        sd15: '#bf00ff',
        sdxl: '#ff6600',
        realesrgan: '#ff0099',
        other: '#a0a0a0'
    };
    
    const emoji = typeEmoji[type] || '📦';
    const color = ecosystemColors[ecosystem] || ecosystemColors.other;
    
    return `
        <div class="catalog-tile" data-type="${type}" data-ecosystem="${ecosystem}">
            ${image ? `
                <div class="catalog-tile-image" style="background-image: url('${image}')">
                    <div class="catalog-tile-badge" style="background: ${color}">
                        ${emoji} ${type}
                    </div>
                </div>
            ` : `
                <div class="catalog-tile-placeholder" style="border-color: ${color}">
                    <div class="catalog-tile-emoji">${emoji}</div>
                    <div class="catalog-tile-badge" style="background: ${color}">
                        ${type}
                    </div>
                </div>
            `}
            <div class="catalog-tile-content">
                <h3 class="catalog-tile-title">${escapeHtml(title)}</h3>
                <div class="catalog-tile-meta">
                    <span class="catalog-tile-ecosystem" style="color: ${color}">
                        ${ecosystem.toUpperCase()}
                    </span>
                    ${version ? `<span class="catalog-tile-version">${escapeHtml(version)}</span>` : ''}
                </div>
                ${size ? `<div class="catalog-tile-size">${size}</div>` : ''}
            </div>
        </div>
    `;
}

/**
 * Show asset detail modal
 */
async function showAssetDetail(asset) {
    const modal = document.getElementById('assetDetailModal');
    const title = document.getElementById('assetModalTitle');
    const content = document.getElementById('assetModalContent');
    
    const metadata = asset.metadata || {};
    const assetTitle = metadata.title || asset.filename || 'Asset Details';
    
    title.textContent = assetTitle;
    
    // Show loading state
    content.innerHTML = `
        <div class="loading-container">
            <div class="loading-spinner"></div>
            <p>Loading details...</p>
        </div>
    `;
    
    modal.style.display = 'flex';
    
    try {
        // Fetch full asset details including markdown description
        const response = await fetch(`/resources/get/${encodeURIComponent(asset.filepath)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const fullAsset = await response.json();
        
        // Render asset details
        renderAssetDetail(fullAsset);
        
    } catch (error) {
        console.error('Error loading asset details:', error);
        content.innerHTML = `
            <div class="error-container">
                <div class="error-icon">⚠️</div>
                <h3>Failed to load details</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

/**
 * Render asset detail in modal
 */
function renderAssetDetail(asset) {
    const content = document.getElementById('assetModalContent');
    const metadata = asset.metadata || {};
    
    // Format metadata display
    const metadataHTML = `
        <div class="asset-metadata">
            ${metadata.type ? `<div class="meta-item"><strong>Type:</strong> ${escapeHtml(metadata.type)}</div>` : ''}
            ${metadata.ecosystem ? `<div class="meta-item"><strong>Ecosystem:</strong> ${escapeHtml(metadata.ecosystem)}</div>` : ''}
            ${metadata.basemodel ? `<div class="meta-item"><strong>Base Model:</strong> ${escapeHtml(metadata.basemodel)}</div>` : ''}
            ${metadata.version ? `<div class="meta-item"><strong>Version:</strong> ${escapeHtml(metadata.version)}</div>` : ''}
            ${metadata.size ? `<div class="meta-item"><strong>Size:</strong> ${formatSize(metadata.size)}</div>` : ''}
            ${metadata.creator ? `<div class="meta-item"><strong>Creator:</strong> ${escapeHtml(metadata.creator)}</div>` : ''}
            ${metadata.license ? `<div class="meta-item"><strong>License:</strong> ${escapeHtml(metadata.license)}</div>` : ''}
            ${metadata.published ? `<div class="meta-item"><strong>Published:</strong> ${metadata.published}</div>` : ''}
        </div>
    `;
    
    // Format description (convert markdown to basic HTML)
    const descriptionHTML = asset.description ? 
        `<div class="asset-description">${formatMarkdown(asset.description)}</div>` : 
        '<p>No description available.</p>';
    
    // Show download command
    const downloadHTML = asset.download_command ? 
        `<div class="asset-download">
            <h4>Download Command</h4>
            <pre class="download-command"><code>${escapeHtml(asset.download_command)}</code></pre>
        </div>` : '';
    
    content.innerHTML = `
        ${metadataHTML}
        ${descriptionHTML}
        ${downloadHTML}
    `;
}

/**
 * Close asset detail modal
 */
function closeAssetDetailModal() {
    const modal = document.getElementById('assetDetailModal');
    modal.style.display = 'none';
}

// Make function globally available
window.closeAssetDetailModal = closeAssetDetailModal;

/**
 * Format file size in human-readable format
 */
function formatSize(bytes) {
    if (!bytes || bytes === 0) return '';
    
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const k = 1024;
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${units[i]}`;
}

/**
 * Basic markdown to HTML conversion
 */
function formatMarkdown(markdown) {
    let html = markdown;
    
    // Convert headers
    html = html.replace(/^### (.*$)/gim, '<h4>$1</h4>');
    html = html.replace(/^## (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^# (.*$)/gim, '<h2>$1</h2>');
    
    // Convert lists
    html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
    html = html.replace(/(<li>[\s\S]*?<\/li>)/gim, '<ul>$1</ul>');
    
    // Convert bold
    html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
    
    // Convert italic
    html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');
    
    // Convert inline code
    html = html.replace(/`(.*?)`/gim, '<code>$1</code>');
    
    // Convert links
    html = html.replace(/\[(.*?)\]\((.*?)\)/gim, '<a href="$2" target="_blank">$1</a>');
    
    // Convert line breaks
    html = html.replace(/\n\n/g, '</p><p>');
    html = `<p>${html}</p>`;
    
    return html;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
