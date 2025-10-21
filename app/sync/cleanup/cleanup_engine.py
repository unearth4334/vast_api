"""
Engine for cleaning up old media files
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, List
from pathlib import Path

from ..models import CleanupConfig, CleanupResult, FileInfo
from ..transport import TransportAdapter

logger = logging.getLogger(__name__)


class CleanupEngine:
    """Engine for cleaning up old media files."""
    
    def __init__(self, config: CleanupConfig = None):
        self.config = config or CleanupConfig()
    
    async def cleanup_old_media(
        self,
        target_path: str,
        age_hours: int = 24,
        dry_run: bool = False,
        transport: Optional[TransportAdapter] = None,
        progress_callback: Optional[Callable] = None
    ) -> CleanupResult:
        """
        Clean up media files older than specified age.
        
        Args:
            target_path: Path to clean (local or remote)
            age_hours: Files older than this will be removed
            dry_run: If True, only report what would be deleted
            transport: Optional transport adapter for remote cleanup
            progress_callback: Optional progress reporting
        
        Returns:
            CleanupResult: Statistics about cleanup operation
        """
        result = CleanupResult(
            files_scanned=0,
            files_deleted=0,
            space_freed_bytes=0,
            dry_run=dry_run
        )
        
        try:
            logger.info(f"Starting cleanup: path={target_path}, age={age_hours}h, dry_run={dry_run}")
            
            # Scan for old files
            old_files = await self._scan_old_files(target_path, age_hours, transport)
            result.files_scanned = len(old_files)
            
            logger.info(f"Found {len(old_files)} files older than {age_hours} hours")
            
            if dry_run:
                # Just report what would be deleted
                for file in old_files:
                    logger.info(f"Would delete: {file.path} ({file.size} bytes)")
                    result.space_freed_bytes += file.size
                return result
            
            # Delete files in batches
            batch_size = self.config.max_files_per_batch
            for i in range(0, len(old_files), batch_size):
                batch = old_files[i:i + batch_size]
                deleted = await self._delete_batch(batch, transport)
                
                result.files_deleted += len(deleted)
                result.space_freed_bytes += sum(f.size for f in deleted)
                
                if progress_callback:
                    progress_callback({
                        'files_scanned': result.files_scanned,
                        'files_deleted': result.files_deleted,
                        'space_freed': result.space_freed_bytes
                    })
            
            logger.info(f"Cleanup complete: deleted {result.files_deleted} files, freed {result.space_freed_bytes} bytes")
            
            return result
        
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            result.errors.append(str(e))
            return result
    
    async def _scan_old_files(
        self,
        path: str,
        age_hours: int,
        transport: Optional[TransportAdapter] = None
    ) -> List[FileInfo]:
        """Scan directory for old files."""
        cutoff_time = datetime.now() - timedelta(hours=age_hours)
        old_files = []
        
        if transport:
            # Remote scanning via transport
            files = await transport.list_files(path)
            
            for file_stat in files:
                file_time = datetime.fromtimestamp(file_stat.mtime)
                if file_time < cutoff_time:
                    # Check against exclude patterns
                    if self._should_preserve(file_stat.path):
                        continue
                    
                    old_files.append(FileInfo(
                        path=file_stat.path,
                        size=file_stat.size,
                        created=file_time,
                        modified=file_time
                    ))
        else:
            # Local scanning
            path_obj = Path(path)
            if not path_obj.exists():
                logger.warning(f"Path does not exist: {path}")
                return []
            
            for file_path in path_obj.rglob('*'):
                if not file_path.is_file():
                    continue
                
                stat = file_path.stat()
                file_time = datetime.fromtimestamp(min(stat.st_ctime, stat.st_mtime))
                
                if file_time < cutoff_time:
                    # Check against exclude patterns
                    if self._should_preserve(str(file_path)):
                        continue
                    
                    old_files.append(FileInfo(
                        path=str(file_path),
                        size=stat.st_size,
                        created=datetime.fromtimestamp(stat.st_ctime),
                        modified=datetime.fromtimestamp(stat.st_mtime)
                    ))
        
        return old_files
    
    async def _delete_batch(
        self,
        files: List[FileInfo],
        transport: Optional[TransportAdapter] = None
    ) -> List[FileInfo]:
        """Delete a batch of files."""
        deleted = []
        
        for file in files:
            try:
                if transport:
                    # Remote deletion
                    success = await transport.delete_file(file.path)
                else:
                    # Local deletion
                    import os
                    os.remove(file.path)
                    success = True
                
                if success:
                    logger.info(f"Deleted: {file.path} ({file.size} bytes)")
                    deleted.append(file)
                else:
                    logger.warning(f"Failed to delete: {file.path}")
            
            except Exception as e:
                logger.error(f"Error deleting {file.path}: {e}")
        
        return deleted
    
    def _should_preserve(self, file_path: str) -> bool:
        """Check if file should be preserved based on patterns."""
        import fnmatch
        
        # Check preserve patterns
        for pattern in self.config.preserve_patterns:
            if fnmatch.fnmatch(file_path, pattern):
                logger.debug(f"Preserving {file_path} (matches {pattern})")
                return True
        
        # Check exclude patterns
        for pattern in self.config.exclude_patterns:
            if fnmatch.fnmatch(file_path, pattern):
                logger.debug(f"Excluding {file_path} (matches {pattern})")
                return True
        
        return False
