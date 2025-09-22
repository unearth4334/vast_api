# Configuration Management

This document describes the centralized configuration loading mechanism implemented for the vast_api application.

## Overview

The application now uses a centralized configuration loading system that provides consistent behavior across all modules. This eliminates hardcoded paths and provides flexible configuration management.

## Configuration Files

### config.yaml
Contains the main application configuration including:
- Column display settings
- VastAI template configuration
- Resource limits and preferences
- Filtering criteria

### api_key.txt
Contains API keys in the format:
```
vastai: your_vast_ai_key_here
openai: your_openai_key_here
```

Or a simple single-line key for backward compatibility:
```
your_vast_ai_key_here
```

## Configuration Path Resolution

The system uses the following priority order to locate configuration files:

1. **Explicit path** (when provided directly)
2. **Environment variables**:
   - `VAST_CONFIG_PATH` for config.yaml location
   - `VAST_API_KEY_PATH` for api_key.txt location
3. **Current working directory**
4. **Application root directory**
5. **Default fallback** (config.yaml, api_key.txt)

## Usage Examples

### Basic Usage
```python
from app.utils.config_loader import load_config, load_api_key

# Load configuration using default resolution
config = load_config()
api_key = load_api_key()
```

### Custom Paths
```python
from app.utils.config_loader import ConfigLoader

# Load from custom paths
loader = ConfigLoader(
    config_path="/path/to/custom_config.yaml",
    api_key_path="/path/to/custom_api_key.txt"
)
config = loader.load_config()
api_key = loader.load_api_key()
```

### Environment Variables
```bash
# Set environment variables
export VAST_CONFIG_PATH="/opt/vast/config.yaml"
export VAST_API_KEY_PATH="/opt/vast/api_key.txt"

# Run your application - it will automatically use these paths
python -m app.vastai.vast_launcher
```

### Docker Deployment
```dockerfile
# In your Dockerfile
ENV VAST_CONFIG_PATH=/app/config/production.yaml
ENV VAST_API_KEY_PATH=/app/secrets/api_key.txt
```

## Multi-Provider API Keys

The system supports multiple API providers in a single file:

```
# api_key.txt
vastai: your_vast_ai_key_here
openai: your_openai_key_here
anthropic: your_anthropic_key_here
```

Load specific provider keys:
```python
from app.utils.config_loader import load_api_key

vast_key = load_api_key(provider="vastai")
openai_key = load_api_key(provider="openai")
```

## Updated Modules

The following modules now use the centralized configuration system:

- `app.vastai.vast_launcher` - VastAI instance launcher
- `app.vastai.vast_display` - Offer display functionality  
- `app.vastai.vast_manager` - VastAI management class
- `app.sync.sync_api` - Synchronization API server

## Error Handling

The configuration loader provides clear error messages for common issues:

- **FileNotFoundError**: When configuration files cannot be found
- **yaml.YAMLError**: When configuration files contain invalid YAML
- **ValueError**: When API keys for specific providers are not found

## Testing

The configuration system includes comprehensive tests:

- Unit tests for ConfigLoader functionality
- Integration tests for cross-module consistency
- Environment variable configuration tests

Run tests with:
```bash
python -m pytest test/test_config_loader.py test/test_config_integration.py -v
```

## Migration from Previous Version

The new system is fully backward compatible. Existing code continues to work without changes. However, you can now optionally:

1. Set environment variables for deployment flexibility
2. Use explicit paths for custom configurations
3. Organize API keys by provider in a single file

## Benefits

- **Consistency**: All modules use the same configuration loading mechanism
- **Flexibility**: Support for environment variables and custom paths
- **Deployment-friendly**: Easy configuration management in containers/cloud
- **Error handling**: Clear error messages for configuration issues
- **Multi-provider**: Support for multiple API keys in one file
- **Backward compatible**: Existing code continues to work unchanged