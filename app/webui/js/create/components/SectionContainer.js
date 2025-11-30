/**
 * Section Container Component
 * Provides collapsible sections for organizing form inputs
 */

class SectionContainer {
    /**
     * Create a section container
     * @param {Object} config - Section configuration
     * @param {string} config.id - Section ID
     * @param {string} config.title - Section title
     * @param {boolean} config.collapsed - Whether section starts collapsed
     * @param {string} config.icon - Optional icon for section header
     */
    constructor(config) {
        this.id = config.id;
        this.title = config.title;
        this.collapsed = config.collapsed || false;
        this.icon = config.icon || '';
        this.element = null;
        this.contentElement = null;
        this.toggleButton = null;
    }

    /**
     * Render the section container
     * @returns {HTMLElement} The section container element
     */
    render() {
        // Create container
        this.element = document.createElement('div');
        this.element.className = 'create-form-section';
        this.element.id = `section-${this.id}`;

        // Create header
        const header = document.createElement('div');
        header.className = 'create-form-section-header';

        // Create title
        const title = document.createElement('h4');
        title.className = 'create-form-section-title';
        title.textContent = this.icon ? `${this.icon} ${this.title}` : this.title;

        // Create toggle button
        this.toggleButton = document.createElement('button');
        this.toggleButton.className = 'create-form-section-toggle';
        this.toggleButton.type = 'button';
        this.toggleButton.textContent = this.collapsed ? '▶' : '▼';
        this.toggleButton.setAttribute('aria-expanded', !this.collapsed);
        this.toggleButton.setAttribute('aria-controls', `section-content-${this.id}`);
        if (this.collapsed) {
            this.toggleButton.classList.add('collapsed');
        }

        this.toggleButton.addEventListener('click', () => this.toggle());

        header.appendChild(title);
        header.appendChild(this.toggleButton);

        // Create content container
        this.contentElement = document.createElement('div');
        this.contentElement.className = 'create-form-section-content';
        this.contentElement.id = `section-content-${this.id}`;
        if (this.collapsed) {
            this.contentElement.classList.add('collapsed');
        }

        this.element.appendChild(header);
        this.element.appendChild(this.contentElement);

        return this.element;
    }

    /**
     * Toggle section visibility
     */
    toggle() {
        this.collapsed = !this.collapsed;
        this.contentElement.classList.toggle('collapsed', this.collapsed);
        this.toggleButton.classList.toggle('collapsed', this.collapsed);
        this.toggleButton.textContent = this.collapsed ? '▶' : '▼';
        this.toggleButton.setAttribute('aria-expanded', !this.collapsed);
    }

    /**
     * Expand the section
     */
    expand() {
        if (this.collapsed) {
            this.toggle();
        }
    }

    /**
     * Collapse the section
     */
    collapse() {
        if (!this.collapsed) {
            this.toggle();
        }
    }

    /**
     * Add content to the section
     * @param {HTMLElement|string} content - Content to add
     */
    addContent(content) {
        if (typeof content === 'string') {
            this.contentElement.innerHTML += content;
        } else {
            this.contentElement.appendChild(content);
        }
    }

    /**
     * Clear all content from the section
     */
    clearContent() {
        this.contentElement.innerHTML = '';
    }

    /**
     * Get the content element for direct manipulation
     * @returns {HTMLElement}
     */
    getContentElement() {
        return this.contentElement;
    }
}

// Export for use in HTML
if (typeof window !== 'undefined') {
    window.SectionContainer = SectionContainer;
}
