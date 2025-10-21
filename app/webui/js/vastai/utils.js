// ==============================
// VastAI Utils Module
// ==============================
// Core utility functions for formatting, normalization, and data processing

/**
 * Format money values consistently
 * @param {number|null|undefined} n - The numeric value to format
 * @returns {string} Formatted money string
 */
export function fmtMoney(n) {
  if (n === null || n === undefined || isNaN(n)) return "$0/hr";
  return `$${(+n).toFixed(3)}/hr`;
}

/**
 * Format GB values consistently  
 * @param {number|null|undefined} v - The numeric value to format
 * @returns {string} Formatted GB string
 */
export function fmtGb(v) {
  if (v === null || v === undefined || isNaN(v)) return "0 GB";
  return `${(+v).toFixed(v < 10 ? 2 : 1)} GB`;
}

/**
 * Check if a value is truthy (not null, undefined, or empty string)
 * @param {any} x - Value to check
 * @returns {boolean} Whether the value is truthy
 */
export function truthy(x) { 
  return x !== undefined && x !== null && x !== ""; 
}

/**
 * Normalize status strings to consistent values
 * @param {string} s - Status string to normalize
 * @returns {string} Normalized status
 */
export function normStatus(s) {
  if (!s) return "unknown";
  const t = String(s).toLowerCase();
  if (["running", "active", "started"].some(k => t.includes(k))) return "running";
  if (["stopped", "terminated", "off"].some(k => t.includes(k))) return "stopped";
  if (["starting", "pending", "init"].some(k => t.includes(k))) return "starting";
  return t;
}

/**
 * Build a consistent geolocation string from instance data
 * @param {object} i - Instance object
 * @returns {string} Normalized geolocation string
 */
export function normGeo(i) {
  if (i.geolocation) return i.geolocation;
  const city = i.city || i.location || i.region;
  const cc = i.country_code || i.countryCode || i.cc;
  const country = i.country || i.country_name || i.countryName;
  if (country && cc) return `${country}, ${cc}`;
  if (city && country) return `${city}, ${country}`;
  if (country) return country;
  return "N/A";
}

/**
 * Get country flag emoji from geolocation string
 * @param {string} geolocation - Geolocation string to parse
 * @returns {string} Country flag emoji or fallback text
 */
export function getCountryFlag(geolocation) {
  if (!geolocation || geolocation === 'N/A') return '';

  const countryFlags = {
    'CA': '🇨🇦', 'US': '🇺🇸', 'TT': '🇹🇹', 'VN': '🇻🇳', 'KR': '🇰🇷', 
    'FR': '🇫🇷', 'CZ': '🇨🇿', 'AU': '🇦🇺', 'HK': '🇭🇰', 'CN': '🇨🇳',
    'HU': '🇭🇺', 'IN': '🇮🇳', 'BG': '🇧🇬', 'DE': '🇩🇪', 'JP': '🇯🇵',
    'SG': '🇸🇬', 'BR': '🇧🇷', 'NL': '🇳🇱', 'GB': '🇬🇧', 'UK': '🇬🇧'
  };

  // Extract parts like "City, CC" or "Country, CC"
  const parts = geolocation.split(',').map(s => s.trim());

  // Check for country codes (2 letters)
  for (let part of parts) {
    if (part.length === 2) {
      const code = part.toUpperCase();
      if (countryFlags[code]) return countryFlags[code];
      return code; // fallback: show 2-letter abbreviation
    }
  }

  // Check for country names
  for (let part of parts) {
    if (countryFlags[part]) {
      return countryFlags[part];
    }
  }

  // Last resort: take last word if it looks like code
  const last = parts[parts.length - 1];
  if (last && last.length === 2) return last.toUpperCase();

  // If we can't parse anything, show just the raw geolocation
  return geolocation;
}

/**
 * Resolve SSH connection details from instance data
 * Always regard Public IP as the SSH host (authoritative)
 * @param {object} i - Instance object
 * @returns {object} Object with host and port properties
 */
export function resolveSSH(i) {
  const host =
    i.public_ip ??
    i.public_ipaddr ??
    i.ip_address ??
    i.publicIp ??
    null;                       // <- we do NOT fall back to ssh_host; public IP wins
  
  // Extract SSH port using the same logic as backend get_ssh_port()
  // Prefers host-side port from ports mapping, falls back to ssh_port
  let port = null;
  
  try {
    // Try to get port from ports mapping (preferred method)
    const ports = i.ports;
    if (ports && typeof ports === 'object' && ports['22/tcp']) {
      const tcpPorts = ports['22/tcp'];
      if (Array.isArray(tcpPorts) && tcpPorts.length > 0) {
        const portMapping = tcpPorts[0];
        if (portMapping && portMapping.HostPort) {
          port = parseInt(portMapping.HostPort, 10);
        }
      }
    }
    
    // Fallback to ssh_port field if ports mapping didn't work
    if (port === null || isNaN(port)) {
      const sshPort = i.ssh_port || i.sshPort || i.port;
      if (sshPort) {
        port = parseInt(sshPort, 10);
      }
    }
    
    // Final fallback to default SSH port
    if (port === null || isNaN(port)) {
      port = 22;
    }
    
  } catch (error) {
    console.warn('Error parsing SSH port:', error);
    // Fallback to ssh_port field or default
    const sshPort = i.ssh_port || i.sshPort || i.port || 22;
    port = parseInt(sshPort, 10);
  }

  return { host, port };
}

console.log('📄 VastAI Utils module loaded');