/**
 * Feature Toggle Group Component
 * Groups related checkboxes/toggles with optional conditional fields
 */

class FeatureToggleGroup {
    /**
     * Create a feature toggle group
     * @param {Object} config - Configuration
     * @param {string} config.id - Group ID
     * @param {string} config.title - Group title
     * @param {Array} config.toggles - Array of toggle configurations
     * @param {boolean} config.collapsed - Whether group starts collapsed
     * @param {Function} onChange - Callback when any toggle changes
     */
    constructor(config, onChange) {
        this.id = config.id;
        this.title = config.title || 'Features';
        this.toggles = config.toggles || [];
        this.collapsed = config.collapsed || false;
        this.onChange = onChange || (() => {});
        
        this.element = null;
        this.contentElement = null;
        this.toggleButton = null;
        this.toggleElements = new Map();
        this.values = {};
        
        // Initialize values with defaults
        for (const toggle of this.toggles) {
            this.values[toggle.id] = toggle.default !== undefined ? toggle.default : false;
        }
    }

    /**
     * Render the component
     * @returns {HTMLElement}
     */
    render() {
        this.element = document.createElement('div');
        this.element.className = 'feature-toggle-group create-form-section';
        this.element.id = `toggle-group-${this.id}`;

        // Header
        const header = document.createElement('div');
        header.className = 'create-form-section-header';

        const title = document.createElement('h4');
        title.className = 'create-form-section-title';
        title.textContent = this.title;

        this.toggleButton = document.createElement('button');
        this.toggleButton.type = 'button';
        this.toggleButton.className = 'create-form-section-toggle';
        this.toggleButton.textContent = this.collapsed ? '▶' : '▼';
        this.toggleButton.setAttribute('aria-expanded', !this.collapsed);
        if (this.collapsed) {
            this.toggleButton.classList.add('collapsed');
        }
        this.toggleButton.addEventListener('click', () => this._toggleCollapse());

        header.appendChild(title);
        header.appendChild(this.toggleButton);

        // Content container
        this.contentElement = document.createElement('div');
        this.contentElement.className = 'create-form-section-content feature-toggle-content';
        if (this.collapsed) {
            this.contentElement.classList.add('collapsed');
        }

        // Group toggles by category
        const categories = this._groupByCategory(this.toggles);
        
        for (const [category, toggles] of categories) {
            if (category) {
                const categoryLabel = document.createElement('div');
                categoryLabel.className = 'feature-toggle-category';
                categoryLabel.textContent = category;
                this.contentElement.appendChild(categoryLabel);
            }

            for (const toggle of toggles) {
                const toggleElement = this._createToggle(toggle);
                this.contentElement.appendChild(toggleElement);
            }
        }

        this.element.appendChild(header);
        this.element.appendChild(this.contentElement);

        // Apply initial dependency states
        this._updateDependencies();

        return this.element;
    }

    /**
     * Create a single toggle element
     * @private
     */
    _createToggle(toggle) {
        const container = document.createElement('div');
        container.className = 'feature-toggle-item';
        container.id = `toggle-item-${toggle.id}`;
        container.dataset.toggleId = toggle.id;

        // Create checkbox container
        const checkboxContainer = document.createElement('div');
        checkboxContainer.className = 'checkbox-field-container';

        // Checkbox
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `toggle-${toggle.id}`;
        checkbox.checked = this.values[toggle.id];
        checkbox.addEventListener('change', (e) => this._handleToggleChange(toggle.id, e.target.checked));

        // Label
        const label = document.createElement('label');
        label.htmlFor = `toggle-${toggle.id}`;
        label.className = 'checkbox-field-label';
        label.textContent = toggle.label;

        checkboxContainer.appendChild(checkbox);
        checkboxContainer.appendChild(label);

        // Description tooltip
        if (toggle.description) {
            const tooltip = document.createElement('span');
            tooltip.className = 'feature-toggle-tooltip';
            tooltip.innerHTML = 'ℹ️';
            tooltip.title = toggle.description;
            checkboxContainer.appendChild(tooltip);
        }

        container.appendChild(checkboxContainer);

        // Conditional field (e.g., slider that appears when toggle is enabled)
        if (toggle.conditional_field) {
            const conditionalContainer = document.createElement('div');
            conditionalContainer.className = 'feature-toggle-conditional';
            conditionalContainer.id = `conditional-${toggle.id}`;
            conditionalContainer.style.display = this.values[toggle.id] ? 'block' : 'none';

            const conditionalField = this._createConditionalField(toggle.conditional_field);
            conditionalContainer.appendChild(conditionalField);
            container.appendChild(conditionalContainer);
        }

        // Store reference
        this.toggleElements.set(toggle.id, {
            container,
            checkbox,
            conditional: toggle.conditional_field ? document.getElementById(`conditional-${toggle.id}`) : null
        });

        return container;
    }

    /**
     * Create a conditional field (like a slider)
     * @private
     */
    _createConditionalField(config) {
        const container = document.createElement('div');
        container.className = 'create-form-field conditional-field';

        if (config.type === 'slider') {
            const labelEl = document.createElement('label');
            labelEl.textContent = config.label;
            
            const sliderContainer = document.createElement('div');
            sliderContainer.className = 'slider-container';

            const slider = document.createElement('input');
            slider.type = 'range';
            slider.className = 'slider-input';
            slider.id = `conditional-slider-${config.id}`;
            slider.min = config.min || 0;
            slider.max = config.max || 100;
            slider.step = config.step || 1;
            slider.value = config.default !== undefined ? config.default : config.min || 0;

            const valueDisplay = document.createElement('span');
            valueDisplay.className = 'slider-value';
            valueDisplay.textContent = slider.value;

            const unit = config.unit ? document.createElement('span') : null;
            if (unit) {
                unit.className = 'slider-unit';
                unit.textContent = config.unit;
            }

            slider.addEventListener('input', (e) => {
                valueDisplay.textContent = e.target.value;
                this.values[config.id] = parseFloat(e.target.value);
                this.onChange(config.id, this.values[config.id]);
            });

            // Initialize value
            this.values[config.id] = parseFloat(slider.value);

            sliderContainer.appendChild(slider);
            sliderContainer.appendChild(valueDisplay);
            if (unit) sliderContainer.appendChild(unit);

            container.appendChild(labelEl);
            container.appendChild(sliderContainer);
        }

        return container;
    }

    /**
     * Handle toggle change
     * @private
     */
    _handleToggleChange(toggleId, checked) {
        this.values[toggleId] = checked;
        
        // Update conditional field visibility
        const conditionalEl = document.getElementById(`conditional-${toggleId}`);
        if (conditionalEl) {
            conditionalEl.style.display = checked ? 'block' : 'none';
        }

        // Update dependencies
        this._updateDependencies();

        // Notify change
        this.onChange(toggleId, checked);
    }

    /**
     * Group toggles by category
     * @private
     */
    _groupByCategory(toggles) {
        const groups = new Map();
        
        for (const toggle of toggles) {
            const category = toggle.category || '';
            if (!groups.has(category)) {
                groups.set(category, []);
            }
            groups.get(category).push(toggle);
        }

        return groups;
    }

    /**
     * Update toggle visibility based on dependencies
     * @private
     */
    _updateDependencies() {
        for (const toggle of this.toggles) {
            if (toggle.depends_on) {
                const depField = toggle.depends_on.field;
                const depValue = toggle.depends_on.value;
                const actualValue = this.values[depField];
                const shouldShow = actualValue === depValue;

                const element = this.toggleElements.get(toggle.id);
                if (element) {
                    element.container.style.display = shouldShow ? '' : 'none';
                }
            }
        }
    }

    /**
     * Toggle collapse state
     * @private
     */
    _toggleCollapse() {
        this.collapsed = !this.collapsed;
        this.contentElement.classList.toggle('collapsed', this.collapsed);
        this.toggleButton.classList.toggle('collapsed', this.collapsed);
        this.toggleButton.textContent = this.collapsed ? '▶' : '▼';
        this.toggleButton.setAttribute('aria-expanded', !this.collapsed);
    }

    /**
     * Get all values
     * @returns {Object} Object mapping toggle IDs to values
     */
    getValue() {
        return { ...this.values };
    }

    /**
     * Get value for a specific toggle
     * @param {string} toggleId - Toggle ID
     * @returns {any} Toggle value
     */
    getToggleValue(toggleId) {
        return this.values[toggleId];
    }

    /**
     * Set value for a specific toggle
     * @param {string} toggleId - Toggle ID
     * @param {any} value - Value to set
     */
    setToggleValue(toggleId, value) {
        this.values[toggleId] = value;
        
        const element = this.toggleElements.get(toggleId);
        if (element && element.checkbox) {
            element.checkbox.checked = value;
        }

        // Update conditional field visibility
        const conditionalEl = document.getElementById(`conditional-${toggleId}`);
        if (conditionalEl) {
            conditionalEl.style.display = value ? 'block' : 'none';
        }

        this._updateDependencies();
    }

    /**
     * Set all values
     * @param {Object} values - Object mapping toggle IDs to values
     */
    setValues(values) {
        for (const [toggleId, value] of Object.entries(values)) {
            this.setToggleValue(toggleId, value);
        }
    }

    /**
     * Expand the group
     */
    expand() {
        if (this.collapsed) {
            this._toggleCollapse();
        }
    }

    /**
     * Collapse the group
     */
    collapse() {
        if (!this.collapsed) {
            this._toggleCollapse();
        }
    }
}

// Export for use in HTML
if (typeof window !== 'undefined') {
    window.FeatureToggleGroup = FeatureToggleGroup;
}
