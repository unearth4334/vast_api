"""
Unit tests for ComfyUI Workflow State
"""

import unittest
import json
from datetime import datetime
from app.sync.comfyui_workflow_state import (
    ComfyUIWorkflowState,
    ComfyUINodeState,
    ComfyUIOutputFile,
    ComfyUIWorkflowStatus,
    ComfyUINodeStatus,
    create_comfyui_workflow_state,
    parse_workflow_nodes
)


class TestComfyUINodeState(unittest.TestCase):
    """Test ComfyUINodeState functionality."""
    
    def test_create_node_state(self):
        """Test creating a node state."""
        node = ComfyUINodeState(
            node_id="7",
            node_type="LoadImage",
            status=ComfyUINodeStatus.PENDING
        )
        
        self.assertEqual(node.node_id, "7")
        self.assertEqual(node.node_type, "LoadImage")
        self.assertEqual(node.status, ComfyUINodeStatus.PENDING)
        self.assertEqual(node.progress, 0.0)
    
    def test_node_to_dict(self):
        """Test node serialization to dict."""
        node = ComfyUINodeState(
            node_id="7",
            node_type="LoadImage",
            status=ComfyUINodeStatus.EXECUTING,
            progress=50.0,
            message="Loading..."
        )
        
        data = node.to_dict()
        
        self.assertEqual(data['node_id'], "7")
        self.assertEqual(data['node_type'], "LoadImage")
        self.assertEqual(data['status'], "executing")
        self.assertEqual(data['progress'], 50.0)
        self.assertEqual(data['message'], "Loading...")
    
    def test_node_from_dict(self):
        """Test node deserialization from dict."""
        data = {
            'node_id': "12",
            'node_type': "KSampler",
            'status': "executed",
            'progress': 100.0
        }
        
        node = ComfyUINodeState.from_dict(data)
        
        self.assertEqual(node.node_id, "12")
        self.assertEqual(node.node_type, "KSampler")
        self.assertEqual(node.status, ComfyUINodeStatus.EXECUTED)
        self.assertEqual(node.progress, 100.0)


class TestComfyUIOutputFile(unittest.TestCase):
    """Test ComfyUIOutputFile functionality."""
    
    def test_create_output_file(self):
        """Test creating an output file."""
        output = ComfyUIOutputFile(
            filename="ComfyUI_00001_.png",
            file_type="image",
            remote_path="/workspace/ComfyUI/output/ComfyUI_00001_.png"
        )
        
        self.assertEqual(output.filename, "ComfyUI_00001_.png")
        self.assertEqual(output.file_type, "image")
        self.assertFalse(output.downloaded)
    
    def test_output_to_dict(self):
        """Test output serialization to dict."""
        output = ComfyUIOutputFile(
            filename="test.png",
            file_type="image",
            remote_path="/remote/test.png",
            downloaded=True,
            local_path="/local/test.png"
        )
        
        data = output.to_dict()
        
        self.assertEqual(data['filename'], "test.png")
        self.assertEqual(data['type'], "image")
        self.assertTrue(data['downloaded'])
        self.assertEqual(data['local_path'], "/local/test.png")


class TestComfyUIWorkflowState(unittest.TestCase):
    """Test ComfyUIWorkflowState functionality."""
    
    def test_create_workflow_state(self):
        """Test creating a workflow state."""
        state = create_comfyui_workflow_state(
            workflow_id="test_workflow_123",
            ssh_connection="ssh -p 12345 root@example.com",
            workflow_file="/path/to/workflow.json",
            workflow_name="Test Workflow"
        )
        
        self.assertEqual(state.workflow_id, "test_workflow_123")
        self.assertEqual(state.workflow_name, "Test Workflow")
        self.assertEqual(state.status, ComfyUIWorkflowStatus.QUEUED)
        self.assertIsNotNone(state.queue_time)
    
    def test_update_progress(self):
        """Test updating workflow progress."""
        state = create_comfyui_workflow_state(
            workflow_id="test",
            ssh_connection="ssh test",
            workflow_file="/test.json"
        )
        
        state.total_nodes = 10
        state.update_progress(5, "node_5")
        
        self.assertEqual(state.completed_nodes, 5)
        self.assertEqual(state.current_node, "node_5")
        self.assertEqual(state.progress_percent, 50.0)
    
    def test_update_node_status(self):
        """Test updating node status."""
        state = create_comfyui_workflow_state(
            workflow_id="test",
            ssh_connection="ssh test",
            workflow_file="/test.json"
        )
        
        # Add nodes
        state.nodes = [
            ComfyUINodeState("1", "LoadImage", ComfyUINodeStatus.PENDING),
            ComfyUINodeState("2", "KSampler", ComfyUINodeStatus.PENDING)
        ]
        
        # Update status
        state.update_node_status("1", ComfyUINodeStatus.EXECUTED, progress=100.0)
        
        self.assertEqual(state.nodes[0].status, ComfyUINodeStatus.EXECUTED)
        self.assertEqual(state.nodes[0].progress, 100.0)
    
    def test_add_output(self):
        """Test adding output files."""
        state = create_comfyui_workflow_state(
            workflow_id="test",
            ssh_connection="ssh test",
            workflow_file="/test.json"
        )
        
        state.add_output("output1.png", "image", "/remote/output1.png")
        
        self.assertEqual(len(state.outputs), 1)
        self.assertEqual(state.outputs[0].filename, "output1.png")
        self.assertFalse(state.outputs[0].downloaded)
    
    def test_mark_output_downloaded(self):
        """Test marking output as downloaded."""
        state = create_comfyui_workflow_state(
            workflow_id="test",
            ssh_connection="ssh test",
            workflow_file="/test.json"
        )
        
        state.add_output("output1.png", "image", "/remote/output1.png")
        state.mark_output_downloaded("output1.png", "/local/output1.png")
        
        self.assertTrue(state.outputs[0].downloaded)
        self.assertEqual(state.outputs[0].local_path, "/local/output1.png")
    
    def test_set_error(self):
        """Test setting error state."""
        state = create_comfyui_workflow_state(
            workflow_id="test",
            ssh_connection="ssh test",
            workflow_file="/test.json"
        )
        
        state.set_error("Test error", "node_5")
        
        self.assertEqual(state.status, ComfyUIWorkflowStatus.FAILED)
        self.assertEqual(state.error_message, "Test error")
        self.assertEqual(state.failed_node, "node_5")
        self.assertIsNotNone(state.end_time)
    
    def test_set_completed(self):
        """Test setting completed state."""
        state = create_comfyui_workflow_state(
            workflow_id="test",
            ssh_connection="ssh test",
            workflow_file="/test.json"
        )
        
        state.set_completed()
        
        self.assertEqual(state.status, ComfyUIWorkflowStatus.COMPLETED)
        self.assertEqual(state.progress_percent, 100.0)
        self.assertIsNotNone(state.end_time)
    
    def test_to_dict(self):
        """Test serialization to dict."""
        state = create_comfyui_workflow_state(
            workflow_id="test_workflow",
            ssh_connection="ssh test",
            workflow_file="/test.json",
            workflow_name="Test"
        )
        
        state.prompt_id = "prompt_123"
        state.total_nodes = 5
        state.update_progress(2, "node_2")
        
        data = state.to_dict()
        
        self.assertEqual(data['workflow_id'], "test_workflow")
        self.assertEqual(data['workflow_name'], "Test")
        self.assertEqual(data['type'], "comfyui_workflow")
        self.assertEqual(data['prompt_id'], "prompt_123")
        self.assertEqual(data['progress']['total_nodes'], 5)
        self.assertEqual(data['progress']['completed_nodes'], 2)
        self.assertIn('timing', data)
        self.assertIn('queue_time', data['timing'])
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            'workflow_id': "test_workflow",
            'type': "comfyui_workflow",
            'workflow_name': "Test",
            'prompt_id': "prompt_123",
            'ssh_connection': "ssh test",
            'workflow_file': "/test.json",
            'status': "executing",
            'progress': {
                'queue_position': 0,
                'current_node': "node_2",
                'total_nodes': 5,
                'completed_nodes': 2,
                'progress_percent': 40.0
            },
            'nodes': [
                {
                    'node_id': "1",
                    'node_type': "LoadImage",
                    'status': "executed",
                    'progress': 100.0
                }
            ],
            'timing': {
                'queue_time': "2024-01-01T00:00:00",
                'start_time': "2024-01-01T00:01:00"
            },
            'outputs': [],
            'error': None
        }
        
        state = ComfyUIWorkflowState.from_dict(data)
        
        self.assertEqual(state.workflow_id, "test_workflow")
        self.assertEqual(state.workflow_name, "Test")
        self.assertEqual(state.status, ComfyUIWorkflowStatus.EXECUTING)
        self.assertEqual(state.total_nodes, 5)
        self.assertEqual(state.completed_nodes, 2)
        self.assertEqual(len(state.nodes), 1)
        self.assertEqual(state.nodes[0].node_id, "1")


class TestParseWorkflowNodes(unittest.TestCase):
    """Test parsing workflow JSON."""
    
    def test_parse_workflow_nodes(self):
        """Test parsing nodes from workflow JSON."""
        workflow_data = {
            "7": {
                "class_type": "LoadImage",
                "inputs": {"image": "input.png"}
            },
            "12": {
                "class_type": "KSampler",
                "inputs": {"model": ["4", 0]}
            },
            "15": {
                "class_type": "SaveImage",
                "inputs": {"images": ["12", 0]}
            }
        }
        
        nodes = parse_workflow_nodes(workflow_data)
        
        self.assertEqual(len(nodes), 3)
        node_ids = [n.node_id for n in nodes]
        self.assertIn("7", node_ids)
        self.assertIn("12", node_ids)
        self.assertIn("15", node_ids)
        
        # Check node types
        load_image_node = next(n for n in nodes if n.node_id == "7")
        self.assertEqual(load_image_node.node_type, "LoadImage")
        self.assertEqual(load_image_node.status, ComfyUINodeStatus.PENDING)


if __name__ == '__main__':
    unittest.main()
