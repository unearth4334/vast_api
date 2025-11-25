#!/usr/bin/env python3
"""
Test progress parser for civitdl output
"""

import sys
sys.path.insert(0, '/home/sdamk/dev/vast_api')

from app.resources.resource_installer import ProgressParser

# Sample civitdl output from user's session
sample_output = """Now downloading "Dramatic Lighting Slider"...
                - Model ID: 1105685
                - Version ID: 1242203

Images: 100%|██████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 3.00/3.00 [00:00<00:00, 6.74iB/s]
Cache of model with version id 1242203 not found.
Model: 100%|████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 8.12M/8.12M [00:00<00:00, 60.9MiB/s]

Download completed for "Dramatic Lighting Slider"
                - Model ID: 1105685
                - Version ID: 1242203"""

print("Testing ProgressParser with civitdl output\n")
print("=" * 80)

for line in sample_output.split('\n'):
    result = ProgressParser.parse_line(line)
    if result:
        print(f"\nLine: {line[:100]}")
        print(f"Parsed: {result}")

print("\n" + "=" * 80)
print("\nTest complete!")
