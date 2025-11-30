#!/usr/bin/env python3
"""
Workflow Generator - Generate ComfyUI workflow JSON from user inputs.
Handles mapping of user inputs to workflow node fields.
"""

import copy
import logging
import random
from typing import Dict, List, Any, Optional

from .workflow_loader import WorkflowConfig, InputConfig

logger = logging.getLogger(__name__)


class WorkflowGenerator:
    """Generate ComfyUI workflow JSON from user inputs"""
    
    def __init__(self, config: WorkflowConfig, template: Dict):
        """
        Initialize generator with workflow config and template.
        
        Args:
            config: WorkflowConfig object with input definitions
            template: The raw workflow JSON template
        """
        self.config = config
        self.template = template
    
    def generate(self, inputs: Dict) -> Dict:
        """
        Generate workflow JSON with user inputs merged in.
        
        Args:
            inputs: Dictionary of user-provided input values
            
        Returns:
            Generated workflow JSON with inputs applied
        """
        # Deep copy to avoid modifying original template
        workflow = copy.deepcopy(self.template)
        
        # Apply each input from the config
        for input_config in self.config.inputs:
            self._apply_input(workflow, input_config, inputs)
        
        return workflow
    
    def _apply_input(self, workflow: Dict, input_config: InputConfig, inputs: Dict):
        """Apply a single input to the workflow"""
        input_id = input_config.id
        
        # Skip if input not provided and not required
        if input_id not in inputs:
            # Apply default if exists
            if input_config.default is not None:
                value = input_config.default
            else:
                return
        else:
            value = inputs[input_id]
        
        # Check depends_on condition
        if input_config.depends_on:
            dep_field = input_config.depends_on.get('field')
            dep_value = input_config.depends_on.get('value')
            if dep_field and inputs.get(dep_field) != dep_value:
                return  # Dependency not satisfied
        
        # Route to appropriate handler based on input type
        input_type = input_config.type
        
        if input_type in ('text', 'textarea'):
            self._apply_text_input(workflow, input_config, value)
        elif input_type == 'slider':
            self._apply_slider_input(workflow, input_config, value)
        elif input_type == 'checkbox':
            self._apply_checkbox_input(workflow, input_config, value)
        elif input_type == 'seed':
            self._apply_seed_input(workflow, input_config, value)
        elif input_type == 'image':
            self._apply_image_input(workflow, input_config, value)
        elif input_type == 'high_low_pair_model':
            self._apply_high_low_model(workflow, input_config, value)
        elif input_type == 'high_low_pair_lora_list':
            self._apply_lora_list(workflow, input_config, value)
        elif input_type == 'single_model':
            self._apply_single_model(workflow, input_config, value)
        elif input_type == 'select':
            self._apply_select_input(workflow, input_config, value)
        else:
            logger.warning(f"Unknown input type '{input_type}' for field '{input_id}'")
            # Try generic application
            self._apply_generic_input(workflow, input_config, value)
    
    def _apply_text_input(self, workflow: Dict, config: InputConfig, value: str):
        """Apply text/textarea input to workflow"""
        node_id = config.node_id
        if not node_id or node_id not in workflow:
            logger.warning(f"Node {node_id} not found for text input {config.id}")
            return
        
        target_field = config.field or 'value'
        if 'inputs' in workflow[node_id]:
            workflow[node_id]['inputs'][target_field] = value
    
    def _apply_slider_input(self, workflow: Dict, config: InputConfig, value: float):
        """Apply slider input to workflow (may update multiple fields)"""
        node_id = config.node_id
        if not node_id or node_id not in workflow:
            logger.warning(f"Node {node_id} not found for slider input {config.id}")
            return
        
        if 'inputs' not in workflow[node_id]:
            return
        
        # Handle single field
        if config.field:
            workflow[node_id]['inputs'][config.field] = value
        
        # Handle multiple fields (e.g., Xi and Xf for mxSlider)
        if config.fields:
            for field in config.fields:
                if field in workflow[node_id]['inputs']:
                    workflow[node_id]['inputs'][field] = value
    
    def _apply_checkbox_input(self, workflow: Dict, config: InputConfig, value: bool):
        """Apply checkbox input to workflow"""
        node_id = config.node_id
        
        # Single node
        if node_id and node_id in workflow:
            target_field = config.field or 'value'
            if 'inputs' in workflow[node_id]:
                workflow[node_id]['inputs'][target_field] = value
        
        # Multiple nodes (e.g., enable/disable pairs)
        if config.node_ids:
            for nid in config.node_ids:
                if nid in workflow:
                    target_field = config.field or 'value'
                    if 'inputs' in workflow[nid]:
                        workflow[nid]['inputs'][target_field] = value
    
    def _apply_seed_input(self, workflow: Dict, config: InputConfig, value: int):
        """Apply seed input with special handling for random (-1)"""
        node_id = config.node_id
        if not node_id or node_id not in workflow:
            logger.warning(f"Node {node_id} not found for seed input {config.id}")
            return
        
        # Handle random seed - use 2^31 - 1 as max for better compatibility
        if value == -1:
            value = random.randint(0, 2**31 - 1)
        
        target_field = config.field or 'noise_seed'
        if 'inputs' in workflow[node_id]:
            workflow[node_id]['inputs'][target_field] = value
    
    def _apply_image_input(self, workflow: Dict, config: InputConfig, value: str):
        """Apply image input (filename/path)"""
        node_id = config.node_id
        if not node_id or node_id not in workflow:
            logger.warning(f"Node {node_id} not found for image input {config.id}")
            return
        
        target_field = config.field or 'image'
        if 'inputs' in workflow[node_id]:
            workflow[node_id]['inputs'][target_field] = value
    
    def _apply_high_low_model(self, workflow: Dict, config: InputConfig, value: Dict):
        """Apply high-low noise model pair"""
        if not value or not isinstance(value, dict):
            return
        
        if not config.node_ids or len(config.node_ids) < 2:
            logger.warning(f"High-low model {config.id} requires exactly 2 node_ids")
            return
        
        high_node_id = config.node_ids[0]
        low_node_id = config.node_ids[1]
        
        high_path = value.get('highNoisePath')
        low_path = value.get('lowNoisePath')
        
        if high_path and high_node_id in workflow:
            if 'inputs' in workflow[high_node_id]:
                workflow[high_node_id]['inputs']['unet_name'] = high_path
        
        if low_path and low_node_id in workflow:
            if 'inputs' in workflow[low_node_id]:
                workflow[low_node_id]['inputs']['unet_name'] = low_path
    
    def _apply_lora_list(self, workflow: Dict, config: InputConfig, value: List[Dict]):
        """Apply LoRA list to Power Lora Loader nodes"""
        if not value or not isinstance(value, list):
            return
        
        if not config.node_ids or len(config.node_ids) < 2:
            logger.warning(f"LoRA list {config.id} requires exactly 2 node_ids")
            return
        
        high_node_id = config.node_ids[0]
        low_node_id = config.node_ids[1]
        
        # Build Power Lora Loader configs
        high_lora_config = {}
        low_lora_config = {}
        
        for idx, lora in enumerate(value):
            if not isinstance(lora, dict):
                continue
            
            key = f"Lora {idx + 1}"
            strength = lora.get('strength', 1.0)
            
            high_path = lora.get('highNoisePath')
            low_path = lora.get('lowNoisePath')
            
            if high_path:
                high_lora_config[key] = {
                    'on': True,
                    'lora': high_path,
                    'strength': strength,
                    'strength_clip': strength
                }
            
            if low_path:
                low_lora_config[key] = {
                    'on': True,
                    'lora': low_path,
                    'strength': strength,
                    'strength_clip': strength
                }
        
        # Apply to workflow nodes
        if high_lora_config and high_node_id in workflow:
            if 'inputs' in workflow[high_node_id]:
                workflow[high_node_id]['inputs']['➕ Add Lora'] = high_lora_config
        
        if low_lora_config and low_node_id in workflow:
            if 'inputs' in workflow[low_node_id]:
                workflow[low_node_id]['inputs']['➕ Add Lora'] = low_lora_config
    
    def _apply_single_model(self, workflow: Dict, config: InputConfig, value: Any):
        """Apply single model selection"""
        node_id = config.node_id
        if not node_id or node_id not in workflow:
            logger.warning(f"Node {node_id} not found for single model {config.id}")
            return
        
        # Handle both string path and dict with 'path' key
        if isinstance(value, dict):
            path = value.get('path', '')
        else:
            path = str(value)
        
        if not path:
            return
        
        target_field = config.field
        if not target_field:
            # Try common field names based on model_type
            model_type = config.model_type
            field_map = {
                'text_encoders': 'clip_name',
                'vae': 'vae_name',
                'upscale_models': 'model_name',
                'diffusion_models': 'unet_name',
            }
            target_field = field_map.get(model_type, 'model_name')
        
        if 'inputs' in workflow[node_id]:
            workflow[node_id]['inputs'][target_field] = path
    
    def _apply_select_input(self, workflow: Dict, config: InputConfig, value: str):
        """Apply select/dropdown input"""
        node_id = config.node_id
        if not node_id or node_id not in workflow:
            logger.warning(f"Node {node_id} not found for select input {config.id}")
            return
        
        target_field = config.field or 'value'
        if 'inputs' in workflow[node_id]:
            workflow[node_id]['inputs'][target_field] = value
    
    def _apply_generic_input(self, workflow: Dict, config: InputConfig, value: Any):
        """Apply input using generic logic"""
        node_id = config.node_id
        if not node_id or node_id not in workflow:
            return
        
        target_field = config.field or 'value'
        if 'inputs' in workflow[node_id]:
            workflow[node_id]['inputs'][target_field] = value
    
    def get_input_summary(self, inputs: Dict) -> Dict:
        """Get a summary of inputs for metadata"""
        summary = {}
        
        # Include key inputs in summary
        key_fields = ['positive_prompt', 'duration', 'steps', 'seed', 'cfg']
        
        for field in key_fields:
            if field in inputs:
                value = inputs[field]
                # Truncate long strings
                if isinstance(value, str) and len(value) > 50:
                    value = value[:47] + '...'
                summary[field] = value
        
        return summary
