#!/usr/bin/env python3
"""
Convenience script to run VastAI CLI from new location
"""
import sys
import os

# Add parent directory to path to import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.vastai.vast_cli import main

if __name__ == '__main__':
    main()