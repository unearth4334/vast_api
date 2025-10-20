"""
VastAI API Logging Module

This module provides comprehensive logging for all VastAI API interactions.
It creates date-based JSON log files with detailed operational information.
"""

import os
import json
import logging
import traceback
import platform
import psutil
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict

# Configure logging
logger = logging.getLogger(__name__)

# Configuration constants
LOG_BASE = os.environ.get('LOG_BASE', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs'))
VASTAI_LOG_DIR = os.path.join(LOG_BASE, 'vastai')


@dataclass
class SystemInfo:
    """System information for enhanced logging"""
    hostname: str
    platform: str
    python_version: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    timestamp: str

    @classmethod
    def capture(cls) -> 'SystemInfo':
        """Capture current system information"""
        try:
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return cls(
                hostname=platform.node(),
                platform=f"{platform.system()} {platform.release()}",
                python_version=platform.python_version(),
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=disk.percent,
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.warning(f"Failed to capture system info: {e}")
            return cls(
                hostname="unknown",
                platform="unknown",
                python_version="unknown",
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                timestamp=datetime.now().isoformat()
            )


@dataclass
class LogContext:
    """Enhanced context information for logging"""
    operation_id: str
    user_agent: str
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    instance_id: Optional[str] = None
    template_name: Optional[str] = None


class EnhancedVastAILogger:
    """Enhanced VastAI logging with comprehensive details"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.system_info = SystemInfo.capture()
        self.ensure_log_directories()
        
    def ensure_log_directories(self):
        """Ensure all required log directories exist"""
        try:
            os.makedirs(VASTAI_LOG_DIR, exist_ok=True)
            # Create subdirectories for better organization
            subdirs = ['api', 'instances', 'operations', 'errors', 'performance']
            for subdir in subdirs:
                os.makedirs(os.path.join(VASTAI_LOG_DIR, subdir), exist_ok=True)
            return True
        except PermissionError:
            logger.error(f"Failed to create VastAI log directory {VASTAI_LOG_DIR}: Permission denied")
            return False

    def _write_log(self, log_data: Dict[str, Any]) -> None:
        """
        Write log data to appropriate log file based on category.
        
        Args:
            log_data (Dict[str, Any]): Log data to write
        """
        try:
            category = log_data.get("category", "general")
            timestamp = datetime.utcnow()
            filename = f"{timestamp.strftime('%Y-%m-%d')}.json"
            
            # Determine the appropriate subdirectory based on category
            if category == "api":
                filepath = os.path.join(VASTAI_LOG_DIR, 'api', filename)
            elif category == "instances":
                filepath = os.path.join(VASTAI_LOG_DIR, 'instances', filename)
            elif category == "operation":
                filepath = os.path.join(VASTAI_LOG_DIR, 'operations', filename)
            elif category == "performance":
                filepath = os.path.join(VASTAI_LOG_DIR, 'performance', filename)
            elif category == "error":
                filepath = os.path.join(VASTAI_LOG_DIR, 'errors', filename)
            else:
                filepath = os.path.join(VASTAI_LOG_DIR, 'general', filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Read existing entries
            log_entries = []
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    try:
                        log_entries = json.load(f)
                    except json.JSONDecodeError:
                        log_entries = []
            
            # Append new entry
            log_entries.append(log_data)
            
            # Write back to file
            with open(filepath, 'w') as f:
                json.dump(log_entries, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Failed to write to log file: {str(e)}")
    
    def log_api_interaction(self, method: str, endpoint: str, context: LogContext,
                           request_data: Dict[Any, Any] = None, 
                           response_data: Dict[Any, Any] = None, 
                           status_code: int = None,
                           error: str = None, 
                           duration_ms: float = None,
                           retry_count: int = 0,
                           rate_limit_info: Dict[str, Any] = None) -> None:
        """
        Enhanced API interaction logging with comprehensive details.
        
        Args:
            method (str): HTTP method (GET, POST, PUT, DELETE)
            endpoint (str): VastAI API endpoint
            context (LogContext): Enhanced context information
            request_data (dict, optional): Request payload/parameters
            response_data (dict, optional): Response data from API
            status_code (int, optional): HTTP status code
            error (str, optional): Error message if request failed
            duration_ms (float, optional): Request duration in milliseconds
            retry_count (int): Number of retries attempted
            rate_limit_info (dict, optional): Rate limiting information
        """
        timestamp = datetime.now()
        system_info = SystemInfo.capture()
        
        # Create comprehensive log entry
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "operation_id": context.operation_id,
            "api": {
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "retry_count": retry_count
            },
            "context": {
                "session_id": context.session_id,
                "user_agent": context.user_agent,
                "ip_address": context.ip_address,
                "instance_id": context.instance_id,
                "template_name": context.template_name
            },
            "system": asdict(system_info),
            "performance": {
                "memory_before_mb": self._get_memory_usage(),
                "duration_category": self._categorize_duration(duration_ms),
                "success": error is None
            }
        }
        
        # Add request data if provided (sanitized)
        if request_data:
            log_entry["request"] = {
                "data": self._sanitize_data(request_data),
                "size_bytes": len(json.dumps(request_data, default=str)),
                "contains_files": self._contains_files(request_data)
            }
        
        # Add response data if provided (sanitized and analyzed)
        if response_data:
            sanitized_response = self._sanitize_data(response_data)
            log_entry["response"] = {
                "data": sanitized_response,
                "size_bytes": len(json.dumps(response_data, default=str)),
                "record_count": self._count_records(response_data),
                "data_types": self._analyze_data_types(response_data)
            }
        
        # Add error details if provided
        if error:
            log_entry["error"] = {
                "message": error,
                "type": type(error).__name__ if hasattr(error, '__class__') else "string",
                "stack_trace": traceback.format_exc() if hasattr(error, '__traceback__') else None,
                "category": self._categorize_error(error)
            }
        
        # Add rate limiting information
        if rate_limit_info:
            log_entry["rate_limit"] = rate_limit_info
        
        # Write to appropriate log files
        self._write_log_entry(log_entry, timestamp)
        
        # Also log to performance file if duration is significant
        if duration_ms and duration_ms > 1000:  # > 1 second
            self._log_performance_issue(log_entry, timestamp)
        
        # Log errors to separate error file
        if error:
            self._log_error(log_entry, timestamp)
    
    def log_instance_operation(self, operation: str, instance_id: str, 
                              details: Dict[str, Any], context: LogContext,
                              success: bool = True, error: str = None) -> None:
        """
        Log instance-specific operations with detailed tracking.
        
        Args:
            operation (str): Type of operation (create, destroy, start, stop, etc.)
            instance_id (str): VastAI instance ID
            details (dict): Operation-specific details
            context (LogContext): Enhanced context information
            success (bool): Whether operation was successful
            error (str, optional): Error message if operation failed
        """
        timestamp = datetime.now()
        
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "operation_id": context.operation_id,
            "instance": {
                "id": instance_id,
                "operation": operation,
                "success": success,
                "details": details
            },
            "context": {
                "session_id": context.session_id,
                "user_agent": context.user_agent,
                "ip_address": context.ip_address,
                "template_name": context.template_name
            },
            "system": asdict(SystemInfo.capture())
        }
        
        if error:
            log_entry["error"] = {
                "message": error,
                "category": self._categorize_error(error)
            }
        
        # Write to instance operations log
        self._write_instance_log(log_entry, timestamp)
    
    def log_template_execution(self, template_name: str, step_name: str,
                             execution_details: Dict[str, Any], context: LogContext,
                             success: bool = True, error: str = None) -> None:
        """
        Log template step execution with comprehensive details.
        
        Args:
            template_name (str): Name of the template being executed
            step_name (str): Name of the step being executed
            execution_details (dict): Step execution details
            context (LogContext): Enhanced context information
            success (bool): Whether step execution was successful
            error (str, optional): Error message if step failed
        """
        timestamp = datetime.now()
        
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "operation_id": context.operation_id,
            "template": {
                "name": template_name,
                "step": step_name,
                "success": success,
                "execution_details": execution_details,
                "duration_ms": execution_details.get("duration_ms")
            },
            "context": {
                "session_id": context.session_id,
                "user_agent": context.user_agent,
                "ip_address": context.ip_address,
                "instance_id": context.instance_id
            },
            "system": asdict(SystemInfo.capture())
        }
        
        if error:
            log_entry["error"] = {
                "message": error,
                "category": self._categorize_error(error),
                "step_context": execution_details
            }
        
        # Write to operations log
        self._write_operations_log(log_entry, timestamp)
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except Exception:
            return 0.0
    
    def _categorize_duration(self, duration_ms: Optional[float]) -> str:
        """Categorize request duration for analysis"""
        if not duration_ms:
            return "unknown"
        
        if duration_ms < 100:
            return "fast"
        elif duration_ms < 1000:
            return "normal"
        elif duration_ms < 5000:
            return "slow"
        else:
            return "very_slow"
    
    def _categorize_error(self, error: str) -> str:
        """Categorize error for better analysis"""
        if not error:
            return "unknown"
        
        error_lower = str(error).lower()
        
        if "timeout" in error_lower or "time out" in error_lower:
            return "timeout"
        elif "connection" in error_lower or "network" in error_lower:
            return "network"
        elif "authentication" in error_lower or "unauthorized" in error_lower:
            return "auth"
        elif "rate limit" in error_lower or "429" in error_lower:
            return "rate_limit"
        elif "permission" in error_lower or "forbidden" in error_lower:
            return "permission"
        elif "not found" in error_lower or "404" in error_lower:
            return "not_found"
        elif "server error" in error_lower or "500" in error_lower:
            return "server_error"
        else:
            return "application"
    
    def _contains_files(self, data: Any) -> bool:
        """Check if request data contains file uploads"""
        if isinstance(data, dict):
            return any("file" in str(key).lower() or 
                      (isinstance(value, str) and len(value) > 1000)
                      for key, value in data.items())
        return False
    
    def _count_records(self, data: Any) -> int:
        """Count records in response data"""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list):
                    return len(value)
        elif isinstance(data, list):
            return len(data)
        return 0
    
    def _analyze_data_types(self, data: Any) -> Dict[str, int]:
        """Analyze data types in response"""
        type_counts = {}
        
        def count_types(obj):
            if isinstance(obj, dict):
                for value in obj.values():
                    type_name = type(value).__name__
                    type_counts[type_name] = type_counts.get(type_name, 0) + 1
                    if isinstance(value, (dict, list)):
                        count_types(value)
            elif isinstance(obj, list):
                for item in obj:
                    count_types(item)
        
        count_types(data)
        return type_counts
    
    def _sanitize_data(self, data: Any) -> Any:
        """Enhanced data sanitization with better coverage"""
        if isinstance(data, dict):
            sanitized = {}
            sensitive_keys = [
                'api_key', 'password', 'token', 'authorization', 'secret',
                'credit_card', 'payment', 'billing', 'ssh_key', 'private_key'
            ]
            
            for key, value in data.items():
                key_lower = str(key).lower()
                if any(sensitive in key_lower for sensitive in sensitive_keys):
                    sanitized[key] = "***REDACTED***"
                elif isinstance(value, (dict, list)):
                    sanitized[key] = self._sanitize_data(value)
                elif isinstance(value, str) and len(value) > 500:
                    # Truncate very long strings but preserve beginning and end
                    sanitized[key] = value[:200] + "...[TRUNCATED]..." + value[-100:]
                else:
                    sanitized[key] = value
            
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        else:
            return data
    
    def _get_log_filename(self, category: str, date: datetime = None) -> str:
        """Get log filename for a specific category and date"""
        if date is None:
            date = datetime.now()
        return f"{category}_log_{date.strftime('%Y%m%d')}.json"
    
    def _write_log_entry(self, log_entry: Dict[str, Any], timestamp: datetime) -> None:
        """Write log entry to main API log file"""
        filename = self._get_log_filename("api", timestamp)
        filepath = os.path.join(VASTAI_LOG_DIR, 'api', filename)
        self._append_to_log_file(filepath, log_entry)
    
    def _write_instance_log(self, log_entry: Dict[str, Any], timestamp: datetime) -> None:
        """Write log entry to instance operations log file"""
        filename = self._get_log_filename("instances", timestamp)
        filepath = os.path.join(VASTAI_LOG_DIR, 'instances', filename)
        self._append_to_log_file(filepath, log_entry)
    
    def _write_operations_log(self, log_entry: Dict[str, Any], timestamp: datetime) -> None:
        """Write log entry to operations log file"""
        filename = self._get_log_filename("operations", timestamp)
        filepath = os.path.join(VASTAI_LOG_DIR, 'operations', filename)
        self._append_to_log_file(filepath, log_entry)
    
    def _log_performance_issue(self, log_entry: Dict[str, Any], timestamp: datetime) -> None:
        """Log performance issues to separate file"""
        filename = self._get_log_filename("performance", timestamp)
        filepath = os.path.join(VASTAI_LOG_DIR, 'performance', filename)
        self._append_to_log_file(filepath, log_entry)
    
    def _log_error(self, log_entry: Dict[str, Any], timestamp: datetime) -> None:
        """Log errors to separate file"""
        filename = self._get_log_filename("errors", timestamp)
        filepath = os.path.join(VASTAI_LOG_DIR, 'errors', filename)
        self._append_to_log_file(filepath, log_entry)
    
    def _append_to_log_file(self, filepath: str, log_entry: Dict[str, Any]) -> None:
        """Safely append log entry to file"""
        try:
            # Load existing entries
            log_entries = []
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    try:
                        log_entries = json.load(f)
                    except json.JSONDecodeError:
                        log_entries = []
            
            # Append new entry
            log_entries.append(log_entry)
            
            # Write back to file
            with open(filepath, 'w') as f:
                json.dump(log_entries, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to write to log file {filepath}: {str(e)}")

    def log_api(self, message: str, status_code: int, context: LogContext,
                extra_data: Dict[str, Any] = None) -> None:
        """
        Log API interactions and responses.
        
        Args:
            message (str): Log message
            status_code (int): HTTP status code
            context (LogContext): Enhanced logging context
            extra_data (Dict[str, Any], optional): Additional data to log
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "category": "api",
            "message": message,
            "status_code": status_code,
            "context": asdict(context),
            "system_info": asdict(self.system_info),
            "extra_data": extra_data or {}
        }
        
        self._write_log(log_data)
        
        # Standard logging
        self.logger.info(
            f"API - {message} (Status: {status_code})",
            extra={"context": asdict(context), "extra_data": extra_data}
        )

    def log_operation(self, message: str, operation: str, context: LogContext,
                     extra_data: Dict[str, Any] = None) -> None:
        """
        Log general operations and activities.
        
        Args:
            message (str): Log message
            operation (str): Operation type
            context (LogContext): Enhanced logging context
            extra_data (Dict[str, Any], optional): Additional data to log
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "category": "operation",
            "message": message,
            "operation": operation,
            "context": asdict(context),
            "system_info": asdict(self.system_info),
            "extra_data": extra_data or {}
        }
        
        self._write_log(log_data)
        
        # Standard logging
        self.logger.info(
            f"Operation - {operation}: {message}",
            extra={"context": asdict(context), "extra_data": extra_data}
        )

    def log_performance(self, message: str, operation: str, duration: float,
                       context: LogContext, extra_data: Dict[str, Any] = None) -> None:
        """
        Log performance metrics and timing information.
        
        Args:
            message (str): Log message
            operation (str): Operation type
            duration (float): Duration in seconds
            context (LogContext): Enhanced logging context
            extra_data (Dict[str, Any], optional): Additional data to log
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "category": "performance",
            "message": message,
            "operation": operation,
            "duration_seconds": duration,
            "duration_ms": duration * 1000,
            "context": asdict(context),
            "system_info": asdict(self.system_info),
            "extra_data": extra_data or {}
        }
        
        self._write_log(log_data)
        
        # Standard logging
        self.logger.info(
            f"Performance - {operation}: {message} ({duration:.3f}s)",
            extra={"context": asdict(context), "extra_data": extra_data}
        )

    def log_error(self, message: str, error_type: str, context: LogContext,
                  extra_data: Dict[str, Any] = None) -> None:
        """
        Log errors and exceptions.
        
        Args:
            message (str): Error message
            error_type (str): Type of error
            context (LogContext): Enhanced logging context
            extra_data (Dict[str, Any], optional): Additional data to log
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "ERROR",
            "category": "error",
            "message": message,
            "error_type": error_type,
            "context": asdict(context),
            "system_info": asdict(self.system_info),
            "extra_data": extra_data or {}
        }
        
        self._write_log(log_data)
        
        # Standard logging
        self.logger.error(
            f"Error - {error_type}: {message}",
            extra={"context": asdict(context), "extra_data": extra_data}
        )


# Global enhanced logger instance
enhanced_logger = EnhancedVastAILogger()


# Maintain backward compatibility with existing log_api_interaction function
def log_api_interaction(method: str, endpoint: str, request_data: Dict[Any, Any] = None, 
                       response_data: Dict[Any, Any] = None, status_code: int = None,
                       error: str = None, duration_ms: float = None) -> None:
    """
    Backward-compatible API interaction logging function.
    """
    # Create a basic context for backward compatibility
    context = LogContext(
        operation_id=f"legacy_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
        user_agent="vast_api_legacy",
        session_id=None,
        ip_address=None
    )
    
    enhanced_logger.log_api_interaction(
        method=method,
        endpoint=endpoint,
        context=context,
        request_data=request_data,
        response_data=response_data,
        status_code=status_code,
        error=error,
        duration_ms=duration_ms
    )


# Maintain backward compatibility functions
def ensure_vastai_log_dir():
    """Backward compatibility function"""
    return enhanced_logger.ensure_log_directories()


def get_log_filename(date: datetime = None) -> str:
    """
    Get the log filename for a given date.
    
    Args:
        date (datetime, optional): Date for the log file. Defaults to current date.
        
    Returns:
        str: Log filename in format "api_log_yyyymmdd.json"
    """
    if date is None:
        date = datetime.now()
    return f"api_log_{date.strftime('%Y%m%d')}.json"


def get_log_filepath(date: datetime = None) -> str:
    """
    Get the full path to a log file for a given date.
    
    Args:
        date (datetime, optional): Date for the log file. Defaults to current date.
        
    Returns:
        str: Full path to the log file
    """
    filename = get_log_filename(date)
    return os.path.join(VASTAI_LOG_DIR, 'api', filename)


def get_vastai_logs(max_lines: int = 100, date_filter: str = None) -> List[Dict[Any, Any]]:
    """
    Retrieve VastAI API logs with enhanced filtering and analysis.
    
    Args:
        max_lines (int): Maximum number of log entries to return
        date_filter (str, optional): Date filter in YYYYMMDD format
        
    Returns:
        list: List of log entries with enhanced metadata
    """
    if not ensure_vastai_log_dir():
        return []
    
    all_entries = []
    
    try:
        # Search through all log categories
        log_categories = ['api', 'instances', 'operations', 'errors', 'performance']
        
        for category in log_categories:
            category_dir = os.path.join(VASTAI_LOG_DIR, category)
            if not os.path.exists(category_dir):
                continue
                
            if date_filter:
                # Load specific date file
                log_filepath = os.path.join(category_dir, f"{category}_log_{date_filter}.json")
                if os.path.exists(log_filepath):
                    entries = _load_log_file(log_filepath, category)
                    all_entries.extend(entries)
            else:
                # Load all log files, sorted by date (newest first)
                log_files = []
                for filename in os.listdir(category_dir):
                    if filename.startswith(f'{category}_log_') and filename.endswith('.json'):
                        filepath = os.path.join(category_dir, filename)
                        log_files.append((os.path.getmtime(filepath), filepath))
                
                # Sort by modification time (newest first)
                log_files.sort(reverse=True)
                
                for _, filepath in log_files:
                    entries = _load_log_file(filepath, category)
                    all_entries.extend(entries)
        
        # Sort entries by timestamp (newest first) and limit
        all_entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Add analysis metadata to entries
        for entry in all_entries:
            entry['_metadata'] = _analyze_log_entry(entry)
        
        return all_entries[:max_lines]
        
    except Exception as e:
        logger.error(f"Error retrieving VastAI logs: {str(e)}")
        return []


def get_vastai_log_manifest() -> List[Dict[str, Any]]:
    """
    Get a comprehensive manifest of available VastAI log files with analytics.
    
    Returns:
        list: List of log file information with enhanced metadata
    """
    if not ensure_vastai_log_dir():
        return []
    
    manifest = []
    
    try:
        log_categories = ['api', 'instances', 'operations', 'errors', 'performance']
        
        for category in log_categories:
            category_dir = os.path.join(VASTAI_LOG_DIR, category)
            if not os.path.exists(category_dir):
                continue
                
            for filename in os.listdir(category_dir):
                if filename.startswith(f'{category}_log_') and filename.endswith('.json'):
                    filepath = os.path.join(category_dir, filename)
                    try:
                        stat = os.stat(filepath)
                        entries = _load_log_file(filepath, category)
                        
                        # Extract date from filename
                        date_str = filename[len(f'{category}_log_'):-5]  # Remove prefix and .json
                        
                        # Calculate analytics
                        analytics = _calculate_log_analytics(entries)
                        
                        manifest.append({
                            'filename': filename,
                            'category': category,
                            'date': date_str,
                            'size': stat.st_size,
                            'entry_count': len(entries),
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'analytics': analytics
                        })
                    except Exception as e:
                        logger.error(f"Error processing log file {filename}: {str(e)}")
        
        # Sort by date and category
        manifest.sort(key=lambda x: (x['date'], x['category']), reverse=True)
        return manifest
        
    except Exception as e:
        logger.error(f"Error getting VastAI log manifest: {str(e)}")
        return []


def get_log_analytics(date_filter: str = None) -> Dict[str, Any]:
    """
    Get comprehensive analytics for VastAI logs.
    
    Args:
        date_filter (str, optional): Date filter in YYYYMMDD format
        
    Returns:
        dict: Comprehensive analytics data
    """
    logs = get_vastai_logs(max_lines=1000, date_filter=date_filter)
    
    analytics = {
        'total_entries': len(logs),
        'date_range': _get_date_range(logs),
        'api_stats': _calculate_api_stats(logs),
        'error_analysis': _calculate_error_analysis(logs),
        'performance_metrics': _calculate_performance_metrics(logs),
        'system_health': _calculate_system_health(logs),
        'operation_patterns': _calculate_operation_patterns(logs)
    }
    
    return analytics


def _load_log_file(filepath: str, category: str) -> List[Dict[str, Any]]:
    """Load and enrich log entries from a file"""
    try:
        with open(filepath, 'r') as f:
            entries = json.load(f)
        
        # Add category to each entry
        for entry in entries:
            entry['_category'] = category
            
        return entries
    except Exception as e:
        logger.error(f"Error loading log file {filepath}: {str(e)}")
        return []


def _analyze_log_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a single log entry for metadata"""
    metadata = {
        'category': entry.get('_category', 'unknown'),
        'has_error': 'error' in entry,
        'duration_category': 'unknown',
        'operation_type': 'unknown'
    }
    
    # Analyze duration
    if 'api' in entry and 'duration_ms' in entry['api']:
        duration = entry['api']['duration_ms']
        if duration:
            if duration < 100:
                metadata['duration_category'] = 'fast'
            elif duration < 1000:
                metadata['duration_category'] = 'normal'
            elif duration < 5000:
                metadata['duration_category'] = 'slow'
            else:
                metadata['duration_category'] = 'very_slow'
    
    # Analyze operation type
    if 'api' in entry:
        endpoint = entry['api'].get('endpoint', '')
        if 'instances' in endpoint:
            metadata['operation_type'] = 'instance_management'
        elif 'offers' in endpoint or 'search' in endpoint:
            metadata['operation_type'] = 'offer_search'
        elif 'create' in endpoint:
            metadata['operation_type'] = 'resource_creation'
        else:
            metadata['operation_type'] = 'api_call'
    elif 'template' in entry:
        metadata['operation_type'] = 'template_execution'
    elif 'instance' in entry:
        metadata['operation_type'] = 'instance_operation'
    
    return metadata


def _calculate_log_analytics(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate analytics for a set of log entries"""
    if not entries:
        return {}
    
    total = len(entries)
    errors = sum(1 for entry in entries if 'error' in entry)
    
    # Duration analysis
    durations = []
    for entry in entries:
        if 'api' in entry and 'duration_ms' in entry['api']:
            duration = entry['api'].get('duration_ms')
            if duration:
                durations.append(duration)
    
    duration_stats = {}
    if durations:
        duration_stats = {
            'avg': sum(durations) / len(durations),
            'min': min(durations),
            'max': max(durations),
            'count': len(durations)
        }
    
    return {
        'total_entries': total,
        'error_count': errors,
        'error_rate': errors / total if total > 0 else 0,
        'duration_stats': duration_stats
    }


def _get_date_range(logs: List[Dict[str, Any]]) -> Dict[str, str]:
    """Get date range from logs"""
    if not logs:
        return {}
    
    timestamps = [entry.get('timestamp') for entry in logs if entry.get('timestamp')]
    timestamps = [ts for ts in timestamps if ts]
    
    if not timestamps:
        return {}
    
    return {
        'earliest': min(timestamps),
        'latest': max(timestamps)
    }


def _calculate_api_stats(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate API-specific statistics"""
    api_logs = [log for log in logs if 'api' in log]
    
    if not api_logs:
        return {}
    
    methods = {}
    endpoints = {}
    status_codes = {}
    
    for log in api_logs:
        api_info = log['api']
        
        method = api_info.get('method', 'unknown')
        methods[method] = methods.get(method, 0) + 1
        
        endpoint = api_info.get('endpoint', 'unknown')
        endpoints[endpoint] = endpoints.get(endpoint, 0) + 1
        
        status_code = api_info.get('status_code', 'unknown')
        status_codes[str(status_code)] = status_codes.get(str(status_code), 0) + 1
    
    return {
        'total_api_calls': len(api_logs),
        'methods': methods,
        'endpoints': endpoints,
        'status_codes': status_codes
    }


def _calculate_error_analysis(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate error analysis"""
    error_logs = [log for log in logs if 'error' in log]
    
    if not error_logs:
        return {'total_errors': 0}
    
    error_categories = {}
    error_types = {}
    
    for log in error_logs:
        error_info = log['error']
        
        category = error_info.get('category', 'unknown')
        error_categories[category] = error_categories.get(category, 0) + 1
        
        error_type = error_info.get('type', 'unknown')
        error_types[error_type] = error_types.get(error_type, 0) + 1
    
    return {
        'total_errors': len(error_logs),
        'error_categories': error_categories,
        'error_types': error_types,
        'error_rate': len(error_logs) / len(logs) if logs else 0
    }


def _calculate_performance_metrics(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate performance metrics"""
    durations = []
    
    for log in logs:
        if 'api' in log and 'duration_ms' in log['api']:
            duration = log['api'].get('duration_ms')
            if duration:
                durations.append(duration)
    
    if not durations:
        return {}
    
    durations.sort()
    n = len(durations)
    
    return {
        'total_requests': n,
        'avg_duration_ms': sum(durations) / n,
        'min_duration_ms': durations[0],
        'max_duration_ms': durations[-1],
        'p50_duration_ms': durations[n // 2],
        'p95_duration_ms': durations[int(n * 0.95)],
        'p99_duration_ms': durations[int(n * 0.99)],
        'slow_requests': sum(1 for d in durations if d > 1000)
    }


def _calculate_system_health(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate system health metrics"""
    system_logs = [log for log in logs if 'system' in log]
    
    if not system_logs:
        return {}
    
    cpu_usage = []
    memory_usage = []
    
    for log in system_logs:
        system_info = log['system']
        
        if 'cpu_usage' in system_info:
            cpu_usage.append(system_info['cpu_usage'])
        
        if 'memory_usage' in system_info:
            memory_usage.append(system_info['memory_usage'])
    
    health = {}
    
    if cpu_usage:
        health['avg_cpu_usage'] = sum(cpu_usage) / len(cpu_usage)
        health['max_cpu_usage'] = max(cpu_usage)
    
    if memory_usage:
        health['avg_memory_usage'] = sum(memory_usage) / len(memory_usage)
        health['max_memory_usage'] = max(memory_usage)
    
    return health


def _calculate_operation_patterns(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate operation patterns and trends"""
    operations = {}
    
    for log in logs:
        metadata = log.get('_metadata', {})
        op_type = metadata.get('operation_type', 'unknown')
        operations[op_type] = operations.get(op_type, 0) + 1
    
    return {
        'operation_types': operations,
        'most_common_operation': max(operations.items(), key=lambda x: x[1])[0] if operations else None
    }