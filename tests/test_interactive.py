"""Tests for interactive mode"""
import pytest
from taskmanager.interactive import InteractiveSession

class TestInteractiveSession:
    
    def test_session_initialization(self):
        """Test session initialization"""
        session = InteractiveSession()
        assert session.history == []
        
    def test_command_parsing(self):
        """Test command parsing"""
        session = InteractiveSession()
        cmd = session.parse_command("submit job1 --nodes=4")
        assert cmd["action"] == "submit"
        assert cmd["target"] == "job1"
        assert cmd["options"]["nodes"] == "4" 