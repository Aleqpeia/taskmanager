"""
Tests for BatchManager class
"""

import pytest
from taskmanager.config import SlurmConfig
from taskmanager.batch import BatchManager


class TestBatchManager:
    
    def test_generate_sequential_script(self, temp_dir, sample_slurm_config):
        """Test generating sequential batch script"""
        config_file = temp_dir / '.slurmparams'
        config_file.write_text(sample_slurm_config)
        
        config = SlurmConfig(str(config_file))
        batch_manager = BatchManager(config)
        
        jobs = [
            {
                'name': 'minimization',
                'job_type': 'minimization',
                'path': 'min',
                'nodes': 4,
                'scripts': ['min_steep.sh', 'min_cg.sh']
            },
            {
                'name': 'equilibration',
                'job_type': 'equilibration',
                'path': 'equil',
                'nodes': 6,
                'scripts': ['equil_stage1.sh']
            }
        ]
        
        script = batch_manager.generate_script(jobs, 'sequential')
        
        assert '#!/bin/bash' in script
        assert '#SBATCH' in script
        assert 'submit_job_step' in script
        assert 'min/min_steep.sh' in script
        assert 'equil/equil_stage1.sh' in script
        assert 'prev_job_id=' in script
    
    def test_generate_parallel_script(self, temp_dir, sample_slurm_config):
        """Test generating parallel batch script"""
        config_file = temp_dir / '.slurmparams'
        config_file.write_text(sample_slurm_config)
        
        config = SlurmConfig(str(config_file))
        batch_manager = BatchManager(config)
        
        jobs = [
            {
                'name': 'test_job',
                'job_type': 'production',
                'path': 'test',
                'nodes': 8,
                'scripts': ['script1.sh', 'script2.sh']
            }
        ]
        
        script = batch_manager.generate_script(jobs, 'parallel')
        
        assert '#!/bin/bash' in script
        assert 'submit_job_step' in script
        assert '(parallel)' in script
    
    def test_chunked_job_handling(self, temp_dir, sample_slurm_config):
        """Test handling of chunked jobs in batch script"""
        config_file = temp_dir / '.slurmparams'
        config_file.write_text(sample_slurm_config)
        
        config = SlurmConfig(str(config_file))
        batch_manager = BatchManager(config)
        
        jobs = [
            {
                'name': 'production',
                'job_type': 'production',
                'path': 'prod',
                'nodes': 8,
                'scripts': ['prod_chunk1.sh', 'prod_chunk2.sh'],
                'is_chunked': True,
                'chunk_metadata': {
                    'total_chunks': 2,
                    'chunk_length_ns': 10
                }
            }
        ]
        
        script = batch_manager.generate_script(jobs, 'sequential')
        
        assert 'Chunked simulation: 2 chunks × 10 ns = 20 ns total' in script
        assert 'prod/prod_chunk1.sh' in script
        assert 'prod/prod_chunk2.sh' in script 