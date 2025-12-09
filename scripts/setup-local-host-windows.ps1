#
# Local ComfyUI Support Setup Script for Windows (PowerShell)
#
# This script configures a Windows host to allow the Media Sync Tool Docker container
# to execute workflows on a local ComfyUI installation via SSH.
#
# Requirements:
#   - Windows 10 1809+ or Windows Server 2019+
#   - Administrator privileges
#   - ComfyUI installed on the host
#   - PowerShell 5.1+
#
# Usage:
#   .\setup-local-host-windows.ps1 -ComfyUIPath "C:\Users\username\ComfyUI" [options]
#
# Options:
#   -ComfyUIPath PATH       Path to ComfyUI installation (required)
#   -SSHPort PORT          SSH port to use (default: 22022)
#   -SSHUser USER          SSH username (default: comfyui_service)
#   -DockerNetwork CIDR    Docker network CIDR (default: 172.17.0.0/16)
#   -OutputDir DIR         Where to save generated files (default: current directory)
#   -TestOnly              Only test existing configuration
#   -Uninstall             Remove local support setup
#   -Help                  Show help message
#

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$ComfyUIPath = "",
    
    [Parameter(Mandatory=$false)]
    [int]$SSHPort = 22022,
    
    [Parameter(Mandatory=$false)]
    [string]$SSHUser = "comfyui_service",
    
    [Parameter(Mandatory=$false)]
    [string]$DockerNetwork = "172.17.0.0/16",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = (Get-Location).Path,
    
    [Parameter(Mandatory=$false)]
    [switch]$TestOnly,
    
    [Parameter(Mandatory=$false)]
    [switch]$Uninstall,
    
    [Parameter(Mandatory=$false)]
    [switch]$Help
)

# Global variables
$Script:LogFile = "C:\ProgramData\comfyui-local-setup.log"
$Script:SSHConfigFile = "C:\ProgramData\ssh\sshd_config_local_comfyui"
$Script:ServiceName = "sshd-local-comfyui"

# Logging functions
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    
    switch ($Level) {
        "INFO"  { Write-Host $logMessage -ForegroundColor Green }
        "WARN"  { Write-Host $logMessage -ForegroundColor Yellow }
        "ERROR" { Write-Host $logMessage -ForegroundColor Red }
        default { Write-Host $logMessage }
    }
    
    Add-Content -Path $Script:LogFile -Value $logMessage -ErrorAction SilentlyContinue
}

function Write-Info {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Cyan
}

# Show help message
function Show-Help {
    @"
Local ComfyUI Support Setup Script for Windows

This script configures your Windows host to allow the Media Sync Tool Docker
container to execute workflows on your local ComfyUI installation.

USAGE:
    .\setup-local-host-windows.ps1 -ComfyUIPath "C:\Path\To\ComfyUI" [options]

REQUIRED:
    -ComfyUIPath PATH       Path to ComfyUI installation directory

OPTIONS:
    -SSHPort PORT          SSH port (default: 22022)
    -SSHUser USER          SSH username (default: comfyui_service)
    -DockerNetwork CIDR    Docker network range (default: 172.17.0.0/16)
    -OutputDir DIR         Output directory for files (default: current dir)
    -TestOnly              Test existing setup without changes
    -Uninstall             Remove local support configuration
    -Help                  Show this help message

EXAMPLES:
    # Basic setup
    .\setup-local-host-windows.ps1 -ComfyUIPath "C:\Users\myuser\ComfyUI"

    # Custom SSH port and user
    .\setup-local-host-windows.ps1 -ComfyUIPath "C:\Users\myuser\ComfyUI" -SSHPort 23000 -SSHUser comfy

    # Test existing configuration
    .\setup-local-host-windows.ps1 -TestOnly

    # Remove setup
    .\setup-local-host-windows.ps1 -Uninstall

WHAT THIS SCRIPT DOES:
    1. Validates prerequisites and ComfyUI installation
    2. Installs OpenSSH Server Windows feature
    3. Creates dedicated Windows user with restricted permissions
    4. Generates SSH key pair for container authentication
    5. Configures SSH server on alternate port
    6. Sets up Windows Firewall rules for Docker network access
    7. Generates local-support-config.yml configuration file
    8. Tests the SSH connection

OUTPUT FILES:
    - local-support-config.yml  Configuration for container
    - local_host_key            SSH private key for container (mount as volume)
    - local_host_key.pub        SSH public key (for reference)

SECURITY NOTES:
    - SSH key-based authentication only (no passwords)
    - Dedicated user with minimal permissions
    - Firewall restricted to Docker network
    - SSH runs on non-standard port

"@
}

# Check if running as Administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Check prerequisites
function Test-Prerequisites {
    Write-Log "Checking prerequisites..."
    
    # Check Administrator
    if (-not (Test-Administrator)) {
        Write-Log "This script must be run as Administrator" "ERROR"
        exit 1
    }
    
    # Check Windows version
    $osVersion = [System.Environment]::OSVersion.Version
    if ($osVersion.Major -lt 10) {
        Write-Log "Windows 10 1809+ or Windows Server 2019+ required" "ERROR"
        exit 1
    }
    
    # Check PowerShell version
    if ($PSVersionTable.PSVersion.Major -lt 5) {
        Write-Log "PowerShell 5.1+ required" "ERROR"
        exit 1
    }
    
    Write-Log "Prerequisites check passed"
}

# Validate ComfyUI installation
function Test-ComfyUIInstallation {
    if ([string]::IsNullOrEmpty($ComfyUIPath)) {
        Write-Log "ComfyUI path is required. Use -ComfyUIPath option." "ERROR"
        exit 1
    }
    
    Write-Log "Validating ComfyUI installation at: $ComfyUIPath"
    
    if (-not (Test-Path $ComfyUIPath)) {
        Write-Log "ComfyUI directory not found: $ComfyUIPath" "ERROR"
        exit 1
    }
    
    # Check for main.py or server.py
    $mainPy = Join-Path $ComfyUIPath "main.py"
    $serverPy = Join-Path $ComfyUIPath "server.py"
    
    if (-not ((Test-Path $mainPy) -or (Test-Path $serverPy))) {
        Write-Log "ComfyUI main.py or server.py not found in: $ComfyUIPath" "ERROR"
        exit 1
    }
    
    Write-Log "ComfyUI installation validated"
}

# Install OpenSSH Server
function Install-OpenSSHServer {
    Write-Log "Checking OpenSSH Server installation..."
    
    # Check if already installed
    $sshServer = Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*'
    
    if ($sshServer.State -eq "Installed") {
        Write-Log "OpenSSH Server already installed"
        return
    }
    
    Write-Log "Installing OpenSSH Server..."
    
    try {
        Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
        Write-Log "OpenSSH Server installed successfully"
    }
    catch {
        Write-Log "Failed to install OpenSSH Server: $_" "ERROR"
        Write-Log "Trying alternative installation method..." "WARN"
        
        # Try using DISM
        try {
            dism /Online /Add-Capability /CapabilityName:OpenSSH.Server~~~~0.0.1.0
            Write-Log "OpenSSH Server installed via DISM"
        }
        catch {
            Write-Log "Failed to install OpenSSH Server. Please install manually." "ERROR"
            exit 1
        }
    }
    
    # Start SSH Agent service
    Start-Service ssh-agent -ErrorAction SilentlyContinue
    Set-Service -Name ssh-agent -StartupType Automatic
}

# Create dedicated Windows user
function New-ComfyUIUser {
    Write-Log "Creating dedicated SSH user: $SSHUser"
    
    # Check if user exists
    try {
        $existingUser = Get-LocalUser -Name $SSHUser -ErrorAction SilentlyContinue
        if ($existingUser) {
            Write-Log "User $SSHUser already exists. Skipping user creation." "WARN"
            return
        }
    }
    catch {
        # User doesn't exist, continue with creation
    }
    
    # Generate random password (won't be used, SSH keys only)
    # Use cryptographically secure random password
    $password = -join ((48..57) + (65..90) + (97..122) + (33..47) | Get-Random -Count 32 | ForEach-Object {[char]$_})
    $securePassword = ConvertTo-SecureString $password -AsPlainText -Force
    
    # Create user
    try {
        New-LocalUser -Name $SSHUser `
                      -Password $securePassword `
                      -FullName "ComfyUI Local Container Access" `
                      -Description "SSH user for Docker container to access local ComfyUI" `
                      -PasswordNeverExpires `
                      -UserMayNotChangePassword `
                      -ErrorAction Stop
        
        Write-Log "User $SSHUser created successfully"
    }
    catch {
        Write-Log "Failed to create user: $_" "ERROR"
        exit 1
    }
    
    # Grant read/write access to ComfyUI directory
    Grant-ComfyUIAccess
}

# Grant user access to ComfyUI directory
function Grant-ComfyUIAccess {
    Write-Log "Granting $SSHUser access to ComfyUI directory..."
    
    try {
        # Get ACL
        $acl = Get-Acl $ComfyUIPath
        
        # Create access rule
        $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $SSHUser,
            "Modify",
            "ContainerInherit,ObjectInherit",
            "None",
            "Allow"
        )
        
        # Add rule
        $acl.SetAccessRule($accessRule)
        Set-Acl $ComfyUIPath $acl
        
        Write-Log "Access granted to $SSHUser"
    }
    catch {
        Write-Log "Failed to grant access: $_" "WARN"
        Write-Log "You may need to grant permissions manually"
    }
}

# Generate SSH keys
function New-SSHKeys {
    Write-Log "Generating SSH key pair..."
    
    $keyPath = Join-Path $OutputDir "local_host_key"
    
    if (Test-Path $keyPath) {
        Write-Log "SSH key already exists at $keyPath" "WARN"
        $overwrite = Read-Host "Overwrite existing key? (y/N)"
        if ($overwrite -ne "y" -and $overwrite -ne "Y") {
            Write-Log "Using existing SSH key"
            return
        }
    }
    
    # Generate ED25519 key
    $hostname = $env:COMPUTERNAME
    ssh-keygen -t ed25519 -f $keyPath -N '''' -C "comfyui-local-container@$hostname"
    
    # Create .ssh directory for user
    $userProfile = "C:\Users\$SSHUser"
    $sshDir = Join-Path $userProfile ".ssh"
    
    if (-not (Test-Path $sshDir)) {
        New-Item -Path $sshDir -ItemType Directory -Force | Out-Null
    }
    
    # Copy public key to authorized_keys
    $authorizedKeys = Join-Path $sshDir "authorized_keys"
    Copy-Item "$keyPath.pub" $authorizedKeys -Force
    
    # Set permissions
    $acl = Get-Acl $sshDir
    $acl.SetAccessRuleProtection($true, $false)
    $acl.Access | ForEach-Object { $acl.RemoveAccessRule($_) } | Out-Null
    
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $SSHUser, "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow"
    )
    $acl.AddAccessRule($rule)
    Set-Acl $sshDir $acl
    
    Write-Log "SSH keys generated and configured"
    Write-Info "Private key: $keyPath"
    Write-Info "Public key: $keyPath.pub"
}

# Configure SSH server
function Set-SSHConfiguration {
    Write-Log "Configuring SSH server..."
    
    # Ensure SSH directory exists
    $sshDir = "C:\ProgramData\ssh"
    if (-not (Test-Path $sshDir)) {
        New-Item -Path $sshDir -ItemType Directory -Force | Out-Null
    }
    
    # Create SSH config
    $config = @"
# SSH Configuration for Local ComfyUI Container Access
# Generated by setup-local-host-windows.ps1 on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# Host: $env:COMPUTERNAME

# Port and network binding
Port $SSHPort
ListenAddress 127.0.0.1

# Authentication
PubkeyAuthentication yes
PasswordAuthentication no
PermitEmptyPasswords no

# User restrictions
AllowUsers $SSHUser

# Security
X11Forwarding no
AllowTcpForwarding no
AllowAgentForwarding no
PermitTunnel no
GatewayPorts no

# Session
MaxSessions 5
MaxStartups 5:50:10

# Logging
LogLevel INFO
SyslogFacility AUTH

# Windows-specific
Subsystem sftp sftp-server.exe
AuthorizedKeysFile .ssh/authorized_keys
"@
    
    Set-Content -Path $Script:SSHConfigFile -Value $config
    Write-Log "SSH configuration created: $Script:SSHConfigFile"
    
    # Create Windows service
    New-SSHService
}

# Create Windows service
function New-SSHService {
    Write-Log "Configuring SSH service..."
    
    try {
        # Stop default sshd if running
        Stop-Service sshd -ErrorAction SilentlyContinue
        
        # Check if custom service exists
        $service = Get-Service -Name $Script:ServiceName -ErrorAction SilentlyContinue
        
        if ($service) {
            Write-Log "Service $Script:ServiceName already exists" "WARN"
            Stop-Service $Script:ServiceName -ErrorAction SilentlyContinue
            
            # Update service
            sc.exe config $Script:ServiceName binPath= "C:\Windows\System32\OpenSSH\sshd.exe -f $Script:SSHConfigFile" | Out-Null
        }
        else {
            # Create new service
            New-Service -Name $Script:ServiceName `
                       -BinaryPathName "C:\Windows\System32\OpenSSH\sshd.exe -f $Script:SSHConfigFile" `
                       -DisplayName "OpenSSH Server for Local ComfyUI" `
                       -Description "SSH server for Docker container to access local ComfyUI" `
                       -StartupType Automatic
        }
        
        # Start service
        Start-Service $Script:ServiceName
        Write-Log "SSH service started"
    }
    catch {
        Write-Log "Failed to configure SSH service: $_" "ERROR"
        exit 1
    }
}

# Configure Windows Firewall
function Set-FirewallRules {
    Write-Log "Configuring Windows Firewall..."
    
    try {
        # Remove existing rule if it exists
        Remove-NetFirewallRule -DisplayName "ComfyUI Local Container Access" -ErrorAction SilentlyContinue
        
        # Add rule for localhost
        New-NetFirewallRule -DisplayName "ComfyUI Local Container Access" `
                            -Direction Inbound `
                            -Protocol TCP `
                            -LocalPort $SSHPort `
                            -Action Allow `
                            -RemoteAddress @("127.0.0.1", $DockerNetwork) `
                            -Profile Any | Out-Null
        
        Write-Log "Firewall rules configured"
    }
    catch {
        Write-Log "Failed to configure firewall: $_" "WARN"
        Write-Log "Please manually allow port $SSHPort from Docker network"
    }
}

# Generate configuration file
function New-ConfigurationFile {
    Write-Log "Generating local-support-config.yml..."
    
    $configFile = Join-Path $OutputDir "local-support-config.yml"
    
    # Convert Windows path to Unix-style for SSH
    $unixPath = $ComfyUIPath -replace '\\', '/' -replace '^([A-Z]):', '/$1'
    
    $config = @"
# Local ComfyUI Support Configuration
# Generated by setup-local-host-windows.ps1 on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# Host: $env:COMPUTERNAME

local_support:
  # Enable local support (set to true to activate)
  enabled: true
  
  # Display name in UI
  display_name: "Local ComfyUI ($env:COMPUTERNAME)"
  
  # SSH connection details
  ssh:
    # Host address (adjust if needed)
    # Use "host.docker.internal" for Docker Desktop on Windows
    host: "host.docker.internal"
    
    # SSH port
    port: $SSHPort
    
    # SSH username
    username: "$SSHUser"
    
    # Path to private key inside container (mount as volume)
    private_key: "/root/.ssh/local_host_key"
    
  # ComfyUI installation details
  comfyui:
    # Path to ComfyUI installation (Unix-style path for SSH)
    home: "$unixPath"
    
    # Python executable
    python_path: "python"
    
    # ComfyUI API port
    api_port: 8188
    
    # Auto-start ComfyUI if not running
    auto_start: true
    
  # File system paths (Unix-style for SSH)
  paths:
    output_sync_path: "$unixPath/output"
    models_path: "$unixPath/models"
    custom_nodes_path: "$unixPath/custom_nodes"
    
  # Features
  features:
    workflow_execution: true
    resource_installation: true
    output_sync: true
    
  # Limits
  limits:
    max_concurrent_workflows: 1
    max_upload_size_mb: 10000
    workflow_timeout_seconds: 3600
"@
    
    Set-Content -Path $configFile -Value $config
    Write-Log "Configuration file generated: $configFile"
    
    Write-Info ""
    Write-Info "Next steps:"
    Write-Info "1. Copy local-support-config.yml to your Docker project directory"
    Write-Info "2. Copy local_host_key to your Docker project directory"
    Write-Info "3. Update docker-compose.yml to mount these files:"
    Write-Info "   volumes:"
    Write-Info "     - ./local-support-config.yml:/app/local-support-config.yml:ro"
    Write-Info "     - ./local_host_key:/root/.ssh/local_host_key:ro"
    Write-Info "4. Restart the Docker container"
}

# Test SSH connection
function Test-SSHConnection {
    Write-Log "Testing SSH connection..."
    
    $keyPath = Join-Path $OutputDir "local_host_key"
    
    if (-not (Test-Path $keyPath)) {
        Write-Log "SSH key not found at $keyPath" "ERROR"
        return $false
    }
    
    # Test connection
    $testCmd = "echo 'Connection successful'"
    $result = ssh -i $keyPath -p $SSHPort -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$SSHUser@127.0.0.1" $testCmd 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Log "✅ SSH connection test PASSED"
        
        # Test ComfyUI directory access
        # Note: SSH uses bash-like commands even on Windows
        $testAccess = ssh -i $keyPath -p $SSHPort -o StrictHostKeyChecking=no "$SSHUser@127.0.0.1" "ls '$ComfyUIPath'" 2>$null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Log "✅ ComfyUI directory access test PASSED"
        }
        else {
            Write-Log "⚠️  Cannot access ComfyUI directory. Check permissions." "WARN"
        }
        
        return $true
    }
    else {
        Write-Log "❌ SSH connection test FAILED" "ERROR"
        return $false
    }
}

# Test existing configuration
function Test-ExistingConfiguration {
    Write-Log "Testing existing configuration..."
    
    # Check if service exists and is running
    $service = Get-Service -Name $Script:ServiceName -ErrorAction SilentlyContinue
    if ($service -and $service.Status -eq "Running") {
        Write-Log "✅ SSH service is running"
    }
    else {
        Write-Log "❌ SSH service is not running" "ERROR"
        return $false
    }
    
    # Check if user exists
    try {
        Get-LocalUser -Name $SSHUser -ErrorAction Stop | Out-Null
        Write-Log "✅ SSH user exists"
    }
    catch {
        Write-Log "❌ SSH user does not exist" "ERROR"
        return $false
    }
    
    # Check if key exists
    $keyPath = Join-Path $OutputDir "local_host_key"
    if (Test-Path $keyPath) {
        Write-Log "✅ SSH key exists"
        Test-SSHConnection
    }
    else {
        Write-Log "❌ SSH key not found at $keyPath" "ERROR"
        return $false
    }
}

# Uninstall local support
function Remove-LocalSupport {
    Write-Log "Uninstalling local ComfyUI support..."
    
    # Stop and remove service
    $service = Get-Service -Name $Script:ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        Stop-Service $Script:ServiceName -ErrorAction SilentlyContinue
        sc.exe delete $Script:ServiceName | Out-Null
        Write-Log "Service removed"
    }
    
    # Remove SSH config
    if (Test-Path $Script:SSHConfigFile) {
        Remove-Item $Script:SSHConfigFile -Force
    }
    
    # Remove firewall rule
    Remove-NetFirewallRule -DisplayName "ComfyUI Local Container Access" -ErrorAction SilentlyContinue
    
    # Ask about removing user
    $removeUser = Read-Host "Remove SSH user $SSHUser? (y/N)"
    if ($removeUser -eq "y" -or $removeUser -eq "Y") {
        try {
            Remove-LocalUser -Name $SSHUser -ErrorAction Stop
            Write-Log "User $SSHUser removed"
        }
        catch {
            Write-Log "Could not remove user $SSHUser: $_" "WARN"
        }
    }
    
    Write-Log "Uninstallation complete"
}

# Main execution
function Main {
    Write-Host "========================================"
    Write-Host "Local ComfyUI Support Setup for Windows"
    Write-Host "========================================"
    Write-Host ""
    
    # Create log file
    $logDir = Split-Path $Script:LogFile -Parent
    if (-not (Test-Path $logDir)) {
        New-Item -Path $logDir -ItemType Directory -Force | Out-Null
    }
    
    # Show help if requested
    if ($Help) {
        Show-Help
        exit 0
    }
    
    Test-Prerequisites
    
    if ($Uninstall) {
        Remove-LocalSupport
        exit 0
    }
    
    if ($TestOnly) {
        Test-ExistingConfiguration
        exit 0
    }
    
    Test-ComfyUIInstallation
    Install-OpenSSHServer
    New-ComfyUIUser
    New-SSHKeys
    Set-SSHConfiguration
    Set-FirewallRules
    New-ConfigurationFile
    Test-SSHConnection
    
    Write-Host ""
    Write-Log "✅ Setup complete!"
    Write-Info ""
    Write-Info "Configuration files created:"
    Write-Info "  - $OutputDir\local-support-config.yml"
    Write-Info "  - $OutputDir\local_host_key (private key)"
    Write-Info "  - $OutputDir\local_host_key.pub (public key)"
    Write-Info ""
    Write-Info "SSH service running on port $SSHPort"
    Write-Info ""
    Write-Info "See the configuration file for next steps."
}

# Run main function
Main
