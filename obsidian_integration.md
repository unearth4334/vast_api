
```dataviewjs
// Configure your API server address
const API_BASE = "http://10.0.78.66:5000"; // Replace with your QNAP NAS IP

// Create container for buttons
const container = dv.el("div", "", {
    style: "margin: 20px 0; padding: 15px; border-radius: 8px; background-color: #f5f5f5;"
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

---

```dataviewjs
// === Media Sync — Auto Attach + Loading Bar + Auto-Hide ===
const API_BASE = "http://10.0.78.66:5000";
const POLL_DELAY_MS = 1000;   // throttle
const HIDE_FADE_MS  = 250;    // CSS fade duration (match snippet below)

const wrap  = dv.el("div","",{cls:"msync-wrap"});
const title = dv.el("div","🔄 Media Sync — Auto Attach",{container:wrap, cls:"msync-title"});
const meta  = dv.el("div","",{container:wrap, cls:"msync-meta"});
const bar   = dv.el("div","",{container:wrap, cls:"msync-bar"});
const fill  = dv.el("div","",{container:bar, cls:"msync-fill", attr:{role:"progressbar","aria-valuemin":"0","aria-valuemax":"100"}});
const status= dv.el("div","",{container:wrap, cls:"msync-status"});

let currentId = null;
let stopped   = false;
let hidden    = false;

function showPanel() {
  if (!hidden) return;
  wrap.style.display = "block";
  requestAnimationFrame(() => wrap.classList.remove("msync-hidden"));
  hidden = false;
}
function hidePanel() {
  if (hidden) return;
  wrap.classList.add("msync-hidden");
  setTimeout(() => { wrap.style.display = "none"; }, HIDE_FADE_MS);
  hidden = true;
}

async function getLatest() {
  const r = await fetch(`${API_BASE}/sync/latest`);
  const j = await r.json();
  if (!j.success) throw new Error(j.message || "no latest");
  return j; // {success, sync_id, progress}
}
async function getProgress(id){
  try{
    const r = await fetch(`${API_BASE}/sync/progress/${id}`);
    const j = await r.json();
    return (j.success && j.progress) ? j.progress : null;
  }catch{ return null; }
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
  const v = Math.max(0, Math.min(100, Number(pct)||0));
  fill.style.width = `${v}%`;
  fill.setAttribute("aria-valuenow", String(v));
}
function setState(statusText, pct, stage, lastMsg){
  title.textContent = `🔄 Media Sync — ${currentId ? `Tracking ${currentId.slice(0,8)}…` : "Idle"}`;
  if (Number.isFinite(pct)) setDeterminate(pct); else setIndeterminate(true);

  fill.classList.remove("is-complete","is-error","is-running");
  if (statusText === "completed" || (Number.isFinite(pct) && pct >= 100)) {
    fill.classList.add("is-complete");
  } else if (statusText === "error") {
    fill.classList.add("is-error");
  } else {
    fill.classList.add("is-running");
  }

  meta.textContent = `${stage || "working"} • ${Number.isFinite(pct) ? Math.round(pct) + "%" : "…"}`;
  status.textContent = lastMsg || "";
}

async function loop(){
  if (stopped) return;
  try{
    const latest = await getLatest();

    // If a new run appears (or we were hidden), switch and show panel
    if (latest.sync_id !== currentId) {
      currentId = latest.sync_id;
      setIndeterminate(true);
      status.textContent = "";
    }

    const p = latest.progress || await getProgress(currentId);

    // Decide visibility first
    const isDone = !!p && (p.status === "completed" || (Number.isFinite(p.progress_percent) && p.progress_percent >= 100));
    if (isDone) hidePanel(); else showPanel();

    // If visible, update the UI
    if (!hidden) {
      if (p){
        const pct  = Number.isFinite(p.progress_percent) ? p.progress_percent : undefined;
        const last = (p.messages && p.messages.length) ? p.messages[p.messages.length-1].message : "";
        setState(p.status, pct, p.current_stage, last);
      } else {
        setState("idle", undefined, "waiting", "No progress yet…");
      }
    }
  } catch (e) {
    // On errors, keep the panel visible to show the error
    showPanel();
    setState("error", undefined, "error", e.message);
  } finally {
    setTimeout(loop, POLL_DELAY_MS);
  }
}

// start
wrap.classList.add("msync-wrap-init","msync-hidden");
setTimeout(() => { showPanel(); }, 10); // initial fade-in
setIndeterminate(true);
loop();
this.containerEl?.onunload?.(() => { stopped = true; });




```

