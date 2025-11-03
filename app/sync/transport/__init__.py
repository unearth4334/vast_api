"""
Transport adapters for different sync mechanisms
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Callable
from ..models import FileStat, TransferResult


class TransportAdapter(ABC):
    """Abstract base for transport mechanisms."""
    
    @abstractmethod
    async def list_files(self, path: str) -> List[FileStat]:
        """List files at remote path."""
        pass
    
    @abstractmethod
    async def transfer_file(
        self,
        source: str,
        dest: str,
        progress_callback: Optional[Callable] = None
    ) -> TransferResult:
        """Transfer a single file."""
        pass
    
    @abstractmethod
    async def transfer_folder(
        self,
        source: str,
        dest: str,
        progress_callback: Optional[Callable] = None
    ) -> TransferResult:
        """Transfer entire folder."""
        pass
    
    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """Delete a file."""
        pass
    
    @abstractmethod
    async def get_file_stat(self, path: str) -> FileStat:
        """Get file metadata."""
        pass
