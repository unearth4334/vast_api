// API helper functions for making HTTP requests

// Helper function to format bytes
function formatBytes(bytes) {
    if (bytes === 0) return '0 bytes';
    const k = 1024;
    const sizes = ['bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// Generic fetch wrapper for JSON APIs
async function fetchJSON(url, options = {}) {
    const response = await fetch(url, {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    });
    return await response.json();
}

// Convenience methods for common operations
const api = {
    get: (url) => fetchJSON(url, { method: 'GET' }),
    post: (url, data = {}) => fetchJSON(url, { 
        method: 'POST', 
        body: JSON.stringify(data) 
    }),
    delete: (url) => fetchJSON(url, { method: 'DELETE' })
};

// Make API client globally available
window.api = api;