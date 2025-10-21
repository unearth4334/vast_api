"""
Ingest interface for database integration
"""

from .ingest_interface import MediaIngestInterface
from .event_manager import MediaEventManager

__all__ = ['MediaIngestInterface', 'MediaEventManager']
