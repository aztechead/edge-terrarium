#!/usr/bin/env -S uv run python
"""
Edge-Terrarium CLI Tool

A unified Python CLI tool for managing the Edge-Terrarium application deployment.
Replaces all Bash scripts with a maintainable Python-based solution.
"""

import sys
import os
from pathlib import Path

# Add the terrarium_cli directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "terrarium_cli"))

# Import and run the main CLI
from terrarium_cli.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
