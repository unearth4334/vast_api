#!/usr/bin/env python3
"""
Demo script to create sample workflow state files and generate HTML visualizations.
This demonstrates how the webui renders workflow progress from the state file.
"""

import json
import os
from datetime import datetime

# Sample workflow state files for different scenarios

def create_state_file(filename, state_data):
    """Create a sample state file"""
    with open(filename, 'w') as f:
        json.dump(state_data, f, indent=2)
    print(f"✅ Created: {filename}")

# Scenario 1: Workflow in progress (3 of 5 steps completed)
state_in_progress = {
    "workflow_id": "workflow_1732248000_demo123",
    "status": "running",
    "current_step": 3,
    "steps": [
        {"action": "test_ssh", "label": "Test SSH Connection", "status": "completed", "index": 0},
        {"action": "set_ui_home", "label": "Set UI Home Directory", "status": "completed", "index": 1},
        {"action": "setup_civitdl", "label": "Setup CivitDL", "status": "completed", "index": 2},
        {"action": "sync_instance", "label": "Sync Instance Files", "status": "in_progress", "index": 3},
        {"action": "install_nodes", "label": "Install Custom Nodes", "status": "pending", "index": 4}
    ],
    "start_time": "2024-11-22T04:00:00Z",
    "last_update": "2024-11-22T04:03:15Z",
    "ssh_connection": "ssh -p 12345 root@123.45.67.89"
}

# Scenario 2: Workflow completed successfully
state_completed = {
    "workflow_id": "workflow_1732248100_demo456",
    "status": "completed",
    "current_step": 4,
    "steps": [
        {"action": "test_ssh", "label": "Test SSH Connection", "status": "completed", "index": 0},
        {"action": "set_ui_home", "label": "Set UI Home Directory", "status": "completed", "index": 1},
        {"action": "setup_civitdl", "label": "Setup CivitDL", "status": "completed", "index": 2},
        {"action": "sync_instance", "label": "Sync Instance Files", "status": "completed", "index": 3},
        {"action": "install_nodes", "label": "Install Custom Nodes", "status": "completed", "index": 4}
    ],
    "start_time": "2024-11-22T03:45:00Z",
    "last_update": "2024-11-22T03:52:30Z",
    "ssh_connection": "ssh -p 12345 root@123.45.67.89"
}

# Scenario 3: Workflow failed at step 3
state_failed = {
    "workflow_id": "workflow_1732248200_demo789",
    "status": "failed",
    "current_step": 2,
    "steps": [
        {"action": "test_ssh", "label": "Test SSH Connection", "status": "completed", "index": 0},
        {"action": "set_ui_home", "label": "Set UI Home Directory", "status": "completed", "index": 1},
        {"action": "setup_civitdl", "label": "Setup CivitDL", "status": "failed", "index": 2},
        {"action": "sync_instance", "label": "Sync Instance Files", "status": "pending", "index": 3},
        {"action": "install_nodes", "label": "Install Custom Nodes", "status": "pending", "index": 4}
    ],
    "start_time": "2024-11-22T03:30:00Z",
    "last_update": "2024-11-22T03:32:45Z",
    "ssh_connection": "ssh -p 12345 root@123.45.67.89"
}

def generate_html_visualization(state_data, output_file):
    """Generate HTML visualization of workflow state"""
    
    status_colors = {
        "completed": "#4CAF50",
        "in_progress": "#2196F3",
        "failed": "#F44336",
        "pending": "#9E9E9E"
    }
    
    status_icons = {
        "completed": "✓",
        "in_progress": "⟳",
        "failed": "✗",
        "pending": "○"
    }
    
    # Calculate progress
    completed_steps = sum(1 for s in state_data['steps'] if s['status'] == 'completed')
    total_steps = len(state_data['steps'])
    progress_percent = (completed_steps / total_steps * 100) if total_steps > 0 else 0
    
    # Generate step HTML
    steps_html = ""
    animation_css = ""
    
    for i, step in enumerate(state_data['steps']):
        status = step['status']
        color = status_colors.get(status, "#999")
        icon = status_icons.get(status, "?")
        
        if status == "in_progress":
            animation_css += f"""
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        .step-icon-{i} {{
            animation: spin 2s linear infinite;
        }}
        """
        
        steps_html += f"""
        <div class="workflow-step" style="border-left: 4px solid {color};">
            <div class="step-icon step-icon-{i}" style="background-color: {color};">
                {icon}
            </div>
            <div class="step-content">
                <div class="step-label">{step['label']}</div>
                <div class="step-status" style="color: {color};">{status.replace('_', ' ').title()}</div>
            </div>
        </div>
        """
        
        if i < len(state_data['steps']) - 1:
            arrow_color = color if status == "completed" else "#ddd"
            steps_html += f"""
        <div class="workflow-arrow" style="border-left: 2px dashed {arrow_color};">
            <div style="color: {arrow_color};">↓</div>
        </div>
        """
    
    # Generate status message
    if state_data['status'] == 'running':
        status_msg = f"🔄 Workflow in progress: {completed_steps}/{total_steps} steps completed"
        status_color = "#2196F3"
    elif state_data['status'] == 'completed':
        status_msg = f"✅ Workflow completed successfully! All {total_steps} steps finished."
        status_color = "#4CAF50"
    elif state_data['status'] == 'failed':
        failed_step = next((i+1 for i, s in enumerate(state_data['steps']) if s['status'] == 'failed'), 0)
        status_msg = f"❌ Workflow failed at step {failed_step} of {total_steps}"
        status_color = "#F44336"
    else:
        status_msg = "Workflow status unknown"
        status_color = "#999"
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Workflow Progress Visualization - {state_data['workflow_id']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
        }}
        
        .header h1 {{
            font-size: 24px;
            margin-bottom: 10px;
        }}
        
        .header .workflow-id {{
            font-size: 12px;
            opacity: 0.8;
            font-family: monospace;
        }}
        
        .status-banner {{
            background: {status_color};
            color: white;
            padding: 15px 30px;
            font-weight: 500;
        }}
        
        .progress-bar {{
            height: 4px;
            background: #e0e0e0;
            position: relative;
            overflow: hidden;
        }}
        
        .progress-fill {{
            height: 100%;
            background: {status_color};
            width: {progress_percent}%;
            transition: width 0.3s ease;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .metadata {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
            padding: 20px;
            background: #f5f5f5;
            border-radius: 8px;
        }}
        
        .metadata-item {{
            display: flex;
            flex-direction: column;
        }}
        
        .metadata-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 5px;
        }}
        
        .metadata-value {{
            font-size: 14px;
            color: #333;
            font-family: monospace;
        }}
        
        .workflow-steps {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        
        .workflow-step {{
            display: flex;
            align-items: center;
            padding: 15px;
            background: #fafafa;
            border-radius: 8px;
            transition: transform 0.2s ease;
        }}
        
        .workflow-step:hover {{
            transform: translateX(5px);
        }}
        
        .step-icon {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 20px;
            margin-right: 15px;
            flex-shrink: 0;
        }}
        
        .step-content {{
            flex: 1;
        }}
        
        .step-label {{
            font-size: 16px;
            font-weight: 500;
            color: #333;
            margin-bottom: 5px;
        }}
        
        .step-status {{
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .workflow-arrow {{
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-left: 20px;
            font-size: 20px;
        }}
        
        .footer {{
            padding: 20px 30px;
            background: #f5f5f5;
            border-top: 1px solid #e0e0e0;
            font-size: 12px;
            color: #666;
            text-align: center;
        }}
        
        {animation_css}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>VastAI Instance Setup Workflow</h1>
            <div class="workflow-id">ID: {state_data['workflow_id']}</div>
        </div>
        
        <div class="status-banner">
            {status_msg}
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill"></div>
        </div>
        
        <div class="content">
            <div class="metadata">
                <div class="metadata-item">
                    <div class="metadata-label">Status</div>
                    <div class="metadata-value">{state_data['status'].upper()}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Progress</div>
                    <div class="metadata-value">{completed_steps}/{total_steps} steps ({progress_percent:.0f}%)</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Started</div>
                    <div class="metadata-value">{state_data['start_time']}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Last Update</div>
                    <div class="metadata-value">{state_data['last_update']}</div>
                </div>
            </div>
            
            <div class="workflow-steps">
{steps_html}            </div>
        </div>
        
        <div class="footer">
            Server-side workflow execution with real-time state persistence<br>
            State file: /tmp/workflow_state.json
        </div>
    </div>
</body>
</html>"""
    
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"✅ Generated visualization: {output_file}")

def main():
    """Main function to generate demo files"""
    demo_dir = "/tmp/workflow_demo"
    os.makedirs(demo_dir, exist_ok=True)
    
    print("\n" + "="*70)
    print("WORKFLOW STATE FILE & VISUALIZATION DEMO")
    print("="*70 + "\n")
    
    # Create state files
    print("📁 Creating sample state files...\n")
    create_state_file(f"{demo_dir}/state_in_progress.json", state_in_progress)
    create_state_file(f"{demo_dir}/state_completed.json", state_completed)
    create_state_file(f"{demo_dir}/state_failed.json", state_failed)
    
    # Generate HTML visualizations
    print("\n🎨 Generating HTML visualizations...\n")
    generate_html_visualization(state_in_progress, f"{demo_dir}/visualization_in_progress.html")
    generate_html_visualization(state_completed, f"{demo_dir}/visualization_completed.html")
    generate_html_visualization(state_failed, f"{demo_dir}/visualization_failed.html")
    
    print("\n" + "="*70)
    print("✅ Demo files created successfully!")
    print("="*70)
    print(f"\n📂 Output directory: {demo_dir}")
    print("\n📄 Files created:")
    print("   State Files:")
    print(f"   - {demo_dir}/state_in_progress.json")
    print(f"   - {demo_dir}/state_completed.json")
    print(f"   - {demo_dir}/state_failed.json")
    print("\n   HTML Visualizations:")
    print(f"   - {demo_dir}/visualization_in_progress.html")
    print(f"   - {demo_dir}/visualization_completed.html")
    print(f"   - {demo_dir}/visualization_failed.html")
    print("\n💡 Open the HTML files in a web browser to see the visualizations!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
