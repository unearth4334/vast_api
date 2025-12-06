"""
Workflow Validator
Validates user inputs against workflow requirements
"""

import logging
from typing import Dict, Any, List

from app.create.workflow_loader import WorkflowConfig, InputConfig

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of input validation"""
    
    def __init__(self):
        self.is_valid = True
        self.errors: List[Dict[str, str]] = []
        self.warnings: List[Dict[str, str]] = []
    
    def add_error(self, field: str, message: str):
        """Add validation error"""
        self.is_valid = False
        self.errors.append({'field': field, 'message': message})
        logger.debug(f"Validation error - {field}: {message}")
    
    def add_warning(self, field: str, message: str):
        """Add validation warning"""
        self.warnings.append({'field': field, 'message': message})
        logger.debug(f"Validation warning - {field}: {message}")


class WorkflowValidator:
    """Validates workflow inputs"""
    
    def __init__(self, config: WorkflowConfig):
        """
        Initialize validator
        
        Args:
            config: Workflow configuration
        """
        self.config = config
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> ValidationResult:
        """
        Validate all inputs
        
        Args:
            inputs: User input values
            
        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()
        
        # Validate each input
        for input_config in self.config.inputs:
            try:
                # Check if input is conditionally shown
                if input_config.depends_on:
                    if not self._check_dependency(inputs, input_config.depends_on):
                        logger.debug(f"Skipping validation for {input_config.id} (dependency not met)")
                        continue
                
                # Validate the input
                self._validate_input(input_config, inputs, result)
                
            except Exception as e:
                logger.error(f"Error validating input {input_config.id}: {e}", exc_info=True)
                result.add_error(input_config.id, f"Validation error: {str(e)}")
        
        return result
    
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
    
    def _validate_input(self, config: InputConfig, inputs: Dict[str, Any], result: ValidationResult):
        """
        Validate single input
        
        Args:
            config: Input configuration
            inputs: User input values
            result: ValidationResult to update
        """
        value = inputs.get(config.id)
        
        # Check required
        if config.required and (value is None or value == ''):
            result.add_error(config.id, f'{config.label} is required')
            return
        
        # Skip further validation if no value provided
        if value is None or value == '':
            return
        
        # Type-specific validation
        input_type = config.type
        
        if input_type == 'slider':
            self._validate_slider(config, value, result)
        elif input_type == 'image':
            self._validate_image(config, value, result)
        elif input_type == 'text' or input_type == 'textarea':
            self._validate_text(config, value, result)
        elif input_type == 'high_low_pair_model':
            self._validate_high_low_model(config, value, result)
        elif input_type == 'high_low_pair_lora_list':
            self._validate_lora_list(config, value, result)
        elif input_type == 'single_model':
            self._validate_single_model(config, value, result)
        elif input_type == 'dropdown':
            self._validate_dropdown(config, value, result)
        elif input_type == 'toggle':
            self._validate_toggle(config, value, result)
    
    def _validate_slider(self, config: InputConfig, value: Any, result: ValidationResult):
        """Validate slider value in range"""
        try:
            numeric_value = float(value)
            
            if config.min is not None and numeric_value < config.min:
                result.add_error(
                    config.id,
                    f'{config.label} must be at least {config.min}'
                )
            
            if config.max is not None and numeric_value > config.max:
                result.add_error(
                    config.id,
                    f'{config.label} must be at most {config.max}'
                )
            
        except (TypeError, ValueError):
            result.add_error(
                config.id,
                f'{config.label} must be a number'
            )
    
    def _validate_image(self, config: InputConfig, value: Any, result: ValidationResult):
        """Validate image input"""
        if not isinstance(value, str):
            result.add_error(config.id, f'{config.label} must be a string (filename or base64)')
            return
        
        # Allow base64 data URLs (from web UI uploads)
        if value.startswith('data:image/'):
            # Validate it's a proper data URL format
            if not ';base64,' in value:
                result.add_error(config.id, f'{config.label} has invalid base64 format')
            return
        
        # Check if filename has valid extension (for file paths)
        if config.accept:
            valid_extensions = [ext.replace('image/', '.') for ext in config.accept.split(',')]
            if not any(value.lower().endswith(ext) for ext in valid_extensions):
                result.add_error(
                    config.id,
                    f'{config.label} must be one of: {", ".join(valid_extensions)}'
                )
    
    def _validate_text(self, config: InputConfig, value: Any, result: ValidationResult):
        """Validate text input"""
        if not isinstance(value, str):
            result.add_error(config.id, f'{config.label} must be text')
            return
        
        # Could add min/max length validation if needed
        if config.min and len(value) < config.min:
            result.add_error(
                config.id,
                f'{config.label} must be at least {config.min} characters'
            )
        
        if config.max and len(value) > config.max:
            result.add_error(
                config.id,
                f'{config.label} must be at most {config.max} characters'
            )
    
    def _validate_high_low_model(self, config: InputConfig, value: Any, result: ValidationResult):
        """Validate high-low noise model pair"""
        # If value is empty, skip validation unless required
        if not value or (isinstance(value, dict) and not value.get('highNoisePath') and not value.get('lowNoisePath')):
            if config.required:
                result.add_error(config.id, f'{config.label} is required')
            return
        
        if not isinstance(value, dict):
            result.add_error(config.id, f'{config.label} must be an object')
            return
        
        if 'highNoisePath' not in value or not value['highNoisePath']:
            result.add_error(config.id, f'{config.label} requires high noise model path')
        
        if 'lowNoisePath' not in value or not value['lowNoisePath']:
            result.add_error(config.id, f'{config.label} requires low noise model path')
    
    def _validate_lora_list(self, config: InputConfig, value: Any, result: ValidationResult):
        """Validate LoRA list"""
        if not isinstance(value, list):
            result.add_error(config.id, f'{config.label} must be a list')
            return
        
        # Validate each LoRA
        for idx, lora in enumerate(value):
            if not isinstance(lora, dict):
                result.add_error(config.id, f'LoRA {idx + 1} must be an object')
                continue
            
            if 'highNoisePath' not in lora or not lora['highNoisePath']:
                result.add_error(config.id, f'LoRA {idx + 1} requires high noise path')
            
            if 'lowNoisePath' not in lora or not lora['lowNoisePath']:
                result.add_error(config.id, f'LoRA {idx + 1} requires low noise path')
            
            if 'strength' in lora:
                try:
                    strength = float(lora['strength'])
                    if strength < 0 or strength > 2:
                        result.add_warning(
                            config.id,
                            f'LoRA {idx + 1} strength {strength} is outside typical range (0-2)'
                        )
                except (TypeError, ValueError):
                    result.add_error(config.id, f'LoRA {idx + 1} strength must be a number')
    
    def _validate_single_model(self, config: InputConfig, value: Any, result: ValidationResult):
        """Validate single model selector"""
        # If value is empty dict, null, or empty string, skip validation unless required
        if not value or (isinstance(value, dict) and not value.get('path')):
            if config.required:
                result.add_error(config.id, f'{config.label} is required')
            return
        
        # Accept both string (default from YAML) and object (from component selection)
        if isinstance(value, str):
            # String value - this is a model path (e.g., from default in YAML)
            if not value:
                if config.required:
                    result.add_error(config.id, f'{config.label} is required')
            return
        
        if not isinstance(value, dict):
            result.add_error(config.id, f'{config.label} must be an object or string')
            return
        
        if 'path' not in value or not value['path']:
            result.add_error(config.id, f'{config.label} requires model path')
    
    def _validate_dropdown(self, config: InputConfig, value: Any, result: ValidationResult):
        """Validate dropdown selection"""
        if config.options and value not in config.options:
            result.add_error(
                config.id,
                f'{config.label} must be one of: {", ".join(config.options)}'
            )
    
    def _validate_toggle(self, config: InputConfig, value: Any, result: ValidationResult):
        """Validate toggle value"""
        if not isinstance(value, bool):
            result.add_error(config.id, f'{config.label} must be true or false')
