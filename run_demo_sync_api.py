#!/usr/bin/env python3
"""
Demo version of sync_api with mock VastAI instances
"""
import sys
import os
from unittest.mock import patch, MagicMock

# Add current directory to path to import from app
sys.path.insert(0, os.path.dirname(__file__))

def mock_list_instances(self):
    """Return mock VastAI instances for demo"""
    return [
        {
            'id': 12345,
            'cur_state': 'running',
            'gpu_name': 'RTX 4090',
            'num_gpus': 1,
            'gpu_ram': 24576,  # in MB
            'ssh_host': '104.189.178.116',
            'ssh_port': 2838,
            'public_ipaddr': '104.189.178.116',
            'geolocation': 'US-West',
            'dph_total': 0.83
        },
        {
            'id': 67890,
            'cur_state': 'running',
            'gpu_name': 'RTX 4080',
            'num_gpus': 2,
            'gpu_ram': 16384,  # in MB
            'ssh_host': '192.168.1.100',
            'ssh_port': 3344,
            'public_ipaddr': '192.168.1.100',
            'geolocation': 'EU-Central',
            'dph_total': 1.24
        },
        {
            'id': 11111,
            'cur_state': 'stopped',
            'gpu_name': 'RTX 3090',
            'num_gpus': 1,
            'gpu_ram': 24576,  # in MB
            'ssh_host': '10.0.0.5',
            'ssh_port': 2222,
            'public_ipaddr': '10.0.0.5',
            'geolocation': 'US-East',
            'dph_total': 0.65
        }
    ]

def mock_get_running_instance(self):
    """Return first running instance for demo"""
    instances = mock_list_instances(self)
    for instance in instances:
        if instance.get("cur_state") == "running":
            return instance
    return None

# Apply patches before importing the app
with patch('app.vastai.vast_manager.VastManager.list_instances', mock_list_instances):
    with patch('app.vastai.vast_manager.VastManager.get_running_instance', mock_get_running_instance):
        from app.sync.sync_api import app
        import logging

        if __name__ == '__main__':
            # Setup logging
            logging.basicConfig(level=logging.INFO)
            logger = logging.getLogger(__name__)
            
            logger.info("Starting Media Sync API Server (Demo Mode with Mock Instances)")
            port = int(sys.argv[1].replace('--port=', '').replace('--port', '')) if len(sys.argv) > 1 and '--port' in sys.argv[1] else 5002
            app.run(host='0.0.0.0', port=port, debug=False)