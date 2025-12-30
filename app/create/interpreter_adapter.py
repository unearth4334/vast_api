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
        
        Follows the WorkflowInterpreter Input JSON Specification:
        - Extracts paths from model objects
        - Converts ComfyUI mode codes (0/2/4) to booleans
        - Transforms model keys (highNoisePath → high_noise)
        - Ensures correct type conversions (int vs float)
        
        Args:
            ui_inputs: Flat dictionary from UI {field_id: value}
            
        Returns:
            Nested dictionary organized by sections with "inputs" wrapper
        """
        def mode_to_bool(value):
            """Convert ComfyUI node mode to boolean (0=enabled, 2/4=disabled)"""
            return value == 0 if isinstance(value, int) else bool(value)
        
        def extract_path(obj):
            """Extract path string from model object or return as-is"""
            if obj is None:
                return None
            if isinstance(obj, dict):
                return obj.get("path")
            return obj
        
        def ensure_float(value, default=0.0):
            """Convert value to float with proper handling"""
            try:
                return float(value) if value is not None else default
            except (ValueError, TypeError):
                return default
        
        # Initialize structure
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
        
        # === BASIC SETTINGS ===
        input_image = ui_inputs.get('input_image')
        # Handle both string filenames and objects with path
        if isinstance(input_image, dict):
            interpreter_inputs["basic_settings"]["input_image"] = input_image.get('path')
        else:
            interpreter_inputs["basic_settings"]["input_image"] = input_image
            
        interpreter_inputs["basic_settings"]["positive_prompt"] = ui_inputs.get('positive_prompt', '')
        interpreter_inputs["basic_settings"]["negative_prompt"] = ui_inputs.get('negative_prompt', '')
        interpreter_inputs["basic_settings"]["seed"] = int(ui_inputs.get('seed', -1))
        
        # === MODEL SELECTION ===
        # Main model - transform keys
        main_model = ui_inputs.get('main_model', {})
        if isinstance(main_model, dict):
            high_path = main_model.get('highNoisePath', '')
            low_path = main_model.get('lowNoisePath', '')
            # Strip basePath prefix if present
            base_path = main_model.get('basePath', '')
            if base_path:
                high_path = high_path.replace(f"{base_path}/", "")
                low_path = low_path.replace(f"{base_path}/", "")
            
            interpreter_inputs["model_selection"]["main_model"] = {
                "high_noise": high_path,
                "low_noise": low_path
            }
        
        # LoRAs - transform keys and ensure float strength
        loras = ui_inputs.get('loras', [])
        converted_loras = []
        for lora in loras:
            if isinstance(lora, dict):
                converted_loras.append({
                    "high_noise": lora.get('highNoisePath', ''),
                    "low_noise": lora.get('lowNoisePath', ''),
                    "strength": ensure_float(lora.get('strength', 1.0))
                })
        interpreter_inputs["model_selection"]["loras"] = converted_loras
        
        # Auxiliary models - extract paths
        interpreter_inputs["model_selection"]["clip_model"] = extract_path(ui_inputs.get('clip_model'))
        interpreter_inputs["model_selection"]["vae_model"] = extract_path(ui_inputs.get('vae_model'))
        interpreter_inputs["model_selection"]["upscale_model"] = extract_path(ui_inputs.get('upscale_model'))
        
        # === GENERATION PARAMETERS ===
        interpreter_inputs["generation_parameters"]["size_x"] = int(ui_inputs.get('size_x', 896))
        interpreter_inputs["generation_parameters"]["size_y"] = int(ui_inputs.get('size_y', 1120))
        interpreter_inputs["generation_parameters"]["duration"] = ensure_float(ui_inputs.get('duration', 5.0))
        interpreter_inputs["generation_parameters"]["steps"] = int(ui_inputs.get('steps', 20))
        interpreter_inputs["generation_parameters"]["cfg"] = ensure_float(ui_inputs.get('cfg', 3.5))
        interpreter_inputs["generation_parameters"]["frame_rate"] = ensure_float(ui_inputs.get('frame_rate', 16.0))
        interpreter_inputs["generation_parameters"]["speed"] = ensure_float(ui_inputs.get('speed', 7.0))
        interpreter_inputs["generation_parameters"]["upscale_ratio"] = ensure_float(ui_inputs.get('upscale_ratio', 2.0))
        
        # === ADVANCED FEATURES ===
        # Output enhancement
        enable_interpolation = mode_to_bool(ui_inputs.get('enable_interpolation', 0))
        use_upscaler = mode_to_bool(ui_inputs.get('use_upscaler', 2))
        enable_upscale_interpolation = mode_to_bool(ui_inputs.get('enable_upscale_interpolation', 2))
        
        interpreter_inputs["advanced_features"]["output_enhancement"] = {
            "save_last_frame": mode_to_bool(ui_inputs.get('save_last_frame', 2)),
            "save_original_output": True,  # Always enabled in base workflow
            "save_interpoled_output": enable_interpolation,
            "save_upscaled_output": use_upscaler,
            "save_upint_output": enable_upscale_interpolation,
            "enable_interpolation": enable_interpolation,
            "use_upscaler": use_upscaler,
            "enable_upscale_interpolation": enable_upscale_interpolation
        }
        
        # Quality enhancements
        interpreter_inputs["advanced_features"]["quality_enhancements"] = {
            "enable_video_enhancer": mode_to_bool(ui_inputs.get('enable_video_enhancer', 0)),
            "enable_cfg_zero_star": mode_to_bool(ui_inputs.get('enable_cfg_zero_star', 0)),
            "enable_speed_regulation": mode_to_bool(ui_inputs.get('enable_speed_regulation', 0)),
            "enable_normalized_attention": mode_to_bool(ui_inputs.get('enable_normalized_attention', 0))
        }
        
        # Performance & memory
        interpreter_inputs["advanced_features"]["performance_memory"] = {
            "enable_magcache": mode_to_bool(ui_inputs.get('enable_magcache', 0)),
            "enable_torch_compile": mode_to_bool(ui_inputs.get('enable_torch_compile', 4)),
            "enable_block_swap": mode_to_bool(ui_inputs.get('enable_block_swap', 0)),
            "vram_reduction": int(ui_inputs.get('vram_reduction', 100))
        }
        
        # Automatic prompting
        interpreter_inputs["advanced_features"]["automatic_prompting"] = {
            "enable_auto_prompt": mode_to_bool(ui_inputs.get('enable_auto_prompt', 0))
        }
        
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
