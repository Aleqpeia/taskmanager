"""
Utility functions
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(verbose: bool = False, log_file: Optional[str] = None):
    """Setup comprehensive logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup handlers
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True  # Override any existing configuration
    )
    
    return logging.getLogger(__name__)


def validate_paths(paths: list) -> bool:
    """Validate that all paths exist"""
    for path in paths:
        if not Path(path).exists():
            print(f"Error: Path does not exist: {path}")
            return False
    return True


class TaskManagerError(Exception):
    """Base exception for task manager errors"""
    pass


class ConfigurationError(TaskManagerError):
    """Configuration-related errors"""
    pass


class ValidationError(TaskManagerError):
    """Validation-related errors"""
    pass