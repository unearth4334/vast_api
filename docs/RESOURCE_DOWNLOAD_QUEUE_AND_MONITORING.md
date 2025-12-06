# Resource Download Queue and Monitoring Design

## Overview
This document describes the design and specifications for a system that queues, executes, and monitors resource downloads to cloud instances. The system is triggered by the "Install Selected" button in the web UI, and supports multiple download command types (e.g., `wget`, `civitdl`).

## Goals
- Queue resource downloads per cloud instance
- Track queue and status in JSON files
- Support multiple download command types
- Monitor download progress and update status
- Web UI polls status and displays real-time progress

---

## 1. Queue File Structure
- **Location:** `./downloads/download_queue.json`
- **Format:** Array of download jobs
- **Fields per job:**
  - `id`: Unique job ID (UUID)
  - `instance_id`: Cloud instance identifier (extracted from SSH connection string)
  - `ssh_connection`: Full SSH connection string (for handler)
  - `ui_home`: Path to ComfyUI installation directory (default: `/workspace/ComfyUI`)
  - `resource_paths`: List of resource file paths (e.g., `loras/wan21_fusionx.md`)
  - `commands`: List of parsed bash commands (from resource card)
  - `total_commands`: Total number of commands in the job
  - `command_index`: Current command being executed (0-based)
  - `added_at`: ISO timestamp when added
  - `status`: `PENDING`, `RUNNING`, `COMPLETE`, `FAILED`, `HOST_VERIFICATION_NEEDED`
  - `progress`: (optional) Progress info (percent, speed, etc.)
  - `error`: (optional) Error message if failed

**Example:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "instance_id": "109_231_106_68",
    "ssh_connection": "ssh -p 44686 root@109.231.106.68 -L 8080:localhost:8080",
    "ui_home": "/workspace/ComfyUI",
    "resource_paths": ["loras/wan21_fusionx.md"],
    "commands": [
      "civitdl \"https://civitai.com/models/1678575?modelVersionId=1900322\" \"$UI_HOME/models/loras\""
    ],
    "total_commands": 1,
    "command_index": 0,
    "added_at": "2025-11-24T20:00:00Z",
    "status": "PENDING"
  }
]
```

---

## 2. Status File Structure
- **Location:** `./downloads/download_status.json`
- **Format:** Array of job status objects (mirrors queue, but updated in real time)
- **Fields:**
  - `id`: Unique job ID (matches queue entry)
  - `instance_id`: Cloud instance identifier
  - `added_at`: ISO timestamp when added (copied from queue)
  - `status`: `PENDING`, `RUNNING`, `COMPLETE`, `FAILED`, `HOST_VERIFICATION_NEEDED`
  - `total_commands`: Total number of commands in the job
  - `command_index`: Current command being executed (1-based during execution)
  - `progress`: Object with progress details:
    - `percent`: Download progress percentage (0-100)
    - `speed`: Download speed (e.g., "10.5MiB/s")
    - `stage`: Current stage ("images", "model", "download")
    - `name`: Name of the model/file being downloaded
    - `downloaded`: Amount downloaded (e.g., "50.0MiB")
    - `total`: Total size (e.g., "100.0MiB")
    - `eta`: Estimated time remaining
  - `error`: Error message (if status is `FAILED`)
  - `host_verification_needed`: Boolean flag for SSH host key verification
  - `host`: Target host (when verification needed)
  - `port`: Target port (when verification needed)
  - `updated_at`: ISO timestamp of last update

**Example Status Entry:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "instance_id": "109_231_106_68",
  "added_at": "2025-11-24T20:00:00Z",
  "status": "RUNNING",
  "total_commands": 1,
  "command_index": 1,
  "progress": {
    "type": "progress",
    "stage": "model",
    "percent": 45,
    "downloaded": "45.0MiB",
    "total": "100.0MiB",
    "speed": "10.5MiB/s",
    "name": "Test LoRA Model"
  },
  "updated_at": "2025-11-24T20:01:30Z"
}
```

---

## 3. Job Status State Machine

Jobs transition through the following states:

```
PENDING ──► RUNNING ──► COMPLETE
              │
              ├──► FAILED
              │
              └──► HOST_VERIFICATION_NEEDED ──► PENDING (after user accepts host key)
```

### State Descriptions:
- **PENDING**: Job is in queue waiting to be processed
- **RUNNING**: Job is currently executing download commands
- **COMPLETE**: All commands executed successfully
- **FAILED**: One or more commands failed with a non-host-key error
- **HOST_VERIFICATION_NEEDED**: SSH connection requires host key verification

---

## 4. Download Handler

### Location
`scripts/download_handler.py`

### Responsibilities
1. **Polling**: Checks `download_queue.json` every 2 seconds for new jobs
2. **Job Processing**:
   - Finds jobs with `status === 'PENDING'`
   - Marks job as `RUNNING` in both queue and status files
   - Connects to instance using `ssh_connection`
   - Executes each command in `commands` sequentially
3. **Progress Tracking**:
   - Monitors stdout for progress output
   - Parses output using appropriate parser (civitdl or wget)
   - Updates `progress` in status file every 2 seconds
4. **Completion Handling**:
   - On success: marks as `COMPLETE` with `percent: 100`
   - On failure: marks as `FAILED` with error message
   - On host key error: marks as `HOST_VERIFICATION_NEEDED` with host/port info

### Key Features
- **Thread-safe file locking**: Uses a Lock for concurrent access to JSON files
- **Progress callback**: Real-time progress updates via callback function
- **Host key verification**: Detects SSH host key errors and triggers verification flow

---

## 5. Command Parsing

### Resource Card Format
Commands are extracted from markdown resource files under `# Download` section:

````markdown
# Download
```bash
civitdl "https://civitai.com/models/1678575?modelVersionId=1900322" \
  "$UI_HOME/models/loras"
```
````

### Parsing Rules
1. Extract lines from bash code block under `# Download` heading
2. Join lines ending with `\` (line continuation)
3. Skip empty lines and comments (lines starting with `#`)
4. Determine parser based on command content:
   - Contains `civitdl` → CivitdlProgressParser
   - Contains `wget` → WgetProgressParser

---

## 6. Progress Parsers

### CivitdlProgressParser
Parses civitdl output format:

**Stage Start:**
```
Now downloading "Model Name"...
```
→ `{ type: 'stage_start', name: 'Model Name' }`

**Progress:**
```
Model: 50%|█████░░░░░| 50.0MiB/100.0MiB [00:05<00:05, 10.0MiB/s]
```
→ `{ type: 'progress', stage: 'model', percent: 50, downloaded: '50.0MiB', total: '100.0MiB', speed: '10.0MiB/s' }`

**Stage Complete:**
```
Download completed for "Model Name"
```
→ `{ type: 'stage_complete', name: 'Model Name' }`

### WgetProgressParser
Parses wget output format (with `--progress=bar:force`):

**Progress:**
```
model.safetensors   50%[====>        ] 50.0M  45.3MB/s  eta 5s
```
→ `{ type: 'progress', stage: 'download', filename: 'model.safetensors', percent: 50, downloaded: '50.0M', speed: '45.3MB/s', eta: '5s' }`

**Complete:**
```
'model.safetensors' saved [104857600/104857600]
```
→ `{ type: 'stage_complete', filename: 'model.safetensors', percent: 100 }`

---

## 7. API Endpoints

### POST /downloads/queue
Add resources to the download queue.

**Request Body:**
```json
{
  "ssh_connection": "ssh -p 44686 root@192.168.1.100 -L 8080:localhost:8080",
  "resources": [
    { "filepath": "loras/wan21_fusionx.md" },
    { "filepath": "upscalers/RealESRGAN.md" }
  ],
  "ui_home": "/workspace/ComfyUI"
}
```

**Response (Success):**
```json
{
  "success": true,
  "jobs": [...],
  "count": 2
}
```

**Behavior:**
- Creates **one job per resource** (not one job for all resources)
- Each job gets a unique UUID
- Extracts download commands from resource markdown files
- Returns 400 if no valid commands found

### GET /downloads/status
Get status of all download jobs, optionally filtered by instance.

**Query Parameters:**
- `instance_id` (optional): Filter by instance ID

**Response:**
```json
[
  {
    "id": "550e8400-...",
    "instance_id": "109_231_106_68",
    "status": "RUNNING",
    "progress": { "percent": 45, "speed": "10.5MiB/s" },
    "commands": [...],
    "resource_paths": [...],
    ...
  }
]
```

### POST /downloads/retry
Reset a failed job to PENDING status for retry.

**Request Body:**
```json
{
  "job_id": "550e8400-..."
}
```

### DELETE /downloads/job/{job_id}
Delete a job from queue and status files.

---

## 8. Web UI Integration

### ResourceDownloadStatus Component
Location: `app/webui/js/resource-download-status.js`

**Features:**
- Polls `/downloads/status` every 2 seconds
- Displays jobs in tasklist format with status tags
- Shows progress bar for RUNNING jobs
- Handles HOST_VERIFICATION_NEEDED by showing verification modal
- Supports delete mode (click to reveal delete buttons)
- Smart re-rendering using state hash to avoid flicker

### Polling Logic
```javascript
// Only re-render if state has changed
const stateHash = this.calculateStateHash(jobs);
if (stateHash !== this.previousStateHash) {
    this.previousStateHash = stateHash;
    this.render(jobs);
}
```

### Status Display
| Status | Icon | Tag Text |
|--------|------|----------|
| PENDING | ⏳ | Queued |
| RUNNING | ⬇️ | {percent}% or Downloading... |
| COMPLETE | ✅ | Complete |
| FAILED | ❌ | Failed |
| HOST_VERIFICATION_NEEDED | 🔐 | Verify Host |

---

## 9. File/Module Layout

```
downloads/
  download_queue.json      # Persistent queue of jobs
  download_status.json     # Real-time status for all jobs

scripts/
  download_handler.py      # Main handler/daemon for processing queue

app/
  api/
    downloads.py           # Flask API endpoints for queue/status
  utils/
    progress_parsers.py    # Parsers for civitdl, wget, etc.
  webui/
    js/
      resource-download-status.js  # UI component for download status

test/
  test_download_management_fixture.py  # Test fixtures and test cases

docs/
  RESOURCE_DOWNLOAD_QUEUE_AND_MONITORING.md  # (this file)
  TEST_FIXTURE_DOWNLOAD_MANAGEMENT.md        # Test fixture documentation
```

---

## 10. Implementation Status

- [x] Implement `download_handler.py` to process queue and update status
- [x] Implement `progress_parsers.py` for civitdl and wget
- [x] Add Flask API endpoints:
    - `POST /downloads/queue` (add job)
    - `GET /downloads/status?instance_id=...` (list jobs for instance)
    - `POST /downloads/retry` (retry failed job)
    - `DELETE /downloads/job/{job_id}` (delete job)
- [x] Update Web UI to POST to queue and poll status
- [x] Add file locking to prevent race conditions
- [x] Add tests for queueing, handler, and progress parsing
- [x] Add host key verification flow

---

## 11. Error Handling

### SSH Host Key Verification
When SSH connection fails due to unknown host key:
1. Download handler detects host key error (exit code 255 + specific error patterns)
2. Job status set to `HOST_VERIFICATION_NEEDED`
3. Status includes `host`, `port`, and `ssh_connection` for verification
4. Web UI detects this status and shows verification modal
5. User can accept/reject the host key
6. On accept: host key added to `known_hosts`, job reset to `PENDING`
7. On reject: job remains in failed state

### Command Failures
- If a command fails (non-zero exit code), job is marked as `FAILED`
- Error message includes the failed command (truncated) and exit code
- Subsequent commands in the job are not executed

### Network Errors
- Connection timeouts are handled by SSH timeout options
- Download tool failures (wget, civitdl) propagate their exit codes

---

## 12. Concurrency Considerations

### File Locking
- All JSON file read/write operations use a threading Lock
- Prevents race conditions when multiple jobs are processed

### Sequential Job Processing
- Jobs are processed one at a time (no parallel downloads per instance)
- This simplifies status tracking and reduces network contention

### UI Polling Optimization
- Status polling uses state hashing to detect changes
- UI only re-renders when state hash changes
- Prevents flickering during rapid polling

---

## 13. Example Resource Card Bash Block

````markdown
# Download
```bash
wget -P "$UI_HOME"/models/diffusion_models/Wan-2.2_ComfyUI_repackaged \
  https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_t2v_high_noise_14B_fp16.safetensors
wget -P "$UI_HOME"/models/diffusion_models/Wan-2.2_ComfyUI_repackaged \
  https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_t2v_low_noise_14B_fp16.safetensors
```

or

# Download
```bash
civitdl "https://civitai.com/models/1678575?modelVersionId=1900322" \
  "$UI_HOME/models/loras"
```
````

---

## 14. Status Polling Example (Web UI)

```javascript
async function pollDownloadStatus(instanceId) {
  const res = await fetch(`/downloads/status?instance_id=${instanceId}`);
  const jobs = await res.json();
  // Render jobs: show status, progress bar, etc.
}
setInterval(() => pollDownloadStatus(selectedInstanceId), 2000);
```

---

## 15. Open Questions
- How to handle authentication/permissions for queue/status endpoints?
- Should completed/failed jobs be archived or deleted automatically?
- Should the handler support parallel downloads per instance?
- How to handle instance restarts or handler crashes?

---

## 16. References
- See also: `RESOURCE_INSTALLATION_STREAMING.md` for civitdl progress parsing and WebSocket streaming details.
- See also: `TEST_FIXTURE_DOWNLOAD_MANAGEMENT.md` for test fixture documentation.
