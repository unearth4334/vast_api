#!/usr/bin/env python3
"""
Workflow Loader - Load and parse workflow YAML and JSON files.
Provides caching for performance optimization.
"""

import os
import logging
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)

# Cache settings
CACHE_TTL_SECONDS = 300  # 5 minutes


@dataclass
class InputConfig:
    """Configuration for a workflow input field"""
    id: str
    section: str
    type: str
    label: str
    description: str = ""
    required: bool = False
    default: Any = None
    node_id: Optional[str] = None
    node_ids: Optional[List[str]] = None
    field: Optional[str] = None
    fields: Optional[List[str]] = None
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    unit: Optional[str] = None
    options: Optional[List[str]] = None
    depends_on: Optional[Dict] = None
    model_type: Optional[str] = None
    accept: Optional[str] = None
    max_size_mb: Optional[int] = None
    rows: Optional[int] = None
    placeholder: Optional[str] = None
    max_length: Optional[int] = None
    category: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'InputConfig':
        """Create InputConfig from dictionary"""
        return cls(
            id=data.get('id', ''),
            section=data.get('section', 'basic'),
            type=data.get('type', 'text'),
            label=data.get('label', ''),
            description=data.get('description', ''),
            required=data.get('required', False),
            default=data.get('default'),
            node_id=str(data.get('node_id')) if data.get('node_id') else None,
            node_ids=[str(n) for n in data.get('node_ids', [])] if data.get('node_ids') else None,
            field=data.get('field'),
            fields=data.get('fields'),
            min=data.get('min'),
            max=data.get('max'),
            step=data.get('step'),
            unit=data.get('unit'),
            options=data.get('options'),
            depends_on=data.get('depends_on'),
            model_type=data.get('model_type'),
            accept=data.get('accept'),
            max_size_mb=data.get('max_size_mb'),
            rows=data.get('rows'),
            placeholder=data.get('placeholder'),
            max_length=data.get('max_length'),
            category=data.get('category'),
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        result = {
            'id': self.id,
            'section': self.section,
            'type': self.type,
            'label': self.label,
            'description': self.description,
            'required': self.required,
        }
        if self.default is not None:
            result['default'] = self.default
        if self.node_id:
            result['node_id'] = self.node_id
        if self.node_ids:
            result['node_ids'] = self.node_ids
        if self.field:
            result['field'] = self.field
        if self.fields:
            result['fields'] = self.fields
        if self.min is not None:
            result['min'] = self.min
        if self.max is not None:
            result['max'] = self.max
        if self.step is not None:
            result['step'] = self.step
        if self.unit:
            result['unit'] = self.unit
        if self.options:
            result['options'] = self.options
        if self.depends_on:
            result['depends_on'] = self.depends_on
        if self.model_type:
            result['model_type'] = self.model_type
        if self.accept:
            result['accept'] = self.accept
        if self.max_size_mb:
            result['max_size_mb'] = self.max_size_mb
        if self.rows:
            result['rows'] = self.rows
        if self.placeholder:
            result['placeholder'] = self.placeholder
        if self.max_length:
            result['max_length'] = self.max_length
        if self.category:
            result['category'] = self.category
        return result


@dataclass
class OutputConfig:
    """Configuration for a workflow output"""
    id: str
    node_id: str
    type: str
    format: str
    label: str
    description: str = ""
    depends_on: Optional[Dict] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'OutputConfig':
        """Create OutputConfig from dictionary"""
        return cls(
            id=data.get('id', ''),
            node_id=str(data.get('node_id', '')),
            type=data.get('type', 'file'),
            format=data.get('format', ''),
            label=data.get('label', ''),
            description=data.get('description', ''),
            depends_on=data.get('depends_on'),
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        result = {
            'id': self.id,
            'node_id': self.node_id,
            'type': self.type,
            'format': self.format,
            'label': self.label,
            'description': self.description,
        }
        if self.depends_on:
            result['depends_on'] = self.depends_on
        return result


@dataclass
class LayoutConfig:
    """Configuration for workflow UI layout"""
    sections: List[Dict] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'LayoutConfig':
        """Create LayoutConfig from dictionary"""
        return cls(
            sections=data.get('sections', [])
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {'sections': self.sections}


@dataclass
class WorkflowConfig:
    """Full workflow configuration"""
    id: str
    name: str
    description: str
    version: str
    category: str
    workflow_file: str
    vram_estimate: str
    time_estimate: Dict
    layout: LayoutConfig
    inputs: List[InputConfig]
    outputs: List[OutputConfig]
    tags: List[str] = field(default_factory=list)
    thumbnail: Optional[str] = None
    requirements: Dict = field(default_factory=dict)
    presets: List[Dict] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict, workflow_id: str) -> 'WorkflowConfig':
        """Create WorkflowConfig from dictionary"""
        inputs = [InputConfig.from_dict(inp) for inp in data.get('inputs', [])]
        outputs = [OutputConfig.from_dict(out) for out in data.get('outputs', [])]
        layout = LayoutConfig.from_dict(data.get('layout', {}))
        
        return cls(
            id=workflow_id,
            name=data.get('name', workflow_id),
            description=data.get('description', ''),
            version=data.get('version', '1.0.0'),
            category=data.get('category', 'other'),
            workflow_file=data.get('workflow_file', ''),
            vram_estimate=data.get('vram_estimate', ''),
            time_estimate=data.get('time_estimate', {}),
            layout=layout,
            inputs=inputs,
            outputs=outputs,
            tags=data.get('tags', []),
            thumbnail=data.get('thumbnail'),
            requirements=data.get('requirements', {}),
            presets=data.get('presets', []),
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'category': self.category,
            'workflow_file': self.workflow_file,
            'vram_estimate': self.vram_estimate,
            'time_estimate': self.time_estimate,
            'layout': self.layout.to_dict(),
            'inputs': [inp.to_dict() for inp in self.inputs],
            'outputs': [out.to_dict() for out in self.outputs],
            'tags': self.tags,
            'thumbnail': self.thumbnail,
            'requirements': self.requirements,
            'presets': self.presets,
        }
    
    def to_metadata(self) -> Dict:
        """Convert to lightweight metadata for list API"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'version': self.version,
            'thumbnail': self.thumbnail,
            'tags': self.tags,
            'vram_estimate': self.vram_estimate,
            'time_estimate': self.time_estimate,
        }


class WorkflowLoader:
    """Load and cache workflow configurations"""
    
    # Class-level cache for parsed workflows
    _config_cache: Dict[str, tuple] = {}  # workflow_id -> (config, timestamp)
    _json_cache: Dict[str, tuple] = {}    # workflow_file -> (json_data, timestamp)
    _discovery_cache: Optional[tuple] = None  # (workflows_list, timestamp)
    
    def __init__(self, workflows_dir: Optional[str] = None):
        """Initialize loader with workflows directory"""
        if workflows_dir:
            self.workflows_dir = Path(workflows_dir)
        else:
            # Default to workflows directory relative to app
            self.workflows_dir = Path(__file__).parent.parent.parent / 'workflows'
    
    def discover_workflows(self) -> List[WorkflowConfig]:
        """Scan workflows directory and return all workflow configs"""
        # Check cache
        if WorkflowLoader._discovery_cache:
            configs, timestamp = WorkflowLoader._discovery_cache
            if time.time() - timestamp < CACHE_TTL_SECONDS:
                return configs
        
        configs = []
        
        if not self.workflows_dir.exists():
            logger.warning(f"Workflows directory does not exist: {self.workflows_dir}")
            return configs
        
        # Find all .webui.yml files
        for yaml_file in self.workflows_dir.glob("*.webui.yml"):
            workflow_id = self._normalize_workflow_id(yaml_file.stem.replace('.webui', ''))
            try:
                config = self.load_workflow(workflow_id)
                if config:
                    configs.append(config)
            except Exception as e:
                logger.error(f"Error loading workflow {workflow_id}: {e}")
        
        # Also check .webui.yaml files
        for yaml_file in self.workflows_dir.glob("*.webui.yaml"):
            workflow_id = self._normalize_workflow_id(yaml_file.stem.replace('.webui', ''))
            # Avoid duplicates
            if not any(c.id == workflow_id for c in configs):
                try:
                    config = self.load_workflow(workflow_id)
                    if config:
                        configs.append(config)
                except Exception as e:
                    logger.error(f"Error loading workflow {workflow_id}: {e}")
        
        # Update cache
        WorkflowLoader._discovery_cache = (configs, time.time())
        
        return configs
    
    def load_workflow(self, workflow_id: str) -> Optional[WorkflowConfig]:
        """Load and parse .webui.yml file for a workflow"""
        # Check cache
        if workflow_id in WorkflowLoader._config_cache:
            config, timestamp = WorkflowLoader._config_cache[workflow_id]
            if time.time() - timestamp < CACHE_TTL_SECONDS:
                return config
        
        yaml_data = self._load_yaml_file(workflow_id)
        if not yaml_data:
            return None
        
        config = WorkflowConfig.from_dict(yaml_data, workflow_id)
        
        # Update cache
        WorkflowLoader._config_cache[workflow_id] = (config, time.time())
        
        return config
    
    def load_workflow_json(self, workflow_id: str) -> Optional[Dict]:
        """Load workflow JSON template"""
        config = self.load_workflow(workflow_id)
        if not config or not config.workflow_file:
            return None
        
        return self._load_json_file(config.workflow_file)
    
    def _load_yaml_file(self, workflow_id: str) -> Optional[Dict]:
        """Load YAML file for a workflow ID"""
        if yaml is None:
            logger.warning("PyYAML not installed, cannot load webui wrappers")
            return None
        
        # Try different naming patterns
        patterns = [
            f"{workflow_id}.webui.yml",
            f"{workflow_id}.webui.yaml",
            f"{workflow_id.replace('-', '_')}.webui.yml",
            f"{workflow_id.replace('_', '-')}.webui.yml",
            f"{workflow_id.replace('_', ' ')}.webui.yml",
            f"IMG_to_VIDEO.webui.yml" if workflow_id == 'img_to_video' else None,
        ]
        
        for pattern in patterns:
            if not pattern:
                continue
            yaml_path = self.workflows_dir / pattern
            if yaml_path.exists():
                try:
                    with open(yaml_path, 'r', encoding='utf-8') as f:
                        return yaml.safe_load(f)
                except Exception as e:
                    logger.error(f"Error loading webui wrapper {yaml_path}: {e}")
                    return None
        
        logger.warning(f"Could not find webui wrapper for workflow: {workflow_id}")
        return None
    
    def _load_json_file(self, workflow_file: str) -> Optional[Dict]:
        """Load workflow JSON file with caching"""
        # Check cache
        if workflow_file in WorkflowLoader._json_cache:
            json_data, timestamp = WorkflowLoader._json_cache[workflow_file]
            if time.time() - timestamp < CACHE_TTL_SECONDS:
                return json_data
        
        json_path = self.workflows_dir / workflow_file
        if not json_path.exists():
            logger.warning(f"Workflow JSON file not found: {json_path}")
            return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Update cache
            WorkflowLoader._json_cache[workflow_file] = (json_data, time.time())
            
            return json_data
        except Exception as e:
            logger.error(f"Error loading workflow JSON {json_path}: {e}")
            return None
    
    def _normalize_workflow_id(self, filename_stem: str) -> str:
        """Normalize a filename stem to a workflow ID"""
        return filename_stem.replace('.webui', '').replace(' ', '_').lower()
    
    @classmethod
    def clear_cache(cls):
        """Clear all caches"""
        cls._config_cache.clear()
        cls._json_cache.clear()
        cls._discovery_cache = None
