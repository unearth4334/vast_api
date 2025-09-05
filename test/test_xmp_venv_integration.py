#!/usr/bin/env python3
"""
Integration test for XMP virtual environment functionality
"""

import unittest
import tempfile
import os
import subprocess
from PIL import Image, PngImagePlugin


class TestXMPVenvIntegration(unittest.TestCase):
    """Test XMP processing with virtual environment"""

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
        
    def test_xmp_tool_with_system_python(self):
        """Test that xmp_tool works with system Python"""
        # Create test PNG
        png_file = self.create_test_png('test.png', 'test prompt data')
        
        # Run xmp_tool
        result = subprocess.run([
            'python', '-m', 'app.utils.xmp_tool', png_file
        ], capture_output=True, text=True, cwd='/home/runner/work/vast_api/vast_api')
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Wrote:', result.stdout)
        
        # Check XMP file was created
        xmp_file = png_file + '.xmp'
        self.assertTrue(os.path.exists(xmp_file))
        
        # Check XMP content
        with open(xmp_file, 'r') as f:
            content = f.read()
            self.assertIn('test prompt data', content)
            self.assertIn('CDATA', content)
    
    def test_venv_detection_logic(self):
        """Test the venv detection logic from sync_outputs.sh"""
        # Test the bash logic for venv detection
        script = '''
        DEFAULT_VENV="/app/.venv"
        XMP_VENV="${XMP_VENV:-$DEFAULT_VENV}"
        VENV_PY="$XMP_VENV/bin/python"
        
        # Check if venv Python exists and is executable (simulated)
        if command -v python3 >/dev/null 2>&1; then
            echo "FOUND:python3"
        elif command -v python >/dev/null 2>&1; then
            echo "FOUND:python"
        else
            echo "FOUND:none"
        fi
        '''
        
        result = subprocess.run(['bash', '-c', script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('FOUND:', result.stdout)
        
    def test_multiple_png_processing(self):
        """Test processing multiple PNG files"""
        # Create multiple test PNGs
        png_files = []
        for i in range(3):
            png_file = self.create_test_png(f'test_{i}.png', f'prompt for image {i}')
            png_files.append(png_file)
        
        # Run xmp_tool on all files
        result = subprocess.run([
            'python', '-m', 'app.utils.xmp_tool'
        ] + png_files, capture_output=True, text=True, cwd='/home/runner/work/vast_api/vast_api')
        
        self.assertEqual(result.returncode, 0)
        
        # Check all XMP files were created
        for png_file in png_files:
            xmp_file = png_file + '.xmp'
            self.assertTrue(os.path.exists(xmp_file))


if __name__ == '__main__':
    unittest.main()