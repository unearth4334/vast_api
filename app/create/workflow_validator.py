#!/usr/bin/env python3
"""
Workflow Validator - Validate user inputs against workflow requirements.
Provides detailed error messages for invalid inputs.
"""

import logging
from typing import Dict, List, Any, Optional

from .workflow_loader import WorkflowConfig, InputConfig

logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_MAX_LORA_ITEMS = 5


class ValidationResult:
    """Result of input validation"""
    
    def __init__(self):
        self.is_valid = True
        self.errors: List[Dict[str, str]] = []
        self.warnings: List[Dict[str, str]] = []
    
    def add_error(self, field: str, message: str):
        """Add a validation error"""
        self.is_valid = False
        self.errors.append({'field': field, 'message': message})
    
    def add_warning(self, field: str, message: str):
        """Add a validation warning (doesn't fail validation)"""
        self.warnings.append({'field': field, 'message': message})
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'is_valid': self.is_valid,
            'errors': self.errors,
            'warnings': self.warnings,
        }


class WorkflowValidator:
    """Validate user inputs against workflow configuration"""
    
    def __init__(self, config: WorkflowConfig):
        """
        Initialize validator with workflow config.
        
        Args:
            config: WorkflowConfig object with input definitions
        """
        self.config = config
    
    def validate_inputs(self, inputs: Dict) -> ValidationResult:
        """
        Validate all inputs against workflow configuration.
        
        Args:
            inputs: Dictionary of user-provided input values
            
        Returns:
            ValidationResult with any errors and warnings
        """
        result = ValidationResult()
        
        for input_config in self.config.inputs:
            self._validate_input(input_config, inputs, result)
        
        return result
    
    def _validate_input(self, config: InputConfig, inputs: Dict, result: ValidationResult):
        """Validate a single input field"""
        input_id = config.id
        value = inputs.get(input_id)
        
        # Check depends_on condition first
        if config.depends_on:
            dep_field = config.depends_on.get('field')
            dep_value = config.depends_on.get('value')
            if dep_field and inputs.get(dep_field) != dep_value:
                # Dependency not satisfied, skip validation
                return
        
        # Check required fields
        if config.required:
            if value is None or value == '':
                result.add_error(input_id, f'{config.label} is required')
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
        elif input_type in ('text', 'textarea'):
            self._validate_text(config, value, result)
        elif input_type == 'seed':
            self._validate_seed(config, value, result)
        elif input_type == 'checkbox':
            self._validate_checkbox(config, value, result)
        elif input_type == 'high_low_pair_model':
            self._validate_high_low_model(config, value, result)
        elif input_type == 'high_low_pair_lora_list':
            self._validate_lora_list(config, value, result)
        elif input_type == 'single_model':
            self._validate_single_model(config, value, result)
        elif input_type == 'select':
            self._validate_select(config, value, result)
    
    def _validate_slider(self, config: InputConfig, value: Any, result: ValidationResult):
        """Validate slider value is within range"""
        input_id = config.id
        
        # Convert to float if needed
        try:
            numeric_value = float(value)
        except (ValueError, TypeError):
            result.add_error(input_id, f'{config.label} must be a number')
            return
        
        # Check min/max bounds
        if config.min is not None and numeric_value < config.min:
            result.add_error(
                input_id,
                f'{config.label} must be at least {config.min}'
            )
        
        if config.max is not None and numeric_value > config.max:
            result.add_error(
                input_id,
                f'{config.label} must be at most {config.max}'
            )
    
    def _validate_image(self, config: InputConfig, value: Any, result: ValidationResult):
        """Validate image input"""
        input_id = config.id
        
        if not isinstance(value, str):
            result.add_error(input_id, f'{config.label} must be a string (filename or path)')
            return
        
        if not value.strip():
            if config.required:
                result.add_error(input_id, f'{config.label} is required')
    
    def _validate_text(self, config: InputConfig, value: Any, result: ValidationResult):
        """Validate text/textarea input"""
        input_id = config.id
        
        if not isinstance(value, str):
            result.add_error(input_id, f'{config.label} must be a string')
            return
        
        # Check max length
        if config.max_length and len(value) > config.max_length:
            result.add_error(
                input_id,
                f'{config.label} must be at most {config.max_length} characters'
            )
    
    def _validate_seed(self, config: InputConfig, value: Any, result: ValidationResult):
        """Validate seed input"""
        input_id = config.id
        
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            result.add_error(input_id, f'{config.label} must be an integer')
            return
        
        # -1 is valid (random), otherwise must be non-negative
        if int_value < -1:
            result.add_error(input_id, f'{config.label} must be -1 (random) or a non-negative integer')
    
    def _validate_checkbox(self, config: InputConfig, value: Any, result: ValidationResult):
        """Validate checkbox input"""
        input_id = config.id
        
        if not isinstance(value, bool):
            # Try to coerce
            if value in (1, '1', 'true', 'True', 'yes', 'Yes'):
                return
            if value in (0, '0', 'false', 'False', 'no', 'No'):
                return
            result.add_error(input_id, f'{config.label} must be a boolean')
    
    def _validate_high_low_model(self, config: InputConfig, value: Any, result: ValidationResult):
        """Validate high-low noise model pair"""
        input_id = config.id
        
        if not isinstance(value, dict):
            result.add_error(input_id, f'{config.label} must be an object with highNoisePath and lowNoisePath')
            return
        
        high_path = value.get('highNoisePath')
        low_path = value.get('lowNoisePath')
        
        if config.required:
            if not high_path:
                result.add_error(input_id, f'{config.label}: High noise model path is required')
            if not low_path:
                result.add_error(input_id, f'{config.label}: Low noise model path is required')
    
    def _validate_lora_list(self, config: InputConfig, value: Any, result: ValidationResult):
        """Validate LoRA list"""
        input_id = config.id
        
        if not isinstance(value, list):
            result.add_error(input_id, f'{config.label} must be an array')
            return
        
        # Check max items using config or default constant
        max_items = DEFAULT_MAX_LORA_ITEMS
        if hasattr(config, 'max_items') and config.max_items:
            max_items = config.max_items
        
        if len(value) > max_items:
            result.add_warning(input_id, f'{config.label} has more than {max_items} items, some may be ignored')
        
        # Validate each LoRA entry
        for idx, lora in enumerate(value):
            if not isinstance(lora, dict):
                result.add_error(input_id, f'{config.label}[{idx}] must be an object')
                continue
            
            if not lora.get('highNoisePath') and not lora.get('lowNoisePath'):
                result.add_warning(input_id, f'{config.label}[{idx}] has no model paths specified')
    
    def _validate_single_model(self, config: InputConfig, value: Any, result: ValidationResult):
        """Validate single model selection"""
        input_id = config.id
        
        # Handle both string and dict formats
        if isinstance(value, dict):
            path = value.get('path', '')
        elif isinstance(value, str):
            path = value
        else:
            result.add_error(input_id, f'{config.label} must be a string or object with path')
            return
        
        if config.required and not path:
            result.add_error(input_id, f'{config.label} is required')
    
    def _validate_select(self, config: InputConfig, value: Any, result: ValidationResult):
        """Validate select/dropdown input"""
        input_id = config.id
        
        if not isinstance(value, str):
            result.add_error(input_id, f'{config.label} must be a string')
            return
        
        # Check if value is in options (if options defined)
        if config.options and value not in config.options:
            result.add_error(
                input_id,
                f'{config.label} must be one of: {", ".join(config.options)}'
            )
