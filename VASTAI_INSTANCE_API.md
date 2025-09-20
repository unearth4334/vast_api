# VastAI Instance API

This document describes the new API endpoints for retrieving and managing individual VastAI instance details, particularly SSH connection information.

## Endpoints

### GET /vastai/instances/<instance_id>

Retrieves detailed information for a specific VastAI instance by calling the VastAI API.

**Request:**
```bash
GET http://localhost:5001/vastai/instances/26070143
```

**Response Format:**
```json
{
  "instances": {
    "cur_state": "running",
    "gpu_name": "RTX 4090", 
    "id": "26070143",
    "ssh_host": "104.189.178.116",
    "ssh_port": 2838
  }
}
```

**Status Codes:**
- `200` - Success
- `404` - Instance not found or configuration files missing
- `500` - Server error

### PUT /vastai/instances/<instance_id>

Updates the SSH host and port information for a specific instance. This endpoint allows manual override of SSH connection details in case the VastAI API fails to provide correct information.

**Request:**
```bash
PUT http://localhost:5001/vastai/instances/26070143
Content-Type: application/json

{
  "ssh_host": "104.189.178.116",
  "ssh_port": 2838
}
```

**Response Format:**
```json
{
  "instances": {
    "id": "26070143",
    "ssh_host": "104.189.178.116", 
    "ssh_port": 2838
  }
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad request (missing required fields)
- `500` - Server error

## Usage Examples

### Using curl

Get instance details:
```bash
curl -X GET http://localhost:5001/vastai/instances/26070143
```

Update SSH connection details:
```bash
curl -X PUT http://localhost:5001/vastai/instances/26070143 \
  -H 'Content-Type: application/json' \
  -d '{"ssh_host": "104.189.178.116", "ssh_port": 2838}'
```

### Using Python requests

```python
import requests

# Get instance details
response = requests.get('http://localhost:5001/vastai/instances/26070143')
data = response.json()
print(f"SSH Host: {data['instances']['ssh_host']}")
print(f"SSH Port: {data['instances']['ssh_port']}")

# Update SSH details
update_data = {
    'ssh_host': '192.168.1.100',
    'ssh_port': 3333
}
response = requests.put('http://localhost:5001/vastai/instances/26070143', json=update_data)
print(f"Updated: {response.json()}")
```

## Configuration Requirements

The API requires the following configuration files in the project root:

- `config.yaml` - VastAI configuration
- `api_key.txt` - API keys including VastAI access token

Example `api_key.txt` format:
```
vastai: your_vast_ai_api_key_here
civitdl: your_civitdl_api_key_here
```

## Error Handling

The API provides detailed error messages for common scenarios:

- Missing configuration files
- Invalid instance IDs
- Network connectivity issues with VastAI API
- Missing required fields in PUT requests

All errors include a `success: false` field and descriptive `message` field for debugging.