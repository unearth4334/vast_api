"""
Template management system for VastAI setup configurations
"""

import os
import yaml
from typing import Dict, List, Any, Optional

class TemplateManager:
    """Manages setup templates for different VastAI configurations"""
    
    def __init__(self, templates_dir: Optional[str] = None):
        if templates_dir is None:
            templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.templates_dir = templates_dir
        self._templates_cache = {}
    
    def load_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Load a specific template by name"""
        if template_name in self._templates_cache:
            return self._templates_cache[template_name]
        
        template_file = os.path.join(self.templates_dir, f'templates_{template_name.lower()}.yml')
        
        if not os.path.exists(template_file):
            return None
        
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template_data = yaml.safe_load(f)
            
            # Validate required fields
            required_fields = ['name', 'setup_steps', 'ui_config']
            for field in required_fields:
                if field not in template_data:
                    raise ValueError(f"Template missing required field: {field}")
            
            self._templates_cache[template_name] = template_data
            return template_data
            
        except (yaml.YAMLError, IOError, ValueError) as e:
            print(f"Error loading template {template_name}: {e}")
            return None
    
    def get_available_templates(self) -> List[Dict[str, str]]:
        """Get list of all available templates"""
        templates = []
        
        if not os.path.exists(self.templates_dir):
            return templates
        
        for filename in os.listdir(self.templates_dir):
            if filename.startswith('templates_') and filename.endswith('.yml'):
                # Extract template name from filename
                template_name = filename[10:-4]  # Remove 'templates_' prefix and '.yml' suffix
                
                template_data = self.load_template(template_name)
                if template_data:
                    templates.append({
                        'id': template_name,
                        'name': template_data.get('name', template_name.title()),
                        'description': template_data.get('description', 'No description available'),
                        'version': template_data.get('version', '1.0.0')
                    })
        
        return templates
    
    def get_template_ui_config(self, template_name: str) -> Dict[str, Any]:
        """Get UI configuration for a specific template"""
        template_data = self.load_template(template_name)
        if not template_data:
            return {}
        
        return template_data.get('ui_config', {})
    
    def get_template_setup_steps(self, template_name: str) -> List[Dict[str, Any]]:
        """Get setup steps for a specific template"""
        template_data = self.load_template(template_name)
        if not template_data:
            return []
        
        return template_data.get('setup_steps', [])
    
    def get_template_environment(self, template_name: str) -> Dict[str, str]:
        """Get environment configuration for a specific template"""
        template_data = self.load_template(template_name)
        if not template_data:
            return {}
        
        return template_data.get('environment', {})
    
    def validate_template(self, template_data: Dict[str, Any]) -> List[str]:
        """Validate template structure and return list of validation errors"""
        errors = []
        
        # Check required top-level fields
        required_fields = ['name', 'setup_steps', 'ui_config']
        for field in required_fields:
            if field not in template_data:
                errors.append(f"Missing required field: {field}")
        
        # Validate setup_steps structure
        if 'setup_steps' in template_data:
            setup_steps = template_data['setup_steps']
            if not isinstance(setup_steps, list):
                errors.append("setup_steps must be a list")
            else:
                for i, step in enumerate(setup_steps):
                    if not isinstance(step, dict):
                        errors.append(f"setup_steps[{i}] must be a dictionary")
                        continue
                    
                    required_step_fields = ['name', 'type', 'description']
                    for field in required_step_fields:
                        if field not in step:
                            errors.append(f"setup_steps[{i}] missing required field: {field}")
        
        # Validate ui_config structure
        if 'ui_config' in template_data:
            ui_config = template_data['ui_config']
            if not isinstance(ui_config, dict):
                errors.append("ui_config must be a dictionary")
            elif 'setup_buttons' in ui_config:
                setup_buttons = ui_config['setup_buttons']
                if not isinstance(setup_buttons, list):
                    errors.append("ui_config.setup_buttons must be a list")
                else:
                    for i, button in enumerate(setup_buttons):
                        if not isinstance(button, dict):
                            errors.append(f"ui_config.setup_buttons[{i}] must be a dictionary")
                            continue
                        
                        required_button_fields = ['label', 'action', 'style']
                        for field in required_button_fields:
                            if field not in button:
                                errors.append(f"ui_config.setup_buttons[{i}] missing required field: {field}")
        
        return errors

# Global template manager instance
template_manager = TemplateManager()