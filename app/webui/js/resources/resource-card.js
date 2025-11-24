/**
 * Resource Card Component
 * 
 * Creates a visual card representation for a resource (workflow, model, etc.)
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
 * Create a resource card element (compact with expand-on-tap)
 * @param {Object} resource - Resource object from API
 * @returns {HTMLElement} Card element
 */
export function createResourceCard(resource) {
    const card = document.createElement('div');
    card.className = 'resource-card';
    card.dataset.resourcePath = resource.filepath;
    
    const metadata = resource.metadata;
    const title = extractTitle(resource.description);
    
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
    const sizeStr = metadata.size ? formatBytes(metadata.size) : null;
    const hasDeps = metadata.dependencies && metadata.dependencies.length > 0;
    
    // Determine status badge
    const isSelected = window.resourceBrowser?.selectedResources?.has(resource.filepath);
    const statusBadge = isSelected ? 
        '<span class="status-badge status-selected">Selected</span>' : 
        '<span class="status-badge status-available">Available</span>';
    
    card.innerHTML = `
        <div class="resource-card-compact">
            <div class="compact-header">
                <h3 class="compact-title">${title}</h3>
                ${statusBadge}
            </div>
            <div class="compact-meta">
                <span class="compact-type">${metadata.type}</span>
                <span class="compact-ecosystem">${metadata.ecosystem}</span>
            </div>
        </div>
        <div class="resource-card-expanded" style="display: none;">
            <div class="resource-card-header">
                <img src="/resources/images/${imagePath}" 
                     alt="${title}"
                     class="resource-thumbnail"
                     onerror="this.src='/resources/images/placeholder.png'">
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
    `;
    
    // Add click listener to expand/collapse
    card.addEventListener('click', (e) => {
        // Don't expand if clicking the select button
        if (e.target.closest('.btn-select')) {
            e.stopPropagation();
            window.resourceBrowser?.toggleSelection(resource.filepath);
            return;
        }
        
        // Toggle selection if clicking the status badge
        if (e.target.closest('.status-badge')) {
            e.stopPropagation();
            window.resourceBrowser?.toggleSelection(resource.filepath);
            return;
        }
        
        window.resourceBrowser?.expandCard(resource.filepath);
    });
    
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
