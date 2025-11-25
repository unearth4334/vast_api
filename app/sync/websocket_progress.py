"""
WebSocket support for real-time progress updates
"""

import logging
from flask_socketio import SocketIO, emit, join_room, leave_room
from ..models import SyncProgress

logger = logging.getLogger(__name__)

# Global socketio instance
_socketio = None


def init_socketio(app):
    """Initialize Flask-SocketIO with the app."""
    global _socketio
    _socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    # Register event handlers
    @_socketio.on('subscribe_progress', namespace='/sync')
    def handle_subscribe(data):
        """Client subscribes to progress updates for a sync job."""
        sync_id = data.get('sync_id')
        if sync_id:
            join_room(sync_id)
            emit('subscribed', {'sync_id': sync_id})
            logger.info(f"Client subscribed to sync progress: {sync_id}")
        else:
            emit('error', {'message': 'sync_id required'})
    
    @_socketio.on('unsubscribe_progress', namespace='/sync')
    def handle_unsubscribe(data):
        """Client unsubscribes from progress updates."""
        sync_id = data.get('sync_id')
        if sync_id:
            leave_room(sync_id)
            emit('unsubscribed', {'sync_id': sync_id})
            logger.info(f"Client unsubscribed from sync progress: {sync_id}")
    
    @_socketio.on('connect', namespace='/sync')
    def handle_connect():
        """Client connected."""
        logger.info("Client connected to sync websocket")
        emit('connected', {'message': 'Connected to sync progress stream'})
    
    @_socketio.on('disconnect', namespace='/sync')
    def handle_disconnect():
        """Client disconnected."""
        logger.info("Client disconnected from sync websocket")
    
    # Resource installation progress handlers
    @_socketio.on('subscribe_install', namespace='/resources')
    def handle_subscribe_install(data):
        """Client subscribes to installation progress for a job."""
        job_id = data.get('job_id')
        if job_id:
            join_room(job_id)
            emit('subscribed', {'job_id': job_id})
            logger.info(f"Client subscribed to installation progress: {job_id}")
        else:
            emit('error', {'message': 'job_id required'})
    
    @_socketio.on('unsubscribe_install', namespace='/resources')
    def handle_unsubscribe_install(data):
        """Client unsubscribes from installation progress."""
        job_id = data.get('job_id')
        if job_id:
            leave_room(job_id)
            emit('unsubscribed', {'job_id': job_id})
            logger.info(f"Client unsubscribed from installation progress: {job_id}")
    
    @_socketio.on('connect', namespace='/resources')
    def handle_resource_connect():
        """Client connected to resources namespace."""
        logger.info("Client connected to resource installation websocket")
        emit('connected', {'message': 'Connected to resource installation stream'})
    
    @_socketio.on('disconnect', namespace='/resources')
    def handle_resource_disconnect():
        """Client disconnected from resources namespace."""
        logger.info("Client disconnected from resource installation websocket")
    
    logger.info("Flask-SocketIO initialized")
    return _socketio


def get_socketio():
    """Get the global socketio instance."""
    return _socketio


class WebSocketProgressReporter:
    """Report progress via WebSocket."""
    
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
    
    def report_progress(self, progress: SyncProgress):
        """Emit progress update via WebSocket."""
        if self.socketio:
            try:
                self.socketio.emit(
                    'sync_progress',
                    progress.to_dict(),
                    namespace='/sync',
                    room=progress.sync_id
                )
            except Exception as e:
                logger.error(f"Failed to emit progress via WebSocket: {e}")
