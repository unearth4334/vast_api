// ==============================
// VastAI Search Module
// ==============================
// Offer search functionality, filters, pill bar, and search state management

import { getCountryFlag, fmtMoney, fmtGb } from './utils.js';
import { showSetupResult, showOfferDetailsModal } from './ui.js';

// Global offer storage to prevent XSS vulnerabilities
window.offerStore = new Map();

// Global state for mobile tap reveal functionality
window.mobileOfferState = {
  expandedEl: null,
  clickHandler: null,
  keydownHandler: null
};

// State management for pill bar filters
export const vastaiSearchState = {
  sortBy: 'dph_total',          // 'dph_total' | 'score' | 'gpu_ram' | 'reliability'
  vramMinGb: null,              // number | null
  pcieMinGbps: null,            // number | null
  netUpMinMbps: null,           // number | null
  netDownMinMbps: null,         // number | null
  priceMaxPerHour: null,        // number | null
  locations: [],                // string[] (country codes)
  gpuModelQuery: ''             // string
};

// Current open editor state
export const pillBarState = {
  activeEditor: null,           // string | null - which editor is open
  isMobile: () => window.matchMedia('(max-width: 560px)').matches
};

// Label formatters for pills
const pillLabelFormatters = {
  search: () => 'Search',
  sort: () => {
    const sortLabels = {
      'dph_total': 'Price/hr',
      'score': 'Score', 
      'gpu_ram': 'GPU RAM',
      'reliability': 'Reliability'
    };
    return `Sort: ${sortLabels[vastaiSearchState.sortBy] || 'Price/hr'}`;
  },
  vram: () => {
    const min = vastaiSearchState.vramMinGb;
    return min ? `VRAM: ≥${min} GB` : 'VRAM: Any';
  },
  pcie: () => {
    const min = vastaiSearchState.pcieMinGbps;
    return min ? `PCIe: ≥${min} GB/s` : 'PCIe: Any';
  },
  net: () => {
    const up = vastaiSearchState.netUpMinMbps;
    const down = vastaiSearchState.netDownMinMbps;
    if (up && down) return `Net: ≥${up}↑/${down}↓`;
    if (up) return `Net Up: ≥${up} Mbps`;
    if (down) return `Net Down: ≥${down} Mbps`;
    return 'Net: Any';
  },
  location: () => {
    const locs = vastaiSearchState.locations;
    if (locs.length === 0) return 'Location: Any';
    if (locs.length === 1) return `Location: ${locs[0]}`;
    return `Location: ${locs.length} selected`;
  },
  gpuModel: () => {
    const query = vastaiSearchState.gpuModelQuery;
    return query ? `GPU: ${query}` : 'GPU Model: Any';
  },
  priceCap: () => {
    const max = vastaiSearchState.priceMaxPerHour;
    return max ? `Price: ≤$${max}/hr` : 'Price: Any';
  }
};

/**
 * Initialize pill bar functionality
 */
export function initializePillBar() {
  updateAllPillLabels();
  setupPillEventListeners();
  
  // Add ARIA live region for announcements
  if (!document.getElementById('pill-announcements')) {
    const liveRegion = document.createElement('div');
    liveRegion.id = 'pill-announcements';
    liveRegion.setAttribute('aria-live', 'polite');
    liveRegion.className = 'sr-only';
    document.body.appendChild(liveRegion);
  }
}

/**
 * Update all pill labels based on current state
 */
function updateAllPillLabels() {
  Object.keys(pillLabelFormatters).forEach(filterType => {
    updatePillLabel(filterType);
  });
}

/**
 * Update a specific pill's label and active state
 * @param {string} filterType - Type of filter to update
 */
function updatePillLabel(filterType) {
  const pill = document.getElementById(`pill-${filterType}`);
  if (!pill) return;
  
  const label = pillLabelFormatters[filterType]();
  pill.textContent = label;
  
  // Update active state based on whether filter has a value
  const hasValue = hasFilterValue(filterType);
  pill.classList.toggle('pill--has-value', hasValue);
}

/**
 * Check if a filter has a non-default value
 * @param {string} filterType - Type of filter to check
 * @returns {boolean} Whether the filter has a value
 */
function hasFilterValue(filterType) {
  const state = vastaiSearchState;
  switch (filterType) {
    case 'search': return false; // Search button doesn't have a "value"
    case 'sort': return state.sortBy !== 'dph_total';
    case 'vram': return state.vramMinGb !== null;
    case 'pcie': return state.pcieMinGbps !== null;
    case 'net': return state.netUpMinMbps !== null || state.netDownMinMbps !== null;
    case 'location': return state.locations.length > 0;
    case 'gpuModel': return state.gpuModelQuery !== '';
    case 'priceCap': return state.priceMaxPerHour !== null;
    default: return false;
  }
}

/**
 * Setup event listeners for pills
 */
function setupPillEventListeners() {
  const pillbar = document.getElementById('pillbar');
  if (!pillbar) return;
  
  // Add click handlers to all pills
  pillbar.addEventListener('click', handlePillClick);
  
  // Add keyboard handlers
  pillbar.addEventListener('keydown', handlePillKeydown);
  
  // Close editors when clicking outside (desktop only)
  document.addEventListener('click', handleOutsideClick);
  
  // ESC key handler
  document.addEventListener('keydown', handleEscKey);
}

/**
 * Handle pill clicks
 * @param {Event} event - Click event
 */
function handlePillClick(event) {
  const pill = event.target.closest('.pill');
  if (!pill) return;
  
  const filterType = pill.dataset.filter;
  if (!filterType) return;
  
  event.preventDefault();
  event.stopPropagation();
  
  // Special handling for search pill
  if (filterType === 'search') {
    searchVastaiOffers();
    return;
  }
  
  // Open the appropriate editor
  openPillEditor(filterType, pill);
}

/**
 * Handle keyboard navigation
 * @param {Event} event - Keydown event
 */
function handlePillKeydown(event) {
  const pill = event.target.closest('.pill');
  if (!pill) return;
  
  switch (event.key) {
    case 'Enter':
    case ' ':
      event.preventDefault();
      pill.click();
      break;
    case 'ArrowLeft':
      event.preventDefault();
      focusPreviousPill(pill);
      break;
    case 'ArrowRight':
      event.preventDefault();
      focusNextPill(pill);
      break;
  }
}

/**
 * Focus management for keyboard navigation
 * @param {Element} currentPill - Current pill element
 */
function focusPreviousPill(currentPill) {
  const pills = [...document.querySelectorAll('.pill')];
  const currentIndex = pills.indexOf(currentPill);
  const previousPill = pills[currentIndex - 1] || pills[pills.length - 1];
  previousPill.focus();
}

/**
 * Focus management for keyboard navigation
 * @param {Element} currentPill - Current pill element
 */
function focusNextPill(currentPill) {
  const pills = [...document.querySelectorAll('.pill')];
  const currentIndex = pills.indexOf(currentPill);
  const nextPill = pills[currentIndex + 1] || pills[0];
  nextPill.focus();
}

/**
 * Open pill editor (mobile or desktop popover)
 * @param {string} filterType - Type of filter
 * @param {Element} pill - Pill element
 */
function openPillEditor(filterType, pill) {
  // Close any existing editor first
  closePillEditor();
  
  // Update active editor state
  pillBarState.activeEditor = filterType;
  
  // Update ARIA states
  document.querySelectorAll('.pill').forEach(p => p.setAttribute('aria-expanded', 'false'));
  pill.setAttribute('aria-expanded', 'true');
  
  if (pillBarState.isMobile()) {
    openMobileEditor(filterType);
  } else {
    openDesktopPopover(filterType, pill);
  }
}

/**
 * Close any open pill editor
 */
export function closePillEditor() {
  // Close mobile editor
  const mobileEditor = document.getElementById('pill-editor');
  if (mobileEditor) {
    mobileEditor.style.display = 'none';
    mobileEditor.innerHTML = '';
  }
  
  // Close desktop popover
  const popover = document.querySelector('.pill-popover');
  if (popover) {
    popover.remove();
  }
  
  // Reset ARIA states
  document.querySelectorAll('.pill').forEach(p => p.setAttribute('aria-expanded', 'false'));
  
  // Clear active editor
  pillBarState.activeEditor = null;
}

/**
 * Handle clicks outside pills/editors (desktop only)
 * @param {Event} event - Click event
 */
function handleOutsideClick(event) {
  if (pillBarState.isMobile()) return;
  
  const isInsidePill = event.target.closest('.pill');
  const isInsidePopover = event.target.closest('.pill-popover');
  
  if (!isInsidePill && !isInsidePopover) {
    closePillEditor();
  }
}

/**
 * Handle ESC key
 * @param {Event} event - Keydown event
 */
function handleEscKey(event) {
  if (event.key === 'Escape' && pillBarState.activeEditor) {
    closePillEditor();
  }
}

/**
 * Search VastAI offers with current filter state
 */
export async function searchVastaiOffers() {
  // Build query parameters from current state
  const params = new URLSearchParams();
  
  // Add non-null values to params
  const state = vastaiSearchState;
  if (state.vramMinGb) params.set('gpu_ram', state.vramMinGb);
  if (state.sortBy) params.set('sort', state.sortBy);
  if (state.pcieMinGbps) params.set('pcie_bandwidth', state.pcieMinGbps);
  if (state.netUpMinMbps) params.set('net_up', state.netUpMinMbps);
  if (state.netDownMinMbps) params.set('net_down', state.netDownMinMbps);
  if (state.priceMaxPerHour) params.set('price_max', state.priceMaxPerHour);
  if (state.gpuModelQuery) params.set('gpu_model', state.gpuModelQuery);
  if (state.locations && state.locations.length > 0) params.set('locations', state.locations.join(','));
  
  const resultsDiv = document.getElementById('searchResults');
  if (!resultsDiv) return;
  
  // Show loading state
  resultsDiv.innerHTML = '<div class="no-results-message">🔍 Searching for available offers...</div>';
  
  try {
    const data = await api.get(`/vastai/search-offers?${params.toString()}`);
    
    if (!data || data.success === false) {
      const msg = (data && data.message) ? data.message : 'Failed to search offers';
      resultsDiv.innerHTML = `<div class="no-results-message" style="color: var(--text-error);">❌ Error: ${msg}</div>`;
      return;
    }
    
    const offers = Array.isArray(data.offers) ? data.offers : [];
    displaySearchResults(offers);
    
    // Close any open editors after search
    closePillEditor();
    
  } catch (error) {
    resultsDiv.innerHTML = `<div class="no-results-message" style="color: var(--text-error);">❌ Request failed: ${error.message}</div>`;
  }
}

/**
 * Clear search results and reset filters
 */
export function clearSearchResults() {
  const resultsDiv = document.getElementById('searchResults');
  if (resultsDiv) {
    resultsDiv.innerHTML = '<div class="no-results-message">Enter search criteria and click "Search Offers" to find available instances</div>';
  }
  
  // Reset all filters to default state
  vastaiSearchState.sortBy = 'dph_total';
  vastaiSearchState.vramMinGb = null;
  vastaiSearchState.pcieMinGbps = null;
  vastaiSearchState.netUpMinMbps = null;
  vastaiSearchState.netDownMinMbps = null;
  vastaiSearchState.priceMaxPerHour = null;
  vastaiSearchState.locations = [];
  vastaiSearchState.gpuModelQuery = '';
  
  // Update all pill labels
  updateAllPillLabels();
  
  // Close any open editors
  closePillEditor();
}

/**
 * Display search results
 * @param {Array} offers - Array of offer objects
 */
function displaySearchResults(offers) {
  const resultsDiv = document.getElementById('searchResults');
  if (!resultsDiv) return;

  if (!offers || offers.length === 0) {
    resultsDiv.innerHTML = '<div class="no-results-message">No offers found matching your criteria</div>';
    return;
  }

  // Clear previous offers from store
  window.offerStore.clear();

  let html = '';
  offers.forEach((offer, index) => {
    const offerKey = `offer_${offer.id || index}_${Date.now()}`;
    window.offerStore.set(offerKey, offer);

    const gpuInfo  = offer.gpu_name || 'Unknown GPU';
    const gpuCount = offer.num_gpus || 1;
    const vram     = offer.gpu_ram ? `${Math.round(offer.gpu_ram / 1024)} GB` : 'N/A';
    const price    = offer.dph_total ? `$${offer.dph_total.toFixed(3)}/hr` : 'N/A';
    const location = offer.geolocation || [offer.country, offer.city].filter(Boolean).join(', ') || 'N/A';
    const pcieBw   = offer.pcie_bw ? `${offer.pcie_bw.toFixed(1)} GB/s` : 'N/A';
    const upDown   = `${offer.inet_up ? Math.round(offer.inet_up) : 0}↑/${offer.inet_down ? Math.round(offer.inet_down) : 0}↓ Mbps`;
    const flag     = getCountryFlag(location);

    html += `
      <div class="offer-item compact" data-offer-id="${offer.id || index}" data-offer-key="${offerKey}" tabindex="0" aria-expanded="false">
        <div class="offer-header">
          <div class="offer-title">${gpuInfo}${gpuCount > 1 ? ` (${gpuCount}x)` : ''}</div>
          <div class="offer-price">${price}</div>
        </div>

        <div class="offer-row">
          <div class="offer-meta">
            <span class="kv"><span class="k">VRAM</span><span class="v">${vram}</span></span>
            <span class="kv"><span class="k">PCIe</span><span class="v">${pcieBw}</span></span>
            <span class="kv"><span class="k">Net</span><span class="v">${upDown}</span></span>
            <span class="kv"><span class="k">Loc</span><span class="v">${flag}</span></span>
          </div>

          <div class="offer-actions compact-actions" aria-label="Actions">
            <button class="offer-action-btn icon" title="Details" aria-label="Details"
                    onclick="VastAISearch.viewOfferDetails('${offerKey}')">ⓘ</button>
            <button class="offer-action-btn" onclick="VastAISearch.createInstanceFromOffer('${offer.id}','${offer.gpu_name || 'GPU'}')">
              🚀 Create
            </button>
          </div>
        </div>
      </div>
    `;
  });

  resultsDiv.innerHTML = html;

  // Enable mobile tap-to-reveal behavior
  setupMobileOfferTapReveal();

  showSetupResult(`Found ${offers.length} available offers`, 'success');
}

/**
 * Setup mobile tap-to-reveal behavior for offers
 */
function setupMobileOfferTapReveal() {
  const results = document.getElementById('searchResults');
  if (!results) return;

  // Remove existing event listeners to prevent duplicates
  if (window.mobileOfferState.clickHandler) {
    results.removeEventListener('click', window.mobileOfferState.clickHandler);
  }
  if (window.mobileOfferState.keydownHandler) {
    results.removeEventListener('keydown', window.mobileOfferState.keydownHandler);
  }

  // Clear any previously expanded element
  window.mobileOfferState.expandedEl = null;

  // Create new event handlers
  window.mobileOfferState.clickHandler = (e) => {
    // Only for mobile width
    if (!window.matchMedia('(max-width: 560px)').matches) return;

    // If the user tapped an action button, don't toggle the card
    if (e.target.closest('.offer-action-btn')) return;

    const item = e.target.closest('.offer-item');
    if (!item) return;

    // Toggle current; collapse previous
    if (window.mobileOfferState.expandedEl && window.mobileOfferState.expandedEl !== item) {
      window.mobileOfferState.expandedEl.classList.remove('expanded');
      window.mobileOfferState.expandedEl.setAttribute('aria-expanded', 'false');
    }

    const willExpand = !item.classList.contains('expanded');
    item.classList.toggle('expanded', willExpand);
    item.setAttribute('aria-expanded', willExpand ? 'true' : 'false');
    window.mobileOfferState.expandedEl = willExpand ? item : null;
  };

  window.mobileOfferState.keydownHandler = (e) => {
    if (!window.matchMedia('(max-width: 560px)').matches) return;

    const item = e.target.closest('.offer-item');
    if (!item) return;

    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      item.click();
    }
  };

  // Add the new event listeners
  results.addEventListener('click', window.mobileOfferState.clickHandler);
  results.addEventListener('keydown', window.mobileOfferState.keydownHandler);
}

/**
 * View offer details in modal
 * @param {string} offerKey - Key to retrieve offer from store
 */
export function viewOfferDetails(offerKey) {
  // Retrieve offer from secure storage
  const offer = window.offerStore.get(offerKey);
  if (!offer) {
    console.error('Offer not found for key:', offerKey);
    return;
  }
  
  let details = [
    { label: "Offer ID", value: offer.id },
    { label: "GPU", value: offer.gpu_name || 'N/A' },
    { label: "GPU Count", value: offer.num_gpus || 1 },
    { label: "GPU RAM", value: offer.gpu_ram ? Math.round(offer.gpu_ram / 1024) + ' GB' : 'N/A' },
    { label: "CPU RAM", value: offer.cpu_ram ? Math.round(offer.cpu_ram / 1024) + ' GB' : 'N/A' },
    { label: "Disk Space", value: offer.disk_space ? Math.round(offer.disk_space) + ' GB' : 'N/A' },
    { label: "Price", value: offer.dph_total ? '$' + offer.dph_total.toFixed(3) + '/hr' : 'N/A' },
    { label: "Location", value: offer.geolocation || [offer.country, offer.city].filter(Boolean).join(', ') || 'N/A' },
    { label: "Reliability", value: offer.reliability ? (offer.reliability * 100).toFixed(1) + '%' : 'N/A' },
    { label: "Score", value: offer.score ? offer.score.toFixed(2) : 'N/A' },
    { label: "CPU", value: offer.cpu_name || 'N/A' },
    { label: "Download Speed", value: offer.download_speed ? offer.download_speed + ' Mbps' : 'N/A' },
    { label: "Upload Speed", value: offer.upload_speed ? offer.upload_speed + ' Mbps' : 'N/A' }
  ];
  showOfferDetailsModal(details);
}

/**
 * Show disk size editor popover before creating instance
 * @param {string} offerId - ID of the offer
 * @param {string} gpuName - Name of the GPU for display
 */
export function createInstanceFromOffer(offerId, gpuName) {
  showDiskSizePopover(offerId, gpuName);
}

/**
 * Show disk size configuration popover
 * @param {string} offerId - ID of the offer
 * @param {string} gpuName - Name of the GPU for display
 */
function showDiskSizePopover(offerId, gpuName) {
  // Remove any existing popover
  const existingPopover = document.getElementById('disk-size-popover-overlay');
  if (existingPopover) {
    existingPopover.remove();
  }
  
  // Create overlay
  const overlay = document.createElement('div');
  overlay.id = 'disk-size-popover-overlay';
  overlay.className = 'disk-size-overlay';
  
  // Create popover container
  const popover = document.createElement('div');
  popover.className = 'disk-size-popover';
  
  // Create header
  const header = document.createElement('div');
  header.className = 'disk-size-popover__header';
  header.innerHTML = `
    <strong>Set Disk Size</strong>
    <span class="disk-size-popover__gpu">${gpuName}</span>
  `;
  
  // Create content
  const content = document.createElement('div');
  content.className = 'disk-size-popover__content';
  
  // Build the disk size editor (similar to GPU RAM Filter)
  const editorSection = buildDiskSizeEditor();
  content.appendChild(editorSection);
  
  // Create actions
  const actions = document.createElement('div');
  actions.className = 'disk-size-popover__actions';
  actions.innerHTML = `
    <button class="search-button" id="disk-size-submit-btn">Submit</button>
    <button class="search-button secondary" id="disk-size-cancel-btn">Cancel</button>
  `;
  
  // Assemble popover
  popover.appendChild(header);
  popover.appendChild(content);
  popover.appendChild(actions);
  overlay.appendChild(popover);
  document.body.appendChild(overlay);
  
  // Wire up event handlers
  const submitBtn = document.getElementById('disk-size-submit-btn');
  const cancelBtn = document.getElementById('disk-size-cancel-btn');
  
  submitBtn.addEventListener('click', () => {
    const diskSizeInput = document.getElementById('disk-size-input');
    let diskSize = diskSizeInput ? parseInt(diskSizeInput.value, 10) : 32;
    // Validate disk size is within reasonable bounds (8-500 GB)
    if (isNaN(diskSize) || diskSize < 8) {
      diskSize = 8;
    } else if (diskSize > 500) {
      diskSize = 500;
    }
    closeDiskSizePopover();
    submitCreateInstance(offerId, gpuName, diskSize);
  });
  
  cancelBtn.addEventListener('click', () => {
    closeDiskSizePopover();
  });
  
  // Close on overlay click (but not when clicking inside popover)
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      closeDiskSizePopover();
    }
  });
  
  // Close on ESC key
  const escHandler = (e) => {
    if (e.key === 'Escape') {
      closeDiskSizePopover();
      document.removeEventListener('keydown', escHandler);
    }
  };
  document.addEventListener('keydown', escHandler);
  
  // Focus the input
  setTimeout(() => {
    const diskSizeInput = document.getElementById('disk-size-input');
    if (diskSizeInput) {
      diskSizeInput.focus();
      diskSizeInput.select();
    }
  }, 100);
}

/**
 * Build disk size editor (similar to GPU RAM Filter)
 * @returns {Element} Editor element
 */
function buildDiskSizeEditor() {
  const section = document.createElement('div');
  section.className = 'editor-section';
  
  const label = document.createElement('label');
  label.className = 'editor-label';
  label.textContent = 'Disk Size (GB)';
  
  const input = document.createElement('input');
  input.type = 'number';
  input.className = 'editor-input';
  input.id = 'disk-size-input';
  input.min = '8';
  input.max = '500';
  input.value = '32'; // Default value
  input.placeholder = 'Enter disk size in GB';
  
  const slider = document.createElement('input');
  slider.type = 'range';
  slider.className = 'editor-slider';
  slider.id = 'disk-size-slider';
  slider.min = '8';
  slider.max = '500';
  slider.value = '32';
  
  const chips = document.createElement('div');
  chips.className = 'editor-chips';
  [16, 32, 64, 100, 150, 200].forEach(value => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'editor-chip';
    if (value === 32) {
      chip.classList.add('selected');
    }
    chip.textContent = `${value} GB`;
    chip.dataset.value = value;
    chips.appendChild(chip);
  });
  
  const helper = document.createElement('div');
  helper.className = 'editor-helper-text';
  helper.textContent = 'Specify the disk space for your instance';
  
  // Sync slider and input
  input.addEventListener('input', () => {
    const val = parseInt(input.value, 10);
    // Only sync if valid number, otherwise keep current slider position
    if (!isNaN(val) && val >= 8 && val <= 500) {
      slider.value = val;
    }
    updateDiskSizeChipSelection(chips, input.value);
  });
  
  slider.addEventListener('input', () => {
    input.value = slider.value;
    updateDiskSizeChipSelection(chips, slider.value);
  });
  
  // Handle chip clicks
  chips.addEventListener('click', (e) => {
    if (e.target.classList.contains('editor-chip')) {
      const value = e.target.dataset.value;
      input.value = value;
      slider.value = value;
      updateDiskSizeChipSelection(chips, value);
    }
  });
  
  section.appendChild(label);
  section.appendChild(input);
  section.appendChild(slider);
  section.appendChild(chips);
  section.appendChild(helper);
  
  return section;
}

/**
 * Update disk size chip selection state
 * @param {Element} chipsContainer - Container with chip buttons
 * @param {string|number} value - Selected value
 */
function updateDiskSizeChipSelection(chipsContainer, value) {
  chipsContainer.querySelectorAll('.editor-chip').forEach(chip => {
    chip.classList.toggle('selected', chip.dataset.value == value);
  });
}

/**
 * Close the disk size popover
 */
function closeDiskSizePopover() {
  const overlay = document.getElementById('disk-size-popover-overlay');
  if (overlay) {
    overlay.remove();
  }
}

/**
 * Submit create instance request with disk size
 * @param {string} offerId - ID of the offer
 * @param {string} gpuName - Name of the GPU
 * @param {number} diskSize - Disk size in GB
 */
async function submitCreateInstance(offerId, gpuName, diskSize) {
  showSetupResult(`Creating instance from offer ${offerId} with ${diskSize} GB disk...`, 'info');
  
  try {
    const data = await api.post('/vastai/create-instance', {
      offer_id: offerId,
      disk_size: diskSize
    });
    
    if (data.success) {
      showSetupResult(`✅ Instance created successfully! Instance ID: ${data.instance_id || 'Unknown'}`, 'success');
      // Refresh the instances list if function is available
      if (window.VastAIInstances && window.VastAIInstances.loadVastaiInstances) {
        window.VastAIInstances.loadVastaiInstances();
      }
      // Close the search modal
      if (window.VastAIUI && window.VastAIUI.closeSearchOffersModal) {
        window.VastAIUI.closeSearchOffersModal();
      }
    } else {
      showSetupResult(`❌ Failed to create instance: ${data.message || 'Unknown error'}`, 'error');
    }
  } catch (error) {
    showSetupResult(`❌ Request failed: ${error.message}`, 'error');
  }
}

/**
 * Open mobile inline editor
 * @param {string} filterType - Type of filter to edit
 */
function openMobileEditor(filterType) {
  const editorContainer = document.getElementById('pill-editor');
  if (!editorContainer) return;
  
  editorContainer.innerHTML = '';
  editorContainer.style.display = 'block';
  
  // Build header
  const header = document.createElement('div');
  header.className = 'pill-editor__header';
  const filterNames = {
    sort: 'Sort Options',
    vram: 'GPU RAM Filter',
    pcie: 'PCIe Bandwidth Filter',
    net: 'Network Speed Filter',
    location: 'Location Filter',
    gpuModel: 'GPU Model Filter',
    priceCap: 'Price Cap Filter'
  };
  header.innerHTML = `
    <strong>${filterNames[filterType] || 'Filter'}</strong>
    <button class="pill-editor__close" aria-label="Close ${filterNames[filterType] || 'Filter'} editor">×</button>
  `;
  
  // Build content
  const content = document.createElement('div');
  content.className = 'pill-editor__content';
  content.appendChild(buildEditor(filterType));
  
  // Build actions
  const actions = document.createElement('div');
  actions.className = 'pill-editor__actions';
  actions.innerHTML = `
    <button class="search-button" data-action="apply">Apply</button>
    <button class="search-button secondary" data-action="clear">Clear</button>
  `;
  
  editorContainer.appendChild(header);
  editorContainer.appendChild(content);
  editorContainer.appendChild(actions);
  
  // Wire up event handlers
  header.querySelector('.pill-editor__close').addEventListener('click', closePillEditor);
  actions.querySelector('[data-action="apply"]').addEventListener('click', () => applyEditorChanges(filterType));
  actions.querySelector('[data-action="clear"]').addEventListener('click', () => clearEditorFilter(filterType));
  
  // Set focus to first interactive element
  const firstInput = content.querySelector('input, select, button');
  if (firstInput) {
    setTimeout(() => firstInput.focus(), 100);
  }
}

/**
 * Open desktop popover editor
 * @param {string} filterType - Type of filter to edit
 * @param {Element} pill - Pill element to attach to
 */
function openDesktopPopover(filterType, pill) {
  const popover = document.createElement('div');
  popover.className = 'pill-popover';
  popover.setAttribute('role', 'dialog');
  popover.setAttribute('aria-labelledby', pill.id);
  
  // Build editor content
  popover.appendChild(buildEditor(filterType));
  
  // Position popover
  document.body.appendChild(popover);
  positionPopover(popover, pill);
  popover.style.display = 'block';
  
  // Set focus to first interactive element
  const firstInput = popover.querySelector('input, select, button');
  if (firstInput) {
    setTimeout(() => firstInput.focus(), 100);
  }
  
  // Setup popover event handlers
  setupPopoverHandlers(popover, filterType);
}

/**
 * Position popover relative to pill
 * @param {Element} popover - Popover element
 * @param {Element} pill - Pill element
 */
function positionPopover(popover, pill) {
  const pillRect = pill.getBoundingClientRect();
  const popoverRect = popover.getBoundingClientRect();
  
  let left = pillRect.left;
  let top = pillRect.bottom + 8;
  
  // Adjust if popover would go off-screen
  if (left + popoverRect.width > window.innerWidth) {
    left = window.innerWidth - popoverRect.width - 16;
  }
  if (left < 16) {
    left = 16;
  }
  
  popover.style.left = `${left}px`;
  popover.style.top = `${top}px`;
}

/**
 * Setup popover event handlers
 * @param {Element} popover - Popover element
 * @param {string} filterType - Type of filter
 */
function setupPopoverHandlers(popover, filterType) {
  // Apply button (if editor supports it)
  popover.addEventListener('change', (e) => {
    // Auto-apply for some editor types
    if (filterType === 'sort') {
      applyEditorChanges(filterType);
    }
  });
  
  // Add apply/clear buttons for non-auto-apply editors
  if (filterType !== 'sort') {
    const actions = document.createElement('div');
    actions.className = 'pill-editor__actions';
    actions.style.marginTop = '8px';
    actions.innerHTML = `
      <button class="search-button" data-action="apply" style="flex: 1;">Apply</button>
      <button class="search-button secondary" data-action="clear" style="flex: 1;">Clear</button>
    `;
    popover.appendChild(actions);
    
    actions.querySelector('[data-action="apply"]').addEventListener('click', () => applyEditorChanges(filterType));
    actions.querySelector('[data-action="clear"]').addEventListener('click', () => clearEditorFilter(filterType));
  }
}

/**
 * Build editor content based on filter type
 * @param {string} filterType - Type of filter
 * @returns {Element} Editor element
 */
function buildEditor(filterType) {
  switch (filterType) {
    case 'sort':
      return buildSortEditor();
    case 'vram':
      return buildVramEditor();
    case 'pcie':
      return buildPcieEditor();
    case 'net':
      return buildNetEditor();
    case 'location':
      return buildLocationEditor();
    case 'gpuModel':
      return buildGpuModelEditor();
    case 'priceCap':
      return buildPriceCapEditor();
    default:
      const section = document.createElement('div');
      section.textContent = 'Editor not implemented';
      return section;
  }
}

/**
 * Build sort editor (radio buttons)
 * @returns {Element} Editor element
 */
function buildSortEditor() {
  const section = document.createElement('div');
  section.className = 'editor-section';
  
  const options = [
    { value: 'dph_total', label: 'Price per hour' },
    { value: 'score', label: 'Score' },
    { value: 'gpu_ram', label: 'GPU RAM' },
    { value: 'reliability', label: 'Reliability' }
  ];
  
  const radioList = document.createElement('div');
  radioList.className = 'editor-radio-list';
  
  options.forEach(option => {
    const item = document.createElement('div');
    item.className = 'editor-radio-item';
    
    const radio = document.createElement('input');
    radio.type = 'radio';
    radio.name = 'sort-option';
    radio.value = option.value;
    radio.id = `sort-${option.value}`;
    radio.checked = vastaiSearchState.sortBy === option.value;
    
    const label = document.createElement('label');
    label.htmlFor = radio.id;
    label.textContent = option.label;
    
    item.appendChild(radio);
    item.appendChild(label);
    radioList.appendChild(item);
  });
  
  section.appendChild(radioList);
  return section;
}

/**
 * Build VRAM editor (slider + input + chips)
 * @returns {Element} Editor element
 */
function buildVramEditor() {
  const section = document.createElement('div');
  section.className = 'editor-section';
  
  const label = document.createElement('label');
  label.className = 'editor-label';
  label.textContent = 'Minimum GB VRAM';
  
  const input = document.createElement('input');
  input.type = 'number';
  input.className = 'editor-input';
  input.id = 'vram-input';
  input.min = '1';
  input.max = '128';
  input.value = vastaiSearchState.vramMinGb || '';
  input.placeholder = 'Any amount';
  
  const slider = document.createElement('input');
  slider.type = 'range';
  slider.className = 'editor-slider';
  slider.id = 'vram-slider';
  slider.min = '1';
  slider.max = '128';
  slider.value = vastaiSearchState.vramMinGb || '16';
  
  const chips = document.createElement('div');
  chips.className = 'editor-chips';
  [8, 16, 24, 32, 48, 80].forEach(value => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'editor-chip';
    chip.textContent = `${value} GB`;
    chip.dataset.value = value;
    if (vastaiSearchState.vramMinGb == value) {
      chip.classList.add('selected');
    }
    chips.appendChild(chip);
  });
  
  const helper = document.createElement('div');
  helper.className = 'editor-helper-text';
  helper.textContent = 'Set minimum GPU VRAM requirement';
  
  // Sync slider and input
  input.addEventListener('input', () => {
    slider.value = input.value || '16';
    updateChipSelection(chips, input.value);
  });
  
  slider.addEventListener('input', () => {
    input.value = slider.value;
    updateChipSelection(chips, slider.value);
  });
  
  // Handle chip clicks
  chips.addEventListener('click', (e) => {
    if (e.target.classList.contains('editor-chip')) {
      const value = e.target.dataset.value;
      input.value = value;
      slider.value = value;
      updateChipSelection(chips, value);
    }
  });
  
  section.appendChild(label);
  section.appendChild(input);
  section.appendChild(slider);
  section.appendChild(chips);
  section.appendChild(helper);
  
  return section;
}

/**
 * Build PCIe editor (number input)
 * @returns {Element} Editor element
 */
function buildPcieEditor() {
  const section = document.createElement('div');
  section.className = 'editor-section';
  
  const label = document.createElement('label');
  label.className = 'editor-label';
  label.textContent = 'Minimum PCIe Bandwidth (GB/s)';
  
  const input = document.createElement('input');
  input.type = 'number';
  input.className = 'editor-input';
  input.id = 'pcie-input';
  input.min = '0';
  input.max = '64';
  input.step = '0.1';
  input.value = vastaiSearchState.pcieMinGbps || '';
  input.placeholder = 'Any speed';
  
  const helper = document.createElement('div');
  helper.className = 'editor-helper-text';
  helper.textContent = 'Set minimum PCIe bandwidth requirement';
  
  section.appendChild(label);
  section.appendChild(input);
  section.appendChild(helper);
  
  return section;
}

/**
 * Build network speed editor (dual inputs)
 * @returns {Element} Editor element
 */
function buildNetEditor() {
  const section = document.createElement('div');
  section.className = 'editor-section';
  
  // Upload speed
  const upLabel = document.createElement('label');
  upLabel.className = 'editor-label';
  upLabel.textContent = 'Minimum Upload Speed (Mbps)';
  
  const upInput = document.createElement('input');
  upInput.type = 'number';
  upInput.className = 'editor-input';
  upInput.id = 'net-up-input';
  upInput.min = '0';
  upInput.max = '10000';
  upInput.value = vastaiSearchState.netUpMinMbps || '';
  upInput.placeholder = 'Any speed';
  upInput.style.marginBottom = '12px';
  
  // Download speed
  const downLabel = document.createElement('label');
  downLabel.className = 'editor-label';
  downLabel.textContent = 'Minimum Download Speed (Mbps)';
  
  const downInput = document.createElement('input');
  downInput.type = 'number';
  downInput.className = 'editor-input';
  downInput.id = 'net-down-input';
  downInput.min = '0';
  downInput.max = '10000';
  downInput.value = vastaiSearchState.netDownMinMbps || '';
  downInput.placeholder = 'Any speed';
  
  const helper = document.createElement('div');
  helper.className = 'editor-helper-text';
  helper.textContent = 'Set minimum network speed requirements';
  
  section.appendChild(upLabel);
  section.appendChild(upInput);
  section.appendChild(downLabel);
  section.appendChild(downInput);
  section.appendChild(helper);
  
  return section;
}

/**
 * Build location editor (searchable checkboxes)
 * @returns {Element} Editor element
 */
function buildLocationEditor() {
  const section = document.createElement('div');
  section.className = 'editor-section';
  
  const searchInput = document.createElement('input');
  searchInput.type = 'text';
  searchInput.className = 'editor-search';
  searchInput.placeholder = 'Search countries...';
  
  const checkboxList = document.createElement('div');
  checkboxList.className = 'editor-checkbox-list';
  
  const countries = [
    { code: 'US', name: 'United States' },
    { code: 'CA', name: 'Canada' },
    { code: 'DE', name: 'Germany' },
    { code: 'FR', name: 'France' },
    { code: 'GB', name: 'United Kingdom' },
    { code: 'JP', name: 'Japan' },
    { code: 'KR', name: 'South Korea' },
    { code: 'AU', name: 'Australia' },
    { code: 'SG', name: 'Singapore' },
    { code: 'NL', name: 'Netherlands' },
    { code: 'BR', name: 'Brazil' },
    { code: 'IN', name: 'India' },
    { code: 'CN', name: 'China' },
    { code: 'HK', name: 'Hong Kong' }
  ];
  
  countries.forEach(country => {
    const item = document.createElement('div');
    item.className = 'editor-checkbox-item';
    
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.id = `loc-${country.code}`;
    checkbox.value = country.code;
    checkbox.checked = vastaiSearchState.locations.includes(country.code);
    
    const label = document.createElement('label');
    label.htmlFor = checkbox.id;
    label.textContent = `${country.name} (${country.code})`;
    
    item.appendChild(checkbox);
    item.appendChild(label);
    checkboxList.appendChild(item);
  });
  
  // Search functionality
  searchInput.addEventListener('input', () => {
    const query = searchInput.value.toLowerCase();
    checkboxList.querySelectorAll('.editor-checkbox-item').forEach(item => {
      const label = item.querySelector('label').textContent.toLowerCase();
      item.style.display = label.includes(query) ? 'flex' : 'none';
    });
  });
  
  section.appendChild(searchInput);
  section.appendChild(checkboxList);
  
  return section;
}

/**
 * Build GPU model editor (text input)
 * @returns {Element} Editor element
 */
function buildGpuModelEditor() {
  const section = document.createElement('div');
  section.className = 'editor-section';
  
  const label = document.createElement('label');
  label.className = 'editor-label';
  label.textContent = 'GPU Model';
  
  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'editor-input';
  input.id = 'gpu-model-input';
  input.value = vastaiSearchState.gpuModelQuery || '';
  input.placeholder = 'e.g., RTX 4090, A100, V100...';
  
  const helper = document.createElement('div');
  helper.className = 'editor-helper-text';
  helper.textContent = 'Enter GPU model name or part of it';
  
  section.appendChild(label);
  section.appendChild(input);
  section.appendChild(helper);
  
  return section;
}

/**
 * Build price cap editor (number input)
 * @returns {Element} Editor element
 */
function buildPriceCapEditor() {
  const section = document.createElement('div');
  section.className = 'editor-section';
  
  const label = document.createElement('label');
  label.className = 'editor-label';
  label.textContent = 'Maximum Price per Hour ($)';
  
  const input = document.createElement('input');
  input.type = 'number';
  input.className = 'editor-input';
  input.id = 'price-cap-input';
  input.min = '0.01';
  input.max = '50';
  input.step = '0.01';
  input.value = vastaiSearchState.priceMaxPerHour || '';
  input.placeholder = 'No limit';
  
  const helper = document.createElement('div');
  helper.className = 'editor-helper-text';
  helper.textContent = 'Set maximum price per hour limit';
  
  section.appendChild(label);
  section.appendChild(input);
  section.appendChild(helper);
  
  return section;
}

/**
 * Update chip selection state
 * @param {Element} chipsContainer - Container with chip buttons
 * @param {string|number} value - Selected value
 */
function updateChipSelection(chipsContainer, value) {
  chipsContainer.querySelectorAll('.editor-chip').forEach(chip => {
    chip.classList.toggle('selected', chip.dataset.value == value);
  });
}

/**
 * Apply editor changes to state
 * @param {string} filterType - Type of filter
 */
function applyEditorChanges(filterType) {
  const state = vastaiSearchState;
  
  switch (filterType) {
    case 'sort':
      const selectedSort = document.querySelector('input[name="sort-option"]:checked');
      if (selectedSort) {
        state.sortBy = selectedSort.value;
      }
      break;
      
    case 'vram':
      const vramValue = document.getElementById('vram-input')?.value;
      state.vramMinGb = vramValue && vramValue > 0 ? parseInt(vramValue) : null;
      break;
      
    case 'pcie':
      const pcieValue = document.getElementById('pcie-input')?.value;
      state.pcieMinGbps = pcieValue && pcieValue > 0 ? parseFloat(pcieValue) : null;
      break;
      
    case 'net':
      const upValue = document.getElementById('net-up-input')?.value;
      const downValue = document.getElementById('net-down-input')?.value;
      state.netUpMinMbps = upValue && upValue > 0 ? parseInt(upValue) : null;
      state.netDownMinMbps = downValue && downValue > 0 ? parseInt(downValue) : null;
      break;
      
    case 'location':
      const selectedLocations = [];
      document.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
        if (cb.id && cb.id.startsWith('loc-')) {
          selectedLocations.push(cb.value);
        }
      });
      state.locations = selectedLocations;
      break;
      
    case 'gpuModel':
      const gpuValue = document.getElementById('gpu-model-input')?.value;
      state.gpuModelQuery = gpuValue ? gpuValue.trim() : '';
      break;
      
    case 'priceCap':
      const priceValue = document.getElementById('price-cap-input')?.value;
      state.priceMaxPerHour = priceValue && priceValue > 0 ? parseFloat(priceValue) : null;
      break;
  }
  
  // Update pill label and close editor
  updatePillLabel(filterType);
  closePillEditor();
  
  // Announce the change
  announceFilterChange(filterType);
}

/**
 * Clear filter and reset to default
 * @param {string} filterType - Type of filter
 */
function clearEditorFilter(filterType) {
  const state = vastaiSearchState;
  
  switch (filterType) {
    case 'sort':
      state.sortBy = 'dph_total';
      break;
    case 'vram':
      state.vramMinGb = null;
      break;
    case 'pcie':
      state.pcieMinGbps = null;
      break;
    case 'net':
      state.netUpMinMbps = null;
      state.netDownMinMbps = null;
      break;
    case 'location':
      state.locations = [];
      break;
    case 'gpuModel':
      state.gpuModelQuery = '';
      break;
    case 'priceCap':
      state.priceMaxPerHour = null;
      break;
  }
  
  // Update pill label and close editor
  updatePillLabel(filterType);
  closePillEditor();
  
  // Announce the change
  announceFilterChange(filterType, true);
}

/**
 * Announce filter change for screen readers
 * @param {string} filterType - Type of filter
 * @param {boolean} cleared - Whether filter was cleared
 */
function announceFilterChange(filterType, cleared = false) {
  const liveRegion = document.getElementById('pill-announcements');
  if (!liveRegion) return;
  
  const filterNames = {
    sort: 'Sort',
    vram: 'VRAM',
    pcie: 'PCIe',
    net: 'Network',
    location: 'Location',
    gpuModel: 'GPU Model',
    priceCap: 'Price Cap'
  };
  
  const name = filterNames[filterType] || 'Filter';
  const message = cleared ? `${name} filter cleared` : `${name} filter updated`;
  
  liveRegion.textContent = message;
  
  // Clear after announcement
  setTimeout(() => {
    liveRegion.textContent = '';
  }, 1000);
}

console.log('📄 VastAI Search module loaded');