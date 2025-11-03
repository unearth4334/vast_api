"""
Event manager for media events
"""

import asyncio
import logging
from typing import Dict, List
from ..models import MediaEvent, MediaEventData
from .ingest_interface import MediaIngestInterface

logger = logging.getLogger(__name__)


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
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(subscriber)
        logger.info(f"Subscriber registered for {event_type.value}")
    
    async def emit(self, event: MediaEventData):
        """Emit event to all subscribers."""
        subscribers = self._subscribers.get(event.event_type, [])
        
        if not subscribers:
            logger.debug(f"No subscribers for event {event.event_type.value}")
            return
        
        results = await asyncio.gather(
            *[self._notify_subscriber(sub, event) for sub in subscribers],
            return_exceptions=True
        )
        
        # Log any failures
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Subscriber notification failed: "
                    f"event={event.event_type.value}, "
                    f"subscriber={subscribers[i].__class__.__name__}, "
                    f"error={str(result)}"
                )
    
    async def _notify_subscriber(
        self,
        subscriber: MediaIngestInterface,
        event: MediaEventData
    ):
        """Notify a single subscriber."""
        try:
            if event.event_type == MediaEvent.FILE_SYNCED:
                return await subscriber.on_file_synced(event)
            elif event.event_type == MediaEvent.BATCH_SYNCED:
                return await subscriber.on_batch_synced([event])
            elif event.event_type == MediaEvent.SYNC_COMPLETE:
                return await subscriber.on_sync_complete(
                    event.sync_id,
                    event.metadata
                )
        except Exception as e:
            logger.error(f"Error notifying subscriber: {e}")
            raise
    
    def unsubscribe(
        self,
        event_type: MediaEvent,
        subscriber: MediaIngestInterface
    ):
        """Unsubscribe from event type."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(subscriber)
                logger.info(f"Subscriber unregistered from {event_type.value}")
            except ValueError:
                logger.warning(f"Subscriber was not subscribed to {event_type.value}")
    
    def clear_subscribers(self, event_type: MediaEvent = None):
        """Clear subscribers for specific event type or all."""
        if event_type:
            self._subscribers[event_type] = []
        else:
            for event in MediaEvent:
                self._subscribers[event] = []
        
        logger.info("Subscribers cleared")
