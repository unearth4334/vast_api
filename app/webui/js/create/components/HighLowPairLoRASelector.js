/**
 * High-Low Pair LoRA Selector Component
 * Multi-select component for LoRAs that come in high-noise/low-noise pairs
 */

class HighLowPairLoRASelector {
    /**
     * Create a high-low pair LoRA selector
     * @param {Object} config - Configuration from webui.yml
     * @param {string} config.id - Input ID
     * @param {string} config.label - Display label
     * @param {string} config.description - Help text
     * @param {string} config.model_type - Type of models to scan (usually 'loras')
     * @param {number} config.max_items - Maximum number of LoRAs allowed
     * @param {boolean} config.required - Whether at least one LoRA is required
     * @param {Function} onChange - Callback when selection changes
     */
    constructor(config, onChange) {
        this.id = config.id;
        this.label = config.label || 'LoRAs';
        this.description = config.description || '';
        this.modelType = config.model_type || 'loras';
        this.maxItems = config.max_items || 5;
        this.required = config.required || false;
        this.onChange = onChange || (() => {});
        
        this.element = null;
        this.selectElement = null;
        this.refreshButton = null;
        this.loadingIndicator = null;
        this.loraListContainer = null;
        this.addButton = null;
        
        this.availableLoras = [];
        this.addedLoras = [];
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
        this.element.className = 'create-form-field model-selector high-low-pair-lora-selector';
        this.element.id = `field-${this.id}`;

        // Label
        const label = document.createElement('label');
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

        // Dropdown container for adding LoRAs
        const addContainer = document.createElement('div');
        addContainer.className = 'lora-add-container';

        // Select element for available LoRAs
        this.selectElement = document.createElement('select');
        this.selectElement.id = `select-${this.id}`;
        this.selectElement.className = 'lora-select';

        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = '-- Select LoRA to add --';
        this.selectElement.appendChild(defaultOption);

        // Add button
        this.addButton = document.createElement('button');
        this.addButton.type = 'button';
        this.addButton.className = 'lora-add-btn';
        this.addButton.innerHTML = '➕ Add';
        this.addButton.title = 'Add selected LoRA';
        this.addButton.addEventListener('click', () => this._handleAddLora());

        // Refresh button
        this.refreshButton = document.createElement('button');
        this.refreshButton.type = 'button';
        this.refreshButton.className = 'model-refresh-btn';
        this.refreshButton.innerHTML = '🔄';
        this.refreshButton.title = 'Refresh LoRA list';
        this.refreshButton.addEventListener('click', () => this.refreshModels(true));

        // Loading indicator
        this.loadingIndicator = document.createElement('span');
        this.loadingIndicator.className = 'model-loading-indicator';
        this.loadingIndicator.innerHTML = '⏳';
        this.loadingIndicator.style.display = 'none';

        addContainer.appendChild(this.selectElement);
        addContainer.appendChild(this.addButton);
        addContainer.appendChild(this.refreshButton);
        addContainer.appendChild(this.loadingIndicator);

        // Container for added LoRAs list
        this.loraListContainer = document.createElement('div');
        this.loraListContainer.className = 'lora-list-container';

        // Assemble
        this.element.appendChild(label);
        if (descriptionEl) {
            this.element.appendChild(descriptionEl);
        }
        this.element.appendChild(addContainer);
        this.element.appendChild(this.loraListContainer);

        return this.element;
    }

    /**
     * Refresh the LoRA list from the server
     * @param {boolean} forceRefresh - Force refresh bypassing cache
     */
    async refreshModels(forceRefresh = false) {
        if (!this.sshConnection) {
            console.warn(`[HighLowPairLoRASelector] No SSH connection set for ${this.id}`);
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
                this.availableLoras = await modelScannerService.scanHighLowPairs(
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
                    this.availableLoras = data.models;
                } else {
                    throw new Error(data.message || 'Failed to scan LoRAs');
                }
            }

            this._renderDropdownOptions();

        } catch (error) {
            console.error(`[HighLowPairLoRASelector] Error refreshing LoRAs for ${this.id}:`, error);
            this._showError(error.message);
        } finally {
            this.isLoading = false;
            this._showLoading(false);
        }
    }

    /**
     * Render dropdown options from available LoRAs
     * @private
     */
    _renderDropdownOptions() {
        // Clear existing options except first default option
        while (this.selectElement.options.length > 1) {
            this.selectElement.remove(1);
        }

        // Add available LoRA options (exclude already added)
        const addedPaths = new Set(this.addedLoras.map(l => l.highNoisePath));
        
        for (let i = 0; i < this.availableLoras.length; i++) {
            const lora = this.availableLoras[i];
            
            // Skip if already added
            if (addedPaths.has(lora.highNoisePath)) {
                continue;
            }
            
            const option = document.createElement('option');
            option.value = String(i);
            option.textContent = lora.displayName;
            if (lora.size) {
                option.textContent += ` (${this._formatSize(lora.size)})`;
            }
            this.selectElement.appendChild(option);
        }

        // Update add button state
        this._updateAddButtonState();
    }

    /**
     * Handle adding a LoRA
     * @private
     */
    _handleAddLora() {
        if (this.addedLoras.length >= this.maxItems) {
            alert(`Maximum ${this.maxItems} LoRAs allowed`);
            return;
        }

        const selectedOption = this.selectElement.options[this.selectElement.selectedIndex];
        if (!selectedOption || selectedOption.value === '') {
            return;
        }

        const index = parseInt(selectedOption.value, 10);
        const lora = this.availableLoras[index];
        
        if (!lora) {
            return;
        }

        // Add to list
        this.addedLoras.push({
            id: `lora_${Date.now()}`,
            displayName: lora.displayName,
            highNoisePath: lora.highNoisePath,
            lowNoisePath: lora.lowNoisePath,
            strength: 1.0
        });

        // Reset selection
        this.selectElement.selectedIndex = 0;
        
        // Re-render
        this._renderDropdownOptions();
        this._renderLoraList();
        
        // Notify change
        this.onChange(this.id, this.getValue());
    }

    /**
     * Handle removing a LoRA
     * @private
     */
    _handleRemoveLora(loraId) {
        this.addedLoras = this.addedLoras.filter(l => l.id !== loraId);
        
        // Re-render
        this._renderDropdownOptions();
        this._renderLoraList();
        
        // Notify change
        this.onChange(this.id, this.getValue());
    }

    /**
     * Handle strength change
     * @private
     */
    _handleStrengthChange(loraId, strength) {
        const lora = this.addedLoras.find(l => l.id === loraId);
        if (lora) {
            lora.strength = parseFloat(strength);
            this.onChange(this.id, this.getValue());
        }
    }

    /**
     * Render the list of added LoRAs
     * @private
     */
    _renderLoraList() {
        if (this.addedLoras.length === 0) {
            this.loraListContainer.innerHTML = '<div class="lora-list-empty">No LoRAs added</div>';
            return;
        }

        this.loraListContainer.innerHTML = '';

        for (const lora of this.addedLoras) {
            const loraItem = document.createElement('div');
            loraItem.className = 'lora-list-item';
            loraItem.dataset.loraId = lora.id;

            // LoRA name and remove button
            const headerDiv = document.createElement('div');
            headerDiv.className = 'lora-item-header';

            const nameSpan = document.createElement('span');
            nameSpan.className = 'lora-item-name';
            nameSpan.textContent = lora.displayName;

            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'lora-remove-btn';
            removeBtn.innerHTML = '❌';
            removeBtn.title = 'Remove LoRA';
            removeBtn.addEventListener('click', () => this._handleRemoveLora(lora.id));

            headerDiv.appendChild(nameSpan);
            headerDiv.appendChild(removeBtn);

            // Strength slider
            const strengthDiv = document.createElement('div');
            strengthDiv.className = 'lora-item-strength';

            const strengthLabel = document.createElement('span');
            strengthLabel.className = 'lora-strength-label';
            strengthLabel.textContent = 'Strength:';

            const strengthSlider = document.createElement('input');
            strengthSlider.type = 'range';
            strengthSlider.className = 'lora-strength-slider';
            strengthSlider.min = '0';
            strengthSlider.max = '2';
            strengthSlider.step = '0.1';
            strengthSlider.value = lora.strength;

            const strengthValue = document.createElement('span');
            strengthValue.className = 'lora-strength-value';
            strengthValue.textContent = lora.strength.toFixed(1);

            strengthSlider.addEventListener('input', (e) => {
                strengthValue.textContent = parseFloat(e.target.value).toFixed(1);
                this._handleStrengthChange(lora.id, e.target.value);
            });

            strengthDiv.appendChild(strengthLabel);
            strengthDiv.appendChild(strengthSlider);
            strengthDiv.appendChild(strengthValue);

            loraItem.appendChild(headerDiv);
            loraItem.appendChild(strengthDiv);

            this.loraListContainer.appendChild(loraItem);
        }
    }

    /**
     * Update add button state
     * @private
     */
    _updateAddButtonState() {
        const canAdd = this.addedLoras.length < this.maxItems &&
                      this.selectElement.options.length > 1;
        this.addButton.disabled = !canAdd;
    }

    /**
     * Get the current value (list of added LoRAs)
     * @returns {Array} List of added LoRA objects
     */
    getValue() {
        return this.addedLoras.map(lora => ({
            id: lora.id,
            displayName: lora.displayName,
            highNoisePath: lora.highNoisePath,
            lowNoisePath: lora.lowNoisePath,
            strength: lora.strength
        }));
    }

    /**
     * Set the value programmatically
     * @param {Array} loras - Array of LoRA objects
     */
    setValue(loras) {
        this.addedLoras = (loras || []).map(lora => ({
            id: lora.id || `lora_${Date.now()}_${Math.random()}`,
            displayName: lora.displayName,
            highNoisePath: lora.highNoisePath,
            lowNoisePath: lora.lowNoisePath,
            strength: lora.strength || 1.0
        }));

        this._renderDropdownOptions();
        this._renderLoraList();
    }

    /**
     * Clear all added LoRAs
     */
    clear() {
        this.addedLoras = [];
        this._renderDropdownOptions();
        this._renderLoraList();
        this.onChange(this.id, this.getValue());
    }

    /**
     * Show loading state
     * @private
     */
    _showLoading(show) {
        this.loadingIndicator.style.display = show ? 'inline' : 'none';
        this.refreshButton.disabled = show;
        this.selectElement.disabled = show;
        this.addButton.disabled = show;
    }

    /**
     * Show no connection message
     * @private
     */
    _showNoConnection() {
        while (this.selectElement.options.length > 1) {
            this.selectElement.remove(1);
        }
        
        const option = document.createElement('option');
        option.value = '';
        option.textContent = '⚠️ Enter SSH connection to load LoRAs';
        option.disabled = true;
        this.selectElement.appendChild(option);
    }

    /**
     * Show error message
     * @private
     */
    _showError(message) {
        while (this.selectElement.options.length > 1) {
            this.selectElement.remove(1);
        }
        
        const option = document.createElement('option');
        option.value = '';
        option.textContent = `❌ Error: ${message}`;
        option.disabled = true;
        this.selectElement.appendChild(option);
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
}

// Export for use in HTML
if (typeof window !== 'undefined') {
    window.HighLowPairLoRASelector = HighLowPairLoRASelector;
}
