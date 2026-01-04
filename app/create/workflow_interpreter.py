"""
Workflow Interpreter - Applies user inputs to ComfyUI workflows using wrapper configurations.

This module takes a base workflow JSON, a wrapper YAML configuration, and user inputs,
then produces a modified workflow by applying elementary change actions.
"""

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import yaml

import logging

logger = logging.getLogger(__name__)


# Type alias for all action types
ChangeAction = Union[
    'ModifyWidgetAction',
    'ToggleNodeModeAction', 
    'AddLoRAPairAction',
    'ModifyVectorWidgetAction'
]


@dataclass
class ModifyWidgetAction:
    """Change widget value(s) in a node's widgets_values array."""
    node_id: int
    widget_indices: List[int]
    value: Union[int, float, str]
    node_type: str
    action_type: str = "modify_widget"


@dataclass
class ToggleNodeModeAction:
    """Toggle node execution mode (enabled/bypassed/muted)."""
    node_ids: List[int]
    enabled: bool
    enabled_mode: int = 0  # 0 = enabled
    disabled_mode: int = 2  # 2 = bypassed, 4 = muted
    save_node_id: Optional[int] = None  # Optional: VHS_VideoCombine node to toggle save_output
    action_type: str = "toggle_node_mode"


@dataclass
class AddLoRAPairAction:
    """Add high/low noise LoRA pair to Power Lora Loader nodes."""
    high_node_id: int
    low_node_id: int
    lora_path: str
    strength: float
    enabled: bool = True
    action_type: str = "add_lora_pair"


@dataclass
class ModifyVectorWidgetAction:
    """Modify coordinated vector values (e.g., X/Y dimensions in mxSlider2D)."""
    node_id: int
    x_value: Optional[float] = None
    y_value: Optional[float] = None
    x_indices: List[int] = None
    y_indices: List[int] = None
    node_type: str = "mxSlider2D"
    action_type: str = "modify_vector_widget"


class WorkflowInterpreter:
    """
    Interprets user inputs and applies them to a workflow using wrapper configuration.
    
    This class handles the complete workflow modification pipeline:
    1. Load base workflow, wrapper config, and user inputs
    2. Generate change actions from inputs using node_mapping
    3. Apply actions to workflow
    4. Export modified workflow
    """
    
    def __init__(self, wrapper_path: Union[str, Path]):
        """
        Initialize interpreter with a wrapper configuration file.
        
        Args:
            wrapper_path: Path to .webui.yml wrapper file
        """
        self.wrapper_path = Path(wrapper_path)
        self.config = self._load_wrapper()
        self.workflow_path = Path(self.config["workflow_file"])
        self.node_mapping = self.config.get("node_mapping", {})
        
    def _load_wrapper(self) -> Dict:
        """Load and parse wrapper YAML configuration."""
        logger.info(f"Loading wrapper config: {self.wrapper_path}")
        with open(self.wrapper_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    
    def _load_workflow(self, workflow_path: Optional[Path] = None) -> Dict:
        """Load workflow JSON file."""
        path = workflow_path or self.workflow_path
        logger.info(f"Loading workflow: {path}")
        with open(path, "r", encoding="utf-8") as f:
            workflow = json.load(f)
        return workflow
    
    def _load_inputs(self, inputs_path: Union[str, Path]) -> Dict:
        """Load user inputs JSON file."""
        path = Path(inputs_path)
        logger.info(f"Loading inputs: {path}")
        with open(path, "r", encoding="utf-8") as f:
            inputs = json.load(f)
        return inputs
    
    def _index_nodes_by_id(self, workflow: Dict) -> Dict[int, Dict]:
        """Create a lookup dictionary for nodes by their ID."""
        nodes_by_id = {}
        for node in workflow.get("nodes", []):
            nodes_by_id[node["id"]] = node
        return nodes_by_id
    
    def generate_actions(self, inputs: Dict) -> List[ChangeAction]:
        """
        Generate change actions from user inputs using node_mapping.
        
        Args:
            inputs: User input dictionary from JSON file
            
        Returns:
            List of ChangeAction objects to apply
        """
        actions = []
        
        # Flatten nested input structure for easier access
        flat_inputs = self._flatten_inputs(inputs.get("inputs", {}))
        
        logger.info(f"Generating actions from {len(flat_inputs)} inputs")
        
        for input_id, value in flat_inputs.items():
            if input_id not in self.node_mapping:
                logger.debug(f"No mapping for input '{input_id}', skipping")
                continue
                
            mapping = self.node_mapping[input_id]
            action_type = mapping.get("action_type")
            
            if action_type == "modify_widget":
                action = self._make_modify_widget_action(input_id, value, mapping)
                if action:
                    actions.append(action)
                    
            elif action_type == "modify_vector_widget":
                # Vector widgets need special handling - collect both X and Y
                # This is handled by _make_vector_widget_action below
                pass
                
            elif action_type == "toggle_node_mode":
                action = self._make_toggle_mode_action(input_id, value, mapping)
                if action:
                    actions.append(action)
                    
            elif action_type == "add_lora_pair":
                # LoRAs are handled specially since they come as a list
                if input_id == "loras" and isinstance(value, list):
                    for lora in value:
                        lora_actions = self._make_add_lora_action(lora, mapping)
                        if lora_actions:
                            actions.extend(lora_actions)
        
        # Handle vector widgets (need both X and Y values)
        actions.extend(self._make_vector_widget_actions(flat_inputs))
        
        logger.info(f"Generated {len(actions)} actions")
        return actions
    
    def _flatten_inputs(self, inputs: Dict, prefix: str = "") -> Dict[str, Any]:
        """Flatten nested input dictionary to simple key-value pairs."""
        flat = {}
        for key, value in inputs.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict) and not self._is_complex_value(value):
                # Recursively flatten nested dicts
                flat.update(self._flatten_inputs(value, full_key))
            else:
                flat[key] = value  # Use simple key without prefix for node_mapping lookup
        return flat
    
    def _is_complex_value(self, value: Any) -> bool:
        """Check if a dict is a complex value (like model config) vs nested structure."""
        # Complex values have specific keys like 'high_noise', 'low_noise'
        if isinstance(value, dict):
            complex_keys = {"high_noise", "low_noise", "path", "strength", "enabled"}
            return bool(complex_keys & set(value.keys()))
        return False
    
    def _make_modify_widget_action(
        self, input_id: str, value: Any, mapping: Dict
    ) -> Optional[ModifyWidgetAction]:
        """Create a ModifyWidgetAction from input and mapping."""
        node_id = mapping.get("node_id")
        widget_indices = mapping.get("widget_indices", [])
        node_type = mapping.get("node_type", "")
        
        if node_id is None:
            logger.warning(f"No node_id in mapping for '{input_id}'")
            return None
        
        logger.debug(f"Modify widget: {input_id} = {value} -> node {node_id}")
        return ModifyWidgetAction(
            node_id=node_id,
            widget_indices=widget_indices,
            value=value,
            node_type=node_type
        )
    
    def _make_vector_widget_actions(self, flat_inputs: Dict) -> List[ModifyVectorWidgetAction]:
        """Create vector widget actions for coordinated X/Y values."""
        actions = []
        
        # Look for paired X/Y inputs in the mapping
        vector_nodes = {}
        for input_id, mapping in self.node_mapping.items():
            if mapping.get("action_type") == "modify_vector_widget":
                node_id = mapping.get("node_id")
                vector_key = mapping.get("vector_key")  # 'x' or 'y'
                
                if node_id not in vector_nodes:
                    vector_nodes[node_id] = {}
                
                vector_nodes[node_id][vector_key] = {
                    "input_id": input_id,
                    "indices": mapping.get("widget_indices", []),
                    "value": flat_inputs.get(input_id),
                    "node_type": mapping.get("node_type", "mxSlider2D")
                }
        
        # Create actions for each node with vector values
        for node_id, vectors in vector_nodes.items():
            x_data = vectors.get("x", {})
            y_data = vectors.get("y", {})
            
            if x_data.get("value") is not None or y_data.get("value") is not None:
                logger.debug(f"Vector widget: node {node_id}, X={x_data.get('value')}, Y={y_data.get('value')}")
                action = ModifyVectorWidgetAction(
                    node_id=node_id,
                    x_value=x_data.get("value"),
                    y_value=y_data.get("value"),
                    x_indices=x_data.get("indices"),
                    y_indices=y_data.get("indices"),
                    node_type=x_data.get("node_type", "mxSlider2D")
                )
                actions.append(action)
        
        return actions
    
    def _make_toggle_mode_action(
        self, input_id: str, value: bool, mapping: Dict
    ) -> Optional[ToggleNodeModeAction]:
        """Create a ToggleNodeModeAction from input and mapping."""
        node_ids = mapping.get("node_ids", [])
        enabled_mode = mapping.get("enabled_mode", 0)
        disabled_mode = mapping.get("disabled_mode", 2)
        save_node_id = mapping.get("save_node_id")  # Optional VHS_VideoCombine node
        
        if not node_ids:
            logger.warning(f"No node_ids in mapping for '{input_id}'")
            return None
        
        logger.debug(f"Toggle mode: {input_id} = {value} -> nodes {node_ids}")
        return ToggleNodeModeAction(
            node_ids=node_ids,
            enabled=bool(value),
            enabled_mode=enabled_mode,
            disabled_mode=disabled_mode,
            save_node_id=save_node_id
        )
    
    def _make_add_lora_action(
        self, lora: Dict, mapping: Dict
    ) -> Optional[List[AddLoRAPairAction]]:
        """Create AddLoRAPairAction(s) from LoRA config and mapping."""
        high_node_id = mapping.get("high_node_id")
        low_node_id = mapping.get("low_node_id")
        
        if not (high_node_id and low_node_id):
            logger.warning("Missing high_node_id or low_node_id in LoRA mapping")
            return None
        
        # Support both old 'path' format and new 'high_noise'/'low_noise' format
        high_noise = lora.get("high_noise")
        low_noise = lora.get("low_noise")
        strength = lora.get("strength", 1.0)
        enabled = lora.get("enabled", True)
        
        actions = []
        
        # High noise LoRA
        if high_noise:
            logger.debug(f"Add LoRA (high): {high_noise} (strength={strength}) -> node {high_node_id}")
            actions.append(AddLoRAPairAction(
                high_node_id=high_node_id,
                low_node_id=low_node_id,
                lora_path=high_noise,
                strength=strength,
                enabled=enabled
            ))
        
        # Low noise LoRA
        if low_noise:
            logger.debug(f"Add LoRA (low): {low_noise} (strength={strength}) -> node {low_node_id}")
            actions.append(AddLoRAPairAction(
                high_node_id=high_node_id,
                low_node_id=low_node_id,
                lora_path=low_noise,
                strength=strength,
                enabled=enabled
            ))
        
        # Fallback to old 'path' format if neither high_noise nor low_noise specified
        if not high_noise and not low_noise:
            lora_path = lora.get("path", "")
            if lora_path:
                logger.debug(f"Add LoRA: {lora_path} (strength={strength}) -> nodes {high_node_id}/{low_node_id}")
                actions.append(AddLoRAPairAction(
                    high_node_id=high_node_id,
                    low_node_id=low_node_id,
                    lora_path=lora_path,
                    strength=strength,
                    enabled=enabled
                ))
        
        return actions if actions else None
    
    def apply_actions(
        self, 
        workflow: Dict, 
        actions: List[ChangeAction]
    ) -> Dict:
        """
        Apply a list of change actions to a workflow.
        
        Args:
            workflow: Base workflow dictionary
            actions: List of actions to apply
            
        Returns:
            Modified workflow dictionary
        """
        # Work on a copy to avoid modifying the original
        import copy
        modified = copy.deepcopy(workflow)
        
        # Index nodes for efficient lookup
        nodes_by_id = self._index_nodes_by_id(modified)
        
        logger.info(f"Applying {len(actions)} actions to workflow")
        
        for action in actions:
            if action.action_type == "modify_widget":
                self._apply_modify_widget(nodes_by_id, action)
            elif action.action_type == "toggle_node_mode":
                self._apply_toggle_mode(nodes_by_id, action)
            elif action.action_type == "add_lora_pair":
                self._apply_add_lora(nodes_by_id, action)
            elif action.action_type == "modify_vector_widget":
                self._apply_modify_vector(nodes_by_id, action)
            else:
                logger.warning(f"Unknown action type: {action.action_type}")
        
        return modified
    
    def _apply_modify_widget(
        self, 
        nodes_by_id: Dict[int, Dict], 
        action: ModifyWidgetAction
    ):
        """Apply a ModifyWidgetAction to the workflow."""
        node = nodes_by_id.get(action.node_id)
        if not node:
            logger.warning(f"Node {action.node_id} not found")
            return
        
        widgets_values = node.get("widgets_values", [])
        
        # Apply value to all specified indices
        for idx in action.widget_indices:
            if idx < len(widgets_values):
                old_value = widgets_values[idx]
                # For mxSlider nodes, ensure numeric values are floats
                value = action.value
                if action.node_type == "mxSlider" and isinstance(value, (int, float)):
                    value = float(value)
                widgets_values[idx] = value
                logger.debug(f"Node {action.node_id}[{idx}]: {old_value} -> {value}")
            else:
                logger.warning(f"Widget index {idx} out of range for node {action.node_id}")
    
    def _apply_toggle_mode(
        self, 
        nodes_by_id: Dict[int, Dict], 
        action: ToggleNodeModeAction
    ):
        """Apply a ToggleNodeModeAction to the workflow."""
        target_mode = action.enabled_mode if action.enabled else action.disabled_mode
        
        for node_id in action.node_ids:
            node = nodes_by_id.get(node_id)
            if not node:
                logger.warning(f"Node {node_id} not found")
                continue
            
            old_mode = node.get("mode", 0)
            node["mode"] = target_mode
            logger.debug(f"Node {node_id} mode: {old_mode} -> {target_mode}")
        
        # If save_node_id is specified, also toggle save_output in widgets_values
        if action.save_node_id is not None:
            save_node = nodes_by_id.get(action.save_node_id)
            if save_node:
                widgets_values = save_node.get("widgets_values")
                if isinstance(widgets_values, dict) and "save_output" in widgets_values:
                    old_save = widgets_values["save_output"]
                    widgets_values["save_output"] = action.enabled
                    logger.debug(f"Node {action.save_node_id} save_output: {old_save} -> {action.enabled}")
                else:
                    logger.warning(f"Node {action.save_node_id} has no save_output in widgets_values")
            else:
                logger.warning(f"Save node {action.save_node_id} not found")
    
    def _apply_add_lora(
        self, 
        nodes_by_id: Dict[int, Dict], 
        action: AddLoRAPairAction
    ):
        """Apply an AddLoRAPairAction to the workflow."""
        # Determine which node to add to based on the action's lora_path
        # High noise LoRAs go to high_node_id, low noise to low_node_id
        # Check for various patterns: "high", "-H-", "_HIGH", etc.
        lora_path_lower = action.lora_path.lower()
        if any(pattern in lora_path_lower for pattern in ["high", "-h-", "_high_", "high_noise"]):
            target_node_id = action.high_node_id
        elif any(pattern in lora_path_lower for pattern in ["low", "-l-", "_low_", "low_noise"]):
            target_node_id = action.low_node_id
        else:
            # Default to high node if unclear
            target_node_id = action.high_node_id
        
        node = nodes_by_id.get(target_node_id)
        if not node:
            logger.warning(f"Node {target_node_id} not found")
            return
        
        widgets_values = node.get("widgets_values", [])
        
        # Power Lora Loader structure:
        # [0] = {}
        # [1] = {"type": "PowerLoraLoaderHeaderWidget"}
        # [2...N] = Individual LoRA entries {"on": bool, "lora": str, "strength": num}
        # [N+1] = {}
        # [N+2] = ""
        
        # Create new LoRA entry
        lora_entry = {
            "on": action.enabled,
            "lora": action.lora_path,
            "strength": action.strength,
            "strengthTwo": None
        }
        
        # Insert before the last two elements ({} and "")
        # Find insertion point (before trailing {} and "")
        insert_idx = len(widgets_values) - 2 if len(widgets_values) >= 2 else len(widgets_values)
        widgets_values.insert(insert_idx, lora_entry)
        
        logger.debug(f"Added LoRA to node {target_node_id} at index {insert_idx}: {action.lora_path}")
    
    def _apply_modify_vector(
        self, 
        nodes_by_id: Dict[int, Dict], 
        action: ModifyVectorWidgetAction
    ):
        """Apply a ModifyVectorWidgetAction to the workflow."""
        node = nodes_by_id.get(action.node_id)
        if not node:
            logger.warning(f"Node {action.node_id} not found")
            return
        
        widgets_values = node.get("widgets_values", [])
        properties = node.get("properties", {})
        
        # Update X values if provided
        if action.x_value is not None and action.x_indices:
            for idx in action.x_indices:
                if idx < len(widgets_values):
                    old_value = widgets_values[idx]
                    widgets_values[idx] = action.x_value
                    logger.debug(f"Node {action.node_id}[{idx}] X: {old_value} -> {action.x_value}")
            # Also update properties.valueX if it exists
            if "valueX" in properties:
                old_value = properties["valueX"]
                properties["valueX"] = action.x_value
                logger.debug(f"Node {action.node_id} property valueX: {old_value} -> {action.x_value}")
        
        # Update Y values if provided
        if action.y_value is not None and action.y_indices:
            for idx in action.y_indices:
                if idx < len(widgets_values):
                    old_value = widgets_values[idx]
                    widgets_values[idx] = action.y_value
                    logger.debug(f"Node {action.node_id}[{idx}] Y: {old_value} -> {action.y_value}")
            # Also update properties.valueY if it exists
            if "valueY" in properties:
                old_value = properties["valueY"]
                properties["valueY"] = action.y_value
                logger.debug(f"Node {action.node_id} property valueY: {old_value} -> {action.y_value}")
    
    def process(
        self, 
        inputs_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None
    ) -> Dict:
        """
        Complete workflow processing: load inputs, generate actions, apply, and export.
        
        Args:
            inputs_path: Path to inputs JSON file
            output_path: Optional path for output workflow (auto-generated if None)
            
        Returns:
            Modified workflow dictionary
        """
        # Load inputs
        inputs = self._load_inputs(inputs_path)
        
        # Load base workflow
        workflow = self._load_workflow()
        
        # Generate and apply actions
        actions = self.generate_actions(inputs)
        modified_workflow = self.apply_actions(workflow, actions)
        
        # Calculate hash for versioning
        workflow_hash = self._calculate_hash(modified_workflow)
        
        # Determine output path
        if output_path is None:
            base_name = self.workflow_path.stem
            output_path = self.workflow_path.parent / f"{base_name}_{workflow_hash}.json"
        
        # Export
        self.export(modified_workflow, output_path)
        
        logger.info(f"Workflow processing complete. Hash: {workflow_hash}")
        return modified_workflow
    
    def _calculate_hash(self, workflow: Dict) -> str:
        """Calculate SHA256 hash of workflow (8-char hex)."""
        workflow_json = json.dumps(workflow, sort_keys=True)
        hash_obj = hashlib.sha256(workflow_json.encode('utf-8'))
        return hash_obj.hexdigest()[:8]
    
    def export(self, workflow: Dict, output_path: Union[str, Path]):
        """Export modified workflow to JSON file."""
        output_path = Path(output_path)
        logger.info(f"Exporting workflow to: {output_path}")
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(workflow, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported successfully: {output_path}")
