"""
Tests for EquilibrationGenerator class
"""

import pytest
from taskmanager.equilibration_generator import EquilibrationGenerator


class TestEquilibrationGenerator:
    
    def test_discover_mdp_files(self, sample_mdp_files):
        """Test MDP file discovery"""
        generator = EquilibrationGenerator(str(sample_mdp_files))
        
        discovered = generator.discovered_mdps
        
        assert len(discovered['minimization']) == 2
        assert 'step6.0_steep.mdp' in discovered['minimization']
        assert 'step6.0_cg.mdp' in discovered['minimization']
        
        assert len(discovered['equilibration']) == 2
        assert 'step6.1_equilibration.mdp' in discovered['equilibration']
        assert 'step6.2_equilibration.mdp' in discovered['equilibration']
        
        assert len(discovered['production']) == 1
        assert 'step7_production.mdp' in discovered['production']
    
    def test_extract_step_number(self, sample_mdp_files):
        """Test step number extraction for sorting"""
        generator = EquilibrationGenerator(str(sample_mdp_files))
        
        assert generator._extract_step_number('step6.0_steep.mdp') == 6.01
        assert generator._extract_step_number('step6.0_cg.mdp') == 6.02
        assert generator._extract_step_number('step6.1_equilibration.mdp') == 6.1
        assert generator._extract_step_number('step6.2_equilibration.mdp') == 6.2
    
    def test_generate_minimization_scripts(self, sample_mdp_files, temp_dir):
        """Test minimization script generation"""
        generator = EquilibrationGenerator(str(sample_mdp_files))
        
        scripts = generator.generate_scripts(str(temp_dir), overwrite=True)
        
        assert 'min_steep.sh' in scripts['minimization']
        assert 'min_cg.sh' in scripts['minimization']
        
        steep_script = temp_dir / 'min_steep.sh'
        assert steep_script.exists()
        assert steep_script.stat().st_mode & 0o111  # Check executable
        
        with open(steep_script, 'r') as f:
            content = f.read()
        
        assert 'step6.0_steep.mdp' in content
        assert 'gmx grompp' in content
        assert 'gmx mdrun' in content
    
    def test_generate_equilibration_scripts(self, sample_mdp_files, temp_dir):
        """Test equilibration script generation"""
        generator = EquilibrationGenerator(str(sample_mdp_files))
        
        scripts = generator.generate_scripts(str(temp_dir), overwrite=True)
        
        assert 'equil_stage1.sh' in scripts['equilibration']
        assert 'equil_stage2.sh' in scripts['equilibration']
        
        equil_script = temp_dir / 'equil_stage1.sh'
        assert equil_script.exists()
        
        with open(equil_script, 'r') as f:
            content = f.read()
        
        assert 'step6.1_equilibration.mdp' in content
        assert 'Stage 1' in content
    
    def test_analyze_mdp_stage(self, sample_mdp_files):
        """Test MDP stage analysis"""
        generator = EquilibrationGenerator(str(sample_mdp_files))
        
        info = generator._analyze_mdp_stage('step6.1_equilibration.mdp')
        
        assert info['duration'] == '100 ps'  # 50000 * 0.002
        assert info['ensemble'] == 'NVT'
        assert 'NVT' in info['description']
    
    def test_show_discovered_files(self, sample_mdp_files, capsys):
        """Test discovered files display"""
        generator = EquilibrationGenerator(str(sample_mdp_files))
        generator.show_discovered_files()
        
        captured = capsys.readouterr()
        assert 'MDP Files' in captured.out
        assert 'step6.0_steep.mdp' in captured.out
        assert 'step6.1_equilibration.mdp' in captured.out
    
    def test_skip_existing_scripts(self, sample_mdp_files, temp_dir):
        """Test skipping existing scripts without overwrite"""
        generator = EquilibrationGenerator(str(sample_mdp_files))
        
        # Create existing script
        existing_script = temp_dir / 'min_steep.sh'
        existing_script.write_text('existing content')
        
        scripts = generator.generate_scripts(str(temp_dir), overwrite=False)
        
        # Should not overwrite
        assert existing_script.read_text() == 'existing content'
        
        # Should create backup when overwriting
        scripts = generator.generate_scripts(str(temp_dir), overwrite=True)
        backup_file = temp_dir / 'min_steep.sh.bak'
        assert backup_file.exists()
        assert backup_file.read_text() == 'existing content' 