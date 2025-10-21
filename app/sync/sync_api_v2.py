"""
Media Sync API v2 - Enhanced endpoints using the redesigned sync system
"""

import asyncio
import logging
from flask import Blueprint, jsonify, request
from datetime import datetime

from .orchestrator import SyncOrchestrator
from .models import SyncConfig

logger = logging.getLogger(__name__)

# Create Blueprint for v2 API
sync_v2_bp = Blueprint('sync_v2', __name__, url_prefix='/api/v2/sync')

# Global orchestrator instance
_orchestrator = None


def get_orchestrator() -> SyncOrchestrator:
    """Get or create the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SyncOrchestrator()
    return _orchestrator


@sync_v2_bp.route('/start', methods=['POST'])
def start_sync():
    """
    Start a new sync operation.
    
    Request body:
    {
        "source_type": "forge|comfyui|vastai",
        "source_host": "10.0.78.108",
        "source_port": 2222,
        "source_path": "/workspace/stable-diffusion-webui/outputs",
        "dest_path": "/media",
        "folders": ["txt2img-images", "img2img-images"],
        "parallel_transfers": 3,
        "enable_cleanup": true,
        "cleanup_age_hours": 24,
        "cleanup_dry_run": false
    }
    
    Returns:
    {
        "success": true,
        "job_id": "uuid",
        "sync_id": "sync_20251021_120000_abc123",
        "message": "Sync started"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['source_type', 'source_host', 'source_port', 'dest_path']
        for field in required:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Create config
        config = SyncConfig(
            source_type=data['source_type'],
            source_host=data['source_host'],
            source_port=int(data['source_port']),
            source_path=data.get('source_path'),
            dest_path=data['dest_path'],
            folders=data.get('folders', []),
            parallel_transfers=data.get('parallel_transfers', 3),
            enable_cleanup=data.get('enable_cleanup', True),
            cleanup_age_hours=data.get('cleanup_age_hours', 24),
            cleanup_dry_run=data.get('cleanup_dry_run', False),
            generate_xmp=data.get('generate_xmp', True),
            calculate_hashes=data.get('calculate_hashes', False),
            extract_metadata=data.get('extract_metadata', True)
        )
        
        # Start sync
        orchestrator = get_orchestrator()
        
        # Run async operation in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        job = loop.run_until_complete(orchestrator.start_sync(config))
        loop.close()
        
        return jsonify({
            'success': True,
            'job_id': job.id,
            'sync_id': f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{job.id[:8]}",
            'message': 'Sync started successfully'
        })
    
    except Exception as e:
        logger.error(f"Failed to start sync: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sync_v2_bp.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """
    Get status of a sync job.
    
    Returns:
    {
        "success": true,
        "job": {
            "id": "uuid",
            "status": "complete",
            "start_time": "2025-10-21T12:00:00",
            "end_time": "2025-10-21T12:05:00",
            "result": {
                "success": true,
                "files_transferred": 42,
                "bytes_transferred": 1024000,
                "duration": 300.5,
                "errors": []
            }
        }
    }
    """
    try:
        orchestrator = get_orchestrator()
        job = orchestrator.get_job_status(job_id)
        
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        job_dict = {
            'id': job.id,
            'status': job.status,
            'start_time': job.start_time.isoformat(),
            'end_time': job.end_time.isoformat() if job.end_time else None
        }
        
        if job.result:
            job_dict['result'] = {
                'success': job.result.success,
                'files_transferred': job.result.files_transferred,
                'bytes_transferred': job.result.bytes_transferred,
                'duration': job.result.duration,
                'errors': job.result.errors
            }
        
        return jsonify({
            'success': True,
            'job': job_dict
        })
    
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sync_v2_bp.route('/progress/<job_id>', methods=['GET'])
def get_progress(job_id):
    """
    Get real-time progress for a sync job.
    
    Returns:
    {
        "success": true,
        "progress": {
            "sync_id": "sync_20251021_120000_abc123",
            "status": "transferring",
            "progress_percent": 45.5,
            "current_stage": "Transferring folders",
            "current_folder": "txt2img-images",
            "transferred_files": 20,
            "total_files": 44,
            "transferred_bytes": 500000,
            "total_bytes": 1100000,
            "transfer_rate_mbps": 2.5,
            "estimated_time_remaining": 120
        }
    }
    """
    try:
        orchestrator = get_orchestrator()
        job = orchestrator.get_job_status(job_id)
        
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        # Find progress by job_id
        progress = None
        for p in orchestrator.progress_manager._progress_store.values():
            if p.job_id == job_id:
                progress = p
                break
        
        if not progress:
            return jsonify({
                'success': False,
                'error': 'Progress not found'
            }), 404
        
        return jsonify({
            'success': True,
            'progress': progress.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Failed to get progress: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sync_v2_bp.route('/active', methods=['GET'])
def list_active():
    """
    List all active sync jobs.
    
    Returns:
    {
        "success": true,
        "jobs": [...]
    }
    """
    try:
        orchestrator = get_orchestrator()
        active_jobs = orchestrator.list_active_jobs()
        
        jobs_list = []
        for job in active_jobs:
            jobs_list.append({
                'id': job.id,
                'status': job.status,
                'start_time': job.start_time.isoformat(),
                'source_type': job.config.source_type,
                'source_host': job.config.source_host
            })
        
        return jsonify({
            'success': True,
            'jobs': jobs_list,
            'count': len(jobs_list)
        })
    
    except Exception as e:
        logger.error(f"Failed to list active jobs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sync_v2_bp.route('/cancel/<job_id>', methods=['POST'])
def cancel_job(job_id):
    """
    Cancel a running sync job.
    
    Returns:
    {
        "success": true,
        "message": "Job cancelled"
    }
    """
    try:
        orchestrator = get_orchestrator()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        cancelled = loop.run_until_complete(orchestrator.cancel_job(job_id))
        loop.close()
        
        if cancelled:
            return jsonify({
                'success': True,
                'message': 'Job cancelled successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Job not found or already completed'
            }), 404
    
    except Exception as e:
        logger.error(f"Failed to cancel job: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def register_v2_api(app):
    """Register the v2 API blueprint with the Flask app."""
    app.register_blueprint(sync_v2_bp)
    logger.info("Registered Sync API v2")
