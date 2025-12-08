/**
 * Workflow Value Mapper
 * Maps UI form values to ComfyUI workflow JSON nodes
 */

class WorkflowValueMapper {
    constructor() {
        this.debug = false;
    }

    /**
     * Enable or disable debug logging
     * @param {boolean} enabled 
     */
    setDebug(enabled) {
        this.debug = enabled;
    }

    /**
     * Log debug message
     * @private
     */
    _log(...args) {
        if (this.debug) {
            console.log('[WorkflowMapper]', ...args);
        }
    }

    /**
     * Map UI form values to ComfyUI workflow JSON
     * @param {Object} formValues - Form values from UI
     * @param {Object} workflowTemplate - Original workflow JSON template
     * @param {Object} config - Workflow configuration (from .webui.yml)
     * @returns {Object} Filled workflow JSON
     */
    mapFormToWorkflow(formValues, workflowTemplate, config) {
        // Deep clone the workflow template
        const workflow = JSON.parse(JSON.stringify(workflowTemplate));

        // Get all input definitions from config
        const allInputs = [
            ...(config.inputs || []),
            ...(config.advanced || [])
        ];

        // Process each input
        for (const input of allInputs) {
            const value = formValues[input.id];
            
            // Skip if no value provided
            if (value === undefined || value === null) {
                this._log(`Skipping ${input.id}: no value provided`);
                continue;
            }

            // Check dependencies
            if (input.depends_on) {
                const depField = input.depends_on.field;
                const depValue = input.depends_on.value;
                const actualValue = formValues[depField];
                
                if (actualValue !== depValue) {
                    this._log(`Skipping ${input.id}: dependency not met (${depField} = ${actualValue}, expected ${depValue})`);
                    continue;
                }
            }

            // Map based on input type
            try {
                this._mapInput(workflow, input, value);
            } catch (error) {
                console.error(`[WorkflowMapper] Error mapping ${input.id}:`, error);
            }
        }

        return workflow;
    }

    /**
     * Map a single input to the workflow
     * @private
     */
    _mapInput(workflow, input, value) {
        switch (input.type) {
            case 'high_low_pair_model':
                this._mapHighLowPairModel(workflow, input, value);
                break;

            case 'high_low_pair_lora_list':
                this._mapLoraList(workflow, input, value);
                break;

            case 'single_model':
                this._mapSingleModel(workflow, input, value);
                break;

            case 'checkbox':
                this._mapCheckbox(workflow, input, value);
                break;

            case 'slider':
                this._mapSlider(workflow, input, value);
                break;

            case 'seed':
                this._mapSeed(workflow, input, value);
                break;

            case 'textarea':
            case 'text':
                this._mapText(workflow, input, value);
                break;

            case 'image':
                this._mapImage(workflow, input, value);
                break;

            case 'select':
                this._mapSelect(workflow, input, value);
                break;

            default:
                this._log(`Unknown input type: ${input.type}`);
                // Try generic mapping
                this._mapGeneric(workflow, input, value);
        }
    }

    /**
     * Map a high-low pair model selection
     * @private
     */
    _mapHighLowPairModel(workflow, input, value) {
        const nodeIds = input.node_ids;
        if (!nodeIds || nodeIds.length < 2) {
            this._log(`Invalid node_ids for high_low_pair_model: ${input.id}`);
            return;
        }

        const [highNodeId, lowNodeId] = nodeIds;

        // Set high noise model path
        if (workflow[highNodeId] && workflow[highNodeId].inputs) {
            workflow[highNodeId].inputs.unet_name = value.highNoisePath;
            this._log(`Set high noise model: ${value.highNoisePath} in node ${highNodeId}`);
        }

        // Set low noise model path
        if (workflow[lowNodeId] && workflow[lowNodeId].inputs) {
            workflow[lowNodeId].inputs.unet_name = value.lowNoisePath;
            this._log(`Set low noise model: ${value.lowNoisePath} in node ${lowNodeId}`);
        }
    }

    /**
     * Map a LoRA list (high-low pairs)
     * @private
     */
    _mapLoraList(workflow, input, loras) {
        if (!Array.isArray(loras) || loras.length === 0) {
            this._log(`No LoRAs to map for ${input.id}`);
            return;
        }

        const nodeIds = input.node_ids;
        if (!nodeIds || nodeIds.length < 2) {
            this._log(`Invalid node_ids for high_low_pair_lora_list: ${input.id}`);
            return;
        }

        const [highNodeId, lowNodeId] = nodeIds;

        // Build Power Lora Loader config for high noise node
        const loraConfigHigh = {};
        loras.forEach((lora, index) => {
            const key = `Lora ${index + 1}`;
            loraConfigHigh[key] = {
                on: true,
                lora: lora.highNoisePath,
                strength: lora.strength || 1.0,
                strength_clip: lora.strength || 1.0
            };
        });

        if (workflow[highNodeId] && workflow[highNodeId].inputs) {
            workflow[highNodeId].inputs["➕ Add Lora"] = loraConfigHigh;
            this._log(`Set ${loras.length} LoRAs for high noise node ${highNodeId}`);
        }

        // Build config for low noise node
        const loraConfigLow = {};
        loras.forEach((lora, index) => {
            const key = `Lora ${index + 1}`;
            loraConfigLow[key] = {
                on: true,
                lora: lora.lowNoisePath,
                strength: lora.strength || 1.0,
                strength_clip: lora.strength || 1.0
            };
        });

        if (workflow[lowNodeId] && workflow[lowNodeId].inputs) {
            workflow[lowNodeId].inputs["➕ Add Lora"] = loraConfigLow;
            this._log(`Set ${loras.length} LoRAs for low noise node ${lowNodeId}`);
        }
    }

    /**
     * Map a single model selection
     * @private
     */
    _mapSingleModel(workflow, input, value) {
        const nodeId = String(input.node_id);
        const field = input.field;

        if (!workflow[nodeId]) {
            this._log(`Node ${nodeId} not found for single_model: ${input.id}`);
            return;
        }

        if (!workflow[nodeId].inputs) {
            workflow[nodeId].inputs = {};
        }

        // Value can be an object with path property or just a string path
        const path = typeof value === 'object' ? value.path : value;
        workflow[nodeId].inputs[field] = path;
        this._log(`Set single model: ${path} in node ${nodeId}.${field}`);
    }

    /**
     * Map a checkbox (feature toggle)
     * @private
     */
    _mapCheckbox(workflow, input, value) {
        // Handle both single node_id and multiple node_ids
        if (input.node_ids) {
            // Toggle multiple nodes (feature toggle pattern)
            for (const nodeId of input.node_ids) {
                if (workflow[nodeId]) {
                    // Enable/disable node (implementation depends on workflow structure)
                    // For now, we'll set a bypass flag if it exists
                    if (workflow[nodeId].inputs && 'bypass' in workflow[nodeId].inputs) {
                        workflow[nodeId].inputs.bypass = !value;
                    }
                }
            }
            this._log(`Toggled ${input.node_ids.length} nodes for ${input.id}: ${value}`);
        } else if (input.node_id) {
            // Single node checkbox - handle multiple fields or single field
            const nodeId = String(input.node_id);
            const fields = input.fields || [input.field || 'value'];

            if (workflow[nodeId] && workflow[nodeId].inputs) {
                for (const field of fields) {
                    if (field) {
                        workflow[nodeId].inputs[field] = value;
                        this._log(`Set checkbox: ${value} in node ${nodeId}.${field}`);
                    }
                }
            }
        }
    }

    /**
     * Map a slider value
     * @private
     */
    _mapSlider(workflow, input, value) {
        const nodeId = String(input.node_id);

        if (!workflow[nodeId]) {
            this._log(`Node ${nodeId} not found for slider: ${input.id}`);
            return;
        }

        if (!workflow[nodeId].inputs) {
            workflow[nodeId].inputs = {};
        }

        // Handle multiple fields (e.g., Xi and Xf for mxSlider)
        const fields = input.fields || [input.field];
        
        for (const field of fields) {
            if (field) {
                workflow[nodeId].inputs[field] = value;
            }
        }

        this._log(`Set slider: ${value} in node ${nodeId} fields: ${fields.join(', ')}`);
    }

    /**
     * Map a seed value
     * @private
     */
    _mapSeed(workflow, input, value) {
        const field = input.field || 'noise_seed';

        // Handle random seed
        // Use 2^32-1 as max for compatibility with most systems
        const MAX_SEED = 0xFFFFFFFF;
        let seedValue = value;
        if (value === -1 || value === 'random') {
            seedValue = Math.floor(Math.random() * MAX_SEED);
        }

        // Seed can have either node_id (single) or node_ids (multiple)
        const nodeIds = input.node_ids || (input.node_id ? [input.node_id] : []);
        
        if (nodeIds.length === 0) {
            this._log(`No node_id or node_ids found for seed: ${input.id}`);
            return;
        }

        // Apply seed to all specified nodes
        for (const nodeId of nodeIds) {
            const nodeIdStr = String(nodeId);
            
            if (!workflow[nodeIdStr]) {
                this._log(`Node ${nodeIdStr} not found for seed: ${input.id}`);
                continue;
            }

            if (!workflow[nodeIdStr].inputs) {
                workflow[nodeIdStr].inputs = {};
            }

            workflow[nodeIdStr].inputs[field] = seedValue;
            this._log(`Set seed: ${seedValue} in node ${nodeIdStr}.${field}`);
        }
    }

    /**
     * Map a text/textarea value
     * @private
     */
    _mapText(workflow, input, value) {
        const nodeId = String(input.node_id);

        if (!workflow[nodeId]) {
            this._log(`Node ${nodeId} not found for text: ${input.id}`);
            return;
        }

        if (!workflow[nodeId].inputs) {
            workflow[nodeId].inputs = {};
        }

        // Handle multiple fields or single field
        const fields = input.fields || [input.field || 'value'];
        
        for (const field of fields) {
            if (field) {
                workflow[nodeId].inputs[field] = value;
                this._log(`Set text in node ${nodeId}.${field}: ${value.substring(0, 50)}...`);
            }
        }
    }

    /**
     * Map an image value
     * @private
     */
    _mapImage(workflow, input, value) {
        const nodeId = String(input.node_id);

        if (!workflow[nodeId]) {
            this._log(`Node ${nodeId} not found for image: ${input.id}`);
            return;
        }

        if (!workflow[nodeId].inputs) {
            workflow[nodeId].inputs = {};
        }

        // Handle multiple fields or single field
        const fields = input.fields || [input.field || 'image'];
        
        // Value is the uploaded filename or base64 data
        for (const field of fields) {
            if (field) {
                workflow[nodeId].inputs[field] = value;
                this._log(`Set image in node ${nodeId}.${field}`);
            }
        }
    }

    /**
     * Map a select/dropdown value
     * @private
     */
    _mapSelect(workflow, input, value) {
        const nodeId = String(input.node_id);

        if (!workflow[nodeId]) {
            this._log(`Node ${nodeId} not found for select: ${input.id}`);
            return;
        }

        if (!workflow[nodeId].inputs) {
            workflow[nodeId].inputs = {};
        }

        // Handle multiple fields or single field
        const fields = input.fields || [input.field || 'value'];
        
        for (const field of fields) {
            if (field) {
                workflow[nodeId].inputs[field] = value;
                this._log(`Set select in node ${nodeId}.${field}: ${value}`);
            }
        }
    }

    /**
     * Generic mapping for unknown types
     * @private
     */
    _mapGeneric(workflow, input, value) {
        if (!input.node_id) {
            this._log(`No node_id for generic mapping: ${input.id}`);
            return;
        }

        const nodeId = String(input.node_id);
        const field = input.field || 'value';

        if (!workflow[nodeId]) {
            this._log(`Node ${nodeId} not found for generic: ${input.id}`);
            return;
        }

        if (!workflow[nodeId].inputs) {
            workflow[nodeId].inputs = {};
        }

        workflow[nodeId].inputs[field] = value;
        this._log(`Generic mapping: ${value} in node ${nodeId}.${field}`);
    }

    /**
     * Validate that required inputs are present
     * @param {Object} formValues - Form values
     * @param {Object} config - Workflow configuration
     * @returns {Object} Validation result with errors array
     */
    validateInputs(formValues, config) {
        const errors = [];
        const allInputs = [
            ...(config.inputs || []),
            ...(config.advanced || [])
        ];

        for (const input of allInputs) {
            if (input.required) {
                const value = formValues[input.id];
                
                // Check for missing value
                if (value === undefined || value === null || value === '') {
                    // Check if dependency allows skipping
                    if (input.depends_on) {
                        const depField = input.depends_on.field;
                        const depValue = input.depends_on.value;
                        const actualValue = formValues[depField];
                        
                        if (actualValue !== depValue) {
                            continue; // Dependency not met, skip validation
                        }
                    }
                    
                    errors.push({
                        field: input.id,
                        label: input.label,
                        message: `${input.label} is required`
                    });
                }
            }
        }

        return {
            valid: errors.length === 0,
            errors
        };
    }
}

// Create and export singleton instance
const workflowValueMapper = new WorkflowValueMapper();

// Export for use in HTML
if (typeof window !== 'undefined') {
    window.workflowValueMapper = workflowValueMapper;
}
