/**
 * VastAI Connection Toolbar
 * 
 * A unified toolbar interface for managing VastAI instance connections across all tabs.
 * Maintains state server-side for persistence across page refreshes and tab switches.
 */

// Import VastAI modules (these should already be loaded by vastai-modular.js)
// We'll access them via window.VastAI* after the page loads

class VastAIConnectionToolbar {
    constructor() {
        this.sessionId = null;
        this.state = null;
        this.instancesData = [];
        this.dropdownOpen = false;
        this.connectionTester = null;
    }

    /**
     * Resolve the host port mapped to SSH (22/tcp) with sensible fallbacks.
     */
    _resolveSshPort(instance) {
        // 1) Preferred: ports['22/tcp'][0].HostPort (Vast AI mapping)
        if (instance?.ports && instance.ports['22/tcp'] && instance.ports['22/tcp'].length > 0) {
            const mapped = parseInt(instance.ports['22/tcp'][0].HostPort, 10);
            if (!Number.isNaN(mapped)) return mapped;
        }
        // 2) Fallback: direct_port_start (start of direct port range)
        if (instance?.direct_port_start) {
            const direct = parseInt(instance.direct_port_start, 10);
            if (!Number.isNaN(direct)) return direct;
        }
        // 3) Legacy: ssh_port / port_forwarded
        if (instance?.ssh_port || instance?.port_forwarded) {
            const legacy = parseInt(instance.port_forwarded || instance.ssh_port, 10);
            if (!Number.isNaN(legacy)) return legacy;
        }
        // Default
        return 22;
    }

    _escapeAttr(str = '') {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/'/g, '&#39;');
    }

    _buildSSHConnectionString(instance) {
        const publicIp = instance.public_ipaddr || instance.public_ip || instance.ip_address;
        const sshPort = this._resolveSshPort(instance);
        if (!publicIp || !sshPort) return null;
        return `ssh -p ${sshPort} root@${publicIp} -L 8080:localhost:8080`;
    }
    
    /**
     * Initialize the toolbar
     */
    async init() {
        console.log('🔧 Initializing VastAI Connection Toolbar...');
        
        // Load or create session
        await this.loadState();
        
        // Render toolbar
        this.renderToolbar();
        
        // Load instances on initialization
        await this.loadInstances();
        
        // Setup event listeners
        this.setupEventListeners();
        
        console.log('✅ VastAI Connection Toolbar initialized');
    }
    
    /**
     * Load toolbar state from server
     */
    async loadState() {
        try {
            // Try to get session ID from localStorage
            const storedSessionId = localStorage.getItem('vastai_toolbar_session_id');
            
            const params = storedSessionId ? `?session_id=${storedSessionId}` : '';
            const response = await fetch(`/api/toolbar/state${params}`);
            const data = await response.json();
            
            if (data.success) {
                this.state = data.state;
                this.sessionId = this.state.session_id;
                
                // Store session ID in localStorage
                localStorage.setItem('vastai_toolbar_session_id', this.sessionId);
                
                console.log('📥 Loaded toolbar state:', this.state);
                return this.state;
            } else {
                console.error('❌ Failed to load toolbar state:', data.message);
                return null;
            }
        } catch (error) {
            console.error('❌ Error loading toolbar state:', error);
            return null;
        }
    }
    
    /**
     * Save complete toolbar state to server
     */
    async saveState(state) {
        try {
            const response = await fetch('/api/toolbar/state', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    ...state
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.state = data.state;
                console.log('💾 Saved toolbar state');
                return true;
            } else {
                console.error('❌ Failed to save toolbar state:', data.message);
                return false;
            }
        } catch (error) {
            console.error('❌ Error saving toolbar state:', error);
            return false;
        }
    }
    
    /**
     * Update specific fields in toolbar state
     */
    async updateState(updates) {
        const newState = { ...this.state, ...updates };
        return await this.saveState(newState);
    }
    
    /**
     * Load VastAI instances from API
     */
    async loadInstances() {
        try {
            console.log('🔄 Loading VastAI instances...');
            
            const response = await fetch('/vastai/instances');
            const data = await response.json();
            
            if (data.success) {
                this.instancesData = data.instances || [];
                
                // Update last refresh timestamp
                await this.updateState({
                    last_refresh: Date.now()
                });
                
                // Re-render dropdown if open
                if (this.dropdownOpen) {
                    this.renderDropdown();
                }
                
                // Update toolbar display
                this.updateToolbarDisplay();
                
                console.log(`✅ Loaded ${this.instancesData.length} instances`);
                return this.instancesData;
            } else {
                console.error('❌ Failed to load instances:', data.message);
                return [];
            }
        } catch (error) {
            console.error('❌ Error loading instances:', error);
            return [];
        }
    }
    
    /**
     * Render the toolbar HTML
     */
    renderToolbar() {
        // Find insertion point (before tab navigation)
        const container = document.querySelector('.container');
        const tabNav = document.querySelector('.tab-navigation');
        
        if (!container || !tabNav) {
            console.error('❌ Could not find container or tab navigation');
            return;
        }
        
        // Create toolbar HTML
        const toolbarHTML = `
            <div class="vastai-connection-toolbar" id="vastai-connection-toolbar">
                <button class="toolbar-btn toolbar-search-btn" id="toolbar-search-btn">
                    <span>🔍</span> Search Offers
                </button>
                
                <div class="toolbar-dropdown-container">
                    <button class="toolbar-btn toolbar-instance-btn" id="toolbar-instance-btn">
                        <span class="toolbar-instance-text" id="toolbar-instance-text">No instance.</span>
                        <span class="toolbar-status-icon" id="toolbar-status-icon"></span>
                        <span class="toolbar-connection-icon" id="toolbar-connection-icon"></span>
                    </button>
                    
                    <div class="toolbar-dropdown" id="toolbar-dropdown" style="display: none;">
                        <div class="toolbar-dropdown-content" id="toolbar-dropdown-content">
                            <!-- Instances will be rendered here -->
                        </div>
                    </div>
                </div>
                
                <button class="toolbar-btn toolbar-refresh-btn" id="toolbar-refresh-btn" title="Refresh instances">
                    <span>🔄</span>
                </button>
            </div>
        `;
        
        // Insert toolbar before tab navigation
        tabNav.insertAdjacentHTML('beforebegin', toolbarHTML);
        
        console.log('✅ Toolbar HTML rendered');
    }
    
    /**
     * Update toolbar display based on current state
     */
    updateToolbarDisplay() {
        const instanceText = document.getElementById('toolbar-instance-text');
        const statusIcon = document.getElementById('toolbar-status-icon');
        const connectionIcon = document.getElementById('toolbar-connection-icon');
        
        if (!instanceText || !statusIcon || !connectionIcon) return;
        
        // Update instance text
        if (this.state.ssh_host && this.state.ssh_port) {
            instanceText.textContent = `${this.state.ssh_host}:${this.state.ssh_port}`;
            instanceText.classList.add('has-instance');
        } else {
            instanceText.textContent = 'No instance.';
            instanceText.classList.remove('has-instance');
        }
        
        // Update status icon
        if (this.state.instance_status) {
            statusIcon.className = `toolbar-status-icon status-${this.state.instance_status}`;
            statusIcon.style.display = 'inline-block';
        } else {
            statusIcon.style.display = 'none';
        }
        
        // Update connection icon
        if (this.state.connection_tested) {
            if (this.state.connection_status === 'connected') {
                connectionIcon.className = 'toolbar-connection-icon connection-success';
                connectionIcon.style.display = 'inline-block';
            } else if (this.state.connection_status === 'failed') {
                connectionIcon.className = 'toolbar-connection-icon connection-failed';
                connectionIcon.style.display = 'inline-block';
            } else {
                connectionIcon.style.display = 'none';
            }
        } else {
            connectionIcon.style.display = 'none';
        }
    }
    
    /**
     * Render instances dropdown
     */
    renderDropdown() {
        const dropdownContent = document.getElementById('toolbar-dropdown-content');
        if (!dropdownContent) return;
        
        if (this.instancesData.length === 0) {
            dropdownContent.innerHTML = `
                <div class="toolbar-no-instances">
                    <p>No active instances found.</p>
                    <p>Click "Search Offers" to find and rent a GPU instance.</p>
                </div>
            `;
            return;
        }
        
        // Render instance tiles
        const tilesHTML = this.instancesData.map(instance => this.renderInstanceTile(instance)).join('');
        dropdownContent.innerHTML = `<div class="toolbar-instances-grid">${tilesHTML}</div>`;
        
        // Setup event listeners for action buttons
        this.setupInstanceActionListeners();
    }
    
    /**
     * Render a single instance tile
     */
    renderInstanceTile(instance) {
        const instanceId = instance.id || instance.instance_id || instance.instanceId;
        const status = instance.actual_status || instance.status || 'unknown';
        const gpuName = instance.gpu_name || instance.gpu || 'Unknown GPU';
        const gpuCount = instance.num_gpus || 1;
        const publicIp = instance.public_ipaddr || instance.public_ip || instance.ip_address || 'N/A';
        const sshPort = this._resolveSshPort(instance);
        const costPerHr = instance.dph_total || instance.cost_per_hour || 0;
        const sshConnection = this._buildSSHConnectionString(instance);
        
        const isSelected = this.state.selected_instance_id === instanceId;
        const isRunning = status === 'running';
        const obTokenHtml = (sshConnection && isRunning)
            ? `<a href="#" class="toolbar-fetch-token" data-action="fetch-token" data-instance-id="${instanceId}" data-ssh="${this._escapeAttr(sshConnection)}">fetch</a>`
            : 'N/A';
        
        return `
            <div class="toolbar-instance-tile ${isSelected ? 'selected' : ''}" data-instance-id="${instanceId}">
                <div class="toolbar-instance-info">
                    <div class="toolbar-instance-header">
                        <span class="toolbar-instance-id">#${instanceId}</span>
                        <span class="instance-status status-${status}">${status}</span>
                    </div>
                    <div class="toolbar-instance-gpu">
                        <strong>${gpuCount}x ${gpuName}</strong>
                    </div>
                    <div class="toolbar-instance-details">
                        <div>📡 ${publicIp}:${sshPort}</div>
                        <div>💰 $${costPerHr.toFixed(3)}/hr</div>
                        <div>🔑 OB Token: <span class="ob-token-value">${obTokenHtml}</span></div>
                    </div>
                </div>
                <div class="toolbar-instance-actions">
                    <button class="toolbar-action-btn toolbar-connect-btn" 
                            data-instance-id="${instanceId}"
                            ${!isRunning ? 'disabled' : ''}>
                        🔗 Connect
                    </button>
                    <button class="toolbar-action-btn toolbar-details-btn" 
                            data-instance-id="${instanceId}">
                        {...} Details
                    </button>
                    <button class="toolbar-action-btn toolbar-power-btn" 
                            data-instance-id="${instanceId}"
                            data-action="${isRunning ? 'stop' : 'start'}">
                        ${isRunning ? '⏹️ Stop' : '▶️ Start'}
                    </button>
                    <button class="toolbar-action-btn toolbar-destroy-btn" 
                            data-instance-id="${instanceId}">
                        🗑️ Destroy
                    </button>
                </div>
            </div>
        `;
    }
    
    /**
     * Setup event listeners for the toolbar
     */
    setupEventListeners() {
        // Search offers button
        const searchBtn = document.getElementById('toolbar-search-btn');
        if (searchBtn) {
            searchBtn.addEventListener('click', () => this.openSearchOffers());
        }
        
        // Instance dropdown button
        const instanceBtn = document.getElementById('toolbar-instance-btn');
        if (instanceBtn) {
            instanceBtn.addEventListener('click', (e) => this.toggleDropdown(e));
        }
        
        // Refresh button
        const refreshBtn = document.getElementById('toolbar-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadInstances());
        }
        
        // Click outside to close dropdown
        document.addEventListener('click', (e) => this.handleClickOutside(e));
    }
    
    /**
     * Setup event listeners for instance action buttons
     */
    setupInstanceActionListeners() {
        // OB token fetch links
        document.querySelectorAll('.toolbar-fetch-token').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const instanceId = parseInt(link.dataset.instanceId, 10);
                const sshConnection = link.dataset.ssh;
                this.fetchOpenButtonToken(instanceId, sshConnection);
            });
        });

        // Connect buttons
        document.querySelectorAll('.toolbar-connect-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const instanceId = parseInt(btn.dataset.instanceId);
                this.connectToInstance(instanceId);
            });
        });
        
        // Details buttons
        document.querySelectorAll('.toolbar-details-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const instanceId = parseInt(btn.dataset.instanceId);
                this.showInstanceDetails(instanceId);
            });
        });
        
        // Power buttons (Start/Stop)
        document.querySelectorAll('.toolbar-power-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const instanceId = parseInt(btn.dataset.instanceId);
                const action = btn.dataset.action;
                this.powerAction(instanceId, action);
            });
        });
        
        // Destroy buttons
        document.querySelectorAll('.toolbar-destroy-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const instanceId = parseInt(btn.dataset.instanceId);
                this.destroyInstance(instanceId);
            });
        });
    }
    
    /**
     * Toggle dropdown visibility
     */
    toggleDropdown(e) {
        e.stopPropagation();
        
        const dropdown = document.getElementById('toolbar-dropdown');
        if (!dropdown) return;
        
        this.dropdownOpen = !this.dropdownOpen;
        
        if (this.dropdownOpen) {
            dropdown.style.display = 'block';
            this.renderDropdown();
        } else {
            dropdown.style.display = 'none';
        }
    }
    
    /**
     * Handle clicks outside dropdown to close it
     */
    handleClickOutside(e) {
        const toolbar = document.getElementById('vastai-connection-toolbar');
        if (toolbar && !toolbar.contains(e.target) && this.dropdownOpen) {
            this.dropdownOpen = false;
            const dropdown = document.getElementById('toolbar-dropdown');
            if (dropdown) {
                dropdown.style.display = 'none';
            }
        }
    }
    
    /**
     * Connect to an instance
     */
    async connectToInstance(instanceId) {
        console.log(`🔗 Connecting to instance ${instanceId}...`);
        
        // Find instance data
        const instance = this.instancesData.find(i => 
            (i.id || i.instance_id || i.instanceId) === parseInt(instanceId, 10)
        );
        
        if (!instance) {
            console.error('❌ Instance not found');
            return;
        }
        
        // Build SSH connection string using the resolved host port mapped to 22/tcp
        const publicIp = instance.public_ipaddr || instance.public_ip || instance.ip_address;
        const sshPort = this._resolveSshPort(instance);
        const sshConnectionString = `ssh -p ${sshPort} root@${publicIp} -L 8080:localhost:8080`;
        
        // Update state
        await this.updateState({
            selected_instance_id: parseInt(instanceId, 10),
            ssh_connection_string: sshConnectionString,
            ssh_host: publicIp,
            ssh_port: sshPort,
            instance_status: instance.actual_status || instance.status
        });
        
        // Test SSH connection
        await this.testSSHConnection(sshConnectionString);
        
        // Update display
        this.updateToolbarDisplay();
        
        // Close dropdown
        this.dropdownOpen = false;
        const dropdown = document.getElementById('toolbar-dropdown');
        if (dropdown) {
            dropdown.style.display = 'none';
        }
    }
    
    /**
     * Test SSH connection
     */
    async testSSHConnection(sshConnectionString) {
        console.log('🔧 Testing SSH connection...');
        
        // Update state to show testing
        await this.updateState({
            connection_status: 'testing',
            connection_tested: false
        });
        
        this.updateToolbarDisplay();
        
        try {
            const response = await fetch('/test/ssh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ssh_connection: sshConnectionString
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Connection successful
                await this.updateState({
                    connection_status: 'connected',
                    connection_tested: true
                });
                
                console.log('✅ SSH connection successful');
            } else if (data.host_verification_needed || data.require_verification) {
                // Host key verification required (API returns host_verification_needed)
                console.log('⚠️ Host key verification required');
                
                await this.updateState({
                    connection_status: 'failed',
                    connection_tested: true
                });
                
                const modalPayload = {
                    host: data.host,
                    port: data.port,
                    error: data.error,
                    host_verification_needed: true
                };
                
                // Show host key verification modal (new or legacy)
                if (typeof window.VastAIUI !== 'undefined' && typeof window.VastAIUI.showSSHHostVerificationModal === 'function') {
                    window.VastAIUI.showSSHHostVerificationModal(modalPayload);
                } else if (typeof showHostKeyVerificationModal === 'function') {
                    showHostKeyVerificationModal(modalPayload);
                } else {
                    alert('Host key verification required. Please verify the host key.');
                }
            } else {
                // Connection failed
                await this.updateState({
                    connection_status: 'failed',
                    connection_tested: true
                });
                
                console.error('❌ SSH connection failed:', data.message);
            }
            
            this.updateToolbarDisplay();
            
        } catch (error) {
            console.error('❌ Error testing SSH connection:', error);
            
            await this.updateState({
                connection_status: 'failed',
                connection_tested: true
            });
            
            this.updateToolbarDisplay();
        }
    }

    async fetchOpenButtonToken(instanceId, sshConnection) {
        const tokenSpan = document.querySelector(`.toolbar-instance-tile[data-instance-id="${instanceId}"] .ob-token-value`);
        if (!tokenSpan) return;

        if (!sshConnection) {
            tokenSpan.innerHTML = '<span style="color: #e74c3c;">missing ssh</span>';
            return;
        }

        tokenSpan.innerHTML = '<span style="color: #888;">fetching...</span>';

        try {
            const response = await fetch(`/vastai/instances/${instanceId}/open-button-token`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ssh_connection: sshConnection })
            });

            const data = await response.json();

            if (data.require_verification || data.host_verification_needed) {
                const verified = await this._verifyHostForToken(data, sshConnection);
                if (verified) {
                    return this.fetchOpenButtonToken(instanceId, sshConnection);
                }

                tokenSpan.innerHTML = `<a href="#" class="toolbar-fetch-token" data-action="fetch-token" data-instance-id="${instanceId}" data-ssh="${this._escapeAttr(sshConnection)}">fetch</a>`;
                this.setupInstanceActionListeners();
                return;
            }

            if (data.success && data.token) {
                const fullToken = data.token;
                const truncated = `${fullToken.substring(0, 4)}...`;

                tokenSpan.innerHTML = `
                    <span class="token-display">${truncated}</span>
                    <button class="copy-token-btn" data-action="copy-token" data-instance-id="${instanceId}" data-token="${this._escapeAttr(fullToken)}">📋 Copy</button>
                `;

                const copyBtn = tokenSpan.querySelector('.copy-token-btn');
                if (copyBtn) {
                    copyBtn.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        this.copyObTokenToClipboard(fullToken, instanceId);
                    });
                }
                return;
            }

            tokenSpan.innerHTML = '<span style="color: #e74c3c;">failed</span>';
        } catch (error) {
            console.error('Error fetching OPEN_BUTTON_TOKEN:', error);
            tokenSpan.innerHTML = `<a href="#" class="toolbar-fetch-token" data-action="fetch-token" data-instance-id="${instanceId}" data-ssh="${this._escapeAttr(sshConnection)}">fetch</a>`;
            this.setupInstanceActionListeners();
        }
    }

    async _verifyHostForToken(data, sshConnection) {
        const modalData = {
            host: data.host,
            port: data.port,
            fingerprints: data.fingerprint ? [data.fingerprint] : [],
            ssh_connection: sshConnection,
            host_verification_needed: true
        };

        const accepted = await this._showHostVerificationModal(modalData);
        if (!accepted) return false;

        try {
            const verifyResp = await fetch('/ssh/verify-host', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ssh_connection: sshConnection, accept: true })
            });
            const verifyData = await verifyResp.json();
            return !!verifyData.success;
        } catch (err) {
            console.error('Host verification error:', err);
            return false;
        }
    }

    async _showHostVerificationModal(modalData) {
        try {
            if (window.VastAIUI && typeof window.VastAIUI.showSSHHostVerificationModal === 'function') {
                return await window.VastAIUI.showSSHHostVerificationModal(modalData);
            }
            if (typeof showHostKeyVerificationModal === 'function') {
                const result = showHostKeyVerificationModal(modalData);
                if (result && typeof result.then === 'function') {
                    return await result;
                }
                return result !== false;
            }
        } catch (error) {
            console.error('Host verification modal error:', error);
        }

        alert('Host key verification required. Please verify the host key.');
        return false;
    }

    async copyObTokenToClipboard(token, instanceId) {
        const copyBtn = document.querySelector(`.toolbar-instance-tile[data-instance-id="${instanceId}"] .copy-token-btn`);
        const resetLabel = () => {
            if (copyBtn) {
                setTimeout(() => {
                    copyBtn.textContent = '📋 Copy';
                }, 1500);
            }
        };

        try {
            await navigator.clipboard.writeText(token);
            if (copyBtn) {
                copyBtn.textContent = 'Copied';
                resetLabel();
            }
        } catch (error) {
            console.error('Clipboard API failed, using fallback:', error);
            const textarea = document.createElement('textarea');
            textarea.value = token;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            try {
                document.execCommand('copy');
                if (copyBtn) {
                    copyBtn.textContent = 'Copied';
                    resetLabel();
                }
            } catch (fallbackError) {
                console.error('Fallback copy failed:', fallbackError);
            }
            document.body.removeChild(textarea);
        }
    }
    
    /**
     * Show instance details modal
     */
    async showInstanceDetails(instanceId) {
        console.log(`📋 Showing details for instance ${instanceId}...`);
        
        // Use existing showInstanceDetails function if available
        if (typeof window.showInstanceDetails === 'function') {
            window.showInstanceDetails(parseInt(instanceId, 10));
        } else {
            console.warn('⚠️ showInstanceDetails function not available');
        }
    }
    
    /**
     * Perform power action (start/stop)
     */
    async powerAction(instanceId, action) {
        console.log(`⚡ ${action} instance ${instanceId}...`);

        const endpoint = action === 'start'
            ? `/vastai/instances/${instanceId}/start`
            : `/vastai/instances/${instanceId}/stop`;

        // Optimistically mark status
        await this.updateState({ connection_status: 'testing' });
        this.updateToolbarDisplay();

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();

            if (!data.success) {
                alert(`Failed to ${action} instance: ${data.message || 'Unknown error'}`);
            } else {
                if (action === 'stop' && this.state.selected_instance_id === instanceId) {
                    // Clear selection if we stopped the selected instance
                    await this.updateState({
                        selected_instance_id: null,
                        ssh_connection_string: '',
                        ssh_host: null,
                        ssh_port: null,
                        connection_status: 'disconnected',
                        connection_tested: false,
                        instance_status: null
                    });
                }
            }
        } catch (error) {
            console.error(`❌ Error performing ${action} on instance ${instanceId}:`, error);
            alert(`Error performing ${action}: ${error.message}`);
        }

        // Refresh instance list to reflect new status
        await this.loadInstances();
    }
    
    /**
     * Destroy an instance
     */
    async destroyInstance(instanceId) {
        // Use a better confirmation approach if possible
        const confirmed = window.confirm(`Are you sure you want to destroy instance #${instanceId}? This cannot be undone.`);
        if (!confirmed) {
            return;
        }
        
        console.log(`🗑️ Destroying instance ${instanceId}...`);
        
        try {
            const response = await fetch(`/vastai/instances/${parseInt(instanceId, 10)}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                console.log('✅ Instance destroyed');
                
                // If this was the selected instance, clear selection
                if (this.state.selected_instance_id === parseInt(instanceId, 10)) {
                    await this.updateState({
                        selected_instance_id: null,
                        ssh_connection_string: '',
                        ssh_host: null,
                        ssh_port: null,
                        connection_status: 'disconnected',
                        connection_tested: false,
                        instance_status: null
                    });
                    
                    this.updateToolbarDisplay();
                }
                
                // Reload instances
                await this.loadInstances();
            } else {
                console.error('❌ Failed to destroy instance:', data.message);
                alert(`Failed to destroy instance: ${data.message}`);
            }
        } catch (error) {
            console.error('❌ Error destroying instance:', error);
            alert('Error destroying instance. Check console for details.');
        }
    }
    
    /**
     * Open search offers modal
     */
    openSearchOffers() {
        if (typeof window.openSearchOffersModal === 'function') {
            window.openSearchOffersModal();
        } else {
            console.warn('⚠️ openSearchOffersModal function not available');
        }
    }
    
    /**
     * Get current SSH connection string
     */
    getSSHConnectionString() {
        return this.state?.ssh_connection_string || '';
    }
    
    /**
     * Check if connected to an instance
     */
    isConnected() {
        return this.state?.connection_status === 'connected';
    }
    
    /**
     * Get selected instance data
     */
    getSelectedInstance() {
        if (!this.state?.selected_instance_id) return null;
        
        return this.instancesData.find(i => 
            (i.id || i.instance_id || i.instanceId) === this.state.selected_instance_id
        );
    }
}

// Create and export singleton instance
const toolbarInstance = new VastAIConnectionToolbar();

// Expose globally
window.VastAIConnectionToolbar = toolbarInstance;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => toolbarInstance.init());
} else {
    // DOM already loaded, initialize now
    toolbarInstance.init();
}
