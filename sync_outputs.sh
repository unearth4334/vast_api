#!/bin/bash
set -euo pipefail

# ----------- ARG PARSING -----------
REMOTE_PORT=""
REMOTE_HOST="localhost"
DO_CLEANUP=0
DO_XMP=1
XMP_VENV=""
XMP_SCRIPT=""
SSH_OPTS=""
UI_HOME_OVERRIDE=""

usage() {
  echo "Usage: $0 -p <ssh-port> [--host <ip-or-name>] [--UI_HOME <path>] [--cleanup] [--no-xmp] [--venv <path>] [--xmp-script <path>] [--ssh-opts \"<flags>\"]"
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
    *)            usage ;;
  esac
done

if [ -z "$REMOTE_PORT" ]; then
  echo "❌ Port not specified."; usage
fi

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
# - Do NOT preserve perms/owner/group/times; those cause "Bad address (14)"
RSYNC_FLAGS=(-rltD --delete --no-perms --no-owner --no-group --omit-dir-times --no-times --info=stats2 --human-readable)
# Add --mkpath if supported (rsync >=3.2)
if rsync --help 2>&1 | grep -q -- '--mkpath'; then
  RSYNC_FLAGS+=(--mkpath)
fi

# Build SSH command defaults (identity + strict LAN trust file)
SSH_BASE=(ssh -p "$REMOTE_PORT" -i "$SSH_KEY" -o UserKnownHostsFile=/root/.ssh/known_hosts -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes)
if [[ -n "$SSH_OPTS" ]]; then SSH_BASE+=($SSH_OPTS); fi
SSH_DEST="$REMOTE_USER@$REMOTE_HOST"
SSH_CMD=("${SSH_BASE[@]}" "$SSH_DEST")

# Helper: run xmp tool for a directory (creates .xmp for *.png)
run_xmp_for_dir() {
  local dir="$1"

  if [[ "$DO_XMP" -ne 1 ]]; then
    return 0
  fi
  if [ ! -x "$VENV_PY" ]; then
    echo "⚠️  XMP skipped ($dir): venv python not found at $VENV_PY"
    return 0
  fi
  if [ ! -f "$XMP_SCRIPT" ]; then
    echo "⚠️  XMP skipped ($dir): script not found at $XMP_SCRIPT"
    return 0
  fi

  local png_count
  png_count=$(find "$dir" -type f -iname '*.png' | wc -l)

  if [[ "$png_count" -eq 0 ]]; then
    echo "📝 XMP: no PNGs in $dir"
    return 0
  fi

  if find "$dir" -type f -iname '*.png' -print0 \
      | xargs -0 -r -n 50 "$VENV_PY" "$XMP_SCRIPT" >/dev/null 2>&1; then
    echo "📝 XMP: processed $png_count PNG(s) in $dir"
  else
    echo "⚠️  XMP: errors while processing $png_count PNG(s) in $dir"
  fi
}

# -------------------------------------

echo "🔗 Remote: $SSH_DEST  (port $REMOTE_PORT)"
if [[ -n "$SSH_OPTS" ]]; then echo "   SSH extra opts: $SSH_OPTS"; fi

# Start ssh-agent and add key
eval "$(ssh-agent -s)"
ssh-add "$SSH_KEY" || { echo "❌ Failed to add SSH key. Exiting."; exit 1; }

# ----------- GET UI_HOME FROM REMOTE (or override) -----------
if [[ -n "$UI_HOME_OVERRIDE" ]]; then
  UI_HOME="$UI_HOME_OVERRIDE"
  echo "📍 Using UI_HOME override: $UI_HOME"
else
  UI_HOME="$("${SSH_CMD[@]}" 'source /etc/environment 2>/dev/null || true; echo "${UI_HOME:-}"' || true)"
  if [ -z "$UI_HOME" ]; then
    echo "❌ Failed to retrieve UI_HOME from remote environment. Use --UI_HOME to specify it manually."
    exit 1
  fi
  echo "📍 Retrieved UI_HOME from remote: $UI_HOME"
fi

# Detect outputs dir
OUTPUT_DIR="$("${SSH_CMD[@]}" "if [ -d \"$UI_HOME/output\" ]; then echo output; elif [ -d \"$UI_HOME/outputs\" ]; then echo outputs; else echo ''; fi" || true)"
if [ -z "$OUTPUT_DIR" ]; then
  echo "❌ Could not find 'output' or 'outputs' directory under $UI_HOME on the remote."
  exit 1
fi

REMOTE_BASE="$UI_HOME/$OUTPUT_DIR"
echo "📁 Using remote output path: $REMOTE_BASE"

# ----------- SYNC FOLDERS -----------
for folder in "${FOLDERS[@]}"; do
  echo "📁 Checking: $folder"

  REMOTE_DIR_EXISTS="$("${SSH_CMD[@]}" "[ -d \"$REMOTE_BASE/$folder\" ] && echo yes || echo no" || true)"
  if [[ "$REMOTE_DIR_EXISTS" != "yes" ]]; then
    echo "⚠️  Remote folder missing: $REMOTE_BASE/$folder — skipping."
    continue
  fi

  remote_subdirs="$("${SSH_CMD[@]}" "find \"$REMOTE_BASE/$folder\" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null || true")"

  if [ -z "$remote_subdirs" ]; then
    echo "⚠️  No subfolders found in $folder — skipping."
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
    RSYNC_SSH=("${SSH_BASE[@]}")  # reuse base (already has key + known_hosts)

    rsync "${RSYNC_FLAGS[@]}" -e "$(printf '%q ' "${RSYNC_SSH[@]}")" \
      "$SSH_DEST:$remote_path" "$local_path/"

    run_xmp_for_dir "$local_path"
  done
done

# ----------- OPTIONAL REMOTE CLEANUP -----------
if [[ "$DO_CLEANUP" -eq 1 ]]; then
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
fi

# ----------- CLEANUP -----------
ssh-agent -k
