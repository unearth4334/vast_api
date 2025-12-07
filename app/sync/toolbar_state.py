"""
Toolbar State Manager
Manages per-client toolbar state for VastAI connection toolbar
"""

import json
import os
import time
import uuid
from typing import Dict, Optional
from threading import Lock

# Directory for storing toolbar state files
STATE_DIR = '/tmp/toolbar_states'

# Ensure state directory exists
os.makedirs(STATE_DIR, exist_ok=True)

# In-memory cache for fast access
_state_cache: Dict[str, Dict] = {}
_cache_lock = Lock()

# State TTL (Time To Live) - 24 hours
STATE_TTL = 24 * 60 * 60


class ToolbarStateManager:
    """Manages toolbar state for each client session"""
    
    @staticmethod
    def _get_state_file_path(session_id: str) -> str:
        """Get the file path for a session's state"""
        return os.path.join(STATE_DIR, f'toolbar_state_{session_id}.json')
    
    @staticmethod
    def _cleanup_old_states():
        """Remove state files older than TTL"""
        try:
            current_time = time.time()
            for filename in os.listdir(STATE_DIR):
                if filename.startswith('toolbar_state_'):
                    filepath = os.path.join(STATE_DIR, filename)
                    try:
                        # Check file modification time
                        file_mtime = os.path.getmtime(filepath)
                        if current_time - file_mtime > STATE_TTL:
                            os.remove(filepath)
                            # Also remove from cache
                            session_id = filename.replace('toolbar_state_', '').replace('.json', '')
                            with _cache_lock:
                                _state_cache.pop(session_id, None)
                    except Exception as e:
                        pass  # Ignore errors for individual files
        except Exception as e:
            pass  # Ignore cleanup errors
    
    @staticmethod
    def get_or_create_session_id(provided_session_id: Optional[str] = None) -> str:
        """
        Get existing session ID or create a new one
        
        Args:
            provided_session_id: Optional session ID from client
            
        Returns:
            Valid session ID
        """
        if provided_session_id:
            # Validate existing session
            state_file = ToolbarStateManager._get_state_file_path(provided_session_id)
            if os.path.exists(state_file):
                return provided_session_id
        
        # Create new session ID
        return str(uuid.uuid4())
    
    @staticmethod
    def get_state(session_id: str) -> Dict:
        """
        Get toolbar state for a session
        
        Args:
            session_id: Client session ID
            
        Returns:
            Toolbar state dictionary
        """
        # Check cache first
        with _cache_lock:
            if session_id in _state_cache:
                return _state_cache[session_id].copy()
        
        # Try to load from file
        state_file = ToolbarStateManager._get_state_file_path(session_id)
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    # Update cache
                    with _cache_lock:
                        _state_cache[session_id] = state
                    return state.copy()
            except Exception:
                pass  # Fall through to default state
        
        # Return default state
        default_state = {
            'session_id': session_id,
            'selected_instance_id': None,
            'ssh_connection_string': '',
            'ssh_host': None,
            'ssh_port': None,
            'connection_status': 'disconnected',  # disconnected, testing, connected, failed
            'connection_tested': False,
            'last_refresh': None,
            'instance_status': None,  # running, stopped, etc.
            'created_at': time.time(),
            'updated_at': time.time()
        }
        
        # Save default state
        ToolbarStateManager.save_state(session_id, default_state)
        return default_state.copy()
    
    @staticmethod
    def save_state(session_id: str, state: Dict) -> bool:
        """
        Save toolbar state for a session
        
        Args:
            session_id: Client session ID
            state: State dictionary to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update timestamp
            state['updated_at'] = time.time()
            state['session_id'] = session_id
            
            # Save to file
            state_file = ToolbarStateManager._get_state_file_path(session_id)
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            # Update cache
            with _cache_lock:
                _state_cache[session_id] = state.copy()
            
            # Cleanup old states periodically (1% chance)
            import random
            if random.random() < 0.01:
                ToolbarStateManager._cleanup_old_states()
            
            return True
        except Exception as e:
            return False
    
    @staticmethod
    def update_state(session_id: str, updates: Dict) -> Dict:
        """
        Update specific fields in toolbar state
        
        Args:
            session_id: Client session ID
            updates: Dictionary of fields to update
            
        Returns:
            Updated state dictionary
        """
        state = ToolbarStateManager.get_state(session_id)
        state.update(updates)
        ToolbarStateManager.save_state(session_id, state)
        return state
    
    @staticmethod
    def delete_state(session_id: str) -> bool:
        """
        Delete toolbar state for a session
        
        Args:
            session_id: Client session ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove from cache
            with _cache_lock:
                _state_cache.pop(session_id, None)
            
            # Remove file
            state_file = ToolbarStateManager._get_state_file_path(session_id)
            if os.path.exists(state_file):
                os.remove(state_file)
            
            return True
        except Exception:
            return False
