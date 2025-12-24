"""
Adapter to convert UI inputs to workflow interpreter format
"""
import logging
from typing import Dict, Any
from pathlib import Path

from .workflow_interpreter import WorkflowInterpreter

logger = logging.getLogger(__name__)


class InterpreterAdapter:
    """Adapts UI inputs to workflow interpreter format and generates workflows"""
    
    def __init__(self, workflow_id: str, wrapper_path: Path):
        """
        Initialize adapter with workflow configuration
        
        Args:
            workflow_id: Workflow identifier
            wrapper_path: Path to .webui.yml wrapper file
        """
        self.workflow_id = workflow_id
        self.interpreter = WorkflowInterpreter(str(wrapper_path))
        logger.info(f"Initialized interpreter for workflow: {workflow_id}")
    
    def convert_ui_inputs_to_interpreter_format(self, ui_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert flat UI inputs to the nested structure expected by interpreter
        
        Args:
            ui_inputs: Flat dictionary from UI {field_id: value}
            
        Returns:
            Nested dictionary organized by sections
        """
        interpreter_inputs = {
            "basic_settings": {},
            "generation_parameters": {},
            "model_selection": {},
            "advanced_features": {
                "output_enhancement": {},
                "quality_enhancements": {},
                "performance_memory": {},
                "automatic_prompting": {}
            }
        }
        
        # Define section mappings
        basic_fields = {'input_image', 'positive_prompt', 'negative_prompt', 'seed'}
        generation_fields = {'size_x', 'size_y', 'duration', 'steps', 'cfg', 'frame_rate', 'speed', 'upscale_ratio'}
        model_fields = {'main_model', 'loras', 'clip_model', 'vae_model', 'upscale_model'}
        
        output_enhancement_fields = {'save_last_frame', 'enable_interpolation', 'use_upscaler', 'enable_upscale_interpolation'}
        quality_enhancement_fields = {'enable_video_enhancer', 'enable_cfg_zero_star', 'enable_speed_regulation', 'enable_normalized_attention'}
        performance_fields = {'enable_magcache', 'enable_torch_compile', 'enable_block_swap', 'vram_reduction'}
        auto_prompt_fields = {'enable_auto_prompt'}
        
        # Map inputs to appropriate sections
        for field_id, value in ui_inputs.items():
            if field_id in basic_fields:
                interpreter_inputs["basic_settings"][field_id] = value
            elif field_id in generation_fields:
                interpreter_inputs["generation_parameters"][field_id] = value
            elif field_id in model_fields:
                # Handle special model formats
                if field_id == 'main_model' and isinstance(value, dict):
                    # Convert to high_noise/low_noise format
                    interpreter_inputs["model_selection"]["main_model"] = {
                        "high_noise": value.get('highNoisePath', ''),
                        "low_noise": value.get('lowNoisePath', '')
                    }
                elif field_id == 'loras' and isinstance(value, list):
                    # Convert LoRA list format
                    converted_loras = []
                    for lora in value:
                        if isinstance(lora, dict):
                            converted_lora = {
                                "high_noise": lora.get('highNoisePath', ''),
                                "low_noise": lora.get('lowNoisePath', ''),
                                "strength": lora.get('strength', 1.0),
                                "enabled": lora.get('enabled', True)
                            }
                            converted_loras.append(converted_lora)
                    interpreter_inputs["model_selection"]["loras"] = converted_loras
                else:
                    interpreter_inputs["model_selection"][field_id] = value
            elif field_id in output_enhancement_fields:
                # Convert node_mode_toggle to boolean (0 = true, 2+ = false)
                bool_value = (value == 0) if isinstance(value, int) else bool(value)
                interpreter_inputs["advanced_features"]["output_enhancement"][field_id] = bool_value
            elif field_id in quality_enhancement_fields:
                bool_value = (value == 0) if isinstance(value, int) else bool(value)
                interpreter_inputs["advanced_features"]["quality_enhancements"][field_id] = bool_value
            elif field_id in performance_fields:
                if field_id == 'vram_reduction':
                    # Keep numeric value
                    interpreter_inputs["advanced_features"]["performance_memory"][field_id] = value
                else:
                    bool_value = (value == 0) if isinstance(value, int) else bool(value)
                    interpreter_inputs["advanced_features"]["performance_memory"][field_id] = bool_value
            elif field_id in auto_prompt_fields:
                bool_value = (value == 0) if isinstance(value, int) else bool(value)
                interpreter_inputs["advanced_features"]["automatic_prompting"][field_id] = bool_value
            else:
                logger.warning(f"Unknown field: {field_id}")
        
        return {"inputs": interpreter_inputs}
    
    def generate(self, ui_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate workflow from UI inputs
        
        Args:
            ui_inputs: Flat dictionary from UI
            
        Returns:
            Generated workflow dictionary
        """
        logger.info(f"Generating workflow for {self.workflow_id}")
        
        # Convert UI inputs to interpreter format
        interpreter_inputs = self.convert_ui_inputs_to_interpreter_format(ui_inputs)
        logger.debug(f"Converted inputs: {list(interpreter_inputs.get('inputs', {}).keys())}")
        
        # Generate actions from inputs
        actions = self.interpreter.generate_actions(interpreter_inputs)
        logger.info(f"Generated {len(actions)} actions")
        
        # Load base workflow
        workflow = self.interpreter._load_workflow()
        
        # Apply actions to workflow
        modified_workflow = self.interpreter.apply_actions(workflow, actions)
        logger.info(f"Applied actions to workflow")
        
        return modified_workflow
    
    def get_input_summary(self, ui_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary of key inputs for metadata"""
        summary = {}
        key_fields = ['positive_prompt', 'negative_prompt', 'duration', 'steps', 'cfg', 'seed']
        
        for field in key_fields:
            if field in ui_inputs:
                value = ui_inputs[field]
                # Truncate long strings
                if isinstance(value, str) and len(value) > 50:
                    summary[field] = value[:50] + "..."
                else:
                    summary[field] = value
        
        return summary
