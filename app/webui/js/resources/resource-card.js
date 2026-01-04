/**
 * Resource Card Component
 * 
 * Creates a visual card representation for a resource (workflow, model, etc.)
 * Supports grid and list view modes with lazy loading
 */

/**
 * Format bytes to human-readable size
 */
function formatBytes(bytes) {
    if (!bytes || bytes === 0) return null;
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Extract title from resource description (first heading)
 */
function extractTitle(description) {
    const match = description.match(/^#\s+(.+)$/m);
    return match ? match[1] : 'Untitled Resource';
}

/**
 * Check if file is a video based on extension
 */
function isVideoFile(filename) {
    if (!filename) return false;
    const videoExtensions = ['.mp4', '.webm', '.ogg', '.mov'];
    return videoExtensions.some(ext => filename.toLowerCase().endsWith(ext));
}

/**
 * Handle image load error by hiding image and showing gradient background
 */
function handleImageError(img) {
    img.style.display = 'none';
    img.parentElement.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
}

/**
 * Create an image element with lazy loading and error handling
 */
function createImageElement(src, alt, useLazyLoading = true) {
    const srcAttr = useLazyLoading ? 'data-src' : 'src';
    return `<img class="resource-media" ${srcAttr}="${src}" alt="${alt}" loading="lazy" onerror="this.style.display='none'; this.parentElement.style.background='linear-gradient(135deg, #667eea 0%, #764ba2 100%)';">`;
}

/**
 * Create a video element with lazy loading support
 */
function createVideoElement(src, useLazyLoading = true) {
    const srcAttr = useLazyLoading ? 'data-src' : 'src';
    return `<video class="resource-media" muted loop playsinline ${srcAttr}="${src}" poster="/resources/images/video-placeholder.png"></video>`;
}

/**
 * Create a resource card element (compact with expand-on-tap)
 * @param {Object} resource - Resource object from API
 * @param {string} viewMode - 'grid' or 'list'
 * @returns {HTMLElement} Card element
 */
export function createResourceCard(resource, viewMode = 'grid') {
    const card = document.createElement('div');
    card.className = `resource-card resource-card-${viewMode}`;
    card.dataset.resourcePath = resource.filepath;
    
    const metadata = resource.metadata;
    const title = metadata.title || extractTitle(resource.description);
    
    // Extract short description (first paragraph after title)
    const descLines = resource.description.split('\n').filter(l => l.trim());
    let shortDesc = '';
    for (let i = 0; i < descLines.length; i++) {
        if (!descLines[i].startsWith('#')) {
            shortDesc = descLines[i];
            break;
        }
    }
    if (shortDesc.length > 150) {
        shortDesc = shortDesc.substring(0, 147) + '...';
    }
    
    // Build card HTML
    const imagePath = metadata.image || 'placeholder.png';
    const imageUrl = `/resources/images/${imagePath}`;
    const sizeStr = metadata.size ? formatBytes(metadata.size) : null;
    const hasDeps = metadata.dependencies && metadata.dependencies.length > 0;
    const isVideo = isVideoFile(imagePath);
    
    // Determine status badge
    const isSelected = window.resourceBrowser?.selectedResources?.has(resource.filepath);
    const statusBadge = isSelected ? 
        '<span class="status-badge status-selected">Selected</span>' : 
        '<span class="status-badge status-available">Available</span>';
    
    // Create media element with lazy loading support
    const mediaHtml = isVideo
        ? createVideoElement(imageUrl, true)
        : createImageElement(imageUrl, title, true);
    
    if (viewMode === 'list') {
        // List view layout
        card.innerHTML = `
            <div class="resource-card-list-layout">
                <div class="list-thumbnail">
                    ${mediaHtml}
                </div>
                <div class="list-content">
                    <div class="list-header">
                        <h3 class="list-title">${title}</h3>
                        ${statusBadge}
                    </div>
                    <div class="list-meta">
                        <span class="tag tag-ecosystem">${metadata.ecosystem}</span>
                        <span class="tag tag-type">${metadata.type}</span>
                        ${sizeStr ? `<span class="meta-size">📦 ${sizeStr}</span>` : ''}
                        ${hasDeps ? `<span class="meta-deps">⚠ ${metadata.dependencies.length} deps</span>` : ''}
                    </div>
                    ${shortDesc ? `<p class="list-description">${shortDesc}</p>` : ''}
                </div>
                <div class="list-actions">
                    <button class="btn-select" data-action="select">
                        <span class="icon">${isSelected ? '☑' : '☐'}</span>
                    </button>
                </div>
            </div>
        `;
    } else {
        // Grid view layout (split tile design)
        // Create expanded media HTML with src for immediate loading when expanded
        const expandedMediaHtml = isVideo
            ? createVideoElement(imageUrl, false)
            : createImageElement(imageUrl, title, false);
        
        card.innerHTML = `
            <div class="resource-card-tile">
                <div class="resource-card-compact">
                    <div class="compact-header">
                        <h3 class="compact-title">${title}</h3>
                    </div>
                    <div class="compact-meta">
                        <span class="compact-type">${metadata.type}</span>
                        <span class="compact-ecosystem">${metadata.ecosystem}</span>
                    </div>
                </div>
                <div class="resource-card-expanded" style="display: none;">
                    <div class="resource-card-header">
                        ${expandedMediaHtml}
                    </div>
                    <div class="resource-card-body">
                        <h3 class="resource-title">${title}</h3>
                        <div class="resource-tags">
                            <span class="tag tag-ecosystem">${metadata.ecosystem}</span>
                            <span class="tag tag-type">${metadata.type}</span>
                        </div>
                        ${shortDesc ? `<p class="resource-description">${shortDesc}</p>` : ''}
                        ${sizeStr ? `<div class="resource-size">Size: ${sizeStr}</div>` : ''}
                        ${hasDeps ? `<div class="resource-deps">⚠ ${metadata.dependencies.length} dependencies</div>` : ''}
                    </div>
                    <div class="resource-card-footer">
                        <button class="btn-select" data-action="select">
                            <span class="icon">☐</span> Select
                        </button>
                    </div>
                </div>
            </div>
            ${statusBadge}
        `;
    }
    
    // Add click listener to expand/collapse (only on tile)
    const cardTile = card.querySelector('.resource-card-tile');
    if (cardTile) {
        cardTile.addEventListener('click', (e) => {
            // Don't expand if clicking the select button
            if (e.target.closest('.btn-select')) {
                e.stopPropagation();
                window.resourceBrowser?.toggleSelection(resource.filepath);
                return;
            }
            
            window.resourceBrowser?.expandCard(resource.filepath);
        });
    }
    
    // Add status badge click listener for selection
    const statusBadge = card.querySelector('.status-badge');
    if (statusBadge) {
        statusBadge.addEventListener('click', (e) => {
            e.stopPropagation();
            window.resourceBrowser?.toggleSelection(resource.filepath);
        });
    }
    
    // Add select button listener in expanded view
    const selectBtn = card.querySelector('.btn-select');
    if (selectBtn) {
        selectBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            window.resourceBrowser?.toggleSelection(resource.filepath);
        });
    }
    
    return card;
}

/**
 * Update card selection state
 */
export function updateCardSelection(card, selected) {
    const selectBtn = card.querySelector('.btn-select');
    const icon = selectBtn?.querySelector('.icon');
    
    // Update compact view status badge
    const compactStatus = card.querySelector('.status-badge');
    if (compactStatus) {
        if (selected) {
            compactStatus.className = 'status-badge status-selected';
            compactStatus.textContent = 'Selected';
        } else {
            compactStatus.className = 'status-badge status-available';
            compactStatus.textContent = 'Available';
        }
    }
    
    // Update expanded view button
    if (selectBtn && icon) {
        if (selected) {
            card.classList.add('selected');
            icon.textContent = '☑';
            selectBtn.textContent = '';
            selectBtn.appendChild(icon);
            selectBtn.append(' Selected');
        } else {
            card.classList.remove('selected');
            icon.textContent = '☐';
            selectBtn.textContent = '';
            selectBtn.appendChild(icon);
            selectBtn.append(' Select');
        }
    }
}

/**
 * Expand a card to show full details
 */
export function expandCard(card) {
    const compact = card.querySelector('.resource-card-compact');
    const expanded = card.querySelector('.resource-card-expanded');
    
    if (compact && expanded) {
        compact.style.display = 'none';
        expanded.style.display = 'block';
        card.classList.add('expanded');
    }
}

/**
 * Collapse a card to compact view
 */
export function collapseCard(card) {
    const compact = card.querySelector('.resource-card-compact');
    const expanded = card.querySelector('.resource-card-expanded');
    
    if (compact && expanded) {
        compact.style.display = 'block';
        expanded.style.display = 'none';
        card.classList.remove('expanded');
    }
}
