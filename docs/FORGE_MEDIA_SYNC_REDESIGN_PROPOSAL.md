# Forge Media Sync Redesign Proposal

## Executive Summary

This document proposes a comprehensive redesign of the forge media sync tool to improve performance, maintainability, and extensibility. The redesigned system will efficiently synchronize media from Forge and ComfyUI containers to local storage while providing robust progress tracking, logging, and a clear path for database integration.

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Design Goals](#design-goals)
3. [Proposed Architecture](#proposed-architecture)
4. [Core Components](#core-components)
5. [Optimization Strategies](#optimization-strategies)
6. [Progress Tracking & Logging](#progress-tracking--logging)
7. [Old Media Cleanup](#old-media-cleanup)
8. [Extensibility Interface](#extensibility-interface)
9. [Implementation Plan](#implementation-plan)
10. [Testing Strategy](#testing-strategy)

---

## Current State Analysis

### Existing Implementation

The current media sync implementation consists of:

- **sync_api.py**: Flask-based REST API providing sync endpoints
- **sync_utils.py**: Python utilities for orchestrating sync operations
- **sync_outputs.sh**: Bash script performing the actual rsync operations

### Current Features

✅ **Working Well:**
- SSH-based synchronization using rsync
- Support for multiple sync targets (Forge, ComfyUI, VastAI)
- Basic progress tracking via JSON files
- XMP sidecar generation for metadata
- Permission normalization for QNAP compatibility
- Remote cleanup of old media (2-day cutoff)

### Current Limitations

❌ **Areas for Improvement:**
- **Performance**: No incremental change detection beyond rsync
- **Progress Tracking**: Limited granularity, no real-time updates
- **Logging**: Scattered across multiple files, inconsistent formats
- **Cleanup**: Fixed 2-day threshold, runs optionally at end of sync
- **Extensibility**: No clear interface for database integration
- **Error Handling**: Limited retry logic and failure recovery
- **Concurrency**: No parallel folder syncing
- **Metadata**: XMP generation is an afterthought, not integrated

---

## Design Goals

The redesigned system will achieve the following objectives:

### 1. Performance Optimization
- Minimize redundant data transfers through intelligent change detection
- Support parallel synchronization of independent folders
- Utilize rsync efficiently with optimized flags
- Implement manifest-based change tracking

### 2. Robust Progress Tracking
- Real-time progress updates with percentage completion
- Per-folder and per-file granularity
- WebSocket support for live UI updates
- Detailed transfer statistics and estimates

### 3. Comprehensive Logging
- Structured logging with multiple severity levels
- Operation correlation via unique sync IDs
- Searchable log aggregation
- Performance metrics collection

### 4. Intelligent Cleanup
- Configurable age threshold (default >24 hours)
- Run cleanup independently or as part of sync
- Preserve recently modified files regardless of creation date
- Cleanup dry-run mode for safety

### 5. Database Integration Ready
- Well-defined ingest interface specification
- Media metadata extraction hooks
- Event-based notification system
- Transaction-safe operations

### 6. Maintainability
- Modular, testable components
- Clear separation of concerns
- Comprehensive documentation
- Type hints and validation

---

## Proposed Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer (Web UI)                   │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST API / WebSocket
┌───────────────────────▼─────────────────────────────────────┐
│                  Sync Orchestrator                          │
│  - Request validation                                       │
│  - Sync job management                                      │
│  - Progress aggregation                                     │
└───────────┬─────────────────────────┬───────────────────────┘
            │                         │
    ┌───────▼───────┐         ┌───────▼────────┐
    │  Sync Engine  │         │  Cleanup Engine │
    │  - Manifest   │         │  - Age-based    │
    │  - Transfer   │         │  - Configurable │
    │  - Verify     │         │  - Safe delete  │
    └───────┬───────┘         └────────────────┘
            │
    ┌───────▼───────────────────────────────────┐
    │        Transport Adapters                 │
    │  - SSH/Rsync                              │
    │  - Docker Copy                            │
    │  - Local Filesystem                       │
    └───────┬───────────────────────────────────┘
            │
    ┌───────▼───────────────────────────────────┐
    │     Media Processing Pipeline             │
    │  - Metadata extraction                    │
    │  - XMP generation                         │
    │  - Thumbnail creation                     │
    │  - Hash calculation                       │
    └───────┬───────────────────────────────────┘
            │
    ┌───────▼───────────────────────────────────┐
    │      Ingest Interface (Future)            │
    │  - Event notifications                    │
    │  - Database connector                     │
    │  - Batch operations                       │
    └───────────────────────────────────────────┘
```

### Component Overview

1. **Sync Orchestrator**: Central coordinator managing sync jobs
2. **Sync Engine**: Core transfer logic with optimization
3. **Cleanup Engine**: Independent media purging component
4. **Transport Adapters**: Pluggable transfer mechanisms
5. **Media Processing Pipeline**: Post-transfer operations
6. **Ingest Interface**: Future database integration point

---

## Core Components

### 1. Sync Orchestrator

**Purpose**: Manage sync lifecycle and coordinate all operations.

**Responsibilities**:
- Accept and validate sync requests
- Create and track sync jobs
- Aggregate progress from workers
- Handle errors and retries
- Emit events for monitoring

**API Interface**:

```python
class SyncOrchestrator:
    """Central coordinator for media sync operations."""
    
    def start_sync(self, config: SyncConfig) -> SyncJob:
        """
        Initiate a new sync operation.
        
        Args:
            config: Sync configuration including source, destination,
                   filters, and options
        
        Returns:
            SyncJob: Job handle for tracking progress
        """
        pass
    
    def get_job_status(self, job_id: str) -> SyncStatus:
        """Get current status of a sync job."""
        pass
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running sync job."""
        pass
    
    def list_active_jobs(self) -> List[SyncJob]:
        """List all active sync jobs."""
        pass
```

**Configuration Model**:

```python
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
```

### 2. Sync Engine

**Purpose**: Execute actual file transfers with optimization.

**Key Features**:
- **Manifest-based change detection**: Track file states to avoid re-scanning
- **Parallel folder processing**: Process independent folders concurrently
- **Smart rsync usage**: Optimized flags for performance and compatibility
- **Integrity verification**: Optional hash-based verification

**Manifest System**:

```python
@dataclass
class FileManifest:
    """Represents the state of synced files."""
    
    path: str
    size: int
    mtime: float  # modification time
    checksum: Optional[str] = None
    last_sync: datetime = None
    
    def needs_sync(self, remote_stat: FileStat) -> bool:
        """Determine if file needs to be synced."""
        if self.size != remote_stat.size:
            return True
        if self.mtime < remote_stat.mtime:
            return True
        return False
```

**Engine Interface**:

```python
class SyncEngine:
    """Core sync execution engine."""
    
    def __init__(self, transport: TransportAdapter):
        self.transport = transport
        self.manifest = ManifestManager()
    
    async def sync_folder(
        self, 
        source: str, 
        dest: str, 
        config: SyncConfig,
        progress_callback: Callable[[SyncProgress], None]
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
        pass
    
    async def sync_folders_parallel(
        self,
        folder_pairs: List[Tuple[str, str]],
        config: SyncConfig,
        progress_callback: Callable[[SyncProgress], None]
    ) -> List[SyncResult]:
        """Sync multiple folders in parallel."""
        pass
```

### 3. Cleanup Engine

**Purpose**: Independently manage old media deletion.

**Key Features**:
- Configurable age threshold (hours since creation/modification)
- Dry-run mode for safety
- Preserve recently modified files
- Detailed deletion logging
- Whitelist/blacklist support

**Interface**:

```python
class CleanupEngine:
    """Engine for cleaning up old media files."""
    
    def __init__(self, config: CleanupConfig):
        self.config = config
    
    async def cleanup_old_media(
        self,
        target_path: str,
        age_hours: int = 24,
        dry_run: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> CleanupResult:
        """
        Clean up media files older than specified age.
        
        Args:
            target_path: Path to clean (local or remote)
            age_hours: Files older than this will be removed
            dry_run: If True, only report what would be deleted
            progress_callback: Optional progress reporting
        
        Returns:
            CleanupResult: Statistics about cleanup operation
        """
        pass
    
    def scan_for_old_files(
        self,
        path: str,
        age_hours: int
    ) -> List[FileInfo]:
        """Scan and identify files eligible for cleanup."""
        pass
```

**Cleanup Configuration**:

```python
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
    errors: List[str]
    dry_run: bool
```

### 4. Transport Adapters

**Purpose**: Abstract different transfer mechanisms.

**Interface**:

```python
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
        options: TransferOptions,
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
```

**Implementations**:

```python
class SSHRsyncAdapter(TransportAdapter):
    """SSH/Rsync-based transport for remote syncing."""
    pass

class DockerCopyAdapter(TransportAdapter):
    """Docker cp-based transport for local containers."""
    pass

class LocalFilesystemAdapter(TransportAdapter):
    """Local filesystem operations."""
    pass
```

### 5. Media Processing Pipeline

**Purpose**: Process media files after transfer.

**Pipeline Stages**:
1. **Metadata Extraction**: Extract EXIF, PNG chunks, etc.
2. **XMP Generation**: Create sidecar files
3. **Hash Calculation**: Generate content hashes
4. **Thumbnail Creation**: Generate preview images
5. **Validation**: Verify file integrity

**Interface**:

```python
class MediaProcessor:
    """Process media files through multiple stages."""
    
    def __init__(self, pipeline: List[ProcessingStage]):
        self.pipeline = pipeline
    
    async def process_file(
        self,
        file_path: str,
        metadata: Optional[dict] = None
    ) -> ProcessingResult:
        """
        Process a single file through the pipeline.
        
        Args:
            file_path: Path to file to process
            metadata: Optional pre-extracted metadata
        
        Returns:
            ProcessingResult: Aggregated results from all stages
        """
        pass
    
    async def process_batch(
        self,
        file_paths: List[str],
        max_concurrent: int = 4
    ) -> List[ProcessingResult]:
        """Process multiple files concurrently."""
        pass

class ProcessingStage(ABC):
    """Abstract base for processing stages."""
    
    @abstractmethod
    async def process(
        self,
        file_path: str,
        context: ProcessingContext
    ) -> StageResult:
        """Execute this processing stage."""
        pass
```

**Example Stages**:

```python
class XMPGeneratorStage(ProcessingStage):
    """Generate XMP sidecar files."""
    
    async def process(
        self,
        file_path: str,
        context: ProcessingContext
    ) -> StageResult:
        # Extract metadata from PNG/JPEG
        # Generate XMP file
        # Return result
        pass

class HashCalculatorStage(ProcessingStage):
    """Calculate file hashes for deduplication."""
    
    async def process(
        self,
        file_path: str,
        context: ProcessingContext
    ) -> StageResult:
        # Calculate SHA256 hash
        # Store in manifest
        pass
```

---

## Optimization Strategies

### 1. Manifest-Based Change Detection

**Approach**: Maintain a local manifest of synced files to avoid expensive remote scanning.

**Benefits**:
- Reduce SSH round-trips
- Skip unchanged files without rsync
- Track sync history
- Enable incremental syncs

**Implementation**:

```python
class ManifestManager:
    """Manage file manifests for change detection."""
    
    def __init__(self, manifest_path: str):
        self.manifest_path = manifest_path
        self.manifest = self._load_manifest()
    
    def get_changes(
        self,
        remote_files: List[FileStat]
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Compare remote files with manifest.
        
        Returns:
            (new_files, modified_files, deleted_files)
        """
        new_files = []
        modified_files = []
        deleted_files = []
        
        remote_by_path = {f.path: f for f in remote_files}
        
        # Find new and modified files
        for path, stat in remote_by_path.items():
            if path not in self.manifest:
                new_files.append(path)
            elif self.manifest[path].needs_sync(stat):
                modified_files.append(path)
        
        # Find deleted files
        for path in self.manifest:
            if path not in remote_by_path:
                deleted_files.append(path)
        
        return new_files, modified_files, deleted_files
    
    def update_manifest(self, file_path: str, stat: FileStat):
        """Update manifest with new file state."""
        self.manifest[file_path] = FileManifest(
            path=file_path,
            size=stat.size,
            mtime=stat.mtime,
            last_sync=datetime.now()
        )
        self._save_manifest()
```

### 2. Parallel Folder Syncing

**Approach**: Process independent folders concurrently using asyncio.

**Benefits**:
- Better resource utilization
- Faster overall sync time
- Responsive progress updates

**Implementation**:

```python
async def sync_folders_parallel(
    self,
    folder_pairs: List[Tuple[str, str]],
    max_concurrent: int = 3
) -> List[SyncResult]:
    """Sync multiple folders in parallel."""
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def sync_with_semaphore(src: str, dest: str):
        async with semaphore:
            return await self.sync_folder(src, dest, self.config)
    
    tasks = [
        sync_with_semaphore(src, dest)
        for src, dest in folder_pairs
    ]
    
    return await asyncio.gather(*tasks, return_exceptions=True)
```

### 3. Optimized Rsync Flags

**Current Flags Analysis**:
```bash
RSYNC_FLAGS=(-rltD --delete --no-perms --no-owner --no-group 
             --omit-dir-times --no-times --info=stats2 
             --itemize-changes --stats)
```

**Proposed Optimizations**:
```bash
RSYNC_FLAGS=(
    # Basic recursive transfer
    -rlD
    
    # Optimization flags
    --compress                 # Compress during transfer
    --compress-level=6         # Balanced compression
    --whole-file              # Don't use delta transfer (faster for images)
    
    # Incremental sync
    --update                  # Skip files newer on receiver
    --delete-after            # Delete after transfer (safer)
    
    # Performance
    --info=progress2          # Show overall progress
    --info=stats2             # Show statistics
    --itemize-changes         # Detailed change info
    
    # Compatibility (QNAP/eCryptfs)
    --no-perms --no-owner --no-group
    --no-times --omit-dir-times
    
    # Safety
    --partial                 # Keep partial transfers
    --partial-dir=.rsync-tmp  # Store partial files
    
    # Bandwidth (optional)
    --bwlimit=<limit>        # If configured
)
```

### 4. Smart File Filtering

**Approach**: Filter files at source to reduce transfer overhead.

**Filters**:
- File size thresholds
- File type whitelist/blacklist
- Date-based filtering
- Path pattern matching

**Implementation**:

```python
@dataclass
class SyncFilter:
    """Filter configuration for sync operations."""
    
    min_size_bytes: Optional[int] = None
    max_size_bytes: Optional[int] = None
    allowed_extensions: Optional[List[str]] = None
    excluded_patterns: List[str] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)
    min_age_minutes: Optional[int] = None
    
    def should_sync(self, file_stat: FileStat) -> bool:
        """Determine if file should be synced."""
        # Check size
        if self.min_size_bytes and file_stat.size < self.min_size_bytes:
            return False
        if self.max_size_bytes and file_stat.size > self.max_size_bytes:
            return False
        
        # Check extension
        if self.allowed_extensions:
            ext = file_stat.path.suffix.lower()
            if ext not in self.allowed_extensions:
                return False
        
        # Check patterns
        for pattern in self.excluded_patterns:
            if fnmatch.fnmatch(file_stat.path, pattern):
                return False
        
        # Check age
        if self.min_age_minutes:
            age = datetime.now() - file_stat.mtime
            if age.total_seconds() < self.min_age_minutes * 60:
                return False
        
        return True
```

---

## Progress Tracking & Logging

### Real-Time Progress System

**Architecture**:

```
┌─────────────┐
│ Sync Worker │──┐
└─────────────┘  │
                 │    ┌──────────────────┐
┌─────────────┐  ├───▶│ Progress Manager │
│ Sync Worker │──┘    └────────┬─────────┘
└─────────────┘                │
                               │
                        ┌──────▼──────┐
                        │ Progress    │
                        │ Aggregator  │
                        └──────┬──────┘
                               │
                   ┌───────────┼───────────┐
                   │           │           │
            ┌──────▼─────┐ ┌──▼────┐ ┌───▼──────┐
            │ REST API   │ │ WebSkt│ │ Log File │
            └────────────┘ └───────┘ └──────────┘
```

**Progress Model**:

```python
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
    start_time: datetime
    last_update: datetime
    end_time: Optional[datetime] = None
    
    # Errors
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
```

**Progress Manager**:

```python
class ProgressManager:
    """Manage progress tracking for sync operations."""
    
    def __init__(self):
        self._progress_store: Dict[str, SyncProgress] = {}
        self._callbacks: List[Callable] = []
    
    def register_callback(self, callback: Callable[[SyncProgress], None]):
        """Register a callback for progress updates."""
        self._callbacks.append(callback)
    
    def update_progress(self, sync_id: str, updates: dict):
        """Update progress for a sync operation."""
        if sync_id not in self._progress_store:
            raise ValueError(f"Unknown sync_id: {sync_id}")
        
        progress = self._progress_store[sync_id]
        
        # Apply updates
        for key, value in updates.items():
            setattr(progress, key, value)
        
        progress.last_update = datetime.now()
        
        # Calculate derived metrics
        self._update_derived_metrics(progress)
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Progress callback failed: {e}")
    
    def _update_derived_metrics(self, progress: SyncProgress):
        """Calculate derived progress metrics."""
        # Calculate percentage
        if progress.total_bytes > 0:
            progress.progress_percent = (
                progress.transferred_bytes / progress.total_bytes * 100
            )
        
        # Calculate transfer rate
        elapsed = (progress.last_update - progress.start_time).total_seconds()
        if elapsed > 0:
            progress.transfer_rate_mbps = (
                progress.transferred_bytes / elapsed / 1_000_000
            )
        
        # Estimate remaining time
        if progress.transfer_rate_mbps > 0 and progress.total_bytes > 0:
            remaining_bytes = progress.total_bytes - progress.transferred_bytes
            progress.estimated_time_remaining = int(
                remaining_bytes / (progress.transfer_rate_mbps * 1_000_000)
            )
```

### WebSocket Support

**Implementation**:

```python
from flask_socketio import SocketIO, emit

socketio = SocketIO(app, cors_allowed_origins="*")

class WebSocketProgressReporter:
    """Report progress via WebSocket."""
    
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
    
    def report_progress(self, progress: SyncProgress):
        """Emit progress update via WebSocket."""
        self.socketio.emit(
            'sync_progress',
            progress.to_dict(),
            namespace='/sync',
            room=progress.sync_id
        )

# Register WebSocket reporter
ws_reporter = WebSocketProgressReporter(socketio)
progress_manager.register_callback(ws_reporter.report_progress)

@socketio.on('subscribe_progress', namespace='/sync')
def handle_subscribe(data):
    """Client subscribes to progress updates for a sync job."""
    sync_id = data.get('sync_id')
    join_room(sync_id)
    emit('subscribed', {'sync_id': sync_id})
```

### Structured Logging

**Log Levels**:
- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for non-critical issues
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical issues requiring immediate attention

**Log Format**:

```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

# Usage
logger.info(
    "sync_started",
    sync_id=sync_id,
    source=config.source_host,
    destination=config.dest_path,
    folders=config.folders
)

logger.error(
    "transfer_failed",
    sync_id=sync_id,
    file=file_path,
    error=str(error),
    retry_count=retry_count
)
```

**Log Aggregation**:

```python
class LogAggregator:
    """Aggregate and query sync logs."""
    
    def __init__(self, log_dir: str):
        self.log_dir = Path(log_dir)
    
    def get_sync_logs(
        self,
        sync_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        level: Optional[str] = None
    ) -> List[dict]:
        """Query sync logs with filters."""
        pass
    
    def get_sync_summary(self, sync_id: str) -> dict:
        """Get summary statistics for a sync operation."""
        pass
```

---

## Old Media Cleanup

### Cleanup Strategy

The cleanup system will operate independently from the sync process, allowing:
- Scheduled cleanup operations
- On-demand cleanup
- Dry-run mode for safety
- Configurable age thresholds

### Age Determination

**Files are considered "old" based on**:
1. Creation time (primary)
2. Modification time (fallback)
3. Last access time (optional)

**Default threshold**: 24 hours

### Cleanup Process

```python
class CleanupEngine:
    """Engine for cleaning up old media files."""
    
    async def cleanup_old_media(
        self,
        target_config: CleanupTarget,
        dry_run: bool = False
    ) -> CleanupResult:
        """
        Execute cleanup operation.
        
        Process:
        1. Scan for eligible files
        2. Sort by age (oldest first)
        3. Verify files are synced (optional)
        4. Delete in batches
        5. Log each deletion
        """
        result = CleanupResult()
        
        # Scan for old files
        old_files = await self._scan_old_files(
            target_config.path,
            target_config.age_hours
        )
        
        result.files_scanned = len(old_files)
        
        if dry_run:
            result.dry_run = True
            result.files_to_delete = old_files
            return result
        
        # Delete in batches
        for batch in self._batch_files(old_files, target_config.batch_size):
            deleted = await self._delete_batch(batch, target_config)
            result.files_deleted += len(deleted)
            result.space_freed_bytes += sum(f.size for f in deleted)
            
            # Progress callback
            if target_config.progress_callback:
                target_config.progress_callback(result)
        
        return result
    
    async def _scan_old_files(
        self,
        path: str,
        age_hours: int
    ) -> List[FileInfo]:
        """Scan directory for old files."""
        cutoff_time = datetime.now() - timedelta(hours=age_hours)
        old_files = []
        
        # Recursively scan
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = Path(root) / file
                stat = file_path.stat()
                
                # Use creation time or modification time
                file_time = datetime.fromtimestamp(
                    min(stat.st_ctime, stat.st_mtime)
                )
                
                if file_time < cutoff_time:
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
        config: CleanupTarget
    ) -> List[FileInfo]:
        """Delete a batch of files."""
        deleted = []
        
        for file in files:
            try:
                # Verify file is synced (if verification enabled)
                if config.verify_synced:
                    if not await self._verify_synced(file):
                        logger.warning(
                            "file_not_synced",
                            file=file.path,
                            action="skip_deletion"
                        )
                        continue
                
                # Delete file
                os.remove(file.path)
                
                logger.info(
                    "file_deleted",
                    file=file.path,
                    size=file.size,
                    age_hours=(datetime.now() - file.created).total_seconds() / 3600
                )
                
                deleted.append(file)
                
            except Exception as e:
                logger.error(
                    "delete_failed",
                    file=file.path,
                    error=str(e)
                )
        
        return deleted
```

### Cleanup Configuration

```python
@dataclass
class CleanupTarget:
    """Configuration for cleanup target."""
    
    # Target configuration
    path: str
    transport: Optional[TransportAdapter] = None  # For remote cleanup
    
    # Age threshold
    age_hours: int = 24
    
    # Safety options
    verify_synced: bool = True
    preserve_patterns: List[str] = field(default_factory=list)
    
    # Performance
    batch_size: int = 100
    progress_callback: Optional[Callable] = None
```

### Cleanup Scheduling

```python
class CleanupScheduler:
    """Schedule periodic cleanup operations."""
    
    def __init__(self, engine: CleanupEngine):
        self.engine = engine
        self.schedules: Dict[str, CleanupSchedule] = {}
    
    def add_schedule(
        self,
        name: str,
        target: CleanupTarget,
        cron_expression: str
    ):
        """Add a scheduled cleanup job."""
        schedule = CleanupSchedule(
            name=name,
            target=target,
            cron=cron_expression
        )
        self.schedules[name] = schedule
    
    async def run_scheduled(self):
        """Run scheduled cleanup jobs."""
        for name, schedule in self.schedules.items():
            if schedule.should_run():
                logger.info("running_scheduled_cleanup", schedule=name)
                result = await self.engine.cleanup_old_media(
                    schedule.target,
                    dry_run=False
                )
                logger.info(
                    "scheduled_cleanup_complete",
                    schedule=name,
                    files_deleted=result.files_deleted,
                    space_freed=result.space_freed_bytes
                )
```

---

## Extensibility Interface

### Database Ingest Interface Specification

**Purpose**: Provide a well-defined interface for future database integration to ingest synchronized media.

### Event-Based Architecture

```python
from enum import Enum
from typing import Protocol

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
```

### Event Manager

```python
class MediaEventManager:
    """Manage media events and notify subscribers."""
    
    def __init__(self):
        self._subscribers: Dict[MediaEvent, List[MediaIngestInterface]] = {
            event: [] for event in MediaEvent
        }
    
    def subscribe(
        self,
        event_type: MediaEvent,
        subscriber: MediaIngestInterface
    ):
        """Subscribe to specific event type."""
        self._subscribers[event_type].append(subscriber)
    
    async def emit(self, event: MediaEventData):
        """Emit event to all subscribers."""
        subscribers = self._subscribers.get(event.event_type, [])
        
        results = await asyncio.gather(
            *[self._notify_subscriber(sub, event) for sub in subscribers],
            return_exceptions=True
        )
        
        # Log any failures
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "subscriber_notification_failed",
                    event=event.event_type,
                    subscriber=subscribers[i].__class__.__name__,
                    error=str(result)
                )
    
    async def _notify_subscriber(
        self,
        subscriber: MediaIngestInterface,
        event: MediaEventData
    ):
        """Notify a single subscriber."""
        if event.event_type == MediaEvent.FILE_SYNCED:
            return await subscriber.on_file_synced(event)
        elif event.event_type == MediaEvent.BATCH_SYNCED:
            return await subscriber.on_batch_synced([event])
        elif event.event_type == MediaEvent.SYNC_COMPLETE:
            return await subscriber.on_sync_complete(
                event.sync_id,
                event.metadata
            )
```

### Example Database Ingest Implementation

```python
class PostgresMediaIngest(MediaIngestInterface):
    """Example PostgreSQL database ingest implementation."""
    
    def __init__(self, db_connection_string: str):
        self.conn_string = db_connection_string
        self.pool = None
    
    async def initialize(self):
        """Initialize database connection pool."""
        self.pool = await asyncpg.create_pool(self.conn_string)
    
    async def on_file_synced(self, event: MediaEventData) -> bool:
        """Ingest synced file into database."""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    INSERT INTO media_files (
                        sync_id, file_path, file_size, file_hash,
                        metadata, synced_at
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (file_path) DO UPDATE SET
                        file_size = EXCLUDED.file_size,
                        file_hash = EXCLUDED.file_hash,
                        metadata = EXCLUDED.metadata,
                        synced_at = EXCLUDED.synced_at
                ''', 
                    event.sync_id,
                    event.file_path,
                    event.file_size,
                    event.file_hash,
                    json.dumps(event.metadata),
                    event.timestamp
                )
                return True
            except Exception as e:
                logger.error(
                    "db_ingest_failed",
                    file=event.file_path,
                    error=str(e)
                )
                return False
    
    async def on_batch_synced(self, events: List[MediaEventData]) -> int:
        """Batch ingest multiple files."""
        success_count = 0
        
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for event in events:
                    if await self.on_file_synced(event):
                        success_count += 1
        
        return success_count
    
    async def verify_file_exists(self, file_path: str) -> bool:
        """Check if file exists in database."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                'SELECT EXISTS(SELECT 1 FROM media_files WHERE file_path = $1)',
                file_path
            )
            return result
```

### Integration with Sync Engine

```python
class SyncEngine:
    """Enhanced sync engine with event emission."""
    
    def __init__(
        self,
        transport: TransportAdapter,
        event_manager: Optional[MediaEventManager] = None
    ):
        self.transport = transport
        self.event_manager = event_manager or MediaEventManager()
    
    async def sync_file(
        self,
        source: str,
        dest: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """Sync a single file and emit event."""
        # Perform transfer
        result = await self.transport.transfer_file(source, dest)
        
        if result.success:
            # Emit event
            event = MediaEventData(
                event_type=MediaEvent.FILE_SYNCED,
                timestamp=datetime.now(),
                sync_id=self.sync_id,
                file_path=dest,
                file_size=result.bytes_transferred,
                file_hash=result.hash,
                metadata=metadata or {}
            )
            
            await self.event_manager.emit(event)
        
        return result.success
```

### Configuration

```python
@dataclass
class IngestConfig:
    """Configuration for database ingest."""
    
    enabled: bool = False
    implementation: str = "postgres"  # 'postgres', 'mongodb', 'custom'
    connection_string: str = ""
    batch_size: int = 50
    retry_failed: bool = True
    async_mode: bool = True  # Non-blocking ingest
```

---

## Implementation Plan

### Phase 1: Core Refactoring (Weeks 1-2)

**Goals**: Establish new architecture foundation

**Tasks**:
1. ✅ Create new module structure
   - `app/sync/engine/` - Core sync engine
   - `app/sync/cleanup/` - Cleanup engine
   - `app/sync/transport/` - Transport adapters
   - `app/sync/progress/` - Progress tracking
   - `app/sync/ingest/` - Ingest interface

2. ✅ Implement base classes and protocols
   - `TransportAdapter` abstract base
   - `MediaIngestInterface` protocol
   - `SyncConfig` and related models

3. ✅ Port existing functionality
   - Migrate `sync_utils.py` logic to new `SyncEngine`
   - Preserve backward compatibility with existing API

**Deliverables**:
- New module structure
- Base class implementations
- Unit tests for core components

### Phase 2: Sync Engine Enhancement (Weeks 3-4)

**Goals**: Implement optimized sync engine

**Tasks**:
1. ✅ Manifest system
   - Implement `ManifestManager`
   - File state tracking
   - Change detection logic

2. ✅ Parallel sync support
   - Async folder syncing
   - Semaphore-based concurrency control
   - Error handling and retries

3. ✅ Transport adapters
   - `SSHRsyncAdapter` (enhanced from existing)
   - `DockerCopyAdapter` (new)
   - Pluggable architecture

**Deliverables**:
- Working manifest system
- Parallel sync implementation
- Transport adapter suite
- Integration tests

### Phase 3: Progress & Logging (Week 5)

**Goals**: Implement comprehensive progress tracking and logging

**Tasks**:
1. ✅ Progress system
   - `ProgressManager` implementation
   - Real-time updates
   - Percentage calculation
   - ETA estimation

2. ✅ WebSocket support
   - Flask-SocketIO integration
   - Live progress streaming
   - Client subscription model

3. ✅ Structured logging
   - Configure structlog
   - Log aggregation
   - Query interface

**Deliverables**:
- Complete progress tracking system
- WebSocket API
- Structured logging implementation
- API documentation

### Phase 4: Cleanup Engine (Week 6)

**Goals**: Implement independent cleanup functionality

**Tasks**:
1. ✅ Cleanup engine
   - Age-based file scanning
   - Batch deletion
   - Dry-run mode

2. ✅ Remote cleanup support
   - SSH-based cleanup
   - Docker exec cleanup
   - Safe deletion verification

3. ✅ Scheduling support
   - Cron-based scheduling
   - Cleanup job management

**Deliverables**:
- Complete cleanup engine
- Scheduling system
- CLI tool for manual cleanup

### Phase 5: Ingest Interface (Week 7)

**Goals**: Implement database ingest interface

**Tasks**:
1. ✅ Event system
   - `MediaEventManager`
   - Event types and models
   - Subscriber management

2. ✅ Reference implementation
   - Example PostgreSQL ingest
   - Documentation
   - Integration guide

3. ✅ Integration
   - Hook events into sync engine
   - Configuration system
   - Error handling

**Deliverables**:
- Complete ingest interface
- Reference implementation
- Integration documentation

### Phase 6: Testing & Documentation (Week 8)

**Goals**: Comprehensive testing and documentation

**Tasks**:
1. ✅ Unit tests
   - Test all core components
   - Mock external dependencies
   - 80%+ code coverage

2. ✅ Integration tests
   - End-to-end sync tests
   - Cleanup tests
   - Ingest tests

3. ✅ Documentation
   - API documentation
   - User guide
   - Developer guide
   - Migration guide

**Deliverables**:
- Complete test suite
- Comprehensive documentation
- Migration guide from old to new system

### Phase 7: Migration & Deployment (Week 9)

**Goals**: Deploy new system with backward compatibility

**Tasks**:
1. ✅ Backward compatibility layer
   - Maintain existing API endpoints
   - Route to new implementation
   - Feature flags for gradual rollout

2. ✅ Migration tools
   - Manifest migration script
   - Configuration converter
   - Data validation

3. ✅ Deployment
   - Docker image updates
   - Configuration examples
   - Rollback plan

**Deliverables**:
- Deployed new system
- Migration completed
- Performance benchmarks

---

## Testing Strategy

### Unit Tests

**Coverage Areas**:
- Manifest change detection
- Progress calculation
- Cleanup file scanning
- Event emission
- Filter logic

**Example**:

```python
class TestManifestManager:
    """Tests for ManifestManager."""
    
    def test_detect_new_files(self):
        """Test detection of new files."""
        manager = ManifestManager("/tmp/test_manifest")
        
        remote_files = [
            FileStat(path="file1.png", size=1000, mtime=time.time()),
            FileStat(path="file2.png", size=2000, mtime=time.time())
        ]
        
        new, modified, deleted = manager.get_changes(remote_files)
        
        assert len(new) == 2
        assert len(modified) == 0
        assert len(deleted) == 0
    
    def test_detect_modified_files(self):
        """Test detection of modified files."""
        manager = ManifestManager("/tmp/test_manifest")
        
        # Simulate existing file
        manager.manifest["file1.png"] = FileManifest(
            path="file1.png",
            size=1000,
            mtime=time.time() - 100
        )
        
        # Remote file is newer
        remote_files = [
            FileStat(path="file1.png", size=1000, mtime=time.time())
        ]
        
        new, modified, deleted = manager.get_changes(remote_files)
        
        assert len(new) == 0
        assert len(modified) == 1
        assert len(deleted) == 0
```

### Integration Tests

**Coverage Areas**:
- End-to-end sync operations
- Progress tracking accuracy
- Cleanup execution
- Event notification
- Error recovery

**Example**:

```python
@pytest.mark.asyncio
class TestSyncIntegration:
    """Integration tests for sync operations."""
    
    async def test_full_sync_workflow(self, test_containers):
        """Test complete sync workflow."""
        # Setup
        config = SyncConfig(
            source_type="forge",
            source_host="localhost",
            source_port=2222,
            dest_path="/tmp/sync_test",
            folders=["txt2img-images"],
            enable_cleanup=False
        )
        
        orchestrator = SyncOrchestrator()
        
        # Execute sync
        job = await orchestrator.start_sync(config)
        
        # Wait for completion
        while True:
            status = orchestrator.get_job_status(job.id)
            if status.status in ["complete", "failed"]:
                break
            await asyncio.sleep(0.1)
        
        # Verify results
        assert status.status == "complete"
        assert status.transferred_files > 0
        assert Path(config.dest_path).exists()
```

### Performance Tests

**Benchmarks**:
- Sync speed (MB/s)
- Manifest performance
- Progress update latency
- Cleanup speed

**Example**:

```python
class TestPerformance:
    """Performance benchmarks."""
    
    def test_manifest_performance(self, benchmark):
        """Benchmark manifest change detection."""
        manager = ManifestManager("/tmp/perf_test")
        
        # Generate 10,000 files
        remote_files = [
            FileStat(path=f"file{i}.png", size=1000, mtime=time.time())
            for i in range(10000)
        ]
        
        # Benchmark
        result = benchmark(manager.get_changes, remote_files)
        
        # Verify performance
        assert benchmark.stats.stats.mean < 0.1  # < 100ms
```

---

## Appendix

### A. Data Models Reference

```python
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
    errors: List[str]
    
@dataclass
class FileInfo:
    """Detailed file information."""
    path: str
    size: int
    created: datetime
    modified: datetime
    hash: Optional[str] = None
```

### B. Configuration Examples

**Basic Sync Configuration**:

```yaml
sync:
  # Source configuration
  source:
    type: forge  # or 'comfyui', 'vastai'
    host: 10.0.78.108
    port: 2222
  
  # Destination
  destination:
    path: /media
  
  # Folders to sync
  folders:
    - txt2img-images
    - img2img-images
    - WAN
  
  # Performance
  parallel_transfers: 3
  bandwidth_limit_mbps: 100
  
  # Processing
  generate_xmp: true
  calculate_hashes: false
  
  # Cleanup
  cleanup:
    enabled: true
    age_hours: 24
    verify_synced: true
```

**Cleanup Configuration**:

```yaml
cleanup:
  # Targets
  targets:
    - name: forge_local
      path: /media
      age_hours: 24
      
    - name: forge_remote
      type: ssh
      host: 10.0.78.108
      port: 2222
      path: /workspace/stable-diffusion-webui/outputs
      age_hours: 24
  
  # Schedule (cron format)
  schedule: "0 */6 * * *"  # Every 6 hours
  
  # Safety
  dry_run: false
  verify_synced: true
```

**Ingest Configuration**:

```yaml
ingest:
  enabled: true
  implementation: postgres
  connection_string: postgresql://user:pass@localhost/media_db
  
  # Options
  batch_size: 50
  retry_failed: true
  async_mode: true
  
  # Event subscriptions
  events:
    - file_synced
    - batch_synced
    - sync_complete
```

### C. API Reference

**REST Endpoints**:

```
POST /api/v2/sync/start
  - Start new sync operation
  - Body: SyncConfig
  - Returns: SyncJob

GET /api/v2/sync/{job_id}/status
  - Get sync job status
  - Returns: SyncStatus

POST /api/v2/sync/{job_id}/cancel
  - Cancel running sync
  - Returns: {success: bool}

GET /api/v2/sync/active
  - List active sync jobs
  - Returns: List[SyncJob]

POST /api/v2/cleanup/start
  - Start cleanup operation
  - Body: CleanupTarget
  - Returns: CleanupJob

GET /api/v2/cleanup/{job_id}/status
  - Get cleanup job status
  - Returns: CleanupResult
```

**WebSocket Events**:

```
# Subscribe to sync progress
-> subscribe_progress { sync_id: "..." }
<- subscribed { sync_id: "..." }

# Progress updates
<- sync_progress { SyncProgress }

# Completion
<- sync_complete { sync_id: "...", result: SyncResult }

# Errors
<- sync_error { sync_id: "...", error: "..." }
```

### D. Migration Checklist

**Pre-Migration**:
- [ ] Backup existing sync configurations
- [ ] Document current sync schedules
- [ ] Test new system in staging environment
- [ ] Prepare rollback plan

**Migration Steps**:
1. [ ] Install new dependencies
2. [ ] Update configuration files
3. [ ] Run manifest migration script
4. [ ] Enable backward compatibility mode
5. [ ] Test with single sync operation
6. [ ] Gradually migrate sync schedules
7. [ ] Monitor for 48 hours
8. [ ] Disable old system

**Post-Migration**:
- [ ] Verify all syncs working correctly
- [ ] Check progress tracking
- [ ] Validate cleanup operations
- [ ] Review logs for errors
- [ ] Update documentation
- [ ] Train users on new features

---

## Conclusion

This redesign proposal provides a comprehensive roadmap for transforming the forge media sync tool into a robust, performant, and extensible system. The modular architecture ensures maintainability while the well-defined interfaces enable future enhancements like database integration.

**Key Benefits**:
- ⚡ **Faster syncs** through parallel processing and smart change detection
- 📊 **Better visibility** with real-time progress and comprehensive logging
- 🧹 **Automated cleanup** with configurable policies and safety features
- 🔌 **Future-ready** with extensible ingest interface
- 🧪 **Testable** with clear component boundaries

**Next Steps**:
1. Review and approve this proposal
2. Set up development environment
3. Begin Phase 1 implementation
4. Schedule regular check-ins

**Timeline**: 9 weeks from approval to production deployment

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-21  
**Author**: Copilot AI  
**Status**: Draft for Review
