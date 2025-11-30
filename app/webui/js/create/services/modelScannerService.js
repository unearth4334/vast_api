/**
 * Model Scanner Service
 * Handles communication with the backend API for model discovery
 */

class ModelScannerService {
    constructor() {
        this.cache = new Map();
        this.cacheTTL = 300000; // 5 minutes in milliseconds
        this.pendingRequests = new Map();
    }

    /**
     * Generate a cache key for a model scan request
     * @param {string} sshConnection - SSH connection string
     * @param {string} modelType - Type of models to scan
     * @param {string} searchPattern - Search pattern ('high_low_pair' or 'single')
     * @returns {string} Cache key
     */
    getCacheKey(sshConnection, modelType, searchPattern) {
        return `${sshConnection}:${modelType}:${searchPattern}`;
    }

    /**
     * Scan for high-low pair models (e.g., WAN 2.2 diffusion models)
     * @param {string} sshConnection - SSH connection string
     * @param {string} modelType - Model type to scan
     * @param {boolean} forceRefresh - Force refresh bypassing cache
     * @returns {Promise<Array>} List of model pair objects
     */
    async scanHighLowPairs(sshConnection, modelType, forceRefresh = false) {
        return this._scanModels(sshConnection, modelType, 'high_low_pair', forceRefresh);
    }

    /**
     * Scan for single model files
     * @param {string} sshConnection - SSH connection string
     * @param {string} modelType - Model type to scan
     * @param {boolean} forceRefresh - Force refresh bypassing cache
     * @returns {Promise<Array>} List of model objects
     */
    async scanSingleModels(sshConnection, modelType, forceRefresh = false) {
        return this._scanModels(sshConnection, modelType, 'single', forceRefresh);
    }

    /**
     * Internal method to scan models
     * @private
     */
    async _scanModels(sshConnection, modelType, searchPattern, forceRefresh) {
        const cacheKey = this.getCacheKey(sshConnection, modelType, searchPattern);

        // Check local cache first (unless force refresh)
        if (!forceRefresh && this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTTL) {
                console.log(`[ModelScanner] Returning cached ${modelType} models`);
                return cached.data;
            }
        }

        // Check if there's already a pending request for this key
        if (this.pendingRequests.has(cacheKey)) {
            console.log(`[ModelScanner] Waiting for pending request for ${modelType}`);
            return this.pendingRequests.get(cacheKey);
        }

        // Create the request promise
        const requestPromise = this._fetchModels(sshConnection, modelType, searchPattern, forceRefresh);
        this.pendingRequests.set(cacheKey, requestPromise);

        try {
            const result = await requestPromise;
            
            // Cache the result
            this.cache.set(cacheKey, {
                data: result,
                timestamp: Date.now()
            });

            return result;
        } finally {
            this.pendingRequests.delete(cacheKey);
        }
    }

    /**
     * Fetch models from the backend API
     * @private
     */
    async _fetchModels(sshConnection, modelType, searchPattern, forceRefresh) {
        try {
            const response = await fetch('/api/models/scan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ssh_connection: sshConnection,
                    model_type: modelType,
                    search_pattern: searchPattern,
                    force_refresh: forceRefresh
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || `Failed to scan models: ${response.status}`);
            }

            if (!data.success) {
                throw new Error(data.message || 'Unknown error scanning models');
            }

            console.log(`[ModelScanner] Found ${data.models.length} ${modelType} models (cached: ${data.cached})`);
            return data.models;

        } catch (error) {
            console.error(`[ModelScanner] Error scanning ${modelType} models:`, error);
            throw error;
        }
    }

    /**
     * Invalidate cache for specific models or all models
     * @param {string} sshConnection - Optional SSH connection to invalidate
     * @param {string} modelType - Optional model type to invalidate
     */
    invalidateCache(sshConnection = null, modelType = null) {
        if (!sshConnection && !modelType) {
            // Clear entire cache
            this.cache.clear();
            console.log('[ModelScanner] Entire cache invalidated');
            return;
        }

        // Selective invalidation
        const keysToRemove = [];
        for (const key of this.cache.keys()) {
            if (sshConnection && !key.includes(sshConnection)) continue;
            if (modelType && !key.includes(modelType)) continue;
            keysToRemove.push(key);
        }

        keysToRemove.forEach(key => this.cache.delete(key));
        console.log(`[ModelScanner] Invalidated ${keysToRemove.length} cache entries`);
    }

    /**
     * Get available model types from the backend
     * @returns {Promise<Object>} Model types configuration
     */
    async getModelTypes() {
        try {
            const response = await fetch('/api/models/types');
            const data = await response.json();

            if (!data.success) {
                throw new Error(data.message || 'Failed to get model types');
            }

            return {
                modelTypes: data.model_types,
                highLowPairTypes: data.high_low_pair_types,
                extensions: data.extensions
            };
        } catch (error) {
            console.error('[ModelScanner] Error getting model types:', error);
            throw error;
        }
    }
}

// Create and export singleton instance
const modelScannerService = new ModelScannerService();

// Export for use in HTML
if (typeof window !== 'undefined') {
    window.modelScannerService = modelScannerService;
}
