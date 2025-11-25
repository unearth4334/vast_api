# Resource Download Queue and Monitoring Design

## Overview
This document proposes a design for a system that queues, executes, and monitors resource downloads to cloud instances. The system is triggered by the "Install Selected" button in the web UI, and supports multiple download command types (e.g., `wget`, `civitdl`).

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
  - `instance_id`: Cloud instance number (from SSH connection string or user selection)
  - `ssh_connection`: Full SSH connection string (for handler)
  - `resource_paths`: List of resource file paths (e.g., `loras/wan21_fusionx.md`)
  - `commands`: List of parsed bash commands (from resource card)
  - `added_at`: ISO timestamp when added
  - `status`: `PENDING`, `RUNNING`, `COMPLETE`, `FAILED`
  - `progress`: (optional) Progress info (percent, speed, etc.)
  - `error`: (optional) Error message if failed

**Example:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "instance_id": 123456,
    "ssh_connection": "ssh -p 44686 root@109.231.106.68 -L 8080:localhost:8080",
    "resource_paths": ["loras/wan21_fusionx.md"],
    "commands": [
      "civitdl \"https://civitai.com/models/1678575?modelVersionId=1900322\" \"$UI_HOME/models/loras\""
    ],
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
  - `id`, `instance_id`, `added_at` (copied from queue)
  - `status`: `PENDING`, `RUNNING`, `COMPLETE`, `FAILED`
  - `progress`: `{ percent, speed, stage, ... }` (updated as available)
  - `error`: (if any)

---

## 3. Download Handler
- **Location:** `scripts/download_handler.py` (or as a service/daemon)
- **Responsibilities:**
  - Watches `download_queue.json` for new jobs
  - For each `PENDING` job:
    - Marks as `RUNNING` in both queue and status files
    - Connects to instance using `ssh_connection`
    - Executes each command in `commands` sequentially
    - Monitors stdout for progress (parses civitdl, wget, etc.)
    - Updates `progress` in `download_status.json` (and optionally in queue)
    - On success: marks as `COMPLETE`, records completion time
    - On failure: marks as `FAILED`, records error
  - Removes or archives jobs after completion (optional)

---

## 4. Command Parsing
- **From Resource Card:**
  - Extracts all lines from the bash block under `# Download`
  - Each line is a command (multi-line commands are joined)
  - Handler determines method:
    - If `civitdl`, use civitdl progress parser
    - If `wget`, use wget progress parser
    - (Extendable for other tools)

---

## 5. Web UI Integration
- When user clicks "Install Selected":
  - Selected resources and instance info are POSTed to `/downloads/queue` endpoint
  - Backend appends job to `download_queue.json`
  - Download handler is notified (via file watcher or polling)
- Web UI polls `/downloads/status?instance_id=...` every 2 seconds
  - Displays all jobs for the selected instance
  - Shows status: `PENDING`, `RUNNING` (with progress bar), `COMPLETE`, `FAILED`
  - Progress bar uses `progress.percent` and `progress.speed` if available

---

## 6. Proposed File/Module Layout

- `downloads/`
  - `download_queue.json`      # Persistent queue of jobs
  - `download_status.json`     # Real-time status for all jobs
- `scripts/`
  - `download_handler.py`      # Main handler/daemon for processing queue
- `app/api/downloads.py`       # Flask API endpoints for queue/status
- `app/utils/progress_parsers.py` # Parsers for civitdl, wget, etc.
- `docs/RESOURCE_DOWNLOAD_QUEUE_AND_MONITORING.md` # (this file)

---

## 7. Implementation Steps (TODO)

1. [ ] Implement `download_handler.py` to process queue and update status
2. [ ] Implement `progress_parsers.py` for civitdl and wget
3. [ ] Add Flask API endpoints:
    - `POST /downloads/queue` (add job)
    - `GET /downloads/status?instance_id=...` (list jobs for instance)
4. [ ] Update Web UI to POST to queue and poll status
5. [ ] Add file locking to prevent race conditions
6. [ ] Add tests for queueing, handler, and progress parsing

---

## 8. Example Resource Card Bash Block

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

## 9. Status Polling Example (Web UI)

```javascript
async function pollDownloadStatus(instanceId) {
  const res = await fetch(`/downloads/status?instance_id=${instanceId}`);
  const jobs = await res.json();
  // Render jobs: show status, progress bar, etc.
}
setInterval(() => pollDownloadStatus(selectedInstanceId), 2000);
```

---

## 10. Open Questions
- How to handle authentication/permissions for queue/status endpoints?
- Should completed/failed jobs be archived or deleted?
- Should the handler support parallel downloads per instance?
- How to handle instance restarts or handler crashes?

---

## 11. Implementation Placeholder

> **Implement the download handler and API endpoints as described above.**
> 
> - `scripts/download_handler.py`: Main loop, command execution, progress parsing, status updates
> - `app/api/downloads.py`: Flask endpoints for queue and status
> - `app/utils/progress_parsers.py`: Parsers for civitdl, wget, etc.

---

## 12. References
- See also: `RESOURCE_INSTALLATION_STREAMING.md` for civitdl progress parsing and WebSocket streaming details.
