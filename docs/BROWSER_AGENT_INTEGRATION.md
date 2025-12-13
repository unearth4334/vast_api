# BrowserAgent Integration for Workflow Execution

## Overview

This document describes the new browser-based workflow execution system that replaces the previous API-based approach. Instead of converting workflows to API format and submitting them programmatically, we now use BrowserAgent to open workflows in a Chromium browser and interact with the ComfyUI interface directly.

## Why Browser-Based Execution?

**Problem with API Format:**
- Some custom nodes have bugs when workflows are converted to API format
- API format requires maintaining separate workflow versions
- Difficult to debug issues that only occur in API mode

**Benefits of Browser-Based Execution:**
- Uses the exact same workflow file as the ComfyUI canvas editor
- No conversion required - what you see in the editor is what executes
- Compatible with all custom nodes (no API conversion issues)
- Can handle complex UI interactions that aren't supported in API mode

## Installation

### Setup Workflow Step

A new setup step has been added to the VastAI Setup tab:

**Button:** 🌐 Install BrowserAgent

**What it does:**
1. Updates apt package list
2. Installs system dependencies for Chromium (libnss3, libnspr4, etc.)
3. Clones/updates BrowserAgent repository from GitHub
4. Installs Python dependencies (playwright, typer, rich)
5. Downloads and installs Chromium browser (~300MB)
6. Verifies installation by importing BrowserAgent
7. Runs unit tests to validate functionality

**Configuration Location:**
- Template: `app/webui/templates/templates_comfyui.yml`
- Step type: `browser_agent_install`
- Execution handler: `execute_browser_agent_install()` in `app/sync/sync_api.py`

### Manual Installation

For manual installation on a cloud instance, see the deployment guide in the user request above.

## Template Configuration

### Step Definition

```yaml
- name: "Install BrowserAgent"
  type: "browser_agent_install"
  description: "Install BrowserAgent for automated workflow execution in browser"
  repository: "https://github.com/unearth4334/BrowserAgent.git"
  destination: "/root/BrowserAgent"
  branch: "main"
  commands:
    - name: "Update package list"
      command: "apt-get update"
      description: "Update apt package list"
      
    - name: "Install system dependencies"
      command: |
        apt-get install -y \
          libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
          libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
          libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
          libgbm1 libpango-1.0-0 libcairo2 libasound2
      description: "Install required system libraries for Chromium"
      
    - name: "Clone or update BrowserAgent"
      command: |
        cd /root
        if [ ! -d "BrowserAgent" ]; then
          git clone https://github.com/unearth4334/BrowserAgent.git
          cd BrowserAgent
          git checkout main
        else
          cd BrowserAgent
          git fetch origin
          git checkout main
          git pull origin main
        fi
      description: "Clone BrowserAgent repository or update existing installation"
      
    - name: "Install Python dependencies"
      command: "cd /root/BrowserAgent && pip install --upgrade ."
      description: "Install BrowserAgent Python package and dependencies"
      
    - name: "Install Playwright browser"
      command: "python3 -m playwright install chromium"
      description: "Install Chromium browser for Playwright (~300MB)"
      
    - name: "Verify installation"
      command: |
        PYTHONPATH=/root/BrowserAgent/src:$PYTHONPATH python3 -c "from browser_agent.agent.core import Agent; print('✓ BrowserAgent import successful')"
      description: "Verify BrowserAgent can be imported"
      
    - name: "Run unit tests"
      command: "cd /root/BrowserAgent && PYTHONPATH=/root/BrowserAgent/src:$PYTHONPATH python3 -m pytest tests/ --ignore=tests/integration/ -v --tb=short"
      description: "Run BrowserAgent unit tests to verify installation"
      optional: true
```

### UI Button

```yaml
- label: "🌐 Install BrowserAgent"
  action: "install_browser_agent"
  style: "primary"
  tooltip: "Install BrowserAgent for automated browser-based workflow execution"
```

## Implementation Details

### Installation Script

The `execute_browser_agent_install()` function in `app/sync/sync_api.py` executes a comprehensive installation script that:

1. **Updates System Packages**
   ```bash
   apt-get update
   ```

2. **Installs Chromium Dependencies**
   ```bash
   apt-get install -y libnss3 libnspr4 libatk1.0-0 ... (17 packages)
   ```

3. **Clones/Updates Repository**
   - Checks if `/root/BrowserAgent` exists
   - If not: clones from GitHub
   - If exists: fetches and pulls latest changes

4. **Installs Python Package**
   ```bash
   cd /root/BrowserAgent
   pip install --upgrade .
   ```
   This installs: playwright>=1.47.0, typer>=0.12.0, rich>=13.0.0

5. **Downloads Chromium**
   ```bash
   python3 -m playwright install chromium
   ```
   Downloads ~300MB Chromium binary to `~/.cache/ms-playwright/`

6. **Verifies Installation**
   - Tests Python import
   - Checks Playwright version
   - Verifies Chromium executable exists
   - Runs 235 unit tests (optional, failures are warnings)

### Timeout Settings

- **Timeout:** 600 seconds (10 minutes)
- **Reason:** Chromium download can take several minutes depending on connection speed

### Error Handling

The function uses enhanced logging to track:
- Operation start/completion
- SSH connection details
- Command execution status
- Error types and messages
- Performance metrics

All errors are logged to the enhanced logger with context for debugging.

## Next Steps

### 1. Remove Old API-Based Workflow Execution

**Files to modify:**
- `app/sync/workflow_executor.py` - Remove API format conversion
- `app/create/workflow_generator.py` - Keep token replacement, remove API format generation
- Any routes that submit workflows via ComfyUI API

**What to keep:**
- Token-based workflow system (still needed for parameter replacement)
- Canvas format workflow files
- Workflow configuration YAML files

### 2. Implement Browser-Based Execution

**New functionality needed:**

```python
# app/sync/browser_workflow_executor.py

from browser_agent.agent.core import Agent
from browser_agent.server.browser_server import BrowserServer

class BrowserWorkflowExecutor:
    """Execute ComfyUI workflows using BrowserAgent"""
    
    def __init__(self, comfyui_url: str = "http://localhost:18188"):
        self.comfyui_url = comfyui_url
        self.browser_server = None
        
    async def start_browser_server(self, port: int = 8765):
        """Start the browser server for remote control"""
        # Implementation here
        pass
        
    async def load_workflow(self, workflow_path: str):
        """Load a workflow JSON file in ComfyUI"""
        # 1. Navigate to ComfyUI URL
        # 2. Click "Load" button
        # 3. Upload workflow file or paste JSON
        pass
        
    async def queue_workflow(self):
        """Click the Queue Prompt button to start execution"""
        # Implementation here
        pass
        
    async def monitor_progress(self):
        """Monitor workflow execution progress"""
        # Implementation here
        pass
        
    async def download_outputs(self, output_dir: str):
        """Download completed workflow outputs"""
        # Implementation here
        pass
```

### 3. Update WebUI Create Tab

**Changes needed:**
- Remove API format workflow generation option
- Update workflow execution to use BrowserWorkflowExecutor
- Add browser connection status indicator
- Show real-time browser screenshots during execution (optional)

### 4. Test Browser-Based Execution

**Test scenarios:**
1. Load IMG_to_VIDEO_canvas.json in browser
2. Replace tokens with user inputs
3. Queue workflow via browser click
4. Monitor progress
5. Download outputs
6. Handle errors (node errors, connection issues, etc.)

### 5. Documentation Updates

**Documents to update:**
- README.md - Explain browser-based execution
- TESTING_GUIDE.md - Add browser execution tests
- User guides - Update workflow execution instructions

## Testing the Installation

After running the "Install BrowserAgent" step, verify the installation:

### Method 1: Check Installation Log

Look for these success messages in the output:
```
✓ BrowserAgent import successful
Version 1.57.0
✓ Chromium executable found
===== 235 passed in 0.59s =====
✅ BrowserAgent installation completed successfully
```

### Method 2: Manual SSH Test

```bash
# SSH into the instance
ssh -p <PORT> <USER>@<HOST>

# Test import
PYTHONPATH=/root/BrowserAgent/src:$PYTHONPATH python3 -c "from browser_agent.agent.core import Agent; print('OK')"

# Check Playwright
python3 -m playwright --version

# Run tests
cd /root/BrowserAgent
PYTHONPATH=/root/BrowserAgent/src:$PYTHONPATH python3 -m pytest tests/ --ignore=tests/integration/ -v
```

### Method 3: Test Browser Server

```bash
# Start server
cd /root/BrowserAgent
PYTHONPATH=/root/BrowserAgent/src:$PYTHONPATH python3 -m browser_agent.server.browser_server \
    --port 8765 \
    --headless \
    --initial-url "http://localhost:18188" &

# Test ping
PYTHONPATH=/root/BrowserAgent/src:$PYTHONPATH python3 -m browser_agent.server.browser_client \
    --host localhost \
    --port 8765 \
    ping

# Stop server
pkill -f browser_server
```

## Architecture Comparison

### Old: API-Based Execution

```
User Input → Token Replacement → Canvas JSON → API Format Conversion → POST to /prompt → Execute
                                                    ↑
                                            (conversion bugs)
```

### New: Browser-Based Execution

```
User Input → Token Replacement → Canvas JSON → Upload to Browser → Click Queue → Execute
                                                    ↑
                                        (no conversion needed)
```

## Benefits Summary

1. **Reliability:** No API conversion bugs
2. **Simplicity:** One workflow format (canvas JSON)
3. **Compatibility:** Works with all custom nodes
4. **Debuggability:** Can see actual browser interactions
5. **Flexibility:** Can handle complex UI scenarios
6. **Future-proof:** Updates to ComfyUI UI automatically supported

## Known Limitations

1. **Performance:** Slightly slower than direct API calls (negligible for most workflows)
2. **Headless Mode:** Requires headless browser support on cloud instance
3. **Dependencies:** Additional system dependencies for Chromium
4. **Disk Space:** Chromium browser ~300MB

## Resources

- **BrowserAgent Repository:** https://github.com/unearth4334/BrowserAgent
- **Playwright Documentation:** https://playwright.dev/python/
- **ComfyUI Repository:** https://github.com/comfyanonymous/ComfyUI
