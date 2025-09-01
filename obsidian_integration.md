
```dataviewjs
// =============================
// Media Sync — Buttons & Status
// =============================
const API_BASE = "http://10.0.78.66:5000"; // NAS API base

// Container
const container = dv.el("div", "", {
  style: "margin:20px 0;padding:15px;border-radius:8px;background-color:#f5f5f5;"
});

// Title
dv.el("h3", "🔄 Media Sync Tool", { 
  container,
  style: "margin-top:0;color:#333;"
});

// Operations
const syncOperations = [
  { name: "🔥 Sync Forge", endpoint: "/sync/forge",  description: "Sync from Stable Diffusion WebUI Forge (10.0.78.108:2222)" },
  { name: "🖼️ Sync Comfy", endpoint: "/sync/comfy",  description: "Sync from ComfyUI (10.0.78.108:2223)" },
  { name: "☁️ Sync VastAI", endpoint: "/sync/vastai", description: "Auto-discover VastAI instance and sync" },
];

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
  dv.el("br", "", { container: row });
  dv.el("small", operation.description, { container: row, style: "color:#888;margin-left:5px;" });

  // CLICK: send a "simple request" POST (no headers) to avoid CORS preflight on mobile
  button.addEventListener("click", async () => {
    const originalText = button.textContent;
    button.textContent = "Syncing...";
    button.style.background = "#ffa500";
    status.textContent = "Starting sync operation...";

    try {
      // Add timeout for mobile networks
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout for sync operations
      
      const resp = await fetch(API_BASE + operation.endpoint, { 
        method: "POST",
        signal: controller.signal
      }); // <-- no headers to avoid CORS preflight
      clearTimeout(timeoutId);
      
      const data = await resp.json();

      if (data.success) {
        button.style.background = "#28a745";
        button.textContent = "✅ Success";
        status.textContent = data.message || "Sync started";
        if (data.instance_info?.id) status.textContent += ` (Instance: ${data.instance_info.id})`;
      } else {
        button.style.background = "#dc3545";
        button.textContent = "❌ Failed";
        status.textContent = data.message || "Sync failed";
      }
    } catch (err) {
      button.style.background = "#dc3545";
      if (err.name === 'AbortError') {
        button.textContent = "⏱️ Timeout";
        status.textContent = "Request timed out - sync may still be running";
      } else {
        button.textContent = "❌ Error";
        status.textContent = `Request failed: ${err.message}`;
      }
    }

    setTimeout(() => {
      button.textContent = originalText;
      button.style.background = "#007cba";
      status.textContent = "";
    }, 5000);
  });
});

// ---- Status check ----
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
    // Add timeout for mobile networks
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
    
    const r = await fetch(API_BASE + "/status", {
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    
    const d = await r.json();
    let html = "<strong>Status:</strong><br>";
    html += `Forge: ${d.forge?.available ? '✅' : '❌'}<br>`;
    html += `ComfyUI: ${d.comfy?.available ? '✅' : '❌'}<br>`;
    html += `VastAI: ${d.vastai?.available ? '✅' : '❌'}`;
    if (d.vastai?.error) html += ` (${d.vastai.error})`;
    statusText.innerHTML = html;
  } catch (e) {
    if (e.name === 'AbortError') {
      statusText.textContent = "Status check timed out - network may be slow";
    } else {
      statusText.textContent = `Status check failed: ${e.message}`;
    }
  }
});

```

---

```dataviewjs

// ==================================================
// Media Sync — Auto Attach + Loading Bar + Auto-Hide
// ==================================================
const API_BASE = "http://10.0.78.66:5000";
const POLL_DELAY_MS = 1000;   // at least 1s between polls
const HIDE_FADE_MS  = 250;    // match CSS fade duration

// UI
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
  try {
    // Add timeout for mobile networks
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
    
    const r = await fetch(`${API_BASE}/sync/latest`, {
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    
    const j = await r.json();
    if (!j.success) return null; // Don't throw error - just return null when no active sync
    return j; // { success, sync_id, progress }
  } catch (e) {
    // Network timeout or abort - return null instead of throwing
    if (e.name === 'AbortError') {
      console.warn('Sync status check timed out - mobile network may be slow');
    }
    return null;
  }
}
async function getProgress(id){
  try{
    // Add timeout for mobile networks
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
    
    const r = await fetch(`${API_BASE}/sync/progress/${id}`, {
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    
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

    // If no active sync found, check if we had a current sync that completed
    if (!latest) {
      if (currentId) {
        // Check if the last known sync completed successfully
        const lastProgress = await getProgress(currentId);
        if (lastProgress && (lastProgress.status === "completed" || lastProgress.progress_percent >= 100)) {
          setState("completed", 100, "completed", "Sync completed successfully!");
          setTimeout(() => hidePanel(), 2000); // Hide after showing success
        }
        currentId = null; // Clear the current sync ID
      }
      // Hide panel when no active sync and no success message to show
      if (!currentId) hidePanel();
      return; // Exit early, no error to show
    }

    // New or different run? switch + reset visuals
    if (latest.sync_id !== currentId) {
      currentId = latest.sync_id;
      setIndeterminate(true);
      status.textContent = "";
    }

    const p = latest.progress || await getProgress(currentId);

    // Hide when done; show when active/new
    const isDone = !!p && (p.status === "completed" || (Number.isFinite(p.progress_percent) && p.progress_percent >= 100));
    if (isDone) {
      setState("completed", 100, "completed", "Sync completed successfully!");
      setTimeout(() => hidePanel(), 2000); // Hide after showing success
    } else {
      showPanel();
    }

    if (!hidden && !isDone) {
      if (p){
        const pct  = Number.isFinite(p.progress_percent) ? p.progress_percent : undefined;
        const last = (p.messages && p.messages.length) ? p.messages[p.messages.length-1].message : "";
        setState(p.status, pct, p.current_stage, last);
      } else {
        setState("idle", undefined, "waiting", "No progress yet…");
      }
    }
  } catch (e) {
    // Only show error panel for actual network/fetch errors, not when sync completes
    console.warn("Sync progress polling error:", e.message);
    // Don't show error state for common cases like "no latest sync"
    if (e.message && !e.message.includes("no latest") && !e.message.includes("404")) {
      showPanel();
      setState("error", undefined, "error", `Connection issue: ${e.message}`);
    }
  } finally {
    setTimeout(loop, POLL_DELAY_MS);
  }
}

// Kickoff
wrap.classList.add("msync-wrap-init","msync-hidden");
setTimeout(() => { showPanel(); }, 10); // initial fade-in
setIndeterminate(true);
loop();
this.containerEl?.onunload?.(() => { stopped = true; });




```

