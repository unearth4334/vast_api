#!/usr/bin/env python3
"""
Validate Workflow Configuration

Tests the enhanced workflow configuration validation system.
Demonstrates template validation with metadata checking.
"""

import sys
import os
import logging
from pathlib import Path

# Add parent directory to path
parent_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, parent_dir)
os.chdir(parent_dir)

from app.create.workflow_loader import WorkflowLoader
from app.create.workflow_validator import TemplateValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

def main():
    """Validate IMG_to_VIDEO_canvas workflow"""
    
    print("=" * 80)
    print("WORKFLOW CONFIGURATION VALIDATION")
    print("=" * 80)
    print()
    
    workflow_id = "IMG_to_VIDEO_canvas"
    
    try:
        print(f"Loading workflow: {workflow_id}")
        print()
        
        # Load workflow config
        config = WorkflowLoader.load_workflow(workflow_id)
        print(f"✅ Workflow loaded: {config.name} v{config.version}")
        print(f"   Inputs: {len(config.inputs)}")
        print(f"   Outputs: {len(config.outputs)}")
        print(f"   Helper Tools: {len(config.helper_tools)}")
        
        if config.validation:
            print(f"\n📋 Validation Configuration:")
            print(f"   Strict Mode: {config.validation.strict_mode}")
            print(f"   Check Tokens: {config.validation.check_tokens}")
            print(f"   Check Node IDs: {config.validation.check_node_ids}")
            print(f"   Check Widgets: {config.validation.check_widgets}")
            print(f"   Warn on Mismatch: {config.validation.warn_on_mismatch}")
        else:
            print("\n⚠️  No validation configuration found")
        
        print("\n" + "=" * 80)
        print("METADATA ANALYSIS")
        print("=" * 80)
        
        # Count inputs with metadata
        inputs_with_metadata = [inp for inp in config.inputs if inp.metadata]
        print(f"\nInputs with metadata: {len(inputs_with_metadata)}/{len(config.inputs)}")
        
        for inp in inputs_with_metadata:
            print(f"\n📝 {inp.id} ({inp.label}):")
            
            if inp.metadata.widget_type:
                print(f"   Widget Type: {inp.metadata.widget_type}")
            
            if inp.metadata.widget_pattern:
                print(f"   Widget Pattern: {inp.metadata.widget_pattern}")
            
            if inp.metadata.widget_indices:
                print(f"   Widget Indices: {inp.metadata.widget_indices}")
            
            if inp.metadata.coupled_with:
                print(f"   Coupled With: {inp.metadata.coupled_with}")
            
            if inp.metadata.target_nodes:
                print(f"   Target Nodes:")
                for node_info in inp.metadata.target_nodes:
                    node_id = node_info.get('node_id')
                    desc = node_info.get('description', '')
                    print(f"      • Node {node_id}: {desc}")
        
        # Load template
        print("\n" + "=" * 80)
        print("TEMPLATE VALIDATION")
        print("=" * 80)
        print()
        
        template = WorkflowLoader.load_workflow_json(workflow_id)
        print(f"✅ Template loaded")
        print(f"   Nodes: {len(template.get('nodes', []))}")
        print(f"   Links: {len(template.get('links', []))}")
        
        # Validate
        print("\n🔍 Running validation...\n")
        result = TemplateValidator.validate_template_mapping(config, template)
        
        # Print results
        print(result.summary())
        
        # Exit with appropriate code
        if not result.is_valid:
            print("\n❌ Validation FAILED")
            return 1
        elif result.has_warnings:
            print("\n⚠️  Validation PASSED with warnings")
            return 0
        else:
            print("\n✅ Validation PASSED")
            return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
