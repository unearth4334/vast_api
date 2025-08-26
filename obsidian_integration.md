# Obsidian DataviewJS Integration

This file contains example code for integrating the Media Sync Tool with Obsidian notes using dataviewjs.

## Simple Button Interface

Add this code block to any Obsidian note:

```dataviewjs
// Configure your API server address
const API_BASE = "http://your-nas-ip:5000"; // Replace with your QNAP NAS IP

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

## Advanced Interface with Auto-Refresh

For a more sophisticated interface that shows real-time status:

```dataviewjs
// Advanced Media Sync Interface with Auto-Status
const API_BASE = "http://your-nas-ip:5000"; // Replace with your QNAP NAS IP

class MediaSyncWidget {
    constructor(container) {
        this.container = container;
        this.statusData = null;
        this.init();
        this.startStatusPolling();
    }
    
    init() {
        this.container.style.cssText = `
            margin: 20px 0; 
            padding: 20px; 
            border-radius: 10px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        `;
        
        this.render();
    }
    
    async render() {
        this.container.innerHTML = `
            <h2 style="margin-top: 0; text-align: center;">🔄 Media Sync Control Center</h2>
            <div id="sync-buttons" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0;"></div>
            <div id="status-display" style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px; margin-top: 20px;">
                <div style="text-align: center;">Loading status...</div>
            </div>
        `;
        
        this.createSyncButtons();
        await this.updateStatus();
    }
    
    createSyncButtons() {
        const buttonsContainer = this.container.querySelector('#sync-buttons');
        const operations = [
            { name: "🔥 Forge", endpoint: "/sync/forge", color: "#ff6b35" },
            { name: "🖼️ Comfy", endpoint: "/sync/comfy", color: "#4ecdc4" },
            { name: "☁️ VastAI", endpoint: "/sync/vastai", color: "#45b7d1" }
        ];
        
        operations.forEach(op => {
            const button = document.createElement('button');
            button.innerHTML = op.name;
            button.style.cssText = `
                background: ${op.color};
                color: white;
                border: none;
                padding: 15px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                font-weight: bold;
                transition: all 0.3s ease;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            `;
            
            button.addEventListener('click', () => this.executeSync(op, button));
            button.addEventListener('mouseenter', () => {
                button.style.transform = 'translateY(-2px)';
                button.style.boxShadow = '0 6px 12px rgba(0,0,0,0.2)';
            });
            button.addEventListener('mouseleave', () => {
                button.style.transform = 'translateY(0)';
                button.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            });
            
            buttonsContainer.appendChild(button);
        });
    }
    
    async executeSync(operation, button) {
        const originalText = button.innerHTML;
        button.innerHTML = '⏳ Syncing...';
        button.disabled = true;
        
        try {
            const response = await fetch(API_BASE + operation.endpoint, { method: 'POST' });
            const data = await response.json();
            
            if (data.success) {
                button.innerHTML = '✅ Success';
                button.style.background = '#28a745';
            } else {
                button.innerHTML = '❌ Failed';
                button.style.background = '#dc3545';
            }
            
            setTimeout(() => {
                button.innerHTML = originalText;
                button.style.background = operation.color;
                button.disabled = false;
            }, 3000);
            
        } catch (error) {
            button.innerHTML = '❌ Error';
            button.style.background = '#dc3545';
            setTimeout(() => {
                button.innerHTML = originalText;
                button.style.background = operation.color;
                button.disabled = false;
            }, 3000);
        }
    }
    
    async updateStatus() {
        try {
            const response = await fetch(API_BASE + "/status");
            this.statusData = await response.json();
            this.renderStatus();
        } catch (error) {
            this.renderStatusError(error.message);
        }
    }
    
    renderStatus() {
        const statusContainer = this.container.querySelector('#status-display');
        const status = this.statusData;
        
        statusContainer.innerHTML = `
            <h4 style="margin-top: 0;">📊 Service Status</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
                <div>Forge: ${status.forge.available ? '🟢 Online' : '🔴 Offline'}</div>
                <div>ComfyUI: ${status.comfy.available ? '🟢 Online' : '🔴 Offline'}</div>
                <div>VastAI: ${status.vastai.available ? '🟢 Available' : '🟡 Unavailable'}</div>
            </div>
            ${status.vastai.instance ? `<div style="margin-top: 10px; font-size: 12px;">VastAI Instance: ${status.vastai.instance.id} (${status.vastai.instance.gpu_name})</div>` : ''}
            <div style="margin-top: 10px; font-size: 11px; opacity: 0.8;">Last updated: ${new Date().toLocaleTimeString()}</div>
        `;
    }
    
    renderStatusError(error) {
        const statusContainer = this.container.querySelector('#status-display');
        statusContainer.innerHTML = `<div style="color: #ffcccb;">❌ Status check failed: ${error}</div>`;
    }
    
    startStatusPolling() {
        // Update status every 30 seconds
        setInterval(() => this.updateStatus(), 30000);
    }
}

// Create the widget
const container = dv.el("div", "");
new MediaSyncWidget(container);
```

## Configuration Notes

1. **Replace `API_BASE`**: Update the IP address to match your QNAP NAS
2. **Network Access**: Ensure your Obsidian client can reach the NAS on port 5000
3. **HTTPS**: For secure access, consider setting up HTTPS with a reverse proxy
4. **CORS**: The API server includes CORS headers for web browser access

## Styling Options

You can customize the appearance by modifying the CSS styles in the code blocks above. The interface is responsive and will adapt to different screen sizes.