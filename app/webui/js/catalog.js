/**
 * Asset Catalog (TileView-style with Callout Filters)
 *
 * - Category selection via radio buttons in callout filter panel
 * - Apply/Reset buttons for filter changes
 * - Sort controls (field and order)
 * - Tile grid based on TileView.md concepts
 * - Click tile opens rendered markdown in a popover
 */

const CATEGORIES = [
    { key: 'checkpoints', label: 'Checkpoints' },
    { key: 'loras', label: 'LoRAs' },
    { key: 'encoders', label: 'Encoders' },
    { key: 'embeddings', label: 'Embeddings' },
    { key: 'upscalers', label: 'Upscalers' },
    { key: 'adetailers', label: 'ADetailers' },
    { key: 'workflows', label: 'Workflows' }
];

// Badge configuration - define what badges to show and where
const BADGE_CONFIG = {
    badges: [
        { field: 'type', corner: 'tr', order: 0, styleMapKey: 'type' },
        { field: 'basemodel', corner: 'tr', order: 1 },
        { field: 'ecosystem', corner: 'tl', order: 0, styleMapKey: 'ecosystem' },
    ],
    cornerStack: { tl: 'down', tr: 'down', bl: 'up', br: 'up' },
    badgeGap: 4,
    styleMaps: {
        type: {
            positive: { background: '#2196f3', color: '#fff' },
            negative: { background: '#f44336', color: '#fff' },
            checkpoint: { background: '#9c27b0', color: '#fff' },
            lora: { background: '#ff9800', color: '#fff' },
        },
        ecosystem: {
            sd15: { background: '#4caf50', color: '#fff' },
            sdxl: { background: '#00bcd4', color: '#fff' },
            flux: { background: '#e91e63', color: '#fff' },
            comfyui: { background: '#3f51b5', color: '#fff' },
        },
    },
};

const catalogState = {
    selectedCategory: 'checkpoints',
    items: [],
    allCards: [],
    loading: false,
    mediaObserver: null,
    playing: new Set(),
    maxConcurrentVideos: 2,
    sortField: 'title',
    sortOrder: 'asc',
    versionGroups: {}, // Map of base title -> array of items
    currentVersionIndex: {} // Map of card ID -> current version index
};

/**
 * Initialize the catalog when the page loads
 */
document.addEventListener('DOMContentLoaded', function() {
    initCatalog();
});

/**
 * Cleanup function (can be called when needed)
 */
function cleanupCatalog() {
    if (catalogState.mediaObserver) {
        catalogState.mediaObserver.disconnect();
        catalogState.mediaObserver = null;
    }
    for (const v of Array.from(catalogState.playing)) {
        try { v.pause(); } catch {}
    }
    catalogState.playing.clear();
}

function initCatalog() {
    setupCategoryFilters();
    setupSortControls();
    setupApplyResetButtons();
    loadSavedCategory().finally(() => {
        // Default if saved category is invalid
        if (!CATEGORIES.some(c => c.key === catalogState.selectedCategory)) {
            catalogState.selectedCategory = 'checkpoints';
        }
        loadCategory(catalogState.selectedCategory);
    });
}

/**
 * Setup category filter options (radio buttons)
 */
function setupCategoryFilters() {
    const container = document.getElementById('tv-category-options');
    if (!container) return;

    container.innerHTML = CATEGORIES.map(cat => `
        <label class="tv-filteroption">
            <input type="radio" name="catalog-category" value="${cat.key}" 
                   ${cat.key === catalogState.selectedCategory ? 'checked' : ''}>
            ${cat.label}
        </label>
    `).join('') + `
        <div class="tv-selection-links">
            <span class="tv-select-link" data-action="first">first</span>
        </div>
    `;

    // Add click handler for "first" link
    const firstLink = container.querySelector('[data-action="first"]');
    if (firstLink) {
        firstLink.addEventListener('click', () => {
            const firstRadio = container.querySelector('input[type="radio"]');
            if (firstRadio) firstRadio.checked = true;
        });
    }
}

/**
 * Setup sort controls
 */
function setupSortControls() {
    const sortField = document.getElementById('tv-sort-field');
    const sortOrder = document.getElementById('tv-sort-order');

    if (sortField) {
        sortField.value = catalogState.sortField;
        sortField.addEventListener('change', () => {
            catalogState.sortField = sortField.value;
            reSortAndRender();
        });
    }

    if (sortOrder) {
        sortOrder.value = catalogState.sortOrder;
        sortOrder.addEventListener('change', () => {
            catalogState.sortOrder = sortOrder.value;
            reSortAndRender();
        });
    }
}

/**
 * Setup Apply and Reset buttons
 */
function setupApplyResetButtons() {
    const applyBtn = document.getElementById('tv-apply');
    const resetBtn = document.getElementById('tv-reset');

    if (applyBtn) {
        applyBtn.addEventListener('click', () => {
            const selected = document.querySelector('input[name="catalog-category"]:checked');
            if (selected && selected.value !== catalogState.selectedCategory) {
                catalogState.selectedCategory = selected.value;
                saveCategoryPreference(catalogState.selectedCategory);
                loadCategory(catalogState.selectedCategory);
            }
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            // Reset to first category
            catalogState.selectedCategory = CATEGORIES[0].key;
            const firstRadio = document.querySelector('input[name="catalog-category"]');
            if (firstRadio) firstRadio.checked = true;
            
            // Reset sort
            catalogState.sortField = 'title';
            catalogState.sortOrder = 'asc';
            const sortField = document.getElementById('tv-sort-field');
            const sortOrder = document.getElementById('tv-sort-order');
            if (sortField) sortField.value = 'title';
            if (sortOrder) sortOrder.value = 'asc';

            saveCategoryPreference(catalogState.selectedCategory);
            loadCategory(catalogState.selectedCategory);
        });
    }
}

/**
 * Load saved category preference
 */
async function loadSavedCategory() {
    try {
        const savedCategory = localStorage.getItem('catalog-selected-category');
        if (savedCategory) {
            catalogState.selectedCategory = savedCategory;
            // Update the radio button
            const radio = document.querySelector(`input[name="catalog-category"][value="${savedCategory}"]`);
            if (radio) radio.checked = true;
        }
    } catch (error) {
        console.log('Could not load saved category:', error);
    }
}

/**
 * Save category preference
 */
async function saveCategoryPreference(category) {
    // Save to localStorage
    localStorage.setItem('catalog-selected-category', category);
}

async function loadCategory(categoryKey) {
    if (catalogState.loading) return;
    catalogState.loading = true;

    const grid = document.getElementById('catalog-grid');
    if (!grid) return;
    grid.innerHTML = `
        <div class="catalog-loading">
            <div class="loading-spinner"></div>
            <p>Loading assets…</p>
        </div>
    `;

    try {
        const resp = await fetch(`/catalog/list?category=${encodeURIComponent(categoryKey)}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        if (!data.success) throw new Error(data.message || 'Failed to load');
        catalogState.items = data.items || [];
        updateCount(catalogState.items.length);
        
        // Group items by base title (without version info)
        groupItemsByBaseTitle();
        
        // Setup media observer before creating cards
        setupMediaObserver();
        
        // Create cards: only one per version group (use first item in each group)
        const seenBaseTitles = new Set();
        catalogState.allCards = catalogState.items
            .map((item, index) => {
                const baseTitle = getBaseTitle(item);
                if (seenBaseTitles.has(baseTitle)) {
                    return null; // Skip duplicate versions
                }
                seenBaseTitles.add(baseTitle);
                return makeCard(item, `card-${baseTitle}`);
            })
            .filter(card => card !== null);
        
        reSortAndRender();
    } catch (e) {
        console.error('Catalog load error:', e);
        updateCount(0);
        grid.innerHTML = `
            <div class="catalog-error">
                <div class="error-icon">⚠️</div>
                <h3>Failed to load catalog</h3>
                <p>${String(e.message || e)}</p>
                <button class="retry-button" id="catalog-retry">Retry</button>
            </div>
        `;
        const retry = document.getElementById('catalog-retry');
        retry?.addEventListener('click', () => loadCategory(categoryKey));
    } finally {
        catalogState.loading = false;
    }
}

function updateCount(n) {
    const el = document.getElementById('catalog-count');
    if (el) el.textContent = `${n} item${n === 1 ? '' : 's'}`;
}

/**
 * Sort cards and re-render grid
 */
function reSortAndRender() {
    const grid = document.getElementById('catalog-grid');
    if (!grid) return;

    // Sort cards
    const sorted = catalogState.allCards.slice().sort((a, b) => {
        const aItem = a._item;
        const bItem = b._item;
        
        let aVal, bVal;
        if (catalogState.sortField === 'title') {
            aVal = aItem.title || '';
            bVal = bItem.title || '';
            const comparison = aVal.localeCompare(bVal);
            return catalogState.sortOrder === 'desc' ? -comparison : comparison;
        } else if (catalogState.sortField === 'date') {
            aVal = aItem.mtime || 0;
            bVal = bItem.mtime || 0;
            return catalogState.sortOrder === 'desc' ? bVal - aVal : aVal - bVal;
        }
        return 0;
    });

    // Clear and render
    grid.innerHTML = '';
    const frag = document.createDocumentFragment();
    sorted.forEach(card => frag.appendChild(card));
    grid.appendChild(frag);
}

    function startVideo(v) {
        if (!v) return;
        if (!catalogState.playing.has(v) && catalogState.playing.size >= catalogState.maxConcurrentVideos) {
            const first = catalogState.playing.values().next().value;
            stopVideo(first);
        }
        v.muted = true;
        v.playsInline = true;
        v.setAttribute('playsinline', '');
        const p = v.play();
        if (p?.catch) p.catch(() => {});
        catalogState.playing.add(v);
    }

    function stopVideo(v) {
        if (!v) return;
        try { v.pause(); } catch {}
        catalogState.playing.delete(v);
    }

    /**
     * Create badge HTML for a corner
     */
    function createCornerBadges(corner, badgeItems) {
        if (!badgeItems.length) return '';
        const direction = BADGE_CONFIG.cornerStack[corner] === 'up' ? 'column-reverse' : 'column';
        const badgesHtml = badgeItems.map(badge => {
            const styleAttr = [];
            if (badge.style.background) styleAttr.push(`background:${badge.style.background}`);
            if (badge.style.color) styleAttr.push(`color:${badge.style.color}`);
            const styleStr = styleAttr.length ? ` style="${styleAttr.join(';')}"` : '';
            return `<div class="tv-badge"${styleStr}>${badge.label}</div>`;
        }).join('');
        return `<div class="tv-badges-corner tv-badges-${corner}" style="flex-direction:${direction};row-gap:${BADGE_CONFIG.badgeGap}px;">${badgesHtml}</div>`;
    }

    /**
     * Get style for a badge value from style map
     */
    function getStyleForValue(styleMap, value) {
        if (!value || !styleMap) return {};
        const v = String(value).toLowerCase();
        for (const [needle, style] of Object.entries(styleMap)) {
            if (v.includes(needle.toLowerCase())) return style;
        }
        return {};
    }

    /**
     * Extract base title from item (removing version info)
     */
    function getBaseTitle(item) {
        const title = item.title || item.file || 'Untitled';
        // Remove version patterns like (v1.0), [v2], etc.
        return title.replace(/[\(\[]v?\d+\.?\d*[\)\]]/gi, '').trim();
    }

    /**
     * Group items by base title to identify multi-version assets
     */
    function groupItemsByBaseTitle() {
        catalogState.versionGroups = {};
        for (const item of catalogState.items) {
            const baseTitle = getBaseTitle(item);
            if (!catalogState.versionGroups[baseTitle]) {
                catalogState.versionGroups[baseTitle] = [];
            }
            catalogState.versionGroups[baseTitle].push(item);
        }
    }

    /**
     * Generate badges for an item based on configuration
     */
    function generateBadges(item) {
        const byCorner = { tl: [], tr: [], bl: [], br: [] };
        
        for (const badgeCfg of BADGE_CONFIG.badges) {
            const rawVal = item[badgeCfg.field];
            if (rawVal == null || rawVal === '') continue;
            
            const val = Array.isArray(rawVal) ? rawVal.join(', ') : rawVal;
            const label = String(val).toUpperCase();
            const styleMap = BADGE_CONFIG.styleMaps[badgeCfg.styleMapKey || badgeCfg.field];
            const style = getStyleForValue(styleMap, val);
            
            // Ensure default styling if no style map matched
            if (!style.background) {
                style.background = '#444';
                style.color = '#fff';
            }
            
            byCorner[badgeCfg.corner].push({ 
                order: badgeCfg.order || 0, 
                label, 
                style 
            });
        }
        
        // Sort badges in each corner by order
        for (const corner of Object.keys(byCorner)) {
            byCorner[corner].sort((a, b) => a.order - b.order);
        }
        
        // Debug logging
        if (Object.values(byCorner).some(arr => arr.length > 0)) {
            console.log('Generated badges for item:', item.title, byCorner);
        }
        
        return byCorner;
    }

    function setupMediaObserver() {
        if (catalogState.mediaObserver) catalogState.mediaObserver.disconnect();

        catalogState.mediaObserver = new IntersectionObserver((entries) => {
            for (const entry of entries) {
                const mediaBox = entry.target;
                const card = mediaBox.closest('.tv-card');
                const ctx = card?._ctx;
                if (!ctx) continue;

                if (entry.isIntersecting) {
                    if (!ctx.mediaAttached) {
                        if (ctx.isVideo) {
                            const v = mediaBox.querySelector('video');
                            if (v) {
                                v.preload = 'metadata';
                                v.src = ctx.mediaUrl || '';
                                v.load();
                                v.addEventListener('loadedmetadata', () => startVideo(v), { once: true });
                            }
                        } else {
                            const img = mediaBox.querySelector('img');
                            if (img) img.src = ctx.mediaUrl || '';
                        }
                        ctx.mediaAttached = true;
                    } else if (ctx.isVideo) {
                        const v = mediaBox.querySelector('video');
                        if (v && v.paused) startVideo(v);
                    }
                } else {
                    if (ctx.mediaAttached) {
                        if (ctx.isVideo) {
                            const v = mediaBox.querySelector('video');
                            stopVideo(v);
                            if (v) {
                                v.removeAttribute('src');
                                v.load();
                            }
                        } else {
                            const img = mediaBox.querySelector('img');
                            img?.removeAttribute('src');
                        }
                        ctx.mediaAttached = false;
                    }
                }
            }
        }, { root: null, rootMargin: '600px 0px', threshold: 0.01 });
    }

function makeCard(item, cardId) {
    const baseTitle = getBaseTitle(item);
    const versions = catalogState.versionGroups[baseTitle] || [item];
    const hasMultipleVersions = versions.length > 1;
    const currentIndex = catalogState.currentVersionIndex[cardId] || 0;
    const currentItem = versions[currentIndex];
    
    const a = document.createElement('a');
    a.className = 'tv-cardlink';
    a.href = '#';
    a._item = currentItem;  // Store item reference for sorting
    a._cardId = cardId;
    a._versions = versions;
    a._currentIndex = currentIndex;

    const title = currentItem.title || currentItem.file || 'Untitled';
    const subtitle = currentItem.subtitle || '';
    const mediaUrl = currentItem.mediaUrl || '';
    const isVideo = !!currentItem.isVideo;
    
    // Generate badges
    const badgesByCorner = generateBadges(currentItem);
    const badgesHtml = [
        createCornerBadges('tl', badgesByCorner.tl),
        createCornerBadges('tr', badgesByCorner.tr),
        createCornerBadges('bl', badgesByCorner.bl),
        createCornerBadges('br', badgesByCorner.br),
    ].join('');

    // Version navigation controls
    const versionNavHtml = hasMultipleVersions ? `
        <button class="tv-version-nav tv-version-prev" aria-label="Previous version">
            <svg class="octicon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M9.78 12.78a.75.75 0 0 1-1.06 0L4.47 8.53a.75.75 0 0 1 0-1.06l4.25-4.25a.751.751 0 0 1 1.042.018.751.751 0 0 1 .018 1.042L6.06 8l3.72 3.72a.75.75 0 0 1 0 1.06Z"></path>
            </svg>
        </button>
        <button class="tv-version-nav tv-version-next" aria-label="Next version">
            <svg class="octicon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M6.22 3.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.751.751 0 0 1-1.042-.018.751.751 0 0 1-.018-1.042L9.94 8 6.22 4.28a.75.75 0 0 1 0-1.06Z"></path>
            </svg>
        </button>
        <div class="tv-version-indicator">${currentIndex + 1}/${versions.length}</div>
    ` : '';

            a.innerHTML = `
                <div class="tv-card">
                    <div class="tv-media">
                        ${isVideo
                            ? `<video muted playsinline loop preload="metadata"></video>`
                            : `<img loading="lazy" decoding="async" alt="" />`
                        }
                        <div class="tv-badges">${badgesHtml}</div>
                        ${versionNavHtml}
                    </div>
                    <div class="tv-footer">
                        <span class="tv-title"></span>
                        ${subtitle ? `<span class="tv-subtitle"></span>` : ''}
                    </div>
                </div>
            `;

            const card = a.querySelector('.tv-card');
            card._ctx = {
                mediaAttached: false,
                isVideo,
                mediaUrl,
                file: currentItem.file
            };

            a.querySelector('.tv-title').textContent = title;
            const sub = a.querySelector('.tv-subtitle');
            if (sub) sub.textContent = subtitle;

            const mediaBox = a.querySelector('.tv-media');
            catalogState.mediaObserver.observe(mediaBox);

            // Version navigation handlers
            if (hasMultipleVersions) {
                setupVersionNavigation(a, versions, cardId);
            }

            a.addEventListener('click', (e) => {
                // Don't open modal if clicking on version nav buttons
                if (e.target.closest('.tv-version-nav')) {
                    e.preventDefault();
                    e.stopPropagation();
                    return;
                }
                e.preventDefault();
                e.stopPropagation();
                openAssetMarkdown(item);
            });

            return a;
        }

        function setupVersionNavigation(cardElement, versions, cardId) {
            const prevBtn = cardElement.querySelector('.tv-version-prev');
            const nextBtn = cardElement.querySelector('.tv-version-next');
            const indicator = cardElement.querySelector('.tv-version-indicator');
            const mediaBox = cardElement.querySelector('.tv-media');
            const badgesContainer = cardElement.querySelector('.tv-badges');
            const titleEl = cardElement.querySelector('.tv-title');
            const subtitleEl = cardElement.querySelector('.tv-subtitle');

            function updateVersion(newIndex) {
                if (newIndex < 0 || newIndex >= versions.length) return;
                
                catalogState.currentVersionIndex[cardId] = newIndex;
                const newItem = versions[newIndex];
                
                // Update stored references
                cardElement._item = newItem;
                cardElement._currentIndex = newIndex;
                
                // Update indicator
                indicator.textContent = `${newIndex + 1}/${versions.length}`;
                
                // Update media
                const card = cardElement.querySelector('.tv-card');
                const ctx = card._ctx;
                const newIsVideo = !!newItem.isVideo;
                const newMediaUrl = newItem.mediaUrl || '';
                
                // If media type changed, replace the element
                if (ctx.isVideo !== newIsVideo) {
                    const oldMedia = mediaBox.querySelector(ctx.isVideo ? 'video' : 'img');
                    const newMedia = newIsVideo
                        ? document.createElement('video')
                        : document.createElement('img');
                    
                    if (newIsVideo) {
                        newMedia.muted = true;
                        newMedia.playsInline = true;
                        newMedia.loop = true;
                        newMedia.preload = 'metadata';
                    } else {
                        newMedia.loading = 'lazy';
                        newMedia.decoding = 'async';
                        newMedia.alt = '';
                    }
                    
                    oldMedia.replaceWith(newMedia);
                    ctx.isVideo = newIsVideo;
                    ctx.mediaAttached = false;
                }
                
                // Update media URL and context
                ctx.mediaUrl = newMediaUrl;
                ctx.file = newItem.file;
                
                // Trigger media reload if in viewport
                if (ctx.mediaAttached) {
                    const media = mediaBox.querySelector(ctx.isVideo ? 'video' : 'img');
                    if (ctx.isVideo) {
                        media.src = newMediaUrl;
                        media.load();
                        media.play().catch(() => {});
                    } else {
                        media.src = newMediaUrl;
                    }
                }
                
                // Update badges
                const badgesByCorner = generateBadges(newItem);
                badgesContainer.innerHTML = [
                    createCornerBadges('tl', badgesByCorner.tl),
                    createCornerBadges('tr', badgesByCorner.tr),
                    createCornerBadges('bl', badgesByCorner.bl),
                    createCornerBadges('br', badgesByCorner.br),
                ].join('');
                
                // Update text
                titleEl.textContent = newItem.title || newItem.file || 'Untitled';
                if (subtitleEl) {
                    subtitleEl.textContent = newItem.subtitle || '';
                }
            }

            // Button click handlers
            prevBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const currentIndex = catalogState.currentVersionIndex[cardId] || 0;
                updateVersion(currentIndex - 1);
            });

            nextBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const currentIndex = catalogState.currentVersionIndex[cardId] || 0;
                updateVersion(currentIndex + 1);
            });

            // Swipe gesture support
            let touchStartX = 0;
            let touchEndX = 0;
            
            mediaBox.addEventListener('touchstart', (e) => {
                touchStartX = e.changedTouches[0].screenX;
            }, { passive: true });
            
            mediaBox.addEventListener('touchend', (e) => {
                touchEndX = e.changedTouches[0].screenX;
                handleSwipe();
            }, { passive: true });
            
            function handleSwipe() {
                const swipeThreshold = 50;
                const diff = touchStartX - touchEndX;
                
                if (Math.abs(diff) > swipeThreshold) {
                    const currentIndex = catalogState.currentVersionIndex[cardId] || 0;
                    
                    if (diff > 0) {
                        // Swiped left - next version
                        updateVersion(currentIndex + 1);
                    } else {
                        // Swiped right - previous version
                        updateVersion(currentIndex - 1);
                    }
                }
            }
        }

        async function openAssetMarkdown(item) {
            const modal = document.getElementById('assetDetailModal');
            const titleEl = document.getElementById('assetModalTitle');
            const contentEl = document.getElementById('assetModalContent');

            if (!modal || !titleEl || !contentEl) return;
            modal.style.display = 'flex';
            titleEl.textContent = item.title || item.file || 'Asset';
            contentEl.innerHTML = `<div class="catalog-loading"><div class="loading-spinner"></div><p>Loading…</p></div>`;

            try {
                const resp = await fetch(`/catalog/render?category=${encodeURIComponent(catalogState.selectedCategory)}&file=${encodeURIComponent(item.file)}`);
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const data = await resp.json();
                if (!data.success) throw new Error(data.message || 'Failed to render');
                titleEl.textContent = data.title || titleEl.textContent;
                contentEl.innerHTML = `<div class="asset-description catalog-markdown">${data.html || ''}</div>`;
                
                // Add copy buttons to code blocks
                addCopyButtonsToCodeBlocks(contentEl);
            } catch (e) {
                contentEl.innerHTML = `<div class="catalog-error"><div class="error-icon">⚠️</div><h3>Failed to load page</h3><p>${String(e.message || e)}</p></div>`;
            }
        }

    /**
     * Add copy buttons to all code blocks in the given container
     */
    function addCopyButtonsToCodeBlocks(container) {
        const codeBlocks = container.querySelectorAll('pre code');
        
        codeBlocks.forEach((codeBlock) => {
            const pre = codeBlock.parentElement;
            if (!pre || pre.querySelector('.code-copy-button')) return; // Skip if button already exists
            
            // Create copy button with octicon
            const button = document.createElement('button');
            button.className = 'code-copy-button';
            button.setAttribute('aria-label', 'Copy code to clipboard');
            button.innerHTML = `
                <svg class="octicon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 0 1 0 1.5h-1.5a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-1.5a.75.75 0 0 1 1.5 0v1.5A1.75 1.75 0 0 1 9.25 16h-7.5A1.75 1.75 0 0 1 0 14.25Z"></path>
                    <path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0 1 14.25 11h-7.5A1.75 1.75 0 0 1 5 9.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z"></path>
                </svg>
                <span>Copy</span>
            `;
            
            // Add click handler
            button.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                const code = codeBlock.textContent;
                try {
                    await navigator.clipboard.writeText(code);
                    
                    // Show success feedback
                    button.classList.add('copied');
                    button.innerHTML = `
                        <svg class="octicon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"></path>
                        </svg>
                        <span>Copied!</span>
                    `;
                    
                    // Reset after 2 seconds
                    setTimeout(() => {
                        button.classList.remove('copied');
                        button.innerHTML = `
                            <svg class="octicon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 0 1 0 1.5h-1.5a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-1.5a.75.75 0 0 1 1.5 0v1.5A1.75 1.75 0 0 1 9.25 16h-7.5A1.75 1.75 0 0 1 0 14.25Z"></path>
                                <path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0 1 14.25 11h-7.5A1.75 1.75 0 0 1 5 9.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z"></path>
                            </svg>
                            <span>Copy</span>
                        `;
                    }, 2000);
                } catch (err) {
                    console.error('Failed to copy code:', err);
                    // Fallback for browsers without clipboard API - use textarea selection
                    try {
                        const textArea = document.createElement('textarea');
                        textArea.value = code;
                        textArea.style.position = 'fixed';
                        textArea.style.left = '-999999px';
                        textArea.style.top = '-999999px';
                        document.body.appendChild(textArea);
                        textArea.focus();
                        textArea.select();
                        const successful = document.execCommand('copy');
                        textArea.remove();
                        
                        if (successful) {
                            // Show success feedback
                            button.classList.add('copied');
                            button.innerHTML = `
                                <svg class="octicon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                                    <path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"></path>
                                </svg>
                                <span>Copied!</span>
                            `;
                            setTimeout(() => {
                                button.classList.remove('copied');
                                button.innerHTML = `
                                    <svg class="octicon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                                        <path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 0 1 0 1.5h-1.5a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-1.5a.75.75 0 0 1 1.5 0v1.5A1.75 1.75 0 0 1 9.25 16h-7.5A1.75 1.75 0 0 1 0 14.25Z"></path>
                                        <path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0 1 14.25 11h-7.5A1.75 1.75 0 0 1 5 9.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z"></path>
                                    </svg>
                                    <span>Copy</span>
                                `;
                            }, 2000);
                        } else {
                            throw new Error('execCommand failed');
                        }
                    } catch (fallbackErr) {
                        console.error('Fallback copy also failed:', fallbackErr);
                        button.innerHTML = `
                            <svg class="octicon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M2.343 13.657A8 8 0 1 1 13.657 2.343 8 8 0 0 1 2.343 13.657ZM6.03 4.97a.751.751 0 0 0-0 1.05L7.94 8 6.03 9.98a.751.751 0 1 0 1.042 1.08L8.99 8l-1.918-3.03a.751.751 0 0 0-1.042 0Zm3.97 4.99h1.5a.75.75 0 0 1 0 1.5h-1.5a.75.75 0 0 1 0-1.5Z"></path>
                            </svg>
                            <span>Failed</span>
                        `;
                        setTimeout(() => {
                            button.innerHTML = `
                                <svg class="octicon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                                    <path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 0 1 0 1.5h-1.5a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-1.5a.75.75 0 0 1 1.5 0v1.5A1.75 1.75 0 0 1 9.25 16h-7.5A1.75 1.75 0 0 1 0 14.25Z"></path>
                                    <path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0 1 14.25 11h-7.5A1.75 1.75 0 0 1 5 9.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z"></path>
                                </svg>
                                <span>Copy</span>
                            `;
                        }, 2000);
                    }
                }
            });
            
            // Insert button into pre element
            pre.appendChild(button);
        });
    }

    function closeAssetDetailModal() {
        const modal = document.getElementById('assetDetailModal');
        if (modal) modal.style.display = 'none';
    }

    window.closeAssetDetailModal = closeAssetDetailModal;
