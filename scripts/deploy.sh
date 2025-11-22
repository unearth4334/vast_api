#!/bin/bash

# Deploy script for vast_api on QNAP
# Usage: ./deploy.sh [push|up|down|destroy] [options]

###################################################
# Example commands:
#   ./deploy.sh git                                # Deploy main branch via git
#   ./deploy.sh git --branch develop               # Deploy specific branch via git
#   ./deploy.sh up                                 # Start containers
#   ./deploy.sh up --build                         # Start containers with rebuild
#   ./deploy.sh up --clean                         # Stop existing containers first, then start
#   ./deploy.sh up --clean --build                 # Stop, rebuild and start containers
#   ./deploy.sh deploy                             # Full deploy: git pull main + up
#   ./deploy.sh deploy --build                     # Full deploy with rebuild
#   ./deploy.sh deploy --clean                     # Full deploy with clean start
#   ./deploy.sh deploy --branch develop --build    # Deploy specific branch with rebuild
#   ./deploy.sh logs vast_api                      # Show logs for vast_api service
#   ./deploy.sh destroy                            # Destroy all containers and volumes
#   ./deploy.sh app-logs                           # Show available app logs and recent entries
#   ./deploy.sh app-logs app.log                   # Show specific log file from volume
#   ./deploy.sh status                             # Show container status
#   ./deploy.sh help                               # Show this help message
###################################################

set -e  # Exit on any error

QNAP_HOST="qnap"
REMOTE_PATH="/share/Container/vast_api"
MOUNTED_PATH="/mnt/qnap-containers/vast_api"
PROJECT_NAME="vast_api"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to deploy via git
deploy_via_git() {
    local branch="${1:-main}"
    
    log_info "Deploying via git to QNAP at ${MOUNTED_PATH}"
    log_info "Target branch: ${branch}"
    
    # Check for unpushed commits in the current repository
    if git status >/dev/null 2>&1; then
        # Get the current branch in the working directory
        local current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
        
        # Only check for unpushed commits if we're on the same branch we're deploying
        if [[ "$current_branch" == "$branch" ]]; then
            # Check if there are commits ahead of origin
            local ahead_count=$(git rev-list --count @{upstream}..HEAD 2>/dev/null || echo "0")
            
            if [[ "$ahead_count" -gt 0 ]]; then
                log_warning "You have $ahead_count unpushed commit(s) on branch '$branch'"
                log_warning "Your deployment will NOT include these local changes:"
                git log --oneline @{upstream}..HEAD 2>/dev/null || true
                echo
                log_warning "Consider running 'git push' first to include your latest changes"
                read -p "Continue with deployment anyway? (y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    log_info "Deployment cancelled"
                    exit 0
                fi
            fi
        fi
    fi
    
    # Check if mounted directory exists
    if [[ ! -d "${MOUNTED_PATH}" ]]; then
        log_error "Mounted directory ${MOUNTED_PATH} not found!"
        log_error "Please ensure QNAP directory is mounted at ${MOUNTED_PATH}"
        exit 1
    fi
    
    local start_time=$(date +%s)
    
    # Check if it's already a git repository
    if [[ ! -d "${MOUNTED_PATH}/.git" ]]; then
        log_info "Initializing git repository at ${MOUNTED_PATH}"
        
        # Get the current repository's origin URL
        local origin_url=$(git config --get remote.origin.url)
        if [[ -z "$origin_url" ]]; then
            log_error "No origin URL found in current repository"
            exit 1
        fi
        
        log_info "Cloning repository from ${origin_url}"
        
        # Create parent directory and clone
        mkdir -p "$(dirname "${MOUNTED_PATH}")"
        git clone "$origin_url" "${MOUNTED_PATH}"
        
        if [[ $? -ne 0 ]]; then
            log_error "Failed to clone repository"
            exit 1
        fi
    else
        log_info "Git repository already exists, updating..."
    fi
    
    # Change to the mounted directory
    cd "${MOUNTED_PATH}" || {
        log_error "Failed to change to ${MOUNTED_PATH}"
        exit 1
    }
    
    # Check for local changes in deployment destination (should never happen in production)
    if ! git diff --quiet || ! git diff --cached --quiet || [[ -n "$(git ls-files --others --exclude-standard)" ]]; then
        log_warning "Deployment destination has local changes that will be discarded:"
        git status --porcelain || true
        log_warning "These changes will be permanently lost during deployment!"
        log_warning "Deployment destinations should only receive changes from remote."
    fi
    
    # Ensure we're on the correct branch and pull latest changes
    log_info "Fetching latest changes..."
    git fetch origin || {
        log_error "Failed to fetch from origin"
        exit 1
    }
    
    # Get current branch
    local current_branch=$(git rev-parse --abbrev-ref HEAD)
    
    # Ensure deployment destination is clean - discard any local changes
    log_info "Ensuring deployment matches remote branch exactly..."
    
    # Switch to target branch if different (force checkout to discard local changes)
    if [[ "$current_branch" != "$branch" ]]; then
        log_info "Switching from ${current_branch} to ${branch}"
        git checkout -f "$branch" || {
            log_error "Failed to switch to branch ${branch}"
            exit 1
        }
    fi
    
    # Reset any local changes to ensure clean state
    git reset --hard HEAD || {
        log_error "Failed to reset local changes"
        exit 1
    }
    
    # Clean any untracked files
    git clean -fd || {
        log_error "Failed to clean untracked files"
        exit 1
    }
    
    # Get commit info before pull
    local old_commit=$(git rev-parse HEAD)
    
    # Force reset to match remote exactly
    log_info "Forcing deployment to match remote ${branch} exactly..."
    git reset --hard "origin/${branch}" || {
        log_error "Failed to reset to remote branch"
        exit 1
    }
    
    # Get commit info after pull
    local new_commit=$(git rev-parse HEAD)
    
    # Calculate statistics
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Show deployment results
    log_success "Git deployment completed successfully!"
    echo -e "${BLUE}  ├─${NC} Duration: ${duration}s"
    echo -e "${BLUE}  ├─${NC} Branch: ${branch}"
    echo -e "${BLUE}  ├─${NC} Target: ${MOUNTED_PATH}"
    
    if [[ "$old_commit" != "$new_commit" ]]; then
        echo -e "${BLUE}  ├─${NC} Updated: ${old_commit:0:8} → ${new_commit:0:8}"
        echo -e "${BLUE}  └─${NC} Deployment now matches remote exactly"
    else
        echo -e "${BLUE}  └─${NC} Already up to date"
    fi
    
    # Return to original directory
    cd - > /dev/null
}

# Function to start containers
docker_up() {
    local build_flag=""
    local clean_flag=""
    local docker_cmd="/share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build)
                build_flag="--build"
                shift
                ;;
            --clean)
                clean_flag="--clean"
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    # If clean flag is set, stop containers first
    if [[ -n "$clean_flag" ]]; then
        log_info "Cleaning up existing containers first..."
        ssh ${QNAP_HOST} "cd ${REMOTE_PATH} && ${docker_cmd} compose down" || true
    fi
    
    # Determine what we're doing
    if [[ -n "$build_flag" && -n "$clean_flag" ]]; then
        log_info "Starting containers with clean and build flags"
    elif [[ -n "$build_flag" ]]; then
        log_info "Starting containers with build flag"
    elif [[ -n "$clean_flag" ]]; then
        log_info "Starting containers with clean flag"
    else
        log_info "Starting containers"
    fi
    
    ssh ${QNAP_HOST} "cd ${REMOTE_PATH} && ${docker_cmd} compose up -d ${build_flag}"
    
    log_success "Containers started successfully"
    
    # Show container status
    log_info "Container status:"
    ssh ${QNAP_HOST} "cd ${REMOTE_PATH} && ${docker_cmd} compose ps"
}

# Function to stop containers
docker_down() {
    local docker_cmd="/share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker"
    log_info "Stopping containers"
    
    ssh ${QNAP_HOST} "cd ${REMOTE_PATH} && ${docker_cmd} compose down"
    
    log_success "Containers stopped successfully"
}

# Function to destroy containers and volumes
docker_destroy() {
    log_warning "This will destroy all containers and volumes for ${PROJECT_NAME}"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Destroying containers and volumes for ${PROJECT_NAME}"
        
        local docker_cmd="/share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker"
        
        # Stop and remove containers and networks defined in docker-compose.yml
        ssh ${QNAP_HOST} "cd ${REMOTE_PATH} && ${docker_cmd} compose down -v"
        
        # Remove only project-specific volumes (those prefixed with project name)
        log_info "Checking for project-specific volumes to remove..."
        local volumes_to_remove=$(ssh ${QNAP_HOST} "${docker_cmd} volume ls -q --filter name=${PROJECT_NAME}")
        
        if [[ -n "$volumes_to_remove" ]]; then
            log_info "Found project volumes to remove:"
            echo "$volumes_to_remove"
            
            # Remove each volume
            for volume in $volumes_to_remove; do
                log_info "Removing volume: $volume"
                ssh ${QNAP_HOST} "${docker_cmd} volume rm $volume" || log_warning "Failed to remove volume $volume"
            done
        else
            log_info "No project-specific volumes found to remove"
        fi
        
        log_success "Containers and volumes for ${PROJECT_NAME} destroyed successfully"
    else
        log_info "Operation cancelled"
    fi
}

# Function to show logs
show_logs() {
    local service="$1"
    local docker_cmd="/share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker"
    log_info "Showing logs for ${service:-all services}"
    
    if [[ -n "$service" ]]; then
        ssh ${QNAP_HOST} "cd ${REMOTE_PATH} && ${docker_cmd} compose logs -f ${service}"
    else
        ssh ${QNAP_HOST} "cd ${REMOTE_PATH} && ${docker_cmd} compose logs -f"
    fi
}

# Function to show application logs from vast_api_logs volume
show_app_logs() {
    local log_file="$1"
    local docker_cmd="/share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker"
    log_info "Reading application logs from vast_api_logs volume"
    
    if [[ -n "$log_file" ]]; then
        # Show specific log file (check in different subdirectories)
        log_info "Searching for log file: ${log_file}"
        ssh ${QNAP_HOST} "${docker_cmd} run --rm -v ${PROJECT_NAME}_vast_api_logs:/logs alpine sh -c 'find /logs -name \"${log_file}\" -exec cat {} \; || echo \"Log file ${log_file} not found\"'"
    else
        # List available log files and show recent entries organized by type
        log_info "Application log structure:"
        ssh ${QNAP_HOST} "${docker_cmd} run --rm -v ${PROJECT_NAME}_vast_api_logs:/logs alpine sh -c 'find /logs -type f -name \"*.json\" -o -name \"*.log\" -o -name \"*.txt\" | sort'"
        
        echo
        log_info "Recent VastAI API logs:"
        ssh ${QNAP_HOST} "${docker_cmd} run --rm -v ${PROJECT_NAME}_vast_api_logs:/logs alpine sh -c 'find /logs/vastai/api -name \"*.json\" -exec tail -5 {} + 2>/dev/null || echo \"No VastAI API logs found\"'"
        
        echo  
        log_info "Recent sync operation logs:"
        ssh ${QNAP_HOST} "${docker_cmd} run --rm -v ${PROJECT_NAME}_vast_api_logs:/logs alpine sh -c 'find /logs/sync/operations -name \"*.json\" -exec tail -5 {} + 2>/dev/null || echo \"No sync operation logs found\"'"
        
        echo
        log_info "Active sync progress files:"
        ssh ${QNAP_HOST} "${docker_cmd} run --rm -v ${PROJECT_NAME}_vast_api_logs:/logs alpine sh -c 'find /logs/sync/progress -name \"*.json\" -exec ls -la {} + 2>/dev/null || echo \"No sync progress files found\"'"
    fi
}

# Function to show help
show_help() {
    echo "Deploy script for vast_api on QNAP"
    echo
    echo "Usage: $0 COMMAND [OPTIONS]"
    echo
    echo "Commands:"
    echo "  git [--branch NAME]       Deploy via git (default: main branch)"
    echo "  up [OPTIONS]              Start containers"
    echo "    --build                 Rebuild containers before starting"
    echo "    --clean                 Stop existing containers first"
    echo "  down                      Stop containers"
    echo "  destroy                   Stop containers and remove volumes"
    echo "  logs [service]            Show logs (optionally for specific service)"
    echo "  app-logs [file]           Show application logs from log_data volume"
    echo "  status                    Show container status"
    echo "  deploy [OPTIONS]          Full deploy: git pull + up"
    echo "    --build                 Rebuild containers"
    echo "    --clean                 Stop existing containers first"
    echo "    --branch NAME           Deploy specific branch (default: main)"
    echo "  help                      Show this help message"
    echo
    echo "Examples:"
    echo "  $0 git                                 # Deploy main branch via git"
    echo "  $0 git --branch develop                # Deploy specific branch via git"
    echo "  $0 up                                  # Start containers"
    echo "  $0 up --build                          # Start containers with rebuild"
    echo "  $0 up --clean                          # Stop existing containers first, then start"
    echo "  $0 up --clean --build                  # Stop, rebuild and start containers"
    echo "  $0 deploy                              # Full deploy: git pull main + up"
    echo "  $0 deploy --build                      # Full deploy with rebuild"
    echo "  $0 deploy --clean                      # Full deploy with clean start"
    echo "  $0 deploy --branch develop --build     # Deploy specific branch with rebuild"
    echo "  $0 logs vast_api                       # Show logs for vast_api service"
    echo "  $0 app-logs                            # Show available app logs and recent entries"
    echo "  $0 app-logs app.log                    # Show specific log file from volume"
    echo "  $0 destroy                             # Destroy all containers and volumes"
    echo
    echo "Note: Git deployment requires QNAP directory mounted at ${MOUNTED_PATH}"
}

# Function to show container status
show_status() {
    local docker_cmd="/share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker"
    log_info "Container status on QNAP:"
    ssh ${QNAP_HOST} "cd ${REMOTE_PATH} && ${docker_cmd} compose ps"
}

# Function for full deployment
full_deploy() {
    local build_flag=""
    local clean_flag=""
    local branch="main"
    
    # Parse arguments for --build, --clean, and --branch
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build)
                build_flag="--build"
                shift
                ;;
            --clean)
                clean_flag="--clean"
                shift
                ;;
            --branch)
                branch="$2"
                shift 2
                ;;
            *)
                # Unknown option, ignore
                shift
                ;;
        esac
    done
    
    log_info "Starting full deployment"
    deploy_via_git "$branch"
    
    # Prepare arguments for docker_up
    local docker_args=()
    [[ -n "$build_flag" ]] && docker_args+=("--build")
    [[ -n "$clean_flag" ]] && docker_args+=("--clean")
    
    docker_up "${docker_args[@]}"
    log_success "Full deployment completed"
}

# Main script logic
case "$1" in
    "git")
        shift
        # Parse --branch argument
        branch="main"
        while [[ $# -gt 0 ]]; do
            case $1 in
                --branch)
                    branch="$2"
                    shift 2
                    ;;
                *)
                    shift
                    ;;
            esac
        done
        deploy_via_git "$branch"
        ;;
    "up")
        shift
        docker_up "$@"
        ;;
    "down")
        docker_down
        ;;
    "destroy")
        docker_destroy
        ;;
    "logs")
        show_logs "$2"
        ;;
    "app-logs")
        show_app_logs "$2"
        ;;
    "status")
        show_status
        ;;
    "deploy")
        shift
        full_deploy "$@"
        ;;
    "help"|"--help"|"-h"|"")
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        echo
        show_help
        exit 1
        ;;
esac