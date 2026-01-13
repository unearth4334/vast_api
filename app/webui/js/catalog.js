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
    sortOrder: 'asc'
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
        
        // Setup media observer before creating cards
        setupMediaObserver();
        
        catalogState.allCards = catalogState.items.map(item => makeCard(item));
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

function makeCard(item) {
    const a = document.createElement('a');
    a.className = 'tv-cardlink';
    a.href = '#';
    a._item = item;  // Store item reference for sorting

    const title = item.title || item.file || 'Untitled';
    const subtitle = item.subtitle || '';
    const mediaUrl = item.mediaUrl || '';
    const isVideo = !!item.isVideo;
    
    // Generate badges
    const badgesByCorner = generateBadges(item);
    const badgesHtml = [
        createCornerBadges('tl', badgesByCorner.tl),
        createCornerBadges('tr', badgesByCorner.tr),
        createCornerBadges('bl', badgesByCorner.bl),
        createCornerBadges('br', badgesByCorner.br),
    ].join('');

            a.innerHTML = `
                <div class="tv-card">
                    <div class="tv-media">
                        ${isVideo
                            ? `<video muted playsinline loop preload="metadata"></video>`
                            : `<img loading="lazy" decoding="async" alt="" />`
                        }
                        <div class="tv-badges">${badgesHtml}</div>
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
                file: item.file
            };

            a.querySelector('.tv-title').textContent = title;
            const sub = a.querySelector('.tv-subtitle');
            if (sub) sub.textContent = subtitle;

            const mediaBox = a.querySelector('.tv-media');
            catalogState.mediaObserver.observe(mediaBox);

            a.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                openAssetMarkdown(item);
            });

            return a;
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
            } catch (e) {
                contentEl.innerHTML = `<div class="catalog-error"><div class="error-icon">⚠️</div><h3>Failed to load page</h3><p>${String(e.message || e)}</p></div>`;
            }
        }

    function closeAssetDetailModal() {
        const modal = document.getElementById('assetDetailModal');
        if (modal) modal.style.display = 'none';
    }

    window.closeAssetDetailModal = closeAssetDetailModal;
