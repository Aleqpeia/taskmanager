"""
Tests for JobParser class
"""

import pytest
import yaml
import json
from pathlib import Path
from taskmanager.job_parser import JobParser


class TestJobParser:
    
    def test_load_yaml_workflow(self, temp_dir, sample_job_config):
        """Test loading YAML workflow configuration"""
        job_file = temp_dir / 'jobs.yaml'
        
        with open(job_file, 'w') as f:
            yaml.dump(sample_job_config, f)
        
        parser = JobParser(str(job_file))
        
        assert parser.workflow_data['workflow']['name'] == 'MD Simulation'
        assert len(parser.workflow_data['jobs']) == 3
    
    def test_load_json_workflow(self, temp_dir, sample_job_config):
        """Test loading JSON workflow configuration"""
        job_file = temp_dir / 'jobs.json'
        
        with open(job_file, 'w') as f:
            json.dump(sample_job_config, f)
        
        parser = JobParser(str(job_file))
        
        assert parser.workflow_data['workflow']['name'] == 'MD Simulation'
        assert len(parser.workflow_data['jobs']) == 3
    
    def test_file_not_found(self, temp_dir):
        """Test handling of missing job file"""
        with pytest.raises(FileNotFoundError):
            JobParser(str(temp_dir / 'nonexistent.yaml'))
    
    def test_invalid_yaml(self, temp_dir):
        """Test handling of invalid YAML"""
        job_file = temp_dir / 'invalid.yaml'
        job_file.write_text('invalid: yaml: content [')
        
        with pytest.raises(ValueError, match="Invalid YAML"):
            JobParser(str(job_file))
    
    def test_missing_jobs_section(self, temp_dir):
        """Test handling of missing jobs section"""
        job_file = temp_dir / 'incomplete.yaml'
        
        with open(job_file, 'w') as f:
            yaml.dump({'workflow': {'name': 'test'}}, f)
        
        with pytest.raises(ValueError, match="must contain 'jobs' section"):
            JobParser(str(job_file))
    
    def test_process_regular_job(self, temp_dir, sample_job_config):
        """Test processing regular (non-chunked) job"""
        job_file = temp_dir / 'jobs.yaml'
        
        with open(job_file, 'w') as f:
            yaml.dump(sample_job_config, f)
        
        parser = JobParser(str(job_file))
        jobs = parser.get_jobs()
        
        min_job = jobs[0]
        assert min_job['name'] == 'minimization'
        assert min_job['scripts'] == ['min_steep.sh', 'min_cg.sh']
        assert not min_job.get('is_chunked', False)
    
    def test_process_chunked_job(self, temp_dir, sample_job_config):
        """Test processing chunked production job"""
        job_file = temp_dir / 'jobs.yaml'
        
        with open(job_file, 'w') as f:
            yaml.dump(sample_job_config, f)
        
        parser = JobParser(str(job_file))
        jobs = parser.get_jobs()
        
        prod_job = jobs[2]
        assert prod_job['name'] == 'production'
        assert prod_job['is_chunked'] == True
        assert len(prod_job['scripts']) == 3
        assert prod_job['scripts'] == ['prod_chunk1.sh', 'prod_chunk2.sh', 'prod_chunk3.sh']
        
        chunk_meta = prod_job['chunk_metadata']
        assert chunk_meta['total_chunks'] == 3
        assert chunk_meta['chunk_length_ns'] == 10
    
    def test_apply_profile(self, temp_dir, sample_job_config):
        """Test applying execution profile"""
        job_file = temp_dir / 'jobs.yaml'
        
        with open(job_file, 'w') as f:
            yaml.dump(sample_job_config, f)
        
        parser = JobParser(str(job_file), profile='quick')
        jobs = parser.get_jobs()
        
        prod_job = jobs[2]
        chunk_meta = prod_job['chunk_metadata']
        assert chunk_meta['total_chunks'] == 2  # Overridden by profile
        assert chunk_meta['chunk_length_ns'] == 5  # Overridden by profile
    
    def test_show_workflow_summary(self, temp_dir, sample_job_config, capsys):
        """Test workflow summary display"""
        job_file = temp_dir / 'jobs.yaml'
        
        with open(job_file, 'w') as f:
            yaml.dump(sample_job_config, f)
        
        parser = JobParser(str(job_file))
        parser.show_workflow_summary()
        
        captured = capsys.readouterr()
        assert 'MD Simulation' in captured.out
        assert 'minimization' in captured.out
        assert 'Chunked: 3 chunks' in captured.out 