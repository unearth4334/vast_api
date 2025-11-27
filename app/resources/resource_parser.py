"""
Resource Parser

Parses markdown resource files with YAML frontmatter and extracts
metadata, descriptions, and download commands.
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ResourceParser:
    """Parser for resource markdown files"""
    
    def __init__(self, resources_path: str):
        """
        Initialize parser with path to resources directory
        
        Args:
            resources_path: Path to the resources directory
        """
        self.resources_path = Path(resources_path)
        logger.info(f"Initialized ResourceParser with path: {self.resources_path}")
    
    def parse_file(self, filepath: Path) -> Dict:
        """
        Parse markdown file and extract metadata + download command
        
        Args:
            filepath: Path to the markdown file
            
        Returns:
            Dictionary containing metadata, description, and download command
            
        Raises:
            ValueError: If file format is invalid
            FileNotFoundError: If file doesn't exist
        """
        if not filepath.exists():
            raise FileNotFoundError(f"Resource file not found: {filepath}")
        
        content = filepath.read_text(encoding='utf-8')
        
        # Extract frontmatter
        frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if not frontmatter_match:
            raise ValueError(f"No frontmatter found in {filepath}")
        
        try:
            metadata = yaml.safe_load(frontmatter_match.group(1))
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in frontmatter: {e}")
        
        body = content[frontmatter_match.end():]
        
        # Validate required fields
        required_fields = ['tags', 'ecosystem', 'basemodel', 'version', 'type']
        missing_fields = [field for field in required_fields if field not in metadata]
        if missing_fields:
            raise ValueError(f"Missing required fields in {filepath}: {missing_fields}")
        
        # Extract download command (supports both # Download and ### Download)
        download_match = re.search(
            r'#{1,3}\s+Download\s*\n+\s*```bash\s*\n(.*?)\n\s*```',
            body,
            re.DOTALL
        )
        
        if not download_match:
            raise ValueError(f"No download command found in {filepath}")
        
        download_command = download_match.group(1).strip()
        
        # Extract description (everything before the Download section)
        description = body[:download_match.start()].strip()
        
        # Get relative path from resources root
        try:
            relative_path = filepath.relative_to(self.resources_path)
        except ValueError:
            relative_path = filepath
        
        return {
            'metadata': metadata,
            'description': description,
            'download_command': download_command,
            'filename': filepath.name,
            'filepath': str(relative_path)
        }
    
    def list_resources(
        self,
        resource_type: Optional[str] = None,
        ecosystem: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None
    ) -> List[Dict]:
        """
        List all resources with optional filtering
        
        Args:
            resource_type: Filter by resource type (workflows, loras, etc.)
            ecosystem: Filter by ecosystem (wan, flux, sd15, etc.)
            tags: Filter by tags (any tag match)
            search: Search in title and description
            
        Returns:
            List of parsed resource dictionaries
        """
        resources = []
        
        # Determine search path
        if resource_type:
            search_path = self.resources_path / resource_type
            if not search_path.exists():
                logger.warning(f"Resource type directory not found: {search_path}")
                return []
            files = search_path.glob('*.md')
        else:
            files = self.resources_path.rglob('*.md')
        
        for filepath in files:
            # Skip metadata files
            if filepath.name.startswith('_'):
                continue
            
            try:
                resource = self.parse_file(filepath)
                
                # Apply filters
                if ecosystem and resource['metadata'].get('ecosystem') != ecosystem:
                    continue
                
                if tags:
                    resource_tags = resource['metadata'].get('tags', [])
                    if not any(tag in resource_tags for tag in tags):
                        continue
                
                if search:
                    search_lower = search.lower()
                    # Search in title (first line of description), description, and metadata
                    title = resource['description'].split('\n')[0].lower()
                    desc_lower = resource['description'].lower()
                    metadata_str = str(resource['metadata']).lower()
                    
                    if not (search_lower in title or 
                           search_lower in desc_lower or 
                           search_lower in metadata_str):
                        continue
                
                resources.append(resource)
            except Exception as e:
                logger.error(f"Error parsing {filepath}: {e}")
                continue
        
        logger.info(f"Found {len(resources)} resources matching filters")
        return resources
    
    def get_ecosystems(self) -> List[str]:
        """Get list of all unique ecosystems from resources"""
        ecosystems = set()
        
        for filepath in self.resources_path.rglob('*.md'):
            if filepath.name.startswith('_'):
                continue
            try:
                resource = self.parse_file(filepath)
                ecosystem = resource['metadata'].get('ecosystem')
                if ecosystem:
                    ecosystems.add(ecosystem)
            except Exception as e:
                logger.debug(f"Skipping {filepath}: {e}")
                continue
        
        return sorted(list(ecosystems))
    
    def get_types(self) -> List[str]:
        """Get list of all unique resource types (directory names)"""
        types = set()
        
        # Get type directories directly from the filesystem
        for item in self.resources_path.iterdir():
            if item.is_dir() and not item.name.startswith('_') and not item.name == 'images':
                # Only include directories that have .md files
                if any(item.glob('*.md')):
                    types.add(item.name)
        
        return sorted(list(types))
    
    def get_tags(self) -> List[str]:
        """Get list of all unique tags from resources"""
        tags = set()
        
        for filepath in self.resources_path.rglob('*.md'):
            if filepath.name.startswith('_'):
                continue
            try:
                resource = self.parse_file(filepath)
                resource_tags = resource['metadata'].get('tags', [])
                tags.update(resource_tags)
            except Exception as e:
                logger.debug(f"Skipping {filepath}: {e}")
                continue
        
        return sorted(list(tags))
