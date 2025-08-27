# SSH Connectivity Test Framework

This document describes the SSH connectivity test framework that verifies the ability to SSH into instances running in containers on the same local network.

## Overview

The SSH test framework provides both automated unit tests and standalone utilities to verify SSH connectivity to configured targets like Forge and ComfyUI containers.

## Components

### 1. test/test_ssh_connectivity.py

Automated unit tests that verify SSH connectivity using the `unittest` framework. These tests:

- Test SSH connections to configured LAN targets (forge, comfy)
- Use existing SSH configuration from `.ssh/config`
- Handle cases where target hosts may not be available
- Include both real connection tests and mocked scenarios
- Follow existing unittest patterns in the project

### 2. ssh_test.py

Standalone command-line utility for manual SSH testing. Features:

- Test specific hosts or all configured hosts
- Configurable timeouts
- JSON or text output formats
- Prerequisites checking
- Integration-friendly for CI/CD pipelines

### 3. Web API Integration

The main sync API (`sync_api.py`) includes a new SSH test endpoint:

- **Endpoint**: `POST /test/ssh`
- **Purpose**: Test SSH connectivity via web interface
- **Integration**: Accessible through the web UI with a "Test SSH Connectivity" button

## Usage

### Running Unit Tests

```bash
# Run all SSH connectivity tests
cd /path/to/vast_api
PYTHONPATH=. python test/test_ssh_connectivity.py

# Run as part of the complete test suite
PYTHONPATH=. python -m unittest discover test/ -v
```

### Using the Standalone Tool

```bash
# Test all default hosts (forge, comfy)
python ssh_test.py

# Test specific host
python ssh_test.py --host forge

# Test with custom timeout
python ssh_test.py --timeout 20

# Output as JSON for automation
python ssh_test.py --format json

# Check prerequisites only
python ssh_test.py --check-prereqs

# Get help
python ssh_test.py --help
```

### Web Interface

1. Start the Flask application:
   ```bash
   python sync_api.py
   ```

2. Open your browser to `http://localhost:5000`

3. Click the "🔧 Test SSH Connectivity" button

4. View results showing the status of all configured SSH targets

### API Endpoint

Test SSH connectivity programmatically:

```bash
curl -X POST http://localhost:5000/test/ssh
```

Example response:
```json
{
  "success": true,
  "message": "SSH connectivity test completed",
  "summary": {
    "total_hosts": 2,
    "successful": 1,
    "failed": 1,
    "success_rate": "50.0%"
  },
  "results": {
    "forge": {
      "host": "forge",
      "success": true,
      "message": "Connection successful",
      "output": "ssh-test-success"
    },
    "comfy": {
      "host": "comfy",
      "success": false,
      "message": "Connection failed",
      "error": "Connection timed out"
    }
  }
}
```

## Configuration

The test framework uses the existing SSH configuration:

- **SSH Config**: `.ssh/config` (or `/root/.ssh/config` in container)
- **Default Targets**: forge (10.0.78.108:2222), comfy (10.0.78.108:2223)
- **Timeout**: Configurable (default 10 seconds)

## Expected Behavior

### In Development/Test Environment

When the target hosts (10.0.78.108:2222, 10.0.78.108:2223) are not available:

- Tests will timeout and report connection failures
- This is expected and tests will still pass (they verify the framework works)
- Error messages will be clear and helpful for debugging

### In Production Environment

When target hosts are available and SSH is properly configured:

- Tests should succeed and show successful connections
- Any failures indicate real SSH connectivity issues
- Results can be used for monitoring and alerting

## Integration with Existing System

The SSH test framework integrates seamlessly with the existing codebase:

1. **Uses existing SSH configuration** from `.ssh/config`
2. **Follows existing test patterns** used in other test files
3. **Leverages existing logging setup** for consistent output
4. **Integrates with Flask API** for web interface access
5. **Minimal dependencies** - uses only standard library and existing packages

## Error Handling

The framework gracefully handles common scenarios:

- **Connection timeouts**: Clear timeout messages with configurable limits
- **Missing configuration**: Helpful error messages about missing SSH config
- **Permission issues**: Warnings about SSH key permissions
- **Network unavailability**: Distinguishes between configuration and network issues

## Security Considerations

- Tests use non-interactive SSH mode (`BatchMode=yes`)
- Timeouts prevent hanging connections
- No sensitive data is logged or exposed
- Uses existing SSH key infrastructure
- Follows SSH best practices from the project's SSH configuration

## Future Enhancements

Potential improvements:

1. **VastAI Integration**: Add tests for dynamic VastAI instances
2. **Performance Metrics**: Add connection timing measurements
3. **Health Monitoring**: Integration with monitoring systems
4. **Docker Integration**: Tests that work within the Docker container context
5. **Automated Recovery**: Suggestions for fixing common SSH issues