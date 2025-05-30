"""
Integration tests for the complete workflow
"""

import pytest
import yaml
from pathlib import Path
from taskmanager.config import SlurmConfig
from taskmanager.job_parser import JobParser
from taskmanager.batch import BatchManager
from taskmanager.script_generator import ScriptGenerator


class TestIntegration:
    
    def test_complete_workflow(self, temp_dir, sample_slurm_config, sample_job_config):
        """Test complete workflow from config to batch script generation"""
        # Setup files
        config_file = temp_dir / '.slurmparams'
        config_file.write_text(sample_slurm_config)
        
        job_file = temp_dir / 'jobs.yaml'
        with open(job_file, 'w') as f:
            yaml.dump(sample_job_config, f)
        
        # Load configuration
        config = SlurmConfig(str(config_file))
        assert config.global_params['PARTITION'] == 'altair'
        
        # Parse jobs
        job_parser = JobParser(str(job_file))
        jobs = job_parser.get_jobs()
        assert len(jobs) == 3
        
        # Generate batch script
        batch_manager = BatchManager(config)
        script_content = batch_manager.generate_script(jobs, 'sequential')
        
        assert '#!/bin/bash' in script_content
        assert '#SBATCH --partition=altair' in script_content
        assert 'min/min_steep.sh' in script_content
        assert 'prod/prod_chunk1.sh' in script_content
    
    def test_workflow_with_profile(self, temp_dir, sample_slurm_config, sample_job_config):
        """Test workflow with execution profile"""
        # Setup files
        config_file = temp_dir / '.slurmparams'
        config_file.write_text(sample_slurm_config)
        
        job_file = temp_dir / 'jobs.yaml'
        with open(job_file, 'w') as f:
            yaml.dump(sample_job_config, f)
        
        # Parse jobs with profile
        job_parser = JobParser(str(job_file), profile='quick')
        jobs = job_parser.get_jobs()
        
        prod_job = next(job for job in jobs if job['name'] == 'production')
        assert prod_job['chunk_metadata']['total_chunks'] == 2  # Profile override
    
    def test_script_generation_integration(self, temp_dir, sample_slurm_config):
        """Test script generation with actual SLURM headers"""
        config_file = temp_dir / '.slurmparams'
        config_file.write_text(sample_slurm_config)
        
        config = SlurmConfig(str(config_file))
        generator = ScriptGenerator(config, str(temp_dir / 'templates'))
        
        output_file = temp_dir / 'test_script.sh'
        generated_path = generator.generate_script(
            'minimization_steep',
            str(output_file),
            {'INPUT_STRUCTURE': 'test.gro'}
        )
        
        # Verify script has proper headers and is executable
        script_path = Path(generated_path)
        assert script_path.exists()
        assert script_path.stat().st_mode & 0o111
        
        content = script_path.read_text()
        assert '#SBATCH --partition=altair' in content
        assert '#SBATCH --time=1-00:00:00' in content
        assert 'test.gro' in content 