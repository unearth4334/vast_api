"""
Core sync execution engine
"""

import asyncio
import logging
from typing import Optional, Callable
from datetime import datetime

from ..models import SyncConfig, SyncResult
from ..transport import TransportAdapter
from .manifest import ManifestManager

logger = logging.getLogger(__name__)


class SyncEngine:
    """Core sync execution engine."""
    
    def __init__(self, transport: TransportAdapter, manifest_path: str = None):
        self.transport = transport
        self.manifest = ManifestManager(manifest_path) if manifest_path else None
    
    async def sync_folder(
        self,
        source: str,
        dest: str,
        config: SyncConfig,
        progress_callback: Optional[Callable] = None
    ) -> SyncResult:
        """
        Sync a single folder from source to destination.
        
        Args:
            source: Source folder path
            dest: Destination folder path
            config: Sync configuration
            progress_callback: Function to report progress
        
        Returns:
            SyncResult: Statistics and status of sync operation
        """
        start_time = datetime.now()
        errors = []
        
        try:
            logger.info(f"Starting sync: {source} -> {dest}")
            
            if progress_callback:
                progress_callback({
                    'stage': 'scanning',
                    'message': f'Scanning {source}'
                })
            
            # Use manifest-based change detection if available
            if self.manifest:
                remote_files = await self.transport.list_files(source)
                new_files, modified_files, deleted_files = self.manifest.get_changes(remote_files)
                
                logger.info(f"Manifest analysis: {len(new_files)} new, {len(modified_files)} modified")
                
                # For now, we'll still use rsync for the actual transfer
                # but this gives us intelligence about what changed
                if not new_files and not modified_files:
                    logger.info("No changes detected, skipping transfer")
                    duration = (datetime.now() - start_time).total_seconds()
                    return SyncResult(
                        success=True,
                        files_transferred=0,
                        bytes_transferred=0,
                        duration=duration,
                        errors=[]
                    )
            
            # Perform the transfer
            if progress_callback:
                progress_callback({
                    'stage': 'transferring',
                    'message': f'Transferring {source}'
                })
            
            result = await self.transport.transfer_folder(
                source,
                dest,
                progress_callback=progress_callback
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if result.success:
                logger.info(f"Sync completed: {result.bytes_transferred} bytes in {duration:.2f}s")
                
                # Update manifest if available
                if self.manifest:
                    remote_files = await self.transport.list_files(source)
                    for file_stat in remote_files:
                        self.manifest.update_manifest(file_stat.path, file_stat)
                
                return SyncResult(
                    success=True,
                    files_transferred=1,  # folder count
                    bytes_transferred=result.bytes_transferred,
                    duration=duration,
                    errors=[]
                )
            else:
                errors.append(result.error or "Transfer failed")
                return SyncResult(
                    success=False,
                    files_transferred=0,
                    bytes_transferred=0,
                    duration=duration,
                    errors=errors
                )
        
        except Exception as e:
            logger.error(f"Sync error: {e}")
            errors.append(str(e))
            duration = (datetime.now() - start_time).total_seconds()
            
            return SyncResult(
                success=False,
                files_transferred=0,
                bytes_transferred=0,
                duration=duration,
                errors=errors
            )
    
    async def sync_folders_parallel(
        self,
        folder_pairs: list,
        config: SyncConfig,
        progress_callback: Optional[Callable] = None
    ) -> list:
        """
        Sync multiple folders in parallel.
        
        Args:
            folder_pairs: List of (source, dest) tuples
            config: Sync configuration
            progress_callback: Function to report progress
        
        Returns:
            List of SyncResult objects
        """
        semaphore = asyncio.Semaphore(config.parallel_transfers)
        
        async def sync_with_semaphore(src: str, dest: str):
            async with semaphore:
                return await self.sync_folder(src, dest, config, progress_callback)
        
        tasks = [
            sync_with_semaphore(src, dest)
            for src, dest in folder_pairs
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Sync task {i} failed: {result}")
                processed_results.append(SyncResult(
                    success=False,
                    files_transferred=0,
                    bytes_transferred=0,
                    duration=0,
                    errors=[str(result)]
                ))
            else:
                processed_results.append(result)
        
        return processed_results
