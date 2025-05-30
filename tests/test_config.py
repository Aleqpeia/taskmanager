"""
Tests for SlurmConfig class
"""

import pytest
from pathlib import Path
from taskmanager.config import SlurmConfig


class TestSlurmConfig:
    
    def test_load_simple_config(self, temp_dir, sample_slurm_config):
        """Test loading simple key=value configuration"""
        config_file = temp_dir / '.slurmparams'
        
        # Create simple config without sections
        simple_config = """PARTITION=altair
TIME=1-00:00:00
JOB_NAME=test_job
NODES=4
CPUS_PER_TASK=2"""
        
        config_file.write_text(simple_config)
        
        config = SlurmConfig(str(config_file))
        
        assert config.global_params['PARTITION'] == 'altair'
        assert config.global_params['TIME'] == '1-00:00:00'
        assert config.global_params['NODES'] == '4'
        assert len(config.job_configs) == 0
    
    def test_load_sectioned_config(self, temp_dir, sample_slurm_config):
        """Test loading INI-style configuration with sections"""
        config_file = temp_dir / '.slurmparams'
        config_file.write_text(sample_slurm_config)
        
        config = SlurmConfig(str(config_file))
        
        # Check global parameters
        assert config.global_params['PARTITION'] == 'altair'
        assert config.global_params['TIME'] == '1-00:00:00'
        assert config.global_params['NODES'] == '8'
        
        # Check job-specific configurations
        assert 'minimization' in config.job_configs
        assert config.job_configs['minimization']['TIME'] == '2:00:00'
        assert config.job_configs['minimization']['NODES'] == '4'
    
    def test_get_job_params_with_override(self, temp_dir, sample_slurm_config):
        """Test getting job parameters with node override"""
        config_file = temp_dir / '.slurmparams'
        config_file.write_text(sample_slurm_config)
        
        config = SlurmConfig(str(config_file))
        
        # Test global parameters
        params = config.get_job_params('default')
        assert params['NODES'] == '8'
        assert params['TIME'] == '1-00:00:00'
        
        # Test job-specific parameters
        params = config.get_job_params('minimization')
        assert params['NODES'] == '4'
        assert params['TIME'] == '2:00:00'
        
        # Test node override
        params = config.get_job_params('minimization', nodes=12)
        assert params['NODES'] == '12'
        assert params['TIME'] == '2:00:00'
    
    def test_format_sbatch_options(self, temp_dir, sample_slurm_config):
        """Test SBATCH option formatting"""
        config_file = temp_dir / '.slurmparams'
        config_file.write_text(sample_slurm_config)
        
        config = SlurmConfig(str(config_file))
        
        options = config.format_sbatch_options('minimization')
        
        assert '--partition=altair' in options
        assert '--time=2:00:00' in options
        assert '--nodes=4' in options
        assert '--output=logs/TASKMANAGER.%A_%a.%N.out' in options
        assert '--error=logs/TASKMANAGER.%A_%a.%N.err' in options
    
    def test_create_default_config(self, temp_dir):
        """Test default configuration creation"""
        config_file = temp_dir / '.slurmparams'
        
        config = SlurmConfig(str(config_file))
        
        assert config_file.exists()
        assert config.global_params['PARTITION'] == 'altair'
        assert config.global_params['JOB_NAME'] == 'modelbound'
    
    def test_validate_config(self, temp_dir):
        """Test configuration validation"""
        config_file = temp_dir / '.slurmparams'
        
        # Invalid config missing required parameters
        invalid_config = """NODES=4"""
        config_file.write_text(invalid_config)
        
        config = SlurmConfig(str(config_file))
        issues = config.validate_config()
        
        assert len(issues) > 0
        assert any('PARTITION' in issue for issue in issues)
        assert any('TIME' in issue for issue in issues)
    
    def test_time_format_validation(self, temp_dir):
        """Test time format validation"""
        config_file = temp_dir / '.slurmparams'
        
        valid_config = """PARTITION=altair
TIME=1-00:00:00
JOB_NAME=test"""
        config_file.write_text(valid_config)
        
        config = SlurmConfig(str(config_file))
        
        # Test valid formats
        assert config._validate_time_format('1-00:00:00')
        assert config._validate_time_format('24:00:00')
        assert config._validate_time_format('60:00')
        assert config._validate_time_format('120')
        
        # Test invalid formats
        assert not config._validate_time_format('invalid')
        assert not config._validate_time_format('25:70:00') 