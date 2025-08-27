#!/bin/bash

# Activate venv in Git Bash / MINGW64
if [ -f "venv/Scripts/activate" ]; then
    echo "Activating virtual environment..."
    source venv/Scripts/activate
else
    echo "❌ venv not found. Run 'py -m venv venv' first."
fi
