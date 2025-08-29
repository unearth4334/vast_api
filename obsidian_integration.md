# Obsidian DataviewJS Integration

This file contains example code for integrating the Media Sync Tool with Obsidian notes using dataviewjs.

## Setup Instructions

1. **Enable the CSS snippet**: Copy the `sync_api.css` file to your Obsidian vault's `.obsidian/snippets/` folder and enable it in Settings > Appearance > CSS snippets.

2. **Copy this dataviewjs code** to any Obsidian note where you want the sync interface.

## Simple Button Interface

Add this code block to any Obsidian note:

```dataviewjs
// Configure your API server address
const API_BASE = "http://10.0.78.66:5000"; // Replace with your QNAP NAS IP

// Create container for buttons
const container = dv.el("div", "", {
    class: "sync-tool-container",
    style: "margin: 20px 0; padding: 15px; border-radius: 8px; background-color: #f5f5f5;"
});

// Add title
dv.el("h3", "🔄 Media Sync Tool", { 
    container: container,
    class: "sync-tool-title",
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

// Add progress pane (must be defined before the button handlers)
const progressPane = dv.el("div", "", {
    container: container,
    class: "sync-progress-pane",
    style: `
        margin-top: 20px; 
        padding: 15px; 
        border-radius: 8px; 
        background-color: #e9ecef; 
        border-left: 4px solid #007cba;
        display: none;
    `
});

const progressTitle = dv.el("h4", "Progress", {
    container: progressPane,
    class: "sync-progress-title",
    style: "margin-top: 0; margin-bottom: 10px; color: #333;"
});

const progressBar = dv.el("div", "", {
    container: progressPane,
    class: "sync-progress-bar-container",
    style: `
        width: 100%; 
        height: 20px; 
        background-color: #dee2e6; 
        border-radius: 10px; 
        overflow: hidden;
        margin-bottom: 10px;
    `
});

const progressFill = dv.el("div", "", {
    container: progressBar,
    class: "sync-progress-bar-fill",
    style: `
        height: 100%; 
        background-color: #007cba; 
        width: 0%; 
        transition: width 0.3s ease;
        border-radius: 10px;
    `
});

const progressText = dv.el("div", "Initializing...", {
    container: progressPane,
    class: "sync-progress-text",
    style: "font-size: 12px; color: #666; margin-bottom: 8px;"
});

const progressDetails = dv.el("div", "", {
    container: progressPane,
    class: "sync-progress-details",
    style: "font-size: 11px; color: #888;"
});

// Progress polling function (must be defined before the button handlers)
function pollProgress(syncId, button, status, originalText) {
    let pollCount = 0;
    const maxPolls = 60; // 5 minutes at 5-second intervals
    
    const poll = async () => {
        try {
            const response = await fetch(`${API_BASE}/sync/progress/${syncId}`);
            const data = await response.json();
            
            if (data.success && data.progress) {
                const progress = data.progress;
                
                // Update progress bar
                progressFill.style.width = `${progress.progress_percent}%`;
                
                // Update progress text
                progressText.textContent = `${progress.current_stage}: ${progress.progress_percent}%`;
                
                // Update progress details
                let details = "";
                if (progress.total_folders > 0) {
                    details += `Folders: ${progress.completed_folders}/${progress.total_folders} `;
                }
                if (progress.current_folder) {
                    details += `Current: ${progress.current_folder}`;
                }
                progressDetails.textContent = details;
                
                // Show recent messages
                if (progress.messages && progress.messages.length > 0) {
                    const lastMessage = progress.messages[progress.messages.length - 1];
                    if (lastMessage && lastMessage.message) {
                        progressDetails.textContent = lastMessage.message;
                    }
                }
                
                // Check if completed
                if (progress.status === 'completed' || progress.progress_percent >= 100) {
                    progressText.textContent = "Sync completed successfully!";
                    setTimeout(() => {
                        progressPane.style.display = "none";
                    }, 3000);
                    return;
                }
                
                // Continue polling if not completed and under max polls
                if (pollCount < maxPolls && progress.status !== 'error') {
                    pollCount++;
                    setTimeout(poll, 5000); // Poll every 5 seconds
                } else {
                    // Timeout or error
                    if (pollCount >= maxPolls) {
                        progressText.textContent = "Progress polling timed out";
                    }
                    setTimeout(() => {
                        progressPane.style.display = "none";
                    }, 3000);
                }
            } else {
                // Progress not found or error
                progressText.textContent = "Progress tracking unavailable";
                setTimeout(() => {
                    progressPane.style.display = "none";
                }, 3000);
            }
        } catch (error) {
            console.error("Error polling progress:", error);
            progressText.textContent = `Progress error: ${error.message}`;
            setTimeout(() => {
                progressPane.style.display = "none";
            }, 3000);
        }
    };
    
    // Start polling immediately
    poll();
}

// Create buttons
syncOperations.forEach(operation => {
    const buttonContainer = dv.el("div", "", {
        container: container,
        class: "sync-button-container",
        style: "margin: 10px 0;"
    });
    
    const button = dv.el("button", operation.name, {
        container: buttonContainer,
        class: "sync-button",
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
        class: "sync-status",
        style: "margin-left: 10px; font-style: italic; color: #666;"
    });
    
    dv.el("br", "", { container: buttonContainer });
    dv.el("small", operation.description, {
        container: buttonContainer,
        class: "sync-description",
        style: "color: #888; margin-left: 5px;"
    });
    
    // Add click handler
    button.addEventListener("click", async () => {
        const originalText = button.textContent;
        button.textContent = "Syncing...";
        button.className = "sync-button syncing";
        button.style.background = "#ffa500";
        status.textContent = "Starting sync operation...";
        
        // Show progress pane
        progressPane.style.display = "block";
        progressTitle.textContent = `Progress: ${operation.name}`;
        progressFill.style.width = "0%";
        progressText.textContent = "Initializing...";
        progressDetails.textContent = "";
        
        try {
            const response = await fetch(API_BASE + operation.endpoint, { 
                method: "POST",
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();
            
            if (data.success) {
                button.className = "sync-button success";
                button.style.background = "#28a745";
                button.textContent = "✅ Success";
                status.textContent = data.message;
                if (data.instance_info) {
                    status.textContent += ` (Instance: ${data.instance_info.id})`;
                }
                
                // Start polling for progress if sync_id is available
                if (data.sync_id) {
                    pollProgress(data.sync_id, button, status, originalText);
                } else {
                    // Hide progress pane after 3 seconds
                    setTimeout(() => {
                        progressPane.style.display = "none";
                    }, 3000);
                }
            } else {
                button.className = "sync-button error";
                button.style.background = "#dc3545";
                button.textContent = "❌ Failed";
                status.textContent = data.message || "Sync failed";
                
                // Hide progress pane on error
                setTimeout(() => {
                    progressPane.style.display = "none";
                }, 3000);
            }
        } catch (error) {
            button.className = "sync-button error";
            button.style.background = "#dc3545";
            button.textContent = "❌ Error";
            status.textContent = `Request failed: ${error.message}`;
            
            // Hide progress pane on error
            setTimeout(() => {
                progressPane.style.display = "none";
            }, 3000);
        }
        
        // Reset button after 5 seconds
        setTimeout(() => {
            button.textContent = originalText;
            button.className = "sync-button";
            button.style.background = "#007cba";
            status.textContent = "";
        }, 5000);
    });
});

// Add status check
const statusContainer = dv.el("div", "", {
    container: container,
    class: "sync-status-container",
    style: "margin-top: 20px; padding-top: 15px; border-top: 1px solid #ddd;"
});

const statusButton = dv.el("button", "🔍 Check Status", {
    container: statusContainer,
    class: "sync-status-button",
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
    class: "sync-status-text",
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

## CSS Snippet

For the best visual experience, add the `sync_api.css` file as a CSS snippet in your Obsidian vault:

1. Copy the `sync_api.css` file to your vault's `.obsidian/snippets/` folder
2. Go to Settings > Appearance > CSS snippets
3. Toggle on the "sync_api" snippet
4. The interface will automatically use proper theme colors and responsive design

The CSS snippet provides:
- Theme-aware colors (light/dark mode support)
- Animated progress bars with moving stripes
- Responsive design for mobile devices
- Accessibility features (focus indicators)
- Smooth transitions and loading animations

