#!/bin/bash

# SYNOPSIS
#     A dedicated installer for ComfyUI custom nodes only.
# DESCRIPTION
#     This script installs custom nodes for an existing ComfyUI installation.
#     It expects ComfyUI to already be installed with a virtual environment.
#
# USAGE
#     ./install-custom-nodes.sh <comfy_path> [--venv-path <path>] [--progress-file <path>] [--verbose]
#
# OPTIONS
#     --venv-path <path>      Path to custom Python virtual environment
#     --progress-file <path>  Path to custom progress JSON file
#     --verbose               Enable verbose logging for debugging progress statistics

#===========================================================================
# SECTION 1: SCRIPT CONFIGURATION & HELPER FUNCTIONS
#===========================================================================

# Parse arguments for ComfyUI root path and optional venv path
if [ $# -eq 0 ]; then
    echo "Error: ComfyUI root directory is required as an argument."
    exit 1
fi

COMFY_PATH="$1"
CUSTOM_VENV_PATH=""
CUSTOM_PROGRESS_FILE=""
VERBOSE=false

# Check for optional venv-path argument
if [ $# -ge 3 ] && [ "$2" = "--venv-path" ]; then
    CUSTOM_VENV_PATH="$3"
fi

# Check for optional progress-file argument
if [ $# -ge 5 ] && [ "$4" = "--progress-file" ]; then
    CUSTOM_PROGRESS_FILE="$5"
fi

# Check for optional verbose flag
if [[ " $* " =~ " --verbose " ]]; then
    VERBOSE=true
fi

# Derive other paths from ComfyUI root and script location
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
INSTALL_PATH="$(dirname "$SCRIPT_DIR")"
SCRIPT_PATH="$INSTALL_PATH/scripts"

# Set venv python path - use custom path if provided, otherwise default
if [ -n "$CUSTOM_VENV_PATH" ]; then
    VENV_PYTHON="$CUSTOM_VENV_PATH"
else
    VENV_PYTHON="$COMFY_PATH/venv/bin/python"
fi

LOG_PATH="$INSTALL_PATH/logs"
LOG_FILE="$LOG_PATH/install_custom_nodes_log.txt"

# Progress log file - overwritten on each run
PROGRESS_LOG="/tmp/custom_nodes_install.log"

# JSON progress file for real-time progress tracking
# Use custom progress file if specified, otherwise default
if [ -n "$CUSTOM_PROGRESS_FILE" ]; then
    PROGRESS_JSON="$CUSTOM_PROGRESS_FILE"
else
    PROGRESS_JSON="/tmp/custom_nodes_progress.json"
fi

# Clear progress log at start
> "$PROGRESS_LOG"
> "$PROGRESS_JSON"

# Load dependencies configuration
DEPENDENCIES_FILE="$(dirname "$0")/dependencies.json"
if [ ! -f "$DEPENDENCIES_FILE" ]; then
    echo "FATAL: dependencies.json not found..." >&2
    read -p "Press Enter to continue..."
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p "$LOG_PATH"

# Verbose logging function
verbose_log() {
    if [ "$VERBOSE" = true ]; then
        # Portable timestamp with milliseconds (use nanoseconds and truncate)
        local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
        local nanos=$(date "+%N" 2>/dev/null || echo "000000000")
        # Validate nanos is at least 3 chars and extract first 3 digits
        if [ ${#nanos} -ge 3 ]; then
            local millis=${nanos:0:3}
        else
            local millis="000"
        fi
        timestamp="${timestamp}.${millis}"
        echo "[VERBOSE $timestamp] $*" >&2
        echo "[VERBOSE $timestamp] $*" >> "$LOG_FILE"
    fi
}

# Write a structured log entry for progress parsing
write_progress_log() {
    local event_type="$1"
    local node_name="$2"
    local status="$3"
    local message="${4:-}"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    
    # Format: [TIMESTAMP] EVENT_TYPE|NODE_NAME|STATUS|MESSAGE
    echo "[$timestamp] $event_type|$node_name|$status|$message" >> "$PROGRESS_LOG"
    
    verbose_log "Progress log: event=$event_type, node=$node_name, status=$status, message=$message"
}

# Write JSON progress file for real-time tracking
write_json_progress() {
    local in_progress="$1"
    local total_nodes="$2"
    local processed="$3"
    local current_node="$4"
    local current_status="$5"
    local successful="${6:-0}"
    local failed="${7:-0}"
    local has_requirements="${8:-false}"
    local requirements_status="${9:-}"
    local clone_progress="${10:-}"
    
    # Escape node name for JSON (replace quotes with escaped quotes)
    local escaped_node=$(echo "$current_node" | sed 's/"/\\"/g')
    
    # Determine completion status
    local completed="false"
    local success_status="true"
    if [ "$in_progress" = "false" ]; then
        completed="true"
        # Installation is successful if we have no failed nodes, or at least some successful ones
        if [ "$failed" -gt 0 ] && [ "$successful" -eq 0 ]; then
            success_status="false"
        fi
    fi
    
    # Build JSON object with completed and success fields
    cat > "$PROGRESS_JSON" <<EOF
{
  "in_progress": $in_progress,
  "completed": $completed,
  "success": $success_status,
  "total_nodes": $total_nodes,
  "processed": $processed,
  "current_node": "$escaped_node",
  "current_status": "$current_status",
  "successful": $successful,
  "failed": $failed,
  "has_requirements": $has_requirements$([ -n "$requirements_status" ] && echo ",
  \"requirements_status\": \"$requirements_status\"" || echo "")$([ -n "$clone_progress" ] && echo ",
  \"clone_progress\": $clone_progress" || echo "")
}
EOF
}

# Write JSON progress file with download statistics
write_json_progress_with_stats() {
    local in_progress="$1"
    local total_nodes="$2"
    local processed="$3"
    local current_node="$4"
    local current_status="$5"
    local successful="${6:-0}"
    local failed="${7:-0}"
    local has_requirements="${8:-false}"
    local requirements_status="${9:-}"
    local clone_progress="${10:-}"
    local download_rate="${11:-}"
    local data_received="${12:-}"
    local total_size="${13:-}"
    local elapsed_time="${14:-}"
    local eta="${15:-}"
    
    verbose_log "Writing progress JSON: node='$current_node', status='$current_status', progress=$clone_progress%, rate='$download_rate', received='$data_received', size='$total_size', elapsed='$elapsed_time', eta='$eta'"
    
    # Escape node name and strings for JSON (replace quotes with escaped quotes)
    local escaped_node=$(echo "$current_node" | sed 's/"/\\"/g')
    local escaped_rate=$(echo "$download_rate" | sed 's/"/\\"/g')
    local escaped_data=$(echo "$data_received" | sed 's/"/\\"/g')
    local escaped_total_size=$(echo "$total_size" | sed 's/"/\\"/g')
    local escaped_elapsed=$(echo "$elapsed_time" | sed 's/"/\\"/g')
    local escaped_eta=$(echo "$eta" | sed 's/"/\\"/g')
    
    # Determine completion status
    local completed="false"
    local success_status="true"
    if [ "$in_progress" = "false" ]; then
        completed="true"
        # Installation is successful if we have no failed nodes, or at least some successful ones
        if [ "$failed" -gt 0 ] && [ "$successful" -eq 0 ]; then
            success_status="false"
        fi
    fi
    
    # Build JSON object with completed and success fields
    cat > "$PROGRESS_JSON" <<EOF
{
  "in_progress": $in_progress,
  "completed": $completed,
  "success": $success_status,
  "total_nodes": $total_nodes,
  "processed": $processed,
  "current_node": "$escaped_node",
  "current_status": "$current_status",
  "successful": $successful,
  "failed": $failed,
  "has_requirements": $has_requirements$([ -n "$requirements_status" ] && echo ",
  \"requirements_status\": \"$requirements_status\"" || echo "")$([ -n "$clone_progress" ] && echo ",
  \"clone_progress\": $clone_progress" || echo "")$([ -n "$download_rate" ] && echo ",
  \"download_rate\": \"$escaped_rate\"" || echo "")$([ -n "$data_received" ] && echo ",
  \"data_received\": \"$escaped_data\"" || echo "")$([ -n "$total_size" ] && echo ",
  \"total_size\": \"$escaped_total_size\"" || echo "")$([ -n "$elapsed_time" ] && echo ",
  \"elapsed_time\": \"$escaped_elapsed\"" || echo "")$([ -n "$eta" ] && echo ",
  \"eta\": \"$escaped_eta\"" || echo "")
}
EOF
}

# Function to clone repository with progress updates
clone_with_progress() {
    local repo_url="$1"
    local target_path="$2"
    local node_name="$3"
    local total_nodes="$4"
    local current_node="$5"
    local successful="$6"
    local failed="$7"
    
    # Track start time for elapsed time and ETA calculation
    local start_time=$(date +%s)
    local last_progress=0
    local last_update_time=$start_time
    local last_eta_calc_time=$start_time
    local ETA_UPDATE_INTERVAL=3  # Update ETA calculation every 3 seconds to reduce overhead
    
    # Run git clone with progress output
    git clone --progress --depth 1 "$repo_url" "$target_path" 2>&1 | while IFS= read -r line; do
        # Git outputs progress like: "Receiving objects: 45% (123/456), 2.5 MiB | 1.2 MiB/s"
        local progress=""
        local download_rate=""
        local data_received=""
        local total_size=""
        local object_count=""
        local total_objects=""
        
        # Extract percentage and object counts (e.g., "Receiving objects: 45% (123/456)")
        if [[ "$line" =~ Receiving[[:space:]]+objects:[[:space:]]*([0-9]+)%[[:space:]]*\(([0-9]+)/([0-9]+)\) ]]; then
            progress="${BASH_REMATCH[1]}"
            object_count="${BASH_REMATCH[2]}"
            total_objects="${BASH_REMATCH[3]}"
            verbose_log "Parsed git progress: $progress% ($object_count/$total_objects objects)"
        elif [[ "$line" =~ Receiving[[:space:]]+objects:[[:space:]]*([0-9]+)% ]]; then
            progress="${BASH_REMATCH[1]}"
            verbose_log "Parsed git progress: $progress%"
        fi
        
        # Extract data and rate with better precision
        # Note: Git uses binary units (KiB, MiB, GiB) which are consistent with our display format
        # Pattern 1: "2.5 MiB | 1.2 MiB/s" (includes both data and rate)
        if [[ "$line" =~ ([0-9.]+)[[:space:]]+(KiB|MiB|GiB)[[:space:]]*\|[[:space:]]*([0-9.]+)[[:space:]]+(KiB|MiB|GiB)/s ]]; then
            data_received="${BASH_REMATCH[1]} ${BASH_REMATCH[2]}"
            download_rate="${BASH_REMATCH[3]} ${BASH_REMATCH[4]}/s"
            verbose_log "Parsed git data: received=$data_received, rate=$download_rate"
        # Pattern 2: Just data received (no rate yet)
        elif [[ "$line" =~ ([0-9.]+)[[:space:]]+(KiB|MiB|GiB) ]] && [[ ! "$line" =~ /s ]]; then
            data_received="${BASH_REMATCH[1]} ${BASH_REMATCH[2]}"
        fi
        
        # Extract total size if present (e.g., "done. Total 456 (delta 123), reused 234 (delta 45), pack-reused 0, pack size 5.2 MiB")
        if [[ "$line" =~ pack[[:space:]]*size[[:space:]]+([0-9.]+)[[:space:]]+(KiB|MiB|GiB) ]]; then
            total_size="${BASH_REMATCH[1]} ${BASH_REMATCH[2]}"
        fi
        
        # Calculate elapsed time and ETA
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        local elapsed_str=$(printf "%02d:%02d" $((elapsed / 60)) $((elapsed % 60)))
        local eta_str=""
        
        # Calculate ETA based on progress using bash arithmetic (avoid bc dependency)
        # Rate-limit ETA calculation to every few seconds to reduce overhead
        if [ -n "$progress" ] && [ "$progress" -gt 0 ] && [ "$progress" -lt 100 ]; then
            # Only calculate ETA if we have meaningful progress and enough time has passed
            local time_since_last_eta=$((current_time - last_eta_calc_time))
            if [ "$time_since_last_eta" -ge "$ETA_UPDATE_INTERVAL" ] && [ "$progress" -gt "$last_progress" ]; then
                local time_diff=$((current_time - last_update_time))
                # Safeguard against division by zero
                if [ "$time_diff" -gt 0 ]; then
                    local progress_diff=$((progress - last_progress))
                    # Safeguard: ensure progress_diff is positive
                    if [ "$progress_diff" -gt 0 ]; then
                        # Use bash integer arithmetic: rate = (progress_diff * 100) / time_diff (in hundredths per second)
                        local rate_per_sec_x100=$(( (progress_diff * 100) / time_diff ))
                        if [ "$rate_per_sec_x100" -gt 0 ]; then
                            local remaining_progress=$((100 - progress))
                            # eta_seconds = (remaining * 100) / rate_per_sec_x100
                            local eta_seconds=$(( (remaining_progress * 100) / rate_per_sec_x100 ))
                            if [ "$eta_seconds" -gt 0 ]; then
                                eta_str=$(printf "%02d:%02d" $((eta_seconds / 60)) $((eta_seconds % 60)))
                                verbose_log "ETA calculated: progress_diff=$progress_diff, time_diff=$time_diff, rate_x100=$rate_per_sec_x100, eta=$eta_str"
                            fi
                        fi
                    fi
                    last_progress=$progress
                    last_update_time=$current_time
                    last_eta_calc_time=$current_time
                fi
            fi
        fi
        
        # Update JSON progress with comprehensive clone statistics
        if [ -n "$progress" ] || [ -n "$download_rate" ] || [ -n "$data_received" ]; then
            write_json_progress_with_stats true "$total_nodes" "$current_node" "$node_name" "running" "$successful" "$failed" false "" "$progress" "$download_rate" "$data_received" "$total_size" "$elapsed_str" "$eta_str"
        fi
        
        # Log the output
        echo "$line" >> "$LOG_FILE"
    done
    
    # Calculate final elapsed time
    local end_time=$(date +%s)
    local total_elapsed=$((end_time - start_time))
    local elapsed_str=$(printf "%02d:%02d" $((total_elapsed / 60)) $((total_elapsed % 60)))
    
    # Get the actual size of the cloned repository
    if [ -d "$target_path" ]; then
        # Get size in bytes and convert to human-readable with consistent units (MiB, KiB, GiB)
        # Using pure bash arithmetic for consistency (no bc or awk dependencies)
        local repo_size_bytes=$(du -sb "$target_path" 2>/dev/null | cut -f1)
        local repo_size=""
        # Validate that we got a valid number
        if [ -n "$repo_size_bytes" ] && [[ "$repo_size_bytes" =~ ^[0-9]+$ ]]; then
            if [ "$repo_size_bytes" -ge 1073741824 ]; then
                # GiB - multiply by 10 for one decimal place, then divide
                local size_gib_x10=$(( (repo_size_bytes * 10) / 1073741824 ))
                local size_int=$((size_gib_x10 / 10))
                local size_dec=$((size_gib_x10 % 10))
                repo_size="${size_int}.${size_dec} GiB"
            elif [ "$repo_size_bytes" -ge 1048576 ]; then
                # MiB - multiply by 10 for one decimal place, then divide
                local size_mib_x10=$(( (repo_size_bytes * 10) / 1048576 ))
                local size_int=$((size_mib_x10 / 10))
                local size_dec=$((size_mib_x10 % 10))
                repo_size="${size_int}.${size_dec} MiB"
            else
                # KiB - multiply by 10 for one decimal place, then divide
                local size_kib_x10=$(( (repo_size_bytes * 10) / 1024 ))
                local size_int=$((size_kib_x10 / 10))
                local size_dec=$((size_kib_x10 % 10))
                repo_size="${size_int}.${size_dec} KiB"
            fi
        fi
        # Write final completion status with size
        # Note: Using repo_size for both total_size and data_received as final status
        # During cloning, data_received shows transfer progress; at completion, shows final size
        write_json_progress_with_stats true "$total_nodes" "$current_node" "$node_name" "success" "$successful" "$failed" false "" "100" "" "$repo_size" "$repo_size" "$elapsed_str" "00:00"
    fi
    
    # Return the exit code of git clone (from PIPESTATUS)
    return ${PIPESTATUS[0]}
}

# Function to write log messages
write_log() {
    local message="$1"
    local level="${2:-1}"
    local color="${3:-white}"
    
    local prefix=""
    local default_color="white"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    
    case $level in
        -2) prefix="" ;;
        0)
            local wrapped_message="| $message |"
            local separator=$(printf '=%.0s' $(seq 1 ${#wrapped_message}))
            local console_message="\n$separator\n$wrapped_message\n$separator"
            local log_message="[$timestamp] $message"
            default_color="yellow"
            ;;
        1) prefix="  - " ;;
        2) prefix="    -> " ;;
        3) prefix="      [INFO] " ;;
    esac
    
    if [ "$color" = "default" ]; then color="$default_color"; fi
    
    if [ $level -ne 0 ]; then
        log_message="[$timestamp] $(echo "$prefix" | xargs) $message"
        console_message="$prefix$message"
    fi
    
    # Print to console with color (simplified color support)
    case $color in
        red) echo -e "\e[31m$console_message\e[0m" ;;
        green) echo -e "\e[32m$console_message\e[0m" ;;
        yellow) echo -e "\e[33m$console_message\e[0m" ;;
        gray) echo -e "\e[90m$console_message\e[0m" ;;
        cyan) echo -e "\e[36m$console_message\e[0m" ;;
        *) echo "$console_message" ;;
    esac
    
    # Append to log file
    echo "$log_message" >> "$LOG_FILE"
    
    # Also write to progress log for real-time parsing
    echo "$log_message" >> "$PROGRESS_LOG"
}

# Function to execute commands and log them
invoke_and_log() {
    local command="$1"
    shift
    local args="$*"
    
    local temp_log_file=$(mktemp)
    
    write_log "Executing: $command $args" 3
    
    if "$command" $args >> "$temp_log_file" 2>&1; then
        cat "$temp_log_file" >> "$LOG_FILE"
        rm -f "$temp_log_file"
        return 0
    else
        local exit_code=$?
        write_log "COMMAND FAILED with exit code $exit_code: $command $args" 3 "red"
        cat "$temp_log_file" >> "$LOG_FILE"
        rm -f "$temp_log_file"
        return $exit_code
    fi
}

# Function to install pip requirements with progress tracking
install_requirements_with_progress() {
    local python_bin="$1"
    local requirements_file="$2"
    local node_name="$3"
    local total_nodes="$4"
    local current_node="$5"
    local successful="$6"
    local failed="$7"
    
    write_log "Executing: $python_bin -m pip install -r $requirements_file" 3
    
    # Track start time for elapsed time calculation
    local start_time=$(date +%s)
    local package_count=0
    local total_packages=$(grep -v "^#" "$requirements_file" | grep -v "^$" | wc -l)
    
    # Run pip install with progress output
    "$python_bin" -m pip install -r "$requirements_file" 2>&1 | while IFS= read -r line; do
        # Log the output
        echo "$line" >> "$LOG_FILE"
        
        # Parse pip output for package being installed
        # Note: pip uses decimal units (kB, MB, GB) while git uses binary units (KiB, MiB, GiB)
        # This is intentional as we preserve the original units from each tool
        local current_package=""
        local download_size=""
        local download_rate=""
        
        # Extract package name from "Collecting package-name"
        if [[ "$line" =~ Collecting[[:space:]]+([^[:space:]]+) ]]; then
            current_package="${BASH_REMATCH[1]}"
            ((package_count++))
            local progress_pct=$((package_count * 100 / total_packages))
            
            # Calculate elapsed time
            local current_time=$(date +%s)
            local elapsed=$((current_time - start_time))
            local elapsed_str=$(printf "%02d:%02d" $((elapsed / 60)) $((elapsed % 60)))
            
            write_json_progress_with_stats true "$total_nodes" "$current_node" "$node_name" "running" "$successful" "$failed" true "collecting ($package_count/$total_packages): $current_package" "$progress_pct" "" "" "" "$elapsed_str" ""
        # Extract download size and rate from "Downloading package (1.2 MB 3.4 MB/s)"
        elif [[ "$line" =~ Downloading.*\(([0-9.]+)[[:space:]]+(kB|MB|GB).*([0-9.]+)[[:space:]]+(kB|MB|GB)/s\) ]]; then
            download_size="${BASH_REMATCH[1]} ${BASH_REMATCH[2]}"
            download_rate="${BASH_REMATCH[3]} ${BASH_REMATCH[4]}/s"
            local progress_pct=$((package_count * 100 / total_packages))
            
            local current_time=$(date +%s)
            local elapsed=$((current_time - start_time))
            local elapsed_str=$(printf "%02d:%02d" $((elapsed / 60)) $((elapsed % 60)))
            
            write_json_progress_with_stats true "$total_nodes" "$current_node" "$node_name" "running" "$successful" "$failed" true "downloading ($package_count/$total_packages)" "$progress_pct" "$download_rate" "$download_size" "" "$elapsed_str" ""
        elif [[ "$line" =~ Downloading.*\(([0-9.]+)[[:space:]]+(kB|MB|GB)\) ]]; then
            download_size="${BASH_REMATCH[1]} ${BASH_REMATCH[2]}"
            local progress_pct=$((package_count * 100 / total_packages))
            
            local current_time=$(date +%s)
            local elapsed=$((current_time - start_time))
            local elapsed_str=$(printf "%02d:%02d" $((elapsed / 60)) $((elapsed % 60)))
            
            write_json_progress_with_stats true "$total_nodes" "$current_node" "$node_name" "running" "$successful" "$failed" true "downloading ($package_count/$total_packages)" "$progress_pct" "" "$download_size" "" "$elapsed_str" ""
        elif [[ "$line" =~ Installing[[:space:]]+collected[[:space:]]+packages ]]; then
            local progress_pct=$((package_count * 100 / total_packages))
            
            local current_time=$(date +%s)
            local elapsed=$((current_time - start_time))
            local elapsed_str=$(printf "%02d:%02d" $((elapsed / 60)) $((elapsed % 60)))
            
            write_json_progress_with_stats true "$total_nodes" "$current_node" "$node_name" "running" "$successful" "$failed" true "installing ($package_count/$total_packages packages)" "$progress_pct" "" "" "" "$elapsed_str" ""
        fi
    done
    
    # Calculate final elapsed time
    local end_time=$(date +%s)
    local total_elapsed=$((end_time - start_time))
    local elapsed_str=$(printf "%02d:%02d" $((total_elapsed / 60)) $((total_elapsed % 60)))
    
    # Write final status with elapsed time
    write_json_progress_with_stats true "$total_nodes" "$current_node" "$node_name" "success" "$successful" "$failed" true "installed ($package_count packages)" "100" "" "" "" "$elapsed_str" ""
    
    # Return the exit code of pip install
    return ${PIPESTATUS[0]}
}

#===========================================================================
# SECTION 2: VALIDATION
#===========================================================================

write_log "ComfyUI Custom Nodes Installer" 0

# Log start event
write_progress_log "START" "installer" "initializing" "Beginning installation"

# Write initial JSON progress
write_json_progress true 0 0 "Initializing" "running" 0 0 false

# Check if ComfyUI is installed
if [ ! -d "$COMFY_PATH" ]; then
    write_log "ComfyUI installation not found at: $COMFY_PATH" 1 "red"
    write_log "Please install ComfyUI first using the main installer." 1 "red"
    read -p "Press Enter to exit..."
    exit 1
fi

# Check if virtual environment exists
if [ ! -f "$VENV_PYTHON" ]; then
    write_log "Python virtual environment not found at: $VENV_PYTHON" 1 "red"
    write_log "Please ensure ComfyUI is properly installed with its virtual environment." 1 "red"
    read -p "Press Enter to exit..."
    exit 1
fi

# Test the virtual environment
if ! "$VENV_PYTHON" --version > /dev/null 2>&1; then
    write_log "Python virtual environment is not functional" 1 "red"
    write_log "Please reinstall ComfyUI to fix the virtual environment." 1 "red"
    read -p "Press Enter to exit..."
    exit 1
fi

write_log "ComfyUI installation found and virtual environment is functional" 1 "green"

#===========================================================================
# SECTION 3: INSTALL CUSTOM NODES
#===========================================================================

write_log "Installing Custom Nodes" 0

CUSTOM_NODES_CSV="$SCRIPT_PATH/custom_nodes.csv"
if [ -f "$CUSTOM_NODES_CSV" ]; then
    CUSTOM_NODES_PATH="$COMFY_PATH/custom_nodes"
    mkdir -p "$CUSTOM_NODES_PATH"
    
    # Count total nodes for progress tracking (exclude empty lines)
    TOTAL_NODES=$(tail -n +2 "$CUSTOM_NODES_CSV" | grep -v "^[[:space:]]*$" | wc -l)
    CURRENT_NODE=0
    SUCCESSFUL_NODES=0
    FAILED_NODES=0
    
    write_log "Found $TOTAL_NODES custom nodes to process" 1
    
    # Log total nodes count
    write_progress_log "INFO" "installer" "installing" "Found $TOTAL_NODES nodes to install"
    
    # Write initial progress with total count
    write_json_progress true "$TOTAL_NODES" 0 "Starting installation" "running" 0 0 false
    
    # Skip header line and process each custom node
    # Use process substitution to avoid subshell and preserve variable updates
    while IFS=',' read -r name repo_url subfolder requirements_file; do
        if [ -n "$name" ] && [ -n "$repo_url" ]; then
            ((CURRENT_NODE++))
            write_log "[$CURRENT_NODE/$TOTAL_NODES] Processing custom node: $name" 1
            
            # Log node processing start
            write_progress_log "NODE" "$name" "processing" "Node $CURRENT_NODE/$TOTAL_NODES"
            
            # Write JSON progress for node being processed
            write_json_progress true "$TOTAL_NODES" "$CURRENT_NODE" "$name" "running" "$SUCCESSFUL_NODES" "$FAILED_NODES" false
            
            if [ -n "$subfolder" ]; then
                NODE_PATH="$CUSTOM_NODES_PATH/$subfolder"
            else
                NODE_PATH="$CUSTOM_NODES_PATH/$name"
            fi
            
            if [ ! -d "$NODE_PATH" ]; then
                write_log "Cloning repository: $repo_url" 2
                write_progress_log "NODE" "$name" "cloning" "Cloning repository"
                
                if clone_with_progress "$repo_url" "$NODE_PATH" "$name" "$TOTAL_NODES" "$CURRENT_NODE" "$SUCCESSFUL_NODES" "$FAILED_NODES"; then
                    # Validate the clone - check if it has valid git history
                    if ! (cd "$NODE_PATH" && git rev-parse HEAD >/dev/null 2>&1); then
                        write_log "Clone validation failed for $name, repository is empty or invalid. Re-cloning..." 2 "yellow"
                        rm -rf "$NODE_PATH"
                        if ! clone_with_progress "$repo_url" "$NODE_PATH" "$name" "$TOTAL_NODES" "$CURRENT_NODE" "$SUCCESSFUL_NODES" "$FAILED_NODES"; then
                            write_log "Failed to re-clone $name" 2 "red"
                            write_progress_log "NODE" "$name" "failed" "Failed to clone repository"
                            ((FAILED_NODES++))
                            write_json_progress true "$TOTAL_NODES" "$CURRENT_NODE" "$name" "failed" "$SUCCESSFUL_NODES" "$FAILED_NODES" false
                            continue
                        fi
                    fi
                    
                    write_log "Successfully cloned $name" 2 "green"
                    ((SUCCESSFUL_NODES++))
                    
                    # Install requirements if specified
                    if [ -n "$requirements_file" ] && [ -f "$NODE_PATH/$requirements_file" ]; then
                        write_log "Installing requirements: $requirements_file" 2
                        write_progress_log "NODE" "$name" "installing_requirements" "Installing dependencies"
                        
                        # Update JSON progress to show requirements installation
                        write_json_progress true "$TOTAL_NODES" "$CURRENT_NODE" "$name" "running" "$SUCCESSFUL_NODES" "$FAILED_NODES" true "running"
                        
                        if install_requirements_with_progress "$VENV_PYTHON" "$NODE_PATH/$requirements_file" "$name" "$TOTAL_NODES" "$CURRENT_NODE" "$SUCCESSFUL_NODES" "$FAILED_NODES"; then
                            write_log "Successfully installed requirements for $name" 2 "green"
                            write_progress_log "NODE" "$name" "success" "Installed successfully"
                            
                            # Update JSON progress with requirements success
                            write_json_progress true "$TOTAL_NODES" "$CURRENT_NODE" "$name" "success" "$SUCCESSFUL_NODES" "$FAILED_NODES" true "success"
                        else
                            write_log "Failed to install requirements for $name" 2 "yellow"
                            write_progress_log "NODE" "$name" "partial" "Cloned, but requirements failed"
                            
                            # Update JSON progress with requirements failure
                            write_json_progress true "$TOTAL_NODES" "$CURRENT_NODE" "$name" "success" "$SUCCESSFUL_NODES" "$FAILED_NODES" true "failed"
                        fi
                    else
                        # No requirements file, mark as success after clone
                        write_progress_log "NODE" "$name" "success" "Installed successfully"
                        
                        # Update JSON progress with success
                        write_json_progress true "$TOTAL_NODES" "$CURRENT_NODE" "$name" "success" "$SUCCESSFUL_NODES" "$FAILED_NODES" false
                    fi
                else
                    write_log "Failed to clone $name" 2 "red"
                    write_progress_log "NODE" "$name" "failed" "Failed to clone repository"
                    ((FAILED_NODES++))
                    
                    # Update JSON progress with failure
                    write_json_progress true "$TOTAL_NODES" "$CURRENT_NODE" "$name" "failed" "$SUCCESSFUL_NODES" "$FAILED_NODES" false
                fi
            else
                write_log "Custom node $name already exists, skipping" 2 "gray"
                write_progress_log "NODE" "$name" "success" "Already installed"
                ((SUCCESSFUL_NODES++))
                
                # Update JSON progress for already installed node
                write_json_progress true "$TOTAL_NODES" "$CURRENT_NODE" "$name" "success" "$SUCCESSFUL_NODES" "$FAILED_NODES" false
            fi
        else
            write_log "Skipping invalid entry: name='$name', repo_url='$repo_url'" 2 "yellow"
            if [ -n "$name" ]; then
                write_progress_log "NODE" "$name" "failed" "Invalid configuration" 
                ((FAILED_NODES++))
                ((CURRENT_NODE++))
                
                # Update JSON progress for invalid node
                write_json_progress true "$TOTAL_NODES" "$CURRENT_NODE" "$name" "failed" "$SUCCESSFUL_NODES" "$FAILED_NODES" false
            fi
        fi
    done < <(tail -n +2 "$CUSTOM_NODES_CSV")
else
    write_log "Custom nodes CSV file not found: $CUSTOM_NODES_CSV" 1 "yellow"
    write_log "Please ensure the custom_nodes.csv file exists in the scripts directory." 1 "yellow"
    
    # Write error to JSON progress
    write_json_progress false 0 0 "Error: CSV file not found" "failed" 0 1 false
    
    read -p "Press Enter to exit..."
    exit 1
fi

#===========================================================================
# SECTION 4: COMPLETION
#===========================================================================

# Log completion
write_progress_log "COMPLETE" "installer" "completed" "Installation finished"

# Write final JSON progress
write_json_progress false "$TOTAL_NODES" "$TOTAL_NODES" "Installation complete" "completed" "$SUCCESSFUL_NODES" "$FAILED_NODES" false

write_log "Custom Nodes Installation Complete!" 0 "green"
write_log "All custom nodes have been installed to: $CUSTOM_NODES_PATH" 1 "green"
write_log "You can now start ComfyUI to use the newly installed custom nodes." 1 "green"

echo
echo "============================================================"
echo "                 Installation Summary"
echo "============================================================"
echo "• Custom nodes installed to: $CUSTOM_NODES_PATH"
echo "• Log file saved to: $LOG_FILE"
echo "• You can now start ComfyUI to use the new nodes"
echo "============================================================"
echo

read -p "Press Enter to close this window."
