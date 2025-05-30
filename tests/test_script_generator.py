"""
Tests for ScriptGenerator class
"""

import pytest
from pathlib import Path
from taskmanager.config import SlurmConfig
from taskmanager.script_generator import ScriptGenerator


class TestScriptGenerator:
    
    def test_template_creation(self, temp_dir, sample_slurm_config):
        """Test default template creation"""
        config_file = temp_dir / '.slurmparams'
        config_file.write_text(sample_slurm_config)
        
        config = SlurmConfig(str(config_file))
        template_dir = temp_dir / 'templates'
        
        generator = ScriptGenerator(config, str(template_dir))
        
        assert template_dir.exists()
        assert (template_dir / 'minimization_steep.sh.template').exists()
        assert (template_dir / 'equilibration.sh.template').exists()
    
    def test_generate_script_with_slurm_headers(self, temp_dir, sample_slurm_config):
        """Test script generation with SLURM headers"""
        config_file = temp_dir / '.slurmparams'
        config_file.write_text(sample_slurm_config)
        
        config = SlurmConfig(str(config_file))
        template_dir = temp_dir / 'templates'
        
        generator = ScriptGenerator(config, str(template_dir))
        
        output_path = temp_dir / 'test_script.sh'
        generated_path = generator.generate_script(
            'minimization_steep', 
            str(output_path),
            {'INPUT_STRUCTURE': 'test.gro'}
        )
        
        assert Path(generated_path).exists()
        
        with open(generated_path, 'r') as f:
            content = f.read()
        
        assert '#!/bin/bash' in content
        assert '#SBATCH' in content
        assert 'test.gro' in content
        assert '--partition=altair' in content
    
    def test_custom_config_application(self, temp_dir, sample_slurm_config):
        """Test applying custom configuration to templates"""
        config_file = temp_dir / '.slurmparams'
        config_file.write_text(sample_slurm_config)
        
        config = SlurmConfig(str(config_file))
        template_dir = temp_dir / 'templates'
        
        generator = ScriptGenerator(config, str(template_dir))
        
        custom_config = {
            'INPUT_STRUCTURE': 'custom_input.gro',
            'MDP_FILE': 'custom.mdp',
            'OUTPUT_PREFIX': 'custom_output'
        }
        
        output_path = temp_dir / 'custom_script.sh'
        generator.generate_script('minimization_steep', str(output_path), custom_config)
        
        with open(output_path, 'r') as f:
            content = f.read()
        
        assert 'custom_input.gro' in content
        assert 'custom.mdp' in content
        assert 'custom_output' in content
    
    def test_missing_template_error(self, temp_dir, sample_slurm_config):
        """Test error handling for missing templates"""
        config_file = temp_dir / '.slurmparams'
        config_file.write_text(sample_slurm_config)
        
        config = SlurmConfig(str(config_file))
        template_dir = temp_dir / 'templates'
        
        generator = ScriptGenerator(config, str(template_dir))
        
        with pytest.raises(FileNotFoundError, match="Template not found: nonexistent"):
            generator.generate_script('nonexistent', str(temp_dir / 'test.sh'))
    
    def test_list_available_templates(self, temp_dir, sample_slurm_config):
        """Test listing available templates"""
        config_file = temp_dir / '.slurmparams'
        config_file.write_text(sample_slurm_config)
        
        config = SlurmConfig(str(config_file))
        template_dir = temp_dir / 'templates'
        
        generator = ScriptGenerator(config, str(template_dir))
        templates = generator.list_available_templates()
        
        assert 'minimization_steep' in templates
        assert 'equilibration' in templates
        assert 'production' in templates 