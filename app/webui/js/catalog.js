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

    // Setup media observer
    setupMediaObserver();
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

            a.innerHTML = `
                <div class="tv-card">
                    <div class="tv-media">
                        ${isVideo
                            ? `<video muted playsinline loop preload="metadata"></video>`
                            : `<img loading="lazy" decoding="async" alt="" />`
                        }
                        <div class="tv-badges"></div>
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
