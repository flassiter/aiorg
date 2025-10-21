"""
pytest configuration file.

Adds the project root directory to sys.path so that tests can import
from organizer and other project modules.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
