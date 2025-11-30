# Download Management Test Fixture

This document describes the test fixture for emulating the cloud instance side of the download management feature.

## Overview

The test fixture provides mock implementations for testing the download management feature without requiring actual SSH connections to cloud instances. It includes:

1. **MockCloudInstance** - Simulates a cloud instance with SSH connection details
2. **MockDownloadProgressEmitter** - Generates realistic download progress output
3. **MockSSHCommandExecutor** - Simulates SSH command execution
4. **DownloadQueueTestFixture** - Manages temporary queue and status files

## Components

### MockCloudInstance

Represents a simulated cloud instance for testing purposes.

```python
from test.test_download_management_fixture import MockCloudInstance

instance = MockCloudInstance(instance_id="test_123")
print(instance.get_ssh_connection_string())
# Output: "ssh -p 44686 root@192.168.1.100 -L 8080:localhost:8080"
```

**Attributes:**
- `instance_id`: Unique identifier for the instance
- `ssh_connection`: Full SSH connection string
- `ui_home`: Path to ComfyUI installation directory

### MockDownloadProgressEmitter

Generates realistic progress output that mimics `civitdl` and `wget` behavior.

```python
from test.test_download_management_fixture import MockDownloadProgressEmitter

# Generate civitdl progress
for line in MockDownloadProgressEmitter.generate_civitdl_progress(
    model_name="Test LoRA",
    model_id=1234567,
    version_id=9876543,
    total_size_mb=100.0,
    simulate_failure=False
):
    print(line)

# Generate wget progress
for line in MockDownloadProgressEmitter.generate_wget_progress(
    url="https://example.com/model.safetensors",
    filename="model.safetensors",
    total_size_mb=50.0,
    simulate_failure=False
):
    print(line)
```

**Parameters:**
- `model_name`/`filename`: Name of the file being downloaded
- `total_size_mb`: Total size in megabytes
- `simulate_failure`: If True, generates failure output

### MockSSHCommandExecutor

Simulates SSH command execution with progress callback support.

```python
from test.test_download_management_fixture import (
    MockCloudInstance,
    MockSSHCommandExecutor
)

instance = MockCloudInstance()
executor = MockSSHCommandExecutor(instance)

# Configure failures (optional)
executor.set_command_failure('civitdl', False)  # Don't fail civitdl commands

# Execute command with progress tracking
def on_progress(line):
    print(f"Progress: {line}")

exit_code, output = executor.execute_command(
    'civitdl "https://civitai.com/models/123" "$UI_HOME/models/loras"',
    progress_callback=on_progress
)

print(f"Exit code: {exit_code}")
print(f"Command log: {executor.command_log}")
```

### DownloadQueueTestFixture

Manages temporary queue and status files for testing.

```python
from test.test_download_management_fixture import DownloadQueueTestFixture

fixture = DownloadQueueTestFixture()

try:
    # Add a job
    job = fixture.add_job(
        instance_id="test_instance",
        ssh_connection="ssh -p 44686 root@192.168.1.100",
        commands=['civitdl "https://civitai.com/models/123" "$UI_HOME/models/loras"'],
        resource_paths=['loras/test_lora.md']
    )
    
    # Update status
    fixture.update_job_status(job['id'], 'RUNNING', {'percent': 50})
    
    # Get status
    status = fixture.get_status(instance_id="test_instance")
    print(status)
    
finally:
    fixture.cleanup()  # Clean up temporary files
```

## Running Tests

Run the test suite with pytest:

```bash
cd /home/runner/work/vast_api/vast_api
python3 -m pytest test/test_download_management_fixture.py -v
```

### Test Categories

1. **TestProgressParsers** - Tests for `CivitdlProgressParser` and `WgetProgressParser`
2. **TestMockCloudInstance** - Tests for cloud instance mock creation
3. **TestMockDownloadProgressEmitter** - Tests for progress output generation
4. **TestMockSSHCommandExecutor** - Tests for command execution simulation
5. **TestDownloadQueueFixture** - Tests for queue/status file management
6. **TestDownloadAPIEndpoints** - Tests for Flask API endpoints
7. **TestIntegration** - End-to-end integration tests
8. **TestMultipleDownloadsTracking** - Tests for tracking multiple simultaneous downloads
   - Multiple jobs for the same instance
   - Job progress transitions
   - Concurrent status updates
   - Detailed progress information
   - Failed job error tracking
9. **TestDownloadQueueEdgeCases** - Edge case handling tests
   - Empty queue operations
   - Non-existent job updates
   - Jobs with multiple commands
   - Special characters in paths
10. **TestProgressParserIntegration** - Parser integration with queue system
    - Civitdl progress to status flow
    - Wget progress to status flow

## Visualization Demo

Open `test/test_download_visualization_demo.html` in a browser to see an interactive demonstration of the download management UI components:

1. Select an instance from the dropdown
2. Click "Add Mock Job" to add download jobs
3. Click "Start Simulation" to see progress updates
4. Watch the console output for progress details

## Integration with Existing Code

The test fixture integrates with the existing download management system:

- **API Endpoints**: `/downloads/queue` (POST) and `/downloads/status` (GET)
- **Progress Parsers**: `app/utils/progress_parsers.py`
- **Download Handler**: `scripts/download_handler.py`
- **Web UI Component**: `app/webui/js/resource-download-status.js`

## Example: Full Workflow Test

```python
from test.test_download_management_fixture import (
    MockCloudInstance,
    MockSSHCommandExecutor,
    DownloadQueueTestFixture
)
from app.utils.progress_parsers import CivitdlProgressParser

# Set up fixtures
instance = MockCloudInstance()
executor = MockSSHCommandExecutor(instance)
queue = DownloadQueueTestFixture()

try:
    # 1. Add job to queue
    job = queue.add_job(
        instance_id=instance.instance_id,
        ssh_connection=instance.get_ssh_connection_string(),
        commands=['civitdl "https://civitai.com/models/123" "$UI_HOME/models/loras"'],
        resource_paths=['loras/test.md']
    )
    
    # 2. Update to RUNNING
    queue.update_job_status(job['id'], 'RUNNING', {'percent': 0})
    
    # 3. Execute with progress tracking
    def track_progress(line):
        parsed = CivitdlProgressParser.parse_line(line)
        if parsed and parsed.get('type') == 'progress':
            queue.update_job_status(
                job['id'],
                'RUNNING',
                {'percent': parsed.get('percent', 0)}
            )
    
    exit_code, _ = executor.execute_command(
        job['commands'][0],
        progress_callback=track_progress
    )
    
    # 4. Update final status
    final_status = 'COMPLETE' if exit_code == 0 else 'FAILED'
    queue.update_job_status(job['id'], final_status)
    
    # 5. Verify
    status = queue.get_status(instance_id=instance.instance_id)
    print(f"Final status: {status[0]['status']}")
    
finally:
    queue.cleanup()
```

## Troubleshooting

### Common Issues

1. **"Flask app not available"**: Ensure all dependencies are installed:
   ```bash
   pip install flask flask-cors pytest
   ```

2. **Progress parsing returns None**: The progress parsers use specific regex patterns. Verify the output format matches expected patterns.

3. **File permission errors**: Ensure the temporary directory is writable.

## Future Improvements

- [ ] Add WebSocket support for real-time progress streaming
- [ ] Implement parallel download simulation
- [ ] Add network failure simulation (timeouts, retries)
- [ ] Enhance progress parsing for more download tools
