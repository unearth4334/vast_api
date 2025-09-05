
```dataviewjs
// Configure your API server address
const API_BASE = "http://10.0.78.66:5000"; // Replace with your QNAP NAS IP

// Create container for buttons
const container = dv.el("div", "", {
    style: "margin: 20px 0; padding: 15px; border-radius: 8px; background-color: #f5f5f5;"
});

// Add title
dv.el("h3", "🔄 Media Sync Tool", { 
    container: container,
    style: "margin-top: 0; color: #333;"
});

// Define sync operations
const syncOperations = [
    { 
        name: "🔥 Sync Forge", 
        endpoint: "/sync/forge",
        description: "Sync from Stable Diffusion WebUI Forge (10.0.78.108:2222)"
    },
    { 
        name: "🖼️ Sync Comfy", 
        endpoint: "/sync/comfy",
        description: "Sync from ComfyUI (10.0.78.108:2223)"
    },
    { 
        name: "☁️ Sync VastAI", 
        endpoint: "/sync/vastai",
        description: "Auto-discover VastAI instance and sync"
    }
];

// Create buttons
syncOperations.forEach(operation => {
    const buttonContainer = dv.el("div", "", {
        container: container,
        style: "margin: 10px 0;"
    });
    
    const button = dv.el("button", operation.name, {
        container: buttonContainer,
        style: `
            background: #007cba; 
            color: white; 
            border: none; 
            padding: 10px 20px; 
            border-radius: 5px; 
            cursor: pointer; 
            margin-right: 10px;
            font-size: 14px;
        `
    });
    
    const status = dv.el("span", "", {
        container: buttonContainer,
        style: "margin-left: 10px; font-style: italic; color: #666;"
    });
    
    dv.el("br", "", { container: buttonContainer });
    dv.el("small", operation.description, {
        container: buttonContainer,
        style: "color: #888; margin-left: 5px;"
    });
    
    // Add click handler
    button.addEventListener("click", async () => {
        const originalText = button.textContent;
        button.textContent = "Syncing...";
        button.style.background = "#ffa500";
        status.textContent = "Starting sync operation...";
        
        try {
            const response = await fetch(API_BASE + operation.endpoint, { 
                method: "POST",
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();
            
            if (data.success) {
                button.style.background = "#28a745";
                button.textContent = "✅ Success";
                status.textContent = data.message;
                if (data.instance_info) {
                    status.textContent += ` (Instance: ${data.instance_info.id})`;
                }
            } else {
                button.style.background = "#dc3545";
                button.textContent = "❌ Failed";
                status.textContent = data.message || "Sync failed";
            }
        } catch (error) {
            button.style.background = "#dc3545";
            button.textContent = "❌ Error";
            status.textContent = `Request failed: ${error.message}`;
        }
        
        // Reset button after 5 seconds
        setTimeout(() => {
            button.textContent = originalText;
            button.style.background = "#007cba";
            status.textContent = "";
        }, 5000);
    });
});

// Add status check
const statusContainer = dv.el("div", "", {
    container: container,
    style: "margin-top: 20px; padding-top: 15px; border-top: 1px solid #ddd;"
});

const statusButton = dv.el("button", "🔍 Check Status", {
    container: statusContainer,
    style: `
        background: #6c757d; 
        color: white; 
        border: none; 
        padding: 8px 16px; 
        border-radius: 5px; 
        cursor: pointer;
        font-size: 12px;
    `
});

const statusText = dv.el("div", "", {
    container: statusContainer,
    style: "margin-top: 10px; font-size: 12px; color: #666;"
});

statusButton.addEventListener("click", async () => {
    statusText.textContent = "Checking status...";
    
    try {
        const response = await fetch(API_BASE + "/status");
        const data = await response.json();
        
        let statusHTML = "<strong>Status:</strong><br>";
        statusHTML += `Forge: ${data.forge.available ? '✅' : '❌'}<br>`;
        statusHTML += `ComfyUI: ${data.comfy.available ? '✅' : '❌'}<br>`;
        statusHTML += `VastAI: ${data.vastai.available ? '✅' : '❌'}`;
        if (data.vastai.error) {
            statusHTML += ` (${data.vastai.error})`;
        }
        
        statusText.innerHTML = statusHTML;
    } catch (error) {
        statusText.textContent = `Status check failed: ${error.message}`;
    }
});
```
## Progress
---

```dataviewjs
// === Media Sync — Auto Attach + Loading Bar ===
// Adjust to your NAS API:
const API_BASE = "http://10.0.78.66:5000";

// --- UI shell ---
const wrap = dv.el("div","",{style:"padding:12px;border:1px solid var(--background-modifier-border);border-radius:10px"});
const title = dv.el("div","🔄 Media Sync — Auto Attach",{container:wrap,style:"font-weight:600;margin-bottom:8px"});
const meta  = dv.el("div","",{container:wrap,style:"font-size:12px;color:var(--text-muted);margin-bottom:8px"});

// Loading bar
const bar   = dv.el("div","",{container:wrap});
bar.classList.add("msync-bar");                  // styled by CSS snippet
const fill  = dv.el("div","",{container:bar});
fill.classList.add("msync-fill");                // styled by CSS snippet
fill.setAttribute("role","progressbar");
fill.setAttribute("aria-valuemin","0");
fill.setAttribute("aria-valuemax","100");

// Optional small status line (last message)
const status = dv.el("div","",{container:wrap,style:"margin-top:8px;font-size:12px;color:var(--text-normal)"});

// --- logic ---
let currentId = null;
let stopped = false;

async function getLatest() {
  const r = await fetch(`${API_BASE}/sync/latest`);
  const j = await r.json();
  if (!j.success) throw new Error(j.message || "no latest");
  return j; // { success, sync_id, progress }
}

async function getProgress(id){
  try{
    const r = await fetch(`${API_BASE}/sync/progress/${id}`);
    const j = await r.json();
    if (!j.success || !j.progress) return null;
    return j.progress;
  }catch(e){ return null; }
}

function setIndeterminate(on=true){
  if (on){
    fill.classList.add("is-indeterminate");
    fill.removeAttribute("aria-valuenow");
    fill.style.width = "0%";
  } else {
    fill.classList.remove("is-indeterminate");
  }
}

function setDeterminate(pct){
  setIndeterminate(false);
  const clamped = Math.max(0, Math.min(100, Number(pct)||0));
  fill.style.width = `${clamped}%`;
  fill.setAttribute("aria-valuenow", String(clamped));
}

function setState(statusText, pct, stage, lastMsg){
  title.textContent = `🔄 Media Sync — ${currentId ? `Tracking ${currentId.slice(0,8)}…` : "Idle"}`;

  // Choose determinate vs indeterminate
  if (Number.isFinite(pct)) {
    setDeterminate(pct);
  } else {
    setIndeterminate(true);
  }

  // Style by status
  fill.classList.remove("is-complete","is-error","is-running");
  if (statusText === "completed" || (Number.isFinite(pct) && pct >= 100)) {
    fill.classList.add("is-complete");
  } else if (statusText === "error") {
    fill.classList.add("is-error");
  } else {
    fill.classList.add("is-running");
  }

  // Text lines
  const stageText = stage || "working";
  const pctText = Number.isFinite(pct) ? `${Math.round(pct)}%` : "…";
  const msg = lastMsg || "";
  meta.textContent = `${stageText} • ${pctText}`;
  status.textContent = msg;
}

async function loop(){
  if (stopped) return;
  try{
    // 1) discover latest (prefers running)
    const latest = await getLatest();
    if (latest.sync_id !== currentId){
      currentId = latest.sync_id;
      // Reset visuals when switching runs
      setIndeterminate(true);
      status.textContent = "";
    }

    // 2) progress (use payload from /latest if present; otherwise fetch)
    const p = latest.progress || await getProgress(currentId);

    if (p){
      const pct = Number.isFinite(p.progress_percent) ? p.progress_percent : undefined;
      const last = (p.messages && p.messages.length) ? p.messages[p.messages.length-1].message : "";
      setState(p.status, pct, p.current_stage, last);
    } else {
      setState("idle", undefined, "waiting", "No progress yet…");
    }
  } catch (e) {
    setState("error", undefined, "error", e.message);
  } finally {
    setTimeout(loop, 2500);  // poll ~2.5s
  }
}

setIndeterminate(true);
loop();

// Stop polling when note/pane is closed
this.containerEl?.onunload?.(() => { stopped = true; });


```

## Logs

```dataviewjs
// Configure your API server address
const API_BASE = "http://10.0.78.66:5000"; // Replace with your QNAP NAS IP

// Create container for logs
const logsContainer = dv.el("div", "", {
    style: "margin: 20px 0; padding: 15px; border-radius: 8px; background-color: #f5f5f5;"
});

// Add title
dv.el("h3", "📋 Sync Logs", { 
    container: logsContainer,
    style: "margin-top: 0; color: #333;"
});

// Loading indicator
const loadingDiv = dv.el("div", "Loading logs...", {
    container: logsContainer,
    style: "font-style: italic; color: #666;"
});

// Container for log list
const logListContainer = dv.el("div", "", {
    container: logsContainer,
    style: "display: none;"
});

// Container for log details callout (initially hidden)
const logDetailsContainer = dv.el("div", "", {
    container: logsContainer,
    style: "display: none; margin-top: 15px; padding: 15px; border-radius: 8px; border: 2px solid #007cba; background-color: #f8f9fa;"
});

// Close button for log details
const closeButton = dv.el("button", "✕ Close", {
    container: logDetailsContainer,
    style: `
        float: right;
        background: #dc3545;
        color: white;
        border: none;
        padding: 5px 10px;
        border-radius: 3px;
        cursor: pointer;
        font-size: 12px;
        margin-bottom: 10px;
    `
});

// Log details content area
const logDetailsContent = dv.el("div", "", {
    container: logDetailsContainer,
    style: "clear: both;"
});

// Close button functionality
closeButton.addEventListener("click", () => {
    logDetailsContainer.style.display = "none";
});

// Function to format duration
function formatDuration(seconds) {
    if (seconds < 60) {
        return `${Math.round(seconds)}s`;
    } else if (seconds < 3600) {
        return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
    } else {
        return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
    }
}

// Function to format timestamp
function formatTimestamp(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString();
}

// Function to display log details
async function showLogDetails(filename) {
    try {
        logDetailsContent.innerHTML = "Loading log details...";
        logDetailsContainer.style.display = "block";
        
        const response = await fetch(`${API_BASE}/logs/${filename}`);
        const data = await response.json();
        
        if (data.success && data.log) {
            const log = data.log;
            const statusIcon = log.success ? "✅" : "❌";
            const statusText = log.success ? "Success" : "Failed";
            
            let detailsHTML = `
                <h4 style="margin-top: 0; color: #333;">
                    ${statusIcon} ${log.sync_type} Sync - ${statusText}
                </h4>
                <div style="margin-bottom: 10px; font-size: 14px;">
                    <strong>Timestamp:</strong> ${formatTimestamp(log.timestamp)}<br>
                    <strong>Duration:</strong> ${formatDuration(log.duration_seconds)}<br>
                    <strong>Sync ID:</strong> <code>${log.sync_id}</code>
                </div>
                <div style="margin-bottom: 10px;">
                    <strong>Message:</strong> ${log.message}
                </div>
            `;
            
            // Add instance info for VastAI syncs
            if (log.instance_info) {
                detailsHTML += `
                    <div style="margin-bottom: 10px;">
                        <strong>Instance Info:</strong><br>
                        ID: ${log.instance_info.id}<br>
                        GPU: ${log.instance_info.gpu || 'N/A'}<br>
                        Host: ${log.instance_info.host}:${log.instance_info.port}
                    </div>
                `;
            }
            
            // Add output if available
            if (log.output) {
                detailsHTML += `
                    <div style="margin-bottom: 10px;">
                        <strong>Output:</strong>
                        <pre style="background: #e9ecef; padding: 10px; border-radius: 4px; white-space: pre-wrap; max-height: 200px; overflow-y: auto; font-size: 12px;">${log.output}</pre>
                    </div>
                `;
            }
            
            // Add error if available
            if (log.error) {
                detailsHTML += `
                    <div style="margin-bottom: 10px;">
                        <strong>Error:</strong>
                        <pre style="background: #f8d7da; padding: 10px; border-radius: 4px; white-space: pre-wrap; max-height: 200px; overflow-y: auto; font-size: 12px; color: #721c24;">${log.error}</pre>
                    </div>
                `;
            }
            
            logDetailsContent.innerHTML = detailsHTML;
        } else {
            logDetailsContent.innerHTML = `<p style="color: #dc3545;">Failed to load log details: ${data.message || 'Unknown error'}</p>`;
        }
    } catch (error) {
        logDetailsContent.innerHTML = `<p style="color: #dc3545;">Error loading log details: ${error.message}</p>`;
    }
}

// Function to load and display logs
async function loadLogs() {
    try {
        const response = await fetch(`${API_BASE}/logs/manifest`);
        const data = await response.json();
        
        loadingDiv.style.display = "none";
        
        if (data.success && data.logs && data.logs.length > 0) {
            logListContainer.style.display = "block";
            
            // Show last 5 logs
            const recentLogs = data.logs.slice(0, 5);
            
            let logListHTML = "<div style='margin-bottom: 10px; font-size: 14px; color: #666;'>Last 5 sync operations:</div>";
            
            recentLogs.forEach((log, index) => {
                const statusIcon = log.success ? "✅" : "❌";
                const timestamp = formatTimestamp(log.timestamp);
                const duration = formatDuration(log.duration_seconds || 0);
                
                logListHTML += `
                    <div class="log-item" data-filename="${log.filename}" style="
                        padding: 10px;
                        margin: 5px 0;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        cursor: pointer;
                        background: white;
                        transition: background-color 0.2s;
                    " onmouseover="this.style.backgroundColor='#f0f8ff'" onmouseout="this.style.backgroundColor='white'">
                        <div style="font-weight: bold; color: #333;">
                            ${statusIcon} ${log.sync_type} - ${timestamp}
                        </div>
                        <div style="font-size: 12px; color: #666; margin-top: 2px;">
                            ${log.message} (${duration})
                        </div>
                    </div>
                `;
            });
            
            logListContainer.innerHTML = logListHTML;
            
            // Add click handlers to log items
            const logItems = logListContainer.querySelectorAll('.log-item');
            logItems.forEach(item => {
                item.addEventListener('click', () => {
                    const filename = item.getAttribute('data-filename');
                    showLogDetails(filename);
                });
            });
            
        } else {
            logListContainer.style.display = "block";
            logListContainer.innerHTML = "<p style='color: #666; font-style: italic;'>No sync logs found.</p>";
        }
        
    } catch (error) {
        loadingDiv.style.display = "none";
        logListContainer.style.display = "block";
        logListContainer.innerHTML = `<p style='color: #dc3545;'>Failed to load logs: ${error.message}</p>`;
    }
}

// Load logs on initialization
loadLogs();
```

