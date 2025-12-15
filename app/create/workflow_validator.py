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


class TemplateValidationResult:
    """Results from template validation"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        
    def add_error(self, message: str):
        """Add an error message"""
        self.errors.append(message)
        logger.error(f"❌ Template Validation Error: {message}")
        
    def add_warning(self, message: str):
        """Add a warning message"""
        self.warnings.append(message)
        logger.warning(f"⚠️ Template Validation Warning: {message}")
        
    def add_info(self, message: str):
        """Add an info message"""
        self.info.append(message)
        logger.info(f"ℹ️ Template Validation Info: {message}")
        
    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)"""
        return len(self.errors) == 0
        
    @property
    def has_warnings(self) -> bool:
        """Check if there are warnings"""
        return len(self.warnings) > 0
        
    def summary(self) -> str:
        """Get validation summary"""
        status = "✅ PASSED" if self.is_valid else "❌ FAILED"
        lines = [
            "=" * 80,
            f"Template Validation Results: {status}",
            "=" * 80,
            f"Errors: {len(self.errors)}",
            f"Warnings: {len(self.warnings)}",
            f"Info: {len(self.info)}",
            "=" * 80
        ]
        
        if self.errors:
            lines.append("\nErrors:")
            for err in self.errors:
                lines.append(f"  • {err}")
                
        if self.warnings:
            lines.append("\nWarnings:")
            for warn in self.warnings:
                lines.append(f"  • {warn}")
        
        return "\n".join(lines)


class TemplateValidator:
    """Validates workflow configurations against templates"""
    
    @staticmethod
    def validate_template_mapping(config: WorkflowConfig, template: dict) -> TemplateValidationResult:
        """
        Validate workflow configuration against template
        
        Args:
            config: Workflow configuration
            template: Workflow template JSON
            
        Returns:
            TemplateValidationResult object
        """
        import json
        import re
        
        result = TemplateValidationResult()
        
        # Skip validation if not configured
        if not config.validation:
            result.add_info("No validation configuration, skipping validation")
            return result
            
        val_config = config.validation
        result.add_info(f"Starting validation (strict={val_config.strict_mode})")
        
        # Extract template data
        template_str = json.dumps(template)
        template_nodes = {str(node['id']): node for node in template.get('nodes', [])}
        
        # Validate tokens
        if val_config.check_tokens:
            TemplateValidator._validate_tokens(config, template_str, result)
            
        # Validate node IDs
        if val_config.check_node_ids:
            TemplateValidator._validate_node_ids(config, template_nodes, result)
            
        # Validate widget structures
        if val_config.check_widgets:
            TemplateValidator._validate_widgets(config, template_nodes, result)
            
        # Log summary
        logger.info(result.summary())
        
        return result
    
    @staticmethod
    def _validate_tokens(config: WorkflowConfig, template_str: str, result: TemplateValidationResult):
        """Validate that all tokens in config exist in template"""
        import re
        
        result.add_info("Checking token mappings...")
        
        # Extract all tokens from template
        template_tokens = set(re.findall(r'\{\{([A-Z_]+)\}\}', template_str))
        
        # Check each input's tokens
        config_tokens = set()
        for inp in config.inputs:
            # Single token
            if inp.token:
                token_name = inp.token.strip('{}')
                config_tokens.add(token_name)
                
                if token_name not in template_tokens:
                    msg = f"Input '{inp.id}': Token {inp.token} not found in template"
                    if config.validation.warn_on_mismatch:
                        result.add_warning(msg)
                    else:
                        result.add_error(msg)
                else:
                    # Count occurrences
                    count = template_str.count(inp.token)
                    result.add_info(f"Input '{inp.id}': Token {inp.token} found {count} time(s)")
                    
            # Multiple tokens
            if inp.tokens:
                for key, token in inp.tokens.items():
                    token_name = token.strip('{}')
                    config_tokens.add(token_name)
                    
                    if token_name not in template_tokens:
                        msg = f"Input '{inp.id}': Token {token} ({key}) not found in template"
                        if config.validation.warn_on_mismatch:
                            result.add_warning(msg)
                        else:
                            result.add_error(msg)
                    else:
                        count = template_str.count(token)
                        result.add_info(f"Input '{inp.id}': Token {token} ({key}) found {count} time(s)")
        
        # Check for unused tokens in template
        unused_tokens = template_tokens - config_tokens
        if unused_tokens:
            result.add_warning(f"Template has {len(unused_tokens)} unused token(s): {sorted(unused_tokens)}")
            
        result.add_info(f"Token validation complete: {len(config_tokens)} token(s) checked")
    
    @staticmethod
    def _validate_node_ids(config: WorkflowConfig, template_nodes: Dict[str, dict], result: TemplateValidationResult):
        """Validate that all node_ids in config exist in template"""
        result.add_info("Checking node ID mappings...")
        
        checked_nodes = set()
        
        for inp in config.inputs:
            # Single node ID
            if inp.node_id:
                checked_nodes.add(inp.node_id)
                if inp.node_id not in template_nodes:
                    msg = f"Input '{inp.id}': Node ID '{inp.node_id}' not found in template"
                    if config.validation.warn_on_mismatch:
                        result.add_warning(msg)
                    else:
                        result.add_error(msg)
                else:
                    node = template_nodes[inp.node_id]
                    result.add_info(f"Input '{inp.id}': Node {inp.node_id} ({node.get('type', 'unknown')}) found")
                    
            # Multiple node IDs
            if inp.node_ids:
                for node_id in inp.node_ids:
                    checked_nodes.add(node_id)
                    if node_id not in template_nodes:
                        msg = f"Input '{inp.id}': Node ID '{node_id}' not found in template"
                        if config.validation.warn_on_mismatch:
                            result.add_warning(msg)
                        else:
                            result.add_error(msg)
                    else:
                        node = template_nodes[node_id]
                        result.add_info(f"Input '{inp.id}': Node {node_id} ({node.get('type', 'unknown')}) found")
        
        result.add_info(f"Node ID validation complete: {len(checked_nodes)} node(s) checked")
    
    @staticmethod
    def _validate_widgets(config: WorkflowConfig, template_nodes: Dict[str, dict], result: TemplateValidationResult):
        """Validate widget structures against metadata"""
        result.add_info("Checking widget structures...")
        
        validated_count = 0
        
        for inp in config.inputs:
            # Only validate if metadata is provided
            if not inp.metadata or not inp.metadata.target_nodes:
                continue
                
            for target_info in inp.metadata.target_nodes:
                node_id = target_info.get('node_id')
                if not node_id:
                    continue
                    
                if node_id not in template_nodes:
                    result.add_warning(f"Input '{inp.id}': Metadata references unknown node {node_id}")
                    continue
                    
                node = template_nodes[node_id]
                validated_count += 1
                
                # Check widget type if specified
                if inp.metadata.widget_type:
                    actual_type = node.get('type')
                    expected_type = inp.metadata.widget_type
                    
                    if actual_type != expected_type:
                        msg = (f"Input '{inp.id}': Node {node_id} type mismatch - "
                               f"expected '{expected_type}', got '{actual_type}'")
                        result.add_warning(msg)
                    else:
                        result.add_info(f"Input '{inp.id}': Node {node_id} type '{actual_type}' validated")
                        
                # Check widget_values structure if indices specified
                if inp.metadata.widget_indices and 'widgets_values' in node:
                    widgets_values = node['widgets_values']
                    max_index = max(inp.metadata.widget_indices)
                    
                    if max_index >= len(widgets_values):
                        msg = (f"Input '{inp.id}': Node {node_id} widget_values has {len(widgets_values)} elements, "
                               f"but metadata references index {max_index}")
                        result.add_warning(msg)
                    else:
                        result.add_info(
                            f"Input '{inp.id}': Node {node_id} widget indices {inp.metadata.widget_indices} validated"
                        )
        
        result.add_info(f"Widget validation complete: {validated_count} widget(s) checked")
    
    @staticmethod
    def validate_workflow_file(workflow_id: str) -> TemplateValidationResult:
        """
        Load and validate a workflow by ID
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            TemplateValidationResult object
        """
        from app.create.workflow_loader import WorkflowLoader
        
        # Load workflow config
        config = WorkflowLoader.load_workflow(workflow_id)
        
        # Load template
        template = WorkflowLoader.load_workflow_json(workflow_id)
        
        # Validate
        return TemplateValidator.validate_template_mapping(config, template)
