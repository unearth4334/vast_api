#!/usr/bin/env python3
"""
Demo script to create mock VastAI instance data for UI testing
"""
import json
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the path to import the app
sys.path.insert(0, os.path.dirname(__file__))


def create_mock_instances():
    """Create mock VastAI instances for testing"""
    return [
        {
            'id': 12345,
            'status': 'running',
            'gpu': 'RTX 4090',
            'gpu_count': 1,
            'gpu_ram_gb': 24.0,
            'ssh_host': '104.189.178.116',
            'ssh_port': 2838,
            'public_ip': '104.189.178.116',
            'geolocation': 'US-West',
            'cost_per_hour': 0.83
        },
        {
            'id': 67890,
            'status': 'running',
            'gpu': 'RTX 4080',
            'gpu_count': 2,
            'gpu_ram_gb': 16.0,
            'ssh_host': '192.168.1.100',
            'ssh_port': 3344,
            'public_ip': '192.168.1.100',
            'geolocation': 'EU-Central',
            'cost_per_hour': 1.24
        },
        {
            'id': 11111,
            'status': 'stopped',
            'gpu': 'RTX 3090',
            'gpu_count': 1,
            'gpu_ram_gb': 24.0,
            'ssh_host': '10.0.0.5',
            'ssh_port': 2222,
            'public_ip': '10.0.0.5',
            'geolocation': 'US-East',
            'cost_per_hour': 0.65
        }
    ]


def patch_vast_manager():
    """Patch VastManager to return mock instances"""
    mock_instances = create_mock_instances()
    
    def mock_list_instances():
        return mock_instances
    
    def mock_get_running_instance():
        # Return first running instance
        return next((inst for inst in mock_instances if inst['status'] == 'running'), None)
    
    return mock_list_instances, mock_get_running_instance


if __name__ == '__main__':
    instances = create_mock_instances()
    print("Mock VastAI instances created:")
    for instance in instances:
        print(f"  - Instance #{instance['id']}: {instance['status']} - {instance['gpu']} @ {instance['ssh_host']}:{instance['ssh_port']}")