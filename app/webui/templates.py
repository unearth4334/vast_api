"""
WebUI template management for the Media Sync Tool
"""

import os

def get_index_template():
    """Get the HTML template for the main web interface"""
    template_path = os.path.join(os.path.dirname(__file__), 'index_template.html')
    with open(template_path, 'r') as f:
        return f.read()