"""
Workflow Loader
Loads and parses workflow YAML and JSON files
"""

import os
import json
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class WorkflowMetadata:
    """Metadata for a workflow"""
    id: str
    name: str
    description: str
    category: str
    version: str
    thumbnail: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    vram_estimate: Optional[str] = None
    time_estimate: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self):
        return asdict(self)


@dataclass
class LayoutConfig:
    """Layout configuration for workflow UI"""
    sections: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self):
        return asdict(self)


@dataclass
class InputConfig:
    """Configuration for a single workflow input"""
    id: str
    section: str
    type: str
    label: str
    description: str
    required: bool
    # Token-based value replacement (NEW - preferred method)
    token: Optional[str] = None  # Single token like "{{DURATION}}"
    tokens: Optional[Dict[str, str]] = None  # Multiple tokens like {"high": "{{WAN_HIGH}}", "low": "{{WAN_LOW}}"}
    # Legacy node-based value replacement (deprecated but still supported)
    node_id: Optional[str] = None
    node_ids: Optional[List[str]] = None
    field: Optional[str] = None
    fields: Optional[List[str]] = None
    # Value constraints and defaults
    default: Optional[Any] = None
    default_high: Optional[str] = None
    default_low: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    options: Optional[List[str]] = None
    depends_on: Optional[Dict[str, Any]] = None
    model_type: Optional[str] = None
    accept: Optional[str] = None
    max_size_mb: Optional[int] = None
    
    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class OutputConfig:
    """Configuration for a workflow output"""
    id: str
    node_id: str
    type: str
    format: str
    label: str
    
    def to_dict(self):
        return asdict(self)


@dataclass
class WorkflowConfig:
    """Complete workflow configuration"""
    id: str
    name: str
    description: str
    version: str
    category: str
    workflow_file: str
    vram_estimate: str
    time_estimate: Dict[str, Any]
    layout: LayoutConfig
    inputs: List[InputConfig]
    outputs: List[OutputConfig]
    thumbnail: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'category': self.category,
            'workflow_file': self.workflow_file,
            'vram_estimate': self.vram_estimate,
            'time_estimate': self.time_estimate,
            'thumbnail': self.thumbnail,
            'tags': self.tags,
            'layout': self.layout.to_dict(),
            'inputs': [inp.to_dict() for inp in self.inputs],
            'outputs': [out.to_dict() for out in self.outputs]
        }


class WorkflowLoader:
    """Loads and parses workflow files"""
    
    # Cache for parsed workflows (TTL: 5 minutes)
    _workflow_cache: Dict[str, tuple[WorkflowConfig, datetime]] = {}
    _template_cache: Dict[str, tuple[dict, datetime]] = {}
    _cache_ttl = timedelta(minutes=5)
    
    @classmethod
    def get_workflows_dir(cls) -> Path:
        """Get the workflows directory path"""
        # Assuming workflows are in the root workflows/ directory
        base_dir = Path(__file__).parent.parent.parent
        workflows_dir = base_dir / 'workflows'
        return workflows_dir
    
    @classmethod
    def discover_workflows(cls) -> List[WorkflowMetadata]:
        """
        Scan workflows directory and return metadata for all workflows
        
        Returns:
            List of WorkflowMetadata objects
        """
        workflows_dir = cls.get_workflows_dir()
        
        if not workflows_dir.exists():
            logger.warning(f"Workflows directory not found: {workflows_dir}")
            return []
        
        workflows = []
        
        # Find all .webui.yml files
        for yaml_file in workflows_dir.glob('*.webui.yml'):
            try:
                with open(yaml_file, 'r') as f:
                    data = yaml.safe_load(f)
                
                # Extract workflow ID from filename
                workflow_id = yaml_file.stem.replace('.webui', '')
                
                # Check if corresponding JSON file exists using workflow_file from YAML
                workflow_json_name = data.get('workflow_file', f"{workflow_id}.json")
                json_file = workflows_dir / workflow_json_name
                if not json_file.exists():
                    logger.warning(f"JSON file not found for {workflow_id}: {workflow_json_name}, skipping")
                    continue
                
                # Create metadata object
                metadata = WorkflowMetadata(
                    id=workflow_id,
                    name=data.get('name', workflow_id),
                    description=data.get('description', ''),
                    category=data.get('category', 'general'),
                    version=data.get('version', '1.0.0'),
                    thumbnail=data.get('thumbnail'),
                    tags=data.get('tags', []),
                    vram_estimate=data.get('vram_estimate'),
                    time_estimate=data.get('time_estimate', {})
                )
                
                workflows.append(metadata)
                
            except Exception as e:
                logger.error(f"Error parsing workflow {yaml_file}: {e}")
                continue
        
        return workflows
    
    @classmethod
    def load_workflow(cls, workflow_id: str) -> WorkflowConfig:
        """
        Load and parse workflow configuration from YAML
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            WorkflowConfig object
            
        Raises:
            FileNotFoundError: If workflow file doesn't exist
        """
        # Check cache
        if workflow_id in cls._workflow_cache:
            cached_workflow, cached_time = cls._workflow_cache[workflow_id]
            if datetime.now() - cached_time < cls._cache_ttl:
                logger.debug(f"Using cached workflow: {workflow_id}")
                return cached_workflow
        
        workflows_dir = cls.get_workflows_dir()
        yaml_file = workflows_dir / f"{workflow_id}.webui.yml"
        
        if not yaml_file.exists():
            raise FileNotFoundError(f"Workflow not found: {workflow_id}")
        
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
            
            # Parse layout
            layout_data = data.get('layout', {})
            layout = LayoutConfig(
                sections=layout_data.get('sections', [])
            )
            
            # Parse inputs
            inputs = []
            for inp_data in data.get('inputs', []):
                input_config = InputConfig(
                    id=inp_data['id'],
                    section=inp_data['section'],
                    type=inp_data['type'],
                    label=inp_data['label'],
                    description=inp_data.get('description', ''),
                    required=inp_data.get('required', False),
                    # Token-based (NEW)
                    token=inp_data.get('token'),
                    tokens=inp_data.get('tokens'),
                    # Node-based (legacy)
                    node_id=inp_data.get('node_id'),
                    node_ids=inp_data.get('node_ids'),
                    field=inp_data.get('field'),
                    fields=inp_data.get('fields'),
                    # Value constraints
                    default=inp_data.get('default'),
                    default_high=inp_data.get('default_high'),
                    default_low=inp_data.get('default_low'),
                    min=inp_data.get('min'),
                    max=inp_data.get('max'),
                    step=inp_data.get('step'),
                    options=inp_data.get('options'),
                    depends_on=inp_data.get('depends_on'),
                    model_type=inp_data.get('model_type'),
                    accept=inp_data.get('accept'),
                    max_size_mb=inp_data.get('max_size_mb')
                )
                inputs.append(input_config)
            
            # Parse outputs
            outputs = []
            for out_data in data.get('outputs', []):
                output_config = OutputConfig(
                    id=out_data['id'],
                    node_id=out_data['node_id'],
                    type=out_data['type'],
                    format=out_data['format'],
                    label=out_data['label']
                )
                outputs.append(output_config)
            
            # Create workflow config
            workflow = WorkflowConfig(
                id=workflow_id,
                name=data['name'],
                description=data.get('description', ''),
                version=data.get('version', '1.0.0'),
                category=data.get('category', 'general'),
                workflow_file=data['workflow_file'],
                vram_estimate=data.get('vram_estimate', 'Unknown'),
                time_estimate=data.get('time_estimate', {}),
                thumbnail=data.get('thumbnail'),
                tags=data.get('tags', []),
                layout=layout,
                inputs=inputs,
                outputs=outputs
            )
            
            # Cache the result
            cls._workflow_cache[workflow_id] = (workflow, datetime.now())
            
            return workflow
            
        except Exception as e:
            logger.error(f"Error loading workflow {workflow_id}: {e}", exc_info=True)
            raise
    
    @classmethod
    def load_workflow_json(cls, workflow_id: str) -> dict:
        """
        Load workflow JSON template
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Workflow JSON as dict
            
        Raises:
            FileNotFoundError: If workflow JSON doesn't exist
        """
        # Check cache
        if workflow_id in cls._template_cache:
            cached_template, cached_time = cls._template_cache[workflow_id]
            if datetime.now() - cached_time < cls._cache_ttl:
                logger.debug(f"Using cached template: {workflow_id}")
                return cached_template
        
        workflows_dir = cls.get_workflows_dir()
        
        # Load YAML to get workflow_file name
        yaml_file = workflows_dir / f"{workflow_id}.webui.yml"
        if not yaml_file.exists():
            raise FileNotFoundError(f"Workflow YAML not found: {workflow_id}")
        
        try:
            with open(yaml_file, 'r') as f:
                yaml_data = yaml.safe_load(f)
            
            workflow_json_name = yaml_data.get('workflow_file', f"{workflow_id}.json")
            json_file = workflows_dir / workflow_json_name
            
            if not json_file.exists():
                raise FileNotFoundError(f"Workflow JSON not found: {workflow_json_name}")
            
            with open(json_file, 'r') as f:
                template = json.load(f)
            
            # Cache the result
            cls._template_cache[workflow_id] = (template, datetime.now())
            
            return template
            
        except Exception as e:
            logger.error(f"Error loading workflow JSON {workflow_id}: {e}", exc_info=True)
            raise
    
    @classmethod
    def clear_cache(cls):
        """Clear the workflow cache"""
        cls._workflow_cache.clear()
        cls._template_cache.clear()
        logger.info("Workflow cache cleared")
