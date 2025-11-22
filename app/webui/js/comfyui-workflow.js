// ==============================
// ComfyUI Workflow Execution Module
// ==============================
// Handles ComfyUI workflow execution with server-side state persistence

/**
 * ComfyUI Workflow Manager
 * Manages workflow execution, progress monitoring, and state restoration
 */
class ComfyUIWorkflowManager {
  constructor() {
    this.currentWorkflowId = null;
    this.pollInterval = null;
    this.pollIntervalMs = 2000; // 2 seconds
    this.isPolling = false;
  }

  /**
   * Execute a ComfyUI workflow
   * @param {string} sshConnection - SSH connection string
   * @param {string} workflowFile - Path to workflow JSON file
   * @param {string} workflowName - Human-readable workflow name
   * @param {Array<string>} inputImages - Array of input image paths
   * @param {string} outputDir - Local output directory
   * @returns {Promise<string>} - Workflow ID
   */
  async executeWorkflow(sshConnection, workflowFile, workflowName = null, inputImages = [], outputDir = '/tmp/comfyui_outputs') {
    try {
      const response = await fetch('/comfyui/workflow/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ssh_connection: sshConnection,
          workflow_file: workflowFile,
          workflow_name: workflowName,
          input_images: inputImages,
          output_dir: outputDir
        })
      });

      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.message);
      }

      this.currentWorkflowId = data.workflow_id;
      return data.workflow_id;
    } catch (error) {
      console.error('Failed to execute workflow:', error);
      throw error;
    }
  }

  /**
   * Get workflow progress
   * @param {string} workflowId - Workflow ID
   * @returns {Promise<Object>} - Progress data
   */
  async getProgress(workflowId) {
    try {
      const response = await fetch(`/comfyui/workflow/${workflowId}/progress`);
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.message);
      }

      return data.progress;
    } catch (error) {
      console.error('Failed to get progress:', error);
      throw error;
    }
  }

  /**
   * Cancel a running workflow
   * @param {string} workflowId - Workflow ID
   * @returns {Promise<boolean>} - Success status
   */
  async cancelWorkflow(workflowId) {
    try {
      const response = await fetch(`/comfyui/workflow/${workflowId}/cancel`, {
        method: 'POST'
      });

      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.message);
      }

      return true;
    } catch (error) {
      console.error('Failed to cancel workflow:', error);
      throw error;
    }
  }

  /**
   * Get workflow outputs
   * @param {string} workflowId - Workflow ID
   * @returns {Promise<Array>} - Array of output files
   */
  async getOutputs(workflowId) {
    try {
      const response = await fetch(`/comfyui/workflow/${workflowId}/outputs`);
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.message);
      }

      return data.outputs;
    } catch (error) {
      console.error('Failed to get outputs:', error);
      throw error;
    }
  }

  /**
   * Load persisted workflow state
   * @returns {Promise<Object|null>} - Workflow state or null
   */
  async loadState() {
    try {
      const response = await fetch('/comfyui/workflow/state');
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.message);
      }

      return data.state;
    } catch (error) {
      console.error('Failed to load state:', error);
      return null;
    }
  }

  /**
   * Check if workflow is active
   * @param {string} workflowId - Workflow ID
   * @returns {Promise<boolean>} - Active status
   */
  async isWorkflowActive(workflowId) {
    try {
      const response = await fetch(`/comfyui/workflow/${workflowId}/active`);
      const data = await response.json();
      
      if (!data.success) {
        return false;
      }

      return data.active;
    } catch (error) {
      console.error('Failed to check active status:', error);
      return false;
    }
  }

  /**
   * Start polling for workflow progress
   * @param {string} workflowId - Workflow ID
   * @param {Function} onProgress - Progress callback
   * @param {Function} onComplete - Completion callback
   * @param {Function} onError - Error callback
   */
  startProgressPolling(workflowId, onProgress, onComplete, onError) {
    // Stop any existing polling
    this.stopProgressPolling();

    this.currentWorkflowId = workflowId;
    this.isPolling = true;

    // Poll immediately
    this.pollProgress(onProgress, onComplete, onError);

    // Start interval
    this.pollInterval = setInterval(() => {
      this.pollProgress(onProgress, onComplete, onError);
    }, this.pollIntervalMs);
  }

  /**
   * Stop polling for progress
   */
  stopProgressPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
    this.isPolling = false;
  }

  /**
   * Poll for progress (internal)
   * @private
   */
  async pollProgress(onProgress, onComplete, onError) {
    if (!this.currentWorkflowId || !this.isPolling) {
      return;
    }

    try {
      const progress = await this.getProgress(this.currentWorkflowId);
      
      // Call progress callback
      if (onProgress) {
        onProgress(progress);
      }

      // Check if completed
      if (progress.status === 'completed') {
        this.stopProgressPolling();
        if (onComplete) {
          onComplete(progress);
        }
      } else if (progress.status === 'failed' || progress.status === 'cancelled') {
        this.stopProgressPolling();
        if (onError) {
          onError(progress);
        }
      }
    } catch (error) {
      console.error('Error polling progress:', error);
      this.stopProgressPolling();
      if (onError) {
        onError({ error: error.message });
      }
    }
  }

  /**
   * Update UI with workflow progress
   * @param {HTMLElement} stepElement - Workflow step element
   * @param {Object} progress - Progress data
   */
  updateProgressUI(stepElement, progress) {
    const progressIndicators = window.progressIndicators;
    if (!progressIndicators) {
      console.error('Progress indicators not available');
      return;
    }

    if (progress.status === 'queued') {
      // Show queue position
      const queueText = progress.queue_position !== null 
        ? `Workflow queued at position ${progress.queue_position}`
        : 'Workflow queued';
      
      progressIndicators.showSimpleProgress(
        stepElement,
        queueText,
        'Waiting for execution...'
      );
    } else if (progress.status === 'executing') {
      // Show node execution progress
      if (progress.nodes && progress.nodes.length > 0) {
        const checklistItems = progress.nodes.map(node => ({
          label: `${node.node_type || 'Node'} (${node.node_id})`,
          state: node.status === 'executed' ? 'completed' : 
                 node.status === 'executing' ? 'active' : 'pending',
          detail: node.message || ''
        }));

        progressIndicators.showChecklistProgress(
          stepElement,
          checklistItems,
          `${progress.completed_nodes}/${progress.total_nodes} nodes completed`
        );
      } else {
        // Fallback to simple progress
        progressIndicators.showSimpleProgress(
          stepElement,
          'Executing workflow',
          `${Math.round(progress.progress_percent)}% complete`
        );
      }
    } else if (progress.status === 'completed') {
      progressIndicators.showSuccess(
        stepElement,
        'Workflow completed successfully!',
        `Generated ${progress.outputs.length} output(s)`
      );
    } else if (progress.status === 'failed') {
      const errorMsg = progress.error_message || 'Workflow execution failed';
      const failedNode = progress.failed_node ? ` at node ${progress.failed_node}` : '';
      
      progressIndicators.showError(
        stepElement,
        'Workflow failed',
        errorMsg + failedNode
      );
    } else if (progress.status === 'cancelled') {
      progressIndicators.showWarning(
        stepElement,
        'Workflow cancelled',
        'Execution was cancelled by user'
      );
    }
  }

  /**
   * Restore workflow state on page load
   * @param {HTMLElement} stepElement - Workflow step element
   */
  async restoreWorkflowState(stepElement) {
    try {
      const state = await this.loadState();
      
      if (!state) {
        console.log('No workflow state to restore');
        return;
      }

      console.log(`Restoring workflow: ${state.workflow_name} (${state.progress_percent}%)`);

      // Show restoration message
      if (window.showSetupResult) {
        window.showSetupResult(
          `⏮️ Restored ComfyUI workflow: ${state.workflow_name}. Progress: ${Math.round(state.progress_percent)}%`,
          'info'
        );
      }

      // Update UI with current state
      this.updateProgressUI(stepElement, state);

      // Resume monitoring if not completed
      if (state.status !== 'completed' && state.status !== 'failed' && state.status !== 'cancelled') {
        this.startProgressPolling(
          state.workflow_id,
          (progress) => this.updateProgressUI(stepElement, progress),
          (progress) => {
            this.updateProgressUI(stepElement, progress);
            this.handleWorkflowComplete(stepElement, progress);
          },
          (progress) => {
            this.updateProgressUI(stepElement, progress);
            this.handleWorkflowError(stepElement, progress);
          }
        );
      }
    } catch (error) {
      console.error('Failed to restore workflow state:', error);
    }
  }

  /**
   * Handle workflow completion
   * @param {HTMLElement} stepElement - Workflow step element
   * @param {Object} progress - Progress data
   */
  async handleWorkflowComplete(stepElement, progress) {
    console.log('Workflow completed:', progress.workflow_id);

    // Get outputs
    try {
      const outputs = await this.getOutputs(progress.workflow_id);
      
      if (outputs.length > 0) {
        console.log(`Downloaded ${outputs.length} output files`);
        
        // Show outputs in UI
        if (window.showSetupResult) {
          const outputList = outputs
            .filter(o => o.downloaded)
            .map(o => o.filename)
            .join(', ');
          
          window.showSetupResult(
            `✅ Workflow completed! Outputs: ${outputList}`,
            'success'
          );
        }
      }
    } catch (error) {
      console.error('Failed to get outputs:', error);
    }

    // Mark step as complete
    this.markStepComplete(stepElement);
  }

  /**
   * Handle workflow error
   * @param {HTMLElement} stepElement - Workflow step element
   * @param {Object} progress - Progress data
   */
  handleWorkflowError(stepElement, progress) {
    console.error('Workflow error:', progress);

    if (window.showSetupResult) {
      const errorMsg = progress.error_message || progress.error || 'Workflow execution failed';
      window.showSetupResult(`❌ ${errorMsg}`, 'error');
    }

    // Mark step as error
    this.markStepError(stepElement);
  }

  /**
   * Mark step as complete
   * @param {HTMLElement} stepElement - Workflow step element
   */
  markStepComplete(stepElement) {
    const toggle = stepElement.querySelector('.step-toggle');
    if (toggle) {
      toggle.style.background = 'var(--text-success)';
      const icon = toggle.querySelector('.toggle-icon');
      if (icon) {
        icon.textContent = '✓';
      }
    }
  }

  /**
   * Mark step as error
   * @param {HTMLElement} stepElement - Workflow step element
   */
  markStepError(stepElement) {
    const toggle = stepElement.querySelector('.step-toggle');
    if (toggle) {
      toggle.style.background = 'var(--text-error)';
      const icon = toggle.querySelector('.toggle-icon');
      if (icon) {
        icon.textContent = '✗';
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

// Create global instance
window.comfyuiWorkflowManager = new ComfyUIWorkflowManager();

// Auto-restore workflow state on page load
document.addEventListener('DOMContentLoaded', () => {
  const stepElement = document.querySelector('[data-action="execute_comfyui_workflow"]');
  if (stepElement) {
    window.comfyuiWorkflowManager.restoreWorkflowState(stepElement);
  }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { ComfyUIWorkflowManager };
}
