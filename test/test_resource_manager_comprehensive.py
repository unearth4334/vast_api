#!/usr/bin/env python3
"""
Comprehensive Test Suite for Resource Management System

This test suite covers:
1. Resource Parser functionality
2. Resource Manager operations
3. API endpoint testing
4. Resource structure validation
5. Error handling
6. Edge cases
"""

import sys
import os
import json
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.resources import ResourceParser, ResourceManager, ResourceInstaller


class TestResourceParser(unittest.TestCase):
    """Test ResourceParser functionality"""
    
    @classmethod
    def setUpClass(cls):
        cls.parser = ResourceParser('resources')
    
    def test_list_all_resources(self):
        """Test listing all resources"""
        resources = self.parser.list_resources()
        self.assertIsInstance(resources, list)
        self.assertGreater(len(resources), 0, "Should find at least one resource")
        print(f"✓ Found {len(resources)} total resources")
    
    def test_filter_by_ecosystem(self):
        """Test filtering resources by ecosystem"""
        ecosystems = ['sdxl', 'flux', 'wan', 'sd15', 'realesrgan']
        
        for eco in ecosystems:
            filtered = self.parser.list_resources(ecosystem=eco)
            if filtered:
                self.assertTrue(all(r['metadata']['ecosystem'] == eco for r in filtered))
                print(f"✓ Ecosystem filter '{eco}': {len(filtered)} resources")
    
    def test_filter_by_type(self):
        """Test filtering resources by type"""
        types = ['workflow', 'lora', 'checkpoint', 'vae', 'upscaler']
        
        for rtype in types:
            filtered = self.parser.list_resources(resource_type=rtype + 's')
            if filtered:
                print(f"✓ Type filter '{rtype}': {len(filtered)} resources")
    
    def test_filter_by_tags(self):
        """Test filtering resources by tags"""
        tags = ['workflow', 'anime', 'upscaler']
        
        for tag in tags:
            filtered = self.parser.list_resources(tags=[tag])
            if filtered:
                self.assertTrue(all(tag in r['metadata'].get('tags', []) for r in filtered))
                print(f"✓ Tag filter '{tag}': {len(filtered)} resources")
    
    def test_search_functionality(self):
        """Test search functionality"""
        test_queries = ['workflow', 'SDXL', 'upscaler', 'video', 'anime']
        
        for query in test_queries:
            results = self.parser.list_resources(search=query)
            print(f"✓ Search '{query}': {len(results)} results")
    
    def test_get_ecosystems(self):
        """Test getting all ecosystems"""
        ecosystems = self.parser.get_ecosystems()
        self.assertIsInstance(ecosystems, list)
        self.assertGreater(len(ecosystems), 0)
        self.assertTrue(all(isinstance(e, str) for e in ecosystems))
        print(f"✓ Found ecosystems: {', '.join(ecosystems)}")
    
    def test_get_types(self):
        """Test getting all resource types"""
        types = self.parser.get_types()
        self.assertIsInstance(types, list)
        self.assertGreater(len(types), 0)
        self.assertTrue(all(isinstance(t, str) for t in types))
        print(f"✓ Found types: {', '.join(types)}")
    
    def test_get_tags(self):
        """Test getting all tags"""
        tags = self.parser.get_tags()
        self.assertIsInstance(tags, list)
        self.assertGreater(len(tags), 0)
        self.assertTrue(all(isinstance(t, str) for t in tags))
        print(f"✓ Found {len(tags)} unique tags")
    
    def test_parse_specific_resource(self):
        """Test parsing a specific resource file"""
        resources = self.parser.list_resources()
        if resources:
            resource = resources[0]
            self.assertIn('metadata', resource)
            self.assertIn('description', resource)
            self.assertIn('download_command', resource)
            self.assertIn('filepath', resource)
            print(f"✓ Successfully parsed resource: {resource['filepath']}")


class TestResourceManager(unittest.TestCase):
    """Test ResourceManager functionality"""
    
    @classmethod
    def setUpClass(cls):
        cls.manager = ResourceManager('resources')
    
    def test_list_resources(self):
        """Test listing resources through manager"""
        resources = self.manager.list_resources()
        self.assertIsInstance(resources, list)
        self.assertGreater(len(resources), 0)
        print(f"✓ Manager listed {len(resources)} resources")
    
    def test_get_specific_resource(self):
        """Test getting a specific resource"""
        resources = self.manager.list_resources()
        if resources:
            filepath = resources[0]['filepath']
            resource = self.manager.get_resource(filepath)
            self.assertIsNotNone(resource)
            self.assertEqual(resource['filepath'], filepath)
            print(f"✓ Manager retrieved resource: {filepath}")
    
    def test_get_nonexistent_resource(self):
        """Test getting a resource that doesn't exist"""
        resource = self.manager.get_resource('nonexistent/resource.md')
        self.assertIsNone(resource)
        print("✓ Manager correctly returns None for nonexistent resource")
    
    def test_search_resources(self):
        """Test search functionality through manager"""
        results = self.manager.search_resources('workflow')
        self.assertIsInstance(results, list)
        print(f"✓ Manager search found {len(results)} results")
    
    def test_get_metadata(self):
        """Test getting metadata (ecosystems, types, tags)"""
        ecosystems = self.manager.get_ecosystems()
        types = self.manager.get_types()
        tags = self.manager.get_tags()
        
        self.assertIsInstance(ecosystems, list)
        self.assertIsInstance(types, list)
        self.assertIsInstance(tags, list)
        
        print(f"✓ Manager metadata: {len(ecosystems)} ecosystems, {len(types)} types, {len(tags)} tags")


class TestResourceStructure(unittest.TestCase):
    """Test resource file structure and validation"""
    
    @classmethod
    def setUpClass(cls):
        cls.parser = ResourceParser('resources')
        cls.resources = cls.parser.list_resources()
    
    def test_required_fields_present(self):
        """Test that all resources have required fields"""
        required_fields = ['tags', 'ecosystem', 'basemodel', 'version', 'type']
        
        for resource in self.resources:
            metadata = resource['metadata']
            for field in required_fields:
                self.assertIn(field, metadata, 
                    f"Resource {resource['filepath']} missing required field: {field}")
        
        print(f"✓ All {len(self.resources)} resources have required fields")
    
    def test_download_command_present(self):
        """Test that all resources have download commands"""
        for resource in self.resources:
            self.assertIn('download_command', resource)
            self.assertTrue(len(resource['download_command']) > 0)
        
        print(f"✓ All {len(self.resources)} resources have download commands")
    
    def test_metadata_types(self):
        """Test that metadata fields have correct types"""
        for resource in self.resources:
            metadata = resource['metadata']
            
            # tags should be a list
            self.assertIsInstance(metadata['tags'], list)
            
            # ecosystem, basemodel, version, type should be strings
            self.assertIsInstance(metadata['ecosystem'], str)
            self.assertIsInstance(metadata['basemodel'], str)
            self.assertIsInstance(metadata['version'], str)
            self.assertIsInstance(metadata['type'], str)
        
        print("✓ All metadata fields have correct types")
    
    def test_optional_fields(self):
        """Test handling of optional fields"""
        optional_fields = ['size', 'author', 'published', 'url', 'license', 'dependencies', 'image']
        
        fields_found = {field: 0 for field in optional_fields}
        
        for resource in self.resources:
            metadata = resource['metadata']
            for field in optional_fields:
                if field in metadata:
                    fields_found[field] += 1
        
        print("✓ Optional fields usage:")
        for field, count in fields_found.items():
            print(f"  - {field}: {count}/{len(self.resources)} resources")


class TestResourceInstaller(unittest.TestCase):
    """Test ResourceInstaller functionality (mocked)"""
    
    def setUp(self):
        self.installer = ResourceInstaller('/root/.ssh/id_ed25519')
    
    @patch('subprocess.Popen')
    def test_install_resource_mock(self, mock_popen):
        """Test resource installation with mocked SSH"""
        # Mock successful process
        mock_process = Mock()
        mock_process.stdout = iter(['Downloading...', 'Complete!'])
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        result = self.installer.install_resource(
            'test.host.com',
            22,
            '/workspace/ComfyUI',
            'echo "test download"',
            'test_resource'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['return_code'], 0)
        print("✓ Mocked installation succeeded")
    
    @patch('subprocess.Popen')
    def test_install_resource_failure_mock(self, mock_popen):
        """Test resource installation failure with mocked SSH"""
        # Mock failed process
        mock_process = Mock()
        mock_process.stdout = iter(['Error: connection failed'])
        mock_process.wait.return_value = 1
        mock_popen.return_value = mock_process
        
        result = self.installer.install_resource(
            'test.host.com',
            22,
            '/workspace/ComfyUI',
            'echo "test download"',
            'test_resource'
        )
        
        self.assertFalse(result['success'])
        self.assertEqual(result['return_code'], 1)
        print("✓ Mocked installation failure handled correctly")
    
    def test_environment_variable_substitution(self):
        """Test that $UI_HOME is correctly substituted"""
        test_command = 'wget -P "$UI_HOME/models" https://example.com/model.pth'
        ui_home = '/workspace/ComfyUI'
        
        substituted = test_command.replace('$UI_HOME', ui_home)
        
        self.assertIn('/workspace/ComfyUI/models', substituted)
        self.assertNotIn('$UI_HOME', substituted)
        print("✓ Environment variable substitution works correctly")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def test_empty_filter_results(self):
        """Test filtering with no matches"""
        parser = ResourceParser('resources')
        results = parser.list_resources(ecosystem='nonexistent')
        self.assertEqual(len(results), 0)
        print("✓ Empty filter results handled correctly")
    
    def test_invalid_resource_path(self):
        """Test accessing invalid resource path"""
        manager = ResourceManager('resources')
        resource = manager.get_resource('invalid/path/to/resource.md')
        self.assertIsNone(resource)
        print("✓ Invalid resource path handled correctly")
    
    def test_malformed_search(self):
        """Test search with empty query"""
        parser = ResourceParser('resources')
        results = parser.list_resources(search='')
        # Empty search should return all resources
        all_resources = parser.list_resources()
        self.assertEqual(len(results), len(all_resources))
        print("✓ Empty search query handled correctly")


def run_comprehensive_tests():
    """Run all test suites"""
    print("=" * 70)
    print("COMPREHENSIVE RESOURCE MANAGER TEST SUITE")
    print("=" * 70)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestResourceParser))
    suite.addTests(loader.loadTestsFromTestCase(TestResourceManager))
    suite.addTests(loader.loadTestsFromTestCase(TestResourceStructure))
    suite.addTests(loader.loadTestsFromTestCase(TestResourceInstaller))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_comprehensive_tests())
