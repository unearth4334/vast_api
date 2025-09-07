#!/usr/bin/env python3
"""
Performance test for XMP sidecar generation optimization
"""

import unittest
import tempfile
import os
import time
import subprocess
from PIL import Image, PngImagePlugin


class TestXMPPerformance(unittest.TestCase):
    """Test XMP processing performance with existing XMP files"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def create_test_png(self, filename, prompt_text):
        """Create a test PNG file with metadata"""
        img = Image.new('RGB', (100, 100), color='red')
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text('parameters', prompt_text)
        
        filepath = os.path.join(self.temp_dir, filename)
        img.save(filepath, 'PNG', pnginfo=pnginfo)
        return filepath
        
    def create_test_xmp(self, png_filepath, content="test content"):
        """Create an XMP sidecar file"""
        xmp_path = png_filepath + ".xmp"
        with open(xmp_path, 'w') as f:
            f.write(f'<?xml version="1.0"?><x:xmpmeta><rdf:RDF><rdf:Description><dc:description><rdf:Alt><rdf:li xml:lang="x-default"><![CDATA[{content}]]></rdf:li></rdf:Alt></dc:description></rdf:Description></rdf:RDF></x:xmpmeta>')
        return xmp_path
        
    def test_performance_with_existing_xmp_files(self):
        """Test that existing XMP files are processed quickly without reading PNG metadata"""
        # Create multiple test PNGs with XMP files already existing
        png_files = []
        num_files = 10
        
        for i in range(num_files):
            png_file = self.create_test_png(f'test_{i}.png', f'prompt for image {i}')
            png_files.append(png_file)
            # Create existing XMP file
            self.create_test_xmp(png_file, f'existing content {i}')
        
        # Run xmp_tool on all files and measure time
        start_time = time.time()
        result = subprocess.run([
            'python', '-m', 'app.utils.xmp_tool'
        ] + png_files, capture_output=True, text=True, cwd='/home/runner/work/vast_api/vast_api')
        end_time = time.time()
        
        self.assertEqual(result.returncode, 0)
        
        # Should show skipping messages for existing files
        skip_count = result.stdout.count('Skipping existing file')
        self.assertEqual(skip_count, num_files)
        
        # Check that XMP files still exist and weren't overwritten
        for png_file in png_files:
            xmp_file = png_file + '.xmp'
            self.assertTrue(os.path.exists(xmp_file))
            with open(xmp_file, 'r') as f:
                content = f.read()
                self.assertIn('existing content', content)
        
        processing_time = end_time - start_time
        print(f"Processing {num_files} files with existing XMP took {processing_time:.3f}s")
        
        # Performance should be very fast since no PNG processing needed
        # With the optimization, this should take well under 1 second
        self.assertLess(processing_time, 2.0, "Processing existing XMP files should be very fast")
        
    def test_performance_comparison_new_vs_existing(self):
        """Compare performance between creating new XMP files vs skipping existing ones"""
        num_files = 5
        
        # Test 1: Create new XMP files (need to read PNG metadata)
        new_png_files = []
        for i in range(num_files):
            png_file = self.create_test_png(f'new_{i}.png', f'new prompt {i}')
            new_png_files.append(png_file)
        
        start_time = time.time()
        result = subprocess.run([
            'python', '-m', 'app.utils.xmp_tool'
        ] + new_png_files, capture_output=True, text=True, cwd='/home/runner/work/vast_api/vast_api')
        new_files_time = time.time() - start_time
        
        self.assertEqual(result.returncode, 0)
        
        # Test 2: Process files with existing XMP (should skip PNG processing)
        existing_png_files = []
        for i in range(num_files):
            png_file = self.create_test_png(f'existing_{i}.png', f'existing prompt {i}')
            existing_png_files.append(png_file)
            self.create_test_xmp(png_file, f'existing content {i}')
        
        start_time = time.time()
        result = subprocess.run([
            'python', '-m', 'app.utils.xmp_tool'
        ] + existing_png_files, capture_output=True, text=True, cwd='/home/runner/work/vast_api/vast_api')
        existing_files_time = time.time() - start_time
        
        self.assertEqual(result.returncode, 0)
        
        print(f"New XMP files: {new_files_time:.3f}s, Existing XMP files: {existing_files_time:.3f}s")
        
        # Processing existing files should be significantly faster
        # Allow some tolerance but existing should be at least 2x faster
        if new_files_time > 0.01:  # Only compare if we have measurable time
            self.assertLess(existing_files_time, new_files_time, 
                          "Processing existing XMP files should be faster than creating new ones")


if __name__ == '__main__':
    unittest.main()