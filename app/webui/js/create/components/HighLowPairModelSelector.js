/**
 * High-Low Pair Model Selector Component
 * Dropdown for selecting model pairs (e.g., WAN 2.2 high/low noise 14B models)
 */

class HighLowPairModelSelector {
    /**
     * Create a high-low pair model selector
     * @param {Object} config - Configuration from webui.yml
     * @param {string} config.id - Input ID
     * @param {string} config.label - Display label
     * @param {string} config.description - Help text
     * @param {string} config.model_type - Type of models to scan
     * @param {string} config.default_high - Default high noise model path
     * @param {string} config.default_low - Default low noise model path
     * @param {boolean} config.required - Whether selection is required
     * @param {Function} onChange - Callback when selection changes
     */
    constructor(config, onChange) {
        this.id = config.id;
        this.label = config.label || 'Model Pair';
        this.description = config.description || '';
        this.modelType = config.model_type || 'diffusion_models';
        this.defaultHigh = config.default_high || '';
        this.defaultLow = config.default_low || '';
        this.required = config.required || false;
        this.onChange = onChange || (() => {});
        
        this.element = null;
        this.selectElement = null;
        this.refreshButton = null;
        this.loadingIndicator = null;
        this.detailsContainer = null;
        this.models = [];
        this.selectedModel = null;
        this.sshConnection = null;
        this.isLoading = false;
    }

    /**
     * Set the SSH connection string for model scanning
     * @param {string} sshConnection - SSH connection string
     */
    setSSHConnection(sshConnection) {
        this.sshConnection = sshConnection;
    }

    /**
     * Render the component
     * @returns {HTMLElement}
     */
    render() {
        this.element = document.createElement('div');
        this.element.className = 'create-form-field model-selector high-low-pair-selector';
        this.element.id = `field-${this.id}`;

        // Label
        const label = document.createElement('label');
        label.htmlFor = `select-${this.id}`;
        label.textContent = this.label;
        if (this.required) {
            label.classList.add('required');
        }

        // Description
        let descriptionEl = null;
        if (this.description) {
            descriptionEl = document.createElement('div');
            descriptionEl.className = 'field-description';
            descriptionEl.textContent = this.description;
        }

        // Dropdown container
        const dropdownContainer = document.createElement('div');
        dropdownContainer.className = 'model-dropdown-container';

        // Select element
        this.selectElement = document.createElement('select');
        this.selectElement.id = `select-${this.id}`;
        this.selectElement.className = 'model-select';
        this.selectElement.addEventListener('change', () => this._handleSelectionChange());

        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = '-- Select Model Pair --';
        this.selectElement.appendChild(defaultOption);

        // Refresh button
        this.refreshButton = document.createElement('button');
        this.refreshButton.type = 'button';
        this.refreshButton.className = 'model-refresh-btn';
        this.refreshButton.innerHTML = '🔄';
        this.refreshButton.title = 'Refresh model list';
        this.refreshButton.addEventListener('click', () => this.refreshModels(true));

        // Loading indicator
        this.loadingIndicator = document.createElement('span');
        this.loadingIndicator.className = 'model-loading-indicator';
        this.loadingIndicator.innerHTML = '⏳';
        this.loadingIndicator.style.display = 'none';

        dropdownContainer.appendChild(this.selectElement);
        dropdownContainer.appendChild(this.refreshButton);
        dropdownContainer.appendChild(this.loadingIndicator);

        // Details container (shows selected model paths)
        this.detailsContainer = document.createElement('div');
        this.detailsContainer.className = 'model-pair-details';
        this.detailsContainer.style.display = 'none';

        // Assemble
        this.element.appendChild(label);
        if (descriptionEl) {
            this.element.appendChild(descriptionEl);
        }
        this.element.appendChild(dropdownContainer);
        this.element.appendChild(this.detailsContainer);

        return this.element;
    }

    /**
     * Refresh the model list from the server
     * @param {boolean} forceRefresh - Force refresh bypassing cache
     */
    async refreshModels(forceRefresh = false) {
        if (!this.sshConnection) {
            console.warn(`[HighLowPairModelSelector] No SSH connection set for ${this.id}`);
            this._showNoConnection();
            return;
        }

        if (this.isLoading) {
            return;
        }

        this.isLoading = true;
        this._showLoading(true);

        try {
            // Use modelScannerService if available
            if (typeof modelScannerService !== 'undefined') {
                this.models = await modelScannerService.scanHighLowPairs(
                    this.sshConnection,
                    this.modelType,
                    forceRefresh
                );
            } else {
                // Fallback to direct fetch
                const response = await fetch('/api/models/scan', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        ssh_connection: this.sshConnection,
                        model_type: this.modelType,
                        search_pattern: 'high_low_pair',
                        force_refresh: forceRefresh
                    })
                });
                const data = await response.json();
                if (data.success) {
                    this.models = data.models;
                } else {
                    throw new Error(data.message || 'Failed to scan models');
                }
            }

            this._renderDropdownOptions();
            this._selectDefaultOrFirst();

        } catch (error) {
            console.error(`[HighLowPairModelSelector] Error refreshing models for ${this.id}:`, error);
            this._showError(error.message);
        } finally {
            this.isLoading = false;
            this._showLoading(false);
        }
    }

    /**
     * Render dropdown options from models list
     * @private
     */
    _renderDropdownOptions() {
        // Clear existing options except first default option
        while (this.selectElement.options.length > 1) {
            this.selectElement.remove(1);
        }

        // Add model options
        for (let i = 0; i < this.models.length; i++) {
            const model = this.models[i];
            const option = document.createElement('option');
            option.value = String(i); // Use index as value
            option.textContent = model.displayName;
            if (model.size) {
                option.textContent += ` (${this._formatSize(model.size)})`;
            }
            this.selectElement.appendChild(option);
        }
    }

    /**
     * Select default model or first available
     * @private
     */
    _selectDefaultOrFirst() {
        // Try to select default value
        if (this.defaultHigh || this.defaultLow) {
            const defaultIndex = this.models.findIndex(m => 
                m.highNoisePath === this.defaultHigh ||
                m.lowNoisePath === this.defaultLow ||
                m.highNoisePath.includes(this.defaultHigh) ||
                m.lowNoisePath.includes(this.defaultLow)
            );
            if (defaultIndex >= 0) {
                this.selectElement.selectedIndex = defaultIndex + 1; // +1 for default option
                this._handleSelectionChange();
                return;
            }
        }

        // Select first model if required and no default
        if (this.required && this.models.length > 0) {
            this.selectElement.selectedIndex = 1;
            this._handleSelectionChange();
        }
    }

    /**
     * Handle selection change
     * @private
     */
    _handleSelectionChange() {
        const selectedOption = this.selectElement.options[this.selectElement.selectedIndex];
        
        if (selectedOption && selectedOption.value !== '') {
            const index = parseInt(selectedOption.value, 10);
            this.selectedModel = this.models[index] || null;
            this._showDetails();
        } else {
            this.selectedModel = null;
            this.detailsContainer.style.display = 'none';
        }

        this.onChange(this.id, this.getValue());
    }

    /**
     * Show details of selected model pair
     * @private
     */
    _showDetails() {
        if (!this.selectedModel) {
            this.detailsContainer.style.display = 'none';
            return;
        }

        this.detailsContainer.innerHTML = `
            <div class="model-pair-detail">
                <span class="model-pair-label">High Noise:</span>
                <span class="model-pair-path" title="${this._escapeHtml(this.selectedModel.highNoisePath)}">
                    ${this._escapeHtml(this._getFileName(this.selectedModel.highNoisePath))}
                </span>
            </div>
            <div class="model-pair-detail">
                <span class="model-pair-label">Low Noise:</span>
                <span class="model-pair-path" title="${this._escapeHtml(this.selectedModel.lowNoisePath)}">
                    ${this._escapeHtml(this._getFileName(this.selectedModel.lowNoisePath))}
                </span>
            </div>
        `;
        this.detailsContainer.style.display = 'block';
    }

    /**
     * Get the current value
     * @returns {Object|null} Selected model pair or null
     */
    getValue() {
        if (!this.selectedModel) return null;
        
        return {
            displayName: this.selectedModel.displayName,
            highNoisePath: this.selectedModel.highNoisePath,
            lowNoisePath: this.selectedModel.lowNoisePath,
            basePath: this.selectedModel.basePath,
            size: this.selectedModel.size
        };
    }

    /**
     * Set the value programmatically
     * @param {Object} value - Model pair object
     */
    setValue(value) {
        if (!value) {
            this.selectElement.selectedIndex = 0;
            this._handleSelectionChange();
            return;
        }

        // Find matching model
        const index = this.models.findIndex(m => 
            m.highNoisePath === value.highNoisePath ||
            m.lowNoisePath === value.lowNoisePath
        );

        if (index >= 0) {
            this.selectElement.selectedIndex = index + 1;
            this._handleSelectionChange();
        }
    }

    /**
     * Show loading state
     * @private
     */
    _showLoading(show) {
        this.loadingIndicator.style.display = show ? 'inline' : 'none';
        this.refreshButton.disabled = show;
        this.selectElement.disabled = show;
    }

    /**
     * Show no connection message
     * @private
     */
    _showNoConnection() {
        // Clear options except default
        while (this.selectElement.options.length > 1) {
            this.selectElement.remove(1);
        }
        
        const option = document.createElement('option');
        option.value = '';
        option.textContent = '⚠️ Enter SSH connection to load models';
        option.disabled = true;
        this.selectElement.appendChild(option);
        
        this.detailsContainer.style.display = 'none';
    }

    /**
     * Show error message
     * @private
     */
    _showError(message) {
        // Clear options except default
        while (this.selectElement.options.length > 1) {
            this.selectElement.remove(1);
        }
        
        const option = document.createElement('option');
        option.value = '';
        option.textContent = `❌ Error: ${message}`;
        option.disabled = true;
        this.selectElement.appendChild(option);
        
        this.detailsContainer.style.display = 'none';
    }

    /**
     * Format file size for display
     * @private
     */
    _formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
    }

    /**
     * Get filename from path
     * @private
     */
    _getFileName(path) {
        return path.split('/').pop();
    }

    /**
     * Escape HTML to prevent XSS
     * @private
     */
    _escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

// Export for use in HTML
if (typeof window !== 'undefined') {
    window.HighLowPairModelSelector = HighLowPairModelSelector;
}
