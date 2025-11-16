# Complete VastAI API Request/Response Logging Implementation

## Overview
Successfully implemented comprehensive logging that captures **all outgoing and incoming information** for VastAI API interactions, providing complete visibility into every API call with full request/response data, headers, timing, and system metrics.

## Enhanced Logging Features

### 1. Complete Request Capture
- **Full request payload** with data structure analysis
- **HTTP headers** (sanitized to protect sensitive data)
- **Request method and URL**
- **Request size and data type information**
- **Parameter count and nesting depth**

### 2. Complete Response Capture  
- **Full response data** with structure preservation
- **Response size and record count**
- **Data type analysis** (arrays, objects, primitives)
- **HTTP status codes and success indicators**
- **Response structure depth and complexity**

### 3. Enhanced Data Analysis
- **Data structure analysis**: nesting levels, data types, complexity
- **Content analysis**: file detection, JSON validation, size categorization
- **Performance categorization**: fast/normal/slow/very_slow based on response time
- **Record counting**: automatic counting of data records in responses

### 4. Security & Privacy
- **Sensitive data sanitization**: API keys, tokens, passwords automatically redacted
- **Header sanitization**: Authorization headers show type but hide actual tokens
- **Large data truncation**: Long strings and large arrays are summarized with previews
- **Structured redaction**: Maintains data structure while hiding sensitive content

## Log Structure

### Complete API Interaction Log Entry:
```json
{
  "timestamp": "2025-10-20T11:50:39.553723",
  "operation_id": "test_integration_1760986431_38a03027",
  "api": {
    "method": "PUT",
    "endpoint": "/asks/12345/",
    "url": "https://console.vast.ai/api/v0/asks/12345/",
    "headers": {
      "Authorization": "Bearer [REDACTED:18 chars]",
      "Content-Type": "application/json"
    },
    "status_code": 200,
    "duration_ms": 2150.3,
    "retry_count": 0,
    "success": true
  },
  "request": {
    "data": {
      "template_hash_id": "abc123def456",
      "disk": 32,
      "extra_env": "{\"UI_HOME\": \"/app/ui\"}",
      "target_state": "running",
      "cancel_unavail": true
    },
    "size_bytes": 125,
    "contains_files": false,
    "data_type": "dict",
    "parameter_count": 5,
    "structure": {
      "type": "dict",
      "keys": ["template_hash_id", "disk", "extra_env", "target_state", "cancel_unavail"],
      "key_count": 5,
      "nested_levels": 1,
      "has_arrays": false,
      "has_objects": false
    }
  },
  "response": {
    "data": {
      "success": true,
      "new_contract": 27050456,
      "message": "Instance created successfully"
    },
    "size_bytes": 78,
    "record_count": 1,
    "data_types": {
      "bool": 1,
      "int": 1,
      "str": 1
    },
    "data_type": "dict",
    "structure": {
      "type": "dict",
      "keys": ["success", "new_contract", "message"],
      "key_count": 3,
      "nested_levels": 1,
      "has_arrays": false,
      "has_objects": false
    }
  },
  "context": {
    "session_id": "session_1760986431",
    "user_agent": "vast_api/1.0 (test_integration)",
    "ip_address": "localhost",
    "instance_id": "27050456",
    "template_name": null
  },
  "system": {
    "hostname": "DESKTOP1",
    "platform": "Linux 6.14.0-33-generic",
    "python_version": "3.13.3",
    "cpu_usage": 2.0,
    "memory_usage": 18.5,
    "disk_usage": 48.5,
    "timestamp": "2025-10-20T11:50:39.654706"
  },
  "performance": {
    "memory_before_mb": 17.41796875,
    "duration_category": "slow",
    "success": true
  }
}
```

## Implementation Details

### Enhanced Functions Updated:

1. **`log_api_interaction()`** - Enhanced with complete request/response capture
   - Added `headers` parameter for HTTP header logging
   - Added `url` parameter for full URL capture
   - Enhanced data sanitization and structure analysis

2. **VastAI API Functions** - All updated with complete logging:
   - `query_offers()` - Full search request and offer response logging
   - `create_instance()` - Complete instance creation request/response
   - `show_instance()` - Instance details request/response
   - `destroy_instance()` - Instance destruction logging
   - `list_instances()` - Complete instance listing with full response data

### New Helper Methods:

1. **`_deep_sanitize_data()`** - Deep sanitization while preserving structure
2. **`_sanitize_headers()`** - HTTP header sanitization with token type preservation
3. **`_analyze_data_structure()`** - Comprehensive data structure analysis
4. **`_get_nesting_depth()`** - Calculate maximum nesting levels
5. **`_is_json_string()`** - Detect JSON content in strings

## Benefits

### 1. Complete Visibility
- **Every API call** is logged with full request and response data
- **No information loss** - all data is captured and analyzed
- **Structured analysis** of data complexity and types
- **Performance insights** with timing categorization

### 2. Security & Compliance
- **Automatic sanitization** of sensitive data (API keys, passwords)
- **Token type preservation** (e.g., "Bearer [REDACTED:18 chars]")
- **Large data handling** with intelligent truncation and previews
- **Structure preservation** during sanitization

### 3. Advanced Analytics
- **Request/response correlation** through operation IDs
- **Performance tracking** with categorization (fast/slow)
- **Data type analysis** for API usage patterns
- **System resource monitoring** during API calls

### 4. Debugging & Troubleshooting
- **Complete context** for every API interaction
- **Full error details** with request/response correlation
- **Performance bottleneck identification**
- **System resource impact analysis**

## Usage Examples

### Automatic Enhanced Logging in VastAI API:
```python
# All VastAI API calls now automatically log complete request/response data
from app.utils.vastai_api import query_offers

# This call will log:
# - Complete search criteria (request)
# - Full offer list response with all details
# - Request/response timing and size
# - System metrics during the call
offers = query_offers(api_key, gpu_ram=24, gpu_model="RTX 4090")
```

### Manual Enhanced Logging:
```python
from app.utils.vastai_logging import enhanced_logger, LogContext

context = create_enhanced_context("custom_operation")

enhanced_logger.log_api_interaction(
    method="POST",
    endpoint="/custom/endpoint",
    context=context,
    request_data={"param1": "value1"},
    response_data={"result": "success"},
    status_code=200,
    duration_ms=1500.2,
    headers={"Authorization": "Bearer token123"},
    url="https://api.example.com/custom/endpoint"
)
```

## Log Analysis Capabilities

With complete request/response logging, you can now:

1. **Analyze API usage patterns** - Which endpoints are called most frequently
2. **Monitor data flow** - Request/response sizes and complexity
3. **Track performance trends** - Response times and system impact
4. **Debug failed requests** - Complete context for troubleshooting
5. **Security auditing** - Monitor sensitive data handling
6. **Resource optimization** - Identify heavy API calls and system usage

## File Organization

### Log Files:
- `logs/vastai/api/api_log_YYYYMMDD.json` - Complete API interaction logs
- `logs/vastai/performance/performance_log_YYYYMMDD.json` - Performance-focused logs
- `logs/vastai/errors/error_log_YYYYMMDD.json` - Error-specific logs

### Log Rotation:
- Daily log files prevent excessive file sizes
- JSON format enables easy parsing and analysis
- Structured data supports advanced querying and analytics

## Summary

The enhanced VastAI logging now captures **every byte** of information flowing between the application and VastAI APIs while maintaining security through intelligent sanitization. This provides unprecedented visibility into API operations, enabling advanced debugging, performance optimization, and system monitoring.

The implementation successfully balances **complete data capture** with **security best practices**, ensuring all outgoing and incoming information is logged while protecting sensitive credentials and managing large data efficiently.