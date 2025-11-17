#!/bin/bash

# SYNOPSIS
#     A dedicated installer for ComfyUI custom nodes only.
# DESCRIPTION
#     This script installs custom nodes for an existing ComfyUI installation.
#     It expects ComfyUI to already be installed with a virtual environment.

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

# Check for optional venv-path argument
if [ $# -ge 3 ] && [ "$2" = "--venv-path" ]; then
    CUSTOM_VENV_PATH="$3"
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

# Load dependencies configuration
DEPENDENCIES_FILE="$(dirname "$0")/dependencies.json"
if [ ! -f "$DEPENDENCIES_FILE" ]; then
    echo "FATAL: dependencies.json not found..." >&2
    read -p "Press Enter to continue..."
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p "$LOG_PATH"

# Progress tracking file (JSON format for easy parsing)
PROGRESS_FILE="/tmp/custom_nodes_progress.json"

# Initialize progress file
init_progress_file() {
    cat > "$PROGRESS_FILE" << 'EOF'
{
  "status": "initializing",
  "total_nodes": 0,
  "processed": 0,
  "successful": 0,
  "failed": 0,
  "nodes": []
}
EOF
}

# Update progress file with node status
update_node_progress() {
    local node_name="$1"
    local status="$2"
    local message="${3:-}"
    
    # Use Python for reliable JSON manipulation
    "$VENV_PYTHON" -c "
import json
import sys

try:
    with open('$PROGRESS_FILE', 'r') as f:
        data = json.load(f)
    
    # Find or create node entry
    node_entry = None
    for node in data['nodes']:
        if node['name'] == '$node_name':
            node_entry = node
            break
    
    if node_entry is None:
        node_entry = {'name': '$node_name', 'status': 'pending', 'message': ''}
        data['nodes'].append(node_entry)
    
    # Update node status
    node_entry['status'] = '$status'
    node_entry['message'] = '''$message'''
    
    # Update counters
    if '$status' in ['success', 'failed', 'partial']:
        data['processed'] = sum(1 for n in data['nodes'] if n['status'] in ['success', 'failed', 'partial'])
    
    data['successful'] = sum(1 for n in data['nodes'] if n['status'] == 'success')
    data['failed'] = sum(1 for n in data['nodes'] if n['status'] == 'failed')
    
    # Write atomically
    with open('$PROGRESS_FILE.tmp', 'w') as f:
        json.dump(data, f, indent=2)
    
    import os
    os.replace('$PROGRESS_FILE.tmp', '$PROGRESS_FILE')
    
except Exception as e:
    print(f'Error updating progress: {e}', file=sys.stderr)
    sys.exit(1)
" 2>> "$LOG_FILE"
}

# Set overall status
set_progress_status() {
    local status="$1"
    "$VENV_PYTHON" -c "
import json
try:
    with open('$PROGRESS_FILE', 'r') as f:
        data = json.load(f)
    data['status'] = '$status'
    with open('$PROGRESS_FILE.tmp', 'w') as f:
        json.dump(data, f, indent=2)
    import os
    os.replace('$PROGRESS_FILE.tmp', '$PROGRESS_FILE')
except:
    pass
" 2>> "$LOG_FILE"
}

# Set total nodes count
set_total_nodes() {
    local total="$1"
    "$VENV_PYTHON" -c "
import json
try:
    with open('$PROGRESS_FILE', 'r') as f:
        data = json.load(f)
    data['total_nodes'] = $total
    with open('$PROGRESS_FILE.tmp', 'w') as f:
        json.dump(data, f, indent=2)
    import os
    os.replace('$PROGRESS_FILE.tmp', '$PROGRESS_FILE')
except:
    pass
" 2>> "$LOG_FILE"
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

#===========================================================================
# SECTION 2: VALIDATION
#===========================================================================

write_log "ComfyUI Custom Nodes Installer" 0

# Initialize progress tracking
init_progress_file

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
    
    # Count total nodes for progress tracking
    TOTAL_NODES=$(tail -n +2 "$CUSTOM_NODES_CSV" | wc -l)
    CURRENT_NODE=0
    
    write_log "Found $TOTAL_NODES custom nodes to process" 1
    
    # Set total nodes in progress file
    set_total_nodes "$TOTAL_NODES"
    set_progress_status "installing"
    
    # Skip header line and process each custom node
    tail -n +2 "$CUSTOM_NODES_CSV" | while IFS=',' read -r name repo_url subfolder requirements_file; do
        if [ -n "$name" ] && [ -n "$repo_url" ]; then
            ((CURRENT_NODE++))
            write_log "[$CURRENT_NODE/$TOTAL_NODES] Processing custom node: $name" 1
            
            # Update progress: node is being processed
            update_node_progress "$name" "installing" "Processing node $CURRENT_NODE/$TOTAL_NODES"
            
            if [ -n "$subfolder" ]; then
                NODE_PATH="$CUSTOM_NODES_PATH/$subfolder"
            else
                NODE_PATH="$CUSTOM_NODES_PATH/$name"
            fi
            
            if [ ! -d "$NODE_PATH" ]; then
                write_log "Cloning repository: $repo_url" 2
                update_node_progress "$name" "cloning" "Cloning repository..."
                
                if invoke_and_log git clone "$repo_url" "$NODE_PATH"; then
                    write_log "Successfully cloned $name" 2 "green"
                    
                    # Install requirements if specified
                    if [ -n "$requirements_file" ] && [ -f "$NODE_PATH/$requirements_file" ]; then
                        write_log "Installing requirements: $requirements_file" 2
                        update_node_progress "$name" "installing_requirements" "Installing dependencies..."
                        
                        if invoke_and_log "$VENV_PYTHON" -m pip install -r "$NODE_PATH/$requirements_file"; then
                            write_log "Successfully installed requirements for $name" 2 "green"
                            update_node_progress "$name" "success" "Installed successfully"
                        else
                            write_log "Failed to install requirements for $name" 2 "yellow"
                            update_node_progress "$name" "partial" "Cloned, but requirements failed"
                        fi
                    else
                        # No requirements file, mark as success after clone
                        update_node_progress "$name" "success" "Installed successfully"
                    fi
                else
                    write_log "Failed to clone $name" 2 "red"
                    update_node_progress "$name" "failed" "Failed to clone repository"
                fi
            else
                write_log "Custom node $name already exists, skipping" 2 "gray"
                update_node_progress "$name" "success" "Already installed"
            fi
        else
            write_log "Skipping invalid entry: name='$name', repo_url='$repo_url'" 2 "yellow"
            if [ -n "$name" ]; then
                update_node_progress "$name" "failed" "Invalid configuration"
            fi
        fi
    done
else
    write_log "Custom nodes CSV file not found: $CUSTOM_NODES_CSV" 1 "yellow"
    write_log "Please ensure the custom_nodes.csv file exists in the scripts directory." 1 "yellow"
    read -p "Press Enter to exit..."
    exit 1
fi

#===========================================================================
# SECTION 4: COMPLETION
#===========================================================================

# Set final status
set_progress_status "completed"

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