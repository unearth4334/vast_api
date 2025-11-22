// Main application bootstrapping - tabs, overlays, and page wiring

// Tab switching functionality
function showTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(tab => tab.classList.remove('active'));
    
    // Remove active class from all tab buttons
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => button.classList.remove('active'));
    
    // Show selected tab content
    const selectedTab = document.getElementById(tabName + '-tab');
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Add active class to clicked tab button
    const clickedButton = event.target;
    clickedButton.classList.add('active');
    
    // Initialize resource browser when resources tab is shown
    if (tabName === 'resources' && !window.resourceBrowserInitialized) {
        initResourceBrowser();
    }
}

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Setup log modal overlay click handling
    const overlay = document.getElementById('logOverlay');
    overlay.addEventListener('click', function(e) {
        if (e.target === overlay) {
            closeLogModal();
        }
    });
    
    // Setup result panel click handler for viewing full reports
    attachResultClickHandler();
    
    // Initialize workflow system (server-side execution + state restoration)
    if (typeof initWorkflow === 'function') {
        initWorkflow();
    }
});

// Initialize resource browser
async function initResourceBrowser() {
    try {
        const { ResourceBrowser } = await import('./resources/resource-browser.js');
        const browser = new ResourceBrowser('resource-manager-container');
        await browser.initialize();
        window.resourceBrowserInitialized = true;
    } catch (error) {
        console.error('Failed to initialize resource browser:', error);
        document.getElementById('resource-manager-container').innerHTML = 
            '<div class="error">Failed to load Resource Manager</div>';
    }
}

// Attach click handler to result panel for viewing full sync reports
function attachResultClickHandler() {
    const resultDiv = document.getElementById('result');
    resultDiv.addEventListener('click', () => {
        if (!lastFullReport) return;

        const overlay = document.getElementById('logOverlay');
        const modalTitle = document.getElementById('logModalTitle');
        const modalContent = document.getElementById('logModalContent');

        modalTitle.textContent = 'Sync Report';

        let content = '';
        // summary
        content += '<div class="log-detail-section"><h4>Summary</h4><div class="log-detail-content">';
        content += (lastFullReport.message || '') + '\\n';
        if (lastFullReport.summary) {
            const s = lastFullReport.summary;
            const bytes = s.bytes_transferred > 0 ? formatBytes(s.bytes_transferred) : '0 bytes';
            content += `Files: ${s.files_transferred}\\nFolders: ${s.folders_synced}\\nBytes: ${bytes}\\n`;
            if (s.by_ext) {
                const extLine = Object.entries(s.by_ext).sort((a,b)=>b[1]-a[1]).map(([k,v])=>k+': '+v).join(', ');
                if (extLine) content += `By type: ${extLine}\\n`;
            }
        }
        content += '</div></div>';

        // stdout
        if (lastFullReport.output) {
            content += '<div class="log-detail-section"><h4>Output</h4><div class="log-detail-content">';
            content += String(lastFullReport.output).replace(/</g,'&lt;');
            content += '</div></div>';
        }
        // stderr
        if (lastFullReport.error) {
            content += '<div class="log-detail-section"><h4>Error</h4><div class="log-detail-content">';
            content += String(lastFullReport.error).replace(/</g,'&lt;');
            content += '</div></div>';
        }

        modalContent.innerHTML = content;
        overlay.style.display = 'flex';
    });
}