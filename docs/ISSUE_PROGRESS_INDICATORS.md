# Progress Indicators Design for Instance Setup Workflow

**Date:** November 16, 2025  
**Test Instance:** `ssh -p 43274 root@72.19.60.156 -L 8080:localhost:8080`

## Overview

This document provides detailed design specifications for progress and completion indicators for each step in the VastAI instance setup workflow. Each indicator should appear within the workflow-step tile, positioned below the step-button and step-toggle elements.

---

## Step 1: Test SSH Connection (`test_ssh`)

### **Interaction Analysis**

**API Endpoint:** `POST /ssh/test`

**Request Payload:**
```json
{
  "ssh_connection": "ssh -p 43274 root@72.19.60.156 -L 8080:localhost:8080"
}
```

**Backend Operation:**
- Parses SSH connection string to extract host and port
- Executes SSH command: `ssh -p {port} -i /root/.ssh/id_ed25519 -o ConnectTimeout=10 root@{host} 'echo "SSH connection successful"'`
- Typical duration: 1-3 seconds (network dependent)
- Timeout: 15 seconds

**Test Results:**
```bash
$ ssh -p 43274 root@72.19.60.156 "echo 'SSH connection successful' && hostname && uptime"
# Output:
# SSH connection successful
# 6ecc5da8c823
# 08:46:51 up 6 days,  6:13,  0 users,  load average: 0.06, 0.32, 0.30
```

### **Progress Indicator Design**

**Visual Elements:**
```html
<div class="step-progress-indicator">
  <div class="progress-spinner"></div>
  <div class="progress-message">
    <span class="status-text">Testing SSH connection...</span>
    <span class="progress-detail">Connecting to 72.19.60.156:43274</span>
  </div>
  <div class="progress-timer">2s</div>
</div>
```

**Progress States:**
1. **Connecting** (0-1s): Spinner + "Establishing connection..."
2. **Authenticating** (1-2s): Spinner + "Authenticating SSH key..."
3. **Testing** (2-3s): Spinner + "Verifying remote access..."

**Styling Requirements:**
- Spinner: Small animated circle (16px), positioned left
- Message: Two-line layout - bold status + gray detail
- Timer: Right-aligned, shows elapsed time in real-time
- Background: Subtle highlight (`rgba(124, 58, 237, 0.05)`)
- Height: 48px, padding: 12px

### **Completion Indicator Design**

**Success State:**
```html
<div class="step-completion-indicator success">
  <div class="completion-icon">✅</div>
  <div class="completion-message">
    <span class="completion-text">SSH connection verified</span>
    <span class="completion-details">Host: 6ecc5da8c823 • Uptime: 6 days</span>
  </div>
  <div class="completion-time">2.3s</div>
</div>
```

**Failure State:**
```html
<div class="step-completion-indicator error">
  <div class="completion-icon">❌</div>
  <div class="completion-message">
    <span class="completion-text">SSH connection failed</span>
    <span class="completion-details">Connection timeout or refused</span>
  </div>
  <div class="completion-action">
    <button class="retry-btn" onclick="testVastAISSH()">🔄 Retry</button>
  </div>
</div>
```

**Persistence:**
- Success: Remains visible with green highlight
- Failure: Remains visible with red highlight + retry button
- Auto-dismiss: Never (user must explicitly retry or continue)

---

## Step 2: Setup CivitDL (`setup_civitdl`)

### **Interaction Analysis**

**API Endpoint:** `POST /ssh/setup-civitdl` (to be implemented)

**Backend Operations:**
1. **Install Package:** `/venv/main/bin/python -m pip install --root-user-action=ignore civitdl`
   - Duration: 5-15 seconds (network + package size dependent)
   - Downloads ~2-3 MB of packages
   
2. **Configure API Key:** `echo {api_key} | /venv/main/bin/civitconfig default --api-key`
   - Duration: <1 second
   
3. **Verify Installation:** `/venv/main/bin/python -c "import civitdl; print(civitdl.__version__)"`
   - Duration: <1 second

**Test Results:**
```bash
$ ssh -p 43274 root@72.19.60.156 "/venv/main/bin/python -m pip list | grep -i civit"
# (Not currently installed - returns empty)

$ ssh -p 43274 root@72.19.60.156 "df -h /workspace | tail -1"
# overlay 200G 6.9G 194G 4% /
# (Plenty of space available)
```

**Total Estimated Duration:** 6-17 seconds

### **Progress Indicator Design**

**Visual Elements:**
```html
<div class="step-progress-indicator multi-phase">
  <div class="progress-phases">
    <div class="phase active">
      <div class="phase-spinner"></div>
      <span class="phase-label">Installing civitdl package...</span>
      <span class="phase-status">Downloading 2.3 MB</span>
    </div>
    <div class="phase pending">
      <div class="phase-dot"></div>
      <span class="phase-label">Configuring API key</span>
    </div>
    <div class="phase pending">
      <div class="phase-dot"></div>
      <span class="phase-label">Verifying installation</span>
    </div>
  </div>
  <div class="progress-bar-container">
    <div class="progress-bar" style="width: 33%"></div>
  </div>
  <div class="progress-timer">8s</div>
</div>
```

**Progress Phases:**
1. **Phase 1** (0-12s): "Installing civitdl package..." 
   - Show download progress if available from pip output
   - Progress bar: 0% → 70%
   
2. **Phase 2** (12-13s): "Configuring API key..."
   - Check mark on Phase 1
   - Progress bar: 70% → 90%
   
3. **Phase 3** (13-14s): "Verifying installation..."
   - Check mark on Phase 2
   - Progress bar: 90% → 100%

**Styling Requirements:**
- Multi-line layout for 3 phases
- Active phase: Spinner + bold text
- Completed phase: Green checkmark + gray text
- Pending phase: Gray dot + muted text
- Progress bar: Full width, smooth transitions
- Height: Auto (expands for 3 phases), max 120px

### **Completion Indicator Design**

**Success State:**
```html
<div class="step-completion-indicator success">
  <div class="completion-icon">✅</div>
  <div class="completion-message">
    <span class="completion-text">CivitDL installed successfully</span>
    <span class="completion-details">
      Version 2.1.2 • API key configured • Ready for downloads
    </span>
  </div>
  <div class="completion-stats">
    <span class="stat">📦 3 packages</span>
    <span class="stat">⏱️ 12.4s</span>
  </div>
</div>
```

**Failure States:**

**Network Error:**
```html
<div class="step-completion-indicator error">
  <div class="completion-icon">❌</div>
  <div class="completion-message">
    <span class="completion-text">Installation failed</span>
    <span class="completion-details">
      Failed at: Installing civitdl package • Network timeout
    </span>
  </div>
  <div class="completion-action">
    <button class="retry-btn">🔄 Retry Installation</button>
    <button class="details-btn">📋 View Logs</button>
  </div>
</div>
```

**API Key Error:**
```html
<div class="step-completion-indicator warning">
  <div class="completion-icon">⚠️</div>
  <div class="completion-message">
    <span class="completion-text">Installation complete, API key failed</span>
    <span class="completion-details">
      CivitDL v2.1.2 installed • API key configuration error
    </span>
  </div>
  <div class="completion-action">
    <button class="fix-btn">🔑 Configure API Key</button>
  </div>
</div>
```

**Persistence:**
- Success: Remains visible with green highlight, shows version info
- Failure: Remains visible with red highlight + retry/view logs buttons
- Warning: Remains visible with yellow highlight + fix button

---

## Step 3: Test CivitDL (`test_civitdl`)

### **Interaction Analysis**

**API Endpoint:** `POST /ssh/test-civitdl` (to be implemented)

**Backend Operations:**
1. **Test CLI:** `/venv/main/bin/civitdl --help`
   - Duration: <1 second
   
2. **Check Config:** `/venv/main/bin/civitconfig settings`
   - Duration: <1 second
   - Validates API key is set
   
3. **Test API Connection:** `python -c "import requests; r = requests.get('https://civitai.com/api/v1/models', timeout=10); print(r.status_code)"`
   - Duration: 1-3 seconds (network dependent)
   - Expected: Status code 200

**Total Estimated Duration:** 2-5 seconds

### **Progress Indicator Design**

**Visual Elements:**
```html
<div class="step-progress-indicator">
  <div class="progress-checklist">
    <div class="check-item active">
      <div class="check-spinner"></div>
      <span>Testing CivitDL CLI...</span>
    </div>
    <div class="check-item pending">
      <div class="check-dot"></div>
      <span>Validating API configuration...</span>
    </div>
    <div class="check-item pending">
      <div class="check-dot"></div>
      <span>Testing API connectivity...</span>
    </div>
  </div>
  <div class="progress-timer">2s</div>
</div>
```

**Progress Sequence:**
1. **CLI Test** (0-1s): Spinner on first item
2. **Config Check** (1-2s): Checkmark on first, spinner on second
3. **API Test** (2-5s): Checkmark on second, spinner on third

### **Completion Indicator Design**

**Success State:**
```html
<div class="step-completion-indicator success">
  <div class="completion-icon">✅</div>
  <div class="completion-message">
    <span class="completion-text">CivitDL tests passed</span>
    <span class="completion-details">
      ✓ CLI functional • ✓ API key valid • ✓ API reachable
    </span>
  </div>
  <div class="completion-stats">
    <span class="stat">🌐 API Status: 200</span>
    <span class="stat">⏱️ 3.2s</span>
  </div>
</div>
```

**Failure State:**
```html
<div class="step-completion-indicator error">
  <div class="completion-icon">❌</div>
  <div class="completion-message">
    <span class="completion-text">CivitDL test failed</span>
    <span class="completion-details">
      ✓ CLI functional • ✗ API key invalid • API test skipped
    </span>
  </div>
  <div class="completion-action">
    <button class="fix-btn">🔑 Reconfigure API Key</button>
    <button class="retry-btn">🔄 Retry Tests</button>
  </div>
</div>
```

---

## Step 4: Set UI_HOME (`set_ui_home`)

### **Interaction Analysis**

**API Endpoint:** `POST /ssh/set-ui-home`

**Backend Operation:**
- Executes: `echo "UI_HOME=/workspace/ComfyUI" | sudo tee -a /etc/environment && source /etc/environment`
- Duration: <1 second
- Modifies system environment file

**Test Results:**
```bash
$ ssh -p 43274 root@72.19.60.156 "source /etc/environment; echo \"UI_HOME: \${UI_HOME}\""
# UI_HOME: /workspace/ComfyUI
```

### **Progress Indicator Design**

**Visual Elements:**
```html
<div class="step-progress-indicator simple">
  <div class="progress-spinner"></div>
  <div class="progress-message">
    <span class="status-text">Setting UI_HOME environment variable...</span>
    <span class="progress-detail">Path: /workspace/ComfyUI</span>
  </div>
</div>
```

**Progress State:**
- Single phase: "Setting UI_HOME environment variable..."
- Very quick operation (<1s)

### **Completion Indicator Design**

**Success State:**
```html
<div class="step-completion-indicator success">
  <div class="completion-icon">✅</div>
  <div class="completion-message">
    <span class="completion-text">UI_HOME configured</span>
    <span class="completion-details">
      Environment variable set: UI_HOME=/workspace/ComfyUI
    </span>
  </div>
  <div class="completion-action">
    <button class="verify-btn" onclick="getUIHome()">👁️ Verify</button>
  </div>
</div>
```

**Failure State:**
```html
<div class="step-completion-indicator error">
  <div class="completion-icon">❌</div>
  <div class="completion-message">
    <span class="completion-text">Failed to set UI_HOME</span>
    <span class="completion-details">Permission denied or file system error</span>
  </div>
  <div class="completion-action">
    <button class="retry-btn">🔄 Retry</button>
  </div>
</div>
```

---

## Step 5: Read UI_HOME (`get_ui_home`)

### **Interaction Analysis**

**API Endpoint:** `POST /ssh/get-ui-home`

**Backend Operation:**
- Executes: `source /etc/environment 2>/dev/null || true; echo "${UI_HOME:-Not set}"`
- Duration: <1 second
- Read-only operation

**Test Results:**
```bash
$ ssh -p 43274 root@72.19.60.156 "source /etc/environment; echo \${UI_HOME}"
# /workspace/ComfyUI
```

### **Progress Indicator Design**

**Visual Elements:**
```html
<div class="step-progress-indicator simple">
  <div class="progress-spinner"></div>
  <div class="progress-message">
    <span class="status-text">Reading UI_HOME from environment...</span>
  </div>
</div>
```

### **Completion Indicator Design**

**Success State (Value Set):**
```html
<div class="step-completion-indicator success">
  <div class="completion-icon">✅</div>
  <div class="completion-message">
    <span class="completion-text">UI_HOME retrieved</span>
    <span class="completion-details">
      Current value: /workspace/ComfyUI
    </span>
  </div>
  <div class="completion-meta">
    <span class="info-badge">✓ Valid path</span>
  </div>
</div>
```

**Warning State (Not Set):**
```html
<div class="step-completion-indicator warning">
  <div class="completion-icon">⚠️</div>
  <div class="completion-message">
    <span class="completion-text">UI_HOME not configured</span>
    <span class="completion-details">Environment variable is not set</span>
  </div>
  <div class="completion-action">
    <button class="fix-btn" onclick="setUIHome()">📁 Set UI_HOME</button>
  </div>
</div>
```

---

## Step 6: Setup Python venv (`setup_python_venv`)

### **Interaction Analysis**

**API Endpoint:** `POST /ssh/setup-python-venv` (to be implemented)

**Backend Operations:**
1. Check if venv exists at `/workspace/ComfyUI/venv`
2. Create venv if needed: `python3 -m venv /workspace/ComfyUI/venv`
3. Upgrade pip: `/workspace/ComfyUI/venv/bin/pip install --upgrade pip`
4. Install requirements if available

**Test Results:**
```bash
$ ssh -p 43274 root@72.19.60.156 "ls -la /workspace/ComfyUI/venv 2>&1 | head -5"
# (Would show venv structure if exists, or error if not)

$ ssh -p 43274 root@72.19.60.156 "python3 --version"
# Python 3.10.12
```

**Estimated Duration:** 3-10 seconds (depending on if venv exists)

### **Progress Indicator Design**

**Visual Elements:**
```html
<div class="step-progress-indicator multi-phase">
  <div class="progress-phases">
    <div class="phase active">
      <div class="phase-spinner"></div>
      <span class="phase-label">Checking for existing venv...</span>
    </div>
    <div class="phase pending">
      <div class="phase-dot"></div>
      <span class="phase-label">Creating virtual environment</span>
    </div>
    <div class="phase pending">
      <div class="phase-dot"></div>
      <span class="phase-label">Upgrading pip</span>
    </div>
  </div>
  <div class="progress-bar-container">
    <div class="progress-bar" style="width: 20%"></div>
  </div>
  <div class="progress-timer">5s</div>
</div>
```

**Progress Phases:**
1. **Check** (0-1s): "Checking for existing venv..."
2. **Create** (1-8s): "Creating virtual environment..." (if needed)
3. **Upgrade** (8-10s): "Upgrading pip..."

**If venv exists:**
- Skip directly to completion with "Existing venv detected"

### **Completion Indicator Design**

**Success State (New venv):**
```html
<div class="step-completion-indicator success">
  <div class="completion-icon">✅</div>
  <div class="completion-message">
    <span class="completion-text">Python venv created</span>
    <span class="completion-details">
      Location: /workspace/ComfyUI/venv • Python 3.10.12 • pip 25.2
    </span>
  </div>
  <div class="completion-stats">
    <span class="stat">⏱️ 8.7s</span>
  </div>
</div>
```

**Success State (Existing venv):**
```html
<div class="step-completion-indicator success">
  <div class="completion-icon">✅</div>
  <div class="completion-message">
    <span class="completion-text">Python venv validated</span>
    <span class="completion-details">
      Existing venv found and verified • Python 3.10.12
    </span>
  </div>
  <div class="completion-stats">
    <span class="stat">♻️ Reused</span>
    <span class="stat">⏱️ 1.2s</span>
  </div>
</div>
```

---

## Step 7: Clone Auto Installer (`clone_auto_installer`)

### **Interaction Analysis**

**API Endpoint:** `POST /ssh/clone-repo` (to be implemented)

**Backend Operations:**
1. Check if repo already exists: `[ -d /workspace/ComfyUI-Auto_installer/.git ]`
2. Clone if needed: `git clone https://github.com/unearth4334/ComfyUI-Auto_installer /workspace/ComfyUI-Auto_installer`
3. Or update if exists: `cd /workspace/ComfyUI-Auto_installer && git pull`

**Test Results:**
```bash
$ ssh -p 43274 root@72.19.60.156 "which git && git --version"
# /usr/bin/git
# git version 2.34.1

$ ssh -p 43274 root@72.19.60.156 "ls -la /workspace/ | grep Auto"
# (Would show if directory exists)
```

**Estimated Duration:** 2-15 seconds (network + repo size dependent)

### **Progress Indicator Design**

**Visual Elements:**
```html
<div class="step-progress-indicator git-clone">
  <div class="progress-git">
    <div class="git-status">
      <div class="git-spinner"></div>
      <span class="git-action">Cloning repository...</span>
    </div>
    <div class="git-details">
      <span class="git-url">github.com/unearth4334/ComfyUI-Auto_installer</span>
      <span class="git-progress">Receiving objects: 45% (123/273)</span>
    </div>
  </div>
  <div class="progress-bar-container">
    <div class="progress-bar" style="width: 45%"></div>
  </div>
  <div class="progress-stats">
    <span class="data-received">2.3 MB</span>
    <span class="timer">8s</span>
  </div>
</div>
```

**Progress Phases:**
1. **Checking** (0-1s): "Checking for existing repository..."
2. **Cloning** (1-12s): "Cloning repository..." (if new)
   - Parse git output for progress: "Receiving objects: X% (Y/Z)"
   - Show data received if available
3. **Updating** (1-5s): "Updating existing repository..." (if exists)

### **Completion Indicator Design**

**Success State (New Clone):**
```html
<div class="step-completion-indicator success">
  <div class="completion-icon">✅</div>
  <div class="completion-message">
    <span class="completion-text">Repository cloned successfully</span>
    <span class="completion-details">
      ComfyUI-Auto_installer • 273 files • 3.2 MB
    </span>
  </div>
  <div class="completion-stats">
    <span class="stat">📁 /workspace/ComfyUI-Auto_installer</span>
    <span class="stat">⏱️ 11.4s</span>
  </div>
</div>
```

**Success State (Updated):**
```html
<div class="step-completion-indicator success">
  <div class="completion-icon">✅</div>
  <div class="completion-message">
    <span class="completion-text">Repository updated</span>
    <span class="completion-details">
      Already up to date • HEAD: a3f2b1c
    </span>
  </div>
  <div class="completion-stats">
    <span class="stat">♻️ Pulled latest</span>
    <span class="stat">⏱️ 2.1s</span>
  </div>
</div>
```

**Failure State:**
```html
<div class="step-completion-indicator error">
  <div class="completion-icon">❌</div>
  <div class="completion-message">
    <span class="completion-text">Git clone failed</span>
    <span class="completion-details">
      Network error or repository not accessible
    </span>
  </div>
  <div class="completion-action">
    <button class="retry-btn">🔄 Retry Clone</button>
    <button class="details-btn">📋 View Error</button>
  </div>
</div>
```

---

## Step 8: Sync Instance (`sync_instance`)

### **Interaction Analysis**

**API Endpoint:** `POST /sync` (with ssh_connection parameter)

**Backend Operations:**
- Executes full sync operation from remote instance to local storage
- Syncs multiple directories: txt2img-images, img2img-images, etc.
- Uses rsync with progress tracking
- Optionally performs cleanup of old files

**Test Results:**
```bash
$ ssh -p 43274 root@72.19.60.156 "ls -la /workspace/ComfyUI/output"
# total 4
# drwxrwxr-x  2 root root   53 Nov 16 08:39 .
# drwxrwxr-x 26 root root 4096 Nov 16 08:41 ..
# -rw-rw-r--  1 root root    0 Nov 16 08:39 _output_images_will_be_put_here
```

**Estimated Duration:** 10 seconds to several minutes (depends on file count/size)

### **Progress Indicator Design**

**Visual Elements:**
```html
<div class="step-progress-indicator sync">
  <div class="sync-overview">
    <div class="sync-spinner"></div>
    <div class="sync-status">
      <span class="sync-stage">Discovering folders...</span>
      <span class="sync-detail">Found 6 output directories</span>
    </div>
  </div>
  <div class="sync-folders">
    <div class="folder-progress completed">
      <span class="folder-icon">✓</span>
      <span class="folder-name">txt2img-images</span>
      <span class="folder-stats">45 files • 125 MB</span>
    </div>
    <div class="folder-progress active">
      <div class="folder-spinner"></div>
      <span class="folder-name">img2img-images</span>
      <span class="folder-stats">12/28 files...</span>
    </div>
    <div class="folder-progress pending">
      <span class="folder-icon">○</span>
      <span class="folder-name">extras-images</span>
      <span class="folder-stats">Waiting...</span>
    </div>
  </div>
  <div class="sync-progress-bar">
    <div class="progress-fill" style="width: 42%"></div>
    <span class="progress-text">42% • 57/135 files • 234 MB</span>
  </div>
  <div class="sync-stats">
    <span class="speed">↓ 15.2 MB/s</span>
    <span class="eta">~12s remaining</span>
    <span class="timer">18s</span>
  </div>
</div>
```

**Progress Stages:**
1. **Discovery** (0-5s): "Discovering folders..."
2. **Per-Folder Sync** (5s-?): Show list of folders with individual progress
3. **Cleanup** (optional): "Cleaning up old files..." (if enabled)

**Real-time Updates:**
- Folder completion checkmarks
- File count progress per folder
- Overall progress bar
- Transfer speed
- ETA calculation
- Elapsed time

### **Completion Indicator Design**

**Success State:**
```html
<div class="step-completion-indicator success sync-complete">
  <div class="completion-icon">✅</div>
  <div class="completion-message">
    <span class="completion-text">Sync completed successfully</span>
    <span class="completion-details">
      6 folders synced • 135 files transferred • 487 MB
    </span>
  </div>
  <div class="completion-breakdown">
    <div class="sync-summary">
      <div class="summary-item">
        <span class="item-label">txt2img-images:</span>
        <span class="item-value">45 files</span>
      </div>
      <div class="summary-item">
        <span class="item-label">img2img-images:</span>
        <span class="item-value">28 files</span>
      </div>
      <div class="summary-item">
        <span class="item-label">extras-images:</span>
        <span class="item-value">12 files</span>
      </div>
      <div class="summary-more">+ 3 more folders</div>
    </div>
  </div>
  <div class="completion-stats">
    <span class="stat">📊 Avg speed: 18.3 MB/s</span>
    <span class="stat">⏱️ 26.7s</span>
    <span class="stat">🧹 Cleanup: enabled</span>
  </div>
  <div class="completion-action">
    <button class="view-btn">📁 View Files</button>
  </div>
</div>
```

**Partial Success State:**
```html
<div class="step-completion-indicator warning">
  <div class="completion-icon">⚠️</div>
  <div class="completion-message">
    <span class="completion-text">Sync completed with warnings</span>
    <span class="completion-details">
      5/6 folders synced • 2 folders had errors
    </span>
  </div>
  <div class="completion-breakdown">
    <div class="error-summary">
      <div class="error-item">
        <span class="error-icon">❌</span>
        <span>txt2img-grids: Permission denied</span>
      </div>
      <div class="error-item">
        <span class="error-icon">❌</span>
        <span>img2img-grids: Connection timeout</span>
      </div>
    </div>
  </div>
  <div class="completion-action">
    <button class="retry-btn">🔄 Retry Failed</button>
    <button class="details-btn">📋 View Logs</button>
  </div>
</div>
```

**Failure State:**
```html
<div class="step-completion-indicator error">
  <div class="completion-icon">❌</div>
  <div class="completion-message">
    <span class="completion-text">Sync failed</span>
    <span class="completion-details">
      Connection lost or insufficient permissions
    </span>
  </div>
  <div class="completion-action">
    <button class="retry-btn">🔄 Retry Sync</button>
    <button class="check-btn">🔧 Check Connection</button>
  </div>
</div>
```

---

## Common CSS Styling Framework

### **Base Classes**

```css
/* Progress Indicators */
.step-progress-indicator {
  margin-top: var(--size-4-2);
  padding: var(--size-4-3);
  background: rgba(124, 58, 237, 0.05);
  border-radius: var(--radius-s);
  border-left: 3px solid var(--interactive-accent);
  font-size: var(--font-ui-small);
}

.progress-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(124, 58, 237, 0.2);
  border-top-color: var(--interactive-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* Completion Indicators */
.step-completion-indicator {
  margin-top: var(--size-4-2);
  padding: var(--size-4-3);
  border-radius: var(--radius-s);
  border-left: 3px solid;
  font-size: var(--font-ui-small);
  display: flex;
  align-items: flex-start;
  gap: var(--size-4-2);
}

.step-completion-indicator.success {
  background: rgba(46, 160, 67, 0.1);
  border-left-color: var(--text-success);
}

.step-completion-indicator.error {
  background: rgba(220, 38, 38, 0.1);
  border-left-color: var(--text-error);
}

.step-completion-indicator.warning {
  background: rgba(245, 158, 11, 0.1);
  border-left-color: #f59e0b;
}

/* Animations */
@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

### **Interactive Elements**

```css
.retry-btn, .fix-btn, .verify-btn, .view-btn {
  padding: var(--size-4-1) var(--size-4-3);
  border-radius: var(--radius-s);
  font-size: var(--font-ui-smaller);
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.retry-btn {
  background: var(--interactive-accent);
  color: var(--text-on-accent);
}

.fix-btn {
  background: #f59e0b;
  color: white;
}

.details-btn {
  background: var(--interactive-normal);
  color: var(--text-normal);
}
```

---

## Implementation Notes

### **Real-time Updates**

All progress indicators should support real-time updates via:
1. **WebSocket connection** (preferred for long-running operations)
2. **Polling** (fallback, every 1-2 seconds during active operations)
3. **Server-Sent Events** (alternative to WebSocket)

### **Error Handling**

Each step should handle:
- Network timeouts
- SSH connection failures
- Permission errors
- Disk space issues
- Missing dependencies

### **Accessibility**

- Use ARIA live regions for screen readers
- Provide text alternatives for emoji/icons
- Ensure sufficient color contrast
- Support keyboard navigation for action buttons

### **Performance**

- Minimize DOM updates during progress
- Use CSS transforms for animations
- Debounce rapid progress updates
- Clean up indicators when step completes

---

## Testing Checklist

- [ ] Test each progress indicator with the provided instance
- [ ] Verify timing accuracy of progress estimates
- [ ] Test failure scenarios for each step
- [ ] Verify persistence of completion indicators
- [ ] Test retry/action buttons functionality
- [ ] Validate responsive design on mobile
- [ ] Check accessibility with screen readers
- [ ] Verify animation performance
- [ ] Test concurrent step execution
- [ ] Validate cleanup of old indicators

---

**End of Document**
