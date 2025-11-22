# Pill Bar Dropdown Editor Implementation

**Source:** Git commit `58447f7` from September 22, 2025  
**Title:** "Implement pill bar with desktop popovers and mobile inline editors"

This was a mostly working implementation of dropdown editors for the search-offers-modal pillbar. The system used different UIs for desktop (popovers) and mobile (inline editors).

## Architecture Overview

### State Management
```javascript
window.pillBarState = {
  activeEditor: null,
  isMobile: () => window.innerWidth <= 560
};

window.vastaiSearchState = {
  sortBy: 'dph_total',
  vramMinGb: null,
  pcieMinGbps: null,
  netUpMinMbps: null,
  netDownMinMbps: null,
  locations: [],
  gpuModelQuery: '',
  priceMaxPerHour: null
};
```

## Key Functions

### Initialization
```javascript
function initializePillBar() {
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
```

### Opening Editors
```javascript
function openPillEditor(filterType, pill) {
  // Close any existing editor first
  closePillEditor();
  
  // Update active editor state
  window.pillBarState.activeEditor = filterType;
  
  // Update ARIA states
  document.querySelectorAll('.pill').forEach(p => p.setAttribute('aria-expanded', 'false'));
  pill.setAttribute('aria-expanded', 'true');
  
  if (window.pillBarState.isMobile()) {
    openMobileEditor(filterType);
  } else {
    openDesktopPopover(filterType, pill);
  }
}
```

### Mobile Editor
```javascript
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
```

### Desktop Popover
```javascript
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
```

## Editor Builders

### Sort Editor (Radio Buttons)
```javascript
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
    radio.checked = window.vastaiSearchState.sortBy === option.value;
    
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
```

### VRAM Editor (Slider + Input + Chips)
```javascript
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
  input.value = window.vastaiSearchState.vramMinGb || '';
  input.placeholder = 'Any amount';
  
  const slider = document.createElement('input');
  slider.type = 'range';
  slider.className = 'editor-slider';
  slider.id = 'vram-slider';
  slider.min = '1';
  slider.max = '128';
  slider.value = window.vastaiSearchState.vramMinGb || '16';
  
  const chips = document.createElement('div');
  chips.className = 'editor-chips';
  [8, 16, 24, 32, 48, 80].forEach(value => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'editor-chip';
    chip.textContent = `${value} GB`;
    chip.dataset.value = value;
    if (window.vastaiSearchState.vramMinGb == value) {
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
```

### Location Editor (Searchable Checkboxes)
```javascript
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
    checkbox.checked = window.vastaiSearchState.locations.includes(country.code);
    
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
```

### GPU Model Editor (Text Input)
```javascript
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
  input.value = window.vastaiSearchState.gpuModelQuery || '';
  input.placeholder = 'e.g., RTX 4090, A100, V100...';
  
  const helper = document.createElement('div');
  helper.className = 'editor-helper-text';
  helper.textContent = 'Enter GPU model name or part of it';
  
  section.appendChild(label);
  section.appendChild(input);
  section.appendChild(helper);
  
  return section;
}
```

### Price Cap Editor (Number Input)
```javascript
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
  input.value = window.vastaiSearchState.priceMaxPerHour || '';
  input.placeholder = 'No limit';
  
  const helper = document.createElement('div');
  helper.className = 'editor-helper-text';
  helper.textContent = 'Set maximum price per hour limit';
  
  section.appendChild(label);
  section.appendChild(input);
  section.appendChild(helper);
  
  return section;
}
```

## Apply & Clear Logic

### Apply Changes
```javascript
function applyEditorChanges(filterType) {
  const state = window.vastaiSearchState;
  
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
```

### Clear Filter
```javascript
function clearEditorFilter(filterType) {
  const state = window.vastaiSearchState;
  
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
```

## CSS Styles

### Mobile Editor
```css
.pill-editor {
    display: none;
    margin-top: 8px;
    border: 1px solid var(--background-modifier-border);
    background: var(--background-secondary);
    border-radius: var(--radius-s);
}

@media (max-width: 560px) {
    .pill-editor {
        display: block;
    }
}

.pill-editor__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    border-bottom: 1px solid var(--background-modifier-border);
    background: var(--background-modifier-form-field);
}

.pill-editor__content {
    padding: 12px;
}

.pill-editor__actions {
    display: flex;
    gap: 8px;
    padding: 12px;
    border-top: 1px solid var(--background-modifier-border);
    background: var(--background-modifier-form-field);
}
```

### Desktop Popover
```css
.pill-popover {
    position: absolute;
    z-index: 1001;
    background: var(--background-primary);
    border: 1px solid var(--background-modifier-border);
    border-radius: var(--radius-m);
    box-shadow: 0 4px 12px var(--background-modifier-box-shadow);
    padding: 12px;
    min-width: 200px;
    max-width: 300px;
    display: none;
}

/* Arrow pointer */
.pill-popover::before {
    content: '';
    position: absolute;
    top: -8px;
    left: 20px;
    width: 0;
    height: 0;
    border-left: 8px solid transparent;
    border-right: 8px solid transparent;
    border-bottom: 8px solid var(--background-modifier-border);
}

.pill-popover::after {
    content: '';
    position: absolute;
    top: -7px;
    left: 21px;
    width: 0;
    height: 0;
    border-left: 7px solid transparent;
    border-right: 7px solid transparent;
    border-bottom: 7px solid var(--background-primary);
}
```

### Editor Components
```css
.editor-section {
    margin-bottom: 12px;
}

.editor-label {
    display: block;
    font-size: var(--font-ui-small);
    font-weight: 600;
    color: var(--text-normal);
    margin-bottom: 4px;
}

.editor-input {
    width: 100%;
    padding: 6px 8px;
    border: 1px solid var(--background-modifier-border);
    border-radius: var(--radius-s);
    background: var(--background-primary);
    color: var(--text-normal);
    font-size: var(--font-ui-small);
}

.editor-slider {
    width: 100%;
    margin: 8px 0;
}

.editor-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 6px;
}

.editor-chip {
    padding: 2px 8px;
    background: var(--interactive-normal);
    border: 1px solid var(--background-modifier-border);
    border-radius: var(--radius-s);
    font-size: var(--font-ui-smaller);
    cursor: pointer;
    transition: all 0.2s ease;
}

.editor-chip:hover,
.editor-chip.selected {
    background: var(--interactive-accent);
    color: white;
    border-color: var(--interactive-accent);
}

.editor-radio-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.editor-radio-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    cursor: pointer;
}

.editor-checkbox-list {
    max-height: 200px;
    overflow-y: auto;
    border: 1px solid var(--background-modifier-border);
    border-radius: var(--radius-s);
    padding: 6px;
}

.editor-checkbox-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    cursor: pointer;
}

.editor-search {
    width: 100%;
    padding: 6px 8px;
    border: 1px solid var(--background-modifier-border);
    border-radius: var(--radius-s);
    background: var(--background-primary);
    color: var(--text-normal);
    font-size: var(--font-ui-small);
    margin-bottom: 8px;
}

.editor-helper-text {
    font-size: var(--font-ui-smaller);
    color: var(--text-muted);
    margin-top: 4px;
}
```

## Key Features

1. **Responsive Design**: Different UIs for mobile (inline) and desktop (popover)
2. **Accessibility**: ARIA attributes, keyboard navigation, screen reader announcements
3. **Rich Controls**: Radio buttons, sliders, chips, checkboxes, search
4. **State Persistence**: All filters stored in `window.vastaiSearchState`
5. **Dynamic Content**: All editors built programmatically via `buildEditor()`
6. **Focus Management**: Auto-focus on first interactive element
7. **Outside Click Detection**: Close popovers when clicking outside (desktop only)
8. **ESC Key Support**: Close any open editor with Escape key

## Integration Points

- Pills trigger via `data-filter` attribute
- Mobile editor uses `#pill-editor` container
- Desktop popovers append to `document.body`
- Search triggered via special "search" pill
- State synced before each search operation
