#!/bin/bash
set -euo pipefail

# Make parsing deterministic
export LC_ALL=C

# ----------- ARG PARSING -----------
REMOTE_PORT=""
REMOTE_HOST="localhost"
DO_CLEANUP=0
DO_XMP=1
XMP_VENV=""
XMP_SCRIPT=""
SSH_OPTS=""
UI_HOME_OVERRIDE=""
SYNC_ID=""
PROGRESS_FILE=""

# Ensure new files default to 0644, dirs to 0755 (group-readable)
umask 022

usage() {
  echo "Usage: $0 -p <ssh-port> [--host <ip-or-name>] [--UI_HOME <path>] [--cleanup] [--no-xmp] [--venv <path>] [--xmp-script <path>] [--ssh-opts \"<flags>\"] [--sync-id <id>]"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -p)           REMOTE_PORT="${2:-}"; shift 2 ;;
    --host)       REMOTE_HOST="${2:-}"; shift 2 ;;
    --UI_HOME)    UI_HOME_OVERRIDE="${2:-}"; shift 2 ;;
    --cleanup)    DO_CLEANUP=1; shift ;;
    --no-xmp)     DO_XMP=0; shift ;;
    --venv)       XMP_VENV="${2:-}"; shift 2 ;;
    --xmp-script) XMP_SCRIPT="${2:-}"; shift 2 ;;
    --ssh-opts)   SSH_OPTS="${2:-}"; shift 2 ;;
    --sync-id)    SYNC_ID="${2:-}"; shift 2 ;;
    *)            usage ;;
  esac
done

if [ -z "$REMOTE_PORT" ]; then
  echo "❌ Port not specified."; usage
fi

# Set up progress tracking
if [[ -n "$SYNC_ID" ]]; then
  PROGRESS_FILE="/tmp/sync_progress_${SYNC_ID}.json"
  # Initialize progress file
  cat > "$PROGRESS_FILE" << EOF
{
  "sync_id": "$SYNC_ID",
  "status": "starting",
  "current_stage": "initialization",
  "progress_percent": 0,
  "total_folders": 0,
  "completed_folders": 0,
  "current_folder": "",
  "messages": [],
  "start_time": "$(date -Iseconds)",
  "last_update": "$(date -Iseconds)"
}
EOF
fi

# Progress update function
update_progress() {
  if [[ -n "$PROGRESS_FILE" && -f "$PROGRESS_FILE" ]]; then
    local stage="$1"
    local percent="$2"
    local message="${3:-}"
    local current_folder="${4:-}"
    
    # Create a temporary file to update progress atomically
    local temp_file="${PROGRESS_FILE}.tmp"
    
    # Read current progress, update it, and write back
    python3 -c "
import json
from datetime import datetime

try:
    with open('$PROGRESS_FILE', 'r') as f:
        data = json.load(f)
except Exception:
    data = {
        'sync_id': '$SYNC_ID',
        'status': 'running',
        'messages': [],
        'start_time': datetime.now().isoformat()
    }

data['current_stage'] = '$stage'
data['progress_percent'] = $percent
data['last_update'] = datetime.now().isoformat()
data['status'] = 'running'

if '$current_folder':
    data['current_folder'] = '$current_folder'

if '$message':
    data['messages'].append({
        'timestamp': datetime.now().isoformat(),
        'message': '$message'
    })
    # Keep only last 20 messages
    data['messages'] = data['messages'][-20:]

with open('$temp_file', 'w') as f:
    json.dump(data, f, indent=2)
" 2>/dev/null || true

    # Atomically replace the progress file
    if [[ -f "$temp_file" ]]; then
      mv "$temp_file" "$PROGRESS_FILE"
    fi
  fi
}

# ----------- CONFIGURATION -----------
REMOTE_USER=root
SSH_KEY=/root/.ssh/id_ed25519
LOCAL_BASE=/media
FOLDERS=("txt2img-grids" "txt2img-images" "img2img-grids" "img2img-images" "WAN" "extras-images")

# Defaults for XMP tool (can be overridden by flags)
DEFAULT_VENV="$(dirname "$0")/.venv"
DEFAULT_XMP_SCRIPT="$(dirname "$0")/xmp_tool.py"
XMP_VENV="${XMP_VENV:-$DEFAULT_VENV}"
XMP_SCRIPT="${XMP_SCRIPT:-$DEFAULT_XMP_SCRIPT}"
VENV_PY="$XMP_VENV/bin/python"

# Safer rsync flags for QNAP/eCryptfs:
# - Do NOT preserve perms/owner/group/times; those caused "Bad address (14)" in the past
# - Use --itemize-changes so we can count files actually sent (>f)
# - Add --stats so summary lines are guaranteed
# - Avoid --human-readable so bytes are raw numbers for easy parsing
RSYNC_FLAGS=(-rltD --delete --no-perms --no-owner --no-group --omit-dir-times --no-times --info=stats2 --itemize-changes --stats)
if rsync --help 2>&1 | grep -q -- '--mkpath'; then
  RSYNC_FLAGS+=(--mkpath)
fi

# SSH base
SSH_BASE=(ssh -p "$REMOTE_PORT" -i "$SSH_KEY" -o UserKnownHostsFile=/root/.ssh/known_hosts -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes)
if [[ -n "$SSH_OPTS" ]]; then SSH_BASE+=($SSH_OPTS); fi
SSH_DEST="$REMOTE_USER@$REMOTE_HOST"
SSH_CMD=("${SSH_BASE[@]}" "$SSH_DEST")

# ----------- HELPERS -----------
# Post-pass normalize: make files 0644 and dirs 0755 without tripping eCryptfs quirks.
normalize_permissions() {
  local path="$1"

  # Directories first
  find "$path" -type d ! -perm -0755 -exec chmod 0755 {} + 2>/dev/null || true

  # Try chmod for files; if any fail, repair via install(1)
  mapfile -d '' not_ok < <(find "$path" -type f ! -perm -0644 -print0 2>/dev/null || true)
  if ((${#not_ok[@]})); then
    chmod -f 0644 "${not_ok[@]}" 2>/dev/null || true
  fi

  # Fix any remaining via copy-rename trick (atomic)
  find "$path" -type f ! -perm -0644 -print0 2>/dev/null | while IFS= read -r -d '' f; do
    tmp="${f}.tmp.$$"
    if install -m 0644 -T -- "$f" "$tmp"; then
      mv -f -- "$tmp" "$f" || rm -f -- "$tmp"
    else
      rm -f -- "$tmp" 2>/dev/null || true
    fi
  done
}

# XMP tool
run_xmp_for_dir() {
  local dir="$1"
  [[ "$DO_XMP" -eq 1 ]] || return 0

  local python_exe=""
  if [ -x "$VENV_PY" ]; then
    python_exe="$VENV_PY"
  elif command -v python3 >/dev/null 2>&1; then
    python_exe="python3"
  elif command -v python >/dev/null 2>&1; then
    python_exe="python"
  else
    echo "⚠️  XMP skipped ($dir): no python executable found"
    return 0
  fi
  
  if [ ! -f "$XMP_SCRIPT" ]; then
    echo "⚠️  XMP skipped ($dir): script not found at $XMP_SCRIPT"
    return 0
  fi

  local png_count
  png_count=$(find "$dir" -type f -iname '*.png' | wc -l)
  [[ "$png_count" -gt 0 ]] || { echo "📝 XMP: no PNGs in $dir"; return 0; }

  if find "$dir" -type f -iname '*.png' -print0 \
      | xargs -0 -r -n 50 "$python_exe" "$XMP_SCRIPT" >/dev/null 2>&1; then
    echo "📝 XMP: processed $png_count PNG(s) in $dir"
  else
    echo "⚠️  XMP: errors while processing $png_count PNG(s) in $dir"
  fi
}

# Progress math helper (prevents division-by-zero)
safe_pct() {
  # args: base, completed, total
  local base="$1" completed="$2" total="$3"
  if [[ "$total" -le 0 ]]; then
    echo "$base"
  else
    echo $(( base + (completed * 60 / total) ))
  fi
}

# -------------------------------------

echo "🔗 Remote: $SSH_DEST  (port $REMOTE_PORT)"
[[ -n "$SSH_OPTS" ]] && echo "   SSH extra opts: $SSH_OPTS"

update_progress "ssh_setup" 5 "Setting up SSH connection"

# Start ssh-agent and add key
eval "$(ssh-agent -s)"
ssh-add "$SSH_KEY" >/dev/null 2>&1 || { echo "❌ Failed to add SSH key. Exiting."; exit 1; }

update_progress "remote_discovery" 10 "Discovering remote UI_HOME"

# ----------- GET UI_HOME FROM REMOTE (or override) -----------
if [[ -n "$UI_HOME_OVERRIDE" ]]; then
  UI_HOME="$UI_HOME_OVERRIDE"
  echo "📍 Using UI_HOME override: $UI_HOME"
  update_progress "remote_discovery" 15 "Using UI_HOME override: $UI_HOME"
else
  UI_HOME="$("${SSH_CMD[@]}" 'source /etc/environment 2>/dev/null || true; echo "${UI_HOME:-}"' || true)"
  if [ -z "$UI_HOME" ]; then
    echo "❌ Failed to retrieve UI_HOME from remote environment. Use --UI_HOME to specify it manually."
    update_progress "error" 0 "Failed to retrieve UI_HOME from remote"
    exit 1
  fi
  echo "📍 Retrieved UI_HOME from remote: $UI_HOME"
  update_progress "remote_discovery" 15 "Retrieved UI_HOME: $UI_HOME"
fi

echo "🧪 Cleanup flag state: DO_CLEANUP=$DO_CLEANUP"

# Detect outputs dir
OUTPUT_DIR="$("${SSH_CMD[@]}" "if [ -d \"$UI_HOME/output\" ]; then echo output; elif [ -d \"$UI_HOME/outputs\" ]; then echo outputs; else echo ''; fi" || true)"
if [ -z "$OUTPUT_DIR" ]; then
  echo "❌ Could not find 'output' or 'outputs' directory under $UI_HOME on the remote."
  update_progress "error" 0 "Could not find output directory"
  exit 1
fi

REMOTE_BASE="$UI_HOME/$OUTPUT_DIR"
echo "📁 Using remote output path: $REMOTE_BASE"
update_progress "folder_discovery" 20 "Found remote output path: $REMOTE_BASE"

# ----------- SYNC FOLDERS -----------
# Count total folders to sync
total_folders=0
for folder in "${FOLDERS[@]}"; do
  REMOTE_DIR_EXISTS="$("${SSH_CMD[@]}" "[ -d \"$REMOTE_BASE/$folder\" ] && echo yes || echo no" || true)"
  if [[ "$REMOTE_DIR_EXISTS" == "yes" ]]; then
    remote_subdirs="$("${SSH_CMD[@]}" "find \"$REMOTE_BASE/$folder\" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null || true")"
    if [ -n "$remote_subdirs" ]; then
      total_folders=$((total_folders + $(echo "$remote_subdirs" | wc -l)))
    fi
  fi
done

# Update progress file with total folders
if [[ -n "$PROGRESS_FILE" && -f "$PROGRESS_FILE" ]]; then
  python3 -c "
import json
try:
    with open('$PROGRESS_FILE', 'r') as f:
        data = json.load(f)
    data['total_folders'] = $total_folders
    with open('$PROGRESS_FILE', 'w') as f:
        json.dump(data, f, indent=2)
except Exception:
    pass
" 2>/dev/null || true
fi

# If no work, succeed with a summary and exit cleanly
if [[ "$total_folders" -le 0 ]]; then
  echo "ℹ️  Nothing to sync: no dated subfolders found."
  echo ""
  echo "📈 SYNC_SUMMARY: Files transferred: 0, Folders synced: 0, Data transferred: 0 bytes; BY_EXT: "
  echo ""
  update_progress "complete" 100 "No changes"
  if [[ -n "$PROGRESS_FILE" && -f "$PROGRESS_FILE" ]]; then
    python3 -c "
import json
from datetime import datetime
try:
    with open('$PROGRESS_FILE','r') as f: data=json.load(f)
    data['status']='completed'; data['end_time']=datetime.now().isoformat(); data['current_stage']='complete'; data['progress_percent']=100
    with open('$PROGRESS_FILE','w') as f: json.dump(data,f,indent=2)
except Exception: pass
" 2>/dev/null || true
  fi
  ssh-agent -k >/dev/null 2>&1 || true
  exit 0
fi

update_progress "sync_folders" 25 "Starting folder sync (found $total_folders folders)"

completed_folders=0
total_files_synced=0
total_bytes_transferred=0
declare -A EXT_COUNTS=()

for folder in "${FOLDERS[@]}"; do
  echo "📁 Checking: $folder"
  update_progress "sync_folders" "$(safe_pct 25 "$completed_folders" "$total_folders")" "Checking folder: $folder" "$folder"

  REMOTE_DIR_EXISTS="$("${SSH_CMD[@]}" "[ -d \"$REMOTE_BASE/$folder\" ] && echo yes || echo no" || true)"
  if [[ "$REMOTE_DIR_EXISTS" != "yes" ]]; then
    echo "⚠️  Remote folder missing: $REMOTE_BASE/$folder — skipping."
    update_progress "sync_folders" "$(safe_pct 25 "$completed_folders" "$total_folders")" "Remote folder missing: $folder" "$folder"
    continue
  fi

  remote_subdirs="$("${SSH_CMD[@]}" "find \"$REMOTE_BASE/$folder\" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null || true")"
  if [ -z "$remote_subdirs" ]; then
    echo "⚠️  No subfolders found in $folder — skipping."
    update_progress "sync_folders" "$(safe_pct 25 "$completed_folders" "$total_folders")" "No subfolders in: $folder" "$folder"
    continue
  fi

  for subdir in $remote_subdirs; do
    remote_path="$REMOTE_BASE/$folder/$subdir/"
    local_path="$LOCAL_BASE/$folder/$subdir"

    if [ ! -d "$local_path" ]; then
      echo "📁 Creating missing local folder: $folder/$subdir"
      mkdir -p "$local_path"
    else
      echo "✅ Local folder exists: $folder/$subdir"
    fi

    echo "🔄 Syncing files"
    update_progress "sync_folders" "$(safe_pct 25 "$completed_folders" "$total_folders")" "Syncing: $folder/$subdir" "$folder"
    
    RSYNC_SSH=("${SSH_BASE[@]}")

    # Capture rsync output to parse stats and per-extension counts
    rsync_output="$(mktemp)"
    if rsync "${RSYNC_FLAGS[@]}" -e "$(printf '%q ' "${RSYNC_SSH[@]}")" \
      "$SSH_DEST:$remote_path" "$local_path/" 2>&1 | tee "$rsync_output"; then

      # Count files actually sent to the receiver in this run:
      # itemized lines that begin with ">f" (allow possible leading spaces)
      count_sent_itemized="$(grep -cE '^[[:space:]]*>f' "$rsync_output" || true)"
      [[ -n "${count_sent_itemized:-}" ]] || count_sent_itemized=0

      # Summary fallback (if present)
      files_transferred_summary="$(grep -E '^Number of regular files transferred:' "$rsync_output" | awk '{print $6}' | tr -d ',' || true)"
      [[ "$files_transferred_summary" =~ ^[0-9]+$ ]] || files_transferred_summary=0

      # Prefer itemized count for "new/updated files synced"
      files_transferred="$count_sent_itemized"
      if [[ "$files_transferred" -eq 0 ]]; then
        files_transferred="$files_transferred_summary"
      fi
      total_files_synced=$(( total_files_synced + files_transferred ))

      # Bytes transferred (raw number; rsync prints "...: N bytes")
      bytes_transferred="$(grep -E '^Total transferred file size:' "$rsync_output" | awk '{print $(NF-1)}' | tr -d ',' | tr -cd '0-9' || true)"
      [[ "$bytes_transferred" =~ ^[0-9]+$ ]] || bytes_transferred=0
      total_bytes_transferred=$(( total_bytes_transferred + bytes_transferred ))

      echo "📊 Files transferred (itemized): ${count_sent_itemized}, Bytes: ${bytes_transferred}"

      # Per-extension counts from itemized lines (>f … filename)
      while IFS= read -r line; do
        [[ "$line" =~ ^[[:space:]]*>f ]] || continue
        fname="${line#* }"
        fname="${fname%% -> *}"
        ext="${fname##*.}"; ext="${ext,,}"
        [[ "$ext" == "$fname" ]] && ext=""   # no dot in name
        [[ -z "$ext" ]] && continue
        EXT_COUNTS["$ext"]=$(( ${EXT_COUNTS["$ext"]:-0} + 1 ))
      done < <(grep -E '^[[:space:]]*>f' "$rsync_output" || true)

    fi
    rm -f "$rsync_output" 2>/dev/null || true

    # Normalize permissions so SMB users can read
    echo "🛡  Normalizing permissions under: $local_path"
    normalize_permissions "$local_path"

    # XMP sidecar generation
    run_xmp_for_dir "$local_path"
    
    completed_folders=$((completed_folders + 1))
    
    # Update progress file with completed folders
    if [[ -n "$PROGRESS_FILE" && -f "$PROGRESS_FILE" ]]; then
      python3 -c "
import json
try:
    with open('$PROGRESS_FILE', 'r') as f:
        data = json.load(f)
    data['completed_folders'] = $completed_folders
    with open('$PROGRESS_FILE', 'w') as f:
        json.dump(data, f, indent=2)
except Exception:
    pass
" 2>/dev/null || true
    fi
  done
done

# ----------- OPTIONAL REMOTE CLEANUP -----------
if [[ "$DO_CLEANUP" -eq 1 ]]; then
  update_progress "cleanup" 90 "Starting remote cleanup"
  CUTOFF_DATE="$(date -d '2 days ago' +%F)"
  echo "🧹 Cleanup enabled. Deleting remote dated folders older than $CUTOFF_DATE ..."
  for folder in "${FOLDERS[@]}"; do
    REMOTE_DIR_EXISTS="$("${SSH_CMD[@]}" "[ -d \"$REMOTE_BASE/$folder\" ] && echo yes || echo no" || true)"
    if [[ "$REMOTE_DIR_EXISTS" != "yes" ]]; then
      echo "   • Skipping $folder (remote folder not found)"
      continue
    fi
    echo "   • Scanning $folder ..."
    "${SSH_CMD[@]}" "
      set -eu
      cutoff='$CUTOFF_DATE'
      base=\"$REMOTE_BASE/$folder\"
      if [ -d \"\$base\" ]; then
        find \"\$base\" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null \
          | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' \
          | while IFS= read -r d; do
              if [ \"\$d\" \< \"\$cutoff\" ]; then
                echo \"🗑 Deleting \$base/\$d\"
                rm -rf \"\$base/\$d\"
              fi
            done
      fi
    " || true
  done
  echo "✅ Cleanup complete."
  update_progress "cleanup" 95 "Remote cleanup completed"
fi

# ----------- COMPLETION -----------
# Build BY_EXT string
by_ext=""
for k in "${!EXT_COUNTS[@]}"; do
  v="${EXT_COUNTS[$k]}"
  if [[ -z "$by_ext" ]]; then by_ext="${k}=${v}"; else by_ext="${by_ext},${k}=${v}"; fi
done

echo ""
echo "📈 SYNC_SUMMARY: Files transferred: ${total_files_synced}, Folders synced: ${completed_folders}, Data transferred: ${total_bytes_transferred} bytes; BY_EXT: ${by_ext}"
echo ""

update_progress "complete" 100 "Sync completed successfully"

# ----------- CLEANUP -----------
# Mark sync as completed in progress file
if [[ -n "$PROGRESS_FILE" && -f "$PROGRESS_FILE" ]]; then
  python3 -c "
import json
from datetime import datetime
try:
    with open('$PROGRESS_FILE', 'r') as f:
        data = json.load(f)
    data['status'] = 'completed'
    data['end_time'] = datetime.now().isoformat()
    data['current_stage'] = 'complete'
    data['progress_percent'] = 100
    with open('$PROGRESS_FILE', 'w') as f:
        json.dump(data, f, indent=2)
except Exception:
    pass
" 2>/dev/null || true
fi

ssh-agent -k >/dev/null 2>&1 || true