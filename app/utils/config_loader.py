"""
Centralized configuration loading mechanism for the vast_api application.

This module provides consistent configuration file loading across all components,
with proper path resolution and error handling.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Centralized configuration loader with consistent path resolution."""
    
    def __init__(self, config_path: Optional[str] = None, api_key_path: Optional[str] = None):
        """
        Initialize the config loader with optional path overrides.
        
        Args:
            config_path: Optional path to config file (defaults to config.yaml)
            api_key_path: Optional path to API key file (defaults to api_key.txt)
        """
        self.config_path = self._resolve_config_path(config_path)
        self.api_key_path = self._resolve_api_key_path(api_key_path)
    
    def _resolve_config_path(self, config_path: Optional[str]) -> str:
        """
        Resolve the configuration file path using a consistent strategy.
        
        Priority order:
        1. Provided config_path parameter
        2. VAST_CONFIG_PATH environment variable
        3. config.yaml in current working directory
        4. config.yaml relative to application root
        """
        if config_path:
            return config_path
        
        # Check environment variable
        env_path = os.environ.get('VAST_CONFIG_PATH')
        if env_path and os.path.exists(env_path):
            return env_path
        
        # Check current directory
        cwd_path = os.path.join(os.getcwd(), 'config.yaml')
        if os.path.exists(cwd_path):
            return cwd_path
        
        # Check relative to application root (assumed to be 2 levels up from this file)
        app_root = Path(__file__).parent.parent.parent
        app_config = app_root / 'config.yaml'
        if app_config.exists():
            return str(app_config)
        
        # Default fallback
        return 'config.yaml'
    
    def _resolve_api_key_path(self, api_key_path: Optional[str]) -> str:
        """
        Resolve the API key file path using a consistent strategy.
        
        Priority order:
        1. Provided api_key_path parameter
        2. VAST_API_KEY_PATH environment variable
        3. api_key.txt in current working directory
        4. api_key.txt relative to application root
        """
        if api_key_path:
            return api_key_path
        
        # Check environment variable
        env_path = os.environ.get('VAST_API_KEY_PATH')
        if env_path and os.path.exists(env_path):
            return env_path
        
        # Check current directory
        cwd_path = os.path.join(os.getcwd(), 'api_key.txt')
        if os.path.exists(cwd_path):
            return cwd_path
        
        # Check relative to application root
        app_root = Path(__file__).parent.parent.parent
        app_key = app_root / 'api_key.txt'
        if app_key.exists():
            return str(app_key)
        
        # Default fallback
        return 'api_key.txt'
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load the YAML configuration file.
        
        Returns:
            Dict containing the configuration data
            
        Raises:
            FileNotFoundError: If the configuration file cannot be found
            yaml.YAMLError: If the configuration file is invalid YAML
        """
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from: {self.config_path}")
                return config or {}
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in configuration file {self.config_path}: {e}")
            raise
    
    def load_api_key(self, provider: str = "vastai") -> str:
        """
        Load the API key from file.
        
        Args:
            provider: The API provider name (default: "vastai")
            
        Returns:
            The API key string
            
        Raises:
            FileNotFoundError: If the API key file cannot be found
            ValueError: If the API key for the provider is not found
        """
        try:
            with open(self.api_key_path, 'r') as f:
                content = f.read().strip()
            
            # Handle multi-line format: "provider: <key>"
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith(f'{provider}:'):
                    api_key = line.split(':', 1)[1].strip()
                    logger.info(f"Loaded API key for {provider} from: {self.api_key_path}")
                    return api_key
            
            # Fallback to entire content if no prefix found
            logger.info(f"Loaded API key (no prefix) from: {self.api_key_path}")
            return content
            
        except FileNotFoundError:
            logger.error(f"API key file not found: {self.api_key_path}")
            raise FileNotFoundError(f"API key file not found: {self.api_key_path}")


# Convenience functions for backward compatibility and easy usage
_default_loader = None

def get_default_loader() -> ConfigLoader:
    """Get the default config loader instance (singleton pattern)."""
    global _default_loader
    # Always create a fresh instance to pick up environment variable changes
    _default_loader = ConfigLoader()
    return _default_loader

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration using the default loader or a custom path.
    
    Args:
        config_path: Optional custom path to config file
        
    Returns:
        Dict containing the configuration data
    """
    if config_path:
        loader = ConfigLoader(config_path=config_path)
        return loader.load_config()
    else:
        return get_default_loader().load_config()

def load_api_key(api_key_path: Optional[str] = None, provider: str = "vastai") -> str:
    """
    Load API key using the default loader or a custom path.
    
    Args:
        api_key_path: Optional custom path to API key file
        provider: The API provider name (default: "vastai")
        
    Returns:
        The API key string
    """
    if api_key_path:
        loader = ConfigLoader(api_key_path=api_key_path)
        return loader.load_api_key(provider)
    else:
        return get_default_loader().load_api_key(provider)