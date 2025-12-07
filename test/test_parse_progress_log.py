"""
Test for _parse_progress_log function
Verifies that progress log parsing correctly builds nodes array with download stats
"""

import unittest


def _parse_progress_log_standalone(log_content: str, current_progress: dict) -> list:
    """
    Standalone version of _parse_progress_log for testing.
    Parse progress log to build nodes array with current state of each node.
    Log format: [TIMESTAMP] EVENT_TYPE|NODE_NAME|STATUS|MESSAGE
    Returns: List of node objects with name, status, message, and stats
    """
    nodes_dict = {}  # Use dict to track latest state of each node
    
    if not log_content:
        return []
    
    for line in log_content.strip().split('\n'):
        if not line or not line.startswith('['):
            continue
            
        try:
            # Parse log line: [TIMESTAMP] EVENT_TYPE|NODE_NAME|STATUS|MESSAGE
            parts = line.split('] ', 1)
            if len(parts) < 2:
                continue
                
            timestamp = parts[0][1:]  # Remove leading [
            rest = parts[1]
            
            pipe_parts = rest.split('|')
            if len(pipe_parts) < 3:
                continue
                
            event_type = pipe_parts[0]
            node_name = pipe_parts[1]
            status = pipe_parts[2]
            message = pipe_parts[3] if len(pipe_parts) > 3 else ''
            
            # Skip non-node events
            if event_type not in ['NODE', 'START', 'INFO', 'COMPLETE']:
                continue
            
            # Skip system messages
            if node_name in ['installer', 'Initializing', 'Starting installation']:
                continue
            
            # Update or create node entry
            if node_name not in nodes_dict:
                nodes_dict[node_name] = {
                    'name': node_name,
                    'status': status,
                    'message': message,
                    'clone_progress': None,
                    'download_rate': None,
                    'data_received': None
                }
            else:
                # Update existing node
                nodes_dict[node_name]['status'] = status
                if message:
                    nodes_dict[node_name]['message'] = message
                    
        except Exception as e:
            print(f"Error parsing log line: {line} - {e}")
            continue
    
    # Convert dict to list
    nodes_list = list(nodes_dict.values())
    
    # Add current progress info from JSON to the active node
    if current_progress:
        current_node_name = current_progress.get('current_node')
        current_status = current_progress.get('current_status', 'running')
        clone_progress = current_progress.get('clone_progress')
        download_rate = current_progress.get('download_rate')
        data_received = current_progress.get('data_received')
        
        # Find and update the current node with real-time stats
        for node in nodes_list:
            if node['name'] == current_node_name:
                node['status'] = current_status
                if clone_progress is not None:
                    node['clone_progress'] = clone_progress
                if download_rate:
                    node['download_rate'] = download_rate
                if data_received:
                    node['data_received'] = data_received
                break
        else:
            # Current node not in list yet, add it
            if current_node_name and current_node_name not in ['Initializing', 'Starting installation']:
                nodes_list.append({
                    'name': current_node_name,
                    'status': current_status,
                    'message': '',
                    'clone_progress': clone_progress,
                    'download_rate': download_rate,
                    'data_received': data_received
                })
    
    return nodes_list


class TestParseProgressLog(unittest.TestCase):
    """Test the _parse_progress_log function"""
    
    def test_empty_log(self):
        """Test parsing empty log"""
        result = _parse_progress_log_standalone('', {})
        self.assertEqual(result, [])
    
    def test_single_node(self):
        """Test parsing log with single node"""
        log_content = "[2025-01-01 10:00:00] NODE|ComfyUI-Manager|cloning|Cloning repository\n"
        current_progress = {
            'current_node': 'ComfyUI-Manager',
            'current_status': 'running',
            'clone_progress': 45,
            'download_rate': '1.2 MiB/s',
            'data_received': '5.4 MiB'
        }
        
        result = _parse_progress_log_standalone(log_content, current_progress)
        
        self.assertEqual(len(result), 1)
        node = result[0]
        self.assertEqual(node['name'], 'ComfyUI-Manager')
        self.assertEqual(node['status'], 'running')
        self.assertEqual(node['clone_progress'], 45)
        self.assertEqual(node['download_rate'], '1.2 MiB/s')
        self.assertEqual(node['data_received'], '5.4 MiB')
    
    def test_multiple_nodes(self):
        """Test parsing log with multiple nodes"""
        log_content = """[2025-01-01 10:00:00] NODE|ComfyUI-Manager|cloning|Cloning repository
[2025-01-01 10:00:05] NODE|ComfyUI-Manager|success|Installed successfully
[2025-01-01 10:00:10] NODE|ComfyUI-Custom-Scripts|cloning|Cloning repository
"""
        current_progress = {
            'current_node': 'ComfyUI-Custom-Scripts',
            'current_status': 'running',
            'clone_progress': 25,
            'download_rate': '2.5 MiB/s',
            'data_received': '3.1 MiB'
        }
        
        result = _parse_progress_log_standalone(log_content, current_progress)
        
        self.assertEqual(len(result), 2)
        
        # First node should be completed
        node1 = next(n for n in result if n['name'] == 'ComfyUI-Manager')
        self.assertEqual(node1['status'], 'success')
        
        # Second node should have current progress stats
        node2 = next(n for n in result if n['name'] == 'ComfyUI-Custom-Scripts')
        self.assertEqual(node2['status'], 'running')
        self.assertEqual(node2['clone_progress'], 25)
        self.assertEqual(node2['download_rate'], '2.5 MiB/s')
        self.assertEqual(node2['data_received'], '3.1 MiB')
    
    def test_node_status_updates(self):
        """Test that node status gets updated when same node appears multiple times"""
        log_content = """[2025-01-01 10:00:00] NODE|ComfyUI-Manager|processing|Starting
[2025-01-01 10:00:05] NODE|ComfyUI-Manager|cloning|Cloning repository
[2025-01-01 10:00:10] NODE|ComfyUI-Manager|success|Installed successfully
"""
        current_progress = {}
        
        result = _parse_progress_log_standalone(log_content, current_progress)
        
        # Should have only one node with final status
        self.assertEqual(len(result), 1)
        node = result[0]
        self.assertEqual(node['name'], 'ComfyUI-Manager')
        self.assertEqual(node['status'], 'success')
        self.assertEqual(node['message'], 'Installed successfully')
    
    def test_skip_system_messages(self):
        """Test that system messages are skipped"""
        log_content = """[2025-01-01 10:00:00] START|installer|initializing|Beginning installation
[2025-01-01 10:00:01] INFO|installer|installing|Found 10 nodes to install
[2025-01-01 10:00:02] NODE|ComfyUI-Manager|cloning|Cloning repository
[2025-01-01 10:00:10] COMPLETE|installer|completed|Installation finished
"""
        current_progress = {}
        
        result = _parse_progress_log_standalone(log_content, current_progress)
        
        # Should only have ComfyUI-Manager, not installer messages
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'ComfyUI-Manager')
    
    def test_new_node_from_current_progress(self):
        """Test that current node is added if not in log yet"""
        log_content = "[2025-01-01 10:00:00] NODE|ComfyUI-Manager|success|Installed\n"
        current_progress = {
            'current_node': 'ComfyUI-New-Node',
            'current_status': 'cloning',
            'clone_progress': 10,
            'download_rate': '1.0 MiB/s',
            'data_received': '0.5 MiB'
        }
        
        result = _parse_progress_log_standalone(log_content, current_progress)
        
        # Should have both nodes
        self.assertEqual(len(result), 2)
        
        # Check new node from current progress
        new_node = next(n for n in result if n['name'] == 'ComfyUI-New-Node')
        self.assertEqual(new_node['status'], 'cloning')
        self.assertEqual(new_node['clone_progress'], 10)


if __name__ == '__main__':
    unittest.main()
