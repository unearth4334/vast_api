"""
Resource Manager

High-level interface for resource operations including listing,
searching, and retrieving resource details.
"""

from pathlib import Path
from typing import Dict, List, Optional
import logging
from .resource_parser import ResourceParser

logger = logging.getLogger(__name__)


class ResourceManager:
    """Manager for resource operations"""
    
    def __init__(self, resources_path: str):
        """
        Initialize resource manager
        
        Args:
            resources_path: Path to the resources directory
        """
        self.resources_path = Path(resources_path)
        self.parser = ResourceParser(resources_path)
        logger.info(f"Initialized ResourceManager with path: {self.resources_path}")
    
    def list_resources(
        self,
        resource_type: Optional[str] = None,
        ecosystem: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None
    ) -> List[Dict]:
        """
        List resources with optional filtering
        
        Args:
            resource_type: Filter by resource type
            ecosystem: Filter by ecosystem
            tags: Filter by tags
            search: Search query
            
        Returns:
            List of resource dictionaries
        """
        return self.parser.list_resources(
            resource_type=resource_type,
            ecosystem=ecosystem,
            tags=tags,
            search=search
        )
    
    def get_resource(self, resource_path: str) -> Optional[Dict]:
        """
        Get details of a specific resource
        
        Args:
            resource_path: Relative path to resource file (e.g., 'workflows/example.md')
            
        Returns:
            Resource dictionary or None if not found
        """
        filepath = self.resources_path / resource_path
        
        if not filepath.exists():
            logger.warning(f"Resource not found: {resource_path}")
            return None
        
        try:
            return self.parser.parse_file(filepath)
        except Exception as e:
            logger.error(f"Error loading resource {resource_path}: {e}")
            return None
    
    def get_ecosystems(self) -> List[str]:
        """Get list of all available ecosystems"""
        return self.parser.get_ecosystems()
    
    def get_types(self) -> List[str]:
        """Get list of all available resource types"""
        return self.parser.get_types()
    
    def get_tags(self) -> List[str]:
        """Get list of all available tags"""
        return self.parser.get_tags()
    
    def search_resources(self, query: str) -> List[Dict]:
        """
        Search resources by query string
        
        Args:
            query: Search query
            
        Returns:
            List of matching resources
        """
        return self.parser.list_resources(search=query)
