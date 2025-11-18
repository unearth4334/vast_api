// ==============================
// Progress Indicators Module
// ==============================
// Manages progress and completion indicators for workflow steps

/**
 * Progress indicator manager
 * Handles creating, updating, and removing progress indicators for workflow steps
 */
class ProgressIndicatorManager {
  constructor() {
    this.timers = new Map(); // Track timers for each step
    this.startTimes = new Map(); // Track start times for duration calculation
  }

  /**
   * Get or create indicator container for a step
   * @param {HTMLElement} stepElement - The workflow step element
   * @returns {HTMLElement} - The indicator container
   */
  getIndicatorContainer(stepElement) {
    let container = stepElement.querySelector('.step-indicator-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'step-indicator-container';
      stepElement.appendChild(container);
    }
    return container;
  }

  /**
   * Clear all indicators for a step
   * @param {HTMLElement} stepElement - The workflow step element
   */
  clearIndicators(stepElement) {
    const container = this.getIndicatorContainer(stepElement);
    container.innerHTML = '';
    
    // Clear any running timers
    const action = stepElement.dataset.action;
    if (this.timers.has(action)) {
      clearInterval(this.timers.get(action));
      this.timers.delete(action);
    }
    this.startTimes.delete(action);
  }

  /**
   * Show simple progress indicator
   * @param {HTMLElement} stepElement - The workflow step element
   * @param {string} statusText - Main status text
   * @param {string} detailText - Detail text (optional)
   */
  showSimpleProgress(stepElement, statusText, detailText = '') {
    this.clearIndicators(stepElement);
    const container = this.getIndicatorContainer(stepElement);
    const action = stepElement.dataset.action;
    
    // Track start time
    this.startTimes.set(action, Date.now());
    
    const indicator = document.createElement('div');
    indicator.className = 'step-progress-indicator simple';
    indicator.setAttribute('role', 'status');
    indicator.setAttribute('aria-live', 'polite');
    
    indicator.innerHTML = `
      <div class="progress-spinner"></div>
      <div class="progress-message">
        <span class="status-text">${this.escapeHtml(statusText)}</span>
        ${detailText ? `<span class="progress-detail">${this.escapeHtml(detailText)}</span>` : ''}
      </div>
      <div class="progress-timer">0s</div>
    `;
    
    container.appendChild(indicator);
    
    // Start timer
    this.startTimer(action, indicator.querySelector('.progress-timer'));
  }

  /**
   * Show multi-phase progress indicator
   * @param {HTMLElement} stepElement - The workflow step element
   * @param {Array<{label: string, status?: string}>} phases - Array of phases
   * @param {number} activePhaseIndex - Index of currently active phase (0-based)
   * @param {number} progressPercent - Overall progress percentage (0-100)
   */
  showMultiPhaseProgress(stepElement, phases, activePhaseIndex = 0, progressPercent = 0) {
    this.clearIndicators(stepElement);
    const container = this.getIndicatorContainer(stepElement);
    const action = stepElement.dataset.action;
    
    // Track start time
    if (!this.startTimes.has(action)) {
      this.startTimes.set(action, Date.now());
    }
    
    const indicator = document.createElement('div');
    indicator.className = 'step-progress-indicator multi-phase';
    indicator.setAttribute('role', 'status');
    indicator.setAttribute('aria-live', 'polite');
    
    const phasesHTML = phases.map((phase, index) => {
      let phaseClass = 'pending';
      let iconHTML = '<div class="phase-dot"></div>';
      
      if (index < activePhaseIndex) {
        phaseClass = 'completed';
        iconHTML = '<span class="folder-icon">✓</span>';
      } else if (index === activePhaseIndex) {
        phaseClass = 'active';
        iconHTML = '<div class="phase-spinner"></div>';
      }
      
      return `
        <div class="phase ${phaseClass}">
          ${iconHTML}
          <span class="phase-label">${this.escapeHtml(phase.label)}</span>
          ${phase.status ? `<span class="phase-status">${this.escapeHtml(phase.status)}</span>` : ''}
        </div>
      `;
    }).join('');
    
    indicator.innerHTML = `
      <div class="progress-phases">
        ${phasesHTML}
      </div>
      <div class="progress-bar-container">
        <div class="progress-bar" style="width: ${progressPercent}%"></div>
      </div>
      <div class="progress-timer">0s</div>
    `;
    
    container.appendChild(indicator);
    
    // Start timer if not already running
    if (!this.timers.has(action)) {
      this.startTimer(action, indicator.querySelector('.progress-timer'));
    }
  }

  /**
   * Show checklist progress indicator
   * @param {HTMLElement} stepElement - The workflow step element
   * @param {Array<{label: string, state: 'pending'|'active'|'completed'}>} items - Checklist items
   */
  showChecklistProgress(stepElement, items) {
    this.clearIndicators(stepElement);
    const container = this.getIndicatorContainer(stepElement);
    const action = stepElement.dataset.action;
    
    // Track start time
    if (!this.startTimes.has(action)) {
      this.startTimes.set(action, Date.now());
    }
    
    const indicator = document.createElement('div');
    indicator.className = 'step-progress-indicator';
    indicator.setAttribute('role', 'status');
    indicator.setAttribute('aria-live', 'polite');
    
    const itemsHTML = items.map(item => {
      let iconHTML = '<div class="check-dot"></div>';
      if (item.state === 'active') {
        iconHTML = '<div class="check-spinner"></div>';
      } else if (item.state === 'completed') {
        iconHTML = '<span class="folder-icon">✓</span>';
      }
      
      return `
        <div class="check-item ${item.state}">
          ${iconHTML}
          <span>${this.escapeHtml(item.label)}</span>
        </div>
      `;
    }).join('');
    
    indicator.innerHTML = `
      <div class="progress-checklist">
        ${itemsHTML}
      </div>
      <div class="progress-timer">0s</div>
    `;
    
    container.appendChild(indicator);
    
    // Start timer if not already running
    if (!this.timers.has(action)) {
      this.startTimer(action, indicator.querySelector('.progress-timer'));
    }
  }

  /**
   * Show git clone progress indicator
   * @param {HTMLElement} stepElement - The workflow step element
   * @param {string} action - Current action ("Cloning repository..." etc)
   * @param {string} url - Repository URL
   * @param {string} progress - Progress text (e.g., "Receiving objects: 45% (123/273)")
   * @param {number} progressPercent - Progress percentage (0-100)
   * @param {string} dataReceived - Data received text (e.g., "2.3 MB")
   */
  showGitProgress(stepElement, action, url, progress = '', progressPercent = 0, dataReceived = '') {
    this.clearIndicators(stepElement);
    const container = this.getIndicatorContainer(stepElement);
    const stepAction = stepElement.dataset.action;
    
    // Track start time
    if (!this.startTimes.has(stepAction)) {
      this.startTimes.set(stepAction, Date.now());
    }
    
    const indicator = document.createElement('div');
    indicator.className = 'step-progress-indicator git-clone';
    indicator.setAttribute('role', 'status');
    indicator.setAttribute('aria-live', 'polite');
    
    indicator.innerHTML = `
      <div class="progress-git">
        <div class="git-status">
          <div class="git-spinner"></div>
          <span class="git-action">${this.escapeHtml(action)}</span>
        </div>
        <div class="git-details">
          <span class="git-url">${this.escapeHtml(url)}</span>
          ${progress ? `<span class="git-progress">${this.escapeHtml(progress)}</span>` : ''}
        </div>
      </div>
      <div class="progress-bar-container">
        <div class="progress-bar" style="width: ${progressPercent}%"></div>
      </div>
      <div class="progress-stats">
        ${dataReceived ? `<span class="data-received">${this.escapeHtml(dataReceived)}</span>` : '<span></span>'}
        <span class="timer">0s</span>
      </div>
    `;
    
    container.appendChild(indicator);
    
    // Start timer if not already running
    if (!this.timers.has(stepAction)) {
      this.startTimer(stepAction, indicator.querySelector('.timer'));
    }
  }

  /**
   * Show sync progress indicator
   * @param {HTMLElement} stepElement - The workflow step element
   * @param {string} stage - Current stage text
   * @param {string} detail - Detail text
   * @param {Array<{name: string, state: 'pending'|'active'|'completed', stats: string}>} folders - Folder progress
   * @param {number} progressPercent - Overall progress percentage
   * @param {string} progressText - Progress text (e.g., "42% • 57/135 files • 234 MB")
   * @param {Object} stats - Stats object {speed: string, eta: string}
   */
  showSyncProgress(stepElement, stage, detail, folders = [], progressPercent = 0, progressText = '', stats = {}) {
    this.clearIndicators(stepElement);
    const container = this.getIndicatorContainer(stepElement);
    const action = stepElement.dataset.action;
    
    // Track start time
    if (!this.startTimes.has(action)) {
      this.startTimes.set(action, Date.now());
    }
    
    const indicator = document.createElement('div');
    indicator.className = 'step-progress-indicator sync';
    indicator.setAttribute('role', 'status');
    indicator.setAttribute('aria-live', 'polite');
    
    const foldersHTML = folders.length > 0 ? `
      <div class="sync-folders">
        ${folders.map(folder => {
          let iconHTML = '<span class="folder-icon">○</span>';
          if (folder.state === 'active') {
            iconHTML = '<div class="folder-spinner"></div>';
          } else if (folder.state === 'completed') {
            iconHTML = '<span class="folder-icon">✓</span>';
          }
          
          return `
            <div class="folder-progress ${folder.state}">
              ${iconHTML}
              <span class="folder-name">${this.escapeHtml(folder.name)}</span>
              <span class="folder-stats">${this.escapeHtml(folder.stats)}</span>
            </div>
          `;
        }).join('')}
      </div>
    ` : '';
    
    indicator.innerHTML = `
      <div class="sync-overview">
        <div class="sync-spinner"></div>
        <div class="sync-status">
          <span class="sync-stage">${this.escapeHtml(stage)}</span>
          <span class="sync-detail">${this.escapeHtml(detail)}</span>
        </div>
      </div>
      ${foldersHTML}
      <div class="sync-progress-bar">
        <div class="progress-fill" style="width: ${progressPercent}%"></div>
        ${progressText ? `<span class="progress-text">${this.escapeHtml(progressText)}</span>` : ''}
      </div>
      <div class="sync-stats">
        ${stats.speed ? `<span class="speed">${this.escapeHtml(stats.speed)}</span>` : '<span></span>'}
        ${stats.eta ? `<span class="eta">${this.escapeHtml(stats.eta)}</span>` : '<span></span>'}
        <span class="timer">0s</span>
      </div>
    `;
    
    container.appendChild(indicator);
    
    // Start timer if not already running
    if (!this.timers.has(action)) {
      this.startTimer(action, indicator.querySelector('.timer'));
    }
  }

  /**
   * Show success completion indicator
   * @param {HTMLElement} stepElement - The workflow step element
   * @param {string} text - Completion text
   * @param {string} details - Detail text
   * @param {Array<string>} stats - Array of stat strings (e.g., ["📦 3 packages", "⏱️ 12.4s"])
   * @param {Object} options - Additional options {actions: Array, breakdown: Object}
   */
  showSuccess(stepElement, text, details, stats = [], options = {}) {
    this.clearIndicators(stepElement);
    const container = this.getIndicatorContainer(stepElement);
    const action = stepElement.dataset.action;
    
    // Calculate duration
    const duration = this.getDuration(action);
    
    const indicator = document.createElement('div');
    indicator.className = 'step-completion-indicator success';
    if (options.syncComplete) {
      indicator.classList.add('sync-complete');
    }
    indicator.setAttribute('role', 'alert');
    indicator.setAttribute('aria-live', 'assertive');
    
    const statsHTML = stats.length > 0 ? `
      <div class="completion-stats">
        ${stats.map(stat => `<span class="stat">${this.escapeHtml(stat)}</span>`).join('')}
      </div>
    ` : '';
    
    const actionsHTML = options.actions && options.actions.length > 0 ? `
      <div class="completion-action">
        ${options.actions.map(btn => 
          `<button class="${btn.class}" onclick="${btn.onclick}">${this.escapeHtml(btn.label)}</button>`
        ).join('')}
      </div>
    ` : '';
    
    const breakdownHTML = options.breakdown ? `
      <div class="completion-breakdown">
        <div class="sync-summary">
          ${options.breakdown.items.map(item => `
            <div class="summary-item">
              <span class="item-label">${this.escapeHtml(item.label)}:</span>
              <span class="item-value">${this.escapeHtml(item.value)}</span>
            </div>
          `).join('')}
          ${options.breakdown.more ? `<div class="summary-more">${this.escapeHtml(options.breakdown.more)}</div>` : ''}
        </div>
      </div>
    ` : '';
    
    indicator.innerHTML = `
      <div class="completion-icon">✅</div>
      <div class="completion-message">
        <span class="completion-text">${this.escapeHtml(text)}</span>
        <span class="completion-details">${this.escapeHtml(details)}</span>
      </div>
      <div class="completion-time">${duration}</div>
      ${statsHTML}
      ${breakdownHTML}
      ${actionsHTML}
    `;
    
    container.appendChild(indicator);
  }

  /**
   * Show error completion indicator
   * @param {HTMLElement} stepElement - The workflow step element
   * @param {string} text - Error text
   * @param {string} details - Detail text
   * @param {Array<Object>} actions - Array of action button configs
   * @param {Array<Object>} errors - Array of error items for breakdown
   */
  showError(stepElement, text, details, actions = [], errors = []) {
    this.clearIndicators(stepElement);
    const container = this.getIndicatorContainer(stepElement);
    const action = stepElement.dataset.action;
    
    // Calculate duration
    const duration = this.getDuration(action);
    
    const indicator = document.createElement('div');
    indicator.className = 'step-completion-indicator error';
    indicator.setAttribute('role', 'alert');
    indicator.setAttribute('aria-live', 'assertive');
    
    const actionsHTML = actions.length > 0 ? `
      <div class="completion-action">
        ${actions.map(btn => 
          `<button class="${btn.class}" onclick="${btn.onclick}">${this.escapeHtml(btn.label)}</button>`
        ).join('')}
      </div>
    ` : '';
    
    const errorsHTML = errors.length > 0 ? `
      <div class="completion-breakdown">
        <div class="error-summary">
          ${errors.map(error => `
            <div class="error-item">
              <span class="error-icon">❌</span>
              <span>${this.escapeHtml(error)}</span>
            </div>
          `).join('')}
        </div>
      </div>
    ` : '';
    
    indicator.innerHTML = `
      <div class="completion-icon">❌</div>
      <div class="completion-message">
        <span class="completion-text">${this.escapeHtml(text)}</span>
        <span class="completion-details">${this.escapeHtml(details)}</span>
      </div>
      <div class="completion-time">${duration}</div>
      ${errorsHTML}
      ${actionsHTML}
    `;
    
    container.appendChild(indicator);
  }

  /**
   * Show warning completion indicator
   * @param {HTMLElement} stepElement - The workflow step element
   * @param {string} text - Warning text
   * @param {string} details - Detail text
   * @param {Array<Object>} actions - Array of action button configs
   */
  showWarning(stepElement, text, details, actions = []) {
    this.clearIndicators(stepElement);
    const container = this.getIndicatorContainer(stepElement);
    const action = stepElement.dataset.action;
    
    // Calculate duration
    const duration = this.getDuration(action);
    
    const indicator = document.createElement('div');
    indicator.className = 'step-completion-indicator warning';
    indicator.setAttribute('role', 'alert');
    indicator.setAttribute('aria-live', 'assertive');
    
    const actionsHTML = actions.length > 0 ? `
      <div class="completion-action">
        ${actions.map(btn => 
          `<button class="${btn.class}" onclick="${btn.onclick}">${this.escapeHtml(btn.label)}</button>`
        ).join('')}
      </div>
    ` : '';
    
    indicator.innerHTML = `
      <div class="completion-icon">⚠️</div>
      <div class="completion-message">
        <span class="completion-text">${this.escapeHtml(text)}</span>
        <span class="completion-details">${this.escapeHtml(details)}</span>
      </div>
      <div class="completion-time">${duration}</div>
      ${actionsHTML}
    `;
    
    container.appendChild(indicator);
  }

  /**
   * Start a timer for a step
   * @param {string} action - Step action identifier
   * @param {HTMLElement} timerElement - Timer element to update
   */
  startTimer(action, timerElement) {
    if (!timerElement) return;
    
    const startTime = this.startTimes.get(action) || Date.now();
    
    const updateTimer = () => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      timerElement.textContent = `${elapsed}s`;
    };
    
    // Update immediately
    updateTimer();
    
    // Update every second
    const intervalId = setInterval(updateTimer, 1000);
    this.timers.set(action, intervalId);
  }

  /**
   * Get formatted duration for a step
   * @param {string} action - Step action identifier
   * @returns {string} - Formatted duration (e.g., "2.3s")
   */
  getDuration(action) {
    const startTime = this.startTimes.get(action);
    if (!startTime) return '0s';
    
    const elapsed = (Date.now() - startTime) / 1000;
    return elapsed < 10 ? `${elapsed.toFixed(1)}s` : `${Math.floor(elapsed)}s`;
  }

  /**
   * Update an existing progress indicator
   * This allows for real-time updates without recreating the entire indicator
   * @param {HTMLElement} stepElement - The workflow step element
   * @param {Object} updates - Object with properties to update
   */
  updateProgress(stepElement, updates) {
    const container = stepElement.querySelector('.step-indicator-container');
    if (!container) return;
    
    const indicator = container.querySelector('.step-progress-indicator');
    if (!indicator) return;
    
    // Update progress bar
    if (updates.progressPercent !== undefined) {
      const progressBar = indicator.querySelector('.progress-bar, .progress-fill');
      if (progressBar) {
        progressBar.style.width = `${updates.progressPercent}%`;
      }
    }
    
    // Update progress text
    if (updates.progressText !== undefined) {
      const progressText = indicator.querySelector('.progress-text, .git-progress');
      if (progressText) {
        progressText.textContent = updates.progressText;
      }
    }
    
    // Update phase status
    if (updates.phaseStatus !== undefined && updates.phaseIndex !== undefined) {
      const phases = indicator.querySelectorAll('.phase');
      if (phases[updates.phaseIndex]) {
        const statusSpan = phases[updates.phaseIndex].querySelector('.phase-status');
        if (statusSpan) {
          statusSpan.textContent = updates.phaseStatus;
        }
      }
    }
    
    // Update active phase
    if (updates.activePhaseIndex !== undefined) {
      const phases = indicator.querySelectorAll('.phase');
      phases.forEach((phase, index) => {
        phase.classList.remove('active', 'completed', 'pending');
        if (index < updates.activePhaseIndex) {
          phase.classList.add('completed');
          const icon = phase.querySelector('.phase-spinner, .phase-dot, .folder-icon');
          if (icon) {
            icon.outerHTML = '<span class="folder-icon">✓</span>';
          }
        } else if (index === updates.activePhaseIndex) {
          phase.classList.add('active');
          const icon = phase.querySelector('.phase-dot, .folder-icon');
          if (icon && icon.classList.contains('phase-dot')) {
            icon.outerHTML = '<div class="phase-spinner"></div>';
          }
        } else {
          phase.classList.add('pending');
        }
      });
    }
    
    // Update sync stats
    if (updates.speed !== undefined) {
      const speed = indicator.querySelector('.speed');
      if (speed) speed.textContent = updates.speed;
    }
    
    if (updates.eta !== undefined) {
      const eta = indicator.querySelector('.eta');
      if (eta) eta.textContent = updates.eta;
    }
    
    // Update folders
    if (updates.folders !== undefined) {
      const foldersContainer = indicator.querySelector('.sync-folders');
      if (foldersContainer) {
        foldersContainer.innerHTML = updates.folders.map(folder => {
          let iconHTML = '<span class="folder-icon">○</span>';
          if (folder.state === 'active') {
            iconHTML = '<div class="folder-spinner"></div>';
          } else if (folder.state === 'completed') {
            iconHTML = '<span class="folder-icon">✓</span>';
          }
          
          return `
            <div class="folder-progress ${folder.state}">
              ${iconHTML}
              <span class="folder-name">${this.escapeHtml(folder.name)}</span>
              <span class="folder-stats">${this.escapeHtml(folder.stats)}</span>
            </div>
          `;
        }).join('');
      }
    }
  }

  /**
   * Escape HTML to prevent XSS
   * @param {string} text - Text to escape
   * @returns {string} - Escaped text
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Create a global instance
window.progressIndicators = new ProgressIndicatorManager();

console.log('📊 Progress Indicators module loaded');
