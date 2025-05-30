"""
Utility functions
"""

import logging
import sys
from pathlib import Path


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def validate_paths(paths: list) -> bool:
    """Validate that all paths exist"""
    for path in paths:
        if not Path(path).exists():
            print(f"Error: Path does not exist: {path}")
            return False
    return True