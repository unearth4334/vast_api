"""
Manifest manager for tracking synced files
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

from ..models import FileManifest, FileStat

logger = logging.getLogger(__name__)


class ManifestManager:
    """Manage file manifests for change detection."""
    
    def __init__(self, manifest_path: str):
        self.manifest_path = Path(manifest_path)
        self.manifest: Dict[str, FileManifest] = {}
        self._load_manifest()
    
    def _load_manifest(self):
        """Load manifest from disk."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, 'r') as f:
                    data = json.load(f)
                    
                for path, entry in data.items():
                    self.manifest[path] = FileManifest(
                        path=entry['path'],
                        size=entry['size'],
                        mtime=entry['mtime'],
                        checksum=entry.get('checksum'),
                        last_sync=datetime.fromisoformat(entry['last_sync']) if entry.get('last_sync') else None
                    )
                
                logger.info(f"Loaded manifest with {len(self.manifest)} entries")
            except Exception as e:
                logger.error(f"Failed to load manifest: {e}")
                self.manifest = {}
        else:
            logger.info("No existing manifest found, starting fresh")
            self.manifest = {}
    
    def _save_manifest(self):
        """Save manifest to disk."""
        try:
            # Ensure directory exists
            self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to serializable format
            data = {}
            for path, entry in self.manifest.items():
                data[path] = {
                    'path': entry.path,
                    'size': entry.size,
                    'mtime': entry.mtime,
                    'checksum': entry.checksum,
                    'last_sync': entry.last_sync.isoformat() if entry.last_sync else None
                }
            
            with open(self.manifest_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved manifest with {len(self.manifest)} entries")
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")
    
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
            else:
                manifest_entry = self.manifest[path]
                if manifest_entry.needs_sync(stat):
                    modified_files.append(path)
        
        # Find deleted files (files in manifest but not in remote)
        for path in self.manifest:
            if path not in remote_by_path:
                deleted_files.append(path)
        
        logger.info(f"Changes detected - New: {len(new_files)}, Modified: {len(modified_files)}, Deleted: {len(deleted_files)}")
        
        return new_files, modified_files, deleted_files
    
    def update_manifest(self, file_path: str, stat: FileStat, checksum: str = None):
        """Update manifest with new file state."""
        self.manifest[file_path] = FileManifest(
            path=file_path,
            size=stat.size,
            mtime=stat.mtime,
            checksum=checksum,
            last_sync=datetime.now()
        )
        self._save_manifest()
    
    def remove_from_manifest(self, file_path: str):
        """Remove file from manifest."""
        if file_path in self.manifest:
            del self.manifest[file_path]
            self._save_manifest()
    
    def clear(self):
        """Clear the manifest."""
        self.manifest = {}
        self._save_manifest()
    
    def get_stats(self) -> dict:
        """Get manifest statistics."""
        if not self.manifest:
            return {
                'total_files': 0,
                'total_size': 0,
                'last_sync': None
            }
        
        total_size = sum(entry.size for entry in self.manifest.values())
        last_sync = max((entry.last_sync for entry in self.manifest.values() if entry.last_sync), default=None)
        
        return {
            'total_files': len(self.manifest),
            'total_size': total_size,
            'last_sync': last_sync.isoformat() if last_sync else None
        }
