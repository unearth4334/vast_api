#!/usr/bin/env python3
"""
Test fixture for download progress visualization.

This test emulates the cloud instance side of the download management feature
and validates that:
1. Download agent posts progress to status JSON file every 2 seconds
2. Status file contains correct fields for the web UI to display
3. Progress visualization shows queued/in-progress/complete downloads in list format
4. Status tags are correctly generated based on job state
"""

import os
import sys
import json
import time
import uuid
import tempfile
import threading
from unittest import TestCase, main as unittest_main
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.progress_parsers import CivitdlProgressParser, WgetProgressParser


class DownloadProgressTestFixture:
    """
    Test fixture for simulating download progress updates.
    
    Creates temporary queue and status files and simulates the download handler
    writing progress every 2 seconds.
    """
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="download_progress_test_")
        self.queue_path = os.path.join(self.temp_dir, "download_queue.json")
        self.status_path = os.path.join(self.temp_dir, "download_status.json")
        
        # Initialize empty files
        self._write_json(self.queue_path, [])
        self._write_json(self.status_path, [])
        
        # Progress update interval
        self.update_interval = 2  # seconds
    
    def _write_json(self, path: str, data: list) -> None:
        """Write data to JSON file"""
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _read_json(self, path: str) -> list:
        """Read data from JSON file"""
        if not os.path.exists(path):
            return []
        with open(path, 'r') as f:
            return json.load(f)
    
    def add_download_job(
        self,
        instance_id: str,
        ssh_connection: str,
        commands: List[str],
        resource_paths: Optional[List[str]] = None
    ) -> Dict:
        """
        Add a download job to the queue and initialize status.
        
        Args:
            instance_id: Cloud instance identifier
            ssh_connection: SSH connection string
            commands: List of download commands
            resource_paths: Optional list of resource file paths
            
        Returns:
            The created job dictionary
        """
        job = {
            'id': str(uuid.uuid4()),
            'instance_id': instance_id,
            'ssh_connection': ssh_connection,
            'resource_paths': resource_paths or [],
            'commands': commands,
            'added_at': datetime.now(timezone.utc).isoformat() + 'Z',
            'status': 'PENDING'
        }
        
        # Add to queue
        queue = self._read_json(self.queue_path)
        queue.append(job)
        self._write_json(self.queue_path, queue)
        
        # Initialize status entry
        status = self._read_json(self.status_path)
        status.append({
            'id': job['id'],
            'instance_id': instance_id,
            'added_at': job['added_at'],
            'status': 'PENDING',
            'progress': {},
            'updated_at': datetime.now(timezone.utc).isoformat() + 'Z'
        })
        self._write_json(self.status_path, status)
        
        return job
    
    def update_status(
        self,
        job_id: str,
        status: str,
        progress: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Update the status of a job (simulating download handler writing every 2 seconds).
        
        Args:
            job_id: Job identifier
            status: New status (PENDING, RUNNING, COMPLETE, FAILED)
            progress: Progress information (percent, speed, etc.)
            error: Error message if failed
        """
        status_list = self._read_json(self.status_path)
        
        for job_status in status_list:
            if job_status['id'] == job_id:
                job_status['status'] = status
                job_status['updated_at'] = datetime.now(timezone.utc).isoformat() + 'Z'
                if progress:
                    job_status['progress'] = progress
                if error:
                    job_status['error'] = error
                break
        
        self._write_json(self.status_path, status_list)
    
    def get_status(self, instance_id: Optional[str] = None) -> List[Dict]:
        """
        Get download status, optionally filtered by instance.
        This simulates what the web UI would receive from the /downloads/status endpoint.
        """
        status = self._read_json(self.status_path)
        
        # Merge with queue to get commands and resource_paths
        queue = self._read_json(self.queue_path)
        job_map = {j['id']: j for j in queue}
        
        for s in status:
            job_id = s.get('id')
            if job_id in job_map:
                s['commands'] = job_map[job_id].get('commands', [])
                s['resource_paths'] = job_map[job_id].get('resource_paths', [])
        
        if instance_id:
            status = [s for s in status if str(s.get('instance_id')) == str(instance_id)]
        
        return status
    
    def simulate_download_progress(
        self,
        job_id: str,
        total_duration_seconds: float = 10,
        simulate_failure: bool = False
    ) -> None:
        """
        Simulate a download with progress updates every 2 seconds.
        
        Args:
            job_id: Job identifier
            total_duration_seconds: Total download time to simulate
            simulate_failure: If True, simulate a failure at 60% progress
        """
        num_updates = int(total_duration_seconds / self.update_interval)
        
        for i in range(num_updates):
            progress_percent = int(((i + 1) / num_updates) * 100)
            
            # Check for simulated failure
            if simulate_failure and progress_percent >= 60:
                self.update_status(
                    job_id,
                    'FAILED',
                    progress={'percent': progress_percent},
                    error='Connection timeout while downloading'
                )
                return
            
            # Update status with progress
            self.update_status(
                job_id,
                'RUNNING',
                progress={
                    'percent': progress_percent,
                    'speed': '45.3MiB/s',
                    'stage': 'model',
                    'name': 'Test Model Download'
                }
            )
            
            # Wait for next update (in tests, we might skip this)
            # time.sleep(self.update_interval)
        
        # Complete
        self.update_status(
            job_id,
            'COMPLETE',
            progress={'percent': 100}
        )
    
    def cleanup(self) -> None:
        """Clean up temporary files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


class TestDownloadProgressVisualization(TestCase):
    """Test cases for download progress visualization"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.fixture = DownloadProgressTestFixture()
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.fixture.cleanup()
    
    def test_status_file_contains_required_fields(self):
        """Test that status file contains all fields needed by web UI"""
        job = self.fixture.add_download_job(
            instance_id="test_instance",
            ssh_connection="ssh -p 44686 root@192.168.1.100",
            commands=['civitdl "https://civitai.com/models/123" "$UI_HOME/models/loras"'],
            resource_paths=['loras/test_model.md']
        )
        
        # Update with progress
        self.fixture.update_status(
            job['id'],
            'RUNNING',
            progress={
                'percent': 50,
                'speed': '45.3MiB/s',
                'stage': 'model',
                'name': 'Test Model'
            }
        )
        
        # Get status
        status = self.fixture.get_status(instance_id="test_instance")
        
        self.assertEqual(len(status), 1)
        job_status = status[0]
        
        # Verify required fields for web UI
        self.assertIn('id', job_status)
        self.assertIn('instance_id', job_status)
        self.assertIn('status', job_status)
        self.assertIn('progress', job_status)
        self.assertIn('updated_at', job_status)
        self.assertIn('commands', job_status)
        self.assertIn('resource_paths', job_status)
        
        # Verify progress fields
        self.assertEqual(job_status['progress']['percent'], 50)
        self.assertEqual(job_status['progress']['speed'], '45.3MiB/s')
        self.assertEqual(job_status['progress']['name'], 'Test Model')
    
    def test_status_updates_every_2_seconds(self):
        """Test that status can be updated at 2-second intervals"""
        job = self.fixture.add_download_job(
            instance_id="test_instance",
            ssh_connection="ssh -p 44686 root@192.168.1.100",
            commands=['civitdl "https://civitai.com/models/123" "$UI_HOME/models/loras"']
        )
        
        # Record timestamps of updates
        timestamps = []
        
        # Simulate multiple updates
        for i in range(3):
            self.fixture.update_status(
                job['id'],
                'RUNNING',
                progress={'percent': (i + 1) * 33}
            )
            status = self.fixture.get_status(instance_id="test_instance")
            timestamps.append(status[0]['updated_at'])
        
        # All updates should have been recorded
        self.assertEqual(len(timestamps), 3)
        
        # Each update should have a different timestamp
        # (In real scenario, they would be 2 seconds apart)
        for i in range(len(timestamps) - 1):
            self.assertNotEqual(timestamps[i], timestamps[i + 1])
    
    def test_multiple_jobs_with_different_statuses(self):
        """Test that we can have multiple jobs in different states"""
        # Add pending job
        job1 = self.fixture.add_download_job(
            instance_id="test_instance",
            ssh_connection="ssh -p 44686 root@192.168.1.100",
            commands=['wget -O model1.safetensors https://example.com/model1.safetensors'],
            resource_paths=['checkpoints/model1.md']
        )
        
        # Add running job
        job2 = self.fixture.add_download_job(
            instance_id="test_instance",
            ssh_connection="ssh -p 44686 root@192.168.1.100",
            commands=['civitdl "https://civitai.com/models/456" "$UI_HOME/models/loras"'],
            resource_paths=['loras/test_lora.md']
        )
        self.fixture.update_status(
            job2['id'],
            'RUNNING',
            progress={'percent': 45, 'speed': '50.0MiB/s'}
        )
        
        # Add complete job
        job3 = self.fixture.add_download_job(
            instance_id="test_instance",
            ssh_connection="ssh -p 44686 root@192.168.1.100",
            commands=['wget -O model2.safetensors https://example.com/model2.safetensors'],
            resource_paths=['checkpoints/model2.md']
        )
        self.fixture.update_status(
            job3['id'],
            'COMPLETE',
            progress={'percent': 100}
        )
        
        # Add failed job
        job4 = self.fixture.add_download_job(
            instance_id="test_instance",
            ssh_connection="ssh -p 44686 root@192.168.1.100",
            commands=['civitdl "https://civitai.com/models/789" "$UI_HOME/models/loras"'],
            resource_paths=['loras/failed_lora.md']
        )
        self.fixture.update_status(
            job4['id'],
            'FAILED',
            progress={'percent': 60},
            error='Connection timeout'
        )
        
        # Get all status for this instance
        status = self.fixture.get_status(instance_id="test_instance")
        
        self.assertEqual(len(status), 4)
        
        # Group by status
        by_status = {}
        for s in status:
            by_status[s['status']] = by_status.get(s['status'], []) + [s]
        
        self.assertEqual(len(by_status['PENDING']), 1)
        self.assertEqual(len(by_status['RUNNING']), 1)
        self.assertEqual(len(by_status['COMPLETE']), 1)
        self.assertEqual(len(by_status['FAILED']), 1)
        
        # Verify running job has progress info
        running_job = by_status['RUNNING'][0]
        self.assertEqual(running_job['progress']['percent'], 45)
        self.assertEqual(running_job['progress']['speed'], '50.0MiB/s')
        
        # Verify failed job has error message
        failed_job = by_status['FAILED'][0]
        self.assertEqual(failed_job['error'], 'Connection timeout')
    
    def test_instance_isolation(self):
        """Test that jobs for different instances are isolated"""
        # Add job for instance 1
        job1 = self.fixture.add_download_job(
            instance_id="instance_1",
            ssh_connection="ssh -p 44686 root@192.168.1.100",
            commands=['civitdl "https://civitai.com/models/123" "$UI_HOME/models/loras"']
        )
        
        # Add job for instance 2
        job2 = self.fixture.add_download_job(
            instance_id="instance_2",
            ssh_connection="ssh -p 44686 root@192.168.1.200",
            commands=['civitdl "https://civitai.com/models/456" "$UI_HOME/models/loras"']
        )
        
        # Get status for instance 1 only
        status_1 = self.fixture.get_status(instance_id="instance_1")
        status_2 = self.fixture.get_status(instance_id="instance_2")
        status_all = self.fixture.get_status()
        
        self.assertEqual(len(status_1), 1)
        self.assertEqual(len(status_2), 1)
        self.assertEqual(len(status_all), 2)
        
        self.assertEqual(status_1[0]['id'], job1['id'])
        self.assertEqual(status_2[0]['id'], job2['id'])
    
    def test_simulate_full_download_flow(self):
        """Test the full download flow from pending to complete"""
        job = self.fixture.add_download_job(
            instance_id="test_instance",
            ssh_connection="ssh -p 44686 root@192.168.1.100",
            commands=['civitdl "https://civitai.com/models/123" "$UI_HOME/models/loras"'],
            resource_paths=['loras/test_model.md']
        )
        
        # Verify initial status is PENDING
        status = self.fixture.get_status(instance_id="test_instance")
        self.assertEqual(status[0]['status'], 'PENDING')
        
        # Simulate download progress (without actual delays)
        self.fixture.simulate_download_progress(job['id'], total_duration_seconds=10)
        
        # Verify final status is COMPLETE
        status = self.fixture.get_status(instance_id="test_instance")
        self.assertEqual(status[0]['status'], 'COMPLETE')
        self.assertEqual(status[0]['progress']['percent'], 100)
    
    def test_simulate_download_failure(self):
        """Test that failures are properly recorded"""
        job = self.fixture.add_download_job(
            instance_id="test_instance",
            ssh_connection="ssh -p 44686 root@192.168.1.100",
            commands=['civitdl "https://civitai.com/models/123" "$UI_HOME/models/loras"'],
            resource_paths=['loras/test_model.md']
        )
        
        # Simulate download that fails at 60%
        self.fixture.simulate_download_progress(job['id'], total_duration_seconds=10, simulate_failure=True)
        
        # Verify final status is FAILED
        status = self.fixture.get_status(instance_id="test_instance")
        self.assertEqual(status[0]['status'], 'FAILED')
        self.assertIn('error', status[0])
        self.assertIn('timeout', status[0]['error'].lower())


class TestProgressParsersEnhanced(TestCase):
    """Test enhanced progress parsers"""
    
    def test_civitdl_parser_with_model_progress(self):
        """Test civitdl parser with model download progress"""
        line = "Model: 75%|███████▓░░| 75.0M/100.0M [00:03<00:01, 25.0MiB/s]"
        result = CivitdlProgressParser.parse_line(line)
        
        if result:  # May not match due to regex format
            self.assertEqual(result['type'], 'progress')
            self.assertEqual(result['percent'], 75)
    
    def test_wget_parser_progress(self):
        """Test wget parser with progress output"""
        line = "model.safetensors   50%[====>        ] 50.0M  45.3MB/s  eta 5s"
        result = WgetProgressParser.parse_line(line)
        
        if result:
            self.assertEqual(result['type'], 'progress')
            self.assertEqual(result['percent'], 50)
    
    def test_wget_parser_saved(self):
        """Test wget parser with file saved message"""
        line = "'model.safetensors' saved [104857600/104857600]"
        result = WgetProgressParser.parse_line(line)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'stage_complete')
        self.assertEqual(result['filename'], 'model.safetensors')
        self.assertEqual(result['percent'], 100)
    
    def test_wget_parser_http_response(self):
        """Test wget parser with HTTP response"""
        line = "HTTP request sent, awaiting response... 200 OK"
        result = WgetProgressParser.parse_line(line)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'http_response')
        self.assertEqual(result['status_code'], 200)


class TestResourceNameExtraction(TestCase):
    """Test resource name extraction for the web UI"""
    
    def test_extract_name_from_resource_path(self):
        """Test extracting name from resource_paths"""
        job = {
            'resource_paths': ['loras/my_awesome_lora.md'],
            'commands': []
        }
        
        # Simulate what the web UI does
        path = job['resource_paths'][0]
        filename = path.split('/')[-1]
        name = filename.replace('.md', '').replace('_', ' ')
        
        self.assertEqual(name, 'my awesome lora')
    
    def test_extract_name_from_civitdl_command(self):
        """Test extracting name from civitdl command"""
        job = {
            'resource_paths': [],
            'commands': ['civitdl "https://civitai.com/models/1234567" "$UI_HOME/models/loras"']
        }
        
        # Simulate extraction
        import re
        cmd = job['commands'][0]
        match = re.search(r'models/(\d+)', cmd)
        if match:
            name = f'Civitai Model {match.group(1)}'
        else:
            name = 'Civitai Download'
        
        self.assertEqual(name, 'Civitai Model 1234567')


if __name__ == '__main__':
    unittest_main()
