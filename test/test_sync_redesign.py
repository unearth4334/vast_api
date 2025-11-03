"""
Tests for the redesigned sync system
"""

import pytest
import asyncio
import os
import tempfile
from datetime import datetime

# Import components to test
from app.sync.models import (
    SyncConfig, SyncProgress, FileManifest, FileStat,
    CleanupConfig, CleanupResult
)
from app.sync.engine.manifest import ManifestManager
from app.sync.progress.progress_manager import ProgressManager


class TestModels:
    """Test data models."""
    
    def test_sync_config_creation(self):
        """Test creating a SyncConfig."""
        config = SyncConfig(
            source_type='forge',
            source_host='10.0.78.108',
            source_port=2222,
            dest_path='/media',
            folders=['txt2img-images']
        )
        
        assert config.source_type == 'forge'
        assert config.source_host == '10.0.78.108'
        assert config.source_port == 2222
        assert config.dest_path == '/media'
        assert config.folders == ['txt2img-images']
        assert config.parallel_transfers == 3  # default
        assert config.enable_cleanup is True  # default
        assert config.cleanup_age_hours == 24  # default
    
    def test_sync_progress_to_dict(self):
        """Test SyncProgress serialization."""
        progress = SyncProgress(
            sync_id='test_sync_123',
            job_id='job_123',
            status='transferring',
            progress_percent=45.5,
            current_stage='Transferring folders'
        )
        
        data = progress.to_dict()
        
        assert data['sync_id'] == 'test_sync_123'
        assert data['job_id'] == 'job_123'
        assert data['status'] == 'transferring'
        assert data['progress_percent'] == 45.5
        assert data['current_stage'] == 'Transferring folders'
        assert 'start_time' in data
    
    def test_file_manifest_needs_sync(self):
        """Test FileManifest.needs_sync logic."""
        manifest = FileManifest(
            path='/test/file.png',
            size=1000,
            mtime=100.0
        )
        
        # Same size and time - no sync needed
        stat1 = FileStat(path='/test/file.png', size=1000, mtime=100.0)
        assert not manifest.needs_sync(stat1)
        
        # Different size - sync needed
        stat2 = FileStat(path='/test/file.png', size=2000, mtime=100.0)
        assert manifest.needs_sync(stat2)
        
        # Newer file - sync needed
        stat3 = FileStat(path='/test/file.png', size=1000, mtime=200.0)
        assert manifest.needs_sync(stat3)


class TestManifestManager:
    """Test ManifestManager."""
    
    def test_manifest_creation(self):
        """Test creating a manifest manager."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            manifest_path = f.name
        
        try:
            manager = ManifestManager(manifest_path)
            assert manager.manifest == {}
            
            # Add a file
            stat = FileStat(path='/test/file.png', size=1000, mtime=100.0)
            manager.update_manifest('/test/file.png', stat)
            
            # Check it was added
            assert '/test/file.png' in manager.manifest
            assert manager.manifest['/test/file.png'].size == 1000
            
            # Create new manager and verify persistence
            manager2 = ManifestManager(manifest_path)
            assert '/test/file.png' in manager2.manifest
            assert manager2.manifest['/test/file.png'].size == 1000
        
        finally:
            if os.path.exists(manifest_path):
                os.unlink(manifest_path)
    
    def test_get_changes(self):
        """Test change detection."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            manifest_path = f.name
        
        try:
            manager = ManifestManager(manifest_path)
            
            # Add existing file to manifest
            stat1 = FileStat(path='/test/file1.png', size=1000, mtime=100.0)
            manager.update_manifest('/test/file1.png', stat1)
            
            # Remote files include:
            # - file1 (unchanged)
            # - file2 (new)
            # - file3 (modified - different size)
            manager.update_manifest('/test/file3.png', FileStat(path='/test/file3.png', size=500, mtime=100.0))
            
            remote_files = [
                FileStat(path='/test/file1.png', size=1000, mtime=100.0),  # unchanged
                FileStat(path='/test/file2.png', size=2000, mtime=200.0),  # new
                FileStat(path='/test/file3.png', size=1500, mtime=150.0),  # modified
            ]
            
            new, modified, deleted = manager.get_changes(remote_files)
            
            assert '/test/file2.png' in new
            assert '/test/file3.png' in modified
            assert len(deleted) == 0
        
        finally:
            if os.path.exists(manifest_path):
                os.unlink(manifest_path)


class TestProgressManager:
    """Test ProgressManager."""
    
    def test_create_progress(self):
        """Test creating progress tracker."""
        manager = ProgressManager()
        
        progress = manager.create_progress('sync_123', 'job_456')
        
        assert progress.sync_id == 'sync_123'
        assert progress.job_id == 'job_456'
        assert progress.status == 'initializing'
        assert progress.progress_percent == 0.0
        
        # Should be retrievable
        retrieved = manager.get_progress('sync_123')
        assert retrieved is not None
        assert retrieved.sync_id == 'sync_123'
    
    def test_update_progress(self):
        """Test updating progress."""
        manager = ProgressManager()
        manager.create_progress('sync_123', 'job_456')
        
        manager.update_progress('sync_123', {
            'status': 'transferring',
            'transferred_bytes': 500000,
            'total_bytes': 1000000
        })
        
        progress = manager.get_progress('sync_123')
        assert progress.status == 'transferring'
        assert progress.transferred_bytes == 500000
        assert progress.total_bytes == 1000000
        assert progress.progress_percent == 50.0
    
    def test_complete_progress(self):
        """Test completing progress."""
        manager = ProgressManager()
        manager.create_progress('sync_123', 'job_456')
        
        manager.complete_progress('sync_123', success=True)
        
        progress = manager.get_progress('sync_123')
        assert progress.status == 'complete'
        assert progress.progress_percent == 100.0
        assert progress.end_time is not None
    
    def test_list_active(self):
        """Test listing active syncs."""
        manager = ProgressManager()
        
        manager.create_progress('sync_1', 'job_1')
        manager.create_progress('sync_2', 'job_2')
        manager.create_progress('sync_3', 'job_3')
        
        # Complete one
        manager.complete_progress('sync_2')
        
        active = manager.list_active()
        assert len(active) == 2
        assert any(p.sync_id == 'sync_1' for p in active)
        assert any(p.sync_id == 'sync_3' for p in active)
        assert not any(p.sync_id == 'sync_2' for p in active)


class TestCleanupConfig:
    """Test cleanup configuration."""
    
    def test_cleanup_config_defaults(self):
        """Test cleanup config defaults."""
        config = CleanupConfig()
        
        assert config.age_hours == 24
        assert config.max_files_per_batch == 100
        assert config.preserve_patterns == []
        assert config.exclude_patterns == []
    
    def test_cleanup_result(self):
        """Test cleanup result."""
        result = CleanupResult(
            files_scanned=100,
            files_deleted=50,
            space_freed_bytes=1024000,
            dry_run=False
        )
        
        assert result.files_scanned == 100
        assert result.files_deleted == 50
        assert result.space_freed_bytes == 1024000
        assert not result.dry_run


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
