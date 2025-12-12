# Download Statistics Feature for Custom Nodes Installation

## Overview
This feature adds real-time download statistics and a swirling loading icon to the custom nodes installation tasklist UI. Users can now see download rate, data received, and progress percentage during git clone operations.

## Changes Made

### 1. Shell Script Enhancements (`scripts/install-custom-nodes.sh`)
- **Enhanced `clone_with_progress()` function** to parse git clone output and extract:
  - Download progress percentage
  - Download rate (e.g., "1.2 MiB/s")
  - Data received (e.g., "5.4 MiB")
- **Added `write_json_progress_with_stats()` function** to write enhanced progress JSON with download statistics
- Progress data now includes `download_rate` and `data_received` fields

### 2. CSS Styling (`app/webui/css/progress-indicators.css`)
- **Added swirling loading icon** using Braille patterns: ⣾⣽⣻⢿⡿⣟⣯⣷
- **New `.checklist-download-stats` section** that displays at the bottom of the checklist
- **Animation keyframes** for smooth icon rotation (8-step animation)
- Styled download statistics with monospace font for better readability

### 3. JavaScript Progress Indicators (`app/webui/js/progress-indicators.js`)
- **Updated `showChecklistProgress()` method** to accept optional `stats` parameter
- **Added statistics footer HTML** that displays:
  - Downloaded data amount
  - Current download rate
  - Estimated time remaining (ETA)
- Swirling loading icon animates during downloads

### 4. Frontend Integration (`app/webui/js/vastai/instances.js`)
- **Enhanced node tracking** to preserve node reference for stats extraction
- **Extract download statistics** from active node's progress data
- **Pass stats to UI** via `showChecklistProgress()` call
- Statistics automatically update during git clone operations

### 5. Backend API (`app/sync/sync_api.py`)
- **Modified `/ssh/install-custom-nodes/progress` endpoint** to:
  - Make `task_id` optional (backward compatibility)
  - Read both progress JSON and progress log files
  - Parse log to build complete nodes array
  - Include download statistics in response
- **Added `_parse_progress_log()` function** to:
  - Parse structured log entries
  - Build nodes array with current state
  - Merge real-time stats from progress JSON
  - Filter system messages
- **Response format changed** to wrap progress data in `progress` field for frontend compatibility

### 6. Unit Tests (`test/test_parse_progress_log.py`)
- 6 comprehensive tests covering:
  - Empty log handling
  - Single and multiple node parsing
  - Node status updates
  - System message filtering
  - Current progress integration
- All tests pass successfully

## Technical Details

### Progress Data Flow
1. Shell script clones repository and captures git output
2. Script parses git progress lines for percentage, rate, and data received
3. Stats written to JSON via `write_json_progress_with_stats()`
4. Backend reads JSON and log file on each poll
5. Backend constructs nodes array with merged stats
6. Frontend receives progress with nodes array
7. UI extracts active node stats and displays at bottom

### JSON Format
```json
{
  "in_progress": true,
  "total_nodes": 10,
  "processed": 3,
  "current_node": "ComfyUI-Manager",
  "current_status": "cloning",
  "clone_progress": 45,
  "download_rate": "1.2 MiB/s",
  "data_received": "5.4 MiB",
  "nodes": [
    {
      "name": "ComfyUI-Manager",
      "status": "cloning",
      "message": "Cloning...",
      "clone_progress": 45,
      "download_rate": "1.2 MiB/s",
      "data_received": "5.4 MiB"
    },
    ...
  ]
}
```

### UI Display
The statistics appear at the bottom of the checklist in a dedicated footer:
```
⣾⣽⣻⢿ Downloaded: 5.4 MiB • Rate: 1.2 MiB/s • ETA: 30s
```

## Files Modified
1. `scripts/install-custom-nodes.sh` - Enhanced progress tracking
2. `app/webui/css/progress-indicators.css` - Added loading icon and stats styles
3. `app/webui/js/progress-indicators.js` - Updated to display stats
4. `app/webui/js/vastai/instances.js` - Integrated stats extraction
5. `app/sync/sync_api.py` - Backend API enhancements

## Files Added
1. `test/test_parse_progress_log.py` - Unit tests for log parsing

## Benefits
- **Better user experience**: Users can see exactly what's happening during downloads
- **Reduced anxiety**: Progress indicators show the system is working
- **Debugging aid**: Download rates help identify network issues
- **Professional appearance**: Animated loading icon provides visual feedback

## Future Enhancements
- Calculate and display ETA based on remaining data and current rate
- Add total download size estimation
- Show network speed graphs
- Add pause/resume functionality for downloads
