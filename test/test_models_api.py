#!/usr/bin/env python3
"""
Test the Models API endpoints for model scanning
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.sync.sync_api import app


class TestModelsAPI(unittest.TestCase):
    """Test the Models API endpoints"""

    def setUp(self):
        """Set up test fixtures"""
        self.app = app.test_client()
        self.app.testing = True

    def test_models_scan_missing_ssh_connection(self):
        """Test scan endpoint with missing SSH connection"""
        response = self.app.post('/api/models/scan',
                                json={'model_type': 'diffusion_models'},
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('ssh_connection is required', data['message'])

    def test_models_scan_missing_model_type(self):
        """Test scan endpoint with missing model type"""
        response = self.app.post('/api/models/scan',
                                json={'ssh_connection': 'ssh -p 2838 root@test'},
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('model_type is required', data['message'])

    def test_models_scan_unknown_model_type(self):
        """Test scan endpoint with unknown model type"""
        response = self.app.post('/api/models/scan',
                                json={
                                    'ssh_connection': 'ssh -p 2838 root@test',
                                    'model_type': 'unknown_type'
                                },
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('Unknown model type', data['message'])

    def test_models_types_endpoint(self):
        """Test model types listing endpoint"""
        response = self.app.get('/api/models/types')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('model_types', data)
        self.assertIn('extensions', data)
        
        # Check that expected model types are present
        model_types = data['model_types']
        self.assertIn('diffusion_models', model_types)
        self.assertIn('loras', model_types)
        self.assertIn('text_encoders', model_types)
        self.assertIn('vae', model_types)
        self.assertIn('upscale_models', model_types)

    def test_models_cache_invalidate(self):
        """Test cache invalidation endpoint"""
        response = self.app.post('/api/models/cache/invalidate',
                                json={},
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('invalidated', data['message'].lower())

    def test_options_request_scan(self):
        """Test OPTIONS request for CORS preflight"""
        response = self.app.options('/api/models/scan')
        self.assertEqual(response.status_code, 204)

    def test_options_request_types(self):
        """Test OPTIONS request for types endpoint"""
        response = self.app.options('/api/models/types')
        self.assertEqual(response.status_code, 204)


class TestModelScanner(unittest.TestCase):
    """Test the ModelScanner class directly"""

    def test_parse_ssh_connection_with_port(self):
        """Test parsing SSH connection string with port"""
        from app.api.model_scanner import ModelScanner
        
        scanner = ModelScanner.__new__(ModelScanner)
        host, port = scanner._parse_ssh_connection('ssh -p 2838 root@104.189.178.116')
        
        self.assertEqual(host, '104.189.178.116')
        self.assertEqual(port, 2838)

    def test_parse_ssh_connection_default_port(self):
        """Test parsing SSH connection string without port"""
        from app.api.model_scanner import ModelScanner
        
        scanner = ModelScanner.__new__(ModelScanner)
        host, port = scanner._parse_ssh_connection('ssh root@104.189.178.116')
        
        self.assertEqual(host, '104.189.178.116')
        self.assertEqual(port, 22)

    def test_parse_ssh_connection_invalid(self):
        """Test parsing invalid SSH connection string"""
        from app.api.model_scanner import ModelScanner
        
        scanner = ModelScanner.__new__(ModelScanner)
        
        with self.assertRaises(ValueError):
            scanner._parse_ssh_connection('invalid connection string')

    def test_format_display_name(self):
        """Test display name formatting"""
        from app.api.model_scanner import ModelScanner
        
        scanner = ModelScanner.__new__(ModelScanner)
        
        # Test basic formatting
        self.assertEqual(scanner._format_display_name('wan2.2_i2v'), 'Wan2.2 I2V')
        self.assertEqual(scanner._format_display_name('test_model_name'), 'Test Model Name')

    def test_get_model_discovery_config(self):
        """Test loading model discovery configuration"""
        from app.api.model_scanner import get_model_discovery_config
        
        config = get_model_discovery_config()
        
        # Should return a dict with expected keys
        self.assertIsInstance(config, dict)
        self.assertIn('base_paths', config)
        self.assertIn('extensions', config)


class TestWorkflowWithNewInputTypes(unittest.TestCase):
    """Test that workflow details include new input types"""

    def setUp(self):
        """Set up test fixtures"""
        self.app = app.test_client()
        self.app.testing = True

    def test_workflow_has_layout_config(self):
        """Test that workflow returns layout configuration"""
        response = self.app.get('/create/workflows/img_to_video')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        workflow = data['workflow']
        self.assertIn('layout', workflow)
        
        # Layout should have sections
        if workflow.get('layout'):
            self.assertIn('sections', workflow['layout'])
            sections = workflow['layout']['sections']
            self.assertIsInstance(sections, list)
            self.assertGreater(len(sections), 0)

    def test_workflow_inputs_have_section_assignment(self):
        """Test that inputs have section assignments"""
        response = self.app.get('/create/workflows/img_to_video')
        data = json.loads(response.data)
        
        workflow = data['workflow']
        inputs = workflow.get('inputs', [])
        
        # At least some inputs should have section assignments
        inputs_with_sections = [i for i in inputs if i.get('section')]
        self.assertGreater(len(inputs_with_sections), 0)

    def test_workflow_has_model_selector_inputs(self):
        """Test that workflow has model selector input types"""
        response = self.app.get('/create/workflows/img_to_video')
        data = json.loads(response.data)
        
        workflow = data['workflow']
        inputs = workflow.get('inputs', [])
        
        # Check for model selector types
        input_types = [i.get('type') for i in inputs]
        
        # Should have at least one model-related input
        model_types = ['high_low_pair_model', 'high_low_pair_lora_list', 'single_model']
        has_model_input = any(t in input_types for t in model_types)
        self.assertTrue(has_model_input, f"Expected model selector types, found: {input_types}")


if __name__ == '__main__':
    unittest.main()
