# BrowserAgent Setup Quick Start

## Purpose

Install BrowserAgent on your VastAI cloud instance to enable browser-based workflow execution. This replaces the old API-based workflow execution method and eliminates conversion bugs with custom nodes.

## Prerequisites

- Active VastAI instance with SSH access
- ComfyUI installed and running
- SSH connection configured in VastAI Setup tab

## Installation Steps

### 1. Navigate to VastAI Setup Tab

In the web interface, go to the **VastAI Setup** tab.

### 2. Click "🌐 Install BrowserAgent" Button

This button will:
- Update system packages
- Install 17 system dependencies for Chromium
- Clone BrowserAgent repository
- Install Python dependencies (playwright, typer, rich)
- Download Chromium browser (~300MB)
- Verify installation
- Run 235 unit tests

**Expected Duration:** 5-10 minutes (mostly Chromium download)

### 3. Monitor Progress

Watch the output panel for these success indicators:

```
=== Step 1: Update package list ===
Reading package lists... Done

=== Step 2: Install system dependencies for Chromium ===
Setting up libnss3... Done
...

=== Step 3: Clone or update BrowserAgent repository ===
Repository cloned successfully

=== Step 4: Install Python dependencies ===
Successfully installed playwright-1.47.0 typer-0.12.0 rich-13.0.0

=== Step 5: Install Playwright Chromium browser ===
Downloading Chromium 129.0.6668.29... (300 MB)
Chromium 129.0.6668.29 downloaded to ~/.cache/ms-playwright

=== Step 6: Verify installation ===
✓ BrowserAgent import successful

=== Step 7: Check Playwright version ===
Version 1.47.0

=== Step 8: Verify Chromium executable ===
-rwxr-xr-x 1 root root 352M chrome

=== Step 9: Run unit tests ===
============================= 235 passed in 0.59s ==============================

✅ BrowserAgent installation completed successfully
```

### 4. Verify Installation (Optional)

If you want to manually verify, SSH into your instance:

```bash
ssh -p <PORT> <USER>@<HOST>

# Test import
PYTHONPATH=/root/BrowserAgent/src:$PYTHONPATH python3 -c "from browser_agent.agent.core import Agent; print('OK')"

# Should output: ✓ BrowserAgent import successful
# Should output: OK
```

## What Gets Installed

### System Dependencies (17 packages)
- libnss3, libnspr4 - Mozilla Network Security Services
- libatk1.0-0, libatk-bridge2.0-0 - Accessibility toolkit
- libcups2 - Printing support
- libdrm2 - Direct Rendering Manager
- libdbus-1-3 - Message bus system
- libxkbcommon0 - Keyboard handling
- libxcomposite1, libxdamage1, libxfixes3, libxrandr2 - X11 extensions
- libgbm1 - Generic Buffer Management
- libpango-1.0-0 - Text rendering
- libcairo2 - 2D graphics
- libasound2 - Sound library

### Python Packages
- **playwright >= 1.47.0** - Browser automation framework
- **typer >= 0.12.0** - CLI framework
- **rich >= 13.0.0** - Terminal formatting

### Browser
- **Chromium** - Headless browser for automation
  - Location: `~/.cache/ms-playwright/chromium-*/`
  - Size: ~300 MB
  - Version: Latest stable

### Repository
- **Location:** `/root/BrowserAgent`
- **Branch:** main
- **Repository:** https://github.com/unearth4334/BrowserAgent

## Troubleshooting

### Installation Times Out

**Problem:** Installation exceeds 10-minute timeout

**Solution:**
1. Check internet connection speed on instance
2. Retry installation - if packages are already downloaded, it will be faster
3. Manually SSH in and run installation commands step by step

### Missing System Dependencies

**Problem:** `apt-get install` fails for some packages

**Solution:**
```bash
# Try fixing broken dependencies
apt-get install --fix-missing

# Update package database
apt-get update

# Retry installation
```

### Playwright Installation Fails

**Problem:** `playwright install chromium` fails

**Solution:**
```bash
# Install manually with verbose output
python3 -m playwright install chromium --verbose

# Check available disk space
df -h

# Chromium requires ~500MB free space
```

### Import Fails

**Problem:** `from browser_agent.agent.core import Agent` fails

**Solution:**
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=/root/BrowserAgent/src:$PYTHONPATH

# Verify repository was cloned
ls -la /root/BrowserAgent/src/

# Reinstall package
cd /root/BrowserAgent
pip install --upgrade --force-reinstall .
```

### Unit Tests Fail

**Problem:** Some unit tests fail

**Solution:**
- Unit test failures are warnings, not blockers
- Installation may still be functional
- Check specific test failures in output
- Report issues to BrowserAgent repository

## Testing the Installation

### Quick Test

```bash
# Test basic import
PYTHONPATH=/root/BrowserAgent/src:$PYTHONPATH python3 -c "from browser_agent.agent.core import Agent; print('✓ Import successful')"
```

### Full Test

```bash
cd /root/BrowserAgent
PYTHONPATH=/root/BrowserAgent/src:$PYTHONPATH python3 -m pytest tests/ --ignore=tests/integration/ -v
```

Expected output: `235 passed in ~0.6s`

### Browser Server Test

```bash
# Start server
cd /root/BrowserAgent
PYTHONPATH=/root/BrowserAgent/src:$PYTHONPATH python3 -m browser_agent.server.browser_server \
    --port 8765 \
    --headless \
    --initial-url "http://localhost:18188" &

# Wait for startup
sleep 3

# Test ping
PYTHONPATH=/root/BrowserAgent/src:$PYTHONPATH python3 -m browser_agent.server.browser_client \
    --host localhost \
    --port 8765 \
    ping

# Expected: {"status": "success", "message": "pong"}

# Stop server
pkill -f browser_server
```

## Next Steps

After successful installation:

1. **Implement Browser Executor** - Create `app/sync/browser_workflow_executor.py`
2. **Update Create Tab** - Modify workflow submission to use browser instead of API
3. **Test Workflow Execution** - Run IMG_to_VIDEO workflow via browser
4. **Remove Old Code** - Clean up API-based workflow execution code

## Resources

- **BrowserAgent Docs:** https://github.com/unearth4334/BrowserAgent
- **Playwright Docs:** https://playwright.dev/python/
- **Implementation Guide:** `/docs/BROWSER_AGENT_INTEGRATION.md`
- **Setup Template:** `/app/webui/templates/templates_comfyui.yml`

## Support

If you encounter issues:

1. Check the installation output in the VastAI Setup tab
2. Review error messages in enhanced logger
3. Test manually via SSH
4. Check BrowserAgent repository issues
5. Review deployment guide in this codebase
