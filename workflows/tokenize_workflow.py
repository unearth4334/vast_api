#!/usr/bin/env python3
"""
Script to add tokens to IMG_to_VIDEO_canvas.json
This prepares the workflow for token-based value replacement
"""

import json
import sys
from pathlib import Path

def add_tokens_to_workflow(workflow_path: Path):
    """Add replacement tokens to workflow JSON"""
    
    print(f"Loading workflow from: {workflow_path}")
    with open(workflow_path, 'r', encoding='utf-8') as f:
        workflow = json.load(f)
    
    if 'nodes' not in workflow:
        print("ERROR: Not a canvas format workflow (missing 'nodes' array)")
        sys.exit(1)
    
    # Track changes
    changes = []
    
    # Iterate through nodes and add tokens
    for node in workflow['nodes']:
        node_id = node.get('id')
        node_type = node.get('type')
        widgets_values = node.get('widgets_values', [])
        
        # Node 88 - LoadImage (input image)
        if node_id == 88 and node_type == 'LoadImage':
            if len(widgets_values) >= 1:
                old_value = widgets_values[0]
                widgets_values[0] = "{{INPUT_IMAGE}}"
                changes.append(f"Node 88 (LoadImage): {old_value} -> {{{{INPUT_IMAGE}}}}")
        
        # Node 408 - Positive Prompt
        elif node_id == 408 and node_type == 'PrimitiveStringMultiline':
            if len(widgets_values) >= 1:
                old_value = widgets_values[0][:50] + "..." if len(widgets_values[0]) > 50 else widgets_values[0]
                widgets_values[0] = "{{POSITIVE_PROMPT}}"
                changes.append(f"Node 408 (Positive): {old_value} -> {{{{POSITIVE_PROMPT}}}}")
        
        # Node 409 - Negative Prompt
        elif node_id == 409 and node_type == 'PrimitiveStringMultiline':
            if len(widgets_values) >= 1:
                old_value = widgets_values[0][:50] + "..." if len(widgets_values[0]) > 50 else widgets_values[0]
                widgets_values[0] = "{{NEGATIVE_PROMPT}}"
                changes.append(f"Node 409 (Negative): {old_value} -> {{{{NEGATIVE_PROMPT}}}}")
        
        # Node 73 - RandomNoise (seed)
        elif node_id == 73 and node_type == 'RandomNoise':
            if len(widgets_values) >= 1:
                old_value = widgets_values[0]
                widgets_values[0] = "{{SEED}}"
                changes.append(f"Node 73 (Seed): {old_value} -> {{{{SEED}}}}")
        
        # Node 83 - mxSlider2D (size)
        elif node_id == 83 and node_type == 'mxSlider2D':
            if len(widgets_values) >= 4:
                widgets_values[0] = "{{SIZE_WIDTH}}"  # Xi
                widgets_values[1] = "{{SIZE_WIDTH}}"  # Xf
                widgets_values[2] = "{{SIZE_HEIGHT}}" # Yi
                widgets_values[3] = "{{SIZE_HEIGHT}}" # Yf
                changes.append(f"Node 83 (Size): Added width/height tokens")
        
        # Node 426 - Duration slider
        elif node_id == 426 and node_type == 'mxSlider':
            if len(widgets_values) >= 2:
                widgets_values[0] = "{{DURATION}}"
                widgets_values[1] = "{{DURATION}}"
                changes.append(f"Node 426 (Duration): Added token")
        
        # Node 82 - Steps slider
        elif node_id == 82 and node_type == 'mxSlider':
            if len(widgets_values) >= 2:
                widgets_values[0] = "{{STEPS}}"
                widgets_values[1] = "{{STEPS}}"
                changes.append(f"Node 82 (Steps): Added token")
        
        # Node 85 - CFG slider
        elif node_id == 85 and node_type == 'mxSlider':
            if len(widgets_values) >= 2:
                widgets_values[0] = "{{CFG}}"
                widgets_values[1] = "{{CFG}}"
                changes.append(f"Node 85 (CFG): Added token")
        
        # Node 490 - Frame rate slider
        elif node_id == 490 and node_type == 'mxSlider':
            if len(widgets_values) >= 2:
                widgets_values[0] = "{{FRAME_RATE}}"
                widgets_values[1] = "{{FRAME_RATE}}"
                changes.append(f"Node 490 (Frame Rate): Added token")
        
        # Node 157 - Speed slider
        elif node_id == 157 and node_type == 'mxSlider':
            if len(widgets_values) >= 2:
                widgets_values[0] = "{{SPEED}}"
                widgets_values[1] = "{{SPEED}}"
                changes.append(f"Node 157 (Speed): Added token")
        
        # Node 421 - Upscale ratio slider
        elif node_id == 421 and node_type == 'mxSlider':
            if len(widgets_values) >= 2:
                widgets_values[0] = "{{UPSCALE_RATIO}}"
                widgets_values[1] = "{{UPSCALE_RATIO}}"
                changes.append(f"Node 421 (Upscale Ratio): Added token")
        
        # Node 522 - UNETLoader High Noise
        elif node_id == 522 and node_type == 'UNETLoader':
            if len(widgets_values) >= 1:
                old_value = widgets_values[0]
                widgets_values[0] = "{{WAN_HIGH_MODEL}}"
                changes.append(f"Node 522 (High Model): {old_value} -> {{{{WAN_HIGH_MODEL}}}}")
        
        # Node 523 - UNETLoader Low Noise
        elif node_id == 523 and node_type == 'UNETLoader':
            if len(widgets_values) >= 1:
                old_value = widgets_values[0]
                widgets_values[0] = "{{WAN_LOW_MODEL}}"
                changes.append(f"Node 523 (Low Model): {old_value} -> {{{{WAN_LOW_MODEL}}}}")
        
        # Node 460 - CLIPLoader
        elif node_id == 460 and node_type == 'CLIPLoader':
            if len(widgets_values) >= 1:
                old_value = widgets_values[0]
                widgets_values[0] = "{{CLIP_MODEL}}"
                changes.append(f"Node 460 (CLIP): {old_value} -> {{{{CLIP_MODEL}}}}")
        
        # Node 461 - VAELoader
        elif node_id == 461 and node_type == 'VAELoader':
            if len(widgets_values) >= 1:
                old_value = widgets_values[0]
                widgets_values[0] = "{{VAE_MODEL}}"
                changes.append(f"Node 461 (VAE): {old_value} -> {{{{VAE_MODEL}}}}")
        
        # Node 384 - UpscaleModelLoader
        elif node_id == 384 and node_type == 'UpscaleModelLoader':
            if len(widgets_values) >= 1:
                old_value = widgets_values[0]
                widgets_values[0] = "{{UPSCALE_MODEL}}"
                changes.append(f"Node 384 (Upscale Model): {old_value} -> {{{{UPSCALE_MODEL}}}}")
    
    # Print changes
    print(f"\nMade {len(changes)} changes:")
    for change in changes:
        print(f"  - {change}")
    
    # Save updated workflow
    output_path = workflow_path.parent / f"{workflow_path.stem}_tokenized.json"
    print(f"\nSaving tokenized workflow to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(workflow, f, indent=2)
    
    print("\nDone! You can now:")
    print(f"1. Review the changes in: {output_path}")
    print(f"2. If satisfied, replace the original: mv {output_path} {workflow_path}")

if __name__ == '__main__':
    script_dir = Path(__file__).parent
    workflow_path = script_dir / 'IMG_to_VIDEO_canvas.json'
    
    if not workflow_path.exists():
        print(f"ERROR: Workflow file not found: {workflow_path}")
        sys.exit(1)
    
    add_tokens_to_workflow(workflow_path)
