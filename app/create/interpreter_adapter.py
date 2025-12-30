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
        
        # Seed handling: -1 means random, so generate a random seed
        seed_value = int(ui_inputs.get('seed', -1))
        if seed_value == -1:
            import random
            seed_value = random.randint(0, 2**32 - 1)  # Generate random 32-bit seed
        interpreter_inputs["basic_settings"]["seed"] = seed_value
        
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
        # Output enhancement - Three independent output pipelines:
        # 1. save_interpoled_output: Standalone Interpolation (nodes 431 + 433)
        # 2. save_upscaled_output: Standalone Upscaler (nodes 385 + 419)
        # 3. save_upint_output: Combined UPINT (nodes 442 + 437 + 443)
        
        # Map old UI field names to new structure
        # Old: enable_interpolation -> New: save_interpoled_output
        # Old: use_upscaler -> New: save_upscaled_output
        # Old: enable_upscale_interpolation -> New: save_upint_output
        interpreter_inputs["advanced_features"]["output_enhancement"] = {
            "save_last_frame": mode_to_bool(ui_inputs.get('save_last_frame', 2)),
            "save_original_output": True,  # Always enabled in base workflow
            "save_interpoled_output": mode_to_bool(ui_inputs.get('enable_interpolation', 2)),
            "save_upscaled_output": mode_to_bool(ui_inputs.get('use_upscaler', 2)),
            "save_upint_output": mode_to_bool(ui_inputs.get('enable_upscale_interpolation', 2))
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
        logger.info(f"📋 InterpreterAdapter.generate() called for {self.workflow_id}")
        logger.info(f"📥 Received {len(ui_inputs)} UI input fields")
        
        # Convert UI inputs to interpreter format
        logger.info(f"🔄 Converting UI inputs to interpreter format...")
        interpreter_inputs = self.convert_ui_inputs_to_interpreter_format(ui_inputs)
        input_sections = list(interpreter_inputs.get('inputs', {}).keys())
        logger.info(f"✅ Converted to {len(input_sections)} sections: {input_sections}")
        
        # Log field counts per section
        for section, fields in interpreter_inputs.get('inputs', {}).items():
            if isinstance(fields, dict):
                logger.info(f"   • {section}: {len(fields)} field(s)")
        
        # Generate actions from inputs
        logger.info(f"⚙️  Calling interpreter.generate_actions()...")
        actions = self.interpreter.generate_actions(interpreter_inputs)
        logger.info(f"✅ Generated {len(actions)} actions from interpreter")
        
        # Load base workflow
        logger.info(f"📂 Loading base workflow...")
        workflow = self.interpreter._load_workflow()
        logger.info(f"✅ Loaded base workflow with {len(workflow.get('nodes', []))} nodes")
        
        # Apply actions to workflow
        logger.info(f"🔧 Applying {len(actions)} actions to workflow...")
        modified_workflow = self.interpreter.apply_actions(workflow, actions)
        logger.info(f"✅ Successfully applied all actions to workflow")
        logger.info(f"📊 Final workflow has {len(modified_workflow.get('nodes', []))} nodes")
        
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
