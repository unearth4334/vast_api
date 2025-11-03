#!/usr/bin/env python3
"""
Visual representation of the SSH Host Key Error UI
This script shows what the UI looks like when a host key error is detected
"""

print("""
================================================================================
SSH HOST KEY ERROR - UI MOCKUP
================================================================================

When a sync operation fails due to a changed SSH host key, the user sees:

1. ERROR MESSAGE IN SYNC PANEL:
   ┌────────────────────────────────────────────────────────────────────────┐
   │ ❌ Forge sync failed                                                   │
   │                                                                        │
   │ @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@           │
   │ @    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @           │
   │ @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@           │
   │ IT IS POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!                 │
   │ ...                                                                    │
   │                                                                        │
   │ (Click for full report)                                               │
   └────────────────────────────────────────────────────────────────────────┘

2. HOST KEY ERROR MODAL (automatically displayed):
   ┌────────────────────────────────────────────────────────────────────────┐
   │ ⚠️  SSH Host Key Changed                                       ✕       │
   ├────────────────────────────────────────────────────────────────────────┤
   │                                                                        │
   │ ┌────────────────────────────────────────────────────────────────────┐ │
   │ │ ⚠️  WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!              │ │
   │ │                                                                    │ │
   │ │ The SSH host key for this server has changed. This could indicate:│ │
   │ │ • The server has been reinstalled or reconfigured                 │ │
   │ │ • You're connecting to a different server at the same address     │ │
   │ │ • Potentially a man-in-the-middle attack                          │ │
   │ └────────────────────────────────────────────────────────────────────┘ │
   │                                                                        │
   │ Host Key Details:                                                      │
   │ ┌────────────────────────────────────────────────────────────────────┐ │
   │ │ Host:              10.0.78.108                                     │ │
   │ │ Port:              2222                                            │ │
   │ │ New Fingerprint:   SHA256:6Dhif6lu1QviP6aTLpbkbv/U3CBxf89Fs...    │ │
   │ │ Known Hosts File:  /root/.ssh/known_hosts                          │ │
   │ └────────────────────────────────────────────────────────────────────┘ │
   │                                                                        │
   │ What would you like to do?                                             │
   │                                                                        │
   │           ┌─────────────────────────┐  ┌─────────────────┐            │
   │           │  ✓ Accept New Host Key  │  │    ✕ Cancel    │            │
   │           └─────────────────────────────┘  └─────────────────┘            │
   │                                                                        │
   │ Note: Accepting the new host key will remove the old key and add the  │
   │ new one to your known_hosts file. Only do this if you trust the       │
   │ server and understand why the key has changed.                        │
   │                                                                        │
   └────────────────────────────────────────────────────────────────────────┘

3. AFTER CLICKING "ACCEPT NEW HOST KEY":
   ┌────────────────────────────────────────────────────────────────────────┐
   │ ✅ Host Key Resolved                                                   │
   │                                                                        │
   │ Host key resolved successfully for 10.0.78.108:2222                   │
   │                                                                        │
   │ You can now retry the sync operation.                                 │
   └────────────────────────────────────────────────────────────────────────┘

================================================================================
FEATURES IMPLEMENTED:
================================================================================

✓ Automatic Detection:
  - Detects SSH host key errors in sync operation output
  - Parses host, port, fingerprint, and file location from error message
  
✓ User-Friendly UI:
  - Modal dialog with clear warning message
  - Displays all relevant information (host, port, fingerprint)
  - Explains potential security implications
  - One-click resolution button
  
✓ Secure Resolution:
  - Removes old host key from known_hosts
  - Accepts new host key automatically
  - Provides feedback on success/failure
  
✓ Integration:
  - Seamlessly integrated with existing sync operations
  - Minimal changes to existing codebase
  - Works with all sync types (Forge, ComfyUI, VastAI)

================================================================================
API ENDPOINTS:
================================================================================

POST /ssh/host-keys/check
  Request:  {"ssh_output": "<error message>"}
  Response: {"success": true, "has_error": true, "error": {...}}

POST /ssh/host-keys/resolve
  Request:  {"host": "10.0.78.108", "port": 2222, "user": "root"}
  Response: {"success": true, "message": "Host key resolved successfully"}

POST /ssh/host-keys/remove
  Request:  {"host": "10.0.78.108", "port": 2222}
  Response: {"success": true, "message": "Old host key removed"}

================================================================================
""")
