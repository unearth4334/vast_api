@echo off
REM Local ComfyUI Support Setup Script for Windows
REM
REM This script configures a Windows host to allow the Media Sync Tool Docker container
REM to execute workflows on a local ComfyUI installation via SSH.
REM
REM Requirements:
REM   - Windows 10 1809+ or Windows Server 2019+
REM   - Administrator privileges
REM   - ComfyUI installed on the host
REM   - PowerShell 5.1+
REM
REM Usage:
REM   Run this batch file as Administrator
REM   It will launch the PowerShell setup script
REM

REM Check for admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo This script requires Administrator privileges.
    echo Please right-click and select "Run as Administrator"
    pause
    exit /b 1
)

REM Launch PowerShell script
powershell -ExecutionPolicy Bypass -File "%~dp0setup-local-host-windows.ps1" %*
