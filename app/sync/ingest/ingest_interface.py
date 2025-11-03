"""
Protocol for database ingest implementations
"""

from typing import Protocol, List
from ..models import MediaEventData


class MediaIngestInterface(Protocol):
    """Protocol for database ingest implementations."""
    
    async def on_file_synced(self, event: MediaEventData) -> bool:
        """
        Called when a file is successfully synced.
        
        Args:
            event: Event data containing file information
        
        Returns:
            bool: True if ingestion succeeded, False otherwise
        """
        ...
    
    async def on_batch_synced(self, events: List[MediaEventData]) -> int:
        """
        Called when a batch of files is synced.
        
        Args:
            events: List of event data for synced files
        
        Returns:
            int: Number of successfully ingested files
        """
        ...
    
    async def on_sync_complete(self, sync_id: str, summary: dict) -> bool:
        """
        Called when entire sync operation completes.
        
        Args:
            sync_id: Unique identifier for sync operation
            summary: Summary statistics and metadata
        
        Returns:
            bool: True if post-processing succeeded
        """
        ...
    
    async def verify_file_exists(self, file_path: str) -> bool:
        """
        Verify if file exists in database.
        
        Args:
            file_path: Path to verify
        
        Returns:
            bool: True if file exists in database
        """
        ...
