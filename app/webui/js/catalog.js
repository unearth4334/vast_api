/**
 * Asset Catalog (TileView-style)
 *
 * - Category dropdown (toolbar-btn / toolbar-dropdown)
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
    loading: false,
    mediaObserver: null,
    playing: new Set(),
    maxConcurrentVideos: 2
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
                setCategoryLabel(catalogState.selectedCategory);
            }
        }
    } catch (error) {
        console.log('Could not load saved category from server, using localStorage');
        // Fallback to localStorage
        const savedCategory = localStorage.getItem('catalog-selected-category');
        if (savedCategory) {
            catalogState.selectedCategory = savedCategory;
            setCategoryLabel(catalogState.selectedCategory);
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

        function initCatalog() {
            setupCategoryDropdown();
            loadSavedCategory().finally(() => {
                // Default if saved category is invalid
                if (!CATEGORIES.some(c => c.key === catalogState.selectedCategory)) {
                    catalogState.selectedCategory = 'checkpoints';
                }
                setCategoryLabel(catalogState.selectedCategory);
                loadCategory(catalogState.selectedCategory);
            });
        }

        function setCategoryLabel(categoryKey) {
            const category = CATEGORIES.find(c => c.key === categoryKey);
            const label = category ? category.label : categoryKey;
            const el = document.getElementById('catalog-category-text');
            if (el) el.textContent = `Category: ${label}`;
        }

        function setupCategoryDropdown() {
            const btn = document.getElementById('catalog-category-btn');
            const menu = document.getElementById('catalog-category-menu');
            if (!btn || !menu) return;

            const toggleMenu = (show) => {
                const isOpen = show ?? (menu.style.display === 'none');
                menu.style.display = isOpen ? 'block' : 'none';
                btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
            };

            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                toggleMenu();
            });

            document.addEventListener('click', () => toggleMenu(false));
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    toggleMenu(false);
                    closeAssetDetailModal();
                }
            });

            menu.addEventListener('click', (e) => {
                const target = e.target;
                if (!(target instanceof HTMLElement)) return;
                const key = target.dataset.category;
                if (!key) return;
                catalogState.selectedCategory = key;
                saveCategoryPreference(key);
                setCategoryLabel(key);
                toggleMenu(false);
                loadCategory(key);
            });
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
                renderTileGrid(catalogState.items);
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

        function renderTileGrid(items) {
            const grid = document.getElementById('catalog-grid');
            if (!grid) return;
            grid.innerHTML = '';

            if (!items.length) {
                grid.innerHTML = `
                    <div class="catalog-empty">
                        <div class="empty-icon">📭</div>
                        <h3>No items found</h3>
                        <p>No markdown files were found for this category.</p>
                    </div>
                `;
                return;
            }

            setupMediaObserver();

            const frag = document.createDocumentFragment();
            for (const item of items) {
                frag.appendChild(makeCard(item));
            }
            grid.appendChild(frag);
        }

        function makeCard(item) {
            const a = document.createElement('a');
            a.className = 'tv-cardlink';
            a.href = '#';

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
