// SSH Host Key Management

let currentHostKeyError = null;

/**
 * Show the host key error modal with error details
 */
function showHostKeyErrorModal(hostKeyError) {
    currentHostKeyError = hostKeyError;
    
    // Update modal content
    document.getElementById('hk-host').textContent = hostKeyError.host || 'Unknown';
    document.getElementById('hk-port').textContent = hostKeyError.port || 'Unknown';
    document.getElementById('hk-fingerprint').textContent = hostKeyError.new_fingerprint || 'Unknown';
    document.getElementById('hk-file').textContent = hostKeyError.known_hosts_file || 'Unknown';
    
    // Show the modal
    document.getElementById('hostKeyErrorOverlay').style.display = 'flex';
}

/**
 * Close the host key error modal
 */
function closeHostKeyErrorModal() {
    document.getElementById('hostKeyErrorOverlay').style.display = 'none';
    currentHostKeyError = null;
}

/**
 * Resolve the host key error by accepting the new key
 */
async function resolveHostKeyError() {
    if (!currentHostKeyError) {
        console.error('No host key error to resolve');
        return;
    }
    
    const resolveBtn = document.getElementById('resolveHostKeyBtn');
    const originalText = resolveBtn.innerHTML;
    
    try {
        // Disable button and show loading state
        resolveBtn.disabled = true;
        resolveBtn.innerHTML = '<span>⏳</span> Resolving...';
        
        // Call API to resolve the host key error
        const response = await fetch('/ssh/host-keys/resolve', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                host: currentHostKeyError.host,
                port: currentHostKeyError.port,
                known_hosts_file: currentHostKeyError.known_hosts_file,
                user: 'root'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Show success message
            const resultDiv = document.getElementById('result');
            resultDiv.className = 'result-panel success';
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = `
                <h3>✅ Host Key Resolved</h3>
                <p>${data.message}</p>
                <p>You can now retry the sync operation.</p>
            `;
            
            // Close the modal
            closeHostKeyErrorModal();
        } else {
            // Show error message
            alert(`Failed to resolve host key: ${data.message}`);
            resolveBtn.disabled = false;
            resolveBtn.innerHTML = originalText;
        }
    } catch (error) {
        console.error('Error resolving host key:', error);
        alert(`Error resolving host key: ${error.message}`);
        resolveBtn.disabled = false;
        resolveBtn.innerHTML = originalText;
    }
}

/**
 * Check if SSH output contains a host key error
 */
async function checkHostKeyError(sshOutput) {
    try {
        const response = await fetch('/ssh/host-keys/check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ssh_output: sshOutput
            })
        });
        
        const data = await response.json();
        
        if (data.success && data.has_error) {
            return data.error;
        }
        
        return null;
    } catch (error) {
        console.error('Error checking for host key error:', error);
        return null;
    }
}

/**
 * Remove a host key from known_hosts
 */
async function removeHostKey(host, port, knownHostsFile = null) {
    try {
        const response = await fetch('/ssh/host-keys/remove', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                host: host,
                port: port,
                known_hosts_file: knownHostsFile
            })
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error removing host key:', error);
        return { success: false, message: error.message };
    }
}
