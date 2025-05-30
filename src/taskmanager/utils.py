import logging
from pathlib import Path

class TaskManagerError(Exception):
    """Base exception class for TaskManager errors"""
    pass

class ConfigurationError(TaskManagerError):
    """Configuration related errors"""
    pass

class ValidationError(TaskManagerError):
    """Validation related errors"""
    pass

def validate_paths(paths):
    """
    Validate that all paths in the list exist
    
    Args:
        paths (list): List of paths to validate
        
    Returns:
        bool: True if all paths exist, False otherwise
    """
    for path in paths:
        if not Path(path).exists():
            return False
    return True

def setup_logging(verbose=False, log_file=None):
    """Setup logging configuration"""
    logger = logging.getLogger('taskmanager.utils')
    
    # Clear any existing handlers
    logger.handlers = []
    
    # Set the base logging level
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    # Create formatters and handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger 