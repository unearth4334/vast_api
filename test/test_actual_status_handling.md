# Actual Status Handling Test Documentation

## Overview
This document describes the changes made to ensure the `actual_status` field is used as the source of truth for instance status display in the UI.

## Changes Made

### 1. JavaScript Status Prioritization
Updated all JavaScript files to prioritize `actual_status` when normalizing instance data:

- **`app/webui/js/vastai/instances.js`**: 
  - `normalizeInstance()` now checks `actual_status` first before falling back to `cur_state`, `status`, or `state`
  - Preserves `actual_status` in the normalized instance object
  - Uses the already-normalized `status` field in display functions

- **`app/webui/js/vastai-legacy.js`**: 
  - Same changes as above for legacy compatibility

- **`app/webui/js/main.js`**: 
  - Uses the already-normalized `status` from `normalizeInstance()`

### 2. CSS Styling
Added CSS classes for additional status states:

- **`app/webui/css/app.css`**:
  - Added `.instance-status.loading` style (yellow/warning color)
  - Added `.instance-status.unknown` style (gray/muted color)

### 3. Button Disabling Logic
The buttons are already correctly conditional based on normalized status:

- **"OB Token: fetch" link**: Only shown when `normalizedStatus === 'running'`
- **"🔗 Connect to SSH Connection Field" button**: Only shown when `normalizedStatus === 'running'`
- When status is not "running", shows "🔄 Load SSH" or "🔄 Refresh details" button instead

## Test Cases

### Case 1: Instance with `actual_status: null`
```json
{
  "actual_status": null,
  "cur_state": "running"
}
```
**Expected Behavior**:
- Status badge shows: "unknown" (gray)
- OB Token shows: "N/A" (no fetch link)
- SSH button shows: "🔄 Load SSH" (refresh button, not connect button)

### Case 2: Instance with `actual_status: "loading"`
```json
{
  "actual_status": "loading",
  "cur_state": "running"
}
```
**Expected Behavior**:
- Status badge shows: "loading" (yellow/warning)
- OB Token shows: "N/A" (no fetch link)
- SSH button shows: "🔄 Load SSH" (refresh button, not connect button)

### Case 3: Instance with `actual_status: "running"`
```json
{
  "actual_status": "running",
  "cur_state": "running"
}
```
**Expected Behavior**:
- Status badge shows: "running" (green)
- OB Token shows: "fetch" (clickable link)
- SSH button shows: "🔗 Connect to SSH Connection Field" (connect button)

### Case 4: Instance with `actual_status: "running"` but `cur_state: "stopped"`
```json
{
  "actual_status": "running",
  "cur_state": "stopped"
}
```
**Expected Behavior**:
- Status badge shows: "running" (green) - prioritizes actual_status
- OB Token shows: "fetch" (clickable link)
- SSH button shows: "🔗 Connect to SSH Connection Field" (connect button)

## Status Normalization Hierarchy

The `normalizeInstance()` function now checks status fields in this order:
1. `actual_status` (primary source of truth)
2. `cur_state` (fallback)
3. `status` (fallback)
4. `state` (fallback)
5. `"unknown"` (default)

The normalized status is then passed through `normStatus()` which maps values:
- "running", "active", "started" → "running"
- "stopped", "terminated", "off" → "stopped"
- "starting", "pending", "init" → "starting"
- Everything else → returned as-is (e.g., "loading", "unknown")

## Files Modified

1. `/home/sdamk/dev/vast_api/app/webui/js/vastai/instances.js`
2. `/home/sdamk/dev/vast_api/app/webui/js/vastai-legacy.js`
3. `/home/sdamk/dev/vast_api/app/webui/js/main.js`
4. `/home/sdamk/dev/vast_api/app/webui/css/app.css`

## Backend Compatibility

The backend already provides the correct data:
- `/vastai/instances` endpoint returns full instance objects including `actual_status`
- `/vastai/instances/<id>` endpoint returns full instance objects including `actual_status`
- The VastAI API wrapper in `app/utils/vastai_api.py` passes through all fields from the VastAI API

No backend changes were required.
