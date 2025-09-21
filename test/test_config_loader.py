#!/usr/bin/env python3
"""
Test the centralized configuration loader
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.utils.config_loader import ConfigLoader, load_config, load_api_key


class TestConfigLoader(unittest.TestCase):
    """Test the centralized configuration loader"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary files for testing
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.yaml')
        self.api_key_file = os.path.join(self.temp_dir, 'test_api_key.txt')
        
        # Sample configuration
        config_content = """
columns:
  - id
  - gpu_name
  - dph_total
max_rows: 5
disk_size_gb: 100
template_hash_id: test_template_123
ui_home_env: /workspace/test
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

    def test_config_loader_with_custom_paths(self):
        """Test ConfigLoader with custom paths"""
        loader = ConfigLoader(config_path=self.config_file, api_key_path=self.api_key_file)
        
        # Test config loading
        config = loader.load_config()
        self.assertEqual(config['max_rows'], 5)
        self.assertEqual(config['disk_size_gb'], 100)
        self.assertEqual(config['template_hash_id'], 'test_template_123')
        
        # Test API key loading
        api_key = loader.load_api_key()
        self.assertEqual(api_key, 'test_api_key_123')

    def test_api_key_fallback_to_content(self):
        """Test API key loading when no provider prefix exists"""
        # Create API key file without provider prefix
        simple_key_file = os.path.join(self.temp_dir, 'simple_api_key.txt')
        with open(simple_key_file, 'w') as f:
            f.write('simple_key_without_prefix')
        
        loader = ConfigLoader(api_key_path=simple_key_file)
        api_key = loader.load_api_key()
        self.assertEqual(api_key, 'simple_key_without_prefix')

    def test_config_path_resolution_priority(self):
        """Test that config path resolution follows correct priority"""
        loader = ConfigLoader()
        
        # Test with explicit path (highest priority)
        explicit_loader = ConfigLoader(config_path=self.config_file)
        self.assertEqual(explicit_loader.config_path, self.config_file)
        
        # Test environment variable priority
        with patch.dict(os.environ, {'VAST_CONFIG_PATH': self.config_file}):
            env_loader = ConfigLoader()
            self.assertEqual(env_loader.config_path, self.config_file)

    def test_convenience_functions(self):
        """Test the convenience functions for backward compatibility"""
        # Test with custom path
        config = load_config(self.config_file)
        self.assertEqual(config['max_rows'], 5)
        
        api_key = load_api_key(self.api_key_file)
        self.assertEqual(api_key, 'test_api_key_123')

    def test_file_not_found_handling(self):
        """Test handling of missing configuration files"""
        loader = ConfigLoader(config_path='/nonexistent/config.yaml')
        
        with self.assertRaises(FileNotFoundError):
            loader.load_config()

    def test_invalid_yaml_handling(self):
        """Test handling of invalid YAML content"""
        invalid_config_file = os.path.join(self.temp_dir, 'invalid_config.yaml')
        with open(invalid_config_file, 'w') as f:
            f.write('invalid: yaml: content: [')
        
        loader = ConfigLoader(config_path=invalid_config_file)
        
        with self.assertRaises(Exception):  # Should raise YAML error
            loader.load_config()

    def test_different_api_providers(self):
        """Test loading API keys for different providers"""
        multi_provider_file = os.path.join(self.temp_dir, 'multi_provider.txt')
        with open(multi_provider_file, 'w') as f:
            f.write('vastai: vast_key_123\nopenai: openai_key_456\n')
        
        loader = ConfigLoader(api_key_path=multi_provider_file)
        
        vast_key = loader.load_api_key('vastai')
        self.assertEqual(vast_key, 'vast_key_123')
        
        openai_key = loader.load_api_key('openai')
        self.assertEqual(openai_key, 'openai_key_456')

    def test_environment_responsiveness(self):
        """Test that the default loader picks up environment variable changes"""
        from app.utils.config_loader import get_default_loader
        import os
        
        # Set environment variable to our test config
        with unittest.mock.patch.dict(os.environ, {'VAST_CONFIG_PATH': self.config_file}):
            loader1 = get_default_loader()
            self.assertEqual(loader1.config_path, self.config_file)
        
        # Clear environment and test fallback behavior 
        with unittest.mock.patch.dict(os.environ, {}, clear=True):
            # Mock os.getcwd to return our temp directory so it finds our config
            with unittest.mock.patch('os.getcwd', return_value=self.temp_dir):
                # Create a config.yaml in the temp dir for fallback
                fallback_config = os.path.join(self.temp_dir, 'config.yaml')
                with open(fallback_config, 'w') as f:
                    f.write('test: fallback')
                
                loader2 = get_default_loader()
                self.assertEqual(loader2.config_path, fallback_config)


if __name__ == '__main__':
    unittest.main()