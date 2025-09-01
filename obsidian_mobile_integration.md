# Obsidian Mobile-Optimized Integration

This file contains mobile-optimized code for integrating the Media Sync Tool with Obsidian on mobile devices, providing more reliable progress tracking.

## Mobile-Optimized Button Interface

This version includes adaptive polling, better error handling, and fallback mechanisms for mobile networks.

```dataviewjs
// =============================
// Media Sync — Mobile-Optimized Version
// =============================
const API_BASE = "http://10.0.78.66:5000"; // NAS API base

// Mobile detection
const isMobile = () => {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
         window.innerWidth <= 768;
};

// Adaptive configuration for mobile vs desktop
const config = {
  mobile: {
    syncTimeout: 45000,      // 45 seconds for sync requests
    progressTimeout: 15000,  // 15 seconds for progress requests
    pollInterval: 3000,      // 3 seconds between polls
    maxPolls: 40,           // Maximum 40 polls (2 minutes total)
    retryDelay: 2000,       // 2 seconds initial retry delay
    maxRetries: 3           // Maximum retries for failed requests
  },
  desktop: {
    syncTimeout: 30000,      // 30 seconds for sync requests
    progressTimeout: 10000,  // 10 seconds for progress requests
    pollInterval: 2000,      // 2 seconds between polls
    maxPolls: 60,           // Maximum 60 polls (2 minutes total)
    retryDelay: 1000,       // 1 second initial retry delay
    maxRetries: 5           // Maximum retries for failed requests
  }
};

const settings = isMobile() ? config.mobile : config.desktop;

// Container
const container = dv.el("div", "", {
  style: "margin:20px 0;padding:15px;border-radius:8px;background-color:#f5f5f5;"
});

// Title with mobile indicator
const titleText = isMobile() ? "🔄 Media Sync Tool (Mobile Mode)" : "🔄 Media Sync Tool";
dv.el("h3", titleText, { 
  container,
  style: "margin-top:0;color:#333;"
});

// Operations
const syncOperations = [
  { name: "🔥 Sync Forge", endpoint: "/sync/forge",  description: "Sync from Stable Diffusion WebUI Forge (10.0.78.108:2222)" },
  { name: "🖼️ Sync Comfy", endpoint: "/sync/comfy",  description: "Sync from ComfyUI (10.0.78.108:2223)" },
  { name: "☁️ Sync VastAI", endpoint: "/sync/vastai", description: "Auto-discover VastAI instance and sync" },
];

// Utility: fetch with timeout and retries
async function robustFetch(url, options = {}, retries = settings.maxRetries) {
  const controller = new AbortController();
  const timeout = options.timeout || settings.syncTimeout;
  
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    
    if (retries > 0 && (error.name === 'AbortError' || error.name === 'TypeError')) {
      console.log(`Retrying request to ${url}, ${retries} attempts remaining`);
      await new Promise(resolve => setTimeout(resolve, settings.retryDelay));
      return robustFetch(url, options, retries - 1);
    }
    
    throw error;
  }
}

// Progress tracking with mobile-optimized polling
class MobileProgressTracker {
  constructor() {
    this.isTracking = false;
    this.currentSyncId = null;
    this.pollCount = 0;
    this.progressElement = null;
    this.statusElement = null;
  }
  
  start(syncId, progressElement, statusElement) {
    this.currentSyncId = syncId;
    this.progressElement = progressElement;
    this.statusElement = statusElement;
    this.isTracking = true;
    this.pollCount = 0;
    
    this.poll();
  }
  
  stop() {
    this.isTracking = false;
    this.currentSyncId = null;
    this.pollCount = 0;
  }
  
  async poll() {
    if (!this.isTracking || this.pollCount >= settings.maxPolls) {
      this.handleComplete("Polling stopped or timed out");
      return;
    }
    
    try {
      this.pollCount++;
      
      // Use mobile-optimized endpoint if available
      const endpoint = isMobile() ? 
        `/sync/mobile/progress/${this.currentSyncId}` : 
        `/sync/progress/${this.currentSyncId}`;
      
      const response = await robustFetch(API_BASE + endpoint, {
        timeout: settings.progressTimeout
      }, 2); // Fewer retries for progress requests
      
      const data = await response.json();
      
      if (data.success && data.progress) {
        this.updateProgress(data.progress);
        
        // Check if completed
        if (data.progress.status === 'completed' || data.progress.progress_percent >= 100) {
          this.handleComplete("Sync completed successfully!");
          return;
        }
        
        // Continue polling
        setTimeout(() => this.poll(), settings.pollInterval);
      } else {
        this.handleError("Progress not available");
      }
    } catch (error) {
      console.warn("Progress polling error:", error.message);
      
      // On mobile, be more tolerant of network errors
      if (isMobile() && this.pollCount < settings.maxPolls) {
        this.updateStatus("Network issue, retrying...");
        setTimeout(() => this.poll(), settings.pollInterval * 2); // Double interval on error
      } else {
        this.handleError(`Network error: ${error.message}`);
      }
    }
  }
  
  updateProgress(progress) {
    if (!this.progressElement || !this.statusElement) return;
    
    const percent = progress.progress_percent || 0;
    const stage = progress.current_stage || "working";
    const message = progress.latest_message || progress.current_folder || "";
    
    this.progressElement.textContent = `${stage}: ${Math.round(percent)}%`;
    this.statusElement.textContent = message;
  }
  
  updateStatus(message) {
    if (this.statusElement) {
      this.statusElement.textContent = message;
    }
  }
  
  handleComplete(message) {
    this.stop();
    if (this.progressElement) {
      this.progressElement.textContent = message;
    }
    
    // Auto-hide progress after completion
    setTimeout(() => {
      if (this.progressElement) this.progressElement.textContent = "";
      if (this.statusElement) this.statusElement.textContent = "";
    }, 3000);
  }
  
  handleError(message) {
    this.stop();
    if (this.statusElement) {
      this.statusElement.textContent = `Progress error: ${message}`;
    }
    
    // Clear error message after delay
    setTimeout(() => {
      if (this.statusElement) this.statusElement.textContent = "";
    }, 5000);
  }
}

// Create buttons for each operation
syncOperations.forEach(operation => {
  const row = dv.el("div", "", { container, style: "margin:10px 0;" });
  const button = dv.el("button", operation.name, {
    container: row,
    style: `
      background:#007cba;color:white;border:none;padding:10px 20px;border-radius:5px;
      cursor:pointer;margin-right:10px;font-size:14px;
    `
  });
  
  const status = dv.el("span", "", {
    container: row,
    style: "margin-left:10px;font-style:italic;color:#666;"
  });
  
  const progressInfo = dv.el("div", "", {
    container: row,
    style: "margin-left:10px;font-size:12px;color:#888;margin-top:5px;"
  });
  
  dv.el("br", "", { container: row });
  dv.el("small", operation.description, { 
    container: row, 
    style: "color:#888;margin-left:5px;" 
  });

  // Progress tracker for this operation
  const tracker = new MobileProgressTracker();

  button.addEventListener("click", async () => {
    const originalText = button.textContent;
    button.textContent = "Syncing...";
    button.style.background = "#ffa500";
    status.textContent = "Starting sync operation...";
    progressInfo.textContent = "";

    try {
      // Stop any existing tracking
      tracker.stop();
      
      const response = await robustFetch(API_BASE + operation.endpoint, { 
        method: "POST",
        timeout: settings.syncTimeout
      });
      
      const data = await response.json();

      if (data.success) {
        button.style.background = "#28a745";
        button.textContent = "✅ Running";
        status.textContent = data.message || "Sync started";
        
        if (data.instance_info?.id) {
          status.textContent += ` (Instance: ${data.instance_info.id})`;
        }
        
        // Start progress tracking if sync_id is available
        if (data.sync_id) {
          progressInfo.textContent = "Tracking progress...";
          tracker.start(data.sync_id, progressInfo, status);
        }
        
      } else {
        button.style.background = "#dc3545";
        button.textContent = "❌ Failed";
        status.textContent = data.message || "Sync failed";
      }
    } catch (error) {
      button.style.background = "#dc3545";
      
      if (error.name === 'AbortError') {
        button.textContent = "⏱️ Timeout";
        status.textContent = "Request timed out - sync may still be running";
      } else {
        button.textContent = "❌ Error";
        status.textContent = `Request failed: ${error.message}`;
      }
    }

    // Reset button after delay
    setTimeout(() => {
      button.textContent = originalText;
      button.style.background = "#007cba";
      if (!tracker.isTracking) {
        status.textContent = "";
        progressInfo.textContent = "";
      }
    }, 5000);
  });
});

// Status check with mobile optimizations
const statusContainer = dv.el("div", "", {
  container,
  style: "margin-top:20px;padding-top:15px;border-top:1px solid #ddd;"
});

const statusButton = dv.el("button", "🔍 Check Status", {
  container: statusContainer,
  style: `
    background:#6c757d;color:white;border:none;padding:8px 16px;border-radius:5px;
    cursor:pointer;font-size:12px;
  `
});

const statusText = dv.el("div", "", {
  container: statusContainer,
  style: "margin-top:10px;font-size:12px;color:#666;"
});

statusButton.addEventListener("click", async () => {
  statusText.textContent = "Checking status...";
  
  try {
    const response = await robustFetch(API_BASE + "/status", {
      timeout: 15000 // 15 second timeout for status check
    }, 2);
    
    const data = await response.json();
    let html = "<strong>Status:</strong><br>";
    html += `Forge: ${data.forge?.available ? '✅' : '❌'}<br>`;
    html += `ComfyUI: ${data.comfy?.available ? '✅' : '❌'}<br>`;
    html += `VastAI: ${data.vastai?.available ? '✅' : '❌'}`;
    if (data.vastai?.error) html += ` (${data.vastai.error})`;
    
    statusText.innerHTML = html;
  } catch (error) {
    if (error.name === 'AbortError') {
      statusText.textContent = "Status check timed out - network may be slow";
    } else {
      statusText.textContent = `Status check failed: ${error.message}`;
    }
  }
});

// Add mobile-specific help text
if (isMobile()) {
  const helpText = dv.el("div", "", {
    container,
    style: "margin-top:15px;padding:10px;background:#e3f2fd;border-radius:5px;font-size:11px;color:#1565c0;"
  });
  helpText.innerHTML = `
    <strong>📱 Mobile Mode Active:</strong><br>
    • Extended timeouts for slow networks<br>
    • Reduced polling frequency to save battery<br>
    • Automatic retry on network errors<br>
    • Simplified progress updates
  `;
}
```

## Alternative: Simplified Mobile Interface

For very unreliable mobile networks, use this simplified version that doesn't rely on real-time progress:

```dataviewjs
// =============================
// Media Sync — Simple Mobile Version (No Progress Tracking)
// =============================
const API_BASE = "http://10.0.78.66:5000";

const container = dv.el("div", "", {
  style: "margin:20px 0;padding:15px;border-radius:8px;background-color:#f5f5f5;"
});

dv.el("h3", "🔄 Media Sync Tool (Simple)", { 
  container,
  style: "margin-top:0;color:#333;"
});

const syncOperations = [
  { name: "🔥 Sync Forge", endpoint: "/sync/forge" },
  { name: "🖼️ Sync Comfy", endpoint: "/sync/comfy" },
  { name: "☁️ Sync VastAI", endpoint: "/sync/vastai" },
];

syncOperations.forEach(operation => {
  const row = dv.el("div", "", { container, style: "margin:10px 0;" });
  const button = dv.el("button", operation.name, {
    container: row,
    style: `
      background:#007cba;color:white;border:none;padding:12px 24px;border-radius:5px;
      cursor:pointer;margin-right:10px;font-size:14px;width:200px;
    `
  });

  button.addEventListener("click", async () => {
    button.textContent = "Starting...";
    button.style.background = "#ffa500";
    button.disabled = true;

    try {
      const controller = new AbortController();
      setTimeout(() => controller.abort(), 30000); // 30 second timeout
      
      const response = await fetch(API_BASE + operation.endpoint, { 
        method: "POST",
        signal: controller.signal
      });
      
      const data = await response.json();

      if (data.success) {
        button.style.background = "#28a745";
        button.textContent = "✅ Started";
      } else {
        button.style.background = "#dc3545";
        button.textContent = "❌ Failed";
      }
    } catch (error) {
      button.style.background = "#dc3545";
      button.textContent = error.name === 'AbortError' ? "⏱️ Timeout" : "❌ Error";
    }

    button.disabled = false;
    setTimeout(() => {
      button.textContent = operation.name;
      button.style.background = "#007cba";
    }, 4000);
  });
});

// Simple status display
const statusDiv = dv.el("div", "", {
  container,
  style: "margin-top:15px;padding:10px;background:#fff3cd;border-radius:5px;font-size:12px;"
});
statusDiv.innerHTML = `
  <strong>📱 Simple Mode:</strong> Sync operations run in the background. 
  Check your media folders after a few minutes to see synced content.
`;
```