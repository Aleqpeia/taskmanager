"""
Pytest configuration and shared fixtures
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_slurm_config():
    """Sample SLURM configuration content"""
    return """# Global SLURM parameters
PARTITION=altair
TIME=1-00:00:00
JOB_NAME=modelbound
OUTPUT_DIR=logs
OUTPUT_PATTERN=TASKMANAGER.%A_%a.%N.out
ERROR_PATTERN=TASKMANAGER.%A_%a.%N.err
MEM_PER_CPU=512MB
NODES=8
NTASKS_PER_NODE=6
NTASKS_PER_CORE=1
CPUS_PER_TASK=4

[MINIMIZATION]
TIME=2:00:00
NODES=4

[EQUILIBRATION]
TIME=4:00:00
NODES=6

[PRODUCTION]
TIME=24:00:00
NODES=8
"""


@pytest.fixture
def sample_job_config():
    """Sample job configuration YAML"""
    return {
        'workflow': {
            'name': 'MD Simulation',
            'description': 'Complete molecular dynamics workflow',
            'base_path': '/scratch/simulations'
        },
        'jobs': [
            {
                'name': 'minimization',
                'job_type': 'minimization',
                'path': 'min',
                'nodes': 4,
                'scripts': ['min_steep.sh', 'min_cg.sh'],
                'outputs': ['step6.0_steep.gro', 'step6.0_cg.gro']
            },
            {
                'name': 'equilibration',
                'job_type': 'equilibration',
                'path': 'equil',
                'nodes': 6,
                'scripts': ['equil_stage1.sh', 'equil_stage2.sh'],
                'outputs': ['step6.1_equilibration.gro', 'step6.2_equilibration.gro']
            },
            {
                'name': 'production',
                'job_type': 'production',
                'path': 'prod',
                'nodes': 8,
                'chunk_config': {
                    'enabled': True,
                    'total_chunks': 3,
                    'chunk_length_ns': 10,
                    'script_prefix': 'prod_chunk'
                }
            }
        ],
        'execution_profiles': {
            'quick': {
                'production': {
                    'chunk_config': {
                        'total_chunks': 2,
                        'chunk_length_ns': 5
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_mdp_files(temp_dir):
    """Create sample MDP files for testing"""
    mdp_dir = temp_dir / 'modelbound'
    mdp_dir.mkdir()
    
    mdp_files = {
        'step6.0_steep.mdp': """
; Steepest descent minimization
integrator = steep
nsteps = 5000
emtol = 1000.0
""",
        'step6.0_cg.mdp': """
; Conjugate gradient minimization  
integrator = cg
nsteps = 5000
emtol = 100.0
""",
        'step6.1_equilibration.mdp': """
; NVT equilibration
integrator = md
nsteps = 50000
dt = 0.002
tcoupl = V-rescale
""",
        'step6.2_equilibration.mdp': """
; NPT equilibration
integrator = md
nsteps = 50000
dt = 0.002
tcoupl = V-rescale
pcoupl = Parrinello-Rahman
""",
        'step7_production.mdp': """
; Production MD
integrator = md
nsteps = 5000000
dt = 0.002
"""
    }
    
    for filename, content in mdp_files.items():
        (mdp_dir / filename).write_text(content)
    
    return mdp_dir 