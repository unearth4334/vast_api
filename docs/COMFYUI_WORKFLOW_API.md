# ComfyUI Workflow Execution API Reference

## Overview

This API provides endpoints for executing ComfyUI workflows on remote instances with server-side state persistence and real-time progress tracking. Workflows continue running on the server even if the web UI is closed or refreshed.

**Base URL:** `http://localhost:5000`

**API Namespace:** `/comfyui/workflow`

---

## Authentication

Currently, no authentication is required. All endpoints are accessible via CORS-enabled HTTP requests.

---

## Endpoints

### 1. Execute Workflow

Start execution of a ComfyUI workflow on a remote instance.

**Endpoint:** `POST /comfyui/workflow/execute`

**Request Body:**

```json
{
  "ssh_connection": "ssh -p 40738 root@198.53.64.194",
  "workflow_file": "/path/to/workflow.json",
  "workflow_name": "Image Enhancement",
  "input_images": ["/path/to/image1.png", "/path/to/image2.png"],
  "output_dir": "/tmp/comfyui_outputs",
  "comfyui_port": 18188,
  "comfyui_input_dir": "/workspace/ComfyUI/input",
  "comfyui_output_dir": "/workspace/ComfyUI/output"
}
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `ssh_connection` | string | Yes | - | SSH connection string for remote instance |
| `workflow_file` | string | Yes | - | Local path to ComfyUI workflow JSON file |
| `workflow_name` | string | No | Filename | Human-readable name for the workflow |
| `input_images` | array | No | `[]` | List of local image file paths to upload |
| `output_dir` | string | No | `/tmp/comfyui_outputs` | Local directory for downloaded outputs |
| `comfyui_port` | integer | No | `18188` | Port for ComfyUI API on remote instance |
| `comfyui_input_dir` | string | No | `/workspace/ComfyUI/input` | Remote ComfyUI input directory |
| `comfyui_output_dir` | string | No | `/workspace/ComfyUI/output` | Remote ComfyUI output directory |

**Response (Success):**

```json
{
  "success": true,
  "workflow_id": "comfyui_workflow_1732234567_abc123",
  "message": "Workflow execution started"
}
```

**Response (Error):**

```json
{
  "success": false,
  "message": "Workflow file not found: /path/to/workflow.json"
}
```

**Status Codes:**
- `200` - Workflow execution started successfully
- `400` - Invalid request (missing required fields, file not found)
- `500` - Server error during execution

**Example Usage:**

```bash
curl -X POST http://localhost:5000/comfyui/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "ssh_connection": "ssh -p 40738 root@198.53.64.194",
    "workflow_file": "/home/user/workflows/txt2img.json",
    "workflow_name": "Text to Image",
    "input_images": []
  }'
```

```javascript
// JavaScript fetch example
const response = await fetch('/comfyui/workflow/execute', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    ssh_connection: sshConnection,
    workflow_file: workflowPath,
    workflow_name: 'My Workflow'
  })
});

const data = await response.json();
if (data.success) {
  const workflowId = data.workflow_id;
  // Start polling for progress...
}
```

---

### 2. Get Workflow Progress

Get real-time progress information for a running workflow.

**Endpoint:** `GET /comfyui/workflow/<workflow_id>/progress`

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workflow_id` | string | Yes | Workflow ID returned from execute endpoint |

**Response (Success):**

```json
{
  "success": true,
  "progress": {
    "workflow_id": "comfyui_workflow_1732234567_abc123",
    "workflow_name": "Image Enhancement",
    "prompt_id": "prompt-abc-def-123",
    "ssh_connection": "ssh -p 40738 root@198.53.64.194",
    "workflow_file": "/path/to/workflow.json",
    "status": "executing",
    "queue_position": null,
    "current_node": "KSampler",
    "total_nodes": 15,
    "completed_nodes": 8,
    "progress_percent": 53.3,
    "nodes": [
      {
        "node_id": "7",
        "node_type": "LoadImage",
        "status": "executed",
        "progress": 100.0,
        "message": "Image loaded successfully"
      },
      {
        "node_id": "12",
        "node_type": "KSampler",
        "status": "executing",
        "progress": 45.0,
        "message": "Sampling step 45/100"
      },
      {
        "node_id": "15",
        "node_type": "SaveImage",
        "status": "pending",
        "progress": 0.0,
        "message": null
      }
    ],
    "queue_time": "2024-11-21T10:30:00Z",
    "start_time": "2024-11-21T10:30:15Z",
    "end_time": null,
    "last_update": "2024-11-21T10:32:45Z",
    "outputs": [],
    "error_message": null,
    "failed_node": null
  }
}
```

**Workflow Status Values:**
- `queued` - Workflow is queued and waiting to execute
- `executing` - Workflow is currently running
- `completed` - Workflow finished successfully
- `failed` - Workflow encountered an error
- `cancelled` - Workflow was cancelled by user

**Node Status Values:**
- `pending` - Node has not started executing
- `executing` - Node is currently running
- `executed` - Node completed successfully
- `failed` - Node encountered an error

**Response (Not Found):**

```json
{
  "success": false,
  "message": "Workflow not found: comfyui_workflow_123"
}
```

**Status Codes:**
- `200` - Progress retrieved successfully
- `404` - Workflow not found
- `500` - Server error

**Example Usage:**

```bash
curl http://localhost:5000/comfyui/workflow/comfyui_workflow_1732234567_abc123/progress
```

```javascript
// Polling example
async function pollProgress(workflowId) {
  const interval = setInterval(async () => {
    const response = await fetch(`/comfyui/workflow/${workflowId}/progress`);
    const data = await response.json();
    
    if (data.success) {
      const progress = data.progress;
      updateUI(progress);
      
      // Stop polling if completed or failed
      if (progress.status === 'completed' || progress.status === 'failed') {
        clearInterval(interval);
      }
    }
  }, 2000); // Poll every 2 seconds
}
```

---

### 3. Cancel Workflow

Cancel a running workflow execution.

**Endpoint:** `POST /comfyui/workflow/<workflow_id>/cancel`

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workflow_id` | string | Yes | Workflow ID to cancel |

**Response (Success):**

```json
{
  "success": true,
  "message": "Workflow cancellation initiated"
}
```

**Response (Not Found):**

```json
{
  "success": false,
  "message": "Workflow not found or already completed: comfyui_workflow_123"
}
```

**Status Codes:**
- `200` - Cancellation initiated successfully
- `404` - Workflow not found or already completed
- `500` - Server error

**Example Usage:**

```bash
curl -X POST http://localhost:5000/comfyui/workflow/comfyui_workflow_1732234567_abc123/cancel
```

```javascript
async function cancelWorkflow(workflowId) {
  const response = await fetch(`/comfyui/workflow/${workflowId}/cancel`, {
    method: 'POST'
  });
  
  const data = await response.json();
  if (data.success) {
    console.log('Workflow cancelled');
  }
}
```

---

### 4. Get Workflow Outputs

Get list of generated output files for a completed workflow.

**Endpoint:** `GET /comfyui/workflow/<workflow_id>/outputs`

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workflow_id` | string | Yes | Workflow ID |

**Response (Success):**

```json
{
  "success": true,
  "outputs": [
    {
      "filename": "ComfyUI_00001_.png",
      "file_type": "image",
      "remote_path": "/workspace/ComfyUI/output/ComfyUI_00001_.png",
      "local_path": "/tmp/outputs/ComfyUI_00001_.png",
      "downloaded": true
    },
    {
      "filename": "ComfyUI_00002_.png",
      "file_type": "image",
      "remote_path": "/workspace/ComfyUI/output/ComfyUI_00002_.png",
      "local_path": "/tmp/outputs/ComfyUI_00002_.png",
      "downloaded": true
    }
  ]
}
```

**Response (Not Found):**

```json
{
  "success": false,
  "message": "Workflow not found: comfyui_workflow_123"
}
```

**Status Codes:**
- `200` - Outputs retrieved successfully
- `404` - Workflow not found
- `500` - Server error

**Example Usage:**

```bash
curl http://localhost:5000/comfyui/workflow/comfyui_workflow_1732234567_abc123/outputs
```

```javascript
async function getOutputs(workflowId) {
  const response = await fetch(`/comfyui/workflow/${workflowId}/outputs`);
  const data = await response.json();
  
  if (data.success) {
    data.outputs.forEach(output => {
      if (output.downloaded) {
        console.log(`Output available: ${output.local_path}`);
      }
    });
  }
}
```

---

### 5. Get Workflow State (Load from Disk)

Load persisted workflow state from disk. Used for restoring workflow progress after page refresh.

**Endpoint:** `GET /comfyui/workflow/state`

**Response (State Exists):**

```json
{
  "success": true,
  "state": {
    "workflow_id": "comfyui_workflow_1732234567_abc123",
    "workflow_name": "Image Enhancement",
    "status": "executing",
    "progress_percent": 53.3,
    ...
  }
}
```

**Response (No State):**

```json
{
  "success": true,
  "state": null
}
```

**Status Codes:**
- `200` - State loaded successfully (or no state found)
- `500` - Server error

**Example Usage:**

```bash
curl http://localhost:5000/comfyui/workflow/state
```

```javascript
// Restore workflow state on page load
async function restoreWorkflowState() {
  const response = await fetch('/comfyui/workflow/state');
  const data = await response.json();
  
  if (data.success && data.state) {
    const state = data.state;
    console.log(`Restoring workflow: ${state.workflow_name} (${state.progress_percent}%)`);
    
    // Resume monitoring
    pollProgress(state.workflow_id);
  }
}

// Call on page load
window.addEventListener('load', restoreWorkflowState);
```

---

### 6. Check Workflow Active Status

Check if a workflow is currently executing in the background.

**Endpoint:** `GET /comfyui/workflow/<workflow_id>/active`

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workflow_id` | string | Yes | Workflow ID |

**Response:**

```json
{
  "success": true,
  "active": true
}
```

**Status Codes:**
- `200` - Status retrieved successfully
- `500` - Server error

**Example Usage:**

```bash
curl http://localhost:5000/comfyui/workflow/comfyui_workflow_1732234567_abc123/active
```

```javascript
async function isWorkflowActive(workflowId) {
  const response = await fetch(`/comfyui/workflow/${workflowId}/active`);
  const data = await response.json();
  
  return data.success && data.active;
}
```

---

## Workflow Lifecycle

The typical workflow execution lifecycle:

```
1. Execute Workflow
   POST /comfyui/workflow/execute
   ↓
   Returns workflow_id
   
2. Monitor Progress (Poll every 2 seconds)
   GET /comfyui/workflow/<workflow_id>/progress
   ↓
   status: queued → executing → completed/failed/cancelled
   
3. Get Outputs (When completed)
   GET /comfyui/workflow/<workflow_id>/outputs
   
(Optional) Cancel Workflow
   POST /comfyui/workflow/<workflow_id>/cancel
   
(On Page Refresh) Restore State
   GET /comfyui/workflow/state
   ↓
   Resume monitoring if workflow is still executing
```

---

## State Persistence

Workflow state is persisted to `/tmp/comfyui_workflow_state.json` and survives:
- Server restarts
- Page refreshes
- Browser closures

The state file is automatically updated during workflow execution and can be loaded via the `/comfyui/workflow/state` endpoint.

---

## Error Handling

### Common Error Scenarios

**1. File Not Found**
```json
{
  "success": false,
  "message": "Workflow file not found: /path/to/workflow.json"
}
```
**Solution:** Verify the workflow file path exists on the server

**2. SSH Connection Failed**
```json
{
  "success": false,
  "message": "Failed to create SSH tunnel"
}
```
**Solution:** Verify SSH connection string and instance is running

**3. Workflow Execution Failed**
```json
{
  "success": true,
  "progress": {
    "status": "failed",
    "error_message": "Node execution failed: Out of memory",
    "failed_node": "KSampler"
  }
}
```
**Solution:** Check ComfyUI logs on remote instance, adjust workflow parameters

**4. Queue Timeout**
```json
{
  "success": true,
  "progress": {
    "status": "queued",
    "queue_position": 5,
    ...
  }
}
```
**Solution:** Wait for queue to clear, or cancel and retry

---

## Rate Limiting

No rate limiting is currently implemented. For production use, consider:
- Limiting concurrent workflows per client
- API rate limits on execute endpoint
- Request throttling on progress endpoint

---

## CORS Configuration

The API supports CORS for the following origins:
- `http://10.0.78.66`
- `http://localhost`
- `http://127.0.0.1`

All `/comfyui/workflow/*` endpoints support CORS preflight (`OPTIONS` requests).

---

## Complete Example: Full Workflow Execution

```javascript
class ComfyUIWorkflowClient {
  constructor(apiBaseUrl = 'http://localhost:5000') {
    this.apiBaseUrl = apiBaseUrl;
  }
  
  // Execute workflow
  async executeWorkflow(sshConnection, workflowFile, workflowName) {
    const response = await fetch(`${this.apiBaseUrl}/comfyui/workflow/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ssh_connection: sshConnection,
        workflow_file: workflowFile,
        workflow_name: workflowName
      })
    });
    
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.message);
    }
    
    return data.workflow_id;
  }
  
  // Monitor workflow with progress callback
  async monitorWorkflow(workflowId, onProgress) {
    return new Promise((resolve, reject) => {
      const interval = setInterval(async () => {
        try {
          const progress = await this.getProgress(workflowId);
          
          // Call progress callback
          onProgress(progress);
          
          // Check if completed
          if (progress.status === 'completed') {
            clearInterval(interval);
            resolve(progress);
          } else if (progress.status === 'failed' || progress.status === 'cancelled') {
            clearInterval(interval);
            reject(new Error(progress.error_message || 'Workflow failed'));
          }
        } catch (error) {
          clearInterval(interval);
          reject(error);
        }
      }, 2000);
    });
  }
  
  // Get progress
  async getProgress(workflowId) {
    const response = await fetch(`${this.apiBaseUrl}/comfyui/workflow/${workflowId}/progress`);
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.message);
    }
    
    return data.progress;
  }
  
  // Cancel workflow
  async cancelWorkflow(workflowId) {
    const response = await fetch(`${this.apiBaseUrl}/comfyui/workflow/${workflowId}/cancel`, {
      method: 'POST'
    });
    
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.message);
    }
  }
  
  // Get outputs
  async getOutputs(workflowId) {
    const response = await fetch(`${this.apiBaseUrl}/comfyui/workflow/${workflowId}/outputs`);
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.message);
    }
    
    return data.outputs;
  }
  
  // Restore state
  async restoreState() {
    const response = await fetch(`${this.apiBaseUrl}/comfyui/workflow/state`);
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.message);
    }
    
    return data.state;
  }
}

// Usage example
async function runWorkflow() {
  const client = new ComfyUIWorkflowClient();
  
  try {
    // Execute workflow
    console.log('Starting workflow...');
    const workflowId = await client.executeWorkflow(
      'ssh -p 40738 root@198.53.64.194',
      '/path/to/workflow.json',
      'My Test Workflow'
    );
    
    console.log(`Workflow started: ${workflowId}`);
    
    // Monitor progress
    const result = await client.monitorWorkflow(workflowId, (progress) => {
      console.log(`Progress: ${progress.progress_percent}% - ${progress.status}`);
      console.log(`Current node: ${progress.current_node || 'None'}`);
    });
    
    console.log('Workflow completed!');
    
    // Get outputs
    const outputs = await client.getOutputs(workflowId);
    console.log(`Generated ${outputs.length} outputs:`);
    outputs.forEach(output => {
      console.log(`  - ${output.filename} (${output.local_path})`);
    });
    
  } catch (error) {
    console.error('Workflow failed:', error.message);
  }
}

// Restore on page load
window.addEventListener('load', async () => {
  const client = new ComfyUIWorkflowClient();
  const state = await client.restoreState();
  
  if (state) {
    console.log(`Restoring workflow: ${state.workflow_name} (${state.progress_percent}%)`);
    
    // Resume monitoring
    try {
      await client.monitorWorkflow(state.workflow_id, (progress) => {
        console.log(`Progress: ${progress.progress_percent}%`);
      });
    } catch (error) {
      console.error('Monitoring failed:', error);
    }
  }
});
```

---

## Testing with curl

```bash
# Execute workflow
WORKFLOW_ID=$(curl -s -X POST http://localhost:5000/comfyui/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "ssh_connection": "ssh -p 40738 root@198.53.64.194",
    "workflow_file": "/home/user/workflows/test.json",
    "workflow_name": "Test Workflow"
  }' | jq -r '.workflow_id')

echo "Workflow ID: $WORKFLOW_ID"

# Monitor progress
while true; do
  STATUS=$(curl -s "http://localhost:5000/comfyui/workflow/$WORKFLOW_ID/progress" | jq -r '.progress.status')
  PROGRESS=$(curl -s "http://localhost:5000/comfyui/workflow/$WORKFLOW_ID/progress" | jq -r '.progress.progress_percent')
  
  echo "Status: $STATUS, Progress: $PROGRESS%"
  
  if [ "$STATUS" == "completed" ] || [ "$STATUS" == "failed" ]; then
    break
  fi
  
  sleep 2
done

# Get outputs
curl -s "http://localhost:5000/comfyui/workflow/$WORKFLOW_ID/outputs" | jq '.outputs'
```

---

## Version History

- **v1.0** (2024-11-21) - Initial API release
  - Execute workflow endpoint
  - Progress monitoring endpoint
  - Cancel workflow endpoint
  - Outputs endpoint
  - State persistence endpoint
  - Active status endpoint

---

## Support

For issues and questions:
- Check the logs at `/logs/vastai/`
- Review the implementation plan at `/docs/COMFYUI_WORKFLOW_EXECUTION_PLAN.md`
- Examine server logs for detailed error information
