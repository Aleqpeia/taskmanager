"""Tests for production chunker"""
import pytest
from pathlib import Path
from taskmanager.production_chunker import ProductionChunker

class TestProductionChunker:
    
    def test_chunk_calculation(self):
        """Test chunk size calculation"""
        chunker = ProductionChunker(total_chunks=3, chunk_length_ns=10)
        assert chunker.total_length_ns == 30
        assert chunker.chunk_size == 10
        
    def test_generate_chunk_scripts(self, temp_dir):
        """Test chunk script generation"""
        chunker = ProductionChunker(total_chunks=2, chunk_length_ns=5)
        scripts = chunker.generate_scripts(
            str(temp_dir),
            prefix="prod_chunk",
            mdp_template="step7_production.mdp"
        )
        
        assert len(scripts) == 2
        assert all(Path(script).exists() for script in scripts)
        
    def test_chunk_naming(self):
        """Test chunk naming convention"""
        chunker = ProductionChunker(total_chunks=3, chunk_length_ns=10)
        names = chunker.get_chunk_names("prod")
        
        assert names == ["prod1", "prod2", "prod3"] 