"""
Workflow Generator
Generates ComfyUI workflow JSON from user inputs
"""

import copy
import logging
from typing import Dict, Any, List

from app.create.workflow_loader import WorkflowConfig, InputConfig

logger = logging.getLogger(__name__)


class WorkflowGenerator:
    """Generates ComfyUI workflow JSON from inputs"""
    
    def __init__(self, config: WorkflowConfig, template: dict):
        """
        Initialize generator
        
        Args:
            config: Workflow configuration
            template: Workflow JSON template
        """
        self.config = config
        self.template = template
    
    def generate(self, inputs: Dict[str, Any]) -> dict:
        """
        Generate workflow JSON from inputs
        
        Args:
            inputs: User input values
            
        Returns:
            Generated workflow JSON
        """
        # Deep copy template to avoid modifying original
        workflow = copy.deepcopy(self.template)
        
        # Apply each input to the workflow
        for input_config in self.config.inputs:
            try:
                # Check if input is conditionally shown
                if input_config.depends_on:
                    if not self._check_dependency(inputs, input_config.depends_on):
                        logger.debug(f"Skipping input {input_config.id} (dependency not met)")
                        continue
                
                # Apply the input based on type
                self._apply_input(workflow, input_config, inputs)
                
            except Exception as e:
                logger.error(f"Error applying input {input_config.id}: {e}", exc_info=True)
                # Continue processing other inputs
        
        return workflow
    
    def _check_dependency(self, inputs: Dict[str, Any], depends_on: Dict[str, Any]) -> bool:
        """
        Check if dependency condition is met
        
        Args:
            inputs: User inputs
            depends_on: Dependency configuration
            
        Returns:
            True if dependency is satisfied
        """
        field = depends_on.get('field')
        value = depends_on.get('value')
        
        if not field:
            return True
        
        input_value = inputs.get(field)
        
        # Check if value matches
        if isinstance(value, list):
            return input_value in value
        else:
            return input_value == value
    
    def _apply_input(self, workflow: dict, input_config: InputConfig, inputs: Dict[str, Any]):
        """
        Apply single input to workflow
        
        Args:
            workflow: Workflow JSON to modify
            input_config: Input configuration
            inputs: User input values
        """
        input_type = input_config.type
        
        # Get the input value
        value = inputs.get(input_config.id)
        
        # Skip if no value provided and not required
        if value is None and not input_config.required:
            logger.debug(f"No value for optional input: {input_config.id}")
            return
        
        # Apply based on type
        if input_type in ['text', 'textarea']:
            self._apply_text_input(workflow, input_config, value)
        elif input_type == 'slider':
            self._apply_slider_input(workflow, input_config, value)
        elif input_type == 'toggle':
            self._apply_toggle_input(workflow, input_config, value)
        elif input_type == 'image':
            self._apply_image_input(workflow, input_config, value)
        elif input_type == 'high_low_pair_model':
            self._apply_high_low_model(workflow, input_config, value)
        elif input_type == 'high_low_pair_lora_list':
            self._apply_lora_list(workflow, input_config, value)
        elif input_type == 'single_model':
            self._apply_single_model(workflow, input_config, value)
        elif input_type == 'dropdown':
            self._apply_dropdown(workflow, input_config, value)
        else:
            logger.warning(f"Unknown input type: {input_type} for {input_config.id}")
    
    def _apply_text_input(self, workflow: dict, config: InputConfig, value: Any):
        """Apply text input to workflow"""
        if not config.node_id or not config.field:
            logger.warning(f"Missing node_id or field for text input: {config.id}")
            return
        
        if config.node_id not in workflow:
            logger.warning(f"Node {config.node_id} not found in workflow")
            return
        
        workflow[config.node_id]['inputs'][config.field] = str(value) if value else ""
        logger.debug(f"Applied text input {config.id} to node {config.node_id}.{config.field}")
    
    def _apply_slider_input(self, workflow: dict, config: InputConfig, value: Any):
        """Apply slider input to workflow"""
        if not config.node_id or not config.field:
            logger.warning(f"Missing node_id or field for slider input: {config.id}")
            return
        
        if config.node_id not in workflow:
            logger.warning(f"Node {config.node_id} not found in workflow")
            return
        
        # Convert to appropriate numeric type
        numeric_value = float(value) if value is not None else config.default
        
        # Clamp to range if specified
        if config.min is not None and numeric_value < config.min:
            numeric_value = config.min
        if config.max is not None and numeric_value > config.max:
            numeric_value = config.max
        
        workflow[config.node_id]['inputs'][config.field] = numeric_value
        logger.debug(f"Applied slider input {config.id} to node {config.node_id}.{config.field} = {numeric_value}")
    
    def _apply_toggle_input(self, workflow: dict, config: InputConfig, value: Any):
        """Apply toggle input to workflow"""
        if not config.node_id or not config.field:
            logger.warning(f"Missing node_id or field for toggle input: {config.id}")
            return
        
        if config.node_id not in workflow:
            logger.warning(f"Node {config.node_id} not found in workflow")
            return
        
        bool_value = bool(value) if value is not None else False
        workflow[config.node_id]['inputs'][config.field] = bool_value
        logger.debug(f"Applied toggle input {config.id} to node {config.node_id}.{config.field} = {bool_value}")
    
    def _apply_image_input(self, workflow: dict, config: InputConfig, value: Any):
        """Apply image input to workflow"""
        if not config.node_id or not config.field:
            logger.warning(f"Missing node_id or field for image input: {config.id}")
            return
        
        if config.node_id not in workflow:
            logger.warning(f"Node {config.node_id} not found in workflow")
            return
        
        workflow[config.node_id]['inputs'][config.field] = str(value) if value else ""
        logger.debug(f"Applied image input {config.id} to node {config.node_id}.{config.field}")
    
    def _apply_dropdown(self, workflow: dict, config: InputConfig, value: Any):
        """Apply dropdown input to workflow"""
        if not config.node_id or not config.field:
            logger.warning(f"Missing node_id or field for dropdown input: {config.id}")
            return
        
        if config.node_id not in workflow:
            logger.warning(f"Node {config.node_id} not found in workflow")
            return
        
        workflow[config.node_id]['inputs'][config.field] = str(value) if value else ""
        logger.debug(f"Applied dropdown input {config.id} to node {config.node_id}.{config.field}")
    
    def _apply_high_low_model(self, workflow: dict, config: InputConfig, value: Any):
        """
        Apply high-low noise model pair
        
        Args:
            workflow: Workflow JSON
            config: Input configuration
            value: Dict with highNoisePath and lowNoisePath
        """
        if not value or not isinstance(value, dict):
            logger.warning(f"Invalid high-low model value for {config.id}")
            return
        
        if not config.node_ids or len(config.node_ids) < 2:
            logger.warning(f"Missing node_ids for high-low model: {config.id}")
            return
        
        high_node_id = config.node_ids[0]
        low_node_id = config.node_ids[1]
        field_name = config.field or 'unet_name'
        
        # Apply high noise model
        if high_node_id in workflow:
            high_path = value.get('highNoisePath', '')
            workflow[high_node_id]['inputs'][field_name] = high_path
            logger.debug(f"Applied high noise model to node {high_node_id}: {high_path}")
        else:
            logger.warning(f"High noise node {high_node_id} not found")
        
        # Apply low noise model
        if low_node_id in workflow:
            low_path = value.get('lowNoisePath', '')
            workflow[low_node_id]['inputs'][field_name] = low_path
            logger.debug(f"Applied low noise model to node {low_node_id}: {low_path}")
        else:
            logger.warning(f"Low noise node {low_node_id} not found")
    
    def _apply_lora_list(self, workflow: dict, config: InputConfig, value: Any):
        """
        Apply LoRA list to Power Lora Loader nodes
        
        Args:
            workflow: Workflow JSON
            config: Input configuration
            value: List of LoRA objects with highNoisePath, lowNoisePath, strength
        """
        if not value or not isinstance(value, list):
            logger.debug(f"No LoRAs provided for {config.id}")
            return
        
        if not config.node_ids or len(config.node_ids) < 2:
            logger.warning(f"Missing node_ids for LoRA list: {config.id}")
            return
        
        high_node_id = config.node_ids[0]
        low_node_id = config.node_ids[1]
        field_name = config.field or '➕ Add Lora'
        
        # Build Power Lora Loader config
        high_lora_config = {}
        low_lora_config = {}
        
        for idx, lora in enumerate(value):
            if not isinstance(lora, dict):
                continue
            
            key = f"Lora {idx + 1}"
            high_lora_config[key] = {
                'on': True,
                'lora': lora.get('highNoisePath', ''),
                'strength': lora.get('strength', 1.0),
                'strength_clip': lora.get('strength', 1.0)
            }
            low_lora_config[key] = {
                'on': True,
                'lora': lora.get('lowNoisePath', ''),
                'strength': lora.get('strength', 1.0),
                'strength_clip': lora.get('strength', 1.0)
            }
        
        # Apply to high noise node
        if high_node_id in workflow:
            workflow[high_node_id]['inputs'][field_name] = high_lora_config
            logger.debug(f"Applied {len(high_lora_config)} LoRAs to high noise node {high_node_id}")
        else:
            logger.warning(f"High noise LoRA node {high_node_id} not found")
        
        # Apply to low noise node
        if low_node_id in workflow:
            workflow[low_node_id]['inputs'][field_name] = low_lora_config
            logger.debug(f"Applied {len(low_lora_config)} LoRAs to low noise node {low_node_id}")
        else:
            logger.warning(f"Low noise LoRA node {low_node_id} not found")
    
    def _apply_single_model(self, workflow: dict, config: InputConfig, value: Any):
        """
        Apply single model selector
        
        Args:
            workflow: Workflow JSON
            config: Input configuration
            value: Dict with path key
        """
        if not value or not isinstance(value, dict):
            logger.warning(f"Invalid single model value for {config.id}")
            return
        
        if not config.node_id or not config.field:
            logger.warning(f"Missing node_id or field for single model: {config.id}")
            return
        
        if config.node_id not in workflow:
            logger.warning(f"Node {config.node_id} not found in workflow")
            return
        
        model_path = value.get('path', '')
        workflow[config.node_id]['inputs'][config.field] = model_path
        logger.debug(f"Applied single model to node {config.node_id}.{config.field}: {model_path}")
    
    def get_input_summary(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary of key inputs for metadata
        
        Args:
            inputs: User input values
            
        Returns:
            Dict with key input values
        """
        summary = {}
        
        # Include key fields commonly used
        key_fields = ['positive_prompt', 'negative_prompt', 'duration', 'steps', 'cfg', 'seed']
        
        for field in key_fields:
            if field in inputs:
                value = inputs[field]
                # Truncate long strings
                if isinstance(value, str) and len(value) > 50:
                    summary[field] = value[:50] + '...'
                else:
                    summary[field] = value
        
        return summary
