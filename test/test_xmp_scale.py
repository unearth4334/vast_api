#!/usr/bin/env python3
"""
Large scale performance test for XMP sidecar generation optimization
"""

import unittest
import tempfile
import os
import time
import subprocess
from PIL import Image, PngImagePlugin


class TestXMPLargeScale(unittest.TestCase):
    """Test XMP processing performance with many files"""

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
        
    def test_large_scale_performance(self):
        """Test performance with many files where most XMP files already exist"""
        num_files = 50
        existing_ratio = 0.8  # 80% of files already have XMP
        
        png_files = []
        expected_skips = 0
        expected_processed = 0
        
        for i in range(num_files):
            png_file = self.create_test_png(f'test_{i}.png', f'prompt for image {i}')
            png_files.append(png_file)
            
            # Create XMP for most files (simulating real-world scenario)
            if i < num_files * existing_ratio:
                self.create_test_xmp(png_file, f'existing content {i}')
                expected_skips += 1
            else:
                expected_processed += 1
        
        # Run xmp_tool on all files and measure time
        start_time = time.time()
        result = subprocess.run([
            'python', '-m', 'app.utils.xmp_tool'
        ] + png_files, capture_output=True, text=True, cwd='/home/runner/work/vast_api/vast_api')
        end_time = time.time()
        
        self.assertEqual(result.returncode, 0)
        
        # Verify the performance summary output
        self.assertIn('📊 Processed', result.stdout)
        
        # Check counts in output
        skip_count = result.stdout.count('Skipping existing file')
        write_count = result.stdout.count('✅ Wrote:')
        
        self.assertEqual(skip_count, expected_skips)
        self.assertEqual(write_count, expected_processed)
        
        processing_time = end_time - start_time
        print(f"Large scale test: {num_files} files ({expected_skips} existing) took {processing_time:.3f}s")
        
        # Performance should scale well - with optimization, mostly checking file existence
        # Should easily handle 50 files in under 5 seconds
        self.assertLess(processing_time, 5.0, "Large scale processing should be fast with optimization")
        
        # Performance per file should be very low for existing files
        time_per_skip = processing_time / expected_skips if expected_skips > 0 else 0
        print(f"Time per skipped file: {time_per_skip*1000:.1f}ms")
        
        if expected_skips > 10:  # Only check if we have a reasonable number of skips
            self.assertLess(time_per_skip, 0.1, "Should skip existing files very quickly")


if __name__ == '__main__':
    unittest.main()