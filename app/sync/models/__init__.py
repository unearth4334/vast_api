"""
Data models for sync operations
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


@dataclass
class SyncConfig:
    """Configuration for a sync operation."""
    
    # Source configuration
    source_type: str  # 'forge', 'comfyui', 'vastai', etc.
    source_host: str
    source_port: int
    source_path: Optional[str] = None
    
    # Destination configuration
    dest_path: str
    
    # Sync options
    folders: List[str] = field(default_factory=list)
    parallel_transfers: int = 3
    bandwidth_limit_mbps: Optional[int] = None
    
    # Cleanup options
    enable_cleanup: bool = True
    cleanup_age_hours: int = 24
    cleanup_dry_run: bool = False
    
    # Processing options
    generate_xmp: bool = True
    calculate_hashes: bool = False
    extract_metadata: bool = True
    
    # Advanced options
    retry_attempts: int = 3
    retry_delay_seconds: int = 5
    verify_transfers: bool = True


@dataclass
class FileStat:
    """File metadata."""
    path: str
    size: int
    mtime: float
    ctime: Optional[float] = None


@dataclass
class TransferResult:
    """Result of file transfer."""
    success: bool
    bytes_transferred: int
    duration: float
    hash: Optional[str] = None
    error: Optional[str] = None


@dataclass
class SyncResult:
    """Result of sync operation."""
    success: bool
    files_transferred: int
    bytes_transferred: int
    duration: float
    errors: List[str] = field(default_factory=list)


@dataclass
class FileManifest:
    """Represents the state of synced files."""
    
    path: str
    size: int
    mtime: float  # modification time
    checksum: Optional[str] = None
    last_sync: Optional[datetime] = None
    
    def needs_sync(self, remote_stat: FileStat) -> bool:
        """Determine if file needs to be synced."""
        if self.size != remote_stat.size:
            return True
        if self.mtime < remote_stat.mtime:
            return True
        return False


@dataclass
class SyncProgress:
    """Real-time sync progress information."""
    
    # Identification
    sync_id: str
    job_id: str
    
    # Overall progress
    status: str  # 'initializing', 'scanning', 'transferring', 'processing', 'complete', 'failed'
    progress_percent: float  # 0.0 to 100.0
    
    # Current operation
    current_stage: str
    current_folder: Optional[str] = None
    current_file: Optional[str] = None
    
    # Statistics
    total_folders: int = 0
    completed_folders: int = 0
    total_files: int = 0
    transferred_files: int = 0
    total_bytes: int = 0
    transferred_bytes: int = 0
    
    # Performance
    transfer_rate_mbps: float = 0.0
    estimated_time_remaining: Optional[int] = None  # seconds
    
    # Timing
    start_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    # Errors
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'sync_id': self.sync_id,
            'job_id': self.job_id,
            'status': self.status,
            'progress_percent': self.progress_percent,
            'current_stage': self.current_stage,
            'current_folder': self.current_folder,
            'current_file': self.current_file,
            'total_folders': self.total_folders,
            'completed_folders': self.completed_folders,
            'total_files': self.total_files,
            'transferred_files': self.transferred_files,
            'total_bytes': self.total_bytes,
            'transferred_bytes': self.transferred_bytes,
            'transfer_rate_mbps': self.transfer_rate_mbps,
            'estimated_time_remaining': self.estimated_time_remaining,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'errors': self.errors,
            'warnings': self.warnings,
        }


@dataclass
class CleanupConfig:
    """Configuration for cleanup operations."""
    
    age_hours: int = 24
    preserve_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    min_free_space_gb: Optional[int] = None  # Force cleanup if space low
    max_files_per_batch: int = 100


@dataclass
class CleanupResult:
    """Result of cleanup operation."""
    
    files_scanned: int
    files_deleted: int
    space_freed_bytes: int
    errors: List[str] = field(default_factory=list)
    dry_run: bool = False


@dataclass
class FileInfo:
    """Detailed file information."""
    path: str
    size: int
    created: datetime
    modified: datetime
    hash: Optional[str] = None


class MediaEvent(Enum):
    """Media lifecycle events."""
    FILE_SYNCED = "file_synced"
    FILE_PROCESSED = "file_processed"
    FILE_DELETED = "file_deleted"
    BATCH_SYNCED = "batch_synced"
    SYNC_COMPLETE = "sync_complete"


@dataclass
class MediaEventData:
    """Data associated with a media event."""
    
    event_type: MediaEvent
    timestamp: datetime
    sync_id: str
    
    # File information
    file_path: str
    file_size: int
    file_hash: Optional[str] = None
    
    # Metadata
    metadata: dict = field(default_factory=dict)
    
    # Processing results
    xmp_path: Optional[str] = None
    thumbnail_path: Optional[str] = None


@dataclass
class SyncJob:
    """Represents a sync job."""
    id: str
    config: SyncConfig
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    result: Optional[SyncResult] = None
