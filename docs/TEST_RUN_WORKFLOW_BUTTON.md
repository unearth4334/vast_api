# Run Workflow Feature - Test Documentation

## Overview

This document describes the "▶️ Run Workflow" button feature and its test coverage.

---

## Feature Description

### What It Does

The "Run Workflow" button in the Create tab:

1. **Collects Form Data**: Gathers all user inputs from the workflow form
2. **Validates Inputs**: Checks required fields and SSH connection
3. **Uploads Images**: Extracts base64 images and uploads to remote instance
4. **Generates Workflow**: Creates final workflow JSON with user inputs
5. **Uploads Workflow**: Transfers workflow JSON to remote instance
6. **Queues Execution**: Uses BrowserAgent to queue workflow on ComfyUI
7. **Tracks Progress**: Returns prompt_id for execution tracking

### User Flow

```
[User fills form] 
    ↓
[User clicks "▶️ Run Workflow"]
    ↓
[Validation: SSH connection + required fields]
    ↓
[Button shows "⏳ Executing..." and disables]
    ↓
[API call: POST /create/queue-workflow]
    ↓
[Success: Show message + prompt_id]
OR
[Error: Show error message + re-enable button]
```

---

## Architecture

### Frontend (WebUI)

**File**: `app/webui/js/create/create-tab.js`

**Key Function**: `executeWorkflow()`

```javascript
async function executeWorkflow() {
    // 1. Validate workflow selected
    if (!CreateTabState.selectedWorkflow) {
        showCreateError('Please select a workflow first');
        return;
    }
    
    // 2. Check SSH connection
    const sshConnection = getCurrentSSHConnection();
    if (!sshConnection) {
        showCreateError('Please connect to an instance');
        return;
    }
    
    // 3. Validate required fields
    for (const field of workflow.inputs) {
        if (field.required && !CreateTabState.formValues[field.id]) {
            showCreateError(`Please fill in: ${field.label}`);
            return;
        }
    }
    
    // 4. Disable button and show executing state
    updateExecuteButton(true);
    
    // 5. Call API
    const response = await fetch('/create/queue-workflow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            ssh_connection: sshConnection,
            workflow_id: workflowId,
            inputs: CreateTabState.formValues
        })
    });
    
    // 6. Handle response
    if (data.success) {
        showCreateSuccess(data.message);
    } else {
        showCreateError(data.message);
    }
    
    // 7. Re-enable button
    updateExecuteButton(false);
}
```

**Button States**:
- Normal: `<span>▶️</span> Run Workflow`
- Executing: `<span>⏳</span> Executing...` (disabled)

### Backend (API)

**File**: `app/sync/create_api.py`

**Endpoint**: `POST /create/queue-workflow`

```python
@create_bp.route('/queue-workflow', methods=['POST'])
def queue_workflow_browser_agent():
    """
    Queue workflow via BrowserAgent
    
    Request:
        {
            "ssh_connection": "ssh -p PORT root@HOST",
            "workflow_id": "IMG_to_VIDEO_canvas",
            "inputs": {
                "input_image": "data:image/jpeg;base64,...",
                "positive_prompt": "...",
                ...
            }
        }
    
    Response (Success):
        {
            "success": true,
            "prompt_id": "abc-123-def-456",
            "message": "Workflow queued successfully!",
            "workflow_id": "IMG_to_VIDEO_canvas"
        }
    
    Response (Error):
        {
            "success": false,
            "message": "Error description",
            "details": "Additional error info"
        }
    """
```

**Processing Steps**:

1. **Load Workflow**: Load workflow template and webui config
2. **Generate Workflow**: Apply user inputs to template
3. **Validate**: Check workflow structure is valid
4. **Connect SSH**: Establish SSH connection to remote instance
5. **Upload Workflow**: Transfer JSON file to remote /tmp
6. **Check Browser Server**: Ensure BrowserAgent server is running
7. **Start Server**: If not running, start BrowserAgent server
8. **Queue Workflow**: Execute `queue_workflow_ui_click.py` script
9. **Parse Response**: Extract prompt_id from output
10. **Cleanup**: Remove temporary files
11. **Return Result**: Send prompt_id or error to client

---

## Test Coverage

### 1. API Tests (Unit)

**File**: `test/test_run_workflow_api.py`

**Test Cases**:

#### ✅ Test 1: Successful Workflow Queueing
- Mocks all dependencies (SSH, workflow loader, generator, validator)
- Simulates successful queueing
- Verifies prompt_id returned
- Checks SSH connection established
- Validates SFTP upload occurred

#### ✅ Test 2: Missing SSH Connection
- Request without ssh_connection field
- Expects 400 Bad Request
- Error message mentions SSH connection

#### ✅ Test 3: Missing Workflow ID
- Request without workflow_id field
- Expects 400 Bad Request
- Error message mentions Workflow ID

#### ✅ Test 4: Workflow Not Found
- workflow_id references non-existent workflow
- Expects 404 Not Found
- Error message says "not found"

#### ✅ Test 5: Workflow Validation Failure
- Generated workflow fails validation
- Expects 400 Bad Request
- Error message mentions validation
- Returns validation errors

#### ✅ Test 6: SSH Authentication Failure
- SSH connection fails with AuthenticationException
- Expects 401 Unauthorized
- Error message mentions authentication

#### ✅ Test 7: No Prompt ID Returned
- Queueing succeeds but no prompt_id in response
- Expects 500 Server Error
- Error message mentions missing prompt ID

**Running**:
```bash
python3 test/test_run_workflow_api.py
```

**Expected Output**:
```
========================================================================
Run Workflow API Tests
========================================================================

test_queue_workflow_success (__main__.TestRunWorkflowAPI) ... ok
test_queue_workflow_missing_ssh_connection (__main__.TestRunWorkflowAPI) ... ok
test_queue_workflow_missing_workflow_id (__main__.TestRunWorkflowAPI) ... ok
test_queue_workflow_not_found (__main__.TestRunWorkflowAPI) ... ok
test_queue_workflow_validation_failure (__main__.TestRunWorkflowAPI) ... ok
test_queue_workflow_ssh_auth_failure (__main__.TestRunWorkflowAPI) ... ok
test_queue_workflow_no_prompt_id (__main__.TestRunWorkflowAPI) ... ok

========================================================================
TEST SUMMARY
========================================================================
Tests run: 7
Successes: 7
Failures: 0
Errors: 0

✅ All tests passed!
```

### 2. WebUI Tests (E2E with Playwright)

**File**: `test/test_run_workflow_button.py`

**Test Cases**:

#### ✅ Test 1: Run Workflow Button Exists
- Navigates to Create tab
- Selects workflow
- Verifies button exists
- Checks button text contains "▶️" or "Run Workflow"

#### ✅ Test 2: Error Without SSH Connection
- Attempts to run workflow without SSH connection
- Verifies error message displayed
- Error mentions "connect" or "instance"

#### ✅ Test 3: Validates Required Fields
- Sets SSH connection
- Clicks button without filling required fields
- Verifies error message displayed
- Error mentions "required"

#### ✅ Test 4: Button Disables During Execution
- Fills form completely
- Clicks Run Workflow button
- Immediately checks button state
- Verifies button is disabled
- Verifies button text shows "Executing" or "⏳"

#### ✅ Test 5: Successful Workflow Execution
- Mocks successful API response
- Clicks Run Workflow button
- Waits for success message
- Verifies success message displayed
- Checks button re-enabled after completion

#### ✅ Test 6: API Error Handling
- Mocks API error response (500)
- Clicks Run Workflow button
- Waits for error message
- Verifies error message displayed
- Checks button re-enabled after error

#### ✅ Test 7: Form Values Sent to API
- Fills form with specific values
- Captures API request payload
- Verifies ssh_connection sent
- Verifies workflow_id sent
- Verifies form inputs sent correctly

**Prerequisites**:
```bash
pip install playwright
playwright install chromium
```

**Running**:
```bash
# Start dev server first
python3 app.py

# In another terminal
python3 test/test_run_workflow_button.py
```

**Expected Output**:
```
========================================================================
Run Workflow Button Tests (Playwright)
========================================================================

🌐 Launching browser...
✅ Browser ready

============================================================
Test 1: Run Workflow button exists
============================================================
📍 Navigating to Create tab...
✅ Navigated to Create tab
📍 Selecting workflow...
✅ Workflow selected and form loaded
✅ PASS: Run Workflow button exists with correct text

============================================================
Test 2: Error shown without SSH connection
============================================================
📍 Navigating to Create tab...
✅ Navigated to Create tab
📍 Selecting workflow...
✅ Workflow selected and form loaded
✅ PASS: Error shown without SSH connection

... (additional tests) ...

🔒 Browser closed

============================================================
TEST SUMMARY
============================================================
Tests run: 7
Passed: 7
Failed: 0

✅ All tests passed!
```

---

## Integration Points

### 1. SSH Connection
- Retrieved from toolbar via `getCurrentSSHConnection()`
- Format: `"ssh -p PORT root@HOST"`
- Required for workflow execution

### 2. Workflow Generator
- Class: `WorkflowGenerator`
- Method: `generate_workflow(workflow_id, template, config, inputs)`
- Replaces tokens with user input values

### 3. BrowserAgent
- Script: `queue_workflow_ui_click.py`
- Runs on remote instance
- Uses Playwright to click ComfyUI's Queue Prompt button
- Returns prompt_id for tracking

### 4. ExecutionQueue Component
- Updates when workflow queued
- Shows current execution status
- Polls ComfyUI API for progress

---

## Error Scenarios

### Frontend Errors

| Error | Trigger | Message | Action |
|-------|---------|---------|--------|
| No workflow selected | Click button before selecting | "Please select a workflow first" | Select workflow |
| No SSH connection | No instance connected | "Please connect to an instance" | Connect via toolbar |
| Missing required field | Empty required input | "Please fill in required field: {label}" | Fill field |
| Network error | API request fails | "Error: {error message}" | Check connection |

### Backend Errors

| Status | Error | Message | Cause |
|--------|-------|---------|-------|
| 400 | Missing ssh_connection | "SSH connection string is required" | Client didn't send connection |
| 400 | Missing workflow_id | "Workflow ID is required" | Client didn't send workflow ID |
| 404 | Workflow not found | "Workflow file not found: {id}" | Invalid workflow_id |
| 400 | Validation failure | "Generated workflow failed validation" | Invalid workflow structure |
| 401 | SSH auth failure | "SSH authentication failed" | SSH keys not configured |
| 500 | Queue error | "Failed to queue workflow on ComfyUI" | ComfyUI error |
| 500 | No prompt_id | "Workflow was sent but no prompt ID returned" | BrowserAgent error |

---

## Manual Testing Checklist

### Prerequisites
- [ ] Backend running (`python3 app.py`)
- [ ] VastAI instance running with ComfyUI
- [ ] SSH connection established via toolbar

### Test Steps

1. **Navigate to Create Tab**
   - [ ] Click "Create" in navigation
   - [ ] Verify workflow grid visible

2. **Select Workflow**
   - [ ] Click on "IMG to VIDEO" workflow
   - [ ] Verify form loads

3. **Test Without SSH Connection**
   - [ ] Disconnect instance (if connected)
   - [ ] Fill required fields
   - [ ] Click "▶️ Run Workflow"
   - [ ] Verify error: "Please connect to an instance"

4. **Test Without Required Fields**
   - [ ] Connect to instance
   - [ ] Leave image field empty
   - [ ] Click "▶️ Run Workflow"
   - [ ] Verify error: "Please fill in required field"

5. **Test Normal Execution**
   - [ ] Fill all required fields
   - [ ] Upload test image
   - [ ] Fill positive prompt
   - [ ] Click "▶️ Run Workflow"
   - [ ] Verify button changes to "⏳ Executing..."
   - [ ] Verify button is disabled
   - [ ] Wait for response
   - [ ] Verify success message with prompt_id
   - [ ] Verify button returns to "▶️ Run Workflow"
   - [ ] Verify button re-enabled

6. **Test Error Handling**
   - [ ] Disconnect instance mid-execution (simulate error)
   - [ ] Click "▶️ Run Workflow"
   - [ ] Verify error message displayed
   - [ ] Verify button re-enabled

7. **Test Execution Queue**
   - [ ] After successful queue
   - [ ] Check Execution Queue section
   - [ ] Verify prompt_id appears
   - [ ] Verify status shows "queued" or "running"

---

## Known Issues

### Issue 1: Image Upload Size
- **Problem**: Large images (>10MB) may timeout
- **Workaround**: Resize images before upload
- **Status**: Needs investigation

### Issue 2: SSH Connection Persistence
- **Problem**: SSH connection string not persisted across page reloads
- **Workaround**: Reconnect via toolbar after reload
- **Status**: Feature request

### Issue 3: BrowserAgent Not Running
- **Problem**: First queue attempt may fail if BrowserAgent server not started
- **Workaround**: Endpoint now auto-starts server
- **Status**: Fixed in current version

---

## Future Enhancements

### Planned Features
1. **Progress Bar**: Show upload progress for large images
2. **Queue History**: Show list of recent executions
3. **Cancel Button**: Allow canceling queued workflows
4. **Retry Button**: One-click retry for failed workflows
5. **Preset Save**: Save form values as preset for reuse

### Performance Improvements
1. **Image Compression**: Auto-compress large images
2. **Parallel Uploads**: Upload multiple images concurrently
3. **Connection Pooling**: Reuse SSH connections
4. **Response Caching**: Cache workflow metadata

---

## Troubleshooting

### Button Not Responding
**Symptoms**: Clicking button does nothing

**Checks**:
1. Open browser console (F12)
2. Look for JavaScript errors
3. Check if `executeWorkflow()` is defined
4. Verify CreateTabState is initialized

### API Returns 500 Error
**Symptoms**: Error message after clicking button

**Checks**:
1. Check backend logs
2. Verify SSH connection valid
3. Test SSH manually: `ssh -p PORT root@HOST`
4. Check BrowserAgent installed on remote
5. Verify ComfyUI is running on remote

### Workflow Queues But Doesn't Execute
**Symptoms**: Success message but no output

**Checks**:
1. Open ComfyUI web interface
2. Check queue for prompt_id
3. Look for errors in ComfyUI console
4. Verify workflow JSON is valid
5. Check remote /tmp for workflow file

---

## Test Maintenance

### Adding New Tests

**API Test Template**:
```python
@patch('app.sync.create_api.paramiko.SSHClient')
@patch('app.sync.create_api.load_workflow_json')
# ... other mocks
def test_new_scenario(self, mock_ssh, mock_load):
    # Setup mocks
    mock_load.return_value = self.mock_workflow_template
    
    # Make request
    response = self.client.post(
        '/create/queue-workflow',
        json=self.valid_inputs
    )
    
    # Verify response
    self.assertEqual(response.status_code, 200)
    data = json.loads(response.data)
    self.assertTrue(data['success'])
```

**WebUI Test Template**:
```python
async def test_new_scenario(self):
    print("\nTest: New Scenario")
    try:
        await self.navigate_to_create_tab()
        await self.select_workflow()
        
        # Test actions
        # ...
        
        # Assertions
        # ...
        
        print("✅ PASS: New scenario")
        self.passed += 1
    except Exception as e:
        print(f"❌ FAIL: {e}")
        self.failed += 1
```

### Updating Tests for Changes

When modifying the Run Workflow feature:

1. **Update API Tests** if backend logic changes
2. **Update WebUI Tests** if button behavior changes
3. **Update Documentation** to reflect new behavior
4. **Add Regression Tests** for any bugs fixed

---

## Summary

**Test Coverage**: Comprehensive

- ✅ **7 API unit tests** covering all error scenarios
- ✅ **7 WebUI E2E tests** covering user interactions
- ✅ **Integration** with SSH, BrowserAgent, ComfyUI
- ✅ **Error handling** for all known failure modes
- ✅ **Manual test checklist** for QA verification

**Confidence Level**: High

The Run Workflow feature is thoroughly tested with both automated unit tests and end-to-end browser tests. All critical paths are covered, including success scenarios, validation errors, and API failures.

**Next Steps**: Run test suites regularly during development and before releases to ensure feature stability.
