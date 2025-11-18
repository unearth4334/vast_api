# Debugging the Reboot Instance Workflow

This document explains how to debug the reboot step in the instance setup workflow.

## Overview

The reboot workflow is the final step in the ComfyUI instance setup process. It reboots a VastAI instance using the VastAI API to apply all configuration changes made during the setup workflow.

## Workflow Architecture

### Frontend (JavaScript)
- **File**: `app/webui/js/vastai/instances.js`
- **Function**: `rebootInstance()`
- **Line**: 1691-1897

### Backend API
- **File**: `app/sync/sync_api.py`
- **Endpoint**: `POST /ssh/reboot-instance`
- **Line**: 1445-1511

### VastAI API Integration
- **File**: `app/utils/vastai_api.py`
- **Function**: `reboot_instance(api_key, instance_id)`
- **Line**: 827-930

## Debug Features

### Console Logging

Enhanced debug logging has been added to track the reboot workflow:

```javascript
🐛 DEBUG: Starting reboot workflow
🐛 DEBUG: Timestamp: [ISO timestamp]
🐛 DEBUG: SSH Connection String: (exists/empty)
🐛 DEBUG: Workflow step element: Found/Not found
🐛 DEBUG: Calling API: GET /vastai/instances
🐛 DEBUG: Instance API response: [JSON response]
🐛 DEBUG: Found X instance(s)
🐛 DEBUG: Target instance ID: [instance_id]
🐛 DEBUG: Calling API: POST /ssh/reboot-instance
🐛 DEBUG: Request payload: [JSON payload]
🐛 DEBUG: Reboot API response: [JSON response]
🐛 DEBUG: Response success: true/false
🐛 DEBUG: Response message: [message]
```

### Server-Side Logging

Backend debug logs are also available:

```python
🐛 DEBUG: Reboot endpoint called
🐛 DEBUG: Request data: {...}
🐛 DEBUG: Instance ID from request: [instance_id]
🐛 DEBUG: Importing VastAI API modules
🐛 DEBUG: Loading VastAI API key
🐛 DEBUG: API key loaded successfully (length: X)
🐛 DEBUG: Calling reboot_instance API for instance [instance_id]
🐛 DEBUG: Reboot API response: {...}
🐛 DEBUG: Reboot successful/failed
```

## How to Use Debug Mode

### 1. Enable Browser Console

Open your browser's Developer Tools (F12) and navigate to the Console tab.

### 2. Execute Reboot Step

Click the "🔄 Reboot Instance" button in the workflow. All debug messages will appear in the console with the 🐛 DEBUG prefix.

### 3. View Server Logs

Check the server console output for backend debug messages:

```bash
python run_sync_api.py
```

### 4. Analyze Debug Output

Debug messages provide:
- **Timestamp**: When each step occurred
- **API Calls**: What endpoints were called and with what data
- **Responses**: Complete API responses for troubleshooting
- **Error Details**: Exception type, message, and stack trace

## Common Issues and Solutions

### Issue: "Please enter an SSH connection string first"

**Debug Output:**
```
🐛 DEBUG: SSH Connection String: (empty)
🐛 DEBUG: Reboot aborted - No SSH connection
```

**Solution:** Enter a valid SSH connection string in the format:
```
ssh -p PORT root@HOST -L 8080:localhost:8080
```

### Issue: "No active VastAI instances found"

**Debug Output:**
```
🐛 DEBUG: No instances found in response
```

**Solution:** 
1. Click "🔄 Load Instances" to fetch your VastAI instances
2. Ensure you have an active VastAI instance
3. Check that your VastAI API key is configured correctly

### Issue: "VastAI API key not found"

**Debug Output:**
```
🐛 DEBUG: VastAI API key not found
```

**Solution:**
1. Create `api_key.txt` in the project root
2. Add your VastAI API key to the file
3. Restart the application

### Issue: Reboot API fails

**Debug Output:**
```
🐛 DEBUG: Reboot failed - API returned unsuccessful result
🐛 DEBUG: Error message: [error details]
```

**Solution:**
1. Check the instance ID is valid
2. Verify the instance is in a rebootable state
3. Check VastAI API status and credentials
4. Review the complete error message in the console

## Testing the Workflow

### Mock Test (Without Real Instance)

1. Start the application
2. Open browser console (F12)
3. Navigate to VastAI Setup tab
4. Click "🔄 Reboot Instance" button
5. Observe debug messages in console

Expected output:
```
🔄 rebootInstance called
🐛 DEBUG: Starting reboot workflow
🐛 DEBUG: SSH Connection String: (empty)
❌ No SSH connection string found
🐛 DEBUG: Reboot aborted - No SSH connection
```

### Full Test (With Real Instance)

1. Configure VastAI API key in `api_key.txt`
2. Start the application
3. Open VastAI Setup tab
4. Enter SSH connection string
5. Click "🔄 Load Instances"
6. Click "🔄 Reboot Instance"
7. Monitor console and server logs for debug output

Expected successful output:
```
🐛 DEBUG: Starting reboot workflow
🐛 DEBUG: Found 1 instance(s)
🐛 DEBUG: Target instance ID: 12345
🐛 DEBUG: Calling API: POST /ssh/reboot-instance
🐛 DEBUG: Response success: true
🐛 DEBUG: Reboot initiated successfully
🐛 DEBUG: Emitting success event for workflow
🐛 DEBUG: Reboot workflow completed successfully
```

## Screenshots

### Initial Workflow View
![Workflow Overview](https://github.com/user-attachments/assets/de3f8c25-0c07-4a10-b81f-f6c67fca7990)

### Workflow Steps
![Workflow Steps](https://github.com/user-attachments/assets/1f71a1eb-1c57-4ff9-9bd3-2416d43956bf)

### Reboot Step
![Reboot Step](https://github.com/user-attachments/assets/2320a8c8-0b9a-4d54-b40b-ee2d7f67dd07)

### Debug Console Output
![Debug Console](https://github.com/user-attachments/assets/a57173ae-3a28-4de5-9e35-9a3e80685eb0)

## Architecture Flow

```
User clicks "Reboot Instance"
    ↓
rebootInstance() called (instances.js)
    ↓
Check SSH connection string exists
    ↓
Fetch instance list (GET /vastai/instances)
    ↓
Select target instance (running or first)
    ↓
Call reboot API (POST /ssh/reboot-instance)
    ↓
Backend receives request (sync_api.py)
    ↓
Load VastAI API key
    ↓
Call VastAI API (vastai_api.py)
    ↓
PUT /instances/reboot/{instance_id}/ to VastAI
    ↓
Return success/failure response
    ↓
Update UI with progress indicators
    ↓
Emit workflow completion event
```

## Debug Log Filters

To filter debug logs in browser console:

- All debug messages: `🐛 DEBUG`
- API calls only: `Calling API`
- Responses only: `response:`
- Errors only: `Error` or `❌`
- Success only: `✅` or `success`

## Performance Monitoring

Debug logs include timing information:

- **Timestamp**: ISO 8601 format for precise timing
- **Duration**: Progress indicator tracks total time
- **Wait periods**: 2-second wait after reboot initiation

## Error Handling

All errors are logged with:
1. Error type (Exception class name)
2. Error message
3. Full stack trace (in console)
4. Context information (instance ID, API call details)

## Additional Resources

- [VastAI API Documentation](https://vast.ai/docs/api/overview)
- [Progress Indicators](./progress-indicators.js)
- [Workflow System](./workflow.js)
