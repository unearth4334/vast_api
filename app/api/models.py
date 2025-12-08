"""
Flask API endpoints for model scanning and discovery.
Provides endpoints for scanning remote SSH instances for available models.
"""

import logging
import time
import threading
from flask import Blueprint, request, jsonify

from .model_scanner import ModelScanner, get_model_discovery_config

logger = logging.getLogger(__name__)

bp = Blueprint('models', __name__, url_prefix='/api/models')

# Thread-safe cache for model scan results
_model_cache = {}
_cache_lock = threading.Lock()


def get_cache_key(ssh_connection: str, model_type: str, search_pattern: str) -> str:
    """Generate cache key for model scan results."""
    return f"{ssh_connection}:{model_type}:{search_pattern}"


def get_cached_result(cache_key: str, ttl: int = 300) -> dict:
    """
    Get cached model scan result if still valid (thread-safe).
    
    Args:
        cache_key: Cache key
        ttl: Time-to-live in seconds
        
    Returns:
        Cached result or None
    """
    with _cache_lock:
        if cache_key in _model_cache:
            cached = _model_cache[cache_key]
            if time.time() - cached['timestamp'] < ttl:
                return cached
    return None


def set_cached_result(cache_key: str, models: list) -> None:
    """Cache model scan result (thread-safe)."""
    with _cache_lock:
        _model_cache[cache_key] = {
            'data': models,
            'timestamp': time.time()
        }


@bp.route('/scan', methods=['POST', 'OPTIONS'])
def scan_models():
    """
    Scan SSH instance for available models.
    
    Request body:
        ssh_connection: SSH connection string (e.g., 'ssh -p 2838 root@104.189.178.116')
        model_type: Type of models to scan ('diffusion_models', 'loras', 'text_encoders', 'vae', 'upscale_models')
        search_pattern: Search pattern ('high_low_pair' or 'single')
        force_refresh: Optional boolean to bypass cache
    
    Response:
        success: Boolean indicating success
        models: List of model objects
        cached: Boolean indicating if result was from cache
        cache_timestamp: ISO timestamp when result was cached
    """
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json() if request.is_json else {}
        
        ssh_connection = data.get('ssh_connection')
        model_type = data.get('model_type')
        search_pattern = data.get('search_pattern', 'single')
        force_refresh = data.get('force_refresh', False)
        
        if not ssh_connection:
            return jsonify({
                'success': False,
                'message': 'ssh_connection is required'
            }), 400
        
        if not model_type:
            return jsonify({
                'success': False,
                'message': 'model_type is required'
            }), 400
        
        # Load configuration
        config = get_model_discovery_config()
        
        if not config:
            return jsonify({
                'success': False,
                'message': 'Model discovery configuration not found'
            }), 500
        
        base_paths = config.get('base_paths', {})
        if model_type not in base_paths:
            return jsonify({
                'success': False,
                'message': f'Unknown model type: {model_type}'
            }), 400
        
        # Check cache
        cache_key = get_cache_key(ssh_connection, model_type, search_pattern)
        cache_ttl = config.get('cache_ttl', 300)
        
        if not force_refresh:
            cached = get_cached_result(cache_key, cache_ttl)
            if cached:
                logger.info(f"Returning cached result for {model_type}")
                return jsonify({
                    'success': True,
                    'models': cached['data'],
                    'cached': True,
                    'cache_timestamp': time.strftime(
                        '%Y-%m-%dT%H:%M:%SZ',
                        time.gmtime(cached['timestamp'])
                    )
                })
        
        # Scan for models
        scanner = ModelScanner(ssh_connection, config)
        base_path = base_paths[model_type]
        
        if search_pattern == 'high_low_pair':
            pattern_config = config.get('high_low_patterns', {}).get(model_type)
            models = scanner.scan_high_low_pairs(base_path, pattern_config)
        else:
            models = scanner.scan_single_models(base_path, model_type)
            
            # For upscale_models, also check ESRGAN directory as fallback
            if model_type == 'upscale_models' and 'ESRGAN' in base_paths:
                esrgan_models = scanner.scan_single_models(base_paths['ESRGAN'], model_type)
                # Merge results, avoiding duplicates
                existing_paths = {m['path'] for m in models}
                for model in esrgan_models:
                    if model['path'] not in existing_paths:
                        models.append(model)
                logger.info(f"Added {len(esrgan_models)} models from ESRGAN directory")
        
        # Cache result
        set_cached_result(cache_key, models)
        
        return jsonify({
            'success': True,
            'models': models,
            'cached': False,
            'cache_timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        })
        
    except ValueError as e:
        logger.error(f"Validation error in model scan: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Error scanning models: {e}")
        return jsonify({
            'success': False,
            'message': f'Error scanning models: {str(e)}'
        }), 500


@bp.route('/cache/invalidate', methods=['POST', 'OPTIONS'])
def invalidate_cache():
    """
    Invalidate cached model scan results.
    
    Request body:
        ssh_connection: Optional SSH connection to invalidate
        model_type: Optional model type to invalidate
        
    If no parameters provided, invalidates entire cache.
    """
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        data = request.get_json() if request.is_json else {}
        
        ssh_connection = data.get('ssh_connection')
        model_type = data.get('model_type')
        
        with _cache_lock:
            if not ssh_connection and not model_type:
                # Clear entire cache
                _model_cache.clear()
                return jsonify({
                    'success': True,
                    'message': 'Entire model cache invalidated'
                })
            
            # Selective invalidation
            keys_to_remove = []
            for key in _model_cache.keys():
                if ssh_connection and ssh_connection not in key:
                    continue
                if model_type and model_type not in key:
                    continue
                keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del _model_cache[key]
        
        return jsonify({
            'success': True,
            'message': f'Invalidated {len(keys_to_remove)} cache entries'
        })
        
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        return jsonify({
            'success': False,
            'message': f'Error invalidating cache: {str(e)}'
        }), 500


@bp.route('/types', methods=['GET', 'OPTIONS'])
def list_model_types():
    """
    List available model types and their configuration.
    """
    if request.method == 'OPTIONS':
        return ("", 204)
    
    try:
        config = get_model_discovery_config()
        
        return jsonify({
            'success': True,
            'model_types': list(config.get('base_paths', {}).keys()),
            'high_low_pair_types': list(config.get('high_low_patterns', {}).keys()),
            'extensions': config.get('extensions', [])
        })
        
    except Exception as e:
        logger.error(f"Error listing model types: {e}")
        return jsonify({
            'success': False,
            'message': f'Error listing model types: {str(e)}'
        }), 500
