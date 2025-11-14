"""
SSH/Rsync transport adapter
"""

import asyncio
import subprocess
import os
import logging
from typing import List, Optional, Callable
from datetime import datetime

from . import TransportAdapter
from ..models import FileStat, TransferResult

logger = logging.getLogger(__name__)


class SSHRsyncAdapter(TransportAdapter):
    """SSH/Rsync-based transport for remote syncing."""
    
    def __init__(self, host: str, port: int, user: str = "root"):
        self.host = host
        self.port = port
        self.user = user
        self.ssh_key = os.path.expanduser("~/.ssh/id_ed25519")
    
    async def list_files(self, path: str) -> List[FileStat]:
        """List files at remote path using SSH."""
        cmd = [
            "ssh",
            "-p", str(self.port),
            "-i", self.ssh_key,
            f"{self.user}@{self.host}",
            f"find {path} -type f -printf '%p|%s|%T@\\n'"
        ]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                logger.error(f"SSH list failed: {stderr.decode()}")
                return []
            
            files = []
            for line in stdout.decode().splitlines():
                if not line.strip():
                    continue
                parts = line.split('|')
                if len(parts) >= 3:
                    files.append(FileStat(
                        path=parts[0],
                        size=int(parts[1]),
                        mtime=float(parts[2])
                    ))
            
            return files
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    async def transfer_file(
        self,
        source: str,
        dest: str,
        progress_callback: Optional[Callable] = None
    ) -> TransferResult:
        """Transfer a single file using rsync."""
        start_time = datetime.now()
        
        cmd = [
            "rsync",
            "-avz",
            "-e", f"ssh -p {self.port} -i {self.ssh_key}",
            f"{self.user}@{self.host}:{source}",
            dest
        ]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if proc.returncode == 0:
                # Get file size
                size = os.path.getsize(dest) if os.path.exists(dest) else 0
                
                return TransferResult(
                    success=True,
                    bytes_transferred=size,
                    duration=duration
                )
            else:
                return TransferResult(
                    success=False,
                    bytes_transferred=0,
                    duration=duration,
                    error=stderr.decode()
                )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return TransferResult(
                success=False,
                bytes_transferred=0,
                duration=duration,
                error=str(e)
            )
    
    async def transfer_folder(
        self,
        source: str,
        dest: str,
        progress_callback: Optional[Callable] = None
    ) -> TransferResult:
        """Transfer entire folder using rsync."""
        start_time = datetime.now()
        
        # Optimized rsync flags
        cmd = [
            "rsync",
            "-rlD",  # recursive, links, devices
            "--compress",
            "--compress-level=6",
            "--whole-file",
            "--update",
            "--delete-after",
            "--info=progress2",
            "--info=stats2",
            "--itemize-changes",
            "--no-perms", "--no-owner", "--no-group",
            "--times",  # preserve modification times from remote files
            "--partial",
            "--partial-dir=.rsync-tmp",
            "-e", f"ssh -p {self.port} -i {self.ssh_key} -o StrictHostKeyChecking=no",
            f"{self.user}@{self.host}:{source}/",
            dest
        ]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if proc.returncode == 0:
                # Parse rsync output for statistics
                output = stdout.decode()
                bytes_transferred = self._parse_rsync_bytes(output)
                
                return TransferResult(
                    success=True,
                    bytes_transferred=bytes_transferred,
                    duration=duration
                )
            else:
                return TransferResult(
                    success=False,
                    bytes_transferred=0,
                    duration=duration,
                    error=stderr.decode()
                )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Transfer error: {e}")
            return TransferResult(
                success=False,
                bytes_transferred=0,
                duration=duration,
                error=str(e)
            )
    
    async def delete_file(self, path: str) -> bool:
        """Delete a file via SSH."""
        cmd = [
            "ssh",
            "-p", str(self.port),
            "-i", self.ssh_key,
            f"{self.user}@{self.host}",
            f"rm -f {path}"
        ]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            return proc.returncode == 0
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    async def get_file_stat(self, path: str) -> FileStat:
        """Get file metadata via SSH."""
        cmd = [
            "ssh",
            "-p", str(self.port),
            "-i", self.ssh_key,
            f"{self.user}@{self.host}",
            f"stat -c '%s|%Y' {path}"
        ]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                parts = stdout.decode().strip().split('|')
                if len(parts) >= 2:
                    return FileStat(
                        path=path,
                        size=int(parts[0]),
                        mtime=float(parts[1])
                    )
            
            raise Exception(f"Failed to get file stat: {stderr.decode()}")
        except Exception as e:
            logger.error(f"Error getting file stat: {e}")
            raise
    
    def _parse_rsync_bytes(self, output: str) -> int:
        """Parse bytes transferred from rsync output."""
        import re
        
        # Look for "total size is X"
        match = re.search(r'total size is ([\d,]+)', output)
        if match:
            return int(match.group(1).replace(',', ''))
        
        return 0
