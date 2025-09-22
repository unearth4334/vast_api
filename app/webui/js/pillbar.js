// ==============================
// pillbar.js — Pill Bar Search Functionality
// ==============================

// Search state object
const searchState = {
  sortBy: 'dph_total',
  vramMinGb: null,
  pcieMinGbps: null,
  netUpMinMbps: null,
  netDownMinMbps: null,
  priceMaxPerHour: null,
  locations: [],
  gpuModelQuery: ''
};

// Track currently open popover
let currentPopover = null;

// Pill update functions
function updatePillLabels() {
  // Sort pill
  const sortLabels = {
    'dph_total': 'Price/hr',
    'score': 'Score',
    'gpu_ram': 'GPU RAM',
    'reliability': 'Reliability'
  };
  document.getElementById('sortPill').textContent = `Sort: ${sortLabels[searchState.sortBy]}`;
  
  // VRAM pill
  const vramPill = document.getElementById('vramPill');
  if (searchState.vramMinGb) {
    vramPill.textContent = `VRAM: ≥ ${searchState.vramMinGb} GB`;
    vramPill.classList.add('pill--active');
  } else {
    vramPill.textContent = 'VRAM: Any';
    vramPill.classList.remove('pill--active');
  }
  
  // PCIe pill
  const pciePill = document.getElementById('pciePill');
  if (searchState.pcieMinGbps) {
    pciePill.textContent = `PCIe: ≥ ${searchState.pcieMinGbps} GB/s`;
    pciePill.classList.add('pill--active');
  } else {
    pciePill.textContent = 'PCIe: Any';
    pciePill.classList.remove('pill--active');
  }
  
  // Net pill
  const netPill = document.getElementById('netPill');
  if (searchState.netUpMinMbps || searchState.netDownMinMbps) {
    const upText = searchState.netUpMinMbps ? `${searchState.netUpMinMbps}↑` : '0↑';
    const downText = searchState.netDownMinMbps ? `${searchState.netDownMinMbps}↓` : '0↓';
    netPill.textContent = `Net: ≥ ${upText}/${downText}`;
    netPill.classList.add('pill--active');
  } else {
    netPill.textContent = 'Net: Any';
    netPill.classList.remove('pill--active');
  }
  
  // Location pill
  const locationPill = document.getElementById('locationPill');
  if (searchState.locations.length > 0) {
    locationPill.textContent = `Loc: ${searchState.locations.length}`;
    locationPill.classList.add('pill--active');
  } else {
    locationPill.textContent = 'Location: Any';
    locationPill.classList.remove('pill--active');
  }
  
  // GPU Model pill
  const gpuModelPill = document.getElementById('gpuModelPill');
  if (searchState.gpuModelQuery) {
    const truncated = searchState.gpuModelQuery.length > 10 
      ? searchState.gpuModelQuery.substring(0, 10) + '...'
      : searchState.gpuModelQuery;
    gpuModelPill.textContent = `GPU: ${truncated}`;
    gpuModelPill.classList.add('pill--active');
  } else {
    gpuModelPill.textContent = 'GPU: Any';
    gpuModelPill.classList.remove('pill--active');
  }
  
  // Price pill
  const pricePill = document.getElementById('pricePill');
  if (searchState.priceMaxPerHour) {
    pricePill.textContent = `Price: ≤ $${searchState.priceMaxPerHour.toFixed(2)}`;
    pricePill.classList.add('pill--active');
  } else {
    pricePill.textContent = 'Price: Any';
    pricePill.classList.remove('pill--active');
  }
}

// Popover management
function togglePillPopover(popoverType) {
  const popoverId = popoverType + 'Popover';
  const popover = document.getElementById(popoverId);
  
  if (!popover) return;
  
  // Close current popover if different
  if (currentPopover && currentPopover !== popover) {
    currentPopover.style.display = 'none';
    currentPopover.setAttribute('aria-hidden', 'true');
  }
  
  // Toggle this popover
  const isVisible = popover.style.display === 'block';
  popover.style.display = isVisible ? 'none' : 'block';
  popover.setAttribute('aria-hidden', isVisible ? 'true' : 'false');
  
  currentPopover = isVisible ? null : popover;
  
  if (!isVisible) {
    // Initialize popover with current state
    initializePopover(popoverType);
    // Focus first interactive element
    const firstInput = popover.querySelector('input, button');
    if (firstInput) firstInput.focus();
  }
}

function closeAllPopovers() {
  if (currentPopover) {
    currentPopover.style.display = 'none';
    currentPopover.setAttribute('aria-hidden', 'true');
    currentPopover = null;
  }
}

// Initialize popover with current state
function initializePopover(popoverType) {
  switch (popoverType) {
    case 'sort':
      const sortRadio = document.querySelector(`input[name="sortOption"][value="${searchState.sortBy}"]`);
      if (sortRadio) sortRadio.checked = true;
      break;
      
    case 'vram':
      const vramSlider = document.getElementById('vramSlider');
      const vramInput = document.getElementById('vramInput');
      const value = searchState.vramMinGb || 10;
      vramSlider.value = value;
      vramInput.value = value;
      break;
      
    case 'pcie':
      const pcieSlider = document.getElementById('pcieSlider');
      const pcieInput = document.getElementById('pcieInput');
      const pcieValue = searchState.pcieMinGbps || 16;
      pcieSlider.value = pcieValue;
      pcieInput.value = pcieValue;
      break;
      
    case 'net':
      const netUpSlider = document.getElementById('netUpSlider');
      const netUpInput = document.getElementById('netUpInput');
      const netDownSlider = document.getElementById('netDownSlider');
      const netDownInput = document.getElementById('netDownInput');
      
      netUpSlider.value = searchState.netUpMinMbps || 100;
      netUpInput.value = searchState.netUpMinMbps || 100;
      netDownSlider.value = searchState.netDownMinMbps || 100;
      netDownInput.value = searchState.netDownMinMbps || 100;
      break;
      
    case 'location':
      // Reset checkboxes
      const checkboxes = document.querySelectorAll('#locationList input[type="checkbox"]');
      checkboxes.forEach(cb => {
        cb.checked = searchState.locations.includes(cb.value);
      });
      break;
      
    case 'gpuModel':
      const gpuModelInput = document.getElementById('gpuModelInput');
      gpuModelInput.value = searchState.gpuModelQuery;
      break;
      
    case 'price':
      const priceSlider = document.getElementById('priceSlider');
      const priceInput = document.getElementById('priceInput');
      const priceValue = searchState.priceMaxPerHour || 1.00;
      priceSlider.value = priceValue;
      priceInput.value = priceValue;
      break;
  }
}

// Sync slider and input values
function syncSliderInput(sliderId, inputId) {
  const slider = document.getElementById(sliderId);
  const input = document.getElementById(inputId);
  
  if (!slider || !input) return;
  
  slider.addEventListener('input', () => {
    input.value = slider.value;
  });
  
  input.addEventListener('input', () => {
    slider.value = input.value;
  });
}

// Initialize slider-input syncing
function initializeSliderSync() {
  syncSliderInput('vramSlider', 'vramInput');
  syncSliderInput('pcieSlider', 'pcieInput');
  syncSliderInput('netUpSlider', 'netUpInput');
  syncSliderInput('netDownSlider', 'netDownInput');
  syncSliderInput('priceSlider', 'priceInput');
}

// Quick chip functions
function setVramValue(value) {
  document.getElementById('vramSlider').value = value;
  document.getElementById('vramInput').value = value;
}

function setPcieValue(value) {
  document.getElementById('pcieSlider').value = value;
  document.getElementById('pcieInput').value = value;
}

function setPriceValue(value) {
  document.getElementById('priceSlider').value = value;
  document.getElementById('priceInput').value = value;
}

// Filter apply functions
function applySortFilter() {
  const selectedSort = document.querySelector('input[name="sortOption"]:checked');
  if (selectedSort) {
    searchState.sortBy = selectedSort.value;
    updatePillLabels();
    closeAllPopovers();
    announceChange('Sort updated');
  }
}

function applyVramFilter() {
  const value = parseInt(document.getElementById('vramInput').value);
  searchState.vramMinGb = value > 0 ? value : null;
  updatePillLabels();
  closeAllPopovers();
  announceChange(`VRAM filter ${searchState.vramMinGb ? 'set to ' + searchState.vramMinGb + ' GB' : 'cleared'}`);
}

function clearVramFilter() {
  searchState.vramMinGb = null;
  updatePillLabels();
  closeAllPopovers();
  announceChange('VRAM filter cleared');
}

function applyPcieFilter() {
  const value = parseInt(document.getElementById('pcieInput').value);
  searchState.pcieMinGbps = value > 0 ? value : null;
  updatePillLabels();
  closeAllPopovers();
  announceChange(`PCIe filter ${searchState.pcieMinGbps ? 'set to ' + searchState.pcieMinGbps + ' GB/s' : 'cleared'}`);
}

function clearPcieFilter() {
  searchState.pcieMinGbps = null;
  updatePillLabels();
  closeAllPopovers();
  announceChange('PCIe filter cleared');
}

function applyNetFilter() {
  const upValue = parseInt(document.getElementById('netUpInput').value);
  const downValue = parseInt(document.getElementById('netDownInput').value);
  searchState.netUpMinMbps = upValue > 0 ? upValue : null;
  searchState.netDownMinMbps = downValue > 0 ? downValue : null;
  updatePillLabels();
  closeAllPopovers();
  announceChange('Network filter applied');
}

function clearNetFilter() {
  searchState.netUpMinMbps = null;
  searchState.netDownMinMbps = null;
  updatePillLabels();
  closeAllPopovers();
  announceChange('Network filter cleared');
}

function applyLocationFilter() {
  const checkboxes = document.querySelectorAll('#locationList input[type="checkbox"]:checked');
  searchState.locations = Array.from(checkboxes).map(cb => cb.value);
  updatePillLabels();
  closeAllPopovers();
  announceChange(`Location filter applied: ${searchState.locations.length} selected`);
}

function clearLocationFilter() {
  searchState.locations = [];
  const checkboxes = document.querySelectorAll('#locationList input[type="checkbox"]');
  checkboxes.forEach(cb => cb.checked = false);
  updatePillLabels();
  closeAllPopovers();
  announceChange('Location filter cleared');
}

function selectAllLocations() {
  const checkboxes = document.querySelectorAll('#locationList input[type="checkbox"]');
  checkboxes.forEach(cb => cb.checked = true);
}

function selectNoLocations() {
  const checkboxes = document.querySelectorAll('#locationList input[type="checkbox"]');
  checkboxes.forEach(cb => cb.checked = false);
}

function applyGpuModelFilter() {
  const value = document.getElementById('gpuModelInput').value.trim();
  searchState.gpuModelQuery = value;
  updatePillLabels();
  closeAllPopovers();
  announceChange(`GPU model filter ${value ? 'set to ' + value : 'cleared'}`);
}

function clearGpuModelFilter() {
  searchState.gpuModelQuery = '';
  document.getElementById('gpuModelInput').value = '';
  updatePillLabels();
  closeAllPopovers();
  announceChange('GPU model filter cleared');
}

function applyPriceFilter() {
  const value = parseFloat(document.getElementById('priceInput').value);
  searchState.priceMaxPerHour = value > 0 ? value : null;
  updatePillLabels();
  closeAllPopovers();
  announceChange(`Price filter ${searchState.priceMaxPerHour ? 'set to $' + searchState.priceMaxPerHour.toFixed(2) : 'cleared'}`);
}

function clearPriceFilter() {
  searchState.priceMaxPerHour = null;
  updatePillLabels();
  closeAllPopovers();
  announceChange('Price filter cleared');
}

// Accessibility announcements
function announceChange(message) {
  let liveRegion = document.getElementById('pillbar-live-region');
  if (!liveRegion) {
    liveRegion = document.createElement('div');
    liveRegion.id = 'pillbar-live-region';
    liveRegion.setAttribute('aria-live', 'polite');
    liveRegion.setAttribute('aria-atomic', 'true');
    liveRegion.style.position = 'absolute';
    liveRegion.style.left = '-10000px';
    liveRegion.style.width = '1px';
    liveRegion.style.height = '1px';
    liveRegion.style.overflow = 'hidden';
    document.body.appendChild(liveRegion);
  }
  
  setTimeout(() => {
    liveRegion.textContent = message;
  }, 100);
}

// Event listeners
function initializePillBarEventListeners() {
  // Click outside to close popovers
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.pill') && !e.target.closest('.pill-popover')) {
      closeAllPopovers();
    }
  });
  
  // ESC key to close popovers
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeAllPopovers();
    }
  });
  
  // Sort radio change
  document.addEventListener('change', (e) => {
    if (e.target.name === 'sortOption') {
      applySortFilter();
    }
  });
  
  // Initialize slider syncing
  initializeSliderSync();
  
  // Initialize pill labels
  updatePillLabels();
}

// Updated searchVastaiOffers function
async function searchVastaiOffersWithPillState() {
  const resultsDiv = document.getElementById('searchResults');
  
  if (!resultsDiv) return;
  
  // Show loading state
  resultsDiv.innerHTML = '<div class="no-results-message">🔍 Searching for available offers...</div>';
  
  try {
    // Build query parameters from state
    const params = new URLSearchParams();
    
    // Always include sort and existing gpu_ram for compatibility
    params.append('sort', searchState.sortBy);
    params.append('gpu_ram', searchState.vramMinGb || 10);
    
    // Add new parameters if they have values
    if (searchState.pcieMinGbps) {
      params.append('pcie_min', searchState.pcieMinGbps);
    }
    if (searchState.netUpMinMbps) {
      params.append('inet_up_min', searchState.netUpMinMbps);
    }
    if (searchState.netDownMinMbps) {
      params.append('inet_down_min', searchState.netDownMinMbps);
    }
    if (searchState.priceMaxPerHour) {
      params.append('price_max', searchState.priceMaxPerHour);
    }
    if (searchState.locations.length > 0) {
      params.append('locations', searchState.locations.join(','));
    }
    if (searchState.gpuModelQuery) {
      params.append('gpu_model', searchState.gpuModelQuery);
    }
    
    const data = await api.get(`/vastai/search-offers?${params.toString()}`);
    
    if (!data || data.success === false) {
      const msg = (data && data.message) ? data.message : 'Failed to search offers';
      resultsDiv.innerHTML = `<div class="no-results-message" style="color: var(--text-error);">❌ Error: ${msg}</div>`;
      return;
    }
    
    const offers = Array.isArray(data.offers) ? data.offers : [];
    displaySearchResults(offers);
    
  } catch (error) {
    resultsDiv.innerHTML = `<div class="no-results-message" style="color: var(--text-error);">❌ Request failed: ${error.message}</div>`;
  }
}

// Expose functions to global scope
window.togglePillPopover = togglePillPopover;
window.setVramValue = setVramValue;
window.setPcieValue = setPcieValue;
window.setPriceValue = setPriceValue;
window.applySortFilter = applySortFilter;
window.applyVramFilter = applyVramFilter;
window.clearVramFilter = clearVramFilter;
window.applyPcieFilter = applyPcieFilter;
window.clearPcieFilter = clearPcieFilter;
window.applyNetFilter = applyNetFilter;
window.clearNetFilter = clearNetFilter;
window.applyLocationFilter = applyLocationFilter;
window.clearLocationFilter = clearLocationFilter;
window.selectAllLocations = selectAllLocations;
window.selectNoLocations = selectNoLocations;
window.applyGpuModelFilter = applyGpuModelFilter;
window.clearGpuModelFilter = clearGpuModelFilter;
window.applyPriceFilter = applyPriceFilter;
window.clearPriceFilter = clearPriceFilter;

// Override the original searchVastaiOffers function
window.searchVastaiOffers = searchVastaiOffersWithPillState;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initializePillBarEventListeners);