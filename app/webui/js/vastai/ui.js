// ==============================
// VastAI UI Components Module
// ==============================
// UI feedback, modals, overlays, and user interaction components

/**
 * Show setup result message to user
 * @param {string} message - Message to display
 * @param {string} type - Type of message ('success', 'error', 'info', 'warning')
 */
export function showSetupResult(message, type) {
  console.log(`📢 showSetupResult called: "${message}" (${type})`);
  const resultDiv = document.getElementById('setup-result');
  console.log(`📍 setup-result element exists:`, !!resultDiv);
  if (!resultDiv) {
    console.error('setup-result element not found');
    return;
  }
  resultDiv.textContent = message;
  resultDiv.className = 'setup-result ' + type;
  resultDiv.style.display = 'block';
  console.log(`✅ Result displayed: "${message}"`);  

  if (type === 'info') {
    setTimeout(() => {
      if (resultDiv.textContent === message) {
        resultDiv.style.display = 'none';
      }
    }, 5000);
  }
}

/**
 * Create and show a modal dialog for offer details
 * @param {Array} details - Array of {label, value} objects to display
 */
export function showOfferDetailsModal(details) {
  // Inject modal CSS once
  if (!document.getElementById('vastai-offer-modal-style')) {
    const style = document.createElement('style');
    style.id = 'vastai-offer-modal-style';
    style.textContent = `
      .vastai-modal-overlay {
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.4);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .vastai-modal {
        background: #fff;
        border-radius: 8px;
        max-width: 400px;
        width: 90%;
        box-shadow: 0 2px 16px rgba(0,0,0,0.2);
        padding: 24px 20px 16px 20px;
        position: relative;
        font-family: inherit;
        animation: fadeIn 0.2s;
      }
      .vastai-modal-close {
        position: absolute;
        top: 8px;
        right: 12px;
        background: none;
        border: none;
        font-size: 1.5em;
        color: #888;
        cursor: pointer;
      }
      .vastai-modal h2 {
        margin-top: 0;
        font-size: 1.2em;
        margin-bottom: 12px;
      }
      .vastai-modal table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 8px;
      }
      .vastai-modal td {
        padding: 4px 0;
        vertical-align: top;
      }
      .vastai-modal td:first-child {
        font-weight: bold;
        color: #333;
        width: 40%;
        padding-right: 8px;
      }
      @keyframes fadeIn {
        from { opacity: 0; transform: scale(0.98);}
        to { opacity: 1; transform: scale(1);}
      }
    `;
    document.head.appendChild(style);
  }

  // Remove any existing modal
  const old = document.getElementById('vastai-offer-modal-overlay');
  if (old) old.remove();

  // Create overlay
  const overlay = document.createElement('div');
  overlay.className = 'vastai-modal-overlay';
  overlay.id = 'vastai-offer-modal-overlay';

  // Modal content
  const modal = document.createElement('div');
  modal.className = 'vastai-modal';

  // Close button
  const closeBtn = document.createElement('button');
  closeBtn.className = 'vastai-modal-close';
  closeBtn.innerHTML = '&times;';
  closeBtn.onclick = () => overlay.remove();
  modal.appendChild(closeBtn);

  // Title
  const title = document.createElement('h2');
  title.textContent = 'Offer Details';
  modal.appendChild(title);

  // Details table
  const table = document.createElement('table');
  details.forEach(row => {
    const tr = document.createElement('tr');
    const tdLabel = document.createElement('td');
    tdLabel.textContent = row.label;
    const tdValue = document.createElement('td');
    tdValue.textContent = row.value;
    tr.appendChild(tdLabel);
    tr.appendChild(tdValue);
    table.appendChild(tr);
  });
  modal.appendChild(table);

  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  // Close modal on overlay click (but not when clicking inside modal)
  overlay.addEventListener('click', function(e) {
    if (e.target === overlay) overlay.remove();
  });
}

/**
 * Show instance details in an overlay modal
 * @param {number} instanceId - ID of the instance to show details for
 */
export async function showInstanceDetails(instanceId) {
  try {
    // Get the raw instance data from the API
    const data = await api.get(`/vastai/instances/${instanceId}`);
    
    if (!data || data.success === false) {
      const msg = (data && data.message) ? data.message : 'Unknown error';
      showSetupResult(`Failed to get instance details: ${msg}`, 'error');
      return;
    }
    
    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'instance-details-overlay';
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.8);
      z-index: 10000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      box-sizing: border-box;
    `;
    
    // Create modal content
    const modal = document.createElement('div');
    modal.style.cssText = `
      background: var(--bg-primary, #ffffff);
      color: var(--text-primary, #000000);
      border-radius: 8px;
      max-width: 90vw;
      max-height: 90vh;
      overflow-y: auto;
      padding: 20px;
      position: relative;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    `;
    
    // Create close button
    const closeBtn = document.createElement('button');
    closeBtn.innerHTML = '×';
    closeBtn.style.cssText = `
      position: absolute;
      top: 10px;
      right: 15px;
      background: none;
      border: none;
      font-size: 24px;
      cursor: pointer;
      color: var(--text-secondary, #666);
      padding: 0;
      width: 30px;
      height: 30px;
      display: flex;
      align-items: center;
      justify-content: center;
    `;
    
    // Create content
    const content = document.createElement('div');
    content.innerHTML = `
      <h2 style="margin-top: 0; margin-bottom: 20px; color: var(--text-primary, #000);">
        Instance #${instanceId} - Raw Details
      </h2>
      <pre style="
        background: var(--bg-secondary, #f5f5f5);
        color: var(--text-primary, #000);
        padding: 15px;
        border-radius: 4px;
        overflow-x: auto;
        white-space: pre-wrap;
        word-wrap: break-word;
        font-family: 'Courier New', Consolas, monospace;
        font-size: 12px;
        line-height: 1.4;
        max-height: 70vh;
        overflow-y: auto;
        border: 1px solid var(--border-color, #ddd);
      ">${JSON.stringify(data.instance, null, 2)}</pre>
    `;
    
    // Assemble modal
    modal.appendChild(closeBtn);
    modal.appendChild(content);
    overlay.appendChild(modal);
    
    // Close handlers
    const closeOverlay = () => {
      if (overlay.parentNode) {
        overlay.parentNode.removeChild(overlay);
      }
    };
    
    closeBtn.addEventListener('click', closeOverlay);
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        closeOverlay();
      }
    });
    
    // Escape key handler
    const escapeHandler = (e) => {
      if (e.key === 'Escape') {
        closeOverlay();
        document.removeEventListener('keydown', escapeHandler);
      }
    };
    document.addEventListener('keydown', escapeHandler);
    
    // Add to page
    document.body.appendChild(overlay);
    
  } catch (error) {
    showSetupResult(`Failed to get instance details: ${error.message}`, 'error');
  }
}

/**
 * Open the search offers modal
 */
export function openSearchOffersModal() {
  const overlay = document.getElementById('searchOffersOverlay');
  if (overlay) {
    overlay.style.display = 'flex';
    // Initialize pill bar after modal opens (if search module is loaded)
    if (window.VastAISearch && window.VastAISearch.initializePillBar) {
      window.VastAISearch.initializePillBar();
    }
  }
}

/**
 * Close the search offers modal
 */
export function closeSearchOffersModal() {
  const overlay = document.getElementById('searchOffersOverlay');
  if (overlay) {
    overlay.style.display = 'none';
    // Clean up any open editors (if search module is loaded)
    if (window.VastAISearch && window.VastAISearch.closePillEditor) {
      window.VastAISearch.closePillEditor();
    }
  }
}

console.log('📄 VastAI UI module loaded');