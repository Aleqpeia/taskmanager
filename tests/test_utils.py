"""
Tests for utility functions
"""

import pytest
import logging
from pathlib import Path
from taskmanager.utils import setup_logging, validate_paths, TaskManagerError


class TestUtils:
    
    def test_setup_logging_console_only(self):
        """Test logging setup with console output only"""
        logger = setup_logging(verbose=True)
        
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) >= 1
    
    def test_setup_logging_with_file(self, temp_dir):
        """Test logging setup with file output"""
        log_file = temp_dir / 'test.log'
        logger = setup_logging(verbose=False, log_file=str(log_file))
        
        assert logger.level == logging.INFO
        
        # Test logging works
        logger.info("Test message")
        assert log_file.exists()
        assert 'Test message' in log_file.read_text()
    
    def test_validate_paths_success(self, temp_dir):
        """Test path validation with existing paths"""
        # Create test files
        file1 = temp_dir / 'file1.txt'
        file2 = temp_dir / 'file2.txt'
        file1.touch()
        file2.touch()
        
        paths = [str(file1), str(file2)]
        assert validate_paths(paths) == True
    
    def test_validate_paths_failure(self, temp_dir):
        """Test path validation with missing paths"""
        file1 = temp_dir / 'file1.txt'
        file1.touch()
        
        paths = [str(file1), str(temp_dir / 'nonexistent.txt')]
        assert validate_paths(paths) == False
    
    def test_custom_exceptions(self):
        """Test custom exception classes"""
        with pytest.raises(TaskManagerError):
            raise TaskManagerError("Test error")
        
        from taskmanager.utils import ConfigurationError, ValidationError
        
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Config error")
        
        with pytest.raises(ValidationError):
            raise ValidationError("Validation error") 