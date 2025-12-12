# Resource Installation with Progress Streaming

This document explains how to install resources to VastAI instances with real-time progress updates via WebSocket.

## Architecture

### Components

1. **ProgressParser** - Parses `civitdl` output to extract progress information
2. **ResourceInstaller** - Executes installation commands via SSH with progress callbacks
3. **WebSocket `/resources` namespace** - Streams progress events to connected clients
4. **POST `/resources/install` endpoint** - Initiates installation jobs

## API Usage

### 1. Start Installation Job

```bash
POST /resources/install
Content-Type: application/json

{
  "ssh_host": "109.231.106.68",
  "ssh_port": 44686,
  "ui_home": "/workspace/ComfyUI",
  "resources": [
    "checkpoints/flux_schnell.md",
    "loras/wan21_fusionx.md"
  ]
}
```

**Response:**
```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Installation started",
  "resource_count": 2
}
```

### 2. Subscribe to Progress Updates

Connect to WebSocket and subscribe to the job:

```javascript
// Connect to WebSocket
const socket = io('http://localhost:5000/resources');

socket.on('connect', () => {
  console.log('Connected to resource installation stream');
  
  // Subscribe to job progress
  socket.emit('subscribe_install', { job_id: jobId });
});

socket.on('subscribed', (data) => {
  console.log('Subscribed to job:', data.job_id);
});
```

### 3. Receive Progress Events

#### Stage Start
Emitted when a resource download begins:

```javascript
socket.on('resource_install_progress', (data) => {
  if (data.type === 'stage_start') {
    console.log(`Downloading: ${data.name}`);
    // data = {
    //   type: 'stage_start',
    //   name: 'Dramatic Lighting Slider',
    //   resource: 'loras/wan21_fusionx.md',
    //   job_id: '550e8400-...'
    // }
  }
});
```

#### Progress Updates
Emitted during download with percentage and speed:

```javascript
socket.on('resource_install_progress', (data) => {
  if (data.type === 'progress') {
    console.log(`${data.stage}: ${data.percent}% - ${data.speed}`);
    // data = {
    //   type: 'progress',
    //   stage: 'model',           // 'images', 'model', or 'cache'
    //   percent: 45,
    //   downloaded: '3.65M',
    //   total: '8.12M',
    //   elapsed: '00:03',
    //   remaining: '00:04',
    //   speed: '60.9MiB/s',
    //   resource: 'loras/wan21_fusionx.md',
    //   job_id: '550e8400-...'
    // }
  }
});
```

#### Stage Complete
Emitted when a resource finishes downloading:

```javascript
socket.on('resource_install_progress', (data) => {
  if (data.type === 'stage_complete') {
    console.log(`Completed: ${data.name}`);
    // data = {
    //   type: 'stage_complete',
    //   name: 'Dramatic Lighting Slider',
    //   resource: 'loras/wan21_fusionx.md',
    //   job_id: '550e8400-...'
    // }
  }
});
```

#### Installation Complete
Emitted when all resources are installed:

```javascript
socket.on('resource_install_complete', (result) => {
  console.log(`Installation complete: ${result.installed}/${result.total} successful`);
  // result = {
  //   success: true,
  //   installed: 2,
  //   total: 2,
  //   results: [...]
  // }
});
```

#### Installation Error
Emitted if installation fails:

```javascript
socket.on('resource_install_error', (error) => {
  console.error('Installation failed:', error.error);
  // error = {
  //   job_id: '550e8400-...',
  //   error: 'SSH connection failed'
  // }
});
```

## Frontend Integration

### Complete Example

```javascript
class ResourceInstaller {
  constructor() {
    this.socket = null;
    this.currentJobId = null;
  }
  
  connect() {
    this.socket = io('http://localhost:5000/resources');
    
    this.socket.on('connect', () => {
      console.log('WebSocket connected');
    });
    
    this.socket.on('resource_install_progress', (data) => {
      this.handleProgress(data);
    });
    
    this.socket.on('resource_install_complete', (result) => {
      this.handleComplete(result);
    });
    
    this.socket.on('resource_install_error', (error) => {
      this.handleError(error);
    });
  }
  
  async startInstallation(sshHost, sshPort, uiHome, resourcePaths) {
    const response = await fetch('/resources/install', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ssh_host: sshHost,
        ssh_port: sshPort,
        ui_home: uiHome,
        resources: resourcePaths
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      this.currentJobId = result.job_id;
      this.socket.emit('subscribe_install', { job_id: result.job_id });
      return result;
    } else {
      throw new Error(result.message);
    }
  }
  
  handleProgress(data) {
    switch (data.type) {
      case 'stage_start':
        console.log(`📥 Downloading: ${data.name}`);
        break;
        
      case 'progress':
        const bar = '█'.repeat(data.percent / 5) + '░'.repeat(20 - data.percent / 5);
        console.log(`[${bar}] ${data.percent}% - ${data.speed}`);
        break;
        
      case 'stage_complete':
        console.log(`✅ Completed: ${data.name}`);
        break;
    }
  }
  
  handleComplete(result) {
    console.log(`🎉 Installation complete: ${result.installed}/${result.total} successful`);
    this.currentJobId = null;
  }
  
  handleError(error) {
    console.error(`❌ Installation failed: ${error.error}`);
    this.currentJobId = null;
  }
}

// Usage
const installer = new ResourceInstaller();
installer.connect();

// Start installation
await installer.startInstallation(
  '109.231.106.68',
  44686,
  '/workspace/ComfyUI',
  ['checkpoints/flux_schnell.md', 'loras/wan21_fusionx.md']
);
```

## Progress Parser

The `ProgressParser` class extracts structured data from `civitdl` output:

### Supported Patterns

1. **Stage Start**: `Now downloading "Model Name"...`
2. **Progress Bar**: `Model: 45%|███░░░| 3.65M/8.12M [00:03<00:04, 60.9MiB/s]`
3. **Stage Complete**: `Download completed for "Model Name"`

### Output Format

```python
# Stage start
{
  'type': 'stage_start',
  'name': 'Dramatic Lighting Slider'
}

# Progress update
{
  'type': 'progress',
  'stage': 'model',      # 'images', 'model', or 'cache'
  'percent': 45,
  'downloaded': '3.65M',
  'total': '8.12M',
  'elapsed': '00:03',
  'remaining': '00:04',
  'speed': '60.9MiB/s'
}

# Stage complete
{
  'type': 'stage_complete',
  'name': 'Dramatic Lighting Slider'
}
```

## Testing

### Test Progress Parser

```bash
python3 test/test_progress_parser.py
```

### Test Installation Endpoint

```bash
curl -X POST http://localhost:5000/resources/install \
  -H "Content-Type: application/json" \
  -d '{
    "ssh_host": "109.231.106.68",
    "ssh_port": 44686,
    "ui_home": "/workspace/ComfyUI",
    "resources": ["loras/wan21_fusionx.md"]
  }'
```

### Monitor WebSocket Events

Use browser console:

```javascript
const socket = io('http://localhost:5000/resources');
socket.on('connect', () => console.log('Connected'));
socket.on('resource_install_progress', (d) => console.log('Progress:', d));
socket.on('resource_install_complete', (d) => console.log('Complete:', d));
socket.on('resource_install_error', (d) => console.log('Error:', d));
```

## Implementation Notes

1. **Threading**: Installations run in background threads to avoid blocking the API
2. **Room-based Broadcasting**: Each job ID is a WebSocket room for isolated progress streams
3. **Regex Parsing**: Progress bars are parsed using regex to extract percentages and speeds
4. **Error Handling**: Failures emit `resource_install_error` events
5. **Timeout**: SSH commands timeout after 1 hour per resource

## Future Enhancements

- [ ] Pause/resume installation jobs
- [ ] Installation queue management
- [ ] Retry failed resources
- [ ] Estimated time remaining calculation
- [ ] Bandwidth throttling
- [ ] Parallel resource downloads
- [ ] Installation verification after completion
