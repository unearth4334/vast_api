#!/usr/bin/env python3
"""
Integration test to verify centralized configuration loading works across all modules
"""

import unittest
import tempfile
import os
import sys
from unittest.mock import patch

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestConfigIntegration(unittest.TestCase):
    """Test that all modules use the centralized config loading mechanism consistently"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary files for testing
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.yaml')
        self.api_key_file = os.path.join(self.temp_dir, 'test_api_key.txt')
        
        # Sample configuration matching the real config.yaml structure
        config_content = """
columns:
  - id
  - gpu_name
  - dph_total
column_headers:
  id: ID
  gpu_name: GPU
  dph_total: $/hr
max_rows: 10
disk_size_gb: 100
template_hash_id: test_template_123
ui_home_env: /workspace/ComfyUI
column_filters:
  gpu_ram: ">= 24576"
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)
        
        # Sample API key with provider format
        with open(self.api_key_file, 'w') as f:
            f.write('vastai: test_api_key_123\n')

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_vast_launcher_uses_centralized_config(self):
        """Test that vast_launcher uses centralized config loading"""
        # Set environment variable to use our test config
        with patch.dict(os.environ, {'VAST_CONFIG_PATH': self.config_file}):
            from app.vastai.vast_launcher import load_config
            
            config = load_config()
            self.assertEqual(config['template_hash_id'], 'test_template_123')
            self.assertEqual(config['ui_home_env'], '/workspace/ComfyUI')

    def test_vast_display_uses_centralized_config(self):
        """Test that vast_display uses centralized config loading"""
        with patch.dict(os.environ, {
            'VAST_CONFIG_PATH': self.config_file,
            'VAST_API_KEY_PATH': self.api_key_file
        }):
            from app.vastai.vast_display import load_config, load_api_key
            
            config = load_config()
            self.assertEqual(config['max_rows'], 10)
            
            api_key = load_api_key()
            self.assertEqual(api_key, 'test_api_key_123')

    def test_sync_api_uses_centralized_config(self):
        """Test that sync_api uses centralized config loading"""
        with patch.dict(os.environ, {'VAST_CONFIG_PATH': self.config_file}):
            from app.sync.sync_api import load_config
            
            config = load_config()
            self.assertEqual(config['disk_size_gb'], 100)
            self.assertEqual(config['template_hash_id'], 'test_template_123')

    def test_vast_manager_uses_centralized_config(self):
        """Test that VastManager uses centralized config loading"""
        from app.vastai.vast_manager import VastManager
        
        # Test with explicit paths
        try:
            manager = VastManager(
                config_path=self.config_file,
                api_key_path=self.api_key_file
            )
            self.assertEqual(manager.config['template_hash_id'], 'test_template_123')
            self.assertEqual(manager.api_key, 'test_api_key_123')
        except Exception as e:
            self.fail(f"VastManager initialization failed: {e}")

    def test_config_consistency_across_modules(self):
        """Test that all modules load the same configuration consistently"""
        with patch.dict(os.environ, {
            'VAST_CONFIG_PATH': self.config_file,
            'VAST_API_KEY_PATH': self.api_key_file
        }):
            # Import config loaders from different modules
            from app.vastai.vast_launcher import load_config as launcher_load_config
            from app.vastai.vast_display import load_config as display_load_config
            from app.sync.sync_api import load_config as sync_load_config
            from app.utils.config_loader import load_config as utils_load_config
            
            # Load config from all modules
            launcher_config = launcher_load_config()
            display_config = display_load_config()
            sync_config = sync_load_config()
            utils_config = utils_load_config()
            
            # All should load the same configuration
            expected_template = 'test_template_123'
            self.assertEqual(launcher_config['template_hash_id'], expected_template)
            self.assertEqual(display_config['template_hash_id'], expected_template)
            self.assertEqual(sync_config['template_hash_id'], expected_template)
            self.assertEqual(utils_config['template_hash_id'], expected_template)
            
            # All should have the same max_rows
            expected_max_rows = 10
            self.assertEqual(launcher_config['max_rows'], expected_max_rows)
            self.assertEqual(display_config['max_rows'], expected_max_rows)
            self.assertEqual(sync_config['max_rows'], expected_max_rows)
            self.assertEqual(utils_config['max_rows'], expected_max_rows)

    def test_environment_variable_config_path_works(self):
        """Test that VAST_CONFIG_PATH environment variable works for all modules"""
        with patch.dict(os.environ, {'VAST_CONFIG_PATH': self.config_file}):
            # Test the utility function directly
            from app.utils.config_loader import load_config
            config = load_config()
            self.assertEqual(config['template_hash_id'], 'test_template_123')

    def test_environment_variable_api_key_path_works(self):
        """Test that VAST_API_KEY_PATH environment variable works"""
        with patch.dict(os.environ, {'VAST_API_KEY_PATH': self.api_key_file}):
            # Test the utility function directly
            from app.utils.config_loader import load_api_key
            api_key = load_api_key()
            self.assertEqual(api_key, 'test_api_key_123')


if __name__ == '__main__':
    unittest.main()