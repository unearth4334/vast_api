"""
Workflow History Manager
Handles saving and retrieving workflow execution history with metadata
"""

import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
import os

logger = logging.getLogger(__name__)

# History storage directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
HISTORY_DIR = Path(os.path.join(BASE_DIR, 'data', 'workflow_history'))
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


class WorkflowHistory:
    """Manager for workflow execution history"""
    
    @staticmethod
    def compute_workflow_hash(workflow_id: str) -> str:
        """
        Compute MD5 hash of the webui.yml file for a workflow
        
        Args:
            workflow_id: Workflow identifier (e.g., "IMG_to_VIDEO")
            
        Returns:
            MD5 hash of the workflow file
        """
        try:
            workflow_dir = Path(os.path.join(BASE_DIR, 'workflows'))
            workflow_file = workflow_dir / f"{workflow_id}.webui.yml"
            
            if not workflow_file.exists():
                logger.warning(f"Workflow file not found: {workflow_file}")
                return ""
            
            # Read file content and compute hash
            content = workflow_file.read_bytes()
            hash_md5 = hashlib.md5(content)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Error computing workflow hash: {e}", exc_info=True)
            return ""
    
    @staticmethod
    def save_history_record(
        workflow_id: str,
        inputs: Dict[str, Any],
        thumbnail: Optional[str] = None,
        prompt_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> str:
        """
        Save a workflow execution to history
        
        Args:
            workflow_id: Workflow identifier
            inputs: Form inputs that were submitted
            thumbnail: Thumbnail filename (if available)
            prompt_id: ComfyUI prompt ID
            task_id: Internal task ID
            
        Returns:
            History record ID
        """
        try:
            # Generate record ID
            record_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            
            # Compute workflow hash
            workflow_hash = WorkflowHistory.compute_workflow_hash(workflow_id)
            
            # Create record
            record = {
                'record_id': record_id,
                'workflow_id': workflow_id,
                'workflow_hash': workflow_hash,
                'timestamp': datetime.now().isoformat(),
                'inputs': inputs,
                'thumbnail': thumbnail,
                'prompt_id': prompt_id,
                'task_id': task_id
            }
            
            # Save to file
            record_file = HISTORY_DIR / f"{record_id}.json"
            with open(record_file, 'w') as f:
                json.dump(record, f, indent=2)
            
            logger.info(f"Saved history record: {record_id}")
            return record_id
            
        except Exception as e:
            logger.error(f"Error saving history record: {e}", exc_info=True)
            raise
    
    @staticmethod
    def get_history_records(
        workflow_id: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve history records with optional filtering and pagination
        
        Args:
            workflow_id: Optional workflow ID to filter by
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of history records, sorted by timestamp (newest first)
        """
        try:
            # Get current workflow hash if filtering by workflow_id
            target_hash = None
            if workflow_id:
                target_hash = WorkflowHistory.compute_workflow_hash(workflow_id)
            
            # Load all history records
            records = []
            for record_file in HISTORY_DIR.glob("*.json"):
                try:
                    with open(record_file, 'r') as f:
                        record = json.load(f)
                    
                    # Filter by workflow hash if specified
                    if target_hash and record.get('workflow_hash') != target_hash:
                        continue
                    
                    records.append(record)
                except Exception as e:
                    logger.warning(f"Error loading record {record_file}: {e}")
                    continue
            
            # Sort by timestamp (newest first)
            records.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Apply pagination
            paginated_records = records[offset:offset + limit]
            
            logger.info(f"Retrieved {len(paginated_records)} history records (offset={offset}, limit={limit})")
            return paginated_records
            
        except Exception as e:
            logger.error(f"Error retrieving history records: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_history_record(record_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific history record by ID
        
        Args:
            record_id: Record ID
            
        Returns:
            History record or None if not found
        """
        try:
            record_file = HISTORY_DIR / f"{record_id}.json"
            
            if not record_file.exists():
                logger.warning(f"History record not found: {record_id}")
                return None
            
            with open(record_file, 'r') as f:
                record = json.load(f)
            
            return record
            
        except Exception as e:
            logger.error(f"Error retrieving history record: {e}", exc_info=True)
            return None
    
    @staticmethod
    def count_history_records(workflow_id: Optional[str] = None) -> int:
        """
        Count total history records, optionally filtered by workflow
        
        Args:
            workflow_id: Optional workflow ID to filter by
            
        Returns:
            Count of matching records
        """
        try:
            # Get current workflow hash if filtering
            target_hash = None
            if workflow_id:
                target_hash = WorkflowHistory.compute_workflow_hash(workflow_id)
            
            count = 0
            for record_file in HISTORY_DIR.glob("*.json"):
                try:
                    if target_hash:
                        with open(record_file, 'r') as f:
                            record = json.load(f)
                        if record.get('workflow_hash') == target_hash:
                            count += 1
                    else:
                        count += 1
                except Exception as e:
                    logger.warning(f"Error reading record {record_file}: {e}")
                    continue
            
            return count
            
        except Exception as e:
            logger.error(f"Error counting history records: {e}", exc_info=True)
            return 0
